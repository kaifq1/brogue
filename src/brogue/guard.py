"""Fact guard: a rewrite may change how something is said, never what is said.

Compares the checkable facts in the source against the rewrite. Anything the
rewrite adds is treated as invented; anything it loses is treated as dropped.
This is deliberately mechanical. It cannot see a changed claim made of ordinary
words, so it is a floor under the rewrite prompt, not a replacement for it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_URL = re.compile(r"https?://[^\s)>\]\"']+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_NUMBER = re.compile(r"(?<![\w.])[$€£₹]?\d[\d,]*(?:\.\d+)?%?")
_QUOTED = re.compile(r"\"([^\"\n]{3,200})\"|“([^”\n]{3,200})”")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)


def _norm_number(raw: str) -> str:
    return raw.replace(",", "").rstrip(".")


def facts(text: str) -> dict[str, set[str]]:
    code = {" ".join(m.group(0).split()) for m in _CODE.finditer(text)}
    body = _CODE.sub(" ", text)
    urls = {m.group(0).rstrip(".,;") for m in _URL.finditer(body)}
    emails = set(_EMAIL.findall(body))
    stripped = _EMAIL.sub(" ", _URL.sub(" ", body))
    return {
        "number": {_norm_number(n) for n in _NUMBER.findall(stripped)},
        "url": urls,
        "email": emails,
        "quote": {" ".join((a or b).split()) for a, b in _QUOTED.findall(stripped)},
        "code": code,
    }


@dataclass
class GuardReport:
    added: dict[str, list[str]] = field(default_factory=dict)
    dropped: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.added and not self.dropped

    def describe(self) -> str:
        if self.ok:
            return "facts preserved"
        parts = []
        for label, group in (("invented", self.added), ("dropped", self.dropped)):
            for kind, values in group.items():
                parts.append(f"{label} {kind}: {', '.join(values)}")
        return "; ".join(parts)


def compare(source: str, rewrite: str) -> GuardReport:
    before, after = facts(source), facts(rewrite)
    report = GuardReport()
    for kind in before:
        added = sorted(after[kind] - before[kind])
        dropped = sorted(before[kind] - after[kind])
        if added:
            report.added[kind] = added
        if dropped:
            report.dropped[kind] = dropped
    return report
