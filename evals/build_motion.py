#!/usr/bin/env python3
"""Feed the Remotion film (motion/) from recorded results.

Picks one recorded task where the unaided model made things up and Brogue did
not, takes the benchmark rows from build_site, and writes motion/src/data.json.
Every text and number in the film comes from the result files.

    python evals/build_motion.py evals/results/agent-*.json
    cd motion && npx remotion render Brogue ../assets/brogue-film.mp4
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import stats
from arena import reader_of
from build_site import GROUNDED, REPO, made_up_rows

ROOT = Path(__file__).resolve().parents[1]


def pick(cells: list[dict]) -> dict:
    """A written-from-a-brief task where Brogue made nothing up, every flagged quote can be shown,
    and both texts fit on screen; among those, the one with the most made-up details per word."""
    def candidate(c):
        u = c.get("unsupported", {})
        plain, text = u.get("plain") or [], c["outputs"].get("plain", "")
        return (c["kind"] == "write" and u.get("brogue") == [] and len(plain) >= 3
                and all(q in text for q in plain) and len(text.split()) <= 170
                and len(c["outputs"]["brogue"].split()) <= 110 and len(c["source"]) <= 480)
    pool = [c for c in cells if candidate(c)]
    if not pool:
        raise SystemExit("no recorded task fits the film; loosen the limits in pick()")
    return max(pool, key=lambda c: len(c["unsupported"]["plain"]) / len(c["outputs"]["plain"].split()))


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]]
    cells, skills = stats.load(paths)
    skills = [s for s in skills if s != GROUNDED and "@" not in s]
    cell = pick(cells)
    rows = made_up_rows(cells, skills)
    ours = next(r for r in rows if r["ours"])
    rival = next(r for r in rows if not r["ours"] and r["key"] != "plain")
    data = {
        "request": cell["source"], "reader": reader_of(cell["persona"]),
        "plain": {"text": cell["outputs"]["plain"].replace("**", ""), "made_up": [q.replace("**", "") for q in cell["unsupported"]["plain"]]},
        "brogue": {"text": cell["outputs"]["brogue"].replace("**", "")},
        "rows": [{k: r[k] for k in ("name", "mean", "lo", "hi", "ours")} for r in rows],
        "texts": len(cells), "tasks": len({f"{c['set']}/{c['task']}" for c in cells}),
        "headline": "Writing that says only what you told it.",
        "sub": f"Brogue: {ours['mean']:.2f} made-up details per text. Next best skill: {rival['mean']:.2f}.",
        "install": f"npx skills add {REPO}",
    }
    (ROOT / "motion/src/data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"wrote motion/src/data.json from {cell['set']}/{cell['task']} ({len(data['plain']['made_up'])} made up)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
