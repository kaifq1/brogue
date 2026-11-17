#!/usr/bin/env python3
"""Arena: Brogue against other writing skills, same model, same tasks, blind reader.

Each skill's SKILL.md becomes the system prompt of the same writer model. Every
arm gets the identical user message, which names the reader in one sentence.
Two kinds of task:

  write    8 briefs (see bench.py), written from scratch
  rewrite  8 machine-sounding drafts, rewritten for a named reader

A second model then plays that reader, knowing only who they are, and compares
Brogue's text with each other skill's text, blind, in both orders.

Alongside preference, three mechanical measures per skill: lint score, length,
and how often the output contains a number that was not in the input.

    python evals/arena.py --skills-dir path/to/skills --writer haiku --judge sonnet

`--skills-dir` holds one folder per competitor with a SKILL.md inside. Skills
are not redistributed here; clone them from their own repositories.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench import TASKS
from tasks_heldout import HELDOUT
from brogue import lint, load_persona, presets
from brogue.guard import facts
from brogue.ground import ground
from brogue.llm import connect
from brogue.panel import _ask
from rejudge import Bare

ROOT = Path(__file__).resolve().parents[1]
ONLY_TEXT = "Reply with only the finished text: no preamble, no notes, no list of changes."
PLAIN = "You are a helpful writing assistant."
GROUNDED = "brogue+ground"
REVIEWED = "@review"
REVIEW = ("Before this goes out, review your draft against my request, following the loaded skill's "
          "instructions for checking and revising, if it has any. Reply with only the final text: "
          "no preamble, no notes, no list of changes.")


def review_user(cell: dict, draft: str) -> str:
    """The second turn every arm gets: same request, its own draft, the same instruction to review it."""
    return f"{cell['user']}\n\n<your_draft>\n{draft}\n</your_draft>\n\n{REVIEW}"


def reader_of(persona: str) -> str:
    """A preset name, or a reader described in words (task files written from agency-agents roles)."""
    return load_persona(persona).summary if persona in presets() else persona


def system_for(skill_text: str | None) -> str:
    if skill_text is None:
        return PLAIN
    return "The following skill is loaded. Apply it to the user's request.\n\n" + skill_text


def cells(drafts: dict[str, str], reps: int, tasks=TASKS) -> list[dict]:
    out = []
    for name, persona, context, brief in tasks:
        reader = reader_of(persona)
        for rep in range(reps):
            out.append({"kind": "write", "task": name, "persona": persona, "context": context, "rep": rep,
                        "source": brief, "user": f"{brief}\n\nThe reader: {reader}\n\n{ONLY_TEXT}"})
            out.append({"kind": "rewrite", "task": name, "persona": persona, "context": context, "rep": rep,
                        "source": drafts[name],
                        "user": "Rewrite this draft so it reads like a person wrote it, for this reader: "
                                f"{reader}\n\n{ONLY_TEXT}\n\n<draft>\n{drafts[name]}\n</draft>"})
    return out


def invented_numbers(source: str, output: str) -> list[str]:
    return sorted(facts(output)["number"] - facts(source)["number"])


def run(skills: dict[str, str | None], drafts: dict[str, str], writer_model: str, judge_model: str,
        reps: int, provider: str, workers: int, tasks=TASKS, reuse: dict | None = None,
        checkpoint: Path | None = None, grounded: bool = False, duels_on: bool = True,
        champion: str = "brogue", orders: int = 2, review: bool = False) -> dict:
    writer, judge = connect(provider, writer_model), connect(provider, judge_model)
    grid = cells(drafts, reps, tasks)
    jobs = [(i, name) for i in range(len(grid)) for name in skills]
    kept = {}
    if reuse:  # keep every rival's recorded text; write only Brogue again
        kept = {(i, n): t for i, c in enumerate(reuse["cells"]) for n, t in c["outputs"].items()
                if n in skills and n != "brogue"}
        jobs = [j for j in jobs if j not in kept]
    with ThreadPoolExecutor(workers) as pool:
        texts = list(pool.map(lambda j: writer(system_for(skills[j[1]]), grid[j[0]]["user"]), jobs))
    for cell in grid:
        cell["outputs"], cell["ballots"] = {}, {}
    for (i, name), text in zip(jobs, texts):
        grid[i]["outputs"][name] = text
    for (i, name), text in kept.items():
        grid[i]["outputs"][name] = text

    skills = dict(skills)
    if reuse:  # carry over reviewed texts already recorded for arms that were not rewritten
        for i, c in enumerate(reuse["cells"]):
            for n, t in c["outputs"].items():
                if n.endswith(REVIEWED) and n != "brogue" + REVIEWED:
                    grid[i]["outputs"][n] = t
    if review:  # a second turn for every arm, identical wording, so no arm gets more compute than another
        todo = [(i, n) for i in range(len(grid)) for n in list(skills) if not n.endswith(REVIEWED)
                and n != GROUNDED and n + REVIEWED not in grid[i]["outputs"]]
        with ThreadPoolExecutor(workers) as pool:
            done = list(pool.map(lambda j: writer(system_for(skills[j[1]]),
                                                  review_user(grid[j[0]], grid[j[0]]["outputs"][j[1]])), todo))
        for (i, n), text in zip(todo, done):
            grid[i]["outputs"][n + REVIEWED] = text.strip()
    for n in [n for n in list(skills) if not n.endswith(REVIEWED)]:
        if all(n + REVIEWED in c["outputs"] for c in grid):
            skills[n + REVIEWED] = skills[n]
    if grounded:  # Brogue's text after the grounding pass, run by the same writer model
        with ThreadPoolExecutor(workers) as pool:
            fixed = list(pool.map(lambda c: ground(c["user"], c["outputs"]["brogue"], writer), grid))
        for cell, g in zip(grid, fixed):
            cell["outputs"][GROUNDED] = g.text
            cell["removed"] = g.removed
        skills[GROUNDED] = None
    if checkpoint:  # the texts are the expensive part; keep them if judging is interrupted
        checkpoint.write_text(json.dumps({"skills": list(skills), "cells": grid}, indent=2, ensure_ascii=False))
    suffix = REVIEWED if champion.endswith(REVIEWED) else ""
    rivals = [n for n in skills if n != champion and n != GROUNDED
              and n.endswith(REVIEWED) == bool(suffix) and not n.startswith("brogue")]
    duels = [(i, rival, slot) for i in range(len(grid)) for rival in rivals for slot in ("A", "B")]
    if orders == 1:  # one ballot per pair, slot alternating by repetition so order still balances
        duels = [(i, rival, "AB"[(grid[i]["rep"] + k) % 2]) for i in range(len(grid)) for k, rival in enumerate(rivals)]
    if not duels_on:
        duels = []

    def duel(job):
        i, rival, slot = job
        cell = grid[i]
        reader = Bare("reader", reader_of(cell["persona"]))
        # _ask(original, humanized): "humanized" is Brogue, so for_humanized means Brogue won.
        return _ask(reader, cell["context"], cell["outputs"][rival], cell["outputs"][champion], slot, judge)

    with ThreadPoolExecutor(workers) as pool:
        ballots = list(pool.map(duel, duels))
    for (i, rival, _), ballot in zip(duels, ballots):
        if ballot:
            grid[i]["ballots"].setdefault(rival, []).append(
                {"brogue_won": ballot.for_humanized, "choice": ballot.choice, "why": ballot.why,
                 "human_delta": ballot.human_delta, "fit_delta": ballot.fit_delta})
    return {"writer": writer_model, "judge": judge_model, "reps": reps, "skills": list(skills), "cells": grid,
            "champion": champion, "review": review}


def summarize(result: dict) -> str:
    grid, skills = result["cells"], result["skills"]
    rivals = [s for s in skills if s not in ("brogue", GROUNDED)]
    out = [f"Writer `{result['writer']}`, reader `{result['judge']}`, {len(grid)} tasks "
           f"({sum(c['kind'] == 'write' for c in grid)} written from a brief, "
           f"{sum(c['kind'] == 'rewrite' for c in grid)} rewrites).", "",
           "### Brogue against each skill, blind reader preference", "",
           "| Against | Brogue wins | Win rate | Writing | Rewriting | Reader chose slot A |", "|---|---|---|---|---|---|"]

    def tally(rival: str, kind: str | None = None) -> tuple[int, int]:
        votes = [b for c in grid if kind in (None, c["kind"]) for b in c["ballots"].get(rival, [])]
        return sum(b["brogue_won"] for b in votes), len(votes)

    for rival in rivals:
        wins, total = tally(rival)
        if not total:
            continue
        w1, t1 = tally(rival, "write")
        w2, t2 = tally(rival, "rewrite")
        votes = [b for c in grid for b in c["ballots"].get(rival, [])]
        bias = sum(b["choice"] == "A" for b in votes) / len(votes) if votes else 0.5
        out.append(f"| {rival} | {wins}/{total} | {wins / total:.0%} | {w1}/{t1} | {w2}/{t2} | {bias:.0%} |")

    out += ["", "### Mechanical measures per skill", "",
            "| Skill | Mean lint score | Mean words | Outputs with an invented number | Rewrites that dropped a number |",
            "|---|---|---|---|---|"]
    for name in skills:
        scores = [lint(c["outputs"][name]).score for c in grid]
        words = [lint(c["outputs"][name]).words for c in grid]
        invented = sum(bool(invented_numbers(c["source"], c["outputs"][name])) for c in grid)
        rewrites = [c for c in grid if c["kind"] == "rewrite"]
        dropped = sum(bool(facts(c["source"])["number"] - facts(c["outputs"][name])["number"]) for c in rewrites)
        out.append(f"| {name} | {statistics.mean(scores):.1f} | {statistics.mean(words):.0f} | "
                   f"{invented}/{len(grid)} | {dropped}/{len(rewrites)} |")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skills-dir", type=Path, help="folders named after each rival, each with SKILL.md")
    parser.add_argument("--drafts", type=Path, default=ROOT / "evals/data/drafts.json")
    parser.add_argument("--writer", default="haiku")
    parser.add_argument("--judge", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--set", choices=("dev", "heldout"), default="dev",
                        help="dev: the tasks the skill was revised against; heldout: tasks never used for revision")
    parser.add_argument("--reuse", type=Path, help="earlier result: keep rivals' texts, rewrite only Brogue")
    parser.add_argument("--grounded", action="store_true", help="add an arm: Brogue's text after `brogue ground`")
    parser.add_argument("--no-duels", action="store_true", help="write the texts only; skip the reader panel")
    parser.add_argument("--review", action="store_true",
                        help="give every arm a second turn asking it to review its draft (name@review)")
    parser.add_argument("--arms", help="comma-separated arms to run, e.g. brogue (default: all)")
    parser.add_argument("--tasks", type=Path, help="JSON task file (see make_tasks.py) instead of --set")
    parser.add_argument("--orders", type=int, choices=(1, 2), default=2,
                        help="2: every pair judged in both orders; 1: once, with the order alternating")
    parser.add_argument("--champion", default="brogue", help="which Brogue arm the readers compare with rivals")
    parser.add_argument("--report", type=Path, help="re-summarize a saved result file")
    args = parser.parse_args()
    if args.report:
        result = json.loads(args.report.read_text())
    else:
        skills: dict[str, str | None] = {"plain": None,
                                         "brogue": (ROOT / "skills/brogue/SKILL.md").read_text()}
        for folder in sorted(args.skills_dir.iterdir()):
            if (folder / "SKILL.md").exists():
                skills[folder.name] = (folder / "SKILL.md").read_text()
        tasks = TASKS if args.set == "dev" else HELDOUT
        if args.tasks:
            spec = json.loads(args.tasks.read_text())
            tasks = [(t["name"], t["reader"], t["context"], t["brief"]) for t in spec["tasks"]]
            args.drafts = None
            drafts = {t["name"]: t["draft"] for t in spec["tasks"]}
        reuse = json.loads(args.reuse.read_text()) if args.reuse else None
        if reuse:
            skills = {name: skills[name] for name in reuse["skills"] if name in skills}
        if args.arms:
            skills = {n: skills[n] for n in args.arms.split(",")}
        if not args.tasks:
            drafts = json.loads(args.drafts.read_text())
        result = run(skills, drafts, args.writer, args.judge,
                     args.reps, args.provider, args.workers, tasks, reuse,
                     args.out.with_suffix(".texts.json") if args.out else None,
                     args.grounded, not args.no_duels, args.champion, args.orders, args.review)
        result["set"] = args.tasks.stem if args.tasks else args.set
        if args.out:
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(summarize(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
