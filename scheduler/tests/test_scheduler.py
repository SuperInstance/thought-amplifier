"""
test_scheduler.py — Tests for the Inference Scheduler

Tests cover:
  1. Serializing concurrent requests (only one at a time)
  2. Priority preemption (higher priority served first)
  3. Fair use prevents starvation
  4. Cloud fallback triggers correctly
  5. Priority evolution improves allocation

Uses mock Ollama (no GPU needed). Runs with plain python3 -m pytest.
All tests are deterministic and fast (< 5s total).
"""

import json
import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

# Ensure we can import from the scheduler package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler import InferenceScheduler, InferenceRequest, Priority, AgentStats
from fair_use import FairUseTracker, AgentRecord
from cloud_bridge import CloudBridge, NeuronUsage
from priority_evolver import PriorityEvolver, OutcomeRecord


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class MockScheduler:
    """A scheduler with a mock Ollama that records call timing."""

    def __init__(self, call_duration: float = 0.05, cloud=None, fair_use=None):
        self.call_log: list[dict] = []
        self.call_duration = call_duration
        self._call_lock = threading.Lock()
        self._concurrent = 0
        self.max_concurrent = 0

        self.scheduler = InferenceScheduler(
            ollama_url="http://mock:11434",
            cloud_bridge=cloud,
            fair_use=fair_use,
        )
        # Patch the _call_ollama method
        self.scheduler._call_ollama = self._mock_call

    def _mock_call(self, req: InferenceRequest) -> dict:
        with self._call_lock:
            self._concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self._concurrent)

        start = time.time()
        self.call_log.append({
            "id": req.id,
            "agent": req.agent,
            "priority": req.priority.name,
            "started": start,
        })
        time.sleep(self.call_duration)
        elapsed_ms = (time.time() - start) * 1000

        with self._call_lock:
            self._concurrent -= 1

        return {
            "model": req.model,
            "response": f"mock response for {req.agent}",
            "done": True,
            "eval_count": 10,
            "_gpu_ms": elapsed_ms,
        }

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.stop()

    def submit(self, **kwargs):
        return self.scheduler.submit(**kwargs)

    def wait_for(self, request_ids: list[str], timeout: float = 5.0):
        """Wait for all requests to complete."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            done = all(
                self.scheduler.get(rid) and
                self.scheduler.get(rid).status in ("done", "error", "cancelled")
                for rid in request_ids
            )
            if done:
                return True
            time.sleep(0.01)
        return False


# ---------------------------------------------------------------------------
# 1. Serialization: concurrent requests are serialized
# ---------------------------------------------------------------------------

def test_concurrent_requests_serialized():
    """Multiple concurrent requests must be served one at a time."""
    mock = MockScheduler(call_duration=0.05)
    mock.start()
    try:
        ids = []
        for i in range(5):
            req = mock.submit(
                prompt=f"test {i}",
                agent=f"agent_{i}",
                priority=Priority.NORMAL,
            )
            ids.append(req.id)

        assert mock.wait_for(ids, timeout=5.0), "Not all requests completed"

        # Verify no concurrent execution
        assert mock.max_concurrent == 1, \
            f"Expected max 1 concurrent, got {mock.max_concurrent}"

        # Verify all completed
        for rid in ids:
            req = mock.scheduler.get(rid)
            assert req.status == "done", f"Request {rid} status={req.status}"
            assert req.result is not None
    finally:
        mock.stop()


def test_ten_rapid_requests_serialize():
    """Burst of 10 requests should still serialize."""
    mock = MockScheduler(call_duration=0.02)
    mock.start()
    try:
        ids = []
        for i in range(10):
            req = mock.submit(prompt=f"burst {i}", agent="burst")
            ids.append(req.id)

        assert mock.wait_for(ids, timeout=10.0)
        assert mock.max_concurrent == 1
        assert len(mock.call_log) == 10
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# 2. Priority: higher priority served first
# ---------------------------------------------------------------------------

def test_priority_ordering():
    """Higher priority requests should be served before lower priority."""
    mock = MockScheduler(call_duration=0.05)
    mock.start()
    try:
        # Submit low priority first
        low = mock.submit(prompt="low", agent="low", priority=Priority.LOW)
        # Give it time to start running
        time.sleep(0.01)
        # Now submit urgent
        urgent = mock.submit(prompt="urgent", agent="urgent", priority=Priority.URGENT)
        normal = mock.submit(prompt="normal", agent="normal", priority=Priority.NORMAL)

        all_ids = [low.id, urgent.id, normal.id]
        assert mock.wait_for(all_ids, timeout=5.0)

        # Check execution order from call log
        order = [entry["agent"] for entry in mock.call_log]
        # Low started first (already running), then urgent should be next
        assert order[0] == "low", f"Expected low first, got {order[0]}"
        assert order[1] == "urgent", f"Expected urgent second, got {order[1]}"
        assert order[2] == "normal", f"Expected normal third, got {order[2]}"
    finally:
        mock.stop()


def test_priority_update_queued():
    """Updating priority of a queued request should change its position."""
    mock = MockScheduler(call_duration=0.1)
    mock.start()
    try:
        # Block with a long-running request
        blocker = mock.submit(prompt="blocker", agent="blocker", priority=Priority.NORMAL)
        time.sleep(0.01)  # Let it start

        # Queue three requests
        low = mock.submit(prompt="low", agent="low_a", priority=Priority.LOW)
        med = mock.submit(prompt="med", agent="med_a", priority=Priority.NORMAL)
        high = mock.submit(prompt="high", agent="high_a", priority=Priority.HIGH)

        # Bump 'low' to URGENT
        mock.scheduler.update_priority(low.id, Priority.URGENT)

        all_ids = [blocker.id, low.id, med.id, high.id]
        assert mock.wait_for(all_ids, timeout=10.0)

        order = [entry["agent"] for entry in mock.call_log]
        # After blocker: low (now URGENT) should be first
        assert order[0] == "blocker"
        assert order[1] == "low_a", f"Expected low_a (upgraded to URGENT) second, got {order[1]}"
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# 3. Fair use prevents starvation
# ---------------------------------------------------------------------------

def test_fair_use_floor():
    """Each agent gets at least its floor of GPU time."""
    tracker = FairUseTracker(
        window_s=10,
        default_floor_ms=1000,
        ceiling_ms=10000,
    )
    tracker.register("agent_a")
    tracker.register("agent_b")

    # Agent A uses lots of GPU
    for _ in range(20):
        tracker.record("agent_a", 500, value=0.8)
    # Agent B uses none
    # Agent B should still have its floor available
    shares = tracker.compute_shares()
    assert shares["agent_b"] >= 1000, \
        f"Agent B floor not guaranteed: {shares['agent_b']}"
    assert shares["agent_a"] >= 0


def test_fair_use_starvation_check():
    """An agent that hasn't been served should not be deferred."""
    tracker = FairUseTracker(
        window_s=10,
        default_floor_ms=500,
        starvation_boost_s=30,
    )
    tracker.register("starving_agent")

    # Agent hasn't been served for a long time
    rec = tracker._agents["starving_agent"]
    rec.last_served = time.time() - 100  # 100 seconds ago

    stats = AgentStats(agent="starving_agent")
    stats.gpu_time_ms = 0

    over, reason = tracker.check_agent(stats, [AgentStats(agent="other")])
    assert not over, f"Starving agent should not be deferred: {reason}"
    assert "starvation" in reason


