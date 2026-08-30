"""
model_selector.py — local model selection.

Given that a request is going local (KNOWN-UNKNOWN), picks between the two
installed Ollama models and returns a ModelProfile:

  granite3.1-dense:2b — 76.8 tok/s, quality-first on analytical/reasoning
                        tasks, never breaks character
  qwen2.5:0.5b        — 178.8 tok/s, better on creative/emotional tasks,
                        sometimes breaks character

Selection order: a character-consistency requirement forces Granite; an
URGENT request without a high quality bar forces Qwen; otherwise a learned
per-task-type EMA score (seeded from MODEL_CAPABILITY, nudged by urgency
and quality-requirement multipliers) decides, with ties going to Granite.
record_outcome() updates the EMA (α=0.05).

Does NOT:
  - run inference or contact Ollama
  - choose more than these two models
  - implement the mid-response hot-swap the older design contemplated
  - persist learned scores across restarts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .confidence import MODEL_CAPABILITY, SuccessHistory

logger = logging.getLogger("router.model_selector")


# ---------------------------------------------------------------------------
# Model Descriptions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelProfile:
    """Static description of a local model."""
    name: str
    parameter_count: str        # "2B" or "0.5B"
    quantization: str           # "Q4_K_M"
    size_gb: float              # disk size
    speed_toks: float           # tokens/second on RTX 4050
    expected_latency_ms: float  # average response time
    strengths: tuple[str, ...]  # task types where it excels
    weaknesses: tuple[str, ...] # task types where it struggles
    breaks_character: bool      # does it ever say "As an AI"?
    reasoning: str = ""


# From EXP3 GPU RERUN — measured data
GRANITE = ModelProfile(
    name="granite3.1-dense:2b",
    parameter_count="2B",
    quantization="Q4_K_M",
    size_gb=1.57,
    speed_toks=76.8,
    expected_latency_ms=1100,
    strengths=("analytical", "problem_solving", "reflection", "causal",
               "code", "spatial"),
    weaknesses=("creative", "emotional"),
    breaks_character=False,
    reasoning="Higher quality on analytical tasks; never breaks character",
)

QWEN = ModelProfile(
    name="qwen2.5:0.5b",
    parameter_count="0.5B",
    quantization="Q4_K_M",
    size_gb=0.398,
    speed_toks=178.8,
    expected_latency_ms=500,
    strengths=("creative", "emotional", "instructional", "social",
               "narrative"),
    weaknesses=("analytical", "problem_solving", "code", "reflection"),
    breaks_character=True,
    reasoning="Faster and better at creative/emotional tasks; may break character",
)

ALL_MODELS = {GRANITE.name: GRANITE, QWEN.name: QWEN}


# ---------------------------------------------------------------------------
# Selection Decision
# ---------------------------------------------------------------------------

@dataclass
class ModelSelection:
    """Result of model selection."""
    name: str                   # model name for Ollama
    expected_latency_ms: float
    confidence: float           # how confident we are in this choice
    reasoning: str
    alternative: str | None = None  # fallback model if this one fails


# ---------------------------------------------------------------------------
# Local Model Selector
# ---------------------------------------------------------------------------

class LocalModelSelector:
    """
    Selects the best local model for a given request.

    Strategy:
      1. If task type clearly favors one model → use it
      2. If urgency is URGENT → prefer Qwen (faster)
      3. If character consistency matters → prefer Granite (never breaks)
      4. If historical data favors one model → use it
      5. Default → Granite (quality-first at GPU speeds)

    The selector learns from outcomes: if Granite consistently does
    better on a task type, its selection weight for that type increases.
    """

    def __init__(self, success_history: SuccessHistory | None = None):
        self.history = success_history or SuccessHistory()
        # Per-task-type model preference (learned)
        self._model_ema: dict[str, dict[str, float]] = {}
        # Initialize from priors
        for model_name, caps in MODEL_CAPABILITY.items():
            for task_type, cap in caps.items():
                if task_type not in self._model_ema:
                    self._model_ema[task_type] = {}
                self._model_ema[task_type][model_name] = cap

    def select(
        self,
        prompt: str,
        assessment: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ModelProfile:
        """
        Select the best local model for this prompt.

        Returns a ModelProfile with the selected model.
        """
        context = context or {}
        task_type = assessment.get("task_type", "general")

        # Override factors from context
        urgency = context.get("urgency", "NORMAL")  # URGENT, HIGH, NORMAL, LOW
        requires_character = context.get("requires_character", False)
        quality_requirement = context.get("quality_requirement", "normal")
        # "low" = quick filler, "normal" = standard, "high" = best possible

        # --- Hard rules first ---

        # Character consistency requirement → Granite (never breaks character)
        if requires_character:
            return ModelProfile(
                name=GRANITE.name,
                parameter_count=GRANITE.parameter_count,
                quantization=GRANITE.quantization,
                size_gb=GRANITE.size_gb,
                speed_toks=GRANITE.speed_toks,
                expected_latency_ms=GRANITE.expected_latency_ms,
                strengths=GRANITE.strengths,
                weaknesses=GRANITE.weaknesses,
                breaks_character=GRANITE.breaks_character,
                reasoning="Character consistency required → Granite (never breaks character)",
            )

        # Urgent + low quality requirement → Qwen (fastest)
        if urgency == "URGENT" and quality_requirement != "high":
            return ModelProfile(
                name=QWEN.name,
                parameter_count=QWEN.parameter_count,
                quantization=QWEN.quantization,
                size_gb=QWEN.size_gb,
                speed_toks=QWEN.speed_toks,
                expected_latency_ms=QWEN.expected_latency_ms,
                strengths=QWEN.strengths,
                weaknesses=QWEN.weaknesses,
                breaks_character=QWEN.breaks_character,
                reasoning="URGENT + no high quality bar → Qwen (fastest at 178.8 tok/s)",
            )

        # --- Soft scoring ---

        granite_score = self._model_ema.get(task_type, {}).get(GRANITE.name, 0.5)
        qwen_score = self._model_ema.get(task_type, {}).get(QWEN.name, 0.5)

        # Urgency modifier (URGENT → slight Qwen boost)
        if urgency == "URGENT":
            qwen_score *= 1.10
        elif urgency in ("LOW", "IDLE"):
            # Low urgency → prefer quality (Granite)
            granite_score *= 1.05

        # Quality requirement modifier
        if quality_requirement == "high":
            granite_score *= 1.15
        elif quality_requirement == "low":
            qwen_score *= 1.10

        # Select
        if granite_score >= qwen_score:
            model = GRANITE
            reasoning = (
                f"Granite selected for '{task_type}' task "
                f"(score={granite_score:.3f} vs Qwen={qwen_score:.3f})"
            )
        else:
            model = QWEN
            reasoning = (
                f"Qwen selected for '{task_type}' task "
                f"(score={qwen_score:.3f} vs Granite={granite_score:.3f})"
            )

        return ModelProfile(
            name=model.name,
            parameter_count=model.parameter_count,
            quantization=model.quantization,
            size_gb=model.size_gb,
            speed_toks=model.speed_toks,
            expected_latency_ms=model.expected_latency_ms,
            strengths=model.strengths,
            weaknesses=model.weaknesses,
            breaks_character=model.breaks_character,
            reasoning=reasoning,
        )

    def record_outcome(
        self,
        task_type: str,
        model_name: str,
        success: bool,
        quality: float = 0.0,
    ):
        """
        Record a model outcome and update selection preferences.

        Uses EMA (α=0.05) — same slow adaptation as the rest of the system.
        """
        if task_type not in self._model_ema:
            self._model_ema[task_type] = {}
            for mn, caps in MODEL_CAPABILITY.items():
                self._model_ema[task_type][mn] = caps.get(task_type, 0.5)

        if model_name not in self._model_ema[task_type]:
            self._model_ema[task_type][model_name] = 0.5

        score = quality if quality > 0 else (1.0 if success else 0.0)
        prev = self._model_ema[task_type][model_name]
        self._model_ema[task_type][model_name] = prev + 0.05 * (score - prev)

        logger.debug("Model preference updated: %s/%s = %.3f → %.3f",
                     task_type, model_name, prev,
                     self._model_ema[task_type][model_name])

    def get_model_scores(self, task_type: str) -> dict[str, float]:
        """Get current model scores for a task type."""
        return dict(self._model_ema.get(task_type, {}))

    def stats(self) -> dict:
        return {
            tt: {mn: round(s, 4) for mn, s in scores.items()}
            for tt, scores in sorted(self._model_ema.items())
        }
