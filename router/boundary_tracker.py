"""
boundary_tracker.py — The Evolving Knowledge Frontier

The boundary between KNOWN-KNOWN, KNOWN-UNKNOWN, and UNKNOWN-UNKNOWN
is not static. It moves. This module tracks that movement.

The system's knowledge frontier is defined by the distribution of
requests across the three epistemic states over time:

  Time 0:    100% UNKNOWN-UNKNOWN (everything is new)
  Time 1h:   ~60% UNKNOWN-UNKNOWN, 30% KNOWN-UNKNOWN, 10% KNOWN-KNOWN
  Time 1day: ~40% UNKNOWN-UNKNOWN, 35% KNOWN-UNKNOWN, 25% KNOWN-KNOWN
  Time 1week: ~20% UNKNOWN-UNKNOWN, 30% KNOWN-UNKNOWN, 50% KNOWN-KNOWN

The exact trajectory depends on the workload. But the direction is
always the same: known grows, unknown shrinks. The production line
gets better at producing value.

This module provides:

1. REQUEST LOGGING
   Every routing decision is logged with its epistemic state, task
   type, model used, and outcome. This is the raw data for boundary
   tracking.

2. RATIO TRACKING
   The ratio of KNOWN to UNKNOWN over sliding windows. This should
   trend toward KNOWN over time. If it doesn't, something is wrong
   (the reflexes aren't compiling, or the workload keeps changing).

3. WRITE-BACK TRACKING
   When a cloud solution succeeds and gets compiled into a reflex,
   that's a boundary event — a piece of UNKNOWN became KNOWN. These
   events are the system's growth metric.

4. ROUTING ACCURACY
   Did the router make the right call? A KNOWN-UNKNOWN routing that
   produces low quality is a routing error (should have been cloud).
   A UNKNOWN-UNKNOWN that produces high quality is also a routing
   error (should have been local). The accuracy metric tracks how
   often the router's confidence assessment was correct.

5. COST EVOLUTION
   Average cost per request over time. As reflexes accumulate, the
   average cost should trend toward $0. This is the financial
   expression of the production line thesis: the hardware gets
   better at producing value (at $0 marginal cost).

Trust tracking: each routing decision has a confidence score. Over
time, we correlate confidence with actual outcomes. A well-calibrated
router has confidence ≈ success rate. If confidence > success rate,
the router is overconfident and needs adjustment.
"""

from __future__ import annotations

import logging
import math
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("router.boundary")


# ---------------------------------------------------------------------------
# Request Record
# ---------------------------------------------------------------------------

@dataclass
class RequestRecord:
    """A single routing decision and its outcome."""
    timestamp: float
    epistemic_state: str       # "KNOWN-KNOWN" | "KNOWN-UNKNOWN" | "UNKNOWN-UNKNOWN"
    target: str                # "reflex" | "local" | "cloud"
    task_type: str
    model: str | None
    confidence: float          # router's confidence at decision time
    cost_estimate: float       # estimated cost
    # Outcome (filled in later when result is known)
    success: bool | None = None
    quality: float | None = None
    actual_cost: float | None = None
    was_correct: bool | None = None  # was the routing decision correct?
    wrote_reflex: bool = False       # did this result compile into a reflex?


# ---------------------------------------------------------------------------
# Boundary Tracker
# ---------------------------------------------------------------------------

