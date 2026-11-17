#!/usr/bin/env python3
"""Control for the benchmark: judge again with readers who were not told the style rules.

In bench.py the juror's brief contains the same conventions that steered the
writer, so a win could mean "the juror was told to like this". Here the juror
knows only who they are (one sentence) and the situation. If the preference
survives, it does not come from the shared brief.

    python evals/rejudge.py evals/results/bench-haiku-sonnet.json --judge sonnet
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench import TASKS, _panel
from brogue import load_persona
from brogue.llm import connect
from brogue.panel import _ask


class Bare:
    """A reader described by one sentence, with no register or convention rules."""

    def __init__(self, name: str, summary: str):
        self.name, self.summary = name, summary

    def brief(self) -> str:
        return f"Reader: {self.summary}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("result", type=Path)
    parser.add_argument("--judge", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.result.read_text())
    judge = connect(args.provider, args.judge)
    context = {name: ctx for name, _, ctx, _ in TASKS}

    def vote(job):
        row, arm, slot = job
        reader = Bare(row["persona"], load_persona(row["persona"]).summary)
        ballot = _ask(reader, context[row["task"]], row["plain"], row[arm], slot, judge)
        return row, arm, ballot

    jobs = [(r, arm, slot) for r in data["rows"] for arm in ("steered", "rewritten")
            if r[arm] != r["plain"] for slot in ("A", "B")]
    for row in data["rows"]:
        row["ballots"] = {"steered": [], "rewritten": []}
    with ThreadPoolExecutor(6) as pool:
        for row, arm, ballot in pool.map(vote, jobs):
            if ballot:
                row["ballots"][arm].append(vars(ballot) | {"for_treated": ballot.for_humanized})
    print(f"Judge `{args.judge}` told only who the reader is. Writer `{data['writer']}`.\n")
    print("| Arm | Ballots won | Win rate | Sounds human | Fits me | Chose slot A |\n|---|---|---|---|---|---|")
    for arm in ("steered", "rewritten"):
        wins, total, bias, human, fit = _panel(data["rows"], arm)
        print(f"| {arm} | {wins}/{total} | {wins / total:.0%} | {human:+.1f} | {fit:+.1f} | {bias:.0%} |")
    if args.out:
        args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