def test_fair_use_over_share_defer():
    """An agent well above its share should be deferred."""
    tracker = FairUseTracker(
        window_s=10,
        default_floor_ms=100,
        ceiling_ms=500,
    )
    tracker.register("greedy")
    tracker.register("waiting")

    # Greedy agent uses lots of GPU
    for _ in range(10):
        tracker.record("greedy", 100, value=0.5)

    # Waiting agent has used nothing
    stats_greedy = AgentStats(agent="greedy")
    stats_greedy.gpu_time_ms = 1000
    stats_waiting = AgentStats(agent="waiting")
    stats_waiting.gpu_time_ms = 0

    over, reason = tracker.check_agent(stats_greedy, [stats_waiting])
    assert over, f"Greedy agent should be deferred: {reason}"


# ---------------------------------------------------------------------------
# 4. Cloud fallback triggers correctly
# ---------------------------------------------------------------------------

def test_cloud_overflow_threshold():
    """Cloud overflow should trigger when queue depth exceeds threshold."""
    bridge = CloudBridge(
        account_id="test",
        api_token="test",
        overflow_threshold=3,
    )
    assert not bridge.should_overflow(0)
    assert not bridge.should_overflow(2)
    assert bridge.should_overflow(3)
    assert bridge.should_overflow(10)


