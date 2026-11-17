import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from brogue import fact_guard, from_sample, ground, humanize, lint, load_persona, presets, steer
from brogue import panel
from brogue.cli import main as cli
from brogue.mirofish import MiroFish
from brogue.persona import violations

ROOT = Path(__file__).resolve().parents[1]
AI = (ROOT / "examples/ai_draft.md").read_text()
HUMAN = (ROOT / "examples/human_draft.md").read_text()
CLEAN = ("We shipped the new onboarding flow. Setup time fell from 14 minutes to 6, and activation "
         "rose 22% in March. I'd wait for April before calling it a trend.")


# -- lint -------------------------------------------------------------------
def test_ai_draft_routes_to_rewrite_and_human_passes():
    assert lint(AI).route == "rewrite"
    assert lint(HUMAN).route == "pass"


def test_expected_rules_fire_on_ai_draft():
    hit = lint(AI).by_rule
    for rule in ("chatbot-residue", "not-x-but-y", "trailing-ing", "weasel-source",
                 "summary-closer", "colon-reveal", "staccato", "em-dash", "ai-vocab"):
        assert rule in hit, rule


def test_code_and_quotes_are_not_linted():
    text = "Run it:\n\n```\nleverage --robust --seamless\n```\n\n> We delve into a rich tapestry.\n\nIt works."
    assert lint(text).findings == []


def test_one_stray_word_in_a_short_reply_still_passes():
    assert lint("Thanks. The estimator is robust to outliers, so I kept it.").route == "pass"


def test_metronome():
    text = " ".join(["The team shipped the new feature last week."] * 7)
    assert "metronome" in lint(text).by_rule


# -- guard ------------------------------------------------------------------
def test_guard_catches_invented_and_dropped_facts():
    source = 'Revenue rose 12% to $4,200. See https://example.com/q3. She said "we are not done".'
    assert fact_guard(source, source.replace("rose", "grew")).ok
    bad = fact_guard(source, "Revenue grew 15% to $4,200, per a 2024 study.")
    assert "15%" in bad.added["number"] and "2024" in bad.added["number"]
    assert "12%" in bad.dropped["number"]
    assert bad.dropped["url"] == ["https://example.com/q3"]
    assert bad.dropped["quote"] == ["we are not done"]


# -- personas ---------------------------------------------------------------
def test_presets_load_and_brief():
    names = presets()
    assert {"neutral", "corporate-us", "corporate-in", "casual-us", "support-empathetic"} <= set(names)
    brief = load_persona("corporate-in").brief()
    assert "british spelling" in brief and "No contractions" in brief
    with pytest.raises(KeyError):
        load_persona("nope")


def test_persona_violations():
    formal = load_persona("corporate-in")
    assert any("contractions" in v for v in violations("We don't organize the color charts.", formal))
    assert any("American" in v for v in violations("We organize the color charts.", formal))
    assert violations("We organise the colour charts for the organism study.", formal) == []


def test_profile_from_sample():
    casual = from_sample("I don't think it's ready. We'll fix it. Can't ship yet, honestly. It's close.")
    assert casual.register == "casual" and casual.contractions == "use"
    formal = from_sample(
        "The committee has reviewed the proposal in considerable detail and wishes to record its "
        "appreciation for the thoroughness of the supporting analysis provided by the finance team. "
        "It is the view of the committee that the programme should proceed, subject to the conditions "
        "set out in the accompanying schedule and to confirmation of funding in the next quarter.")
    assert formal.register == "formal" and formal.contractions == "avoid"


def test_steer_carries_persona_and_invariants():
    text = steer(load_persona("corporate-uk"))
    assert "Add no fact" in text and "british spelling" in text


# -- pipeline ---------------------------------------------------------------
def test_clean_text_passes_without_calling_the_model():
    def boom(system, user):
        raise AssertionError("model must not be called")
    result = humanize(HUMAN, "neutral", boom)
    assert result.route == "pass" and not result.changed and result.passes == 0


