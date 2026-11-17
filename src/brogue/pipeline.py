"""The middleware: lint, route, rewrite, verify.

    draft -> lint -> route --pass--> returned untouched (no model call)
                       |--edit/rewrite--> model -> fact guard + re-lint -> accept or retry

A rewrite is accepted only if it keeps every checkable fact and scores better
than what it replaces. If no attempt clears both bars, the original comes back
with a warning. Returning unimproved text is a better failure than returning
text that reads well and says something the source did not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import guard, prompts
from .lint import Report, lint
from .llm import LLM
from .persona import Persona, load, violations


@dataclass
class Result:
    text: str
    route: str  # pass | edit | rewrite
    changed: bool
    before: Report
    after: Report
    passes: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        head = f"{self.route}: score {self.before.score} -> {self.after.score}, {self.passes} model call(s)"
        return "\n".join([head, *[f"warning: {w}" for w in self.warnings]])


def _unwrap(text: str) -> str:
    """Models sometimes echo the delimiters or add a fence despite instructions."""
    text = text.strip()
    match = re.fullmatch(r"<text>\s*(.*?)\s*</text>", text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.fullmatch(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def humanize(text: str, persona: str | Persona | None = None, llm: LLM | None = None,
             max_passes: int = 2) -> Result:
    who = load(persona)
    before = lint(text)
    mismatches = violations(text, who)

    if before.route == "pass" and not mismatches:
        return Result(text, "pass", False, before, before)

    route = before.route if before.route != "pass" else "edit"
    if llm is None:
        return Result(text, route, False, before, before,
                      warnings=["needs a rewrite but no model was supplied; text returned unchanged"])

    report = before if before.route != "pass" else Report(before.words, before.score, "edit", before.findings)
    feedback = ""
    warnings: list[str] = []
    for attempt in range(1, max_passes + 1):
        system, user = prompts.rewrite(text, who, report, mismatches, feedback)
        candidate = _unwrap(llm(system, user))
        after = lint(candidate)
        facts = guard.compare(text, candidate)
        remaining = violations(candidate, who)
        better = after.score < before.score or (after.score == before.score and len(remaining) < len(mismatches))
        if facts.ok and better:
            if remaining:
                warnings.append("still off for this reader: " + "; ".join(remaining))
            return Result(candidate, route, True, before, after, attempt, warnings)
        feedback = facts.describe() if not facts.ok else (
            f"it still scores {after.score} against {before.score} before; "
            f"remaining tells: {', '.join(after.by_rule) or 'none'}")
        warnings.append(f"attempt {attempt} rejected: {feedback}")

    warnings.append("no attempt passed verification; original returned")
    return Result(text, route, False, before, before, max_passes, warnings)