def test_cloud_overflow_quota_exhausted():
    """Should not overflow when neuron quota is exhausted."""
    bridge = CloudBridge(
        account_id="test",
        api_token="test",
        overflow_threshold=1,
        min_neuron_reserve=100,
    )
    # Exhaust quota — set date to today first so reset doesn't zero it
    today = time.strftime("%Y-%m-%d", time.gmtime())
    bridge.neurons.date = today
    bridge.neurons.neurons_used = 9900
    bridge.neurons.daily_limit = 10000

    assert not bridge.should_overflow(5), "Should not overflow with low quota"


def test_cloud_overflow_unconfigured():
    """Should not overflow if not configured."""
    bridge = CloudBridge(
        account_id="",
        api_token="",
        overflow_threshold=1,
    )
    assert not bridge.should_overflow(10)


def test_cloud_overflow_cooldown():
    """Should not overflow during cooldown after error."""
    bridge = CloudBridge(
        account_id="test",
        api_token="test",
        overflow_threshold=1,
        cooldown_s=60,
    )
    bridge._last_error = time.time()
    assert not bridge.should_overflow(5)

    # After cooldown
    bridge._last_error = time.time() - 120
    assert bridge.should_overflow(5)


def test_neuron_daily_reset():
    """Neuron counter should reset on new UTC day."""
    usage = NeuronUsage()
    usage.date = "2020-01-01"
    usage.neurons_used = 5000
    usage.reset_if_new_day()
    # Should have reset to today
    today = time.strftime("%Y-%m-%d", time.gmtime())
    assert usage.date == today
    assert usage.neurons_used == 0


# ---------------------------------------------------------------------------
# 5. Priority evolution improves allocation
# ---------------------------------------------------------------------------

def test_evolver_records_outcomes():
    """Evolver should track outcomes correctly."""
    evolver = PriorityEvolver(ema_alpha=0.1, min_observations=5)

    for i in range(10):
        evolver.record_outcome(OutcomeRecord(
            agent="test_agent",
            assigned_priority=2,
            base_priority=2,
            quality=0.8,
            timeliness=0.9,
            gpu_ms=500,
            served_by="local",
            timestamp=time.time(),
        ))

    stats = evolver.stats()
    assert stats["total_outcomes"] == 10
    assert "test_agent" in stats["agent_quality"]
    assert stats["agent_quality"]["test_agent"] > 0.5


def test_evolver_finds_better_priority():
    """After enough data, evolver should adjust priority toward better outcomes."""
    evolver = PriorityEvolver(
        ema_alpha=0.2,
        min_observations=5,
        evolution_interval_s=0,  # evolve immediately
        adjustment_clamp=2.0,
    )

    # Agent performs better at URGENT (0) than at NORMAL (2)
    for _ in range(20):
        # High reward at URGENT
        evolver.record_outcome(OutcomeRecord(
            agent="worker",
            assigned_priority=0,
            base_priority=2,
            quality=0.9,
            timeliness=1.0,
            gpu_ms=400,
            served_by="local",
            timestamp=time.time(),
        ))
        # Low reward at NORMAL
        evolver.record_outcome(OutcomeRecord(
            agent="worker",
            assigned_priority=2,
            base_priority=2,
            quality=0.3,
            timeliness=0.2,
            gpu_ms=800,
            served_by="local",
            timestamp=time.time(),
        ))

    # Force evolution
    evolver._evolve_policy()

    # The adjustment should be negative (expedite this agent)
    adj = evolver.get_adjustment("worker")
    assert adj < 0, f"Expected negative adjustment (expedite), got {adj}"


def test_evolver_min_observations():
    """Evolver should not adjust with too few observations."""
    evolver = PriorityEvolver(min_observations=100)

    for _ in range(10):
        evolver.record_outcome(OutcomeRecord(
            agent="sparse",
            assigned_priority=0,
            base_priority=2,
            quality=1.0,
            timeliness=1.0,
            gpu_ms=100,
            served_by="local",
            timestamp=time.time(),
        ))

    evolver._evolve_policy()
    adj = evolver.get_adjustment("sparse")
    assert adj == 0.0, f"Should not adjust with <100 observations, got {adj}"


