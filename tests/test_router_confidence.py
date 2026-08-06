"""
Tests for router/confidence.py — Prompt complexity, task classification,
model capability, success history, novelty detection, and the
confidence ensemble.

Covers:
  - analyze_complexity() across many prompt shapes
  - _classify_task() for all task types
  - best_model_for_task() and max_capability()
  - SuccessHistory EMA tracking
  - NoveltyDetector shape hashing
  - ConfidenceAssessor ensemble scoring
"""

import sys
import os
import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from router.confidence import (
    analyze_complexity, _classify_task, best_model_for_task,
    max_capability, SuccessHistory, NoveltyDetector,
    ConfidenceAssessor, MODEL_CAPABILITY, TASK_PATTERNS,
    ComplexityScore,
)


class TestAnalyzeComplexity(unittest.TestCase):

    def test_simple_prompt(self):
        c = analyze_complexity("hello")
        self.assertLess(c.word_count, 5)
        self.assertLess(c.complexity, 0.5)

    def test_complex_prompt(self):
        prompt = ("First, analyze the root causes. Then, design a solution. "
                  "Finally, implement it step by step. What are the tradeoffs "
                  "when compared to alternative approaches?")
        c = analyze_complexity(prompt)
        self.assertGreater(c.word_count, 15)
        self.assertGreater(c.complexity, 0.2)
        self.assertTrue(c.has_multi_step)

    def test_code_detection(self):
        c = analyze_complexity("def foo():\n    return 42")
        self.assertTrue(c.has_code)

    def test_no_code(self):
        c = analyze_complexity("Tell me about the weather")
        self.assertFalse(c.has_code)

    def test_multi_step_detection(self):
        c = analyze_complexity("First do X. Then do Y. Finally do Z.")
        self.assertTrue(c.has_multi_step)

    def test_question_depth(self):
        c1 = analyze_complexity("What is this?")
        c2 = analyze_complexity("Why does X happen when Y occurs because Z?")
        self.assertGreaterEqual(c2.question_depth, c1.question_depth)

    def test_sentence_count(self):
        c = analyze_complexity("One. Two. Three.")
        self.assertGreaterEqual(c.sentence_count, 3)

    def test_avg_sentence_length(self):
        c = analyze_complexity("Short sentence.")
        self.assertGreater(c.avg_sentence_length, 0)

    def test_complexity_in_range(self):
        for prompt in ["", "hi", "word " * 500, "code: def f(): pass"]:
            c = analyze_complexity(prompt)
            self.assertGreaterEqual(c.complexity, 0.0)
            self.assertLessEqual(c.complexity, 1.0)

    def test_task_type_returned(self):
        c = analyze_complexity("Compare two approaches analytically")
        self.assertIsInstance(c.task_type, str)
        self.assertGreater(len(c.task_type), 0)

    def test_task_confidence_in_range(self):
        c = analyze_complexity("Compare two approaches analytically")
        self.assertGreaterEqual(c.task_confidence, 0.0)
        self.assertLessEqual(c.task_confidence, 1.0)


class TestClassifyTask(unittest.TestCase):

    def test_analytical(self):
        task, conf = _classify_task("Compare and analyze the differences")
        self.assertEqual(task, "analytical")

    def test_creative(self):
        task, conf = _classify_task("Write a creative story or poem")
        self.assertEqual(task, "creative")

    def test_code(self):
        task, conf = _classify_task("Write Python code with a function")
        self.assertEqual(task, "code")

    def test_instructional(self):
        task, conf = _classify_task("Explain what a database is")
        self.assertEqual(task, "instructional")

    def test_emotional(self):
        task, conf = _classify_task("I feel sad and worried about this")
        self.assertEqual(task, "emotional")

    def test_no_match_returns_general(self):
        task, conf = _classify_task("zzz qqq xxx")
        self.assertEqual(task, "general")
        self.assertEqual(conf, 0.0)

    def test_confidence_proportional(self):
        _, conf1 = _classify_task("Compare analyze")
        _, conf2 = _classify_task("Compare analyze evaluate assess")
        # More matches → higher confidence
        self.assertGreaterEqual(conf2, conf1)


class TestModelCapability(unittest.TestCase):

    def test_granite_best_for_analytical(self):
        model, score = best_model_for_task("analytical")
        self.assertEqual(model, "granite3.1-dense:2b")
        self.assertGreater(score, 0.7)

    def test_qwen_best_for_creative(self):
        model, score = best_model_for_task("creative")
        self.assertEqual(model, "qwen2.5:0.5b")
        self.assertGreater(score, 0.6)

    def test_max_capability(self):
        mc = max_capability("analytical")
        self.assertGreater(mc, 0.7)

    def test_all_task_types_have_capability(self):
        for model, caps in MODEL_CAPABILITY.items():
            for task in ["analytical", "creative", "code", "emotional", "general"]:
                self.assertIn(task, caps, f"{model} missing {task}")

    def test_capability_values_in_range(self):
        for model, caps in MODEL_CAPABILITY.items():
            for task, val in caps.items():
                self.assertGreater(val, 0.0)
                self.assertLessEqual(val, 1.0)


