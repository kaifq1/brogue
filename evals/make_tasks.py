#!/usr/bin/env python3
"""Write a fresh, unseen task set from real job roles.

Tasks written by the skill's author can favour the skill without meaning to.
Here a model writes them instead, from role files in agency-agents
(github.com/msitarzewski/agency-agents, MIT), picked at random with a fixed
seed, one role per division. The prompt says nothing about Brogue or about
invented details. Each task has a writer's role, a reader, a short brief with
the facts the writer knows, and a first draft in the usual padded assistant
style for the rewrite form.

    git clone --depth 1 https://github.com/msitarzewski/agency-agents
    python evals/make_tasks.py agency-agents --n 12 --seed 7 --out evals/data/tasks-agency.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from brogue.llm import connect

SYSTEM = """You design realistic workplace writing tasks for a benchmark of writing assistants.

You are given one professional role. Invent one ordinary message this professional would need to write
at work this week. Reply with one JSON object and nothing else:

{"reader": "one sentence: who reads the message and their relationship to the writer",
 "context": "one sentence: where the reader meets the message, written to the reader as 'you'",
 "brief": "the request the professional types to an assistant: what to write, plus 3 to 5 concrete facts
           (numbers, dates, names, decisions) and nothing else the message should rely on",
 "draft": "a first draft of that message in the padded style of a generic AI assistant: a run-up,
           filler, a tidy closing line. It may restate the brief's facts but adds no new facts."}

The brief is one to three sentences, written the way a busy person types a request."""


def roles(root: Path, n: int, seed: int, skip: set[str] = frozenset()) -> list[Path]:
    divisions = sorted(d for d in root.iterdir() if d.is_dir() and list(d.glob("*.md")) and not d.name.startswith("."))
    rng = random.Random(seed)
    rng.shuffle(divisions)
    picked = []
    for d in divisions * 3:  # round-robin over divisions until n new roles are found
        options = [f for f in sorted(d.glob("*.md")) if f.stem not in skip and f not in picked
                   and not f.stem.isupper()]  # skip README, QUICKSTART and other non-role files
        if options and len(picked) < n:
            picked.append(rng.choice(options))
    return picked


def profile(path: Path) -> str:
    head = path.read_text(encoding="utf-8")[:1500]
    name = re.search(r"^name:\s*(.+)$", head, re.M)
    desc = re.search(r"^description:\s*(.+)$", head, re.M)
    return f"{name.group(1) if name else path.stem}: {desc.group(1) if desc else ''}".strip()


def make(model, path: Path) -> dict | None:
    raw = model(SYSTEM, f"Role: {profile(path)}")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        task = json.loads(match.group(0))
        assert all(task.get(k) for k in ("reader", "context", "brief", "draft"))
    except (AttributeError, AssertionError, ValueError):
        return None
    return {"name": path.stem, "role": profile(path), **{k: task[k].strip() for k in ("reader", "context", "brief", "draft")}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("agency", type=Path, help="a checkout of msitarzewski/agency-agents")
    parser.add_argument("--n", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--exclude", type=Path, nargs="*", default=[], help="earlier task files whose roles to skip")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    model = connect(args.provider, args.model)
    skip = {t["name"] for f in args.exclude for t in json.loads(f.read_text())["tasks"]}
    picked = roles(args.agency, args.n, args.seed, skip)
    with ThreadPoolExecutor(6) as pool:
        tasks = [t for t in pool.map(lambda p: make(model, p), picked) if t]
    args.out.write_text(json.dumps({"source": "msitarzewski/agency-agents", "seed": args.seed,
                                    "model": args.model, "tasks": tasks}, indent=2, ensure_ascii=False))
    print(f"wrote {len(tasks)} tasks to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
