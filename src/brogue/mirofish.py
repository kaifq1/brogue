"""Optional adapter: run the audience panel inside a MiroFish simulation.

MiroFish (github.com/666ghj/MiroFish) is AGPL-3.0. Brogue does not import,
vendor or modify it. This module talks to a MiroFish server you run yourself,
over its HTTP API, and returns the same PanelReport as the built-in panel.

What MiroFish adds over the built-in panel: the readers are agents with
memory inside a simulated social platform, so they react after seeing each
other react. What it costs: a running backend, an LLM key, a Zep key, and
minutes per run instead of seconds.

Status: experimental. Written against the API as of MiroFish main in
November 2026 and exercised only against a stub server in tests/.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from .panel import PanelReport, parse_ballot
from .persona import Persona, load


class MiroFishError(RuntimeError):
    pass


def seed_document(original: str, humanized: str, jurors: list[Persona], context: str) -> str:
    """The seed MiroFish builds its world from: who the readers are and what they were sent."""
    roster = "\n\n".join(
        f"### Reader {i}: {p.name}\n{p.summary}\nLocale {p.locale}. Register they expect: {p.register}."
        for i, p in enumerate(jurors, 1)
    )
    return (
        "# Message test\n\n"
        f"## Situation\n{context}\n\n"
        "A sender prepared two wordings of the same message. The readers below each "
        "receive both and discuss which one they would rather have been sent.\n\n"
        f"## Readers\n\n{roster}\n\n"
        f"## Wording one\n\n{original}\n\n## Wording two\n\n{humanized}\n"
    )


def _question(a: str, b: str) -> str:
    return (
        "Two wordings of the same message follow. Answer as yourself with one JSON object "
        'and nothing else: {"choice": "A" or "B", "human": {"A": 1-10, "B": 1-10}, '
        '"fit": {"A": 1-10, "B": 1-10}, "why": "one sentence"}. "human" is how much it sounds '
        'like a person wrote it; "fit" is how well it suits you.\n\n'
        f"VERSION A:\n{a}\n\nVERSION B:\n{b}"
    )


class MiroFish:
    def __init__(self, base_url: str = "http://localhost:5001", timeout: int = 300,
                 poll_seconds: float = 5.0, deadline_seconds: float = 3600.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.poll = poll_seconds
        self.deadline = deadline_seconds

    # -- transport ---------------------------------------------------------
    def _send(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as err:
            raise MiroFishError(f"{err.code} {request.full_url}: {err.read().decode(errors='replace')[:300]}") from err
        except urllib.error.URLError as err:
            raise MiroFishError(f"cannot reach MiroFish at {self.base}: {err.reason}") from err
        if not payload.get("success"):
            raise MiroFishError(f"{request.full_url}: {payload.get('error', 'request failed')}")
        return payload.get("data") or {}

    def _json(self, path: str, body: dict | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"} if body is not None else {}
        return self._send(urllib.request.Request(f"{self.base}{path}", data=data, headers=headers))

    def _upload(self, path: str, fields: dict[str, str], filename: str, content: str) -> dict[str, Any]:
        boundary = uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()
        ]
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: text/markdown\r\n\r\n{content}\r\n--{boundary}--\r\n"
        )
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        return self._send(urllib.request.Request(f"{self.base}{path}", data="".join(parts).encode(), headers=headers))

    def _wait(self, check, what: str) -> dict[str, Any]:
        end = time.monotonic() + self.deadline
        while time.monotonic() < end:
            state = check()
            if state is not None:
                return state
            time.sleep(self.poll)
        raise MiroFishError(f"timed out waiting for {what}")

    # -- steps -------------------------------------------------------------
    def _graph_done(self, task_id: str):
        task = self._json(f"/api/graph/task/{task_id}")
        if task.get("status") == "failed":
            raise MiroFishError(f"graph build failed: {task.get('message') or task.get('error')}")
        return task if task.get("status") == "completed" else None

    def _prepared(self, simulation_id: str, task_id: str | None):
        body = {"simulation_id": simulation_id} | ({"task_id": task_id} if task_id else {})
        state = self._json("/api/simulation/prepare/status", body)
        if state.get("status") == "failed":
            raise MiroFishError(f"simulation prepare failed: {state.get('message')}")
        ready = state.get("already_prepared") or state.get("status") in ("completed", "ready")
        return state if ready else None

    def _alive(self, simulation_id: str):
        state = self._json("/api/simulation/env-status", {"simulation_id": simulation_id})
        return state if state.get("env_alive") else None

    def run_panel(self, original: str, humanized: str, jurors: list[str | Persona],
                  context: str = "The readers received this message.", max_rounds: int = 5,
                  platform: str = "reddit") -> PanelReport:
        personas = [load(j) for j in jurors]
        project = self._upload(
            "/api/graph/ontology/generate",
            {"project_name": "brogue-panel",
             "simulation_requirement": "Which wording do these readers prefer, and why? "
                                       "Model each listed reader as an individual agent."},
            "seed.md", seed_document(original, humanized, personas, context),
        )
        project_id = project["project_id"]
        build = self._json("/api/graph/build", {"project_id": project_id})
        self._wait(lambda: self._graph_done(build["task_id"]), "graph build")

        sim = self._json("/api/simulation/create", {
            "project_id": project_id,
            "enable_twitter": platform == "twitter", "enable_reddit": platform == "reddit",
        })
        simulation_id = sim["simulation_id"]
        prep = self._json("/api/simulation/prepare", {"simulation_id": simulation_id})
        self._wait(lambda: self._prepared(simulation_id, prep.get("task_id")), "simulation prepare")
        self._json("/api/simulation/start", {
            "simulation_id": simulation_id, "platform": platform, "max_rounds": max_rounds})
        self._wait(lambda: self._alive(simulation_id), "simulation environment")

        report = PanelReport(source=f"mirofish:{simulation_id}")
        try:
            for slot in ("A", "B"):
                a, b = (humanized, original) if slot == "A" else (original, humanized)
                answer = self._json("/api/simulation/interview/all", {
                    "simulation_id": simulation_id, "prompt": _question(a, b),
                    "platform": platform, "timeout": self.timeout})
                results = (answer.get("result") or {}).get("results") or {}
                for key, item in results.items():
                    ballot = parse_ballot(str(item.get("response", "")), f"agent_{item.get('agent_id', key)}", slot)
                    if ballot:
                        report.ballots.append(ballot)
                    else:
                        report.spoiled += 1
        finally:
            try:
                self._json("/api/simulation/close-env", {"simulation_id": simulation_id})
            except MiroFishError:
                pass
        return report
