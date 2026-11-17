#!/usr/bin/env python3
"""Agent arena: every skill installed the way people install it, in a real agent session.

`arena.py` pastes each SKILL.md into a system prompt and asks for one reply. That
is how a skill behaves in an API call. Most people use skills inside an agent,
where the skill loads on demand, can read its own reference files and can run
its own scripts. This harness tests that.

For each task and each skill, a fresh Claude Code session runs headless with:

- a clean config directory, so no globally installed skill or plugin leaks in;
- only the skill under test, loaded as a plugin from its full folder
  (SKILL.md, references, scripts), exactly as published;
- the same tools for every arm (Bash, Read, Write, Edit, Glob, Grep, Skill);
- the same user message, prefixed with "Use the <name> skill." for skill arms.

The final reply is recorded as that arm's text. Texts are checkpointed after
every session, so an interrupted run resumes where it stopped. Duels and
audits then reuse arena.py and fidelity.py on the result file.

    python evals/agent_arena.py --skills-dir fullskills --tasks evals/data/tasks-agency.json \
        --out evals/results/agent-agency.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from arena import cells, reader_of
from bench import TASKS
from brogue.llm import LLMError, connect
from brogue.panel import _ask
from rejudge import Bare
from tasks_heldout import HELDOUT

ROOT = Path(__file__).resolve().parents[1]
TOOLS = "Bash,Read,Write,Edit,Glob,Grep,Skill"
_lock = threading.Lock()


def skill_name(folder: Path) -> str:
    match = re.search(r"^name:\s*(\S+)", (folder / "SKILL.md").read_text(), re.M)
    return match.group(1) if match else folder.name


def session(prompt: str, folder: Path | None, model: str, timeout: int = 420) -> dict:
    """One headless agent session. Returns the reply and the tools it used."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        config, work = tmp / "config", tmp / "work"
        config.mkdir(), work.mkdir()
        creds = Path.home() / ".claude/.credentials.json"
        if creds.exists():
            (config / ".credentials.json").symlink_to(creds)
        command = ["claude", "-p", "--model", model, "--allowedTools", TOOLS, "--no-session-persistence",
                   "--output-format", "stream-json", "--verbose"]
        if folder is not None:
            plugin = tmp / "plugin"
            (plugin / ".claude-plugin").mkdir(parents=True)
            (plugin / ".claude-plugin/plugin.json").write_text('{"name": "under-test", "version": "0.0.0"}')
            shutil.copytree(folder, plugin / "skills" / folder.name)
            command += ["--plugin-dir", str(plugin)]
            prompt = f"Use the {skill_name(folder)} skill.\n\n{prompt}"
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SYNC_PLUGINS", "CLAUDE_CODE_SYNC_SKILLS")}
        env["CLAUDE_CONFIG_DIR"] = str(config)
        try:
            out = subprocess.run(command + [prompt], cwd=work, env=env, capture_output=True, text=True,
                                 timeout=timeout).stdout
        except subprocess.TimeoutExpired:
            return {"text": None, "tools": [], "error": "timeout"}
    tools, text, loaded = [], None, []
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            loaded = [s for s in event.get("skills", []) if s.startswith("under-test:")]
        if event.get("type") == "assistant":
            for part in event["message"].get("content", []):
                if part.get("type") == "tool_use":
                    detail = part["input"].get("command") or part["input"].get("skill") or part["input"].get("file_path") or ""
                    tools.append(f"{part['name']}: {str(detail)[:4000]}")
        if event.get("type") == "result" and not event.get("is_error"):
            text = (event.get("result") or "").strip() or None
    return {"text": text, "tools": tools, "loaded": loaded}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skills-dir", type=Path, required=True, help="one full skill folder per rival")
    parser.add_argument("--tasks", type=Path, help="task file from make_tasks.py")
    parser.add_argument("--set", choices=("dev", "heldout"), default="dev")
    parser.add_argument("--drafts", type=Path, default=ROOT / "evals/data/drafts.json")
    parser.add_argument("--writer", default="haiku")
    parser.add_argument("--judge", default="sonnet")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--arms", help="comma-separated arms (default: plain, brogue and every rival)")
    parser.add_argument("--no-duels", action="store_true")
    parser.add_argument("--rivals", help="comma-separated arms Brogue is duelled against (default: all)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    folders: dict[str, Path | None] = {"plain": None, "brogue": ROOT / "skills/brogue"}
    folders |= {f.name: f for f in sorted(args.skills_dir.iterdir()) if (f / "SKILL.md").exists()}
    if args.arms:
        folders = {n: folders[n] for n in args.arms.split(",")}
    if args.tasks:
        spec = json.loads(args.tasks.read_text())
        tasks = [(t["name"], t["reader"], t["context"], t["brief"]) for t in spec["tasks"]]
        drafts = {t["name"]: t["draft"] for t in spec["tasks"]}
    else:
        tasks, drafts = (TASKS if args.set == "dev" else HELDOUT), json.loads(args.drafts.read_text())

    if args.out.exists():  # resume
        result = json.loads(args.out.read_text())
        grid = result["cells"]
    else:
        grid = cells(drafts, args.reps, tasks)
        for c in grid:
            c["outputs"], c["tools"], c["ballots"] = {}, {}, {}
        result = {"mode": "agent", "writer": args.writer, "judge": args.judge, "reps": args.reps,
                  "set": args.tasks.stem if args.tasks else args.set, "cells": grid}
    result["skills"] = list(dict.fromkeys([*result.get("skills", []), *folders]))

    def save():
        with _lock:
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    jobs = [(i, n) for i in range(len(grid)) for n in folders if not grid[i]["outputs"].get(n)]
    print(f"{len(jobs)} sessions to run", file=sys.stderr)

    def work(job):
        i, name = job
        got = session(grid[i]["user"], folders[name], args.writer)
        if got["text"]:
            with _lock:
                grid[i]["outputs"][name], grid[i]["tools"][name] = got["text"], got["tools"]
            save()
        return got

    with ThreadPoolExecutor(args.workers) as pool:
        failed = sum(not g["text"] for g in pool.map(work, jobs))
    print(f"{failed} sessions failed", file=sys.stderr)

    if not args.no_duels:
        judge = connect(args.provider, args.judge)
        rivals = [n for n in result["skills"] if n != "brogue" and (not args.rivals or n in args.rivals.split(","))]
        duels = [(i, r, "AB"[(i + k) % 2]) for i, c in enumerate(grid) for k, r in enumerate(rivals)
                 if c["outputs"].get(r) and c["outputs"].get("brogue") and r not in c["ballots"]]

        def duel(job):  # each ballot is saved as it arrives, so a refused call loses nothing else
            i, rival, slot = job
            c = grid[i]
            try:
                ballot = _ask(Bare("reader", reader_of(c["persona"])), c["context"], c["outputs"][rival],
                              c["outputs"]["brogue"], slot, judge)
            except LLMError as err:
                print(f"skipped duel {c['task']}/{rival}: {str(err)[:120]}", file=sys.stderr)
                return
            if ballot:
                with _lock:
                    c["ballots"].setdefault(rival, []).append(
                        {"brogue_won": ballot.for_humanized, "choice": ballot.choice, "why": ballot.why})
                save()

        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(duel, duels))
        save()
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