class BoundaryTracker:
    """
    Tracks the evolution of the knowledge frontier.

    Records every routing decision, computes rolling statistics, and
    provides insight into how the system is learning.

    The key insight: the boundary between states IS the system's
    knowledge frontier. Tracking its movement is tracking growth.
    """

    MAX_RECORDS = 10_000  # keep last 10K requests in memory

    def __init__(self):
        self._records: deque[RequestRecord] = deque(maxlen=self.MAX_RECORDS)
        self._reflex_writes: deque[float] = deque(maxlen=500)
        # Calibration tracking: (confidence, success) pairs per task type
        self._calibration: dict[str, list[tuple[float, bool]]] = {}

    def record(self, decision) -> None:
        """Record a routing decision (before outcome is known)."""
        rec = RequestRecord(
            timestamp=decision.decided_at,
            epistemic_state=decision.epistemic_state.value,
            target=decision.target.value,
            task_type=decision.signals.get("task_type", "unknown"),
            model=decision.model,
            confidence=decision.confidence,
            cost_estimate=decision.cost_estimate,
        )
        self._records.append(rec)

    def record_outcome(
        self,
        decision,
        success: bool,
        quality: float = 0.0,
    ) -> None:
        """Record the outcome of a routing decision."""
        if not self._records:
            return

        # Find the most recent matching record (search backwards)
        rec = None
        for r in reversed(self._records):
            if (r.epistemic_state == decision.epistemic_state.value and
                r.target == decision.target.value and
                abs(r.confidence - decision.confidence) < 0.01):
                rec = r
                break

        if rec is None:
            return

        rec.success = success
        rec.quality = quality
        rec.actual_cost = decision.cost_estimate

        # Determine if routing was correct
        rec.was_correct = self._evaluate_correctness(rec, success, quality)

        # Track reflex writes
        if (decision.should_compile_reflex and success and
            quality > 0.6):
            rec.wrote_reflex = True
            self._reflex_writes.append(time.time())

        # Update calibration tracking
        task_type = rec.task_type
        if task_type not in self._calibration:
            self._calibration[task_type] = []
        self._calibration[task_type].append((rec.confidence, success))
        # Keep last 200 per task type
        if len(self._calibration[task_type]) > 200:
            self._calibration[task_type] = self._calibration[task_type][-200:]

    def _evaluate_correctness(
        self,
        rec: RequestRecord,
        success: bool,
        quality: float,
    ) -> bool:
        """
        Evaluate whether a routing decision was correct.

        KNOWN-KNOWN (reflex): correct if the reflex was useful
          (quality > 0.5). Incorrect if quality was poor (the reflex
          was wrong and should have been re-processed).

        KNOWN-UNKNOWN (local): correct if the local model produced
          adequate quality (quality > 0.4). Incorrect if quality was
          so low it should have escalated to cloud.

        UNKNOWN-UNKNOWN (cloud): correct if the cloud model produced
          good quality (quality > 0.5). It's also "correct" if the
          quality was low but the local model would have done worse
          (we can't know this, so we use a low bar). Incorrect if
          quality was high and the local model probably could have
          handled it (over-escalation).
        """
        if rec.epistemic_state == "KNOWN-KNOWN":
            return quality > 0.5
        elif rec.epistemic_state == "KNOWN-UNKNOWN":
            return quality > 0.4
        elif rec.epistemic_state == "UNKNOWN-UNKNOWN":
            # Over-escalation: high quality on cloud suggests local
            # could have handled it. But we're conservative — cloud
            # producing high quality is always "acceptable."
            # Only mark incorrect if quality was very high (>0.8)
            # AND confidence was low (borderline decision).
            if quality > 0.8 and rec.confidence > 0.40:
                return False  # likely over-escalation
            return quality > 0.3
        return True

    # --- Statistics ---

    def _window_records(self, window_s: float = 3600.0) -> list[RequestRecord]:
        """Get records from the last window_s seconds."""
        cutoff = time.time() - window_s
        return [r for r in self._records if r.timestamp >= cutoff]

    def state_distribution(self, window_s: float = 3600.0) -> dict[str, float]:
        """
        Distribution of epistemic states over a time window.

        Returns dict mapping state name → proportion (0.0 to 1.0).
        This is the core metric of the knowledge frontier.
        """
        records = self._window_records(window_s)
        if not records:
            return {"KNOWN-KNOWN": 0.0, "KNOWN-UNKNOWN": 0.0, "UNKNOWN-UNKNOWN": 0.0}

        counts = Counter(r.epistemic_state for r in records)
        total = len(records)
        return {
            state: round(counts.get(state, 0) / total, 4)
            for state in ["KNOWN-KNOWN", "KNOWN-UNKNOWN", "UNKNOWN-UNKNOWN"]
        }

    def routing_accuracy(self, window_s: float = 3600.0) -> float | None:
        """
        What fraction of routing decisions were correct?

        Returns None if no outcomes have been recorded yet.
        """
        records = [
            r for r in self._window_records(window_s)
            if r.was_correct is not None
        ]
        if not records:
            return None
        correct = sum(1 for r in records if r.was_correct)
        return round(correct / len(records), 4)

    def calibration_error(self, task_type: str | None = None) -> float | None:
        """
        How well-calibrated is the router's confidence?

        Perfect calibration: confidence = success rate.
        Returns the mean absolute calibration error.
        Lower is better.
        """
        pairs: list[tuple[float, bool]] = []
        if task_type:
            pairs = self._calibration.get(task_type, [])
        else:
            for tt_pairs in self._calibration.values():
                pairs.extend(tt_pairs)

        if len(pairs) < 10:
            return None

        # Bin by confidence (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
        bins: dict[str, list[tuple[float, bool]]] = {}
        for conf, success in pairs:
            bin_key = f"{int(conf * 10) / 10:.1f}"
            if bin_key not in bins:
                bins[bin_key] = []
            bins[bin_key].append((conf, success))

        total_error = 0.0
        total_count = 0
        for bin_key, bin_pairs in bins.items():
            avg_conf = sum(c for c, _ in bin_pairs) / len(bin_pairs)
            success_rate = sum(1 for _, s in bin_pairs if s) / len(bin_pairs)
            total_error += abs(avg_conf - success_rate) * len(bin_pairs)
            total_count += len(bin_pairs)

        return round(total_error / max(1, total_count), 4)

    def reflex_growth_rate(self, window_s: float = 3600.0) -> float:
        """
        Rate of reflex compilation (write-backs per hour).
        This is how fast UNKNOWN is becoming KNOWN.
        """
        cutoff = time.time() - window_s
        writes = sum(1 for ts in self._reflex_writes if ts >= cutoff)
        hours = window_s / 3600.0
        return round(writes / max(0.01, hours), 2)

    def avg_cost_trend(self, window_s: float = 3600.0) -> dict:
        """
        Average cost metrics over a time window.

        As reflexes accumulate, avg_cost should trend toward $0.
        """
        records = self._window_records(window_s)
        if not records:
            return {"avg_cost": 0.0, "total_cost": 0.0, "free_ratio": 0.0}

        costs = [r.cost_estimate for r in records]
        total = sum(costs)
        avg = total / len(records)
        free = sum(1 for c in costs if c == 0.0) / len(records)

        return {
            "avg_cost": round(avg, 6),
            "total_cost": round(total, 6),
            "free_ratio": round(free, 4),
        }

    def task_type_breakdown(self, window_s: float = 3600.0) -> dict[str, dict]:
        """Breakdown by task type showing state distribution per type."""
        records = self._window_records(window_s)
        by_type: dict[str, list[RequestRecord]] = {}
        for r in records:
            tt = r.task_type or "unknown"
            if tt not in by_type:
                by_type[tt] = []
            by_type[tt].append(r)

        result = {}
        for tt, recs in sorted(by_type.items()):
            counts = Counter(r.epistemic_state for r in recs)
            total = len(recs)
            outcomes = [r for r in recs if r.success is not None]
            avg_quality = (
                sum(r.quality for r in outcomes if r.quality is not None) /
                max(1, len(outcomes))
            )
            result[tt] = {
                "count": total,
                "known_known": round(counts.get("KNOWN-KNOWN", 0) / total, 3),
                "known_unknown": round(counts.get("KNOWN-UNKNOWN", 0) / total, 3),
                "unknown_unknown": round(counts.get("UNKNOWN-UNKNOWN", 0) / total, 3),
                "avg_quality": round(avg_quality, 3) if outcomes else None,
            }
        return result

    def report(self) -> dict:
        """
        Full boundary report.

        This is the system's growth dashboard — a snapshot of how
        the knowledge frontier has moved.
        """
        # Short and long term distributions
        dist_1h = self.state_distribution(3600)
        dist_24h = self.state_distribution(86400)

        return {
            "state_distribution_1h": dist_1h,
            "state_distribution_24h": dist_24h,
            "routing_accuracy_1h": self.routing_accuracy(3600),
            "routing_accuracy_24h": self.routing_accuracy(86400),
            "calibration_error": self.calibration_error(),
            "reflex_growth_rate_per_h": self.reflex_growth_rate(3600),
            "cost_trend_1h": self.avg_cost_trend(3600),
            "cost_trend_24h": self.avg_cost_trend(86400),
            "total_requests": len(self._records),
            "reflex_writes_total": len(self._reflex_writes),
            "task_breakdown_1h": self.task_type_breakdown(3600),
        }

    def export_records(self, limit: int = 1000) -> list[dict]:
        """Export recent records as dicts (for logging/analysis)."""
        records = list(self._records)[-limit:]
        return [
            {
                "timestamp": r.timestamp,
                "epistemic_state": r.epistemic_state,
                "target": r.target,
                "task_type": r.task_type,
                "model": r.model,
                "confidence": r.confidence,
                "cost_estimate": r.cost_estimate,
                "success": r.success,
                "quality": r.quality,
                "was_correct": r.was_correct,
                "wrote_reflex": r.wrote_reflex,
            }
            for r in records
        ]