def test_evolver_export_import():
    """Policy should survive export/import round-trip."""
    evolver = PriorityEvolver(ema_alpha=0.3, min_observations=5)

    for _ in range(10):
        evolver.record_outcome(OutcomeRecord(
            agent="imp_test",
            assigned_priority=1,
            base_priority=2,
            quality=0.7,
            timeliness=0.8,
            gpu_ms=300,
            served_by="local",
            timestamp=time.time(),
        ))

    evolver._evolve_policy()
    exported = evolver.export_policy()

    new_evolver = PriorityEvolver()
    new_evolver.import_policy(exported)

    assert new_evolver.get_adjustment("imp_test") == evolver.get_adjustment("imp_test")


# ---------------------------------------------------------------------------
# 6. Integration: full flow
# ---------------------------------------------------------------------------

def test_full_flow_submit_wait_result():
    """Submit a request, wait for it, get the result."""
    mock = MockScheduler(call_duration=0.02)
    mock.start()
    try:
        req = mock.submit(
            prompt="hello world",
            agent="test_agent",
            priority=Priority.NORMAL,
            model="llama3.2:3b",
        )
        assert mock.wait_for([req.id], timeout=5.0)

        result = mock.scheduler.get(req.id)
        assert result.status == "done"
        assert result.result is not None
        assert "response" in result.result
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at
    finally:
        mock.stop()


def test_cancel_queued_request():
    """A queued request can be cancelled."""
    mock = MockScheduler(call_duration=0.2)
    mock.start()
    try:
        # Start a long request
        first = mock.submit(prompt="long", agent="a")
        time.sleep(0.01)
        # Queue a second
        second = mock.submit(prompt="second", agent="b")

        # Cancel the second
        ok = mock.scheduler.cancel(second.id)
        assert ok

        # Wait for first
        assert mock.wait_for([first.id], timeout=5.0)

        result = mock.scheduler.get(second.id)
        assert result.status == "cancelled"
    finally:
        mock.stop()


def test_queue_snapshot():
    """Queue snapshot should reflect current state."""
    mock = MockScheduler(call_duration=0.2)
    mock.start()
    try:
        # Start one (it'll be running)
        r1 = mock.submit(prompt="running", agent="a")
        time.sleep(0.01)
        # Queue two more
        r2 = mock.submit(prompt="queued1", agent="b", priority=Priority.HIGH)
        r3 = mock.submit(prompt="queued2", agent="c", priority=Priority.LOW)

        snap = mock.scheduler.queue_snapshot()
        assert snap["current"] is not None
        assert snap["current"]["id"] == r1.id
        assert snap["queue_depth"] == 2

        mock.wait_for([r1.id, r2.id, r3.id], timeout=5.0)
    finally:
        mock.stop()


def test_agent_stats_tracked():
    """Stats should be tracked per agent."""
    mock = MockScheduler(call_duration=0.02)
    mock.start()
    try:
        ids = []
        for _ in range(3):
            req = mock.submit(prompt="stat test", agent="stat_agent")
            ids.append(req.id)

        mock.wait_for(ids, timeout=5.0)

        stats = mock.scheduler.all_stats()
        assert "stat_agent" in stats
        assert stats["stat_agent"]["requests_completed"] == 3
        assert stats["stat_agent"]["total_gpu_ms"] > 0
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run without pytest if not available
    tests = [
        test_concurrent_requests_serialized,
        test_ten_rapid_requests_serialize,
        test_priority_ordering,
        test_priority_update_queued,
        test_fair_use_floor,
        test_fair_use_starvation_check,
        test_fair_use_over_share_defer,
        test_cloud_overflow_threshold,
        test_cloud_overflow_quota_exhausted,
        test_cloud_overflow_unconfigured,
        test_cloud_overflow_cooldown,
        test_neuron_daily_reset,
        test_evolver_records_outcomes,
        test_evolver_finds_better_priority,
        test_evolver_min_observations,
        test_evolver_export_import,
        test_full_flow_submit_wait_result,
        test_cancel_queued_request,
        test_queue_snapshot,
        test_agent_stats_tracked,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
