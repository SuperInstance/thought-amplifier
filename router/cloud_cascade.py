"""
cloud_cascade.py — Cloud Escalation Path

When local models aren't enough (UNKNOWN-UNKNOWN), we cascade to cloud
models that have a larger "model of understanding." These models can
shape problems that the local models can't even perceive.

Each cloud model has a specialty — a kind of understanding it's best at
shaping:

  DeepSeek V3 (direct API) — reasoning, planning, analysis
    The deep thinker. When the problem requires multi-step reasoning
    that local models can't follow, DeepSeek builds the chain.

  Qwen3-Coder-480B (DeepInfra) — code generation
    The builder. When the problem is "write me a function that..."
    and the local model's code is wrong or incomplete, this model
    generates production-quality code.

  Hermes-3-Llama-405B (DeepInfra) — creative, personality, voice
    The artist. When the problem requires creative thinking that
    exceeds the local models' capability, Hermes brings genuine
    novelty and personality.

  Cloudflare Workers AI (@cf/meta/llama-3.1-8b) — cheap overflow
    The utility player. When the queue is deep and we just need
    throughput, this model is free (within quota) and decent.

Cost tracking:
  Each cloud model has a per-1K-token cost. The router estimates
  total cost based on prompt length and expected output size.
  This feeds into the Ethos (fair use) faculty — the system tracks
  cloud spend and can throttle when budgets are tight.

After a cloud response succeeds with high quality, the result is
compiled into a reflex (Pincher write-back). Next time the same
(or similar) prompt arrives, it's a KNOWN-KNOWN — sub-1ms, $0.
The cloud solution became a local reflex. The boundary moved.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("router.cloud_cascade")


# ---------------------------------------------------------------------------
# Cloud Model Profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CloudModel:
    """Description of a cloud model."""
    name: str
    provider: str             # "deepseek" | "deepinfra" | "cloudflare"
    specialty: str            # primary use case
    strength_types: tuple[str, ...]  # task types where it excels
    cost_per_1k_input: float  # USD per 1K input tokens
    cost_per_1k_output: float # USD per 1K output tokens
    expected_latency_s: float # typical round-trip
    max_tokens: int           # max output tokens
    reasoning: str = ""


# Cloud model registry
DEEPSEEK_V3 = CloudModel(
    name="deepseek-chat",
    provider="deepseek",
    specialty="reasoning",
    strength_types=("analytical", "problem_solving", "reflection", "causal",
                    "code"),
    cost_per_1k_input=0.00027,
    cost_per_1k_output=0.00110,
    expected_latency_s=15.0,
    max_tokens=8192,
    reasoning="Deep reasoning, planning, multi-step analysis",
)

QWEN_CODER_480B = CloudModel(
    name="Qwen/Qwen3-Coder-480B",
    provider="deepinfra",
    specialty="code_generation",
    strength_types=("code", "problem_solving", "analytical"),
    cost_per_1k_input=0.00060,
    cost_per_1k_output=0.00120,
    expected_latency_s=12.0,
    max_tokens=8192,
    reasoning="Production-quality code generation, debugging, refactoring",
)

HERMES_405B = CloudModel(
    name="NousResearch/Hermes-3-Llama-3.1-405B",
    provider="deepinfra",
    specialty="creative",
    strength_types=("creative", "emotional", "social", "narrative",
                    "reflection"),
    cost_per_1k_input=0.00080,
    cost_per_1k_output=0.00120,
    expected_latency_s=20.0,
    max_tokens=8192,
    reasoning="Creative voice, character personality, nuanced emotional content",
)

CF_LLAMA_8B = CloudModel(
    name="@cf/meta/llama-3.1-8b-instruct",
    provider="cloudflare",
    specialty="overflow",
    strength_types=("general", "instructional"),
    cost_per_1k_input=0.0,   # free tier (10K neurons/day)
    cost_per_1k_output=0.0,
    expected_latency_s=3.0,
    max_tokens=2048,
    reasoning="Free overflow model, decent quality within Workers AI quota",
)

ALL_CLOUD_MODELS = {
    DEEPSEEK_V3.name: DEEPSEEK_V3,
    QWEN_CODER_480B.name: QWEN_CODER_480B,
    HERMES_405B.name: HERMES_405B,
    CF_LLAMA_8B.name: CF_LLAMA_8B,
}


# ---------------------------------------------------------------------------
# Cost Estimation
# ---------------------------------------------------------------------------

def estimate_cloud_cost(
    model: CloudModel,
    prompt: str,
    expected_output_tokens: int = 500,
) -> float:
    """
    Estimate the USD cost of a cloud inference call.

    Uses character-based heuristic for input token count:
    1 token ≈ 4 characters (rough but conservative).
    """
    input_tokens = len(prompt) / 4
    cost = (
        (input_tokens / 1000) * model.cost_per_1k_input +
        (expected_output_tokens / 1000) * model.cost_per_1k_output
    )
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Cloud Model Selection Result
# ---------------------------------------------------------------------------

@dataclass
class CloudModelSelection:
    """Result of cloud model selection."""
    name: str
    provider: str
    estimated_cost: float
    expected_latency_s: float
    reasoning: str
    specialty: str = ""


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------

class CloudBudget:
    """
    Tracks cloud spending over a sliding window.

    The system has a daily budget (default $1.00). When the budget
    is exceeded, cloud requests are suppressed and the system falls
    back to local-only (degraded but functional).
    """

    def __init__(self, daily_budget_usd: float = 1.0):
        self.daily_budget = daily_budget_usd
        self._date = ""
        self._spent: float = 0.0

    def _reset_if_new_day(self):
        today = time.strftime("%Y-%m-%d")
        if self._date != today:
            if self._date:
                logger.info("Cloud budget reset: %s spent $%.4f, new day",
                           self._date, self._spent)
            self._date = today
            self._spent = 0.0

    def remaining(self) -> float:
        self._reset_if_new_day()
        return max(0.0, self.daily_budget - self._spent)

    def spend(self, amount: float):
        self._reset_if_new_day()
        self._spent += amount
        if self._spent > self.daily_budget:
            logger.warning("Cloud budget exceeded: $%.4f / $%.2f",
                          self._spent, self.daily_budget)

    def is_exhausted(self) -> bool:
        return self.remaining() <= 0.0

    def stats(self) -> dict:
        return {
            "daily_budget": self.daily_budget,
            "spent_today": round(self._spent, 6),
            "remaining": round(self.remaining(), 6),
            "exhausted": self.is_exhausted(),
        }


# ---------------------------------------------------------------------------
# Cloud Cascade
# ---------------------------------------------------------------------------

class CloudCascade:
    """
    The cloud escalation path.

    Given that a request is UNKNOWN-UNKNOWN, select the best cloud
    model and execute the inference.

    Selection logic:
      1. Match task type to model specialty
      2. Check budget availability
      3. Prefer cheaper models when quality difference is small
      4. Fall back to Cloudflare free tier if budget exhausted

    The cascade does NOT execute the inference itself — it returns
    a CloudModelSelection that the caller uses to make the actual
    API call (through the existing scheduler/cloud_bridge or
    directly). This separation lets the cascade be tested without
    network access.
    """

    def __init__(self, budget: CloudBudget | None = None):
        self.budget = budget or CloudBudget()

    def select_model(
        self,
        prompt: str,
        assessment: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> CloudModelSelection:
        """
        Select the best cloud model for this prompt.

        The selection considers:
          - Task type → model specialty match
          - Budget constraints
          - Prompt characteristics (code? creative? analytical?)
        """
        context = context or {}
        task_type = assessment.get("task_type", "general")

        # Score each cloud model for this task
        scores: list[tuple[float, CloudModel]] = []
        for model in ALL_CLOUD_MODELS.values():
            score = self._score_model(model, task_type, prompt)
            scores.append((score, model))

        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_model = scores[0]

        # Budget check
        estimated_cost = estimate_cloud_cost(best_model, prompt)
        if self.budget.is_exhausted():
            # Fall back to free Cloudflare model
            best_model = CF_LLAMA_8B
            estimated_cost = 0.0
            reasoning = (
                f"Budget exhausted, falling back to free Cloudflare model "
                f"({CF_LLAMA_8B.name})"
            )
        else:
            reasoning = (
                f"{best_model.name} selected for '{task_type}' task "
                f"(score={best_score:.3f}, cost≈${estimated_cost:.4f}, "
                f"specialty={best_model.specialty})"
            )

        return CloudModelSelection(
            name=best_model.name,
            provider=best_model.provider,
            estimated_cost=estimated_cost,
            expected_latency_s=best_model.expected_latency_s,
            reasoning=reasoning,
            specialty=best_model.specialty,
        )

    def _score_model(
        self,
        model: CloudModel,
        task_type: str,
        prompt: str,
    ) -> float:
        """
        Score a cloud model's suitability for a given task.

        Higher = better match.
        """
        # Base score from specialty match
        if task_type in model.strength_types:
            base = 0.90
        elif task_type == "general":
            base = 0.50
        else:
            base = 0.40

        # Specialty boost
        specialty_match = {
            "reasoning": ("analytical", "problem_solving", "reflection",
                          "causal"),
            "code_generation": ("code", "problem_solving"),
            "creative": ("creative", "emotional", "social", "narrative"),
            "overflow": (),  # no specialty boost
        }
        if task_type in specialty_match.get(model.specialty, ()):
            base = max(base, 0.85)

        # Cost penalty (cheaper is better, all else equal)
        total_cost = model.cost_per_1k_input + model.cost_per_1k_output
        if total_cost == 0:
            cost_factor = 1.10  # free is great
        else:
            cost_factor = max(0.70, 1.0 - total_cost * 50)

        # Latency penalty (faster is better)
        latency_factor = max(0.70, 1.0 - (model.expected_latency_s / 60.0))

        return base * cost_factor * latency_factor

    def record_spend(self, amount: float):
        """Record a cloud spend."""
        self.budget.spend(amount)

    def stats(self) -> dict:
        return {
            "budget": self.budget.stats(),
            "models": {
                name: {
                    "provider": m.provider,
                    "specialty": m.specialty,
                    "cost_per_1k_input": m.cost_per_1k_input,
                    "cost_per_1k_output": m.cost_per_1k_output,
                }
                for name, m in ALL_CLOUD_MODELS.items()
            },
        }
