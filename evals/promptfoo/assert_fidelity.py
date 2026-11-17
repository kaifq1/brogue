"""promptfoo assertion: list what the output states as fact that the request never said.

Score is 1 / (1 + made-up details); the test passes when there are none.
The auditor prompt is the same one evals/fidelity.py uses.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))
from brogue.llm import connect  # noqa: E402
from fidelity import audit  # noqa: E402


def get_assert(output, context):
    found = audit(connect("auto", "sonnet"), context["vars"]["brief"], output)
    if found is None:
        return {"pass": False, "score": 0, "reason": "the auditor reply could not be read"}
    reason = "nothing made up" if not found else "made up: " + "; ".join(found)
    return {"pass": not found, "score": 1 / (1 + len(found)), "reason": reason}
