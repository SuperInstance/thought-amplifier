"""
router.py — The Core Cognitive Router

Casey's three epistemic states, made executable:

  1. KNOWN-KNOWN     — We've seen this before and know the answer.
                       Reflex cache hit. Sub-1ms. $0 cost.
                       (Pincher pattern: vector DB is the runtime)

  2. KNOWN-UNKNOWN   — We know what kind of processing is needed but
                       haven't processed THIS exact request. Route to
                       the fastest sufficient local model.
                       ~1-3s latency. $0 cost.
                       (Lever Runner 3-gate cascade)

  3. UNKNOWN-UNKNOWN — No pattern exists. The puzzle pieces don't fit.
                       Cascade to a LARGER model of understanding.
                       ~10-30s latency. Paid cost.
                       Worth it because it creates NEW knowledge.

The profound part:
  - State 3 solutions become State 1 reflexes over time (Pincher write-back)
  - The boundary between State 2 and State 3 EVOLVES
  - Known-unknowns grow, unknown-unknowns shrink
  - The router itself LEARNS which routing decisions were correct

Integration with the existing scheduler:
  The scheduler handles GPU serialization and fair-use. The router
  sits IN FRONT of the scheduler — it decides WHERE a request goes.
  The scheduler decides WHEN it runs. Together they form the full
  Logos faculty: what to do, and when to do it.

  router → scheduler → model

  The router enriches InferenceRequest with routing metadata
  (epistemic_state, target, expected latency, cost estimate)
  and optionally overrides the model selection.
"""

from __future__ import annotations

import logging
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal

logger = logging.getLogger("router")


class EpistemicState(str, Enum):
    """The three epistemic states of an inference request."""
    KNOWN_KNOWN = "KNOWN-KNOWN"
    KNOWN_UNKNOWN = "KNOWN-UNKNOWN"
    UNKNOWN_UNKNOWN = "UNKNOWN-UNKNOWN"

    @property
    def is_reflex(self) -> bool:
        return self == EpistemicState.KNOWN_KNOWN

    @property
    def is_local(self) -> bool:
        return self == EpistemicState.KNOWN_UNKNOWN

    @property
    def is_cloud(self) -> bool:
        return self == EpistemicState.UNKNOWN_UNKNOWN


class RouteTarget(str, Enum):
    """Where the request should be executed."""
    REFLEX = "reflex"
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(frozen=True)
class RouteDecision:
    """
    The router's verdict on a request.

    This is an immutable record of WHY a request was routed where it
    was. It travels with the request through the scheduler so that
    downstream components (trust tracker, boundary tracker) can
    evaluate whether the routing was correct.
    """
    target: RouteTarget
    epistemic_state: EpistemicState
    model: str | None = None
    reflex_text: str | None = None
    confidence: float = 0.0
    latency_expectation_ms: float = 0.0       # estimated
    cost_estimate: float = 0.0                 # USD
    should_compile_reflex: bool = False        # learn from this response
    reasoning: str = ""                        # human-readable rationale
    signals: dict[str, float] = field(default_factory=dict)
    decided_at: float = field(default_factory=time.time)

    @property
    def is_free(self) -> bool:
        """True if this routing costs nothing (reflex or local)."""
        return self.target in (RouteTarget.REFLEX, RouteTarget.LOCAL)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.value,
            "epistemic_state": self.epistemic_state.value,
            "model": self.model,
            "confidence": round(self.confidence, 4),
            "latency_expectation_ms": round(self.latency_expectation_ms, 1),
            "cost_estimate": round(self.cost_estimate, 6),
            "should_compile_reflex": self.should_compile_reflex,
            "reasoning": self.reasoning,
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
        }


# ---------------------------------------------------------------------------
# Reflex Cache (simple in-process; backed by boundary_tracker for persistence)
# ---------------------------------------------------------------------------

