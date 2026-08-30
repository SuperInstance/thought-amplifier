#!/usr/bin/env python3
"""
core/thinker.py — The Continuous Thought Loop

A small model thinks continuously, producing a stream of thoughts.
Ollama (localhost:11434) is the preferred backend with Granite 3.1 2B.
If Ollama is unavailable, falls back to GLM API or DeepSeek API.

The thinker is NOT an agent: it doesn't call tools or plan actions. It
generates thoughts given the current prompt and context, one at a time,
forever (or until stopped). It does NOT stream tokens (stream=False), does
NOT retry within a tick beyond the single Ollama → GLM → DeepSeek sweep
(a failed tick is journalled and the loop tries again on the next one),
and keeps no state beyond the journal and an in-memory thought count.

Design principles from REPO_DESIGN.md:
- Degrades gracefully: Ollama → GLM → DeepSeek → error (never blocks)
- Every thought carries metadata: prompt version, model, temperature
- The supervisor shapes thoughts by modifying the prompt/params,
  NOT by intercepting the thought itself
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.journal import Journal


# ─── Configuration ──────────────────────────────────────────────

@dataclass
class ThinkerConfig:
    """Configuration for the thought loop."""
    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "granite3.1-dense:2b"

    # API fallback settings
    glm_api_url: str = "https://api.z.ai/api/paas/v4/chat/completions"
    glm_api_key: str = ""  # From ZAI_API_KEY or ZHIPUAI_API_KEY env
    glm_model: str = "glm-4-flash"  # Cheap fast model

    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    deepseek_api_key: str = ""  # From DEEPSEEK_API_KEY env
    deepseek_model: str = "deepseek-chat"

    # Thought generation parameters
    system_prompt: str = (
        "You are a stream of consciousness. Generate one interesting, specific "
        "thought right now. Be concise (2-4 sentences). Be original — don't "
        "repeat ideas. Connect concepts in surprising ways. Think about "
        "whatever is most interesting given the context."
    )
    temperature: float = 0.9
    max_tokens: int = 200
    interval: float = 5.0  # Seconds between thoughts

    # Context injection
    context: str = ""  # Additional context prepended to each thought

    # Which backend to try, in order
    backend_priority: list[str] = field(default_factory=lambda: ["ollama", "glm", "deepseek"])


# ─── HTTP via curl ──────────────────────────────────────────────

def _curl_post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None,
                    timeout: int = 30) -> dict[str, Any]:
    """POST JSON using subprocess+curl. Cloudflare blocks Python HTTP libraries.

    Returns the parsed JSON response dict.
    Raises RuntimeError on failure.
    """
    json_str = json.dumps(payload, ensure_ascii=False)
    cmd = [
        "curl", "-s", "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "--max-time", str(timeout),
        "--data-binary", "@-",
    ]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])

    try:
        result = subprocess.run(
            cmd,
            input=json_str,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if result.returncode != 0:
            raise RuntimeError(f"curl failed (exit {result.returncode}): {result.stderr}")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"curl timed out after {timeout}s")
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON response: {result.stdout[:500]}")
    except Exception as e:
        raise RuntimeError(f"curl error: {e}")


def _curl_get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    """GET JSON using subprocess+curl."""
    cmd = ["curl", "-s", "--max-time", str(timeout), url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode != 0:
            raise RuntimeError(f"curl GET failed: {result.stderr}")
        return json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"curl GET error: {e}")


# ─── Backend Check ──────────────────────────────────────────────

def check_ollama(url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is available and responsive."""
    try:
        result = _curl_get_json(f"{url}/api/tags", timeout=3)
        return "models" in result
    except Exception:
        return False


def resolve_api_keys() -> dict[str, str]:
    """Find API keys from environment variables and .bashrc."""
    keys: dict[str, str] = {}

    # Check environment first
    for var in ("ZAI_API_KEY", "Z_AI_API_KEY", "ZHIPUAI_API_KEY"):
        val = os.environ.get(var, "")
        if val:
            keys["glm"] = val
            break
    for var in ("DEEPSEEK_API_KEY",):
        val = os.environ.get(var, "")
        if val:
            keys["deepseek"] = val
            break

    # If not found in env, try .bashrc
    if "glm" not in keys or "deepseek" not in keys:
        import re
        for bashrc_path in (
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.profile"),
            os.path.expanduser("~/.bash_profile"),
        ):
            try:
                with open(bashrc_path, "r") as f:
                    for line in f:
                        # Match: export VAR_NAME="value"
                        m = re.match(r'\s*export\s+(\w+)\s*=\s*["\']([^"\']+)["\']', line)
                        if m:
                            var_name = m.group(1)
                            var_value = m.group(2)
                            if var_name in ("ZAI_API_KEY", "Z_AI_API_KEY", "ZHIPUAI_API_KEY") and "glm" not in keys:
                                keys["glm"] = var_value
                            elif var_name == "DEEPSEEK_API_KEY" and "deepseek" not in keys:
                                keys["deepseek"] = var_value
            except FileNotFoundError:
                continue

    return keys


# ─── Thought Generation ─────────────────────────────────────────

def generate_ollama(config: ThinkerConfig) -> str:
    """Generate a thought using Ollama."""
    user_content = config.context + "\n\nGenerate one thought right now."
    payload = {
        "model": config.ollama_model,
        "messages": [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
        },
    }
    result = _curl_post_json(f"{config.ollama_url}/api/chat", payload)
    return result.get("message", {}).get("content", "").strip()


