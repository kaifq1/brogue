"""Audience panel: does the humanized version land better with the people it is for?

Each juror is a persona. Each juror sees the two versions blind, twice, with
the order swapped, so a juror that just picks whichever comes first cancels
itself out and shows up in `position_bias`.

Simulated readers are a screening tool. They catch regressions cheaply and
they disagree with each other in useful ways. They are not evidence about what
real people in a demographic prefer, and the report says so.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import prompts
from .llm import LLM
from .persona import Persona, load

_JSON = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Ballot:
    juror: str
    humanized_slot: str  # which label the humanized text wore
    choice: str  # label the juror picked
    human_delta: float  # humanized minus original, 1-10 scale
    fit_delta: float
    why: str = ""

    @property
    def for_humanized(self) -> bool:
        return self.choice == self.humanized_slot


@dataclass
class PanelReport:
    ballots: list[Ballot] = field(default_factory=list)
    spoiled: int = 0
    source: str = "brogue-panel"

    def _rate(self, ballots: list[Ballot]) -> float:
        return sum(b.for_humanized for b in ballots) / len(ballots) if ballots else 0.0

    @property
    def win_rate(self) -> float:
        return self._rate(self.ballots)

    @property
    def position_bias(self) -> float:
        """Share of ballots that chose slot A. Far from 0.5 means order, not content, decided."""
        return sum(b.choice == "A" for b in self.ballots) / len(self.ballots) if self.ballots else 0.5

    def by_juror(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for name in dict.fromkeys(b.juror for b in self.ballots):
            mine = [b for b in self.ballots if b.juror == name]
            out[name] = {
                "win_rate": self._rate(mine),
                "human_delta": sum(b.human_delta for b in mine) / len(mine),
                "fit_delta": sum(b.fit_delta for b in mine) / len(mine),
                "ballots": len(mine),
            }
        return out

    @property
    def verdict(self) -> str:
        if not self.ballots:
            return "no valid ballots"
        if abs(self.position_bias - 0.5) > 0.3:
            return "inconclusive: jurors picked by position"
        losers = [n for n, s in self.by_juror().items() if s["win_rate"] < 0.5]
        if self.win_rate >= 0.6 and not losers:
            return "humanized version preferred across the panel"
        if self.win_rate >= 0.6:
            return f"preferred overall, but it lost with: {', '.join(losers)}"
        if self.win_rate <= 0.4:
            return "original preferred: the rewrite made it worse for this audience"
        return "no clear preference"

    def to_dict(self) -> dict:
        return {
            "source": self.source, "verdict": self.verdict, "win_rate": round(self.win_rate, 3),
            "position_bias": round(self.position_bias, 3), "spoiled": self.spoiled,
            "by_juror": self.by_juror(),
            "ballots": [vars(b) | {"for_humanized": b.for_humanized} for b in self.ballots],
        }

    def markdown(self) -> str:
        lines = [
            f"**Verdict:** {self.verdict}",
            f"Humanized win rate {self.win_rate:.0%} over {len(self.ballots)} ballots "
            f"(position bias {self.position_bias:.0%} chose A; {self.spoiled} spoiled). Source: {self.source}.",
            "", "| Juror | Prefers humanized | Sounds human | Fits me |", "|---|---|---|---|",
        ]
        for name, s in self.by_juror().items():
            lines.append(f"| {name} | {s['win_rate']:.0%} | {s['human_delta']:+.1f} | {s['fit_delta']:+.1f} |")
        quotes = [f"- {b.juror}: {b.why}" for b in self.ballots if b.why][:8]
        if quotes:
            lines += ["", "What decided it:", *quotes]
        lines += ["", "_Simulated readers screen for regressions. They do not stand in for real ones._"]
        return "\n".join(lines)


def parse_ballot(raw: str, juror: str, humanized_slot: str) -> Ballot | None:
    match = _JSON.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        choice = str(data["choice"]).strip().upper()[:1]
        if choice not in ("A", "B"):
            return None
        other = "B" if humanized_slot == "A" else "A"
        human, fit = data.get("human", {}), data.get("fit", {})
        return Ballot(
            juror, humanized_slot, choice,
            float(human[humanized_slot]) - float(human[other]),
            float(fit[humanized_slot]) - float(fit[other]),
            str(data.get("why", ""))[:300],
        )
    except (KeyError, TypeError, ValueError):
        return None


def _ask(persona: Persona, context: str, original: str, humanized: str, slot: str, llm: LLM,
         heard: list[Ballot] | None = None) -> Ballot | None:
    a, b = (humanized, original) if slot == "A" else (original, humanized)
    system, user = prompts.juror(persona, context, a, b)
    if heard:
        other = "B" if slot == "A" else "A"
        said = "\n".join(f"- A reader who preferred {slot if h.for_humanized else other}: {h.why}"
                         for h in heard if h.why)
        user += ("\n\nBefore you answer, here is what other readers said. They are different people "
                 f"with different expectations. Weigh it, then answer for yourself.\n{said}")
    return parse_ballot(llm(system, user), persona.name, slot)


def run(original: str, humanized: str, jurors: list[str | Persona], llm: LLM,
        context: str = "You received this message.", rounds: int = 1,
        deliberate: bool = False) -> PanelReport:
    """Blind, order-balanced comparison.

    With `deliberate`, every juror votes again after reading the other jurors'
    reasons, and only that second vote is reported. This is the cheap version
    of what a social simulation gives you: opinion after exposure to others.
    """
    personas = [load(j) for j in jurors]
    report = PanelReport()
    for persona in personas:
        for _ in range(rounds):
            for slot in ("A", "B"):
                ballot = _ask(persona, context, original, humanized, slot, llm)
                if ballot:
                    report.ballots.append(ballot)
                else:
                    report.spoiled += 1
    if not deliberate:
        return report
    final = PanelReport(source="brogue-panel:deliberated")
    for persona in personas:
        heard = [b for b in report.ballots if b.juror != persona.name]
        for slot in ("A", "B"):
            ballot = _ask(persona, context, original, humanized, slot, llm, heard)
            if ballot:
                final.ballots.append(ballot)
            else:
                final.spoiled += 1
    return final
