"""
Tests for distillation loop error handling paths.

Covers:
  - HTTP retry logic (curl_post_json)
  - Teacher stage: API failures, empty responses, timeouts
  - Student stage: Ollama down, empty responses, watchdog recovery
  - Run iteration: partial failures (teacher fails, student fails)
  - Stats computation with mixed success/failure
  - Domain rotation logic
"""

import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repo to path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class TestCurlPostJson(unittest.TestCase):
    """Test the HTTP utility with retry logic."""

    def test_successful_response(self):
        """Normal response parses correctly."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"choices": [{"message": {"content": "hello"}}]}\n200',
                stderr="",
            )
            result = _curl_post_json(
                "http://example.com", {}, {"test": True}, timeout=5,
            )
        self.assertEqual(result["choices"][0]["message"]["content"], "hello")

    def test_network_error_retries(self):
        """Network errors trigger retries."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run, \
             patch("time.sleep") as mock_sleep:
            mock_run.side_effect = subprocess.TimeoutExpired("curl", 30)
            result = _curl_post_json(
                "http://example.com", {}, {"test": True},
                timeout=5, retries=3, backoff_base=0.01,
            )
        self.assertIn("error", result)
        self.assertIn("3 attempts", result["error"])
        self.assertEqual(mock_run.call_count, 3)
        # Only sleeps between retries (not after the last attempt)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_http_429_retries(self):
        """HTTP 429 triggers retry."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run, \
             patch("time.sleep"):
            # First call: 429, Second call: 200
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout='{"error": "rate limited"}\n429', stderr=""),
                MagicMock(returncode=0, stdout='{"ok": true}\n200', stderr=""),
            ]
            result = _curl_post_json(
                "http://example.com", {}, {"test": True},
                timeout=5, retries=3, backoff_base=0.01,
            )
        self.assertEqual(result, {"ok": True})

    def test_http_4xx_no_retry(self):
        """HTTP 4xx (non-429) does not retry."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"error": "bad request"}\n400',
                stderr="",
            )
            result = _curl_post_json(
                "http://example.com", {}, {"test": True},
                timeout=5, retries=3,
            )
        self.assertIn("error", result)
        self.assertIn("HTTP 400", result["error"])
        self.assertEqual(mock_run.call_count, 1)

    def test_json_decode_error_retries(self):
        """Malformed JSON triggers retry."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run, \
             patch("time.sleep"):
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="not json\n200", stderr=""),
                MagicMock(returncode=0, stdout='{"ok": true}\n200', stderr=""),
            ]
            result = _curl_post_json(
                "http://example.com", {}, {"test": True},
                timeout=5, retries=3, backoff_base=0.01,
            )
        self.assertEqual(result, {"ok": True})

    def test_all_retries_exhausted(self):
        """All retries failing returns error dict."""
        from distillation_loop import _curl_post_json

        with patch("subprocess.run") as mock_run, \
             patch("time.sleep"):
            mock_run.side_effect = subprocess.TimeoutExpired("curl", 30)
            result = _curl_post_json(
                "http://example.com", {}, {"test": True},
                timeout=5, retries=2, backoff_base=0.01,
            )
        self.assertIn("error", result)
        self.assertIn("2 attempts", result["error"])


class TestStageTeacher(unittest.TestCase):
    """Test the teacher stage error handling."""

    @patch("distillation_loop._curl_post_json")
    def test_teacher_success(self, mock_curl):
        """Successful teacher call returns proper artifact."""
        from distillation_loop import stage_teacher

        mock_curl.return_value = {
            "choices": [{"message": {"content": "Lesson about Lua tables"}}],
            "usage": {"total_tokens": 100},
        }
        result = stage_teacher("roblox", "Lua tables", 1)

        self.assertTrue(result["success"])
        self.assertEqual(result["lesson"], "Lesson about Lua tables")
        self.assertEqual(result["domain"], "roblox")

    @patch("distillation_loop._curl_post_json")
    def test_teacher_api_failure(self, mock_curl):
        """API failure is handled gracefully."""
        from distillation_loop import stage_teacher

        mock_curl.return_value = {"error": "connection refused"}
        result = stage_teacher("roblox", "Lua tables", 1)

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["lesson"], "")

    @patch("distillation_loop._curl_post_json")
    def test_teacher_empty_response(self, mock_curl):
        """Empty response is handled properly."""
        from distillation_loop import stage_teacher

        mock_curl.return_value = {
            "choices": [{"message": {"content": ""}}],
            "usage": {},
        }
        result = stage_teacher("roblox", "Lua tables", 1)

        self.assertFalse(result["success"])
        self.assertIn("Empty response", result.get("error", ""))

    @patch("distillation_loop._curl_post_json")
    def test_teacher_no_choices(self, mock_curl):
        """Response with no choices is handled."""
        from distillation_loop import stage_teacher

        mock_curl.return_value = {"choices": [], "usage": {}}
        result = stage_teacher("roblox", "Lua tables", 1)

        self.assertFalse(result["success"])


class TestStageStudent(unittest.TestCase):
    """Test the student stage error handling."""

    @patch("distillation_loop._curl_post_json")
    def test_student_success(self, mock_curl):
        """Successful student call returns proper artifact."""
        from distillation_loop import stage_student

        mock_curl.return_value = {
            "message": {"content": "Here's my analysis..."},
            "eval_count": 50,
            "eval_duration": 1000,
        }
        teacher = {"lesson": "Test lesson", "success": True}
        task = {"task": "Review code", "code": "test.lua"}
        result = stage_student(teacher, task, "code here", True, 1, "roblox")

        self.assertTrue(result["success"])
        self.assertEqual(result["label"], "taught")
        self.assertIn("analysis", result["response"])

    @patch("distillation_loop._curl_post_json")
    def test_student_ollama_down(self, mock_curl):
        """Ollama being down is handled with error artifact."""
        from distillation_loop import stage_student

        mock_curl.return_value = {"error": "connection refused"}
        teacher = {"lesson": "Test lesson", "success": True}
        task = {"task": "Review code", "code": "test.lua"}

        # Mock the watchdog import inside stage_student
        with patch.dict("sys.modules", {"watchdog": MagicMock()}):
            result = stage_student(teacher, task, "code", False, 1, "roblox")

        self.assertFalse(result["success"])
        self.assertIn("error", result["response"].lower())

    @patch("distillation_loop._curl_post_json")
    def test_student_empty_response(self, mock_curl):
        """Empty model response is flagged."""
        from distillation_loop import stage_student

        mock_curl.return_value = {
            "message": {"content": ""},
            "eval_count": 0,
        }
        teacher = {"lesson": "Test", "success": True}
        task = {"task": "Review", "code": "test.lua"}
        result = stage_student(teacher, task, "code", False, 1, "roblox")

        self.assertFalse(result["success"])
        self.assertIn("Empty", result["response"])


class TestRunIteration(unittest.TestCase):
    """Test the full iteration with failure scenarios."""

    @patch("distillation_loop.stage_student")
    @patch("distillation_loop.stage_teacher")
    def test_teacher_failure_skips_iteration(self, mock_teacher, mock_student):
        """When teacher fails, iteration is skipped gracefully."""
        from distillation_loop import run_iteration

        mock_teacher.return_value = {
            "lesson": "",
            "success": False,
            "error": "API timeout",
        }
        result = run_iteration("roblox", 1)

        self.assertFalse(result["success"])
        self.assertEqual(result["delta"], 0.0)
        self.assertFalse(result["teaching_helped"])
        # Student should not be called since teacher failed
        mock_student.assert_not_called()

    @patch("distillation_loop.stage_evaluate")
    @patch("distillation_loop.stage_student")
    @patch("distillation_loop.stage_teacher")
    def test_student_failure_skips_evaluation(
        self, mock_teacher, mock_student, mock_eval
    ):
        """When student fails, evaluation is skipped."""
        from distillation_loop import run_iteration

        mock_teacher.return_value = {
            "lesson": "Great lesson",
            "success": True,
        }
        mock_student.return_value = {
            "response": "(error)",
            "success": False,
        }
        result = run_iteration("roblox", 1)

        self.assertFalse(result["success"])
        # Evaluate should not be called
        mock_eval.assert_not_called()

    @patch("distillation_loop.stage_update_prompt")
    @patch("distillation_loop.stage_distill")
    @patch("distillation_loop.stage_evaluate")
    @patch("distillation_loop.stage_student")
    @patch("distillation_loop.stage_teacher")
    def test_successful_iteration(
        self, mock_teacher, mock_student, mock_eval, mock_distill, mock_update
    ):
        """Fully successful iteration flows through all stages."""
        from distillation_loop import run_iteration

        mock_teacher.return_value = {"lesson": "L1", "success": True, "topic": "T"}
        mock_student.return_value = {"response": "R1", "success": True}
        mock_eval.return_value = {
            "baseline_composite": 0.3,
            "taught_composite": 0.5,
            "delta": 0.2,
            "teaching_helped": True,
            "taught_scores": {"novelty": 0.5, "specificity": 0.5, "engagement": 0.5, "spatial": 0.5},
        }
        mock_distill.return_value = {"compiled": True, "nail_id": "abc123"}
        mock_update.return_value = {"updated": False, "consecutive_positives": 1}

        result = run_iteration("cognition", 1)

        self.assertTrue(result["success"])
        self.assertEqual(result["delta"], 0.2)
        self.assertTrue(result["teaching_helped"])
        self.assertTrue(result["reflex_compiled"])


class TestComputeStats(unittest.TestCase):
    """Test stats computation with mixed success/failure."""

    def test_all_successful(self):
        from distillation_loop import compute_stats

        summaries = [
            {"delta": 0.1, "teaching_helped": True, "reflex_compiled": True,
             "prompt_updated": False, "success": True, "iteration": 1},
            {"delta": -0.05, "teaching_helped": False, "reflex_compiled": False,
             "prompt_updated": False, "success": True, "iteration": 2},
        ]
        stats = compute_stats(summaries)
        self.assertEqual(stats["total_iterations"], 2)
        self.assertEqual(stats["successful_iterations"], 2)
        self.assertEqual(stats["teaching_helped_count"], 1)
        self.assertAlmostEqual(stats["avg_delta"], 0.025, places=3)

    def test_mixed_success_failure(self):
        from distillation_loop import compute_stats

        summaries = [
            {"delta": 0.1, "teaching_helped": True, "reflex_compiled": True,
             "prompt_updated": False, "success": True, "iteration": 1},
            {"delta": 0.0, "teaching_helped": False, "reflex_compiled": False,
             "prompt_updated": False, "success": False, "error": "timeout",
             "iteration": 2},
        ]
        stats = compute_stats(summaries)
        self.assertEqual(stats["total_iterations"], 2)
        self.assertEqual(stats["successful_iterations"], 1)
        self.assertEqual(stats["failed_iterations"], 1)
        self.assertIn("timeout", stats["errors"])

    def test_all_failed(self):
        from distillation_loop import compute_stats

        summaries = [
            {"delta": 0.0, "teaching_helped": False, "reflex_compiled": False,
             "prompt_updated": False, "success": False, "error": "API down",
             "iteration": 1},
        ]
        stats = compute_stats(summaries)
        self.assertEqual(stats["total_iterations"], 1)
        self.assertEqual(stats["successful_iterations"], 0)

    def test_empty(self):
        from distillation_loop import compute_stats

        stats = compute_stats([])
        self.assertEqual(stats, {})


class TestWatchdog(unittest.TestCase):
    """Test the Ollama watchdog."""

    def test_check_ollama_alive_success(self):
        from watchdog import check_ollama_alive

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"models": []}',
                stderr="",
            )
            self.assertTrue(check_ollama_alive())

    def test_check_ollama_alive_failure(self):
        from watchdog import check_ollama_alive

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="connection refused",
            )
            self.assertFalse(check_ollama_alive())

    def test_check_ollama_alive_timeout(self):
        from watchdog import check_ollama_alive

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("curl", 15)
            self.assertFalse(check_ollama_alive())

    def test_check_model_available_present(self):
        from watchdog import check_model_available

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "models": [
                        {"name": "granite3.1-dense:2b"},
                        {"name": "llama3.2:1b"},
                    ]
                }),
                stderr="",
            )
            self.assertTrue(check_model_available())

    def test_check_model_available_absent(self):
        from watchdog import check_model_available

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "models": [{"name": "llama3.2:1b"}]
                }),
                stderr="",
            )
            self.assertFalse(check_model_available())

    def test_health_check_full_healthy(self):
        from watchdog import health_check_full

        with patch("watchdog.check_ollama_alive", return_value=True), \
             patch("watchdog.check_model_available", return_value=True), \
             patch("watchdog.check_gpu_available", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"response": "ok"}),
                stderr="",
            )
            status = health_check_full()

        self.assertTrue(status["ollama_alive"])
        self.assertTrue(status["model_available"])
        self.assertTrue(status["gpu_available"])
        self.assertTrue(status["test_inference"])
        self.assertEqual(status["issues"], [])

    def test_health_check_full_ollama_down(self):
        from watchdog import health_check_full

        with patch("watchdog.check_ollama_alive", return_value=False):
            status = health_check_full()

        self.assertFalse(status["ollama_alive"])
        self.assertIn("Ollama process not responding", status["issues"])

    @patch("watchdog.check_ollama_alive")
    @patch("watchdog.start_ollama")
    @patch("watchdog.ensure_model_pulled")
    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    def test_ensure_healthy_recovery(
        self, mock_sleep, mock_health, mock_pull, mock_start, mock_alive
    ):
        """Test that ensure_healthy recovers from Ollama being down."""
        from watchdog import ensure_healthy

        # First check: down. After restart: up.
        mock_alive.return_value = True
        mock_start.return_value = True
        mock_pull.return_value = True
        mock_health.side_effect = [
            {"ollama_alive": False, "model_available": False,
             "gpu_available": True, "test_inference": False, "issues": ["down"]},
            {"ollama_alive": True, "model_available": True,
             "gpu_available": True, "test_inference": True, "issues": []},
        ]

        result = ensure_healthy(max_attempts=3)
        self.assertTrue(result)
        mock_start.assert_called_once()

    @patch("watchdog.check_ollama_alive", return_value=False)
    @patch("watchdog.start_ollama", return_value=False)
    @patch("watchdog.time.sleep")
    def test_ensure_healthy_all_retries_fail(self, mock_sleep, mock_start, mock_alive):
        """Test that ensure_healthy gives up after max attempts."""
        from watchdog import ensure_healthy

        result = ensure_healthy(max_attempts=2)
        self.assertFalse(result)


class TestMorningBriefing(unittest.TestCase):
    """Test the morning briefing generator."""

    def test_briefing_generation(self):
        from run_overnight import generate_briefing

        summaries = {
            "roblox": [
                {"delta": 0.15, "teaching_helped": True, "reflex_compiled": True,
                 "prompt_updated": False, "success": True, "iteration": 1,
                 "topic": "Luau types", "baseline_score": 0.3, "taught_score": 0.45},
                {"delta": -0.02, "teaching_helped": False, "reflex_compiled": False,
                 "prompt_updated": False, "success": True, "iteration": 2,
                 "topic": "DataStore", "baseline_score": 0.4, "taught_score": 0.38},
            ],
            "maritime": [
                {"delta": 0.08, "teaching_helped": True, "reflex_compiled": True,
                 "prompt_updated": True, "success": True, "iteration": 1,
                 "topic": "Fish populations", "baseline_score": 0.25, "taught_score": 0.33},
            ],
            "cognition": [
                {"delta": 0.0, "teaching_helped": False, "reflex_compiled": False,
                 "prompt_updated": False, "success": False, "error": "API timeout",
                 "iteration": 1, "topic": "Embeddings"},
            ],
            "digital-twin": [],
        }

        briefing = generate_briefing(
            summaries,
            start_time="2026-08-04T08:00:00Z",
            end_time="2026-08-04T14:00:00Z",
            watchdog_events=[
                {"timestamp": "2026-08-04T10:00:00Z", "type": "restart_attempt", "details": {}},
            ],
        )

        # Check structure
        self.assertIn("Night Watch Briefing", briefing)
        self.assertIn("roblox", briefing)
        self.assertIn("maritime", briefing)
        self.assertIn("cognition", briefing)
        self.assertIn("Help rate", briefing)
        self.assertIn("Avg delta", briefing)
        self.assertIn("Watchdog Events", briefing)
        self.assertIn("Surprises", briefing)

        # Check that the promotion was noted
        self.assertIn("⭐", briefing)

        # Check that the error was noted
        self.assertIn("⚠️", briefing)

    def test_briefing_with_no_failures(self):
        from run_overnight import generate_briefing

        summaries = {
            "roblox": [
                {"delta": 0.1, "teaching_helped": True, "reflex_compiled": True,
                 "prompt_updated": False, "success": True, "iteration": 1,
                 "topic": "T1", "baseline_score": 0.3, "taught_score": 0.4},
            ],
            "maritime": [],
            "cognition": [],
            "digital-twin": [],
        }

        briefing = generate_briefing(
            summaries,
            "2026-08-04T08:00:00Z",
            "2026-08-04T10:00:00Z",
            [],
        )

        self.assertIn("Nothing surprising", briefing)
        self.assertIn("No watchdog events", briefing)

    def test_briefing_negative_delta_flagged(self):
        from run_overnight import generate_briefing

        summaries = {
            "cognition": [
                {"delta": -0.1, "teaching_helped": False, "reflex_compiled": False,
                 "prompt_updated": False, "success": True, "iteration": 1,
                 "topic": "Bad topic", "baseline_score": 0.5, "taught_score": 0.4},
            ],
            "roblox": [],
            "maritime": [],
            "digital-twin": [],
        }

        briefing = generate_briefing(
            summaries, "2026-08-04T08:00:00Z", "2026-08-04T10:00:00Z", []
        )

        self.assertIn("📉", briefing)


class TestDomainRotation(unittest.TestCase):
    """Test that domain rotation covers all domains correctly."""

    def test_all_domains_present(self):
        from run_overnight import ALL_DOMAINS

        expected = {"roblox", "maritime", "cognition", "digital-twin"}
        self.assertEqual(set(ALL_DOMAINS), expected)

    def test_domain_topics_exist(self):
        from distillation_loop import TEACHING_TOPICS

        for domain in ["roblox", "maritime", "cognition", "digital-twin"]:
            topics = TEACHING_TOPICS.get(domain, [])
            self.assertGreaterEqual(
                len(topics), 5,
                f"Domain {domain} needs at least 5 topics for rotation, has {len(topics)}",
            )

    def test_domain_tasks_exist(self):
        from distillation_loop import TASK_SOURCES

        for domain in ["roblox", "maritime", "cognition", "digital-twin"]:
            tasks = TASK_SOURCES.get(domain, [])
            self.assertGreaterEqual(
                len(tasks), 3,
                f"Domain {domain} needs at least 3 tasks, has {len(tasks)}",
            )


if __name__ == "__main__":
    unittest.main()
