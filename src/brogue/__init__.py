"""Brogue: make model output read like a person wrote it, for the person reading it."""
from .ground import Grounded, ground
from .guard import compare as fact_guard
from .lint import lint
from .persona import Persona, from_sample, load as load_persona, presets
from .pipeline import Result, humanize
from .prompts import steer

__version__ = "0.1.0"
__all__ = [
    "Grounded", "Persona", "Result", "fact_guard", "from_sample", "ground", "humanize", "lint",
    "load_persona", "presets", "steer",
]
