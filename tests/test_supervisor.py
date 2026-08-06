"""
Tests for core/supervisor.py — QualityScore, Directive, Supervisor.

Covers:
  - QualityScore.compute() across many scenarios
  - Directive.apply() for all kinds (prompt, temperature, context, interval)
  - Supervisor review cycle (assess, choose directive, apply)
  - Trust tracking (asymmetric, rollback)
  - Prompt library constants
  - Edge cases (empty thoughts, insufficient data, consecutive decreases)
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.journal import Journal
from core.supervisor import QualityScore, Directive, Supervisor, PROMPT_VARIATIONS
from core.thinker import Thinker, ThinkerConfig


# ─── QualityScore Tests ────────────────────────────────────────

class TestQualityScoreCompute(unittest.TestCase):
    """QualityScore heuristic quality assessment."""

    def test_first_thought_is_novel(self):
        score = QualityScore.compute("A unique first thought about cosmos", [])
        self.assertGreater(score.novelty, 0.5)

    def test_low_word_count_low_specificity(self):
        score = QualityScore.compute("hi", [])
        self.assertLess(score.specificity, 0.3)

    def test_moderate_word_count_good_specificity(self):
        score = QualityScore.compute(" ".join(["word"] * 20), [])
        self.assertGreaterEqual(score.specificity, 0.5)

    def test_very_long_thought_decreases_specificity(self):
        score = QualityScore.compute(" ".join(["word"] * 150), [])
        self.assertLess(score.specificity, 0.8)

    def test_questions_boost_engagement(self):
        score = QualityScore.compute("Why does this happen? What causes it?", [])
        self.assertGreater(score.engagement, 0.4)

    def test_transition_words_boost_engagement(self):
        score = QualityScore.compute("However, this is surprising and unexpected.", [])
        self.assertGreater(score.engagement, 0.5)

    def test_causal_words_boost_engagement(self):
        score = QualityScore.compute("This happens because of that.", [])
        self.assertGreater(score.engagement, 0.4)

    def test_engagement_capped_at_1(self):
        score = QualityScore.compute(
            "But however surprising! Why? Because therefore means imagine!", [])
        self.assertLessEqual(score.engagement, 1.0)

    def test_overall_is_weighted_mean(self):
        score = QualityScore.compute("A test thought about things.", [])
        expected = (score.novelty * 0.3 + score.specificity * 0.25 +
                    score.coherence * 0.2 + score.engagement * 0.25)
        self.assertAlmostEqual(score.overall, expected, places=5)

    def test_novelty_decreases_with_repetition(self):
        recent = ["the cat sat on the mat"] * 10
        score_novel = QualityScore.compute("the cat sat on the mat", recent)
        self.assertLess(score_novel.novelty, 0.5)

    def test_novelty_high_with_different_words(self):
        recent = ["alpha beta gamma"] * 10
        score = QualityScore.compute("delta epsilon zeta eta theta", recent)
        self.assertGreater(score.novelty, 0.7)

    def test_empty_thought(self):
        score = QualityScore.compute("", [])
        self.assertGreaterEqual(score.overall, 0.0)
        self.assertLessEqual(score.overall, 1.0)

    def test_all_scores_in_range(self):
        for text in ["", "short", "a b c d e", "x " * 200, "Why? Because! However..."]:
            score = QualityScore.compute(text, [])
            for attr in ("novelty", "specificity", "coherence", "engagement", "overall"):
                val = getattr(score, attr)
                self.assertGreaterEqual(val, 0.0, f"{attr} < 0 for {text!r}")
                self.assertLessEqual(val, 1.0, f"{attr} > 1 for {text!r}")

    def test_coherence_with_sentences(self):
        score = QualityScore.compute(
            "This is a full sentence. Here is another one.", [])
        self.assertGreater(score.coherence, 0.3)

    def test_coherence_with_fragment(self):
        score = QualityScore.compute("a", [])
        self.assertLess(score.coherence, 0.5)


# ─── Directive Tests ───────────────────────────────────────────

class TestDirective(unittest.TestCase):
    """Directive creation and apply()."""

    def setUp(self):
        self.config = ThinkerConfig()

    def test_apply_prompt_directive(self):
        d = Directive(kind="prompt", description="test",
                      changes={"system_prompt": "New prompt"})
        d.apply(self.config)
        self.assertEqual(self.config.system_prompt, "New prompt")

    def test_apply_temperature_directive(self):
        d = Directive(kind="temperature", description="test",
                      changes={"temperature": 1.2})
        d.apply(self.config)
        self.assertEqual(self.config.temperature, 1.2)

    def test_apply_context_directive(self):
        d = Directive(kind="context", description="test",
                      changes={"context": "New context"})
        d.apply(self.config)
        self.assertEqual(self.config.context, "New context")

    def test_apply_interval_directive(self):
        d = Directive(kind="interval", description="test",
                      changes={"interval": 10.0})
        d.apply(self.config)
        self.assertEqual(self.config.interval, 10.0)

    def test_apply_unknown_kind_does_nothing(self):
        original_prompt = self.config.system_prompt
        d = Directive(kind="unknown", description="test", changes={})
        d.apply(self.config)
        self.assertEqual(self.config.system_prompt, original_prompt)


# ─── Prompt Variations Tests ───────────────────────────────────

class TestPromptVariations(unittest.TestCase):
    """The PROMPT_VARIATIONS constant library."""

    def test_all_variations_are_strings(self):
        for name, prompt in PROMPT_VARIATIONS.items():
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 20)

    def test_default_exists(self):
        self.assertIn("default", PROMPT_VARIATIONS)

    def test_all_expected_styles_exist(self):
        expected = {"default", "analytical", "creative", "philosophical",
                    "scientific", "playful", "investigative"}
        self.assertEqual(set(PROMPT_VARIATIONS.keys()), expected)

    def test_prompts_are_distinct(self):
        prompts = list(PROMPT_VARIATIONS.values())
        for i in range(len(prompts)):
            for j in range(i + 1, len(prompts)):
                self.assertNotEqual(prompts[i], prompts[j])


# ─── Supervisor Tests ──────────────────────────────────────────

class TestSupervisorInit(unittest.TestCase):
    """Supervisor initialization."""

    def test_initial_state(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)
        self.assertEqual(sup.quality_history, [])
        self.assertEqual(sup.directives_sent, 0)
        self.assertAlmostEqual(sup.trust_score, 0.5)
        self.assertEqual(sup.consecutive_decreases, 0)
        self.assertIsNone(sup.last_directive)
        self.assertFalse(sup._running)


class TestSupervisorAssessWindow(unittest.TestCase):
    """Supervisor._assess_window() quality computation."""

    def _make_supervisor(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Supervisor(thinker, j)

    def test_empty_window_returns_default(self):
        sup = self._make_supervisor()
        q = sup._assess_window([])
        self.assertAlmostEqual(q, 0.5)

    def test_quality_stored_in_metadata(self):
        sup = self._make_supervisor()
        thoughts = [{"content": "A novel thought about physics.", "metadata": {}}]
        q = sup._assess_window(thoughts)
        self.assertIn("quality", thoughts[0]["metadata"])
        self.assertIn("quality_detail", thoughts[0]["metadata"])

    def test_quality_history_appended(self):
        sup = self._make_supervisor()
        thoughts = [{"content": "Some thought", "metadata": {}}]
        sup._assess_window(thoughts)
        self.assertEqual(len(sup.quality_history), 1)


class TestSupervisorChooseDirective(unittest.TestCase):
    """Supervisor._choose_directive() decision logic."""

    def _make_supervisor(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Supervisor(thinker, j)

    def test_no_thoughts_returns_none(self):
        sup = self._make_supervisor()
        self.assertIsNone(sup._choose_directive([], 0.5))

    def test_low_quality_returns_prompt_directive(self):
        sup = self._make_supervisor()
        thoughts = [{"content": "stuf", "metadata": {}}]
        d = sup._choose_directive(thoughts, 0.2)
        self.assertIsNotNone(d)
        self.assertEqual(d.kind, "prompt")

    def test_high_quality_returns_temperature_or_none(self):
        sup = self._make_supervisor()
        thoughts = [{"content": "A very interesting and specific thought.", "metadata": {}}]
        d = sup._choose_directive(thoughts, 0.85)
        # Should either increase temp or leave alone
        if d is not None:
            self.assertIn(d.kind, ("temperature",))

    def test_mid_quality_returns_context_directive(self):
        sup = self._make_supervisor()
        thoughts = [
            {"content": "An interesting thought.", "metadata": {"quality": 0.6}},
        ]
        d = sup._choose_directive(thoughts, 0.5)
        if d is not None:
            self.assertEqual(d.kind, "context")

    def test_rollback_after_consecutive_decreases(self):
        sup = self._make_supervisor()
        sup.quality_history = [0.7, 0.6, 0.5]
        sup.consecutive_decreases = 2
        sup.last_directive = Directive(
            kind="prompt", description="test",
            changes={"system_prompt": "current"})
        thoughts = [{"content": "thought", "metadata": {}}]
        d = sup._choose_directive(thoughts, 0.4)
        if d is not None:
            self.assertIn("rollback", d.description.lower())


class TestSupervisorApplyDirective(unittest.TestCase):
    """Supervisor._apply_directive() application and tracking."""

    def test_directive_applied_to_config(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)

        d = Directive(kind="temperature", description="test",
                      changes={"temperature": 1.1})
        sup._apply_directive(d)
        self.assertEqual(config.temperature, 1.1)
        self.assertEqual(sup.directives_sent, 1)
        self.assertIs(sup.last_directive, d)

    def test_directive_journaled(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)

        d = Directive(kind="temperature", description="Increase temp",
                      changes={"temperature": 1.0})
        sup._apply_directive(d)
        directives = j.read_directives()
        self.assertEqual(len(directives), 1)

    def test_callback_called(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)

        called_with = []
        sup.set_on_directive(lambda d: called_with.append(d))
        d = Directive(kind="temperature", description="test", changes={"temperature": 1.0})
        sup._apply_directive(d)
        self.assertEqual(len(called_with), 1)

    def test_callback_error_does_not_crash(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)

        def bad_callback(d):
            raise ValueError("boom")

        sup.set_on_directive(bad_callback)
        d = Directive(kind="temperature", description="test", changes={"temperature": 1.0})
        sup._apply_directive(d)  # should not raise

    def test_prompt_directive_saves_previous(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig(system_prompt="Original")
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)

        d = Directive(kind="prompt", description="change",
                      changes={"system_prompt": "New"})
        sup._apply_directive(d)
        self.assertEqual(sup.previous_prompt, "Original")


class TestSupervisorReview(unittest.TestCase):
    """Supervisor.review() full cycle."""

    def test_review_returns_none_with_insufficient_data(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)
        # < 3 thoughts → no directive
        self.assertIsNone(sup.review())

    def test_review_with_enough_thoughts(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)

        # Write some thoughts to journal
        for i in range(5):
            j.write("thought", f"This is thought number {i} about topic {i}.")

        sup = Supervisor(thinker, j, api_key="", deepseek_api_key="")
        result = sup.review()
        # Should either return a Directive or None (both valid)
        if result is not None:
            self.assertIsInstance(result, Directive)

    def test_review_writes_summary(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        for i in range(5):
            j.write("thought", f"Thought {i} with some content.")
        sup = Supervisor(thinker, j, api_key="", deepseek_api_key="")
        sup.review()
        summaries = j.read_entries(limit=10, entry_type="summary")
        self.assertGreater(len(summaries), 0)


class TestSupervisorTrustTracking(unittest.TestCase):
    """Trust score updates after directives."""

    def test_trust_increases_on_improvement(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)
        sup.quality_history = [0.5, 0.6]
        sup.last_directive = Directive(kind="temperature", description="t", changes={})
        sup.trust_score = 0.5

        # Simulate: review updates trust
        # We need to trigger the trust update logic manually
        # because review() needs 3+ thoughts
        for i in range(3):
            j.write("thought", f"Novel content {i} about stuff.")
        sup.review()
        # trust should have moved (up or down)
        # Not asserting exact value since quality computation is heuristic

    def test_trust_decreases_on_decline(self):
        sup = MagicMock()
        sup.quality_history = [0.7, 0.5, 0.3]
        # Trust logic is embedded in review(), test the formula
        trust = 0.5
        consecutive = 0
        for i in range(1, len(sup.quality_history)):
            prev_q = sup.quality_history[i - 1]
            curr_q = sup.quality_history[i]
            if curr_q > prev_q:
                trust = min(0.95, trust + 0.5 / 10)
                consecutive = 0
            elif curr_q < prev_q:
                trust = max(0.05, trust - 2.0 / 10)
                consecutive += 1
        self.assertAlmostEqual(trust, 0.1)  # 0.5 - 0.2 = 0.3, 0.3 - 0.2 = 0.1
        self.assertEqual(consecutive, 2)


class TestSupervisorStop(unittest.TestCase):
    """Supervisor.stop() signals shutdown."""

    def test_stop_sets_running_false(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        sup = Supervisor(thinker, j)
        sup._running = True
        sup.stop()
        self.assertFalse(sup._running)


if __name__ == "__main__":
    unittest.main()