def generate_glm(config: ThinkerConfig) -> str:
    """Generate a thought using GLM API (Z.AI)."""
    if not config.glm_api_key:
        raise RuntimeError("No GLM API key configured")

    user_content = config.context + "\n\nGenerate one thought right now."
    payload = {
        "model": config.glm_model,
        "messages": [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {config.glm_api_key}"}
    result = _curl_post_json(config.glm_api_url, payload, headers=headers)
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def generate_deepseek(config: ThinkerConfig) -> str:
    """Generate a thought using DeepSeek API."""
    if not config.deepseek_api_key:
        raise RuntimeError("No DeepSeek API key configured")

    user_content = config.context + "\n\nGenerate one thought right now."
    payload = {
        "model": config.deepseek_model,
        "messages": [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {config.deepseek_api_key}"}
    result = _curl_post_json(config.deepseek_api_url, payload, headers=headers)
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


# ─── Backend Resolution ─────────────────────────────────────────

def detect_backend(config: ThinkerConfig) -> str:
    """Detect which backend to use based on availability.

    Returns the backend name ("ollama", "glm", or "deepseek").
    """
    for backend in config.backend_priority:
        if backend == "ollama" and check_ollama(config.ollama_url):
            return "ollama"
        elif backend == "glm" and config.glm_api_key:
            return "glm"
        elif backend == "deepseek" and config.deepseek_api_key:
            return "deepseek"

    # Last resort: deepseek if we have any key
    if config.deepseek_api_key:
        return "deepseek"
    if config.glm_api_key:
        return "glm"

    raise RuntimeError(
        "No LLM backend available. Install Ollama or set ZAI_API_KEY / DEEPSEEK_API_KEY"
    )


GENERATORS: dict[str, Callable[[ThinkerConfig], str]] = {
    "ollama": generate_ollama,
    "glm": generate_glm,
    "deepseek": generate_deepseek,
}


# ─── The Thought Loop ───────────────────────────────────────────

class Thinker:
    """The continuous thought generator.

    Generates thoughts at the configured interval, using the best available
    backend. The supervisor can modify the config at any time to shape
    what thoughts look like.
    """

    def __init__(self, config: ThinkerConfig, journal: Journal) -> None:
        self.config = config
        self.journal = journal
        self.backend: str | None = None
        self.backend_history: list[dict[str, Any]] = []
        self.thought_count = 0
        self._running = False
        self._on_thought: Callable[[dict[str, Any]], None] | None = None

    def set_on_thought(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback called after each thought is generated."""
        self._on_thought = callback

    def _resolve_backend(self) -> str:
        """Find and cache the best backend."""
        if self.backend is None:
            self.backend = detect_backend(self.config)
            self.journal.write(
                "system",
                f"Backend: {self.backend} "
                f"(model={self._backend_model_name()})",
                {"backend": self.backend, "model": self._backend_model_name()},
            )
        return self.backend

    def _backend_model_name(self) -> str:
        """Get the model name for the current backend."""
        if self.backend == "ollama":
            return self.config.ollama_model
        elif self.backend == "glm":
            return self.config.glm_model
        elif self.backend == "deepseek":
            return self.config.deepseek_model
        return "unknown"

    def generate_one(self) -> str:
        """Generate a single thought using the best available backend.

        Tries the primary backend first, falls back to others on error.
        """
        errors: list[str] = []

        for backend_name in self.config.backend_priority:
            generator = GENERATORS.get(backend_name)
            if generator is None:
                continue

            if backend_name == "ollama" and not check_ollama(self.config.ollama_url):
                errors.append("ollama: not available")
                continue
            if backend_name == "glm" and not self.config.glm_api_key:
                errors.append("glm: no API key")
                continue
            if backend_name == "deepseek" and not self.config.deepseek_api_key:
                errors.append("deepseek: no API key")
                continue

            try:
                thought = generator(self.config)
                if thought:
                    self.backend = backend_name
                    return thought
            except Exception as e:
                errors.append(f"{backend_name}: {e}")
                continue

        raise RuntimeError(f"All backends failed: {'; '.join(errors)}")

    def think_once(self) -> dict[str, Any]:
        """Generate one thought, journal it, and return the entry."""
        try:
            thought_text = self.generate_one()
        except Exception as e:
            # Journal the failure and return; the loop retries on the next tick.
            entry = self.journal.write(
                "system",
                f"Thought generation failed: {e}",
                {"error": str(e), "thought_count": self.thought_count},
            )
            return entry

        self.thought_count += 1

        entry = self.journal.write(
            "thought",
            thought_text,
            {
                "backend": self.backend,
                "model": self._backend_model_name(),
                "temperature": self.config.temperature,
                "thought_number": self.thought_count,
                "system_prompt": self.config.system_prompt[:200] + "..."
                    if len(self.config.system_prompt) > 200 else self.config.system_prompt,
            },
        )

        if self._on_thought:
            try:
                self._on_thought(entry)
            except Exception:
                pass  # Callback errors shouldn't crash the loop

        return entry

    def run(self) -> None:
        """Run the continuous thought loop. Blocks until interrupted."""
        self._running = True
        self._resolve_backend()

        self.journal.write(
            "system",
            f"Thought loop started (backend={self.backend}, "
            f"model={self._backend_model_name()}, "
            f"interval={self.config.interval}s)",
        )

        while self._running:
            try:
                self.think_once()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.journal.write("system", f"Loop error: {e}", {"error": str(e)})

            # Wait for interval (check running flag for clean shutdown)
            waited = 0.0
            while self._running and waited < self.config.interval:
                time.sleep(0.5)
                waited += 0.5

        self.journal.write(
            "system",
            f"Thought loop stopped after {self.thought_count} thoughts",
        )

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._running = False
