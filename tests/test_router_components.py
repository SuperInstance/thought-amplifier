"""
Tests for router/model_selector.py, router/cloud_cascade.py,
and router/boundary_tracker.py.

Covers:
  - LocalModelSelector selection logic (task match, urgency, character, learning)
  - CloudCascade model selection, cost estimation, budget tracking
  - CloudBudget daily reset and exhaustion
  - BoundaryTracker recording, distribution, accuracy, calibration
"""

import sys
import os
import time
import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from router.model_selector import (
    LocalModelSelector, GRANITE, QWEN, ModelProfile, ModelSelection,
)
from router.cloud_cascade import (
    CloudCascade, CloudBudget, estimate_cloud_cost,
    DEEPSEEK_V3, QWEN_CODER_480B, HERMES_405B, CF_LLAMA_8B,
    ALL_CLOUD_MODELS,
)
from router.boundary_tracker import BoundaryTracker, RequestRecord
from router.router import (
    CognitiveRouter, RouteDecision, EpistemicState, RouteTarget,
)


class TestLocalModelSelector(unittest.TestCase):

    def test_granite_for_analytical(self):
        sel = LocalModelSelector()
        result = sel.select("Compare approaches", {"task_type": "analytical"})
        self.assertEqual(result.name, GRANITE.name)

    def test_qwen_for_creative(self):
        sel = LocalModelSelector()
        result = sel.select("Write a poem", {"task_type": "creative"})
        self.assertEqual(result.name, QWEN.name)

    def test_character_consistency_forces_granite(self):
        sel = LocalModelSelector()
        result = sel.select("Write story", {"task_type": "creative"},
                           context={"requires_character": True})
        self.assertEqual(result.name, GRANITE.name)

    def test_urgent_low_quality_prefers_qwen(self):
        sel = LocalModelSelector()
        result = sel.select("quick thing", {"task_type": "general"},
                           context={"urgency": "URGENT", "quality_requirement": "low"})
        self.assertEqual(result.name, QWEN.name)

    def test_high_quality_prefers_granite(self):
        sel = LocalModelSelector()
        result = sel.select("important task", {"task_type": "general"},
                           context={"quality_requirement": "high"})
        self.assertEqual(result.name, GRANITE.name)

    def test_learning_updates_scores(self):
        sel = LocalModelSelector()
        for _ in range(20):
            sel.record_outcome("analytical", GRANITE.name, success=False, quality=0.1)
            sel.record_outcome("analytical", QWEN.name, success=True, quality=0.9)
        scores = sel.get_model_scores("analytical")
        self.assertLess(scores[GRANITE.name], scores[QWEN.name])

    def test_stats_returns_dict(self):
        sel = LocalModelSelector()
        sel.record_outcome("code", GRANITE.name, True, 0.8)
        stats = sel.stats()
        self.assertIn("code", stats)

    def test_granite_profile_constants(self):
        self.assertGreater(GRANITE.speed_toks, 50)
        self.assertGreater(GRANITE.expected_latency_ms, 100)
        self.assertFalse(GRANITE.breaks_character)

    def test_qwen_profile_constants(self):
        self.assertGreater(QWEN.speed_toks, 100)
        self.assertTrue(QWEN.breaks_character)

    def test_default_selects_granite_for_general(self):
        sel = LocalModelSelector()
        result = sel.select("general task", {"task_type": "general"})
        # Granite is higher capability for general (0.55 > 0.50)
        self.assertEqual(result.name, GRANITE.name)


class TestCloudBudget(unittest.TestCase):

    def test_initial_budget(self):
        budget = CloudBudget(daily_budget_usd=5.0)
        self.assertAlmostEqual(budget.remaining(), 5.0)

    def test_spend(self):
        budget = CloudBudget(daily_budget_usd=1.0)
        budget.spend(0.3)
        self.assertAlmostEqual(budget.remaining(), 0.7)

    def test_exhausted(self):
        budget = CloudBudget(daily_budget_usd=0.5)
        budget.spend(0.5)
        self.assertTrue(budget.is_exhausted())

    def test_not_exhausted(self):
        budget = CloudBudget(daily_budget_usd=1.0)
        budget.spend(0.3)
        self.assertFalse(budget.is_exhausted())

    def test_daily_reset(self):
        budget = CloudBudget(daily_budget_usd=1.0)
        budget.spend(0.8)
        # Force new day
        budget._date = "2020-01-01"
        budget._reset_if_new_day()
        self.assertAlmostEqual(budget.remaining(), 1.0)

    def test_stats(self):
        budget = CloudBudget(daily_budget_usd=2.0)
        budget.spend(0.5)
        stats = budget.stats()
        self.assertAlmostEqual(stats["daily_budget"], 2.0)
        self.assertAlmostEqual(stats["spent_today"], 0.5)
        self.assertAlmostEqual(stats["remaining"], 1.5)


class TestEstimateCloudCost(unittest.TestCase):

    def test_positive_cost(self):
        cost = estimate_cloud_cost(DEEPSEEK_V3, "short prompt", 500)
        self.assertGreater(cost, 0)

    def test_zero_cost_free_model(self):
        cost = estimate_cloud_cost(CF_LLAMA_8B, "prompt", 500)
        self.assertEqual(cost, 0.0)

    def test_longer_prompt_costs_more(self):
        short = estimate_cloud_cost(DEEPSEEK_V3, "hi", 100)
        long_cost = estimate_cloud_cost(DEEPSEEK_V3, "x " * 1000, 2000)
        self.assertGreater(long_cost, short)

    def test_cost_reasonable_small(self):
        cost = estimate_cloud_cost(DEEPSEEK_V3, "A reasonable prompt of moderate length.", 300)
        self.assertLess(cost, 0.01)


