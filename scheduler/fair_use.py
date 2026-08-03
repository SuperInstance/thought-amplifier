"""
fair_use.py — The Ethos: Guaranteed Minimum GPU Share

Every agent gets a floor. No agent starves. The pie is divided so that
even the LOWEST priority agent gets its minimum share of GPU time over
any sliding window. Above the floor, excess capacity is redistributed
by value-weight — agents that produce more value per GPU-ms get more.

This is the university supercomputer model: every lab gets a guaranteed
allocation. Labs that use their allocation productively get more.
Nobody is ever fully cut off, but neither is capacity wasted on agents
that produce nothing useful.

The sliding window is key. We don't track total GPU time since the
beginning of the universe — we track the last N seconds (default 5 min).
This means an agent that was greedy 10 minutes ago isn't penalized
forever, and an agent that was idle can ramp up.

Guarantees:
  1. Every registered agent gets at least floor_ms per window
  2. No agent can consume more than ceiling_ms per window
  3. Excess capacity (total - sum of floors) distributed by value
  4. New agents get a "warmup" period with default floor
  5. Starvation is impossible: if an agent hasn't been served in
     window_s * 2, its effective priority is boosted to HIGH

Value-weighted redistribution:
  excess_ms = available_ms - sum(floors)
  agent_share = excess_ms * (agent_value / sum(all_values))
  where agent_value = EMA of quality scores from completed requests
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger("fair_use")


@dataclass
class AgentRecord:
    """Per-agent fair-use accounting."""
    agent: str
    # GPU time in the current window
    gpu_history: deque = field(default_factory=lambda: deque(maxlen=600))
    # Quality scores (0-1) from completed requests
    value_history: deque = field(default_factory=lambda: deque(maxlen=200))
    # Value EMA
    value_ema: float = 0.5
    # Last serve time
    last_served: float = 0.0
    # Registered?
    registered: bool = False
    # Custom floor (0 = use default)
    custom_floor_ms: float = 0.0

    def record_usage(self, gpu_ms: float, value: float = 0.0):
        now = time.time()
        self.gpu_history.append((now, gpu_ms))
        if value > 0:
            self.value_history.append((now, value))
            # EMA with alpha=0.1 (slow adaptation)
            self.value_ema = 0.1 * value + 0.9 * self.value_ema
        self.last_served = now

    def window_gpu_ms(self, window_s: float = 300.0) -> float:
        cutoff = time.time() - window_s
        return sum(ms for ts, ms in self.gpu_history if ts >= cutoff)

    def time_since_served(self) -> float:
        if self.last_served == 0:
            return float("inf")
        return time.time() - self.last_served

    def effective_value(self) -> float:
        """Value score used for redistribution weighting."""
        if self.value_ema <= 0:
            return 0.01  # minimum nonzero weight
        return self.value_ema


class FairUseTracker:
    """
    Thread-safe fair-use enforcement.

    Usage:
        tracker = FairUseTracker(window_s=300, default_floor_ms=2000)
        tracker.register("thinker", floor_ms=3000)
        tracker.register("conductor", floor_ms=1500)

        # Before serving a request:
        over, reason = tracker.check_agent(stats, other_agents_stats)
    """

    def __init__(
        self,
        window_s: float = 300.0,
        default_floor_ms: float = 2000.0,
        ceiling_ms: float = 60000.0,
        starvation_boost_s: float = 600.0,
        min_value_weight: float = 0.01,
    ):
        """
        Args:
            window_s: Sliding window for GPU accounting (default 5 min)
            default_floor_ms: Minimum GPU time per agent per window
            ceiling_ms: Maximum GPU time per agent per window
            starvation_boost_s: Seconds without service before priority boost
            min_value_weight: Minimum weight in redistribution
        """
        self.window_s = window_s
        self.default_floor_ms = default_floor_ms
        self.ceiling_ms = ceiling_ms
        self.starvation_boost_s = starvation_boost_s
        self.min_value_weight = min_value_weight
        self._agents: dict[str, AgentRecord] = {}
        self._lock = threading.Lock()
        # Total GPU capacity estimate (ms per window)
        # On RTX 4050 with ~500ms per inference, that's ~600 inferences
        # in 5 minutes, so ~300,000ms of GPU time
        self.total_capacity_ms = 300_000.0

    def register(self, agent: str, floor_ms: float = 0):
        """Register an agent with an optional custom floor."""
        with self._lock:
            rec = self._agents.get(agent)
            if rec is None:
                rec = AgentRecord(agent=agent)
                self._agents[agent] = rec
            rec.registered = True
            if floor_ms > 0:
                rec.custom_floor_ms = floor_ms
            logger.info("Registered agent %s floor=%.0fms", agent,
                        rec.custom_floor_ms or self.default_floor_ms)

    def record(self, agent: str, gpu_ms: float, value: float = 0.0):
        """Record GPU usage for an agent."""
        with self._lock:
            rec = self._agents.setdefault(agent, AgentRecord(agent=agent))
            rec.record_usage(gpu_ms, value)

    def get_floor(self, agent: str) -> float:
        rec = self._agents.get(agent)
        if rec and rec.custom_floor_ms > 0:
            return rec.custom_floor_ms
        return self.default_floor_ms

    def compute_shares(self) -> dict[str, float]:
        """
        Compute fair GPU share (ms) for each agent in current window.

        share[agent] = floor + excess * (value / total_value)
        clamped to [0, ceiling]

        Thread-safe. Callers already holding self._lock should use
        _compute_shares_unlocked() instead.
        """
        with self._lock:
            return self._compute_shares_unlocked()

    def _compute_shares_unlocked(self) -> dict[str, float]:
        """Internal: compute shares. Caller must hold self._lock."""
        agents = list(self._agents.values())
        if not agents:
            return {}

        now = time.time()
        cutoff = now - self.window_s

        total_floor = sum(
            (a.custom_floor_ms or self.default_floor_ms)
            for a in agents if a.registered
        )

        used = sum(a.window_gpu_ms(self.window_s) for a in agents)

        excess = max(0, self.total_capacity_ms - total_floor - used)

        values = {a.agent: a.effective_value() for a in agents}
        total_value = sum(values.values())

        shares = {}
        for a in agents:
            if not a.registered:
                continue
            floor = a.custom_floor_ms or self.default_floor_ms
            if total_value > 0:
                bonus = excess * (values[a.agent] / total_value)
            else:
                bonus = excess / len(agents)
            share = floor + bonus
            used_a = a.window_gpu_ms(self.window_s)
            share = min(share, max(0, self.ceiling_ms - used_a))
            shares[a.agent] = share

        return shares

    def check_agent(self, agent_stats, other_agents_stats: list) -> tuple[bool, str]:
        """
        Check if an agent should be deferred (is over its share).

        Returns (should_defer, reason). The caller requeues the request
        and picks the next one.
        """
        agent_name = agent_stats.agent
        with self._lock:
            rec = self._agents.setdefault(agent_name, AgentRecord(agent=agent_name))

            # Starvation check — always serve if starving
            if rec.time_since_served() > self.starvation_boost_s:
                return (False, "starvation_override")

            used = rec.window_gpu_ms(self.window_s)
            floor = rec.custom_floor_ms or self.default_floor_ms

            # Ceiling check
            if used >= self.ceiling_ms:
                # Hard ceiling — defer unless nobody else is waiting
                if other_agents_stats:
                    return (True, f"ceiling_reached ({used:.0f}ms >= {self.ceiling_ms:.0f}ms)")

            # Floor check for OTHER agents
            # If this agent is well above its floor and others are below,
            # defer to let the under-served agent go first
            if other_agents_stats:
                shares = self._compute_shares_unlocked()
                my_share = shares.get(agent_name, floor)
                if used > my_share * 1.5:  # 50% above share
                    # Check if anyone else is significantly under-served
                    for other in other_agents_stats:
                        other_name = other.agent if hasattr(other, 'agent') else str(other)
                        other_rec = self._agents.get(other_name)
                        if other_rec:
                            other_used = other_rec.window_gpu_ms(self.window_s)
                            other_share = shares.get(other_name, floor)
                            if other_used < other_share * 0.5:
                                return (True,
                                        f"over_share ({used:.0f}ms vs {my_share:.0f}ms share, "
                                        f"{other_name} under-served at {other_used:.0f}ms)")

            return (False, "ok")

    def stats(self) -> dict[str, dict]:
        with self._lock:
            shares = self._compute_shares_unlocked()
            result = {}
            for agent, rec in self._agents.items():
                result[agent] = {
                    "window_gpu_ms": round(rec.window_gpu_ms(self.window_s), 1),
                    "fair_share_ms": round(shares.get(agent, 0), 1),
                    "value_ema": round(rec.value_ema, 3),
                    "last_served_ago_s": round(rec.time_since_served(), 1)
                    if rec.last_served > 0 else None,
                    "floor_ms": rec.custom_floor_ms or self.default_floor_ms,
                    "registered": rec.registered,
                }
            return result

    def total_capacity(self) -> float:
        return self.total_capacity_ms

    def set_capacity(self, ms: float):
        self.total_capacity_ms = ms
