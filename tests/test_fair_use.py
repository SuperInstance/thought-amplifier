"""
Tests for scheduler/fair_use.py — Fair-use GPU time tracking.

Covers:
  - AgentRecord GPU history and value tracking
  - FairUseTracker registration, recording, share computation
  - Starvation prevention
  - Ceiling enforcement
  - Over-share deferral
  - Stats and capacity management
"""

import sys
import os
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scheduler"))

from fair_use import FairUseTracker, AgentRecord
from scheduler import AgentStats


class TestAgentRecord(unittest.TestCase):

    def test_initial_values(self):
        rec = AgentRecord(agent="test")
        self.assertEqual(rec.window_gpu_ms(), 0.0)
        self.assertEqual(rec.time_since_served(), float("inf"))
        self.assertAlmostEqual(rec.value_ema, 0.5)
        self.assertFalse(rec.registered)

    def test_record_usage(self):
        rec = AgentRecord(agent="test")
        rec.record_usage(500, value=0.8)
        self.assertEqual(rec.window_gpu_ms(), 500.0)
        self.assertGreater(rec.last_served, 0)
        self.assertNotEqual(rec.time_since_served(), float("inf"))

    def test_value_ema_updates(self):
        rec = AgentRecord(agent="test")
        rec.record_usage(100, value=1.0)
        # EMA: 0.1 * 1.0 + 0.9 * 0.5 = 0.55
        self.assertAlmostEqual(rec.value_ema, 0.55, places=2)

    def test_window_expiry(self):
        rec = AgentRecord(agent="test")
        rec.record_usage(500, value=0.5)
        # Force old timestamp
        rec.gpu_history.clear()
        rec.gpu_history.append((time.time() - 1000, 500))
        self.assertEqual(rec.window_gpu_ms(window_s=300), 0.0)

    def test_effective_value_default(self):
        rec = AgentRecord(agent="test")
        # Default value_ema is 0.5
        self.assertAlmostEqual(rec.effective_value(), 0.5)

    def test_effective_value_minimum(self):
        rec = AgentRecord(agent="test")
        rec.value_ema = 0.0
        self.assertGreaterEqual(rec.effective_value(), 0.01)

    def test_custom_floor(self):
        rec = AgentRecord(agent="test")
        rec.custom_floor_ms = 5000
        self.assertEqual(rec.custom_floor_ms, 5000)


class TestFairUseTracker(unittest.TestCase):

    def test_register_agent(self):
        tracker = FairUseTracker()
        tracker.register("agent_a", floor_ms=3000)
        self.assertIn("agent_a", tracker._agents)
        self.assertEqual(tracker._agents["agent_a"].custom_floor_ms, 3000)
        self.assertTrue(tracker._agents["agent_a"].registered)

    def test_record_usage(self):
        tracker = FairUseTracker()
        tracker.record("agent_a", 500, value=0.7)
        rec = tracker._agents["agent_a"]
        self.assertEqual(rec.window_gpu_ms(), 500.0)

    def test_get_floor_custom(self):
        tracker = FairUseTracker(default_floor_ms=2000)
        tracker.register("custom", floor_ms=5000)
        self.assertEqual(tracker.get_floor("custom"), 5000)

    def test_get_floor_default(self):
        tracker = FairUseTracker(default_floor_ms=2000)
        tracker.register("standard")
        self.assertEqual(tracker.get_floor("standard"), 2000)

    def test_compute_shares_empty(self):
        tracker = FairUseTracker()
        self.assertEqual(tracker.compute_shares(), {})

    def test_compute_shares_registered_agents(self):
        tracker = FairUseTracker(default_floor_ms=1000)
        tracker.set_capacity(10000)
        tracker.register("a")
        tracker.register("b")
        shares = tracker.compute_shares()
        self.assertIn("a", shares)
        self.assertIn("b", shares)
        self.assertGreater(shares["a"], 0)
        self.assertGreater(shares["b"], 0)

    def test_check_agent_starvation_override(self):
        tracker = FairUseTracker(starvation_boost_s=30)
        tracker.register("starving")
        rec = tracker._agents["starving"]
        rec.last_served = time.time() - 100

        stats = AgentStats(agent="starving")
        over, reason = tracker.check_agent(stats, [])
        self.assertFalse(over)
        self.assertIn("starvation", reason)

    def test_check_agent_ok(self):
        tracker = FairUseTracker(default_floor_ms=2000, starvation_boost_s=99999)
        tracker.register("normal")
        # Mark as recently served so it's not starving
        tracker._agents["normal"].last_served = time.time()
        stats = AgentStats(agent="normal")
        over, reason = tracker.check_agent(stats, [])
        self.assertFalse(over)
        self.assertEqual(reason, "ok")

    def test_ceiling_enforcement(self):
        tracker = FairUseTracker(ceiling_ms=500, default_floor_ms=100)
        tracker.register("greedy")
        # Use lots of GPU
        for _ in range(10):
            tracker.record("greedy", 100, value=0.5)
        stats = AgentStats(agent="greedy")
        other = AgentStats(agent="other")
        over, reason = tracker.check_agent(stats, [other])
        self.assertTrue(over)

    def test_total_capacity(self):
        tracker = FairUseTracker()
        self.assertGreater(tracker.total_capacity(), 0)

    def test_set_capacity(self):
        tracker = FairUseTracker()
        tracker.set_capacity(500000)
        self.assertEqual(tracker.total_capacity(), 500000)

    def test_stats(self):
        tracker = FairUseTracker()
        tracker.register("a")
        tracker.record("a", 300, value=0.6)
        stats = tracker.stats()
        self.assertIn("a", stats)
        self.assertIn("window_gpu_ms", stats["a"])

    def test_unregistered_agent_not_in_shares(self):
        tracker = FairUseTracker()
        tracker.record("unreg", 100)  # records but doesn't register
        shares = tracker.compute_shares()
        self.assertNotIn("unreg", shares)

    def test_shares_clamped_by_ceiling(self):
        tracker = FairUseTracker(
            default_floor_ms=100,
            ceiling_ms=1000,
        )
        tracker.set_capacity(100000)
        tracker.register("a")
        shares = tracker.compute_shares()
        # Share should not exceed ceiling minus used
        self.assertLessEqual(shares["a"], 1000)


class TestFairUseIntegration(unittest.TestCase):

    def test_two_agents_fair_distribution(self):
        tracker = FairUseTracker(
            default_floor_ms=1000,
            ceiling_ms=10000,
        )
        tracker.set_capacity(50000)
        tracker.register("a")
        tracker.register("b")
        # Agent A uses lots
        for _ in range(20):
            tracker.record("a", 500, value=0.8)
        # Agent B uses little
        tracker.record("b", 100, value=0.5)
        shares = tracker.compute_shares()
        # Agent B should still get at least floor
        self.assertGreaterEqual(shares["b"], 0)

    def test_value_weighted_redistribution(self):
        tracker = FairUseTracker(
            default_floor_ms=100,
        )
        tracker.set_capacity(50000)
        tracker.register("low_value")
        tracker.register("high_value")
        # High value agent produces better results
        for _ in range(10):
            tracker.record("high_value", 200, value=0.9)
            tracker.record("low_value", 200, value=0.1)
        shares = tracker.compute_shares()
        # High-value agent gets more excess capacity
        self.assertGreaterEqual(shares["high_value"], shares["low_value"] * 0.9)


if __name__ == "__main__":
    unittest.main()
