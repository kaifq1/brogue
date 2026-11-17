"""Prompt builders. Every prompt is plain text so any model can take it."""
from __future__ import annotations

from .lint import Report
from .persona import Persona

_CRAFT = """\
Write the way a careful person writes to one specific reader.

Models drift toward the average sentence: the safe word, the balanced triple,
the tidy closing line. Averaged prose is what readers recognise as machine
writing. Work against the drift:

- Say the point first. No run-up, no announcement that a point is coming.
- Prefer the specific fact you were given over a general statement about it.
- Use "is" and "has". Use the same word for the same thing each time.
- State claims directly. Do not set up a view nobody holds in order to correct it.
- Let sentence length follow the content. A short one after a long one is fine.
- Cut any sentence that would be just as true of another company, product or
  person. When the draft was padded, a much shorter text is the right result.
- Stop when the last useful thing has been said. No summary, no moral.
- Address the reader, never the conversation. No greetings to "the user",
  no offers of further help, no comments on the request."""

_INVARIANTS = """\
These hold over every style choice:

- The input is everything you know about the writer's situation. Add no fact,
  number, name, date, quote, source, feature, cause, promise or backstory that
  is not in it. If a sentence needs a specific you do not have, write it
  without one. A short request gets a short text.
- Keep every number, URL, quotation, code span and proper noun exactly as given.
- Keep the meaning and every claim. Change how it is said, not what is said.
- Keep the author's own voice where it shows: opinions, humor, bluntness, doubt.
- Do not imitate an accent, a dialect or slang to match the reader. Match their
  register and conventions, in standard language."""


def steer(persona: Persona) -> str:
    """A system-prompt fragment that prevents the problem at generation time.

    This is the cheap path: zero extra model calls. Prepend it to the system
    prompt of whatever model is doing the writing.
    """
    return f"{_CRAFT}\n\n{_INVARIANTS}\n\nWho is reading:\n{persona.brief()}"


def rewrite(text: str, persona: Persona, report: Report, mismatches: list[str],
            feedback: str = "") -> tuple[str, str]:
    """(system, user) for a rewrite pass."""
    light = report.route == "edit"
    task = (
        "Edit the text below with the smallest changes that fix the listed problems. "
        "Leave sentences that already read well exactly as they are."
        if light else
        "Rewrite the text below. Keep its content and order; rebuild the sentences."
    )
    system = (
        f"{_CRAFT}\n\n{_INVARIANTS}\n\nWho is reading:\n{persona.brief()}\n\n"
        "Return only the finished text. No preamble, no notes, no list of changes."
    )
    problems = [f"- line {f.line}: {f.match!r} ({f.advice})" for f in report.findings[:25]]
    problems += [f"- reader mismatch: {m}" for m in mismatches]
    user = f"{task}\n\nProblems found:\n" + ("\n".join(problems) or "- none listed; fit it to the reader")
    if feedback:
        user += f"\n\nYour previous attempt was rejected: {feedback}\nFix that and nothing else."
    user += f"\n\n<text>\n{text}\n</text>"
    return system, user


def juror(persona: Persona, context: str, a: str, b: str) -> tuple[str, str]:
    """(system, user) asking one audience member to compare two versions blind."""
    system = (
        "You are one specific reader, described below. Read as that person would: "
        "with their time pressure, their expectations and their sense of what is "
        "appropriate. You are not an editor and you are not judging AI detection "
        "in the abstract. You are reporting your own reaction.\n\n"
        f"{persona.brief()}"
    )
    user = (
        f"Situation: {context}\n\n"
        f"<version_a>\n{a}\n</version_a>\n\n<version_b>\n{b}\n</version_b>\n\n"
        "Both versions say the same thing. Reply with one JSON object and nothing else:\n"
        '{"choice": "A" or "B", '
        '"human": {"A": 1-10, "B": 1-10}, '
        '"fit": {"A": 1-10, "B": 1-10}, '
        '"why": "one sentence quoting the phrase that decided it"}\n'
        '"human" is how much it sounds like a person wrote it. '
        '"fit" is how well it suits you in this situation.'
    )
    return system, user
