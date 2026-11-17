"""Model access. An LLM here is any callable (system, user) -> text.

That one-function contract is the whole abstraction: wrap whatever SDK you
already use in a lambda and pass it in. `OpenAICompatible` is a convenience for
the many providers and local servers that speak the chat-completions protocol.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Callable

LLM = Callable[[str, str], str]


class LLMError(RuntimeError):
    pass


class OpenAICompatible:
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, temperature: float = 0.7, timeout: int = 120):
        self.model = model or os.environ.get("BROGUE_MODEL", "")
        self.base_url = (base_url or os.environ.get("BROGUE_BASE_URL")
                         or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("BROGUE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.temperature = temperature
        self.timeout = timeout
        if not self.model:
            raise LLMError("no model set: pass model=... or export BROGUE_MODEL")

    def __call__(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as err:
            raise LLMError(f"{err.code} from {self.base_url}: {err.read().decode(errors='replace')[:300]}") from err
        except urllib.error.URLError as err:
            raise LLMError(f"cannot reach {self.base_url}: {err.reason}") from err
        try:
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as err:
            raise LLMError(f"unexpected response shape: {str(payload)[:300]}") from err


class ClaudeCLI:
    """Use an installed Claude Code CLI as the model. No API key to manage.

    Every call is a fresh, isolated one-shot: no tools, no skills, no project
    instructions, an empty working directory. The system prompt passed in is
    the only system prompt, so the output reflects the prompt and nothing else.
    """

    def __init__(self, model: str = "haiku", timeout: int = 180, binary: str | None = None):
        self.model = model
        self.timeout = timeout
        self.binary = binary or shutil.which("claude") or ""
        if not self.binary:
            raise LLMError("claude CLI not found on PATH")
        self._cwd = tempfile.mkdtemp(prefix="brogue-")

    def __call__(self, system: str, user: str) -> str:
        command = [
            self.binary, "-p", "--model", self.model, "--system-prompt", system,
            "--tools", "", "--safe-mode", "--disable-slash-commands",
            "--strict-mcp-config", "--no-session-persistence",
        ]
        try:
            done = subprocess.run(command, input=user, capture_output=True, text=True,
                                  timeout=self.timeout, cwd=self._cwd)
        except subprocess.TimeoutExpired as err:
            raise LLMError(f"claude CLI timed out after {self.timeout}s") from err
        if done.returncode != 0:
            raise LLMError(f"claude CLI failed: {(done.stderr or done.stdout).strip()[:300]}")
        return done.stdout.strip()


def connect(provider: str = "auto", model: str | None = None, base_url: str | None = None) -> LLM:
    """Pick a model backend. 'auto' prefers an explicit API endpoint, then a local Claude CLI."""
    if provider == "auto":
        has_api = bool(base_url or os.environ.get("BROGUE_BASE_URL") or os.environ.get("BROGUE_API_KEY")
                       or os.environ.get("OPENAI_API_KEY"))
        provider = "openai" if has_api or not shutil.which("claude") else "claude-cli"
    if provider == "claude-cli":
        return ClaudeCLI(model or os.environ.get("BROGUE_MODEL") or "haiku")
    if provider == "openai":
        return OpenAICompatible(model=model, base_url=base_url)
    raise LLMError(f"unknown provider {provider!r}; use auto, openai or claude-cli")