class TestCloudCascade(unittest.TestCase):

    def test_select_for_analytical(self):
        cascade = CloudCascade()
        result = cascade.select_model("Analyze tradeoffs", {"task_type": "analytical"})
        self.assertIn(result.provider, ("deepseek", "deepinfra"))

    def test_select_for_code(self):
        cascade = CloudCascade()
        result = cascade.select_model("Write Python code", {"task_type": "code"})
        self.assertIn("Coder", result.name)

    def test_select_for_creative(self):
        cascade = CloudCascade()
        result = cascade.select_model("Write fantasy story", {"task_type": "creative"})
        self.assertIn("Hermes", result.name)

    def test_budget_exhaustion_falls_back(self):
        budget = CloudBudget(daily_budget_usd=0.001)
        budget.spend(0.001)
        cascade = CloudCascade(budget=budget)
        result = cascade.select_model("complex task", {"task_type": "analytical"})
        self.assertEqual(result.estimated_cost, 0.0)

    def test_record_spend(self):
        cascade = CloudCascade()
        cascade.record_spend(0.05)
        stats = cascade.stats()
        self.assertAlmostEqual(stats["budget"]["spent_today"], 0.05)

    def test_all_models_have_valid_profiles(self):
        for name, model in ALL_CLOUD_MODELS.items():
            self.assertGreater(model.expected_latency_s, 0)
            self.assertGreaterEqual(model.max_tokens, 100)
            self.assertIsInstance(model.strength_types, tuple)

    def test_stats_returns_dict(self):
        cascade = CloudCascade()
        stats = cascade.stats()
        self.assertIn("budget", stats)
        self.assertIn("models", stats)

    def test_model_scoring_prefers_specialty_match(self):
        cascade = CloudCascade()
        # Code task should pick coder model
        result = cascade.select_model("def foo()", {"task_type": "code"})
        self.assertIn("Coder", result.name)


class TestBoundaryTracker(unittest.TestCase):

    def test_record_and_track_count(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.route("test prompt 1")
        router.route("test prompt 2")
        self.assertEqual(len(tracker._records), 2)

    def test_state_distribution_empty(self):
        tracker = BoundaryTracker()
        dist = tracker.state_distribution()
        self.assertEqual(dist["KNOWN-KNOWN"], 0.0)

    def test_state_distribution_with_data(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.reflex_cache.store("q", "a", confidence=0.95)
        router.route("q")  # KNOWN-KNOWN
        dist = tracker.state_distribution(window_s=3600)
        total = sum(dist.values())
        self.assertGreater(total, 0)

    def test_routing_accuracy_none_without_outcomes(self):
        tracker = BoundaryTracker()
        self.assertIsNone(tracker.routing_accuracy())

    def test_routing_accuracy_with_outcomes(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        decision = router.route("Compare two things analytically")
        router.record_outcome("Compare two things analytically", decision,
                            success=True, quality=0.8)
        acc = tracker.routing_accuracy(window_s=3600)
        self.assertIsNotNone(acc)

    def test_calibration_error_few_samples(self):
        tracker = BoundaryTracker()
        self.assertIsNone(tracker.calibration_error())

    def test_export_records(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.route("test")
        records = tracker.export_records()
        self.assertGreater(len(records), 0)
        self.assertIn("epistemic_state", records[0])

    def test_report(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.route("prompt")
        report = tracker.report()
        self.assertIn("state_distribution_1h", report)
        self.assertIn("total_requests", report)
        self.assertIn("cost_trend_1h", report)

    def test_reflex_writes_tracked(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        decision = router.route("complex prompt", force_target=RouteTarget.CLOUD)
        router.record_outcome("complex prompt", decision,
                            success=True, quality=0.9,
                            response_text="answer")
        self.assertGreater(len(tracker._reflex_writes), 0)

    def test_reflex_growth_rate(self):
        tracker = BoundaryTracker()
        rate = tracker.reflex_growth_rate(window_s=3600)
        self.assertGreaterEqual(rate, 0.0)

    def test_avg_cost_trend(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.route("free local prompt")
        cost = tracker.avg_cost_trend(window_s=3600)
        self.assertIn("avg_cost", cost)
        self.assertIn("free_ratio", cost)

    def test_task_type_breakdown_empty(self):
        tracker = BoundaryTracker()
        report = tracker.task_type_breakdown()
        self.assertEqual(report, {})

    def test_task_type_breakdown_with_data(self):
        tracker = BoundaryTracker()
        router = CognitiveRouter(boundary_tracker=tracker)
        router.route("Compare and analyze")
        breakdown = tracker.task_type_breakdown(window_s=3600)
        self.assertGreater(len(breakdown), 0)

    def test_max_records_bounded(self):
        tracker = BoundaryTracker()
        # The deque has maxlen=10_000
        self.assertEqual(tracker.MAX_RECORDS, 10_000)

    def test_correctness_evaluation_known_known(self):
        tracker = BoundaryTracker()
        rec = RequestRecord(
            timestamp=time.time(),
            epistemic_state="KNOWN-KNOWN",
            target="reflex",
            task_type="general",
            model=None,
            confidence=0.9,
            cost_estimate=0.0,
        )
        correct = tracker._evaluate_correctness(rec, True, 0.8)
        self.assertTrue(correct)
        correct_bad = tracker._evaluate_correctness(rec, True, 0.3)
        self.assertFalse(correct_bad)


if __name__ == "__main__":
    unittest.main()
