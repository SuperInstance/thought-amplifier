"""
priority_evolver.py — The Learning System: Scheduling Policy That Evolves

Starts with static weights. Learns which priority assignments produce
better outcomes. The scheduling policy ITSELF evolves to fit the
application — this is the dynamic ML.

How it works:
  1. Every completed request gets a quality score (0-1) from the outcome
     (did the agent use the result? was it fast enough? was the output good?)
  2. The evolver tracks: for each (agent, priority) pair, what's the
     average quality outcome?
  3. Periodically, it adjusts the effective priority of agents whose
     outcomes are consistently better at different priority levels
  4. It also tracks timing patterns: agent X produces better results
     in the morning, agent Y is better after long idle periods

The evolution is slow (EMA alpha=0.05) and conservative (clamp [0.05, 0.95]).
It never makes extreme changes. The policy can always be overridden by
explicit user/agent priority settings.

This is ZeroClaw Arena's policy breeding applied to scheduling:
  - State = (agent, time_of_day, queue_depth, recent_load)
  - Actions = adjust effective priority by +/- 1
  - Reward = quality_score * timeliness_factor
  - Update = EMA alpha=0.05, clamp [0.05, 0.95]

The policy is a dict[str, str], <50KB, zero imports, hot-swappable.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger("evolver")


class Priority(IntEnum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4


@dataclass
class OutcomeRecord:
    """A completed inference with its outcome quality."""
    agent: str
    assigned_priority: int  # the priority that was used
    base_priority: int      # what the agent requested
    quality: float          # 0-1 quality score
    timeliness: float       # 0-1, 1=immediate, 0=very delayed
    gpu_ms: float
    served_by: str          # local/cloud
    timestamp: float
    # Context features
    time_of_day: float = 0.0    # 0-24
    queue_depth: int = 0
    recent_load: float = 0.0    # 0-1, fraction of capacity used


class PriorityEvolver:
    """
    Learns optimal priority assignments.

    The policy table maps (agent, context_bucket) -> priority_adjustment.
    Context buckets are coarse:
      - time_of_day: morning/afternoon/evening/night
      - load_level: light/moderate/heavy

    The adjustment is added to the base priority (clamped).
    A positive adjustment means "serve this agent later than requested"
    A negative adjustment means "serve this agent sooner than requested"
    """

    def __init__(
        self,
        ema_alpha: float = 0.05,
        min_observations: int = 10,
        adjustment_clamp: float = 2.0,
        evolution_interval_s: float = 120.0,
    ):
        """
        Args:
            ema_alpha: Learning rate (slow = stable)
            min_observations: Don't adjust until we have this many data points
            adjustment_clamp: Maximum priority adjustment magnitude
            evolution_interval_s: How often to recompute policy
        """
        self.ema_alpha = ema_alpha
        self.min_observations = min_observations
        self.adjustment_clamp = adjustment_clamp
        self.evolution_interval_s = evolution_interval_s

        # Outcome tracking: (agent, context_bucket) -> list of (priority, reward)
        self._outcomes: dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        # Policy: agent -> {context_bucket -> adjustment}
        self._policy: dict[str, dict[str, float]] = {}
        # Quality tracking per agent
        self._agent_quality: dict[str, float] = {}  # EMA of quality
        self._lock = threading.Lock()
        self._last_evolution = time.time()
        self._total_outcomes = 0
        self._evolution_count = 0

    def record_outcome(self, record: OutcomeRecord):
        """Record a completed inference outcome for learning."""
        bucket = self._context_bucket(record)
        key = f"{record.agent}:{bucket}"

        # Compute composite reward
        # Reward = quality * 0.6 + timeliness * 0.3 + efficiency * 0.1
        # where efficiency = 1 if local+fast, 0.5 if cloud, 0 if slow local
        if record.served_by == "local":
            efficiency = 1.0 if record.gpu_ms < 1000 else 0.7
        elif record.served_by == "cloud":
            efficiency = 0.5
        else:
            efficiency = 0.3

        reward = (
            record.quality * 0.6
            + record.timeliness * 0.3
            + efficiency * 0.1
        )

        with self._lock:
            self._outcomes[key].append((record.assigned_priority, reward))
            self._total_outcomes += 1

            # Update agent quality EMA
            current = self._agent_quality.get(record.agent, 0.5)
            self._agent_quality[record.agent] = (
                self.ema_alpha * record.quality + (1 - self.ema_alpha) * current
            )

        logger.debug("Recorded outcome: %s pri=%d reward=%.3f q=%.2f t=%.2f",
                     key, record.assigned_priority, reward,
                     record.quality, record.timeliness)

    def get_adjustment(self, agent: str, context: dict | None = None) -> float:
        """
        Get the current priority adjustment for an agent in a context.
        Positive = delay (serve later), negative = expedite (serve sooner).
        If no context given, returns the mean adjustment across all
        buckets for this agent.
        """
        with self._lock:
            agent_policy = self._policy.get(agent, {})
            if not agent_policy:
                return 0.0
            if context:
                bucket = self._context_bucket_from_dict(context)
                adjustment = agent_policy.get(bucket, 0.0)
            else:
                # No context — average across all learned buckets
                vals = list(agent_policy.values())
                adjustment = sum(vals) / len(vals) if vals else 0.0
            # Clamp
            return max(-self.adjustment_clamp,
                       min(self.adjustment_clamp, adjustment))

    def effective_priority(self, base_priority: int, agent: str,
                           context: dict | None = None) -> int:
        """Apply learned adjustment to a base priority."""
        adj = self.get_adjustment(agent, context)
        adjusted = int(round(base_priority + adj))
        return max(0, min(4, adjusted))

    def maybe_evolve(self) -> bool:
        """
        Check if it's time to recompute the policy. If so, do it.
        Returns True if policy was updated.
        """
        if time.time() - self._last_evolution < self.evolution_interval_s:
            return False

        self._evolve_policy()
        return True

    def _evolve_policy(self):
        """
        Recompute priority adjustments from accumulated outcomes.

        For each (agent, context_bucket):
          - Compute average reward at each priority level
          - Find the priority level with highest average reward
          - Set adjustment = best_priority - agent_average_base_priority
          - Apply EMA smoothing to the adjustment
        """
        with self._lock:
            self._last_evolution = time.time()
            self._evolution_count += 1

            for key, outcomes in self._outcomes.items():
                if len(outcomes) < self.min_observations:
                    continue

                parts = key.split(":", 1)
                agent = parts[0]
                bucket = parts[1] if len(parts) > 1 else "default"

                # Group rewards by assigned priority
                pri_rewards: dict[int, list[float]] = defaultdict(list)
                for pri, reward in outcomes:
                    pri_rewards[pri].append(reward)

                # Find best priority (highest avg reward)
                best_pri = None
                best_reward = -1
                for pri, rewards in pri_rewards.items():
                    avg = sum(rewards) / len(rewards)
                    if avg > best_reward:
                        best_reward = avg
                        best_pri = pri

                if best_pri is None:
                    continue

                # Compute current average base priority
                avg_base = sum(p for p, _ in outcomes) / len(outcomes)

                # Target adjustment
                target_adj = best_pri - avg_base
                # Clamp
                target_adj = max(-self.adjustment_clamp,
                                 min(self.adjustment_clamp, target_adj))

                # EMA update
                agent_policy = self._policy.setdefault(agent, {})
                current_adj = agent_policy.get(bucket, 0.0)
                new_adj = self.ema_alpha * target_adj + (1 - self.ema_alpha) * current_adj
                # Clamp again after smoothing
                new_adj = max(-self.adjustment_clamp,
                              min(self.adjustment_clamp, new_adj))
                agent_policy[bucket] = new_adj

                if abs(new_adj - current_adj) > 0.1:
                    logger.info(
                        "Policy evolved: %s/%s adj %.2f -> %.2f "
                        "(best_pri=%d reward=%.3f observations=%d)",
                        agent, bucket, current_adj, new_adj,
                        best_pri, best_reward, len(outcomes)
                    )

    def _context_bucket(self, record: OutcomeRecord) -> str:
        """Discretize context into coarse buckets."""
        tod = record.time_of_day or (
            time.localtime().tm_hour + time.localtime().tm_min / 60.0
        )
        if 5 <= tod < 12:
            time_bucket = "morning"
        elif 12 <= tod < 17:
            time_bucket = "afternoon"
        elif 17 <= tod < 22:
            time_bucket = "evening"
        else:
            time_bucket = "night"

        if record.recent_load < 0.3:
            load_bucket = "light"
        elif record.recent_load < 0.7:
            load_bucket = "moderate"
        else:
            load_bucket = "heavy"

        return f"{time_bucket}_{load_bucket}"

    def _context_bucket_from_dict(self, ctx: dict) -> str:
        record = OutcomeRecord(
            agent=ctx.get("agent", ""),
            assigned_priority=ctx.get("priority", 2),
            base_priority=ctx.get("priority", 2),
            quality=0,
            timeliness=0,
            gpu_ms=0,
            served_by="local",
            timestamp=time.time(),
            time_of_day=ctx.get("time_of_day", 0),
            queue_depth=ctx.get("queue_depth", 0),
            recent_load=ctx.get("recent_load", 0),
        )
        return self._context_bucket(record)

    def export_policy(self) -> dict:
        """Export the current policy as a JSON-serializable dict (<50KB)."""
        with self._lock:
            return {
                "policy": dict(self._policy),
                "agent_quality": dict(self._agent_quality),
                "total_outcomes": self._total_outcomes,
                "evolution_count": self._evolution_count,
                "ema_alpha": self.ema_alpha,
            }

    def import_policy(self, data: dict):
        """Import a previously exported policy."""
        with self._lock:
            self._policy = data.get("policy", {})
            self._agent_quality = data.get("agent_quality", {})
            logger.info("Imported policy: %d agents, %d outcomes",
                       len(self._policy), data.get("total_outcomes", 0))

    def stats(self) -> dict:
        return {
            "total_outcomes": self._total_outcomes,
            "evolution_count": self._evolution_count,
            "tracked_keys": len(self._outcomes),
            "policy_size": len(self._policy),
            "last_evolution_ago_s": round(time.time() - self._last_evolution, 1),
            "agent_quality": {
                k: round(v, 3) for k, v in self._agent_quality.items()
            },
        }