def test_rewrite_accepted_when_facts_hold():
    result = humanize(AI, "neutral", lambda s, u: CLEAN)
    assert result.changed and result.text == CLEAN and result.after.score < result.before.score


def test_invented_fact_is_rejected_then_retried():
    replies = iter([CLEAN.replace("22%", "31%"), CLEAN])
    seen = []
    def model(system, user):
        seen.append(user)
        return next(replies)
    result = humanize(AI, "neutral", model)
    assert result.text == CLEAN and result.passes == 2
    assert "31%" in seen[1]  # the rejection reason is fed back


def test_original_returned_when_every_attempt_fails():
    result = humanize(AI, "neutral", lambda s, u: "Activation rose 99%.")
    assert not result.changed and result.text == AI
    assert "original returned" in result.warnings[-1]


def test_persona_mismatch_alone_triggers_an_edit():
    calls = []
    def model(system, user):
        calls.append(user)
        return HUMAN.replace("don't", "do not").replace("I'd", "I would")
    result = humanize(HUMAN, "corporate-in", model)
    assert result.route == "edit" and result.changed and "reader mismatch" in calls[0]


def test_no_model_returns_text_with_warning():
    result = humanize(AI, "neutral", None)
    assert not result.changed and result.warnings


# -- panel ------------------------------------------------------------------
def _juror(prefers):
    """A fake reader that picks whichever version contains `prefers`."""
    def model(system, user):
        a = user.split("<version_a>")[1].split("</version_a>")[0]
        pick, other = ("A", "B") if prefers in a else ("B", "A")
        return "Sure. " + json.dumps({"choice": pick, "human": {pick: 8, other: 3},
                                      "fit": {pick: 7, other: 4}, "why": "it gets to the point"})
    return model


def test_panel_prefers_humanized_and_is_order_balanced():
    report = panel.run(AI, CLEAN, ["corporate-us", "casual-us"], _juror("I'd wait"))
    assert len(report.ballots) == 4 and report.win_rate == 1.0 and report.position_bias == 0.5
    assert report.verdict.startswith("humanized")
    assert report.by_juror()["corporate-us"]["human_delta"] == 5
    assert "corporate-us" in report.markdown()


def test_panel_flags_position_bias_and_spoiled_ballots():
    always_a = lambda s, u: '{"choice": "A", "human": {"A": 5, "B": 5}, "fit": {"A": 5, "B": 5}}'
    assert "position" in panel.run(AI, CLEAN, ["neutral"], always_a).verdict
    assert panel.run(AI, CLEAN, ["neutral"], lambda s, u: "no idea").spoiled == 2


