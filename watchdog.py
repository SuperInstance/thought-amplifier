"""
Ollama Watchdog — keeps the local model alive during overnight runs.

Checks Ollama health, restarts if dead, verifies GPU availability,
and logs all watchdog events for the morning briefing.

Scope is the Ollama server and the required model only: this module does
not watch the amplifier or distillation processes, does not send alerts,
and never stops a running Ollama — its only recovery actions are starting
the server and pulling the model.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Configuration ─────────────────────────────────────────────

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/tags")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite3.1-dense:2b")
OLLAMA_BIN = os.environ.get("OLLAMA_BIN", "/home/eileen/.local/bin/ollama")

REPO_ROOT = Path(__file__).resolve().parent
WATCHDOG_LOG = REPO_ROOT / "distillation-output" / "logs" / "watchdog.jsonl"
WATCHDOG_LOG.parent.mkdir(parents=True, exist_ok=True)

# Maximum restart attempts before giving up
MAX_RESTART_ATTEMPTS = 5
# Seconds to wait between restart attempts (exponential backoff base)
RESTART_BACKOFF_BASE = 5
# Seconds to wait for Ollama to respond after restart
HEALTH_CHECK_TIMEOUT = 30


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Log a watchdog event to the JSONL log."""
    entry = {
        "timestamp": _iso_ts(),
        "type": event_type,
        "details": details or {},
    }
    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def check_ollama_alive() -> bool:
    """Quick liveness check — can we reach the Ollama API?"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--connect-timeout", "5", "--max-time", "10",
             OLLAMA_URL],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        return "models" in data or isinstance(data, dict)
    except Exception:
        return False


def check_model_available() -> bool:
    """Check if the specific model we need is available in Ollama."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--connect-timeout", "5", "--max-time", "10",
             "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        models = [m.get("name", "") for m in data.get("models", [])]
        return OLLAMA_MODEL in models
    except Exception:
        return False


def check_gpu_available() -> bool:
    """
    Check whether a GPU is visible for Ollama inference.

    Tries nvidia-smi, then the WSL2 /proc/driver/nvidia path. Returns False
    when neither indicates a GPU; callers treat that as a warning rather than
    fatal, since Ollama can fall back to CPU.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check the WSL2 /proc/driver/nvidia path
    nvidia_proc = Path("/proc/driver/nvidia")
    if nvidia_proc.exists():
        return True

    return False


def start_ollama() -> bool:
    """Start the Ollama server."""
    log_event("restart_attempt", {"binary": OLLAMA_BIN})

    try:
        proc = subprocess.Popen(
            [OLLAMA_BIN, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from our process group
        )
        log_event("restart_started", {"pid": proc.pid})
        return True
    except (FileNotFoundError, OSError) as e:
        log_event("restart_failed", {"error": str(e)})
        return False


def ensure_model_pulled() -> bool:
    """Ensure the required model is pulled in Ollama."""
    if check_model_available():
        return True

    log_event("model_pull_start", {"model": OLLAMA_MODEL})
    try:
        result = subprocess.run(
            [OLLAMA_BIN, "pull", OLLAMA_MODEL],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            log_event("model_pull_success", {"model": OLLAMA_MODEL})
            return True
        else:
            log_event("model_pull_failed", {
                "model": OLLAMA_MODEL,
                "stderr": result.stderr[:500],
            })
            return False
    except subprocess.TimeoutExpired:
        log_event("model_pull_timeout", {"model": OLLAMA_MODEL})
        return False


def health_check_full() -> dict[str, Any]:
    """
    Full health check — returns a detailed status report.

    Checks:
      - Ollama process alive
      - Required model available
      - GPU accessible
      - Test inference works
    """
    status = {
        "timestamp": _iso_ts(),
        "ollama_alive": False,
        "model_available": False,
        "gpu_available": False,
        "test_inference": False,
        "issues": [],
    }

    # Check process
    if not check_ollama_alive():
        status["issues"].append("Ollama process not responding")
        return status
    status["ollama_alive"] = True

    # Check GPU
    gpu = check_gpu_available()
    status["gpu_available"] = gpu
    if not gpu:
        status["issues"].append("GPU not detected — will use CPU (slower)")

    # Check model
    if not check_model_available():
        status["issues"].append(f"Model {OLLAMA_MODEL} not available")
        return status
    status["model_available"] = True

    # Quick test inference
    try:
        result = subprocess.run(
            ["curl", "-s", "--connect-timeout", "10", "--max-time", "30",
             "-X", "POST", "http://localhost:11434/api/generate",
             "-d", json.dumps({
                 "model": OLLAMA_MODEL,
                 "prompt": "Say 'ok'.",
                 "stream": False,
                 "options": {"num_predict": 5},
             })],
            capture_output=True, text=True, timeout=35,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            status["test_inference"] = bool(data.get("response", ""))
        else:
            status["issues"].append("Test inference returned error")
    except Exception as e:
        status["issues"].append(f"Test inference failed: {e}")

    return status


def ensure_healthy(max_attempts: int = MAX_RESTART_ATTEMPTS) -> bool:
    """
    Ensure Ollama is healthy. If not, attempt recovery.

    Returns True if Ollama is healthy (now or after recovery).
    Returns False if recovery failed after max_attempts.
    """
    for attempt in range(1, max_attempts + 1):
        status = health_check_full()

        if status["ollama_alive"] and status["model_available"] and status["test_inference"]:
            if attempt > 1:
                log_event("recovery_success", {"attempt": attempt})
            return True

        # GPU not available is a warning, not a blocker
        if not status["gpu_available"]:
            log_event("gpu_warning", {"issues": status["issues"]})

        # If Ollama is down, try to restart
        if not status["ollama_alive"]:
            log_event("ollama_down_restart", {"attempt": attempt})
            start_ollama()

            # Wait for it to come up with exponential backoff
            wait = RESTART_BACKOFF_BASE * (2 ** (attempt - 1))
            time.sleep(min(wait, 60))

            # Check if it's up now
            if check_ollama_alive():
                log_event("restart_success", {"attempt": attempt})
                # Ensure model is pulled
                ensure_model_pulled()
                # Wait a moment for model to be ready
                time.sleep(2)
            else:
                log_event("restart_failed_retry", {"attempt": attempt})
                continue

        # If process is alive but model missing, pull it
        if status["ollama_alive"] and not status["model_available"]:
            log_event("model_missing_pull", {"model": OLLAMA_MODEL})
            ensure_model_pulled()

        # Re-check health
        time.sleep(3)
        recheck = health_check_full()
        if recheck["ollama_alive"] and recheck["model_available"] and recheck["test_inference"]:
            log_event("recovery_success", {"attempt": attempt})
            return True

        log_event("recovery_retry", {
            "attempt": attempt,
            "remaining": max_attempts - attempt,
        })

        if attempt < max_attempts:
            wait = RESTART_BACKOFF_BASE * (2 ** (attempt - 1))
            time.sleep(min(wait, 60))

    log_event("recovery_failed", {"max_attempts": max_attempts})
    return False
