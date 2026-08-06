"""
Tests for watchdog.py — Ollama watchdog health checks, logging, and recovery.

All subprocess calls are mocked to avoid needing a real Ollama/GPU environment.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

import watchdog


# ─── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def reset_env(monkeypatch):
    """Reset watchdog environment variables to defaults."""
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BIN", raising=False)


@pytest.fixture
def mock_curl_success():
    """Mock subprocess.run for a successful curl to Ollama API."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps({"models": [{"name": "granite3.1-dense:2b"}]})
    result.stderr = ""
    return result


@pytest.fixture
def mock_curl_empty():
    """Mock subprocess.run for curl returning empty/invalid response."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


@pytest.fixture
def mock_curl_fail():
    """Mock subprocess.run for a failed curl."""
    result = MagicMock()
    result.returncode = 1
    result.stdout = ""
    result.stderr = "connection refused"
    return result


# ─── Timestamp Tests ───────────────────────────────────────────

class TestTimestamps:
    def test_timestamp_format(self):
        ts = watchdog._timestamp()
        assert len(ts) == 15  # YYYYMMDD_HHMMSS
        assert ts[8] == "_"
        # Should be parseable
        datetime.strptime(ts, "%Y%m%d_%H%M%S")

    def test_timestamp_utc(self):
        """Timestamp should be in UTC."""
        ts = watchdog._timestamp()
        now_utc = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Allow for the second ticking over during the test
        assert abs(int(ts[9:]) - int(now_utc[9:])) <= 1

    def test_iso_ts_format(self):
        ts = watchdog._iso_ts()
        # ISO format with timezone
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None

    def test_iso_ts_utc(self):
        ts = watchdog._iso_ts()
        parsed = datetime.fromisoformat(ts)
        # Should be UTC
        assert parsed.utcoffset().total_seconds() == 0

    def test_iso_ts_returns_string(self):
        assert isinstance(watchdog._iso_ts(), str)


# ─── Log Event Tests ───────────────────────────────────────────

class TestLogEvent:
    def test_log_event_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", tmp_path / "wd.jsonl")
        result = watchdog.log_event("test_event")
        assert isinstance(result, dict)
        assert result["type"] == "test_event"
        assert "timestamp" in result

    def test_log_event_with_details(self, tmp_path, monkeypatch):
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", tmp_path / "wd.jsonl")
        details = {"key": "value", "count": 42}
        result = watchdog.log_event("detail_event", details)
        assert result["details"] == details

    def test_log_event_no_details(self, tmp_path, monkeypatch):
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", tmp_path / "wd.jsonl")
        result = watchdog.log_event("bare_event")
        assert result["details"] == {}

    def test_log_event_none_details(self, tmp_path, monkeypatch):
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", tmp_path / "wd.jsonl")
        result = watchdog.log_event("none_event", None)
        assert result["details"] == {}

    def test_log_event_writes_to_file(self, tmp_path, monkeypatch):
        log_path = tmp_path / "wd.jsonl"
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", log_path)
        watchdog.log_event("write_test", {"data": "hello"})
        content = log_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["type"] == "write_test"
        assert entry["details"]["data"] == "hello"

    def test_log_event_appends(self, tmp_path, monkeypatch):
        log_path = tmp_path / "wd.jsonl"
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", log_path)
        watchdog.log_event("first")
        watchdog.log_event("second")
        watchdog.log_event("third")
        content = log_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["type"] == "first"
        assert json.loads(lines[2])["type"] == "third"

    def test_log_event_unicode(self, tmp_path, monkeypatch):
        log_path = tmp_path / "wd.jsonl"
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", log_path)
        watchdog.log_event("unicode_test", {"msg": "héllo 世界 🐟"})
        content = log_path.read_text(encoding="utf-8")
        entry = json.loads(content)
        assert entry["details"]["msg"] == "héllo 世界 🐟"

    def test_log_event_ensure_ascii_false(self, tmp_path, monkeypatch):
        """JSON should use ensure_ascii=False for readable logs."""
        log_path = tmp_path / "wd.jsonl"
        monkeypatch.setattr(watchdog, "WATCHDOG_LOG", log_path)
        watchdog.log_event("ascii_test", {"msg": "café"})
        content = log_path.read_text(encoding="utf-8")
        # If ensure_ascii=True, this would be "caf\u00e9"
        assert "café" in content


# ─── Check Ollama Alive Tests ──────────────────────────────────

class TestCheckOllamaAlive:
    @patch("watchdog.subprocess.run")
    def test_alive_success(self, mock_run, mock_curl_success):
        mock_run.return_value = mock_curl_success
        assert watchdog.check_ollama_alive() is True

    @patch("watchdog.subprocess.run")
    def test_alive_fail_returncode(self, mock_run, mock_curl_fail):
        mock_run.return_value = mock_curl_fail
        assert watchdog.check_ollama_alive() is False

    @patch("watchdog.subprocess.run")
    def test_alive_empty_stdout(self, mock_run, mock_curl_empty):
        mock_run.return_value = mock_curl_empty
        assert watchdog.check_ollama_alive() is False

    @patch("watchdog.subprocess.run")
    def test_alive_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("curl", 15)
        assert watchdog.check_ollama_alive() is False

    @patch("watchdog.subprocess.run")
    def test_alive_json_decode_error(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "not json at all"
        mock_run.return_value = result
        assert watchdog.check_ollama_alive() is False

    @patch("watchdog.subprocess.run")
    def test_alive_generic_exception(self, mock_run):
        mock_run.side_effect = OSError("boom")
        assert watchdog.check_ollama_alive() is False

    @patch("watchdog.subprocess.run")
    def test_alive_models_key_present(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"models": []})
        mock_run.return_value = result
        assert watchdog.check_ollama_alive() is True

    @patch("watchdog.subprocess.run")
    def test_alive_dict_without_models(self, mock_run):
        """A dict response without 'models' key should still return True (isinstance check)."""
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"status": "ok"})
        mock_run.return_value = result
        assert watchdog.check_ollama_alive() is True


# ─── Check Model Available Tests ───────────────────────────────

class TestCheckModelAvailable:
    @patch("watchdog.subprocess.run")
    def test_model_present(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({
            "models": [{"name": "granite3.1-dense:2b"}, {"name": "qwen2.5:7b"}]
        })
        mock_run.return_value = result
        assert watchdog.check_model_available() is True

    @patch("watchdog.subprocess.run")
    def test_model_absent(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({
            "models": [{"name": "qwen2.5:7b"}, {"name": "llama3:8b"}]
        })
        mock_run.return_value = result
        assert watchdog.check_model_available() is False

    @patch("watchdog.subprocess.run")
    def test_empty_models_list(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"models": []})
        mock_run.return_value = result
        assert watchdog.check_model_available() is False

    @patch("watchdog.subprocess.run")
    def test_curl_fail(self, mock_run, mock_curl_fail):
        mock_run.return_value = mock_curl_fail
        assert watchdog.check_model_available() is False

    @patch("watchdog.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("curl", 15)
        assert watchdog.check_model_available() is False

    @patch("watchdog.subprocess.run")
    def test_json_error(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "invalid"
        mock_run.return_value = result
        assert watchdog.check_model_available() is False

    @patch("watchdog.subprocess.run")
    def test_custom_model_env(self, mock_run, monkeypatch):
        monkeypatch.setattr(watchdog, "OLLAMA_MODEL", "custom-model:latest")
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({
            "models": [{"name": "custom-model:latest"}]
        })
        mock_run.return_value = result
        assert watchdog.check_model_available() is True


# ─── Check GPU Available Tests ─────────────────────────────────

class TestCheckGpuAvailable:
    @patch("watchdog.subprocess.run")
    def test_nvidia_smi_success(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "NVIDIA GeForce RTX 4050, 6144 MiB, 1024 MiB"
        mock_run.return_value = result
        assert watchdog.check_gpu_available() is True

    @patch("watchdog.subprocess.run")
    def test_nvidia_smi_fail(self, mock_run):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "no devices"
        mock_run.return_value = result
        # Falls through to /proc/driver/nvidia check
        with patch("pathlib.Path.exists", return_value=False):
            assert watchdog.check_gpu_available() is False

    @patch("watchdog.subprocess.run")
    def test_nvidia_smi_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        with patch("pathlib.Path.exists", return_value=False):
            assert watchdog.check_gpu_available() is False

    @patch("watchdog.subprocess.run")
    def test_nvidia_smi_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 10)
        with patch("pathlib.Path.exists", return_value=False):
            assert watchdog.check_gpu_available() is False

    @patch("watchdog.subprocess.run")
    def test_nvidia_smi_empty_stdout(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        mock_run.return_value = result
        with patch("pathlib.Path.exists", return_value=False):
            assert watchdog.check_gpu_available() is False

    @patch("watchdog.subprocess.run")
    def test_proc_driver_nvidia_exists(self, mock_run):
        mock_run.side_effect = FileNotFoundError("no nvidia-smi")
        with patch("pathlib.Path.exists", return_value=True):
            assert watchdog.check_gpu_available() is True

    @patch("watchdog.subprocess.run")
    def test_no_gpu_returns_false(self, mock_run):
        mock_run.side_effect = FileNotFoundError("no nvidia-smi")
        with patch("pathlib.Path.exists", return_value=False):
            assert watchdog.check_gpu_available() is False


# ─── Start Ollama Tests ────────────────────────────────────────

class TestStartOllama:
    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_success(self, mock_log, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        result = watchdog.start_ollama()
        assert result is True
        mock_popen.assert_called_once()

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_file_not_found(self, mock_log, mock_popen):
        mock_popen.side_effect = FileNotFoundError("no ollama binary")
        result = watchdog.start_ollama()
        assert result is False

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_os_error(self, mock_log, mock_popen):
        mock_popen.side_effect = OSError("permission denied")
        result = watchdog.start_ollama()
        assert result is False

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_logs_attempt(self, mock_log, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 99
        mock_popen.return_value = mock_proc
        watchdog.start_ollama()
        # First call: restart_attempt
        assert mock_log.call_args_list[0][0][0] == "restart_attempt"

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_logs_started_with_pid(self, mock_log, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_popen.return_value = mock_proc
        watchdog.start_ollama()
        # Second call: restart_started with pid
        second_call = mock_log.call_args_list[1]
        assert second_call[0][0] == "restart_started"
        assert second_call[0][1]["pid"] == 42

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_logs_failure(self, mock_log, mock_popen):
        mock_popen.side_effect = FileNotFoundError("missing")
        watchdog.start_ollama()
        failure_calls = [c for c in mock_log.call_args_list if c[0][0] == "restart_failed"]
        assert len(failure_calls) == 1
        assert "error" in failure_calls[0][0][1]

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_uses_start_new_session(self, mock_log, mock_popen):
        mock_popen.return_value = MagicMock(pid=1)
        watchdog.start_ollama()
        kwargs = mock_popen.call_args[1]
        assert kwargs.get("start_new_session") is True

    @patch("watchdog.subprocess.Popen")
    @patch("watchdog.log_event")
    def test_start_redirects_stdout_stderr(self, mock_log, mock_popen):
        mock_popen.return_value = MagicMock(pid=1)
        watchdog.start_ollama()
        kwargs = mock_popen.call_args[1]
        assert kwargs.get("stdout") == subprocess.DEVNULL
        assert kwargs.get("stderr") == subprocess.DEVNULL


# ─── Ensure Model Pulled Tests ─────────────────────────────────

class TestEnsureModelPulled:
    @patch("watchdog.check_model_available")
    def test_already_available(self, mock_check):
        mock_check.return_value = True
        result = watchdog.ensure_model_pulled()
        assert result is True
        mock_check.assert_called_once()

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_success(self, mock_log, mock_run, mock_check):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "success"
        result.stderr = ""
        mock_run.return_value = result
        assert watchdog.ensure_model_pulled() is True
        mock_run.assert_called_once()

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_fail(self, mock_log, mock_run, mock_check):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "network error"
        mock_run.return_value = result
        assert watchdog.ensure_model_pulled() is False

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_timeout(self, mock_log, mock_run, mock_check):
        mock_run.side_effect = subprocess.TimeoutExpired("ollama", 300)
        assert watchdog.ensure_model_pulled() is False

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_logs_start(self, mock_log, mock_run, mock_check):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result
        watchdog.ensure_model_pulled()
        start_calls = [c for c in mock_log.call_args_list if c[0][0] == "model_pull_start"]
        assert len(start_calls) == 1

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_logs_success(self, mock_log, mock_run, mock_check):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result
        watchdog.ensure_model_pulled()
        success_calls = [c for c in mock_log.call_args_list if c[0][0] == "model_pull_success"]
        assert len(success_calls) == 1

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_logs_failed_with_stderr(self, mock_log, mock_run, mock_check):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "some error detail"
        mock_run.return_value = result
        watchdog.ensure_model_pulled()
        fail_calls = [c for c in mock_log.call_args_list if c[0][0] == "model_pull_failed"]
        assert len(fail_calls) == 1
        assert "some error detail" in fail_calls[0][0][1]["stderr"]

    @patch("watchdog.check_model_available", return_value=False)
    @patch("watchdog.subprocess.run")
    @patch("watchdog.log_event")
    def test_pull_stderr_truncated(self, mock_log, mock_run, mock_check):
        """Stderr should be truncated to 500 chars in logs."""
        result = MagicMock()
        result.returncode = 1
        result.stderr = "x" * 1000
        mock_run.return_value = result
        watchdog.ensure_model_pulled()
        fail_calls = [c for c in mock_log.call_args_list if c[0][0] == "model_pull_failed"]
        assert len(fail_calls[0][0][1]["stderr"]) == 500


# ─── Health Check Full Tests ───────────────────────────────────

class TestHealthCheckFull:
    @patch("watchdog.check_ollama_alive", return_value=False)
    def test_ollama_dead_returns_early(self, mock_alive):
        status = watchdog.health_check_full()
        assert status["ollama_alive"] is False
        assert status["model_available"] is False
        assert "Ollama process not responding" in status["issues"]

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=False)
    def test_model_missing(self, mock_model, mock_gpu, mock_alive):
        status = watchdog.health_check_full()
        assert status["ollama_alive"] is True
        assert status["model_available"] is False
        assert any("not available" in i for i in status["issues"])

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=False)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_gpu_warning_not_blocking(self, mock_run, mock_model, mock_gpu, mock_alive):
        """GPU not available should be a warning, not a blocker."""
        # Mock test inference success
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"response": "ok"})
        mock_run.return_value = result
        status = watchdog.health_check_full()
        assert status["gpu_available"] is False
        assert status["test_inference"] is True
        assert any("GPU not detected" in i for i in status["issues"])

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_all_healthy(self, mock_run, mock_model, mock_gpu, mock_alive):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"response": "hello"})
        mock_run.return_value = result
        status = watchdog.health_check_full()
        assert status["ollama_alive"] is True
        assert status["model_available"] is True
        assert status["gpu_available"] is True
        assert status["test_inference"] is True
        assert len(status["issues"]) == 0

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_inference_fail_returncode(self, mock_run, mock_model, mock_gpu, mock_alive):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        mock_run.return_value = result
        status = watchdog.health_check_full()
        assert status["test_inference"] is False
        assert any("returned error" in i for i in status["issues"])

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_inference_timeout(self, mock_run, mock_model, mock_gpu, mock_alive):
        mock_run.side_effect = subprocess.TimeoutExpired("curl", 35)
        status = watchdog.health_check_full()
        assert status["test_inference"] is False
        assert any("Test inference failed" in i for i in status["issues"])

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_inference_json_error(self, mock_run, mock_model, mock_gpu, mock_alive):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "not json"
        mock_run.return_value = result
        status = watchdog.health_check_full()
        assert status["test_inference"] is False

    @patch("watchdog.check_ollama_alive", return_value=True)
    @patch("watchdog.check_gpu_available", return_value=True)
    @patch("watchdog.check_model_available", return_value=True)
    @patch("watchdog.subprocess.run")
    def test_inference_empty_response(self, mock_run, mock_model, mock_gpu, mock_alive):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"response": ""})
        mock_run.return_value = result
        status = watchdog.health_check_full()
        assert status["test_inference"] is False

    def test_status_has_timestamp(self):
        with patch("watchdog.check_ollama_alive", return_value=False):
            status = watchdog.health_check_full()
            assert "timestamp" in status
            datetime.fromisoformat(status["timestamp"])

    def test_status_has_issues_list(self):
        with patch("watchdog.check_ollama_alive", return_value=False):
            status = watchdog.health_check_full()
            assert isinstance(status["issues"], list)


# ─── Ensure Healthy Tests ──────────────────────────────────────

class TestEnsureHealthy:
    @patch("watchdog.health_check_full")
    def test_healthy_first_try(self, mock_health):
        mock_health.return_value = {
            "ollama_alive": True,
            "model_available": True,
            "test_inference": True,
            "gpu_available": True,
            "issues": [],
            "timestamp": "",
        }
        assert watchdog.ensure_healthy(max_attempts=3) is True

    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    @patch("watchdog.start_ollama")
    @patch("watchdog.check_ollama_alive", return_value=False)
    @patch("watchdog.log_event")
    def test_dead_ollama_recovery_fails(self, mock_log, mock_alive, mock_start, mock_sleep, mock_health):
        # Always returns unhealthy
        mock_health.return_value = {
            "ollama_alive": False,
            "model_available": False,
            "test_inference": False,
            "gpu_available": False,
            "issues": ["dead"],
            "timestamp": "",
        }
        result = watchdog.ensure_healthy(max_attempts=2)
        assert result is False
        assert mock_start.call_count == 2  # tried to start twice

    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    @patch("watchdog.start_ollama")
    @patch("watchdog.check_ollama_alive")
    @patch("watchdog.ensure_model_pulled")
    @patch("watchdog.log_event")
    def test_recovery_after_restart(self, mock_log, mock_pull, mock_alive, mock_start, mock_sleep, mock_health):
        # First check: dead. After restart: alive + healthy.
        mock_alive.return_value = True
        mock_pull.return_value = True

        first_check = {
            "ollama_alive": False, "model_available": False,
            "test_inference": False, "gpu_available": False,
            "issues": ["dead"], "timestamp": "",
        }
        healthy = {
            "ollama_alive": True, "model_available": True,
            "test_inference": True, "gpu_available": True,
            "issues": [], "timestamp": "",
        }
        # health_check_full called multiple times: first (entry), then recheck after recovery
        mock_health.side_effect = [first_check, healthy, healthy]
        result = watchdog.ensure_healthy(max_attempts=3)
        assert result is True

    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    @patch("watchdog.log_event")
    def test_gpu_warning_logged(self, mock_log, mock_sleep, mock_health):
        """GPU not available should be logged as warning when other issues exist too."""
        # When everything is healthy, ensure_healthy returns True before reaching GPU check.
        # GPU warning is only logged when there's another issue keeping us in the loop.
        mock_health.return_value = {
            "ollama_alive": True,
            "model_available": True,
            "test_inference": False,  # inference broken keeps us in the loop
            "gpu_available": False,
            "issues": ["GPU not detected", "inference broken"],
            "timestamp": "",
        }
        watchdog.ensure_healthy(max_attempts=1)
        gpu_warnings = [c for c in mock_log.call_args_list if c[0][0] == "gpu_warning"]
        assert len(gpu_warnings) >= 1

    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    @patch("watchdog.log_event")
    def test_recovery_success_logged(self, mock_log, mock_sleep, mock_health):
        """Recovery success after multiple attempts should be logged."""
        unhealthy = {
            "ollama_alive": False, "model_available": False,
            "test_inference": False, "gpu_available": False,
            "issues": ["dead"], "timestamp": "",
        }
        healthy = {
            "ollama_alive": True, "model_available": True,
            "test_inference": True, "gpu_available": True,
            "issues": [], "timestamp": "",
        }
        mock_health.side_effect = [unhealthy, healthy]
        with patch("watchdog.start_ollama"), \
             patch("watchdog.check_ollama_alive", return_value=True), \
             patch("watchdog.ensure_model_pulled", return_value=True):
            result = watchdog.ensure_healthy(max_attempts=3)
        assert result is True
        success_logs = [c for c in mock_log.call_args_list if c[0][0] == "recovery_success"]
        assert len(success_logs) >= 1

    @patch("watchdog.health_check_full")
    @patch("watchdog.time.sleep")
    @patch("watchdog.log_event")
    def test_max_attempts_exhausted(self, mock_log, mock_sleep, mock_health):
        unhealthy = {
            "ollama_alive": True, "model_available": True,
            "test_inference": False, "gpu_available": True,
            "issues": ["inference broken"], "timestamp": "",
        }
        mock_health.return_value = unhealthy
        result = watchdog.ensure_healthy(max_attempts=3)
        assert result is False
        failed_logs = [c for c in mock_log.call_args_list if c[0][0] == "recovery_failed"]
        assert len(failed_logs) == 1


# ─── Configuration Tests ───────────────────────────────────────

class TestConfiguration:
    def test_default_ollama_url(self):
        assert "localhost:11434" in watchdog.OLLAMA_URL

    def test_default_ollama_model(self):
        assert "granite" in watchdog.OLLAMA_MODEL.lower()

    def test_default_ollama_bin(self):
        assert "ollama" in watchdog.OLLAMA_BIN

    def test_max_restart_attempts_is_int(self):
        assert isinstance(watchdog.MAX_RESTART_ATTEMPTS, int)
        assert watchdog.MAX_RESTART_ATTEMPTS > 0

    def test_restart_backoff_base_positive(self):
        assert watchdog.RESTART_BACKOFF_BASE > 0

    def test_health_check_timeout_positive(self):
        assert watchdog.HEALTH_CHECK_TIMEOUT > 0

    def test_watchdog_log_is_path(self):
        assert isinstance(watchdog.WATCHDOG_LOG, Path)

    def test_watchdog_log_parent_exists(self):
        """The log directory should be created at import time."""
        assert watchdog.WATCHDOG_LOG.parent.exists()