@dataclass
class ReflexEntry:
    """A cached reflex — a known answer to a known question."""
    text: str
    confidence: float
    prompt_hash: str
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0
    last_hit: float = field(default_factory=time.time)
    source: str = "local"  # "local" | "cloud:deepseek" | "cloud:qwen-coder" etc.
    max_consecutive_uses: int = 50  # escape hatch — forced re-check after N hits
    _consecutive: int = 0

    def can_use(self) -> bool:
        """Check if this reflex is still usable (escape hatch check)."""
        return self._consecutive < self.max_consecutive_uses

    def record_hit(self) -> bool:
        """Record a hit. Returns True if the reflex can still be used."""
        self.hit_count += 1
        self._consecutive += 1
        self.last_hit = time.time()
        return self.can_use()

    def reset_consecutive(self):
        """Reset the consecutive counter (after a re-verification)."""
        self._consecutive = 0


class ReflexCache:
    """
    In-process reflex cache. Keyed by prompt hash.

    The escape hatch is critical: after max_consecutive_uses identical
    dispatches, the reflex is force-invalidated. This ensures the system
    keeps sampling evidence to correct wrong reflexes. Without it, a
    high-confidence wrong answer becomes a permanent blind spot.
    """

    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        self._cache: dict[str, ReflexEntry] = {}

    def _hash(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    def check(self, prompt: str) -> ReflexEntry | None:
        """Check for a reflex hit. Returns None if no hit or escape hatch triggered."""
        h = self._hash(prompt)
        entry = self._cache.get(h)
        if entry is None:
            return None
        if entry.confidence < self.confidence_threshold:
            return None
        if not entry.can_use():
            logger.info("Reflex escape hatch triggered for %s (N=%d consecutive)",
                       h, entry._consecutive)
            entry.reset_consecutive()
            return None
        entry.record_hit()
        return entry

    def store(self, prompt: str, text: str, confidence: float,
              source: str = "local"):
        """Store a new reflex or update an existing one."""
        h = self._hash(prompt)
        self._cache[h] = ReflexEntry(
            text=text,
            confidence=min(0.95, max(0.05, confidence)),
            prompt_hash=h,
            source=source,
        )
        logger.debug("Stored reflex %s (confidence=%.3f, source=%s)",
                     h, confidence, source)

    def update_confidence(self, prompt: str, success: bool):
        """
        Adjust a reflex's confidence after observing an outcome.

        Pincher's asymmetric update, additive form:
          success: +0.05 * (1 - c)   [gains shrink as confidence rises]
          failure: -0.10 * c          [losses shrink as confidence falls]
          clamped to [0.05, 0.95]
        """
        h = self._hash(prompt)
        entry = self._cache.get(h)
        if entry is None:
            return
        c = entry.confidence
        if success:
            c = c + 0.05 * (1.0 - c)
        else:
            c = c - 0.10 * c
        c = max(0.05, min(0.95, c))
        entry.confidence = c
        if c < self.confidence_threshold:
            logger.info("Reflex %s dropped below threshold (%.3f)", h, c)

    def size(self) -> int:
        return len(self._cache)

    def stats(self) -> dict:
        total_hits = sum(e.hit_count for e in self._cache.values())
        avg_conf = (sum(e.confidence for e in self._cache.values()) /
                    max(1, len(self._cache)))
        active = sum(1 for e in self._cache.values()
                     if e.confidence >= self.confidence_threshold)
        return {
            "total_reflexes": len(self._cache),
            "active_reflexes": active,
            "total_hits": total_hits,
            "avg_confidence": round(avg_conf, 4),
        }


# ---------------------------------------------------------------------------
# The Cognitive Router
# ---------------------------------------------------------------------------

class CognitiveRouter:
    """
    The main routing interface. Given a request (prompt + context),
    decide:

      1. Is this a KNOWN-KNOWN? → reflex cache hit
      2. Is this a KNOWN-UNKNOWN? → local model (Granite/Qwen)
      3. Is this an UNKNOWN-UNKNOWN? → cloud cascade

    The router is stateless across requests except for the reflex cache
    and the confidence history. It does NOT maintain conversation state
    — that's the caller's job. The router is a pure function from
    (prompt, context) → RouteDecision.

    Usage:

        router = CognitiveRouter()
        decision = router.route("What is 2+2?")
        if decision.target == RouteTarget.REFLEX:
            print(decision.reflex_text)  # "4"
        elif decision.target == RouteTarget.LOCAL:
            scheduler.submit(prompt, model=decision.model, ...)
        elif decision.target == RouteTarget.CLOUD:
            cloud_cascade.escalate(prompt, decision.model, ...)
    """

    # Thresholds — tuned from experimental data
    REFLEX_CONFIDENCE = 0.85    # above this → KNOWN-KNOWN
    LOCAL_CONFIDENCE = 0.55     # above this → KNOWN-UNKNOWN (local sufficient)
    # Below LOCAL_CONFIDENCE → UNKNOWN-UNKNOWN (cloud cascade)

    # Estimated latencies (from EXP2/EXP3 GPU benchmarks)
    REFLEX_LATENCY_MS = 0.5
    GRANITE_LATENCY_MS = 1100   # ~1.1s at 76.8 tok/s
    QWEN_LATENCY_MS = 500       # ~0.5s at 178.8 tok/s
    CLOUD_LATENCY_MS = 15_000   # ~10-30s depending on model

    def __init__(
        self,
        reflex_cache: ReflexCache | None = None,
        confidence_assessor: "ConfidenceAssessor | None" = None,
        model_selector: "LocalModelSelector | None" = None,
        cloud_cascade: "CloudCascade | None" = None,
        boundary_tracker: "BoundaryTracker | None" = None,
    ):
        self.reflex_cache = reflex_cache or ReflexCache()
        # Import here to avoid circular import at module load
        from .confidence import ConfidenceAssessor
        from .model_selector import LocalModelSelector
        from .cloud_cascade import CloudCascade
        from .boundary_tracker import BoundaryTracker

        self.assessor = confidence_assessor or ConfidenceAssessor()
        self.model_selector = model_selector or LocalModelSelector()
        self.cloud = cloud_cascade or CloudCascade()
        self.boundary = boundary_tracker or BoundaryTracker()

    def route(
        self,
        prompt: str,
        agent: str = "default",
        context: dict[str, Any] | None = None,
        force_target: RouteTarget | None = None,
    ) -> RouteDecision:
        """
        Make a routing decision for a prompt.

        Args:
            prompt: The input text
            agent: Which agent is making the request
            context: Additional context (conversation history, task type, etc.)
            force_target: Override the routing decision (for testing or
                         explicit user intent)

        Returns:
            A RouteDecision telling the caller where and how to execute.
        """
        context = context or {}

        # --- Force override (testing or explicit intent) ---
        if force_target:
            return self._force_route(prompt, force_target, context)

        # --- Gate 1: Reflex cache (KNOWN-KNOWN) ---
        reflex = self.reflex_cache.check(prompt)
        if reflex:
            decision = RouteDecision(
                target=RouteTarget.REFLEX,
                epistemic_state=EpistemicState.KNOWN_KNOWN,
                reflex_text=reflex.text,
                confidence=reflex.confidence,
                latency_expectation_ms=self.REFLEX_LATENCY_MS,
                cost_estimate=0.0,
                reasoning=f"Reflex cache hit (confidence={reflex.confidence:.3f}, "
                         f"hits={reflex.hit_count}, source={reflex.source})",
                signals={"reflex_confidence": reflex.confidence},
            )
            self.boundary.record(decision)
            return decision

        # --- Gate 2: Confidence assessment (KNOWN-UNKNOWN vs UNKNOWN-UNKNOWN) ---
        assessment = self.assessor.assess(prompt, agent, context)

        if assessment["confidence"] >= self.LOCAL_CONFIDENCE:
            # KNOWN-UNKNOWN: local model can handle this
            model = self.model_selector.select(prompt, assessment, context)

            decision = RouteDecision(
                target=RouteTarget.LOCAL,
                epistemic_state=EpistemicState.KNOWN_UNKNOWN,
                model=model.name,
                confidence=assessment["confidence"],
                latency_expectation_ms=model.expected_latency_ms,
                cost_estimate=0.0,
                reasoning=f"Local confidence {assessment['confidence']:.3f} "
                         f">= {self.LOCAL_CONFIDENSE_STR()}; "
                         f"selected {model.name} "
                         f"({model.reasoning})",
                signals=assessment["signals"],
            )
            self.boundary.record(decision)
            return decision

        # --- Gate 3: Cloud cascade (UNKNOWN-UNKNOWN) ---
        cloud_model = self.cloud.select_model(prompt, assessment, context)

        decision = RouteDecision(
            target=RouteTarget.CLOUD,
            epistemic_state=EpistemicState.UNKNOWN_UNKNOWN,
            model=cloud_model.name,
            confidence=assessment["confidence"],
            latency_expectation_ms=self.CLOUD_LATENCY_MS,
            cost_estimate=cloud_model.estimated_cost,
            should_compile_reflex=True,  # learn from cloud response
            reasoning=f"Local confidence {assessment['confidence']:.3f} "
                     f"< {self.LOCAL_CONFIDENSE_STR()}; "
                     f"unknown territory, cascading to {cloud_model.name} "
                     f"({cloud_model.reasoning})",
            signals=assessment["signals"],
        )
        self.boundary.record(decision)
        return decision

    def record_outcome(
        self,
        prompt: str,
        decision: RouteDecision,
        success: bool,
        quality: float = 0.0,
        response_text: str | None = None,
    ):
        """
        Feed back the outcome of a routing decision.

        This is the learning loop:
        - Reflex hits that were wrong → confidence drops
        - Reflex hits that were right → confidence rises
        - Cloud responses that succeeded → compile into reflex
        - Local failures → boundary tracker logs the escalation point
        """
        # Update reflex confidence if this was a reflex hit
        if decision.target == RouteTarget.REFLEX:
            self.reflex_cache.update_confidence(prompt, success)
            self.boundary.record_outcome(decision, success, quality)
            return

        # Cloud responses get compiled into reflexes (Pincher write-back)
        if decision.target == RouteTarget.CLOUD and decision.should_compile_reflex:
            if success and quality > 0.6 and response_text:
                # Compile: the cloud answer becomes a reflex
                # Confidence starts low — it has to earn trust
                initial_confidence = 0.55 + quality * 0.15  # 0.55 - 0.70
                self.reflex_cache.store(
                    prompt, response_text,
                    confidence=initial_confidence,
                    source=f"cloud:{decision.model}",
                )
                logger.info("Compiled cloud response into reflex "
                           "(quality=%.2f, initial_confidence=%.3f)",
                           quality, initial_confidence)

        # Record in boundary tracker
        self.boundary.record_outcome(decision, success, quality)

    def get_boundary_report(self) -> dict:
        """Get the current state of the knowledge frontier."""
        return self.boundary.report()

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            "reflex_cache": self.reflex_cache.stats(),
            "boundary": self.boundary.report(),
            "thresholds": {
                "reflex_confidence": self.REFLEX_CONFIDENCE,
                "local_confidence": self.LOCAL_CONFIDENCE,
            },
        }

    # --- Internal helpers ---

    def LOCAL_CONFIDENSE_STR(self) -> str:
        """Human-readable local confidence threshold."""
        return f"{self.LOCAL_CONFIDENCE}"

    def _force_route(
        self,
        prompt: str,
        target: RouteTarget,
        context: dict[str, Any],
    ) -> RouteDecision:
        """Create a forced routing decision (for testing/explicit intent)."""
        if target == RouteTarget.REFLEX:
            reflex = self.reflex_cache.check(prompt)
            return RouteDecision(
                target=RouteTarget.REFLEX,
                epistemic_state=EpistemicState.KNOWN_KNOWN,
                reflex_text=reflex.text if reflex else None,
                confidence=reflex.confidence if reflex else 0.0,
                latency_expectation_ms=self.REFLEX_LATENCY_MS,
                reasoning="Forced reflex lookup",
            )
        if target == RouteTarget.LOCAL:
            model = self.model_selector.select(prompt, {"confidence": 0.7}, context)
            return RouteDecision(
                target=RouteTarget.LOCAL,
                epistemic_state=EpistemicState.KNOWN_UNKNOWN,
                model=model.name,
                confidence=0.7,
                latency_expectation_ms=model.expected_latency_ms,
                reasoning=f"Forced local ({model.name})",
            )
        # Cloud
        cloud_model = self.cloud.select_model(prompt, {"confidence": 0.3}, context)
        return RouteDecision(
            target=RouteTarget.CLOUD,
            epistemic_state=EpistemicState.UNKNOWN_UNKNOWN,
            model=cloud_model.name,
            confidence=0.3,
            latency_expectation_ms=self.CLOUD_LATENCY_MS,
            cost_estimate=cloud_model.estimated_cost,
            should_compile_reflex=True,
            reasoning=f"Forced cloud ({cloud_model.name})",
        )