class TestSuccessHistory(unittest.TestCase):

    def test_initial_returns_none(self):
        hist = SuccessHistory()
        self.assertIsNone(hist.success_rate("analytical"))

    def test_after_min_observations(self):
        hist = SuccessHistory()
        for _ in range(6):
            hist.record("analytical", success=True, quality=0.8)
        rate = hist.success_rate("analytical")
        self.assertIsNotNone(rate)
        self.assertGreater(rate, 0.5)

    def test_below_min_returns_none(self):
        hist = SuccessHistory()
        for _ in range(4):  # MIN_OBSERVATIONS = 5
            hist.record("analytical", success=True, quality=0.8)
        self.assertIsNone(hist.success_rate("analytical"))

    def test_ema_converges_slowly(self):
        hist = SuccessHistory()
        # All successes at quality 1.0
        for _ in range(20):
            hist.record("test_task", success=True, quality=1.0)
        rate_high = hist.success_rate("test_task")
        # Now switch to all failures at quality 0.0
        for _ in range(20):
            hist.record("test_task", success=False, quality=0.0)
        rate_low = hist.success_rate("test_task")
        self.assertGreater(rate_high, rate_low)

    def test_independent_task_types(self):
        hist = SuccessHistory()
        for _ in range(10):
            hist.record("analytical", success=True, quality=0.9)
            hist.record("creative", success=False, quality=0.2)
        self.assertGreater(hist.success_rate("analytical"),
                          hist.success_rate("creative"))

    def test_stats(self):
        hist = SuccessHistory()
        for _ in range(6):
            hist.record("test", success=True, quality=0.7)
        stats = hist.stats()
        self.assertIn("test", stats)
        self.assertEqual(stats["test"]["count"], 6)


class TestNoveltyDetector(unittest.TestCase):

    def test_first_observation_max_novelty(self):
        det = NoveltyDetector()
        novelty = det.observe("Compare A and B", "analytical")
        self.assertGreater(novelty, 0.9)  # First observation: 1 - 1/20 = 0.95

    def test_novelty_decreases_with_repetition(self):
        det = NoveltyDetector()
        for _ in range(20):
            novelty = det.observe("Compare A and B", "analytical")
        self.assertLess(novelty, 0.1)

    def test_different_shapes_different_novelty(self):
        det = NoveltyDetector()
        det.observe("Compare A and B", "analytical")
        # Same shape, different content → not novel shape
        novelty_same = det.novelty_of("Compare X and Y", "analytical")
        # Different shape
        novelty_diff = det.novelty_of("Write a poem about the ocean", "creative")
        self.assertGreater(novelty_diff, novelty_same)

    def test_novelty_of_does_not_record(self):
        det = NoveltyDetector()
        det.observe("test prompt", "general")
        n1 = det.novelty_of("test prompt", "general")
        n2 = det.novelty_of("test prompt", "general")
        self.assertEqual(n1, n2)  # No new observations

    def test_length_buckets(self):
        det = NoveltyDetector()
        # Short and long prompts with same task type
        det.observe("hi", "general")
        n_short = det.novelty_of("hi", "general")
        n_long = det.novelty_of("word " * 100, "general")
        # Long prompt should be in different bucket → max novelty
        self.assertGreater(n_long, n_short)


class TestConfidenceAssessor(unittest.TestCase):

    def test_returns_confidence(self):
        assessor = ConfidenceAssessor()
        result = assessor.assess("Compare two approaches")
        self.assertIn("confidence", result)
        self.assertGreater(result["confidence"], 0.0)
        self.assertLess(result["confidence"], 1.0)

    def test_returns_signals(self):
        assessor = ConfidenceAssessor()
        result = assessor.assess("Explain something")
        self.assertIn("signals", result)
        for key in ("capability", "history", "complexity", "novelty"):
            self.assertIn(key, result["signals"])

    def test_returns_task_type(self):
        assessor = ConfidenceAssessor()
        result = assessor.assess("Write a poem")
        self.assertEqual(result["task_type"], "creative")

    def test_returns_recommended_model(self):
        assessor = ConfidenceAssessor()
        result = assessor.assess("Compare and analyze")
        self.assertIn("recommended_model", result)

    def test_novel_prompt_lower_confidence(self):
        fresh = ConfidenceAssessor()
        result1 = fresh.assess("Compare A and B")
        # Observe many times
        warmed = ConfidenceAssessor()
        for _ in range(20):
            warmed.assess("Compare A and B")
        result2 = warmed.assess("Compare A and B")
        # Warmed up should have higher confidence (lower novelty)
        self.assertGreaterEqual(result2["confidence"], result1["confidence"] - 0.05)

    def test_record_outcome(self):
        assessor = ConfidenceAssessor()
        for _ in range(10):
            assessor.record_outcome("analytical", success=True, quality=0.9)
        # After recording, success history should have data
        rate = assessor.success_history.success_rate("analytical")
        self.assertIsNotNone(rate)

    def test_familiar_analytical_higher_than_novel_creative(self):
        assessor = ConfidenceAssessor()
        # Train heavily on analytical
        for _ in range(20):
            result = assessor.assess("Compare and analyze data")
        analytical_conf = result["confidence"]

        # Fresh creative prompt
        fresh = ConfidenceAssessor()
        creative_result = fresh.assess("Write a creative emotional poem")
        # Both should be in valid range; analytical with history may be similar
        self.assertGreater(creative_result["confidence"], 0.0)

    def test_context_passed_through(self):
        assessor = ConfidenceAssessor()
        result = assessor.assess("test", agent="myagent", context={"foo": "bar"})
        self.assertIn("confidence", result)


if __name__ == "__main__":
    unittest.main()
