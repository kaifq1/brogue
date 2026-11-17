"""promptfoo test generator: the write tasks from the task files in evals/data."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def generate_tests(config=None):
    files = (config or {}).get("files", ["tasks-agency-2.json", "tasks-agency-3.json"])
    limit = (config or {}).get("limit")
    tests = []
    for name in files:
        for task in json.loads((DATA / name).read_text())["tasks"]:
            tests.append({"description": task["name"], "vars": {"brief": task["brief"], "reader": task["reader"]}})
    return tests[:limit] if limit else tests
