"""
Tests for distillation_loop.py production hardening (2026-08-30).

Covers the three real bugs found in the audit:
  1. Promotion streaks were in-memory only — restarts (cron/overnight, one
     process per invocation) silently reset them. Now persisted on disk.
  2. Prompt evolution was unbounded — versions grew forever with no quality
     record. Now capped (archive-flagged, never deleted) with metrics.
  3. Ollama-down stalls — every student call retried + ran watchdog recovery
     even when Ollama was truly dead. Now a circuit breaker short-circuits.

No network access: _curl_post_json and watchdog are mocked.
"""

import json
import time
from pathlib import Path

import pytest

import distillation_loop as dl


# ─── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    """Redirect all artifact writes to a tmp dir."""
    monkeypatch.setattr(dl, "PROMPT_DIR", tmp_path)
    monkeypatch.setattr(dl, "STUDENT_DIR", tmp_path / "student")
    (tmp_path / "student").mkdir()
    return tmp_path


@pytest.fixture
def reset_breaker(monkeypatch):
    """Fresh breaker state + fast thresholds for tests."""
    monkeypatch.setattr(dl, "BREAKER_THRESHOLD", 2)
    monkeypatch.setattr(dl, "BREAKER_COOLDOWN", 50.0)
    dl._breaker_reset()
    yield
    dl._breaker_reset()


def make_teacher(topic="cascade routing"):
    return {"topic": topic, "lesson": "Lessons " * 40, "timestamp": "20260830_000000"}


def make_eval(delta=0.05, helped=True):
    return {
        "teaching_helped": helped,
        "delta": delta,
        "taught_composite": 0.5,
        "baseline_composite": 0.45,
    }


def make_task():
    return {"task": "Review the router", "code": "src/router.py"}


# ─── 1. Persisted promotion streaks ────────────────────────────

class TestStreakPersistence:
    def test_streak_survives_process_restart(self, tmp_dirs):
        """Two helped evals, then a 'restart' (fresh module state via disk),
        then one more helped eval must still promote."""
        # Process A: two wins (streak 2 of 3 — old code lost this on exit)
        for i in (1, 2):
            r = dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", i)
            assert r["updated"] is False

        # Restart: the streak must be on disk
        streaks_file = tmp_dirs / "domain_streaks.json"
        assert streaks_file.exists(), "streaks must persist to disk"
        state = json.loads(streaks_file.read_text())
        assert state["cognition"]["streak"] == [True, True]

        # Process B (fresh call path, state loaded from disk only): third win promotes
        r = dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", 3)
        assert r["updated"] is True
        assert r["version"] == "v1"

    def test_promotion_resets_streak_on_disk(self, tmp_dirs):
        for i in (1, 2, 3):
            dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", i)
        state = json.loads((tmp_dirs / "domain_streaks.json").read_text())
        assert state["cognition"]["streak"] == []
        # Metrics keep running after promotion
        assert state["cognition"]["metrics"]["iterations"] == 3
        assert state["cognition"]["metrics"]["helped"] == 3

    def test_failed_eval_breaks_streak(self, tmp_dirs):
        dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", 1)
        dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", 2)
        dl.stage_update_prompt(make_teacher(), make_eval(helped=False, delta=-0.01), "cognition", 3)
        r = dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", 4)
        assert r["updated"] is False

    def test_corrupt_streaks_file_is_tolerated(self, tmp_dirs):
        (tmp_dirs / "domain_streaks.json").write_text("{not json")
        r = dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", 1)
        assert r["updated"] is False  # no crash, no promotion


# ─── 2. Bounded prompt evolution ───────────────────────────────

