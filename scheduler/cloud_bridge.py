"""
cloud_bridge.py — The Cloud Overflow: Local + Cloud Transparent Routing

When the local GPU is saturated (queue too deep, agents waiting too long),
requests are transparently routed to Cloudflare Workers AI. The agent
doesn't know or care where its inference came from — it just gets a result.

Cloudflare Workers AI free tier: 10,000 neurons/day.
@cf/meta/llama-3.1-8b-instruct is our overflow model — larger than what
the RTX 4050 can run locally, decent quality, and free within quota.

The bridge tracks:
  - Daily neuron usage (reset at UTC midnight)
  - Queue depth threshold for activation
  - Failover back to local if cloud is rate-limited
  - Per-request routing decision logged for auditability

Design principle: cloud is an accelerator, never a dependency. If the
cloud is down, rate-limited, or quota exhausted, the system degrades
gracefully — requests stay in the local queue, just slower.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger("cloud_bridge")


@dataclass
class NeuronUsage:
    """Tracks Workers AI neuron consumption."""
    date: str = ""  # YYYY-MM-DD
    neurons_used: int = 0
    daily_limit: int = 10_000

    def reset_if_new_day(self):
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if self.date != today:
            self.date = today
            self.neurons_used = 0
            logger.info("Neuron daily counter reset (new day: %s)", today)

    def remaining(self) -> int:
        self.reset_if_new_day()
        return max(0, self.daily_limit - self.neurons_used)

    def consume(self, neurons: int):
        self.reset_if_new_day()
        self.neurons_used += neurons
        if self.neurons_used > self.daily_limit:
            logger.warning("Neuron daily limit exceeded: %d/%d",
                          self.neurons_used, self.daily_limit)


class CloudBridge:
    """
    Routes inference requests to Cloudflare Workers AI when the local
    queue is overloaded.

    Routing decision:
      overflow = queue_depth >= threshold
               AND neurons_remaining > min_reserve
               AND last_cloud_error > cooldown_s ago

    If any condition fails, request stays local (returns a sentinel
    that the scheduler interprets as "keep local").
    """

    def __init__(
        self,
        account_id: str = "",
        api_token: str = "",
        model: str = "@cf/meta/llama-3.1-8b-instruct",
        overflow_threshold: int = 3,
        cooldown_s: float = 60.0,
        min_neuron_reserve: int = 500,
    ):
        """
        Args:
            account_id: Cloudflare account ID
            api_token: Workers AI API token (or set CF_API_TOKEN env)
            model: Workers AI model for overflow
            overflow_threshold: Queue depth that triggers cloud routing
            cooldown_s: Seconds to wait after a cloud error before retrying
            min_neuron_reserve: Minimum neurons to keep in reserve
        """
        self.account_id = account_id or os.environ.get("CF_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CF_API_TOKEN", "")
        self.model = model
        self.overflow_threshold = overflow_threshold
        self.cooldown_s = cooldown_s
        self.min_neuron_reserve = min_neuron_reserve
        self.neurons = NeuronUsage()
        self._last_error: float = 0.0
        self._lock = threading.Lock()

        # Stats
        self.cloud_requests = 0
        self.cloud_successes = 0
        self.cloud_failures = 0
        self.local_fallbacks = 0
        # Estimated neurons per request (rough: ~100 tokens in, ~200 out)
        self.neurons_per_request = 30  # conservative estimate

    def configure(self, account_id: str = "", api_token: str = ""):
        """Set credentials after construction."""
        if account_id:
            self.account_id = account_id
        if api_token:
            self.api_token = api_token

    def is_configured(self) -> bool:
        return bool(self.account_id and self.api_token)

    def should_overflow(self, queue_depth: int) -> bool:
        """Decide whether the next request should go to cloud."""
        if not self.is_configured():
            return False
        if queue_depth < self.overflow_threshold:
            return False
        if self.neurons.remaining() <= self.min_neuron_reserve:
            logger.debug("Cloud overflow suppressed: low neuron reserve (%d)",
                        self.neurons.remaining())
            return False
        with self._lock:
            if time.time() - self._last_error < self.cooldown_s:
                logger.debug("Cloud overflow suppressed: cooldown (%.0fs remaining)",
                            self.cooldown_s - (time.time() - self._last_error))
                return False
        return True

    def infer(self, request) -> dict:
        """
        Execute inference via Cloudflare Workers AI.

        Uses curl to POST to the Workers AI REST API.
        Returns a dict matching Ollama's response format so callers
        don't need to know the source.
        """
        if not self.is_configured():
            raise RuntimeError("CloudBridge not configured (missing account_id or api_token)")

        self.cloud_requests += 1

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )

        # Workers AI expects messages format
        payload = json.dumps({
            "messages": [
                {"role": "user", "content": request.prompt}
            ],
            "stream": False,
            "max_tokens": request.options.get("num_predict", 256),
        })

        cmd = [
            "curl", "-s", "-S",
            "--max-time", "60",
            "--connect-timeout", "10",
            "-X", "POST",
            "-H", f"Authorization: Bearer {self.api_token}",
            "-H", "Content-Type: application/json",
            "-d", payload,
            url,
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
            if proc.returncode != 0:
                self._record_error(f"curl rc={proc.returncode}: {proc.stderr}")
                raise RuntimeError(f"Cloud request failed: {proc.stderr}")

            data = json.loads(proc.stdout)

            if not data.get("success", True):
                errors = data.get("errors", [])
                msg = errors[0].get("message", "unknown") if errors else "unknown"
                self._record_error(msg)
                raise RuntimeError(f"Workers AI error: {msg}")

            self.cloud_successes += 1
            self.neurons.consume(self.neurons_per_request)

            result = data.get("result", {})
            response_text = result.get("response", "")

            # Normalize to Ollama-style response format
            return {
                "model": self.model,
                "response": response_text,
                "done": True,
                "context": [],
                "total_duration": int(result.get("usage", {}).get("total_tokens", 0)),
                "prompt_eval_count": int(result.get("usage", {}).get("prompt_tokens", 0)),
                "eval_count": int(result.get("usage", {}).get("completion_tokens", 0)),
                "_served_by": "cloudflare_workers_ai",
                "_neurons_consumed": self.neurons_per_request,
            }

        except subprocess.TimeoutExpired:
            self._record_error("timeout")
            raise RuntimeError("Cloud request timed out")
        except json.JSONDecodeError as exc:
            self._record_error(f"json decode: {exc}")
            raise RuntimeError(f"Invalid response from cloud: {exc}")

    def _record_error(self, reason: str):
        with self._lock:
            self._last_error = time.time()
        self.cloud_failures += 1
        logger.error("Cloud bridge error: %s", reason)

    def stats(self) -> dict:
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "overflow_threshold": self.overflow_threshold,
            "neurons_used_today": self.neurons.neurons_used,
            "neurons_remaining": self.neurons.remaining(),
            "neurons_daily_limit": self.neurons.daily_limit,
            "cloud_requests": self.cloud_requests,
            "cloud_successes": self.cloud_successes,
            "cloud_failures": self.cloud_failures,
            "local_fallbacks": self.local_fallbacks,
            "cooldown_active": (time.time() - self._last_error) < self.cooldown_s,
        }
