#!/usr/bin/env python3
"""Statistics for the arena results, with no dependencies.

Every comparison is paired: the same task, the same model, two skills. Tasks
are the unit of resampling, because the write and rewrite forms of one task,
and its repetitions, are not independent of each other.

- Means come with 95% intervals from a cluster bootstrap over tasks.
- Brogue against each rival: the mean per-task difference, its bootstrap
  interval, and a two-sided sign-flip permutation p-value.
- Reader preference: Brogue's share of ballots with a Wilson 95% interval and
  an exact two-sided binomial p-value against a coin flip.

    python evals/stats.py evals/results/agent-agency.json evals/results/agent-heldout.json
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

B = 10_000
SEED = 20261117


def label(name: str) -> str:
    return {"plain": "no skill", "brogue": "Brogue"}.get(name, name)


def by_task(cells: list[dict], value) -> dict[str, list[float]]:
    """Group a per-cell value by task; cells where it is undefined are skipped."""
    groups: dict[str, list[float]] = {}
    for c in cells:
        v = value(c)
        if v is not None:
            groups.setdefault(f"{c.get('set', '')}/{c['task']}", []).append(v)
    return groups


def cluster_mean(groups: dict[str, list[float]]) -> float:
    values = [v for vs in groups.values() for v in vs]
    return sum(values) / len(values)


def bootstrap(groups: dict[str, list[float]], rng: random.Random) -> tuple[float, float]:
    keys = list(groups)
    stats = []
    for _ in range(B):
        values = [v for k in rng.choices(keys, k=len(keys)) for v in groups[k]]
        stats.append(sum(values) / len(values))
    stats.sort()
    return stats[int(0.025 * B)], stats[int(0.975 * B) - 1]


def sign_flip_p(groups: dict[str, list[float]], rng: random.Random) -> float:
    """Two-sided permutation p-value for a mean paired difference of zero, flipping whole tasks."""
    sums = [sum(vs) for vs in groups.values()]
    n = sum(len(vs) for vs in groups.values())
    observed = abs(sum(sums)) / n
    hits = sum(abs(sum(s if rng.random() < 0.5 else -s for s in sums)) / n >= observed - 1e-12 for _ in range(B))
    return (hits + 1) / (B + 1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return 0.0, 1.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def binomial_p(k: int, n: int) -> float:
    """Exact two-sided binomial test against p = 0.5."""
    probs = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(q for q in probs if q <= probs[k] + 1e-15))


def load(paths: list[Path]) -> tuple[list[dict], list[str]]:
    cells, skills = [], None
    for path in paths:
        result = json.loads(path.read_text())
        for c in result["cells"]:
            c["set"] = result.get("set", path.stem)
            cells.append(c)
        skills = [s for s in result["skills"] if skills is None or s in skills]
    return cells, skills


def report(paths: list[Path]) -> str:
    cells, skills = load(paths)
    rng = random.Random(SEED)
    made_up = lambda name: (lambda c: len(c["unsupported"][name]) if c.get("unsupported", {}).get(name) is not None else None)
    left_out = lambda name: (lambda c: len(c["omitted"][name]) if c.get("omitted", {}).get(name) is not None else None)
    tasks = len({f"{c['set']}/{c['task']}" for c in cells})
    out = [f"{len(cells)} texts per skill from {tasks} tasks ({', '.join(sorted({c['set'] for c in cells}))}). "
           f"95% intervals from {B:,} bootstrap resamples of tasks.", ""]

    out += ["### Made-up details per text", "", "| Skill | Mean | 95% interval | Texts with none |", "|---|---|---|---|"]
    rows = []
    for name in skills:
        groups = by_task(cells, made_up(name))
        if not groups:
            continue
        values = [v for vs in groups.values() for v in vs]
        rows.append((cluster_mean(groups), name, bootstrap(groups, rng), sum(v == 0 for v in values), len(values)))
    for mean, name, (lo, hi), clean, total in sorted(rows):
        bold = "**" if name == "brogue" else ""
        out.append(f"| {bold}{label(name)}{bold} | {bold}{mean:.2f}{bold} | {lo:.2f} to {hi:.2f} | {clean} of {total} |")

    out += ["", "### Brogue minus each other skill, paired by task (negative means Brogue made up less)", "",
            "| Against | Difference | 95% interval | p | Tasks where Brogue made up less / same / more |", "|---|---|---|---|---|"]
    for name in [n for n in skills if n != "brogue"]:
        def diff(c, name=name):
            a, b = made_up("brogue")(c), made_up(name)(c)
            return None if a is None or b is None else a - b
        groups = by_task(cells, diff)
        if not groups:
            continue
        per_task = [sum(vs) / len(vs) for vs in groups.values()]
        lo, hi = bootstrap(groups, rng)
        out.append(f"| {label(name)} | {cluster_mean(groups):+.2f} | {lo:+.2f} to {hi:+.2f} | {sign_flip_p(groups, rng):.4f} | "
                   f"{sum(d < 0 for d in per_task)} / {sum(d == 0 for d in per_task)} / {sum(d > 0 for d in per_task)} |")

    if any(c.get("omitted") for c in cells):
        out += ["", "### Supplied facts left out per text (texts written from a brief)", "",
                "| Skill | Mean | 95% interval | Texts missing something |", "|---|---|---|---|"]
        rows = []
        for name in skills:
            groups = by_task([c for c in cells if c["kind"] == "write"], left_out(name))
            if groups:
                values = [v for vs in groups.values() for v in vs]
                rows.append((cluster_mean(groups), name, bootstrap(groups, rng), sum(v > 0 for v in values), len(values)))
        for mean, name, (lo, hi), missing, total in sorted(rows):
            out.append(f"| {label(name)} | {mean:.2f} | {lo:.2f} to {hi:.2f} | {missing} of {total} |")

    retest = [(len(c["unsupported"][n]), len(c["retest"][n])) for c in cells for n in c.get("retest", {})
              if c["retest"][n] is not None and c.get("unsupported", {}).get(n) is not None]
    if retest:
        diffs = [abs(a - b) for a, b in retest]
        agree = sum((a == 0) == (b == 0) for a, b in retest)
        out += ["", "### The auditor's own noise", "",
                f"{len(retest)} texts audited a second time, independently. The two counts differ by "
                f"{sum(diffs) / len(diffs):.2f} per text on average; they agree on whether a text has any made-up "
                f"detail in {agree} of {len(retest)} ({agree / len(retest):.0%})."]
        for name in sorted({n for c in cells for n in c.get("retest", {})}):
            pairs = [(len(c["unsupported"][name]), len(c["retest"][name])) for c in cells
                     if c.get("retest", {}).get(name) is not None and c.get("unsupported", {}).get(name) is not None]
            out.append(f"- {label(name)}: first audit {sum(a for a, _ in pairs) / len(pairs):.2f}, "
                       f"second audit {sum(b for _, b in pairs) / len(pairs):.2f} per text")

    ballots = [(r, b) for c in cells for r, bs in c.get("ballots", {}).items() for b in bs]
    if ballots:
        out += ["", "### Blind reader preference, Brogue against each", "",
                "| Against | Brogue won | Share | 95% interval | p against a coin flip |", "|---|---|---|---|---|"]
        for name in [n for n in skills if n != "brogue"] + [None]:
            votes = [b for r, b in ballots if name in (None, r)]
            if not votes:
                continue
            k, n = sum(b["brogue_won"] for b in votes), len(votes)
            lo, hi = wilson(k, n)
            who = "all skills together" if name is None else label(name)
            out.append(f"| {who} | {k} of {n} | {k / n:.0%} | {lo:.0%} to {hi:.0%} | {binomial_p(k, n):.3f} |")
    return "\n".join(out)


if __name__ == "__main__":
    print(report([Path(p) for p in sys.argv[1:]]))
