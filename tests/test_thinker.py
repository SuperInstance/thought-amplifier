"""
Tests for core/thinker.py — ThinkerConfig, Thinker, backend detection.

Covers:
  - ThinkerConfig defaults and custom values
  - Thinker initialization and state
  - Backend detection priority (ollama → glm → deepseek)
  - generate_one() with mocked backends
  - think_once() journaling
  - Callback handling
  - Error handling (all backends fail)
  - Stop/run signals
  - resolve_api_keys() from env and .bashrc
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.journal import Journal
from core.thinker import (
    ThinkerConfig, Thinker, detect_backend, check_ollama,
    resolve_api_keys, generate_ollama, generate_glm, generate_deepseek,
    GENERATORS, _curl_post_json, _curl_get_json,
)


class TestThinkerConfig(unittest.TestCase):
    """ThinkerConfig dataclass."""

    def test_defaults(self):
        c = ThinkerConfig()
        self.assertEqual(c.ollama_url, "http://localhost:11434")
        self.assertEqual(c.ollama_model, "granite3.1-dense:2b")
        self.assertEqual(c.temperature, 0.9)
        self.assertEqual(c.max_tokens, 200)
        self.assertEqual(c.interval, 5.0)
        self.assertEqual(c.context, "")
        self.assertGreater(len(c.system_prompt), 20)
        self.assertEqual(len(c.backend_priority), 3)
        self.assertIn("ollama", c.backend_priority)

    def test_custom_values(self):
        c = ThinkerConfig(
            ollama_model="qwen2.5:7b",
            temperature=0.5,
            interval=10.0,
            context="Custom context",
            glm_api_key="test-key",
        )
        self.assertEqual(c.ollama_model, "qwen2.5:7b")
        self.assertEqual(c.temperature, 0.5)
        self.assertEqual(c.interval, 10.0)
        self.assertEqual(c.context, "Custom context")
        self.assertEqual(c.glm_api_key, "test-key")

    def test_backend_priority_default(self):
        c = ThinkerConfig()
        self.assertEqual(c.backend_priority, ["ollama", "glm", "deepseek"])

    def test_system_prompt_is_substantial(self):
        c = ThinkerConfig()
        self.assertGreater(len(c.system_prompt), 100,
                           "Default prompt should have meaningful content")


class TestCheckOllama(unittest.TestCase):

    @patch("core.thinker._curl_get_json")
    def test_available(self, mock_get):
        mock_get.return_value = {"models": []}
        self.assertTrue(check_ollama())

    @patch("core.thinker._curl_get_json")
    def test_unavailable(self, mock_get):
        mock_get.side_effect = RuntimeError("connection refused")
        self.assertFalse(check_ollama())

    @patch("core.thinker._curl_get_json")
    def test_no_models_key(self, mock_get):
        mock_get.return_value = {"status": "ok"}
        self.assertFalse(check_ollama())

    @patch("core.thinker._curl_get_json")
    def test_custom_url(self, mock_get):
        check_ollama("http://custom:1234")
        mock_get.assert_called_once()
        args = mock_get.call_args[0]
        self.assertIn("custom:1234", args[0])


class TestDetectBackend(unittest.TestCase):

    def test_ollama_first_if_available(self):
        config = ThinkerConfig(glm_api_key="k", deepseek_api_key="k")
        with patch("core.thinker.check_ollama", return_value=True):
            self.assertEqual(detect_backend(config), "ollama")

    def test_glm_if_no_ollama(self):
        config = ThinkerConfig(glm_api_key="glk", deepseek_api_key="dsk")
        with patch("core.thinker.check_ollama", return_value=False):
            self.assertEqual(detect_backend(config), "glm")

    def test_deepseek_if_no_ollama_no_glm(self):
        config = ThinkerConfig(glm_api_key="", deepseek_api_key="dsk")
        with patch("core.thinker.check_ollama", return_value=False):
            self.assertEqual(detect_backend(config), "deepseek")

    def test_deepseek_as_last_resort_with_any_key(self):
        config = ThinkerConfig(glm_api_key="g", deepseek_api_key="d")
        with patch("core.thinker.check_ollama", return_value=False):
            # With both keys, priority says glm first
            self.assertEqual(detect_backend(config), "glm")

    def test_raises_if_no_backend(self):
        config = ThinkerConfig(glm_api_key="", deepseek_api_key="")
        with patch("core.thinker.check_ollama", return_value=False):
            with self.assertRaises(RuntimeError):
                detect_backend(config)

    def test_custom_priority(self):
        config = ThinkerConfig(
            glm_api_key="g",
            deepseek_api_key="d",
            backend_priority=["deepseek", "glm", "ollama"]
        )
        with patch("core.thinker.check_ollama", return_value=False):
            self.assertEqual(detect_backend(config), "deepseek")


class TestGenerateFunctions(unittest.TestCase):

    def test_generate_ollama_builds_payload(self):
        config = ThinkerConfig()
        with patch("core.thinker._curl_post_json") as mock_post:
            mock_post.return_value = {"message": {"content": "test thought"}}
            result = generate_ollama(config)
            self.assertEqual(result, "test thought")
            mock_post.assert_called_once()

    def test_generate_ollama_handles_empty(self):
        config = ThinkerConfig()
        with patch("core.thinker._curl_post_json") as mock_post:
            mock_post.return_value = {"message": {}}
            result = generate_ollama(config)
            self.assertEqual(result, "")

    def test_generate_glm_no_key_raises(self):
        config = ThinkerConfig(glm_api_key="")
        with self.assertRaises(RuntimeError):
            generate_glm(config)

    def test_generate_glm_success(self):
        config = ThinkerConfig(glm_api_key="test")
        with patch("core.thinker._curl_post_json") as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": "GLM thought"}}]}
            result = generate_glm(config)
            self.assertEqual(result, "GLM thought")

    def test_generate_deepseek_no_key_raises(self):
        config = ThinkerConfig(deepseek_api_key="")
        with self.assertRaises(RuntimeError):
            generate_deepseek(config)

    def test_generate_deepseek_success(self):
        config = ThinkerConfig(deepseek_api_key="test")
        with patch("core.thinker._curl_post_json") as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": "DS thought"}}]}
            result = generate_deepseek(config)
            self.assertEqual(result, "DS thought")

    def test_generators_dict_has_all_backends(self):
        self.assertIn("ollama", GENERATORS)
        self.assertIn("glm", GENERATORS)
        self.assertIn("deepseek", GENERATORS)


class TestThinker(unittest.TestCase):

    def _make_thinker(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        return Thinker(config, j), j

    def test_init_defaults(self):
        thinker, j = self._make_thinker()
        self.assertIsNone(thinker.backend)
        self.assertEqual(thinker.thought_count, 0)
        self.assertFalse(thinker._running)
        self.assertIsNone(thinker._on_thought)

    def test_set_on_thought_callback(self):
        thinker, _ = self._make_thinker()
        callback = lambda e: None
        thinker.set_on_thought(callback)
        self.assertIs(thinker._on_thought, callback)

    def test_backend_model_name(self):
        thinker, _ = self._make_thinker()
        thinker.backend = "ollama"
        self.assertEqual(thinker._backend_model_name(), "granite3.1-dense:2b")
        thinker.backend = "glm"
        self.assertEqual(thinker._backend_model_name(), "glm-4-flash")
        thinker.backend = "deepseek"
        self.assertEqual(thinker._backend_model_name(), "deepseek-chat")
        thinker.backend = "unknown"
        self.assertEqual(thinker._backend_model_name(), "unknown")

    def test_generate_one_with_ollama(self):
        thinker, _ = self._make_thinker()
        with patch("core.thinker.check_ollama", return_value=True), \
             patch.dict("core.thinker.GENERATORS", {"ollama": lambda c: "A thought"}):
            result = thinker.generate_one()
            self.assertEqual(result, "A thought")
            self.assertEqual(thinker.backend, "ollama")

    def test_generate_one_fallback_to_glm(self):
        thinker, _ = self._make_thinker()
        thinker.config.glm_api_key = "test"
        with patch("core.thinker.check_ollama", return_value=False), \
             patch.dict("core.thinker.GENERATORS", {"glm": lambda c: "GLM thought"}):
            result = thinker.generate_one()
            self.assertEqual(result, "GLM thought")

    def test_generate_one_all_fail_raises(self):
        thinker, _ = self._make_thinker()
        with patch("core.thinker.check_ollama", return_value=False):
            with self.assertRaises(RuntimeError):
                thinker.generate_one()

    def test_generate_one_empty_result_falls_through(self):
        thinker, _ = self._make_thinker()
        thinker.config.glm_api_key = "test"
        with patch("core.thinker.check_ollama", return_value=True), \
             patch.dict("core.thinker.GENERATORS", {
                 "ollama": lambda c: "",
                 "glm": lambda c: "GLM backup",
             }):
            result = thinker.generate_one()
            self.assertEqual(result, "GLM backup")

    def test_think_once_journals_thought(self):
        thinker, j = self._make_thinker()
        with patch.object(thinker, "generate_one", return_value="Test thought"):
            entry = thinker.think_once()
            self.assertEqual(entry["type"], "thought")
            self.assertEqual(entry["content"], "Test thought")
            self.assertEqual(thinker.thought_count, 1)

    def test_think_once_handles_error(self):
        thinker, j = self._make_thinker()
        with patch.object(thinker, "generate_one", side_effect=RuntimeError("fail")):
            entry = thinker.think_once()
            self.assertEqual(entry["type"], "system")
            self.assertIn("failed", entry["content"].lower())

    def test_think_once_calls_callback(self):
        thinker, _ = self._make_thinker()
        called = []
        thinker.set_on_thought(lambda e: called.append(e))
        with patch.object(thinker, "generate_one", return_value="thought"):
            thinker.think_once()
            self.assertEqual(len(called), 1)

    def test_think_once_callback_error_swallowed(self):
        thinker, _ = self._make_thinker()
        def bad_cb(e):
            raise ValueError("boom")
        thinker.set_on_thought(bad_cb)
        with patch.object(thinker, "generate_one", return_value="thought"):
            thinker.think_once()  # should not raise

    def test_thought_metadata(self):
        thinker, _ = self._make_thinker()
        thinker.backend = "ollama"
        with patch.object(thinker, "generate_one", return_value="Test"):
            entry = thinker.think_once()
            self.assertEqual(entry["metadata"]["backend"], "ollama")
            self.assertEqual(entry["metadata"]["model"], "granite3.1-dense:2b")
            self.assertEqual(entry["metadata"]["temperature"], 0.9)
            self.assertEqual(entry["metadata"]["thought_number"], 1)

    def test_stop_sets_running_false(self):
        thinker, _ = self._make_thinker()
        thinker._running = True
        thinker.stop()
        self.assertFalse(thinker._running)


class TestResolveApiKeys(unittest.TestCase):

    def test_from_env(self):
        with patch.dict("os.environ", {"ZAI_API_KEY": "zai-k", "DEEPSEEK_API_KEY": "ds-k"}):
            keys = resolve_api_keys()
            self.assertEqual(keys.get("glm"), "zai-k")
            self.assertEqual(keys.get("deepseek"), "ds-k")

    def test_z_ai_key_var(self):
        with patch.dict("os.environ", {"Z_AI_API_KEY": "zai-k2"}, clear=False):
            keys = resolve_api_keys()
            self.assertEqual(keys.get("glm"), "zai-k2")

    def test_zhipu_key_var(self):
        import os
        env = {k: v for k, v in os.environ.items()}
        env.pop("ZAI_API_KEY", None)
        env.pop("Z_AI_API_KEY", None)
        env["ZHIPUAI_API_KEY"] = "zhipu-k"
        with patch.dict("os.environ", env, clear=True):
            keys = resolve_api_keys()
            self.assertEqual(keys.get("glm"), "zhipu-k")

    def test_no_keys_returns_empty(self):
        env = {}
        with patch.dict("os.environ", env, clear=True), \
             patch("builtins.open", side_effect=FileNotFoundError):
            keys = resolve_api_keys()
            self.assertEqual(keys, {})


class TestCurlFunctions(unittest.TestCase):

    @patch("subprocess.run")
    def test_curl_post_json_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}', stderr="")
        result = _curl_post_json("http://test", {"key": "value"})
        self.assertEqual(result, {"ok": True})

    @patch("subprocess.run")
    def test_curl_post_json_curl_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        with self.assertRaises(RuntimeError):
            _curl_post_json("http://test", {})

    @patch("subprocess.run")
    def test_curl_post_json_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("curl", 30)
        with self.assertRaises(RuntimeError):
            _curl_post_json("http://test", {})

    @patch("subprocess.run")
    def test_curl_post_json_bad_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        with self.assertRaises(RuntimeError):
            _curl_post_json("http://test", {})

    @patch("subprocess.run")
    def test_curl_get_json_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}', stderr="")
        result = _curl_get_json("http://test")
        self.assertEqual(result, {"ok": True})

    @patch("subprocess.run")
    def test_curl_get_json_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        with self.assertRaises(RuntimeError):
            _curl_get_json("http://test")

    @patch("subprocess.run")
    def test_curl_post_json_with_headers(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}', stderr="")
        _curl_post_json("http://test", {}, headers={"Auth": "Bearer xyz"})
        cmd = mock_run.call_args[0][0]
        self.assertIn("Auth: Bearer xyz", cmd)


if __name__ == "__main__":
    unittest.main()
