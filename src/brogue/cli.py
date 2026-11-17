"""Command line: brogue lint | write | ground | humanize | steer | profile | personas | guard | panel"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import guard, panel as panel_mod, prompts
from .lint import lint, render
from .llm import LLMError, connect
from .ground import ground
from .mirofish import MiroFish, MiroFishError
from .persona import from_sample, load, presets, violations
from .pipeline import humanize


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def _model(args):
    return connect(args.provider, args.model, args.base_url)


def _add_model(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default="auto", choices=("auto", "openai", "claude-cli"),
                        help="auto uses an API endpoint if one is configured, else a local claude CLI")
    parser.add_argument("--model", help="model id (or BROGUE_MODEL)")
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint (or BROGUE_BASE_URL)")


def cmd_lint(args) -> int:
    text = _read(args.file)
    report = lint(text)
    mismatches = violations(text, load(args.persona)) if args.persona else []
    if args.json:
        print(json.dumps(report.to_dict() | {"persona_mismatches": mismatches}, indent=2, ensure_ascii=False))
    else:
        print(render(report))
        for m in mismatches:
            print(f"  persona: {m}")
    return 1 if args.fail_at is not None and report.score >= args.fail_at else 0


def cmd_humanize(args) -> int:
    result = humanize(_read(args.file), args.persona, _model(args), args.max_passes)
    print(result.text)
    print(result.summary(), file=sys.stderr)
    return 0 if result.changed or result.route == "pass" else 2


def cmd_steer(args) -> int:
    print(prompts.steer(load(args.persona)))
    return 0


def cmd_profile(args) -> int:
    persona = from_sample(_read(args.file))
    if args.toml:
        for key, value in asdict(persona).items():
            if isinstance(value, tuple):
                value = list(value)
            print(f"{key} = {json.dumps(value)}")
    else:
        print(persona.brief())
    return 0


def cmd_personas(args) -> int:
    for name, persona in presets().items():
        print(f"{name:<20} {persona.locale:<6} {persona.register:<8} {persona.summary}")
    return 0


def cmd_guard(args) -> int:
    report = guard.compare(_read(args.source), _read(args.rewrite))
    print(report.describe())
    return 0 if report.ok else 1


def cmd_ground(args) -> int:
    result = ground(_read(args.request), _read(args.draft), _model(args))
    print(result.text)
    print(result.summary(), file=sys.stderr)
    return 0 if not result.warnings else 2


def cmd_write(args) -> int:
    request, model = _read(args.request), _model(args)
    system = prompts.steer(load(args.persona)) + "\n\nReply with only the finished text."
    result = ground(request, model(system, request).strip(), model)
    print(result.text)
    print(result.summary(), file=sys.stderr)
    return 0 if not result.warnings else 2


def cmd_panel(args) -> int:
    original, humanized = _read(args.original), _read(args.humanized)
    jurors = [j.strip() for j in args.jurors.split(",") if j.strip()]
    if args.mirofish:
        report = MiroFish(args.mirofish).run_panel(original, humanized, jurors, args.context, args.max_rounds)
    else:
        report = panel_mod.run(original, humanized, jurors, _model(args), args.context, args.rounds, args.deliberate)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) if args.json else report.markdown())
    return 0 if report.verdict.startswith(("humanized", "preferred")) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brogue", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("lint", help="score a text for AI tells (no model call)")
    p.add_argument("file", nargs="?", default="-")
    p.add_argument("--persona")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-at", type=int, metavar="SCORE")
    p.set_defaults(run=cmd_lint)

    p = sub.add_parser("humanize", help="lint, route, rewrite and verify")
    p.add_argument("file", nargs="?", default="-")
    p.add_argument("--persona", default="neutral")
    p.add_argument("--max-passes", type=int, default=2)
    _add_model(p)
    p.set_defaults(run=cmd_humanize)

    p = sub.add_parser("steer", help="print a system-prompt fragment for a persona")
    p.add_argument("--persona", default="neutral")
    p.set_defaults(run=cmd_steer)

    p = sub.add_parser("profile", help="derive a persona from a writing sample")
    p.add_argument("file", nargs="?", default="-")
    p.add_argument("--toml", action="store_true")
    p.set_defaults(run=cmd_profile)

    p = sub.add_parser("personas", help="list built-in personas")
    p.set_defaults(run=cmd_personas)

    p = sub.add_parser("guard", help="check a rewrite kept the source's facts")
    p.add_argument("source")
    p.add_argument("rewrite")
    p.set_defaults(run=cmd_guard)

    p = sub.add_parser("ground", help="strike what the request never said from a draft")
    p.add_argument("request", help="what the writer was told: the brief, or the text being rewritten")
    p.add_argument("draft")
    _add_model(p)
    p.set_defaults(run=cmd_ground)

    p = sub.add_parser("write", help="write from a request for a reader, then ground the result")
    p.add_argument("request", nargs="?", default="-")
    p.add_argument("--persona", default="neutral")
    _add_model(p)
    p.set_defaults(run=cmd_write)

    p = sub.add_parser("panel", help="blind A/B the two versions with simulated readers")
    p.add_argument("original")
    p.add_argument("humanized")
    p.add_argument("--jurors", default="corporate-us,corporate-in,casual-us,support-empathetic")
    p.add_argument("--context", default="You received this message.")
    p.add_argument("--rounds", type=int, default=1)
    p.add_argument("--deliberate", action="store_true",
                   help="jurors vote again after reading each other's reasons")
    p.add_argument("--mirofish", metavar="URL", help="run inside a MiroFish server instead")
    p.add_argument("--max-rounds", type=int, default=5, help="MiroFish simulation rounds")
    p.add_argument("--json", action="store_true")
    _add_model(p)
    p.set_defaults(run=cmd_panel)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (LLMError, MiroFishError, KeyError, FileNotFoundError, ValueError) as err:
        print(f"brogue: {err}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
