#!/usr/bin/env python3
"""Deterministic AI-tell linter.

Stdlib only and single-file on purpose: the same file ships inside the agent
skill (skills/brogue/scripts/lint.py) so it runs anywhere Python does, with no
install step and no model call.

The score is a density, not a verdict. Humans use every pattern here; what
reads as machine-written is several of them clustered in one passage.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field

PASS_BELOW = 10  # leave the text alone
CLUSTER_WEIGHT = 3.0  # below this total, hits are isolated and prove nothing
REWRITE_FROM = 30  # too dense for spot edits

_AP = "['’]"  # straight or curly apostrophe


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    weight: float
    pattern: str
    advice: str
    flags: int = re.IGNORECASE

    def regex(self) -> re.Pattern[str]:
        return re.compile(self.pattern, self.flags)


RULES: list[Rule] = [
    Rule(
        "ai-vocab", "vocabulary", 1.0,
        r"\b(?:delv(?:e|es|ed|ing)|tapestr(?:y|ies)|testament|pivotal|intricate|intricacies"
        r"|meticulous(?:ly)?|multifaceted|paramount|foster(?:s|ed|ing)?|leverag(?:e|es|ed|ing)"
        r"|utiliz(?:e|es|ed|ing)|facilitat(?:e|es|ed|ing)|empower(?:s|ed|ing)?"
        r"|streamlin(?:e|es|ed|ing)|robust|seamless(?:ly)?|cutting-edge|groundbreaking"
        r"|transformative|game-?changers?|holistic|synerg(?:y|ies)|paradigm|myriad|plethora"
        r"|vibrant|ever-evolving|realm|beacon|elevat(?:e|es|ed|ing)|embark(?:s|ed|ing)?"
        r"|harness(?:es|ed|ing)?|supercharg(?:e|es|ed|ing)|underscor(?:e|es|ed|ing)"
        r"|showcas(?:e|es|ed|ing)|deep dive|treasure trove|valuable insights)\b",
        "Use the plain word (use, help, show, strong, careful) or cut it.",
    ),
    Rule(
        "soft-vocab", "vocabulary", 0.5,
        r"\b(?:landscape|crucial|comprehensive|enhanc(?:e|es|ed|ing)|unlock(?:s|ed|ing)?"
        r"|journey|navigat(?:e|es|ed|ing)|innovative|dynamic)\b",
        "Fine once and literally. In a cluster, swap for the specific thing.",
    ),
    Rule(
        "filler", "phrasing", 1.5,
        rf"\b(?:it{_AP}?s worth noting|it is worth noting|(?:it{_AP}?s |it is )?important to (?:note|remember)"
        r"|in today" + _AP + r"s (?:[\w-]+ )?(?:world|age|era|landscape)|at the end of the day"
        r"|when it comes to|at its core|let" + _AP + r"s dive in|dive into|in the (?:realm|world) of"
        r"|plays? an? (?:vital|crucial|key|pivotal|significant) role"
        r"|here" + _AP + r"s the thing|let me be clear|the (?:truth|reality) is|look no further"
        r"|rich (?:cultural )?heritage|needless to say)\b",
        "Delete the run-up and state the point.",
    ),
    Rule(
        "chatbot-residue", "residue", 3.0,
        rf"(?:\bgreat question\b|\bi hope this helps\b|\blet me know if\b|\bcertainly!|\babsolutely!"
        rf"|\bas an ai\b|\bas of my last\b|\byou{_AP}re absolutely right\b|\bwould you like me to\b"
        r"|\bfeel free to\b|\bhappy to help\b|\bi can help (?:you )?with that\b)",
        "This is the assistant talking to its user. It never belongs in the deliverable.",
    ),
    Rule(
        "not-x-but-y", "structure", 2.0,
        r"\bnot (?:just|only|merely|simply) [^.!?\n]{1,80}?\bbut\b"
        rf"|\b(?:isn{_AP}t|aren{_AP}t|wasn{_AP}t|is not|are not|not) (?:just |only |merely |simply )?"
        rf"(?:about )?[^.!?,;\n]{{1,60}}[.,;—–]\s*(?:it{_AP}s|it is|they{_AP}re|this is|that{_AP}s)\b",
        "Nobody claimed X. State Y directly.",
    ),
    Rule(
        "trailing-ing", "structure", 1.5,
        r",\s+(?:highlighting|underscoring|reflecting|showcasing|emphasizing|ensuring|fostering"
        r"|demonstrating|solidifying|cementing|paving the way)\b",
        "End the sentence at the fact. If the consequence is real, give it its own sentence.",
    ),
    Rule(
        "copula-dodge", "structure", 1.0,
        r"\b(?:serves? as|stands? as|boasts?)\b",
        "Say 'is' or 'has'.",
    ),
    Rule(
        "weasel-source", "authority", 1.5,
        r"\b(?:experts (?:agree|say|believe)|studies (?:show|suggest|have shown)"
        r"|research (?:shows|suggests)|many (?:argue|believe)|widely regarded"
        r"|industry (?:reports|experts))\b",
        "Name the source or own the claim. Never invent one.",
    ),
    Rule(
        "summary-closer", "structure", 2.0,
        r"^\s*(?:in conclusion|in summary|overall|ultimately|to sum up|all in all),",
        "The reader was just there. End on the last concrete point.",
        re.IGNORECASE | re.MULTILINE,
    ),
    Rule(
        "faux-insight", "staging", 2.0,
        rf"\b(?:here{_AP}s what (?:nobody|no one)|what most people (?:get wrong|miss)"
        r"|the part (?:everyone|most people) (?:misses|miss|skips|skip)|plot twist|what if i told you)\b",
        "Drop the setup. Make the claim and let it stand.",
    ),
    Rule(
        "colon-reveal", "staging", 1.0,
        r"\bthe (?:best|worst|real|key|hard|interesting|biggest) "
        r"(?:part|thing|truth|lesson|problem|question|takeaway|secret)(?: is)?: ",
        "Write it as a plain sentence.",
    ),
    Rule(
        "empty-claim", "phrasing", 1.5,
        r"\b(?:the results (?:are clear|speak for themselves)"
        r"|more than (?:just )?an? (?:number|metric|tool|product|feature|milestone)"
        r"|reflects? (?:our|the|its|their) (?:broader |deep |ongoing )?(?:approach|commitment|dedication)"
        r"|(?:our|their|its) commitment to|attention to detail|every step of the way"
        r"|take[sn]? (?:it|this|things) to the next level|make[s]? all the difference)\b",
        "True of any company and any product. Cut the sentence or put a fact in it.",
    ),
    Rule(
        "hedge-stack", "phrasing", 1.0,
        r"\b(?:could|may|might|can) (?:potentially|possibly|perhaps)\b",
        "One hedge is honest. Two is noise.",
    ),
    Rule(
        "emoji-heading", "formatting", 2.0,
        r"^#{1,6} .*[\U0001F300-\U0001FAFF☀-➿]",
        "No emoji in headings.",
        re.MULTILINE,
    ),
    Rule(
        "bold-label-bullet", "formatting", 1.0,
        r"^\s*[-*] \*\*[^*\n]+(?::\*\*|\*\*:)",
        "A '**Term:** definition' list is usually two sentences of prose.",
        re.MULTILINE,
    ),
]

_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_BLOCKQUOTE = re.compile(r"^\s*>.*$", re.MULTILINE)
_QUOTED = re.compile(r"\"[^\"\n]{1,200}\"|\u201c[^\u201d\n]{1,200}\u201d")
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’)]*\s+(?=[A-Z\"'“(])")
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
_TRIAD = re.compile(r"\b[\w-]+, [\w-]+(?: [\w-]+)?,? and [\w-]+")
_EM_DASH = re.compile(r"—|(?<=\w) -- (?=\w)")


@dataclass
class Finding:
    rule: str
    category: str
    weight: float
    line: int
    match: str
    advice: str


@dataclass
class Report:
    words: int
    score: int
    route: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def by_rule(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.rule] = out.get(f.rule, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "words": self.words,
            "score": self.score,
            "route": self.route,
            "by_rule": self.by_rule,
            "findings": [asdict(f) for f in self.findings],
        }


def _blank(match: re.Match[str]) -> str:
    # Keep newlines so line numbers survive.
    return re.sub(r"[^\n]", " ", match.group(0))


def prose_only(text: str) -> str:
    """Mask code and quoted text: they are not ours to judge or rewrite."""
    for pattern in (_FENCE, _INLINE_CODE, _BLOCKQUOTE, _QUOTED):
        text = pattern.sub(_blank, text)
    return text


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        if not block or block.startswith("#"):
            continue
        out.extend(s for s in _SENTENCE_END.split(block) if _WORD.search(s))
    return out


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _rhythm_findings(prose: str) -> list[Finding]:
    found: list[Finding] = []
    sents = sentences(prose)
    lengths = [word_count(s) for s in sents]
    if len(lengths) >= 6:
        mean = statistics.mean(lengths)
        spread = statistics.pstdev(lengths) / mean if mean else 0.0
        if spread < 0.25:
            found.append(Finding(
                "metronome", "rhythm", 2.0, 1,
                f"{len(lengths)} sentences, mean {mean:.0f} words, spread {spread:.2f}",
                "Every sentence is the same length. Let a short one follow a long one.",
            ))
    run = 0
    for sent, n in zip(sents, lengths):
        run = run + 1 if n <= 4 else 0
        if run == 3:
            at = prose.find(sent.strip()[:20])
            found.append(Finding(
                "staccato", "rhythm", 1.5, _line_of(prose, max(at, 0)), sent.strip()[:80],
                "Three clipped fragments in a row is staged drama. Use a full sentence.",
            ))
    return found


def lint(text: str) -> Report:
    prose = prose_only(text)
    words = word_count(prose)
    findings: list[Finding] = []

    for rule in RULES:
        for m in rule.regex().finditer(prose):
            findings.append(Finding(
                rule.id, rule.category, rule.weight, _line_of(prose, m.start()),
                " ".join(m.group(0).split())[:80], rule.advice,
            ))

    dashes = list(_EM_DASH.finditer(prose))
    allowed = max(1, words // 300)
    for m in dashes[allowed:]:
        findings.append(Finding(
            "em-dash", "rhythm", 1.0, _line_of(prose, m.start()), "—",
            "A comma, a period or parentheses will do. Keep at most one per 300 words.",
        ))

    for m in list(_TRIAD.finditer(prose))[1:]:
        findings.append(Finding(
            "triad", "rhythm", 0.5, _line_of(prose, m.start()), m.group(0)[:80],
            "Lists of three by reflex. Keep the one or two items that carry weight.",
        ))

    findings.extend(_rhythm_findings(prose))
    findings.sort(key=lambda f: (f.line, f.rule))

    weighted = sum(f.weight for f in findings)
    # The floor stops one stray word in a two-line reply from scoring as slop.
    score = min(100, round(weighted / max(words, 50) * 1000))
    if weighted < CLUSTER_WEIGHT:
        score = min(score, PASS_BELOW - 1)
    route = "pass" if score < PASS_BELOW else "edit" if score < REWRITE_FROM else "rewrite"
    return Report(words=words, score=score, route=route, findings=findings)


def render(report: Report, limit: int = 40) -> str:
    lines = [f"score {report.score}/100  route: {report.route}  ({report.words} words)"]
    for f in report.findings[:limit]:
        lines.append(f"  L{f.line:<4} {f.rule:<18} {f.match!r}\n        -> {f.advice}")
    if len(report.findings) > limit:
        lines.append(f"  ... {len(report.findings) - limit} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score text for clustered AI writing tells.")
    parser.add_argument("file", nargs="?", default="-", help="path, or - for stdin")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-at", type=int, default=None, metavar="SCORE",
                        help="exit 1 when the score reaches this value (for CI)")
    args = parser.parse_args(argv)
    text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    report = lint(text)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) if args.json else render(report))
    return 1 if args.fail_at is not None and report.score >= args.fail_at else 0


if __name__ == "__main__":
    raise SystemExit(main())
