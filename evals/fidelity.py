#!/usr/bin/env python3
"""Fidelity: how much does each skill make up?

A blind reader cannot know what the writer was told, so a reader panel rewards
text that sounds specific whether or not the specifics are true. This script
measures the other half. A judge model sees the input (the brief, or the draft
being rewritten) next to each output and lists every specific the output states
as fact that the input does not support.

    python evals/fidelity.py evals/results/arena-haiku-sonnet.json --judge sonnet
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from brogue.llm import LLMError, connect

SYSTEM_V1 = """You audit a piece of writing against the only information its writer was given.

List every specific that the OUTPUT states as fact and the INPUT does not contain or directly imply:
names of people, products or tools; numbers, dates and durations; events that happened; features;
causes; commitments and promises; quotes; results.

Do not list: bracketed placeholders such as [Name] or [date]; greetings, thanks, apologies and other
courtesy; opinions clearly marked as the writer's own; generic advice; restatements of the input in
other words; an offer to talk or answer questions.

Reply with one JSON object and nothing else: {"unsupported": ["short quote", ...]}
Use an empty list when the output adds nothing."""

# v2 also stops counting what the writer derived correctly from the input. v1 counted
# "net cost about $110K" (the difference of two supplied figures) as made up, which
# rewarded a writer for withholding the conclusion a reader needs.
SYSTEM = SYSTEM_V1.replace(
    "an offer to talk or answer questions.",
    "an offer to talk or answer questions; arithmetic or logic correctly worked out from the input (a total, a "
    "difference, a percentage, the weekday of a given date, a consequence that follows directly); an explanation of "
    "what an input fact means that is true in general and not a claim about this writer's situation.")
assert SYSTEM != SYSTEM_V1


OMITTED = """You check whether a piece of writing used the information its writer was given.

INPUT is a request to write something. List every fact INPUT supplies that OUTPUT leaves out or
changes: a number, a duration, a name, an event, a condition, an instruction to include something.

Do not list: the instruction to write itself; the description of the reader; a fact that OUTPUT
states in other words or in another unit.

Reply with one JSON object and nothing else: {"unsupported": ["short quote from INPUT", ...]}
Use an empty list when nothing is missing."""


def audit(judge, source: str, output: str, system: str = SYSTEM) -> list[str] | None:
    raw = judge(system, f"<input>\n{source}\n</input>\n\n<output>\n{output}\n</output>")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        return [str(x) for x in json.loads(match.group(0))["unsupported"]]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def summarize(result: dict) -> str:
    out = ["| Skill | Unsupported specifics per text | Texts with none | Texts audited |", "|---|---|---|---|"]
    rows = []
    for name in result["skills"]:
        counts = [len(c["unsupported"][name]) for c in result["cells"] if c.get("unsupported", {}).get(name) is not None]
        if not counts:
            continue
        rows.append((statistics.mean(counts), name, sum(n == 0 for n in counts), len(counts)))
    for mean, name, clean, total in sorted(rows):
        out.append(f"| {name} | {mean:.2f} | {clean}/{total} | {total} |")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("result", type=Path)
    parser.add_argument("--judge", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--only", help="audit just this skill and keep earlier audits of the others")
    parser.add_argument("--omissions", action="store_true",
                        help="audit the other direction on briefs: supplied facts the text left out")
    parser.add_argument("--field", default="unsupported",
                        help="where to store the audit; a second field (e.g. retest) measures the auditor's own noise")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    if not args.report:
        field, system = ("omitted", OMITTED) if args.omissions else (args.field, SYSTEM)
        judge = connect(args.provider, args.judge)
        jobs = [(c, name) for c in result["cells"] if not args.omissions or c["kind"] == "write"
                for name in result["skills"]
                if (args.only is None or name in args.only.split(",")) and c["outputs"].get(name)
                and c.get(field, {}).get(name) is None]  # resume: skip what an earlier run already audited
        lock, done = threading.Lock(), [0]

        def work(job):
            cell, name = job
            try:
                items = audit(judge, cell["source"], cell["outputs"][name], system)
            except LLMError as err:  # a refused or failed call leaves the text unaudited for the next run
                print(f"skipped {cell['task']}/{name}: {str(err)[:120]}", file=sys.stderr)
                return
            with lock:
                cell.setdefault(field, {})[name] = items
                done[0] += 1
                if done[0] % 25 == 0:
                    args.result.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(work, jobs))
        result["fidelity_judge"] = args.judge
        result["fidelity_auditor"] = "v2"
        args.result.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"audited {done[0]} of {len(jobs)} texts", file=sys.stderr)
    if args.omissions:
        print("| Skill | Supplied facts left out, per text | Texts missing something |\n|---|---|---|")
        for name in result["skills"]:
            counts = [len(c["omitted"][name]) for c in result["cells"] if c.get("omitted", {}).get(name) is not None]
            if counts:
                print(f"| {name} | {statistics.mean(counts):.2f} | {sum(n > 0 for n in counts)}/{len(counts)} |")
        return 0
    print(summarize(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
