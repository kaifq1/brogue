#!/usr/bin/env python3
"""Build the showcase page and the README chart from recorded results.

Everything shown is a recorded model output from the result files given on the
command line, and every number is computed here from those files with the
same statistics as `stats.py`. Nothing on the page is typed in by hand.

    python evals/build_site.py evals/results/agent-*.json
"""
from __future__ import annotations

import html
import json
import random
import sys
from pathlib import Path

import stats
from brogue import lint
from arena import reader_of

ROOT = Path(__file__).resolve().parents[1]
REPO = "KAIFQ1/brogue"
GROUNDED = "brogue+ground"  # older result files only
MODEL_NAMES = {"haiku": "Claude Haiku", "sonnet": "Claude Sonnet", "opus": "Claude Opus"}
INK, MUTED, SURFACE, GOOD, REST, GRID = "#1b1a17", "#6b675e", "#fffdf8", "#1f7a52", "#9a958a", "#e2ddd0"


def task_labels() -> dict[str, str]:
    """Task id to a readable label: the role name from task files, else the id."""
    out = {}
    for f in (ROOT / "evals/data").glob("tasks-*.json"):
        for t in json.loads(f.read_text())["tasks"]:
            out[t["name"]] = t.get("role", t["name"]).split(":")[0].strip()
    return out


def label(name: str) -> str:
    return stats.label(name)


def made_up_rows(cells: list[dict], skills: list[str]) -> list[dict]:
    rng = random.Random(stats.SEED)
    rows = []
    for name in skills:
        groups = stats.by_task(cells, lambda c, n=name: len(c["unsupported"][n])
                               if c.get("unsupported", {}).get(n) is not None else None)
        if not groups:
            continue
        values = [v for vs in groups.values() for v in vs]
        lo, hi = stats.bootstrap(groups, rng)
        rows.append({"name": label(name), "key": name, "ours": name == "brogue", "mean": round(stats.cluster_mean(groups), 2),
                     "lo": round(lo, 2), "hi": round(hi, 2), "clean": sum(v == 0 for v in values), "total": len(values)})
    return sorted(rows, key=lambda r: r["mean"])


def paired_rows(cells: list[dict], skills: list[str]) -> list[dict]:
    rng = random.Random(stats.SEED)
    rows = []
    for name in [s for s in skills if s != "brogue"]:
        def diff(c, n=name):
            u = c.get("unsupported", {})
            return None if u.get("brogue") is None or u.get(n) is None else len(u["brogue"]) - len(u[n])
        groups = stats.by_task(cells, diff)
        per_task = [sum(v) / len(v) for v in groups.values()]
        lo, hi = stats.bootstrap(groups, rng)
        rows.append({"name": label(name), "diff": round(stats.cluster_mean(groups), 2), "lo": round(lo, 2), "hi": round(hi, 2),
                     "p": round(stats.sign_flip_p(groups, rng), 4), "better": sum(d < 0 for d in per_task),
                     "same": sum(d == 0 for d in per_task), "worse": sum(d > 0 for d in per_task)})
    return sorted(rows, key=lambda r: r["diff"])


def pref_rows(cells: list[dict], skills: list[str]) -> list[dict]:
    rows = []
    for name in [s for s in skills if s != "brogue"] + [None]:
        votes = [b for c in cells for r, bs in c.get("ballots", {}).items() if name in (None, r) for b in bs]
        if votes:
            k, n = sum(b["brogue_won"] for b in votes), len(votes)
            lo, hi = stats.wilson(k, n)
            rows.append({"name": "All, together" if name is None else label(name), "wins": k, "total": n,
                         "lo": round(lo, 3), "hi": round(hi, 3), "p": round(stats.binomial_p(k, n), 3)})
    return rows


def omit_rows(cells: list[dict], skills: list[str]) -> list[dict]:
    rows = []
    for name in skills:
        vals = [len(c["omitted"][name]) for c in cells if c["kind"] == "write" and c.get("omitted", {}).get(name) is not None]
        if vals:
            rows.append({"name": label(name), "mean": round(sum(vals) / len(vals), 2), "missing": sum(v > 0 for v in vals), "total": len(vals)})
    return sorted(rows, key=lambda r: r["mean"])