class TestBoundedPromptEvolution:
    def test_active_directives_capped_older_archived_not_deleted(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr(dl, "MAX_ACTIVE_DIRECTIVES", 4)
        it = 0
        for _ in range(7):  # 7 promotions => 7 versions, cap 4 active
            for _ in range(3):
                it += 1
                r = dl.stage_update_prompt(make_teacher(), make_eval(delta=0.02), "cognition", it)
            assert r["updated"] is True

        versions = [
            json.loads(line)
            for line in (tmp_dirs / "cognition_versions.jsonl").read_text().strip().split("\n")
            if line.strip()
        ]
        assert len(versions) == 7, "all versions retained — archive, never delete"
        active = [v for v in versions if not v.get("archived")]
        assert len(active) <= 4, "active directives must be capped"
        archived = [v for v in versions if v.get("archived")]
        assert len(archived) == 3
        assert all("archived_at" in v for v in archived), "archival is dated"

    def test_promotion_records_quality_metrics(self, tmp_dirs):
        # 2 wins, 1 loss, then 3 wins -> promote with help_rate 5/6
        seq = [True, True, False, True, True, True]
        for i, helped in enumerate(seq, start=1):
            r = dl.stage_update_prompt(
                make_teacher(),
                make_eval(delta=0.1 if helped else -0.05, helped=helped),
                "cognition",
                i,
            )
        assert r["updated"] is True
        versions = [
            json.loads(line)
            for line in (tmp_dirs / "cognition_versions.jsonl").read_text().strip().split("\n")
        ]
        v = versions[-1]
        assert v["help_rate"] == round(5 / 6, 3)
        assert v["avg_delta"] == round((0.1 * 5 - 0.05) / 6, 3), "avg delta recorded at promotion"

    def test_version_history_jsonl_appends(self, tmp_dirs):
        for i in range(3):
            dl.stage_update_prompt(make_teacher(), make_eval(), "cognition", i + 1)
        hist = (tmp_dirs / "VERSION_HISTORY.jsonl").read_text().strip().split("\n")
        assert len(hist) == 1  # exactly one promotion from 3 wins
        assert json.loads(hist[0])["version"] == "v1"


# ─── 3. Ollama-down circuit breaker ────────────────────────────

class TestCircuitBreaker:
    def _fail_curl(self, calls):
        def fake(url, headers, data, **kwargs):
            calls.append(url)
            return {"error": "connection refused"}
        return fake

    def test_breaker_opens_and_skips_network(self, tmp_dirs, reset_breaker, monkeypatch):
        calls = []
        monkeypatch.setattr(dl, "_curl_post_json", self._fail_curl(calls))
        import watchdog as wd
        monkeypatch.setattr(wd, "ensure_healthy", lambda max_attempts=3: False)

        # Threshold=2: first 2 calls hit the (mocked) network, then breaker opens
        a1 = dl.stage_student(make_teacher(), make_task(), "code", True, 1, "cognition")
        a2 = dl.stage_student(make_teacher(), make_task(), "code", True, 2, "cognition")
        assert a1["success"] is False and a2["success"] is False
        assert dl.breaker_is_open() is True

        net_calls_before = len(calls)
        a3 = dl.stage_student(make_teacher(), make_task(), "code", True, 3, "cognition")
        a4 = dl.stage_student(make_teacher(), make_task(), "code", False, 4, "cognition")
        assert len(calls) == net_calls_before, "open breaker must make zero network calls"
        assert a3["error"] == "student_circuit_open"
        assert a4["error"] == "student_circuit_open"
        assert a3["label"] == "taught" and a4["label"] == "baseline"

    def test_breaker_half_opens_after_cooldown(self, tmp_dirs, reset_breaker, monkeypatch):
        calls = []
        monkeypatch.setattr(dl, "_curl_post_json", self._fail_curl(calls))
        import watchdog as wd
        monkeypatch.setattr(wd, "ensure_healthy", lambda max_attempts=3: False)

        dl.stage_student(make_teacher(), make_task(), "code", True, 1, "cognition")
        dl.stage_student(make_teacher(), make_task(), "code", True, 2, "cognition")
        assert dl.breaker_is_open() is True

        # Fast-forward past the cooldown: next check half-opens (one probe allowed)
        future = time.time() + 51.0
        monkeypatch.setattr(time, "time", lambda: future)
        assert dl.breaker_is_open() is False, "cooldown elapsed -> half-open"
        dl.stage_student(make_teacher(), make_task(), "code", True, 3, "cognition")
        assert len(calls) == 3, "half-open state must allow exactly one probe"

    def test_success_closes_breaker(self, reset_breaker, monkeypatch):
        dl.breaker_record(False)
        dl.breaker_record(False)
        assert dl.breaker_is_open() is True
        dl.breaker_record(True)
        assert dl.breaker_is_open() is False

    def test_successful_student_call_closes_breaker(self, tmp_dirs, reset_breaker, monkeypatch):
        state = {"fail": True}
        calls = []

        def flaky(url, headers, data, **kwargs):
            calls.append(url)
            if state["fail"]:
                return {"error": "down"}
            return {"message": {"content": "a real analysis of the router module"}}

        monkeypatch.setattr(dl, "_curl_post_json", flaky)
        import watchdog as wd
        monkeypatch.setattr(wd, "ensure_healthy", lambda max_attempts=3: False)

        dl.stage_student(make_teacher(), make_task(), "code", True, 1, "cognition")
        dl.stage_student(make_teacher(), make_task(), "code", True, 2, "cognition")
        assert dl.breaker_is_open() is True
        # Ollama comes back after cooldown
        future = time.time() + 51.0
        monkeypatch.setattr(time, "time", lambda: future)
        state["fail"] = False
        dl.breaker_is_open()  # half-open
        a = dl.stage_student(make_teacher(), make_task(), "code", True, 3, "cognition")
        assert a["success"] is True
        assert dl.breaker_is_open() is False
