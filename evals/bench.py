#!/usr/bin/env python3
"""Benchmark: does Brogue change what a model writes, and do readers prefer it?

Three arms per writing task, each written by the `--writer` model:

  plain      a bare "helpful writing assistant" system prompt
  steered    the same, with `brogue.steer(persona)` prepended (prevention)
  rewritten  the plain output passed through `brogue.humanize` (interception)

Two measurements:

  lint score  Brogue's own linter. Circular by construction: it shows the arms
              move the patterns Brogue counts, nothing more.
  panel       The `--judge` model plays the task's target reader and compares
              each treated output against its plain twin, blind, in both
              orders. This is the measure that is independent of the linter.

Needs no API key when a `claude` CLI is installed:

    python evals/bench.py --writer haiku --judge sonnet --reps 3 --out evals/results/bench.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from brogue import fact_guard, humanize, lint, load_persona, steer
from brogue.llm import connect
from brogue.panel import PanelReport, _ask

PLAIN = "You are a helpful writing assistant."

TASKS = [
    ("linkedin-launch", "casual-us", "A LinkedIn post from a founder you follow.",
     "Write a LinkedIn post announcing that our startup's scheduling app now syncs with Outlook. "
     "It took 4 months. Two engineers built it."),
    ("exec-update", "corporate-us", "A status update from someone on your team.",
     "Write a short update to our VP: the data migration finished Friday, two days late, "
     "because of a schema mismatch in the billing tables. No data was lost."),
    ("formal-request", "corporate-in", "An email from a vendor you work with.",
     "Write an email to a senior client in Mumbai asking to move Thursday's review meeting to the "
     "following Monday because our lead analyst is unwell."),
    ("support-reply", "support-empathetic", "You were charged twice and complained. This is the reply.",
     "A customer was charged twice for an annual plan and is angry. Write the reply. "
     "The refund was issued today and takes 5 to 7 business days."),
    ("blog-intro", "neutral", "The opening of a blog post you clicked on.",
     "Write the opening two paragraphs of a blog post about why small teams should write "
     "design docs before coding."),
    ("uk-proposal", "corporate-uk", "A paragraph in a proposal you are reviewing for the council.",
     "Write a paragraph for a proposal to a UK council explaining that our recycling pilot "
     "raised collection rates from 41% to 48% across 3 wards in 6 months."),
    ("product-desc", "casual-us", "A product description on a shop page.",
     "Write a product description for a 1-litre insulated water bottle that keeps drinks "
     "cold for 24 hours and fits a car cup holder."),
    ("eng-answer", "technical-terse", "A teammate's answer in your team channel.",
     "Explain to a teammate why our nightly job failed: the S3 bucket policy was changed and the "
     "job's role lost s3:PutObject. Say what to do about it."),
]


def run(writer_model: str, judge_model: str, reps: int, provider: str, workers: int) -> dict:
    writer = connect(provider, writer_model)
    judge = connect(provider, judge_model)
    cells = [(task, rep) for task in TASKS for rep in range(reps)]

    def write(cell):
        (name, persona_name, context, prompt), rep = cell
        persona = load_persona(persona_name)
        plain = writer(PLAIN, prompt)
        steered = writer(steer(persona) + "\n\n" + PLAIN, prompt)
        result = humanize(plain, persona, writer)
        row = {"task": name, "persona": persona_name, "rep": rep,
               "plain": plain, "steered": steered, "rewritten": result.text,
               "rewrite_changed": result.changed, "rewrite_route": result.route,
               "rewrite_calls": result.passes, "rewrite_warnings": result.warnings,
               "rewrite_facts_ok": fact_guard(plain, result.text).ok}
        for arm in ("plain", "steered", "rewritten"):
            report = lint(row[arm])
            row[f"{arm}_score"], row[f"{arm}_words"] = report.score, report.words
        ballots = {}
        for arm in ("steered", "rewritten"):
            if row[arm] == plain:
                ballots[arm] = []
                continue
            votes = [_ask(persona, context, plain, row[arm], slot, judge) for slot in ("A", "B")]
            ballots[arm] = [vars(v) | {"for_treated": v.for_humanized} for v in votes if v]
        row["ballots"] = ballots
        return row

    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(write, cells))
    return {"writer": writer_model, "judge": judge_model, "reps": reps, "rows": rows}


def _panel(rows: list[dict], arm: str) -> tuple[int, int, float, float, float]:
    votes = [b for r in rows for b in r["ballots"][arm]]
    if not votes:
        return 0, 0, 0.5, 0.0, 0.0
    wins = sum(b["for_treated"] for b in votes)
    bias = sum(b["choice"] == "A" for b in votes) / len(votes)
    return (wins, len(votes), bias, statistics.mean(b["human_delta"] for b in votes),
            statistics.mean(b["fit_delta"] for b in votes))


def summarize(result: dict) -> str:
    rows = result["rows"]
    out = [f"Writer `{result['writer']}`, judge `{result['judge']}`, {result['reps']} rep(s) per task, "
           f"{len(rows)} cells.", "",
           "### Lint score (0 is clean; Brogue's own linter)", "",
           "| Task | Reader | Plain | Steered | Rewritten |", "|---|---|---|---|---|"]

    def mean(key: str, task: str | None = None) -> float:
        return statistics.mean(r[key] for r in rows if task in (None, r["task"]))

    for name, persona, _, _ in TASKS:
        out.append(f"| {name} | {persona} | {mean('plain_score', name):.0f} | "
                   f"{mean('steered_score', name):.0f} | {mean('rewritten_score', name):.0f} |")
    out.append(f"| **mean** | | **{mean('plain_score'):.0f}** | **{mean('steered_score'):.0f}** | "
               f"**{mean('rewritten_score'):.0f}** |")
    out.append(f"| mean words | | {mean('plain_words'):.0f} | {mean('steered_words'):.0f} | "
               f"{mean('rewritten_words'):.0f} |")

    out += ["", "### Blind reader preference against the plain output", "",
            "| Arm | Ballots won | Win rate | Sounds human | Fits me | Chose slot A |", "|---|---|---|---|---|---|"]
    for arm in ("steered", "rewritten"):
        wins, total, bias, human, fit = _panel(rows, arm)
        rate = f"{wins / total:.0%}" if total else "n/a"
        out.append(f"| {arm} | {wins}/{total} | {rate} | {human:+.1f} | {fit:+.1f} | {bias:.0%} |")

    out += ["", "### Per task, ballots won by the treated version", "",
            "| Task | Steered | Rewritten |", "|---|---|---|"]
    for name, _, _, _ in TASKS:
        mine = [r for r in rows if r["task"] == name]
        cells = []
        for arm in ("steered", "rewritten"):
            wins, total, *_ = _panel(mine, arm)
            cells.append(f"{wins}/{total}" if total else "unchanged")
        out.append(f"| {name} | {cells[0]} | {cells[1]} |")

    changed = sum(r["rewrite_changed"] for r in rows)
    passed = sum(r["rewrite_route"] == "pass" for r in rows)
    refused = len(rows) - changed - passed
    facts = sum(r["rewrite_facts_ok"] for r in rows)
    calls = sum(r["rewrite_calls"] for r in rows)
    out += ["", "### Pipeline behaviour", "",
            f"- {passed}/{len(rows)} plain outputs were already clean and passed through with no model call.",
            f"- {changed}/{len(rows)} were rewritten and accepted; {refused} were refused by verification "
            "and returned unchanged.",
            f"- {facts}/{len(rows)} final texts keep every number, link and quote of the plain output.",
            f"- {calls} rewrite calls in total."]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--writer", default="haiku")
    parser.add_argument("--judge", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path, help="re-summarize a saved result file")
    args = parser.parse_args()
    if args.report:
        result = json.loads(args.report.read_text())
    else:
        result = run(args.writer, args.judge, args.reps, args.provider, args.workers)
        if args.out:
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(summarize(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
