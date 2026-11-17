"""Grounding: strike what the request never said.

A draft written from a short request always carries more than the request did:
a feature nobody listed, a cause nobody confirmed, a promise nobody made. Rules
in a prompt reduce that and do not end it. This module closes the loop with one
more model call. The model sees the request beside the draft, lists every
statement about the writer's situation that the request does not support, and
returns the draft with those statements removed and nothing else changed.

A mechanical check then refuses any "fix" that introduces a number, link, quote
or code span of its own, or drops one the request supplied. A failed correction
is retried once, and after that the draft comes back untouched.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import guard
from .llm import LLM

SYSTEM = """\
You check a draft against the only information its writer was given, and then you fix the draft.

Step 1. Read REQUEST. It is everything the writer knows about their own situation: their product, \
team, plans, what happened and why. Then read DRAFT one sentence at a time. List each statement in \
DRAFT about that situation which REQUEST neither states nor directly implies. Typical cases: a \
feature, benefit, material or instruction for use that nobody listed; a cause, reason or backstory; \
a claim about the state of things; a commitment made on the writer's behalf to do a specific thing or meet a specific time (an \
open invitation such as "tell me if this doesn't work", or an offer of something REQUEST says \
exists, is fine and stays); a \
name, number, date or duration; what happened to customers; what the rest of a document contains; \
an example told as if it happened.

Leave alone: anything worked out from REQUEST's own facts (a total, a difference, a percentage, the \
weekday of a given date, a consequence that follows by plain logic); explanations of what a fact \
means that are true in general and not about this writer, unless they carry a made-up figure; \
greetings, thanks and apologies; bracketed placeholders; an opinion or example clearly marked as one. \
Derived conclusions are often the most useful sentence in the draft. Cut only what had to be \
supplied from outside REQUEST.

Never list a statement that REQUEST supports, even loosely worded: every fact REQUEST supplies \
must survive. REQUEST may also give instructions ("offer to join next year", "ask them to reply"). \
Whatever it tells the writer to say, offer or ask for is supported, and stays.

Step 2. Write the draft again with every listed statement deleted, or cut back to what REQUEST \
says. Change nothing else: same voice, same order, same wording, same formatting. Add nothing. If a \
deletion leaves a sentence or paragraph broken, repair it with the fewest words. A shorter text is \
the expected result.

Reply in exactly this form:
<unsupported>
one statement per line, quoted from the draft, or the single word none
</unsupported>
<text>
the corrected draft
</text>"""


@dataclass
class Grounded:
    text: str
    removed: list[str] = field(default_factory=list)
    changed: bool = False
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        head = f"grounded: {len(self.removed)} unsupported statement(s) removed" if self.changed \
            else "grounded: nothing to remove"
        return "\n".join([head, *[f"  - {r}" for r in self.removed], *[f"warning: {w}" for w in self.warnings]])


def _section(raw: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", raw, re.DOTALL)
    return match.group(1) if match else None


_WORDS = dict(zip("one two three four five six seven eight nine ten eleven twelve".split(), range(1, 13)))


def _digits(text: str) -> str:
    """Spell small numbers as digits so that "six years" and "6 years" compare equal."""
    return re.sub(r"\b(" + "|".join(_WORDS) + r")\b", lambda m: str(_WORDS[m.group(1).lower()]), text, flags=re.I)


def _problem(request: str, draft: str, text: str) -> str:
    """Why a correction cannot be accepted, or an empty string."""
    asked, had, after = (guard.facts(_digits(t)) for t in (request, draft, text))
    added = sorted(x for kind in after for x in after[kind] - had[kind] - asked[kind])
    if added:
        return "the correction introduced " + ", ".join(added[:5])
    lost = sorted(x for kind in asked for x in (asked[kind] & had[kind]) - after[kind])
    if lost:
        return "the correction dropped " + ", ".join(lost[:5]) + ", which the request supplied"
    return ""


def ground(request: str, draft: str, llm: LLM, attempts: int = 2) -> Grounded:
    """Remove from `draft` whatever `request` does not support. One model call, a second if the first fails."""
    user, warnings = f"<request>\n{request}\n</request>\n\n<draft>\n{draft}\n</draft>", []
    for _ in range(attempts):
        raw = llm(SYSTEM, user if not warnings else
                  f"{user}\n\nYour previous correction was rejected: {warnings[-1]}. "
                  "Keep every fact the request supplies and add nothing.")
        listed, text = _section(raw, "unsupported"), _section(raw, "text")
        if listed is None or not text:
            warnings.append("the checker's reply could not be read")
            continue
        removed = [line.strip(" -\t\"'") for line in listed.splitlines() if line.strip(" -\t\"'")]
        if [r.lower() for r in removed] == ["none"] or not removed or text.strip() == draft.strip():
            return Grounded(draft)
        problem = _problem(request, draft, text)
        if not problem:
            return Grounded(text.strip(), removed, True)
        warnings.append(problem)
    return Grounded(draft, warnings=[*warnings, "draft returned unchanged"])