# -- mirofish (against a stub of its HTTP API) --------------------------------
class _Stub(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args):
        pass

    def _reply(self, data):
        body = json.dumps({"success": True, "data": data}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.calls.append(self.path)
        self._reply({"status": "completed"})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"])).decode()
        self.calls.append(self.path)
        if self.path.endswith("/ontology/generate"):
            assert 'filename="seed.md"' in raw and "corporate-us" in raw
            return self._reply({"project_id": "proj_1"})
        if self.path.endswith("/interview/all"):
            prompt = json.loads(raw)["prompt"]
            a = prompt.split("VERSION A:")[1].split("VERSION B:")[0]
            pick, other = ("A", "B") if "I'd wait" in a else ("B", "A")
            vote = json.dumps({"choice": pick, "human": {pick: 9, other: 2}, "fit": {pick: 8, other: 3}})
            return self._reply({"result": {"results": {
                "reddit_0": {"agent_id": 0, "response": vote},
                "reddit_1": {"agent_id": 1, "response": "I refuse."}}}})
        self._reply({"task_id": "t1", "simulation_id": "sim_1", "status": "ready", "env_alive": True})


def test_mirofish_adapter_walks_the_api_and_parses_ballots():
    _Stub.calls = []
    server = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = MiroFish(f"http://127.0.0.1:{server.server_port}", poll_seconds=0.01)
        report = client.run_panel(AI, CLEAN, ["corporate-us"])
    finally:
        server.shutdown()
    assert [c.rsplit("/api/", 1)[1] for c in _Stub.calls] == [
        "graph/ontology/generate", "graph/build", "graph/task/t1", "simulation/create",
        "simulation/prepare", "simulation/prepare/status", "simulation/start",
        "simulation/env-status", "simulation/interview/all", "simulation/interview/all",
        "simulation/close-env"]
    assert report.win_rate == 1.0 and report.spoiled == 2 and report.source == "mirofish:sim_1"


# -- cli and skill packaging ------------------------------------------------
def test_readme_example_numbers_are_true():
    rewrite = (ROOT / "examples/rewrite_neutral.md").read_text()
    assert lint(AI).score == 100 and lint(rewrite).score == 0
    assert fact_guard(AI, rewrite).ok


def test_cli(capsys):
    assert cli(["lint", str(ROOT / "examples/ai_draft.md"), "--fail-at", "30"]) == 1
    assert cli(["lint", str(ROOT / "examples/human_draft.md"), "--fail-at", "30"]) == 0
    assert cli(["personas"]) == 0 and cli(["steer", "--persona", "corporate-in"]) == 0
    assert cli(["lint", "missing.md"]) == 3
    assert "corporate-in" in capsys.readouterr().out


def test_skill_is_well_formed_and_linter_copy_is_in_sync():
    skill = ROOT / "skills/brogue"
    import importlib.util
    spec = importlib.util.spec_from_file_location("bundle", ROOT / "tools/bundle_skill.py")
    bundle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bundle)
    assert (skill / "scripts/lint.py").read_text() == bundle.lint_script()
    assert (skill / "scripts/ground.py").read_text() == bundle.ground_script()  # run tools/bundle_skill.py
    text = (skill / "SKILL.md").read_text()
    front = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL).group(1)
    name = re.search(r"^name: (.+)$", front, re.M).group(1)
    description = re.search(r"^description: (.+)$", front, re.M).group(1)
    assert name == skill.name and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)
    assert description.startswith("Use when") and len(description) <= 1024
    assert len(text.splitlines()) < 500
    for ref in re.findall(r"`((?:references|scripts)/[\w./-]+)`", text):
        assert (skill / ref).exists(), ref


def test_the_skill_passes_its_own_linter():
    for path in [*(ROOT / "skills/brogue").rglob("*.md"), ROOT / "README.md"]:
        if path.name == "tells.md":  # quotes the patterns on purpose
            continue
        assert lint(path.read_text()).score < 10, path


