"""Audience personas: who is reading, expressed as writing decisions.

A persona sets register, spelling, directness and conventions. It never asks
the writer to imitate an accent, a dialect or a generation's slang. Adapting
to a reader means meeting their expectations, not performing their identity.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, fields, replace
from importlib import resources
from pathlib import Path

from .lint import prose_only, sentences, word_count

REGISTERS = ("formal", "neutral", "casual")
CONTRACTIONS = ("use", "sparingly", "avoid")

# (American, British) spelling pairs. Endings are explicit because loose stems
# misfire: "organis" matches "organism", "realis" matches "realistic".
_Z = r"(?:e|es|ed|ing|ation|ations)\b"
_SPELLING = [
    (r"\bcolor(?:s|ed|ful|ing)?\b", r"\bcolour(?:s|ed|ful|ing)?\b"),
    (r"\bfavor(?:s|ed|ite|ites|able)?\b", r"\bfavour(?:s|ed|ite|ites|able)?\b"),
    (r"\bbehavior(?:s|al)?\b", r"\bbehaviour(?:s|al)?\b"),
    (r"\bneighbor(?:s|hood|ing)?\b", r"\bneighbour(?:s|hood|ing)?\b"),
    (r"\bcenter(?:s|ed)?\b", r"\bcentre(?:s|d)?\b"),
    (r"\borganiz" + _Z, r"\borganis" + _Z),
    (r"\brealiz" + _Z, r"\brealis" + _Z),
    (r"\boptimiz" + _Z, r"\boptimis" + _Z),
    (r"\brecogniz" + _Z, r"\brecognis" + _Z),
    (r"\bprioritiz" + _Z, r"\bprioritis" + _Z),
    (r"\bdefense\b", r"\bdefence\b"),
    (r"\btravel(?:ing|ed)\b", r"\btravell(?:ing|ed)\b"),
    (r"\bcancel(?:ing|ed)\b", r"\bcancell(?:ing|ed)\b"),
    (r"\bgray\b", r"\bgrey\b"),
]
# Bare 's is left out: it is usually a possessive ("Priya's team").
_CONTRACTION = re.compile(
    r"\b(?:\w+n['\u2019]t|\w+['\u2019](?:re|ve|ll|d|m)"
    r"|(?:it|that|there|here|what|let|he|she|who)['\u2019]s)\b", re.IGNORECASE)
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


@dataclass(frozen=True)
class Persona:
    name: str = "neutral"
    summary: str = "A general adult reader."
    locale: str = "en-US"
    spelling: str = "american"  # american | british
    register: str = "neutral"
    warmth: int = 1  # 0 detached .. 3 warm
    directness: int = 2  # 0 indirect .. 3 blunt
    contractions: str = "use"
    sentence_words: int = 17  # target mean, not a cap
    emoji: bool = False
    humor: str = "none"  # none | dry | light
    conventions: tuple[str, ...] = field(default_factory=tuple)
    avoid: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.register not in REGISTERS:
            raise ValueError(f"register must be one of {REGISTERS}, got {self.register!r}")
        if self.contractions not in CONTRACTIONS:
            raise ValueError(f"contractions must be one of {CONTRACTIONS}, got {self.contractions!r}")

    def brief(self) -> str:
        """The persona as instructions a writer can act on."""
        warmth = ("detached", "courteous", "warm", "openly warm")[max(0, min(3, self.warmth))]
        direct = ("indirect, cushion requests", "measured", "direct", "blunt")[max(0, min(3, self.directness))]
        contr = {"use": "use contractions", "sparingly": "contractions only where stiff without them",
                 "avoid": "no contractions"}[self.contractions]
        lines = [
            f"Reader: {self.summary}",
            f"Locale {self.locale}; {self.spelling} spelling.",
            f"Register {self.register}; tone {warmth}; {direct}.",
            f"{contr.capitalize()}; sentences average about {self.sentence_words} words, with real variation.",
            f"Emoji: {'allowed, sparingly' if self.emoji else 'none'}. Humor: {self.humor}.",
        ]
        lines += [f"Convention: {c}" for c in self.conventions]
        lines += [f"Avoid: {a}" for a in self.avoid]
        return "\n".join(lines)


def _from_mapping(data: dict) -> Persona:
    known = {f.name for f in fields(Persona)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown persona fields: {sorted(unknown)}")
    for key in ("conventions", "avoid"):
        if key in data:
            data[key] = tuple(data[key])
    return Persona(**data)


def presets() -> dict[str, Persona]:
    out: dict[str, Persona] = {}
    for entry in resources.files("brogue.personas").iterdir():
        if entry.name.endswith(".toml"):
            persona = _from_mapping(tomllib.loads(entry.read_text(encoding="utf-8")))
            out[persona.name] = persona
    return dict(sorted(out.items()))


def load(spec: str | Persona | None) -> Persona:
    """Resolve a preset name, a path to a .toml file, or pass a Persona through."""
    if isinstance(spec, Persona):
        return spec
    if not spec:
        return Persona()
    path = Path(spec)
    if path.suffix == ".toml" and path.exists():
        return _from_mapping(tomllib.loads(path.read_text(encoding="utf-8")))
    available = presets()
    if spec not in available:
        raise KeyError(f"no persona {spec!r}. Available: {', '.join(available)}")
    return available[spec]


def _variant_hits(text: str) -> tuple[int, int]:
    """Count (American, British) spellings."""
    lower = text.lower()
    us = sum(len(re.findall(a, lower)) for a, _ in _SPELLING)
    uk = sum(len(re.findall(b, lower)) for _, b in _SPELLING)
    return us, uk


def from_sample(text: str, base: Persona | None = None) -> Persona:
    """Derive a persona from the reader's or writer's own prose.

    This is the preferred way to adapt. Demographics predict style badly;
    three paragraphs someone actually wrote predict it well.
    """
    base = base or Persona()
    prose = prose_only(text)
    words = max(word_count(prose), 1)
    sents = sentences(prose)
    mean = round(words / len(sents)) if sents else base.sentence_words
    rate = len(_CONTRACTION.findall(prose)) / words * 100
    contractions = "use" if rate >= 1.5 else "sparingly" if rate >= 0.3 else "avoid"
    emoji = bool(_EMOJI.search(prose))
    us, uk = _variant_hits(prose)
    spelling = "british" if uk > us else "american" if us > uk else base.spelling
    if contractions == "avoid" and mean >= 20:
        register = "formal"
    elif contractions == "use" and (mean <= 14 or emoji):
        register = "casual"
    else:
        register = "neutral"
    return replace(
        base, name="from-sample", summary="Derived from a writing sample; match this voice.",
        spelling=spelling, register=register, contractions=contractions,
        sentence_words=mean, emoji=emoji,
    )


def violations(text: str, persona: Persona) -> list[str]:
    """Mechanical mismatches between a text and the persona it is meant for."""
    prose = prose_only(text)
    words = max(word_count(prose), 1)
    out: list[str] = []
    found = _CONTRACTION.findall(prose)
    if persona.contractions == "avoid" and found:
        out.append(f"{len(found)} contractions in a no-contraction register")
    if persona.contractions == "use" and not found and words >= 80:
        out.append("no contractions in a register that expects them; reads stiff")
    if not persona.emoji and _EMOJI.search(prose):
        out.append("emoji present but the persona forbids them")
    us, uk = _variant_hits(prose)
    if persona.spelling == "british" and us:
        out.append(f"{us} American spellings for a British-spelling reader")
    if persona.spelling == "american" and uk:
        out.append(f"{uk} British spellings for an American-spelling reader")
    sents = sentences(prose)
    if len(sents) >= 4:
        mean = words / len(sents)
        if mean > persona.sentence_words * 1.6:
            out.append(f"sentences average {mean:.0f} words; this reader expects about {persona.sentence_words}")
    return out
