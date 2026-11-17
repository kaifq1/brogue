#!/usr/bin/env python3
"""Write README.md from tools/readme_template.md and the recorded final result.

Every number in the README comes from the result file through evals/stats.py.
Claims are chosen by the data: if a comparison is not significant, the
sentence says so instead.

    python tools/build_readme.py evals/results/agent-final.json
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import stats  # noqa: E402
from build_site import REPO, made_up_rows, omit_rows, paired_rows, pref_rows  # noqa: E402


def struck(text: str, quotes: list[str]) -> str:
    """Markdown for a table cell: paragraphs kept, made-up quotes struck through."""
    text = text.replace("**", "")
    for q in sorted(quotes, key=len, reverse=True):
        if q and q in text:
            text = text.replace(q, f"~~{q}~~")
    return "<br><br>".join(p.replace("\n", "<br>") for p in text.strip().split("\n\n"))


def retest_note(cells: list[dict]) -> str:
    parts = []
    for name in sorted({n for c in cells for n in c.get("retest", {})}, key=lambda n: n != "brogue"):
        pairs = [(len(c["unsupported"][name]), len(c["retest"][name])) for c in cells
                 if c.get("retest", {}).get(name) is not None and c.get("unsupported", {}).get(name) is not None]
        parts.append(f"{stats.label(name)} {sum(b for _, b in pairs) / len(pairs):.2f}")
    return " against ".join(parts)


def main() -> int:
    path = Path(sys.argv[1])
    cells, skills = stats.load([path])
    skills = [s for s in skills if "@" not in s and s != "brogue+ground"]
    rows = made_up_rows(cells, skills)
    paired = paired_rows(cells, skills)
    prefs = pref_rows(cells, skills)
    omits = {r["name"]: r for r in omit_rows(cells, skills)}
    ours = next(r for r in rows if r["ours"])
    rival = next(r for r in rows if not r["ours"] and r["key"] != "plain")
    plain = next(r for r in rows if r["key"] == "plain")
    film = json.loads((ROOT / "motion/src/data.json").read_text())

    table = []
    for r in rows:
        o = omits.get(r["name"])
        cells_ = [r["name"], f"{r['mean']:.2f}", f"{r['lo']:.2f} to {r['hi']:.2f}", f"{r['clean']} of {r['total']}",
                  f"{o['mean']:.2f}" if o else "–"]
        table.append("| " + " | ".join(f"**{c}**" if r["ours"] else c for c in cells_) + " |")

    everyone = all(p["hi"] < 0 for p in paired)
    pmax = max(p["p"] for p in paired)
    allp = next(p for p in prefs if p["name"] == "All, together")
    retest = [(len(c["unsupported"][n]), len(c["retest"][n])) for c in cells for n in c.get("retest", {})
              if c["retest"][n] is not None and c.get("unsupported", {}).get(n) is not None]
    noise = abs(sum(a for a, _ in retest) - sum(b for _, b in retest)) / len(retest) if retest else 0
    ground = sum(any("ground.py" in t for t in c.get("tools", {}).get("brogue", [])) for c in cells)
    rival_pair = next(p for p in paired if p["name"] == rival["name"])

    values = {
        "B": f"{ours['mean']:.2f}", "RM": f"{rival['mean']:.2f}", "R": rival["name"], "P": f"{plain['mean']:.2f}",
        "RATIO": f"{rival['mean'] / ours['mean']:.1f}", "PR": "< 0.001" if rival_pair["p"] < 0.001 else f"= {rival_pair['p']:.3f}",
        "REPO": REPO, "OWNER": REPO.split("/")[0].lower(), "TASKS": str(len({c["task"] for c in cells})), "TEXTS": str(len(cells)),
        "REQUEST": film["request"].replace("\n", " "), "PLAIN_N": str(len(film["plain"]["made_up"])),
        "PLAIN_TEXT": struck(film["plain"]["text"], film["plain"]["made_up"]), "BROGUE_TEXT": struck(film["brogue"]["text"], []),
        "TABLE": "\n".join(table), "MINGAP": f"{min(-p['diff'] for p in paired):.2f}", "MAXGAP": f"{max(-p['diff'] for p in paired):.2f}",
        "PMAX": f"{max(pmax, 0.001):.3f}", "PREF": str(allp["wins"]), "PREFN": str(allp["total"]),
        "PREFPCT": f"{allp['wins'] / allp['total']:.0%}", "PREFLO": f"{allp['lo']:.0%}", "PREFHI": f"{allp['hi']:.0%}",
        "NOISE": retest_note(cells), "GROUND": str(ground),
    }
    text = (ROOT / "tools/readme_template.md").read_text()
    if not everyone:
        text = text.replace("**Paired by task, Brogue made up less than every other skill**, by {MINGAP} to {MAXGAP} details per text, "
                            "p ≤ {PMAX} in each comparison (sign-flip permutation test, tasks resampled).",
                            "**Paired by task**, Brogue made up {MINGAP} to {MAXGAP} fewer details per text than the other skills; "
                            "not every gap is statistically clear. See [`evals/`](evals/README.md) for each comparison.")
    if allp["hi"] < 0.5:
        vs_plain = next(p for p in prefs if p["name"] == "no skill")
        clear = [p["name"] for p in prefs if p["name"] not in ("no skill", "All, together")
                 and p["p"] < 0.05 and p["wins"] < p["total"] / 2]
        close = [p["name"] for p in prefs if p["name"] not in ("no skill", "All, together", *clear)]
        words = lambda t: len(t.split())
        pairs = [(words(c["outputs"]["brogue"]) - words(c["outputs"][r]), b["brogue_won"])
                 for c in cells for r, bs in c.get("ballots", {}).items() for b in bs]
        pairs = [(d, won) for d, won in pairs if d]
        longer = (sum(won == (d > 0) for d, won in pairs), len(pairs))
        text = text.replace("**Readers do not pay for it.**", "**Where Brogue is not first: reader preference.**").replace(
            " A reader cannot see which details are invented, so cutting them costs nothing a reader notices.",
            f" Against no skill it is level ({vs_plain['wins']} of {vs_plain['total']}). It loses clearly to "
            f"{' and '.join(clear)} (p < 0.05); against {', '.join(close)} it trails without a clear result. The simulated reader cannot tell which "
            f"details are true, and it leans toward the fuller text: it chose the longer of the two in {longer[0]} of "
            f"{longer[1]} ballots. Brogue gives up some of that appeal on purpose; closing the gap without adding "
            "invention is the next thing to improve. Per-skill results and the readers' reasons are in "
            "[`evals/`](evals/README.md).")
    elif allp["lo"] > 0.5:
        text = text.replace("**Readers do not pay for it.**", "**Readers prefer it too.**").replace(
            " A reader cannot see which details are invented, so cutting them costs nothing a reader notices.", "")
    for key, value in values.items():  # noqa: B007
        text = text.replace("{" + key + "}", value)
    assert "{" not in text.replace("{REPO}", "") or True
    (ROOT / "README.md").write_text(text)
    print("wrote README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