def test_openai_compatible_client_and_cli_humanize(capsys, monkeypatch):
    class Chat(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            sent = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/v1/chat/completions" and sent["model"] == "stub"
            assert self.headers["Authorization"] == "Bearer k"
            body = json.dumps({"choices": [{"message": {"content": f"```\n{CLEAN}\n```"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Chat)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("BROGUE_API_KEY", "k")
    try:
        code = cli(["humanize", str(ROOT / "examples/ai_draft.md"), "--model", "stub",
                    "--base-url", f"http://127.0.0.1:{server.server_port}/v1"])
    finally:
        server.shutdown()
    out = capsys.readouterr()
    assert code == 0 and out.out.strip() == CLEAN and "100 -> 0" in out.err


def test_deliberation_shows_other_readers_reasons_and_revotes():
    seen = []
    base = _juror("I'd wait")
    def model(system, user):
        seen.append(user)
        return base(system, user)
    report = panel.run(AI, CLEAN, ["corporate-us", "casual-us"], model, deliberate=True)
    assert report.source.endswith("deliberated") and len(report.ballots) == 4 and len(seen) == 8
    assert "other readers said" not in seen[0] and "A reader who preferred" in seen[-1]


def test_empty_claims_are_flagged():
    text = ("Activation rose 22%. That number is more than a metric. The results are clear. "
            "This launch reflects our broader approach to helping users.")
    assert lint(text).by_rule.get("empty-claim") == 3


def test_claude_cli_backend_passes_system_prompt_and_isolates(tmp_path):
    from brogue.llm import ClaudeCLI, LLMError
    fake = tmp_path / "claude"
    fake.write_text('#!/bin/sh\nprintf "%s|" "$@"\ncat\n')
    fake.chmod(0o755)
    out = ClaudeCLI("haiku", binary=str(fake))("SYS", "hello")
    assert "--system-prompt|SYS|" in out and "--safe-mode" in out and out.endswith("hello")
    broken = tmp_path / "bad"
    broken.write_text("#!/bin/sh\necho nope >&2\nexit 1\n")
    broken.chmod(0o755)
    with pytest.raises(LLMError, match="nope"):
        ClaudeCLI("haiku", binary=str(broken))("s", "u")


def test_showcase_page_and_docs_are_built_from_recorded_results():
    page = (ROOT / "docs/index.html").read_text()
    assert "__DATA__" not in page and "__REPO__" not in page and '"made_up"' in page
    assert (ROOT / "assets/arena.svg").read_text().startswith("<svg")
    summary = json.loads((ROOT / "evals/results/summary.json").read_text())
    rows = {r["key"]: r for r in summary["made_up"]}
    readme = (ROOT / "README.md").read_text()
    best_rival = min((r for k, r in rows.items() if k not in ("brogue", "plain")), key=lambda r: r["mean"])
    for row in (rows["brogue"], best_rival, rows["plain"]):  # headline numbers are the recorded ones
        assert f"{row['mean']:.2f}" in readme
    film = json.loads((ROOT / "motion/src/data.json").read_text())
    assert {r["name"]: r["mean"] for r in film["rows"]} == {r["name"]: r["mean"] for r in summary["made_up"]}


def test_stats_are_sane():
    import sys
    sys.path.insert(0, str(ROOT / "evals"))
    import stats
    lo, hi = stats.wilson(50, 100)
    assert lo < 0.5 < hi and abs(stats.binomial_p(50, 100) - 1) < 1e-9 and stats.binomial_p(90, 100) < 1e-9
    groups = {"a": [1.0, 1.0], "b": [0.0], "c": [2.0]}
    assert stats.cluster_mean(groups) == 1.0


# --- grounding ---------------------------------------------------------------

REQUEST = "Announce that our app now syncs with Outlook. It took 4 months."
DRAFT = "Our app now syncs with Outlook. It took 4 months. Changes sync both ways."


def _checker(unsupported: str, text: str):
    return lambda system, user: f"<unsupported>\n{unsupported}\n</unsupported>\n<text>\n{text}\n</text>"


def test_ground_removes_what_the_request_never_said():
    result = ground(REQUEST, DRAFT, _checker("Changes sync both ways.", "Our app now syncs with Outlook. It took 4 months."))
    assert result.changed and result.removed == ["Changes sync both ways."]
    assert "both ways" not in result.text


def test_ground_leaves_a_supported_draft_alone():
    result = ground(REQUEST, DRAFT, _checker("none", DRAFT))
    assert not result.changed and result.text == DRAFT and not result.warnings


def test_ground_refuses_a_fix_that_adds_or_drops_a_fact():
    added = ground(REQUEST, DRAFT, _checker("x", "Our app now syncs with Outlook. It took 4 months and 2 engineers."))
    dropped = ground(REQUEST, DRAFT, _checker("x", "Our app now syncs with Outlook."))
    for result in (added, dropped):
        assert result.text == DRAFT and not result.changed and result.warnings
    assert ground(REQUEST, DRAFT, lambda s, u: "sorry").warnings
    spelled = "Our app now syncs with Outlook. It took four months. Changes sync both ways."
    assert ground(REQUEST, spelled, _checker("x", "Our app now syncs with Outlook.")).text == spelled
    assert ground(REQUEST, spelled, _checker("x", "Our app now syncs with Outlook. It took four months.")).changed
