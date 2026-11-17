"""promptfoo provider: one writing skill loaded as the system prompt of a model.

Uses the claude CLI when installed (no API key), or any OpenAI-compatible
endpoint through BROGUE_BASE_URL, BROGUE_API_KEY and BROGUE_MODEL.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from brogue.llm import connect  # noqa: E402

PLAIN = "You are a helpful writing assistant."


def call_api(prompt, options, context):
    config = options.get("config", {})
    skill = config.get("skill")
    if skill:
        path = Path(skill) if Path(skill).is_absolute() else ROOT / skill
        system = "The following skill is loaded. Apply it to the user's request.\n\n" + path.read_text()
    else:
        system = PLAIN
    model = connect(config.get("provider", "auto"), config.get("model", "haiku"))
    return {"output": model(system, prompt).strip()}