def chart_svg(rows: list[dict], note: str) -> str:
    """The README chart: dot and 95% interval per skill, Brogue in green."""
    top = max(r["hi"] for r in rows)
    scale = max(1, int(-(-top // 1)))
    left, width, row_h, head = 170, 400, 36, 74
    height = head + row_h * len(rows) + 52
    x = lambda v: left + width * v / scale
    font = "ui-sans-serif, system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {height}" width="680" height="{height}" '
             f'font-family="{font}" role="img" aria-label="Made-up details per text by writing skill, with 95% intervals. Lower is better.">',
             f'<rect width="680" height="{height}" rx="12" fill="{SURFACE}"/>',
             f'<text x="24" y="32" font-size="16" font-weight="600" fill="{INK}">Made-up details per text (lower is better)</text>',
             f'<text x="24" y="53" font-size="12.5" fill="{MUTED}">{html.escape(note)}</text>']
    for tick in range(scale + 1):
        parts.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{head - 6}" y2="{head + row_h * len(rows)}" stroke="{GRID}"/>')
        parts.append(f'<text x="{x(tick):.1f}" y="{head + row_h * len(rows) + 18}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{tick}</text>')
    for i, r in enumerate(rows):
        y = head + i * row_h + row_h / 2
        color = GOOD if r["ours"] else REST
        weight = 700 if r["ours"] else 400
        parts += [f'<text x="{left - 14}" y="{y + 4.5:.1f}" font-size="13" text-anchor="end" font-weight="{weight}" fill="{INK}">{html.escape(r["name"])}</text>',
                  f'<rect x="{x(r["lo"]):.1f}" y="{y - 3.5:.1f}" width="{max(x(r["hi"]) - x(r["lo"]), 2):.1f}" height="7" rx="3.5" fill="{color}" opacity=".28"/>',
                  f'<circle cx="{x(r["mean"]):.1f}" cy="{y:.1f}" r="{7 if r["ours"] else 6}" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>',
                  f'<text x="{x(r["hi"]) + 10:.1f}" y="{y + 4.5:.1f}" font-size="13" font-weight="{600 if r["ours"] else 400}" fill="{INK}">{r["mean"]:.2f}</text>']
    parts.append(f'<text x="24" y="{height - 14}" font-size="11.5" fill="{MUTED}">Dots are means; bars are 95% intervals from resampling tasks.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def page(cells: list[dict], skills: list[str], meta: dict) -> str:
    samples, names = [], task_labels()
    for c in cells:
        if c.get("rep", 0) != 0 or not all(c["outputs"].get(n) for n in skills):
            continue
        outputs = {}
        for name in skills:
            text = c["outputs"][name]
            outputs[name] = {"text": text, "words": lint(text).words, "made_up": c.get("unsupported", {}).get(name)}
        samples.append({"id": f"{c['set']}/{c['task']}/{c['kind']}", "kind": c["kind"], "label": names.get(c["task"], c["task"].replace("-", " ")),
                        "reader": reader_of(c["persona"]), "source": c["source"], "outputs": outputs})
    gap = lambda s: len(s["outputs"]["plain"]["made_up"] or []) - len(s["outputs"]["brogue"]["made_up"] or [])
    start = max((s for s in samples if s["kind"] == "write"), key=gap)["id"]
    rows = made_up_rows(cells, skills)
    best_rival = next(r["key"] for r in rows if not r["ours"] and r["key"] != "plain")
    omits = omit_rows(cells, skills)
    ours_omit = next((r for r in omits if r["name"] == "Brogue"), None)
    omit_note = (f"The opposite failure, leaving out a fact the request supplied: Brogue {ours_omit['mean']:.2f} per text "
                 f"({ours_omit['missing']} of {ours_omit['total']}), other skills from {min(r['mean'] for r in omits):.2f} "
                 f"to {max(r['mean'] for r in omits):.2f}.") if ours_omit else ""
    data = {"samples": samples, "skills": skills, "start": start, "default_rival": best_rival, "made_up": rows,
            "paired": paired_rows(cells, skills), "prefs": pref_rows(cells, skills), "omit_note": omit_note, "meta": meta}
    template = (ROOT / "evals/site_template.html").read_text().replace("__REPO__", REPO)
    return template.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]]
    cells, skills = stats.load(paths)
    first = json.loads(paths[0].read_text())
    skills = [s for s in skills if s != GROUNDED and "@" not in s]
    tasks = len({f"{c['set']}/{c['task']}" for c in cells})
    meta = {"writer": MODEL_NAMES.get(first["writer"], first["writer"]), "judge": MODEL_NAMES.get(first["judge"], first["judge"]),
            "tasks": tasks, "texts": len(cells)}
    rows = made_up_rows(cells, skills)
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "assets/arena.svg").write_text(chart_svg(rows, f"{len(cells)} texts per skill, {tasks} tasks, agent sessions on {meta['writer']}, audited by {meta['judge']}."))
    (ROOT / "docs/index.html").write_text(page(cells, skills, meta))
    (ROOT / "evals/results/summary.json").write_text(json.dumps(
        {"meta": meta, "made_up": rows, "paired": paired_rows(cells, skills), "prefs": pref_rows(cells, skills),
         "omitted": omit_rows(cells, skills)}, indent=2))
    print("wrote assets/arena.svg, docs/index.html and evals/results/summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
