"""
scheduler.py — The Core: Priority Queue + GPU Serialization

The RTX 4050 has 6GB VRAM. Ollama loads one model at a time. When two
agents call simultaneously, the GPU OOMs and Ollama crashes. This module
serializes all inference requests through a single queue with preemptive
priority and fair-use guarantees.

Design constraints (from EXP1 and SELF_AUDIT):
- ONE inference at a time, no exceptions
- Higher priority preempts lower (but running inference completes atomically)
- GPU time tracked per agent over a sliding window
- Idle capacity goes to background/evolution work

Priority levels (borrowed from OS scheduling):
  URGENT (0) — user-facing, blocking, real-time
  HIGH   (1) — conductor analysis, trust scoring
  NORMAL (2) — agent thinking loop
  LOW    (3) — batch embedding, indexing
  IDLE   (4) — evolution rollouts, background training

The jazz metaphor: scheduled turns are the beat, urgent preempts are
syncopation. The rhythm section (fair_use) keeps everyone in pocket.
"""

from __future__ import annotations

import heapq
import itertools
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable

logger = logging.getLogger("scheduler")

# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

class Priority(IntEnum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4

    @classmethod
    def parse(cls, value: str | int) -> "Priority":
        if isinstance(value, int):
            return cls(value)
        return cls[value.upper()]


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

@dataclass(order=True)
class InferenceRequest:
    """Heap-ordered. Lower (priority, seq) = served first."""
    sort_key: tuple[int, int] = field(init=False)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent: str = "default"
    priority: Priority = Priority.NORMAL
    model: str = "llama3.2:3b"
    prompt: str = ""
    stream: bool = False
    options: dict[str, Any] = field(default_factory=dict)
    submitted_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    status: str = "queued"  # queued | running | done | error | cancelled
    result: dict[str, Any] | None = None
    error: str | None = None
    _cancelled: bool = False
    # Cloud bridge bookkeeping
    served_by: str = "local"  # "local" | "cloud" | "cache"

    def __post_init__(self):
        # Heap sorts ascending; lower priority value = more urgent.
        self.sort_key = (int(self.priority), 0)  # seq filled at enqueue

    def cancel(self):
        self._cancelled = True
        if self.status == "queued":
            self.status = "cancelled"


# ---------------------------------------------------------------------------
# Stats per agent
# ---------------------------------------------------------------------------

@dataclass
class AgentStats:
    agent: str
    requests_total: int = 0
    requests_completed: int = 0
    requests_errors: int = 0
    gpu_time_ms: float = 0.0
    # Sliding window (default 5 min) for fair-use calculation
    gpu_history: deque = field(default_factory=lambda: deque(maxlen=600))
    # Value tracking (for priority_evolver)
    value_scores: deque = field(default_factory=lambda: deque(maxlen=200))
    last_served: float = 0.0
    fair_share_ms: float = 0.0  # computed by FairUseTracker

    def record(self, gpu_ms: float, value: float = 0.0):
        self.requests_completed += 1
        self.gpu_time_ms += gpu_ms
        now = time.time()
        self.gpu_history.append((now, gpu_ms))
        if value != 0.0:
            self.value_scores.append((now, value))
        self.last_served = now

    def window_gpu_ms(self, window_s: float = 300.0) -> float:
        cutoff = time.time() - window_s
        return sum(ms for ts, ms in self.gpu_history if ts >= cutoff)

    def avg_value(self) -> float:
        if not self.value_scores:
            return 0.0
        return sum(v for _, v in self.value_scores) / len(self.value_scores)


# ---------------------------------------------------------------------------
# The Core Scheduler
# ---------------------------------------------------------------------------

class InferenceScheduler:
    """
    Thread-safe priority queue that serializes requests to Ollama.

    Worker loop:
      1. Pop highest-priority request
      2. Check fair-use — if agent is over share and others are waiting,
         defer (move to back of its priority band)
      3. Execute via Ollama CLI (curl subprocess)
      4. Record stats
      5. Repeat

    Preemption is soft: a running inference completes atomically (GPU can't
    be safely interrupted mid-generation), but the NEXT pop will always
    pick the highest-priority queued request, so an URGENT that arrives
    during a LOW run will be served immediately after.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        cloud_bridge: "CloudBridge | None" = None,
        fair_use: "FairUseTracker | None" = None,
        max_retries: int = 1,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.cloud_bridge = cloud_bridge
        self.fair_use = fair_use
        self.max_retries = max_retries

        self._heap: list[list] = []  # [sort_key, counter, request]
        self._counter = itertools.count()
        self._lock = threading.Lock()
        self._wakeup = threading.Condition(self._lock)
        self._requests: dict[str, InferenceRequest] = {}
        self._stats: dict[str, AgentStats] = defaultdict(lambda: AgentStats(agent=""))
        self._running = False
        self._worker: threading.Thread | None = None
        self._current: InferenceRequest | None = None
        self._seq_counter = itertools.count()

    # --- public API ---

    def submit(
        self,
        prompt: str,
        agent: str = "default",
        priority: Priority | str | int = Priority.NORMAL,
        model: str = "llama3.2:3b",
        options: dict | None = None,
    ) -> InferenceRequest:
        """Submit an inference request. Returns immediately."""
        if isinstance(priority, (str, int)):
            priority = Priority.parse(priority)

        req = InferenceRequest(
            agent=agent,
            priority=priority,
            model=model,
            prompt=prompt,
            options=options or {},
        )
        # Assign sequence for stable FIFO within same priority
        req.sort_key = (int(priority), next(self._seq_counter))

        with self._lock:
            self._requests[req.id] = req
            stats = self._stats[agent]
            stats.agent = agent
            stats.requests_total += 1
            heapq.heappush(self._heap, [req.sort_key, next(self._counter), req])
            self._wakeup.notify()

        logger.debug("Queued %s agent=%s pri=%s", req.id, agent, priority.name)
        return req

    def get(self, request_id: str) -> InferenceRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if req and req.status == "queued":
                req.cancel()
                return True
            return False

    def update_priority(self, request_id: str, priority: Priority | str | int):
        if isinstance(priority, (str, int)):
            priority = Priority.parse(priority)
        with self._lock:
            req = self._requests.get(request_id)
            if not req or req.status != "queued":
                return False
            # Remove from heap, update priority, reinsert
            req.priority = priority
            req.sort_key = (int(priority), next(self._seq_counter))
            heapq.heappush(self._heap, [req.sort_key, next(self._counter), req])
            self._wakeup.notify()
            return True

    def queue_snapshot(self) -> list[dict]:
        with self._lock:
            queued = [
                {
                    "id": r.id,
                    "agent": r.agent,
                    "priority": r.priority.name,
                    "model": r.model,
                    "submitted_at": r.submitted_at,
                    "wait_ms": (time.time() - r.submitted_at) * 1000,
                    "status": r.status,
                }
                for _, _, r in sorted(self._heap)
                if r.status == "queued"
            ]
            current = None
            if self._current:
                current = {
                    "id": self._current.id,
                    "agent": self._current.agent,
                    "priority": self._current.priority.name,
                    "model": self._current.model,
                    "started_at": self._current.started_at,
                    "running_ms": (time.time() - self._current.started_at) * 1000
                    if self._current.started_at else 0,
                }
            return {"current": current, "queued": queued, "queue_depth": len(queued)}

    def all_stats(self) -> dict[str, dict]:
        with self._lock:
            return {
                agent: {
                    "requests_total": s.requests_total,
                    "requests_completed": s.requests_completed,
                    "requests_errors": s.requests_errors,
                    "total_gpu_ms": round(s.gpu_time_ms, 1),
                    "window_gpu_ms": round(s.window_gpu_ms(), 1),
                    "avg_value": round(s.avg_value(), 3),
                    "fair_share_ms": round(s.fair_share_ms, 1),
                    "last_served_ago_s": round(time.time() - s.last_served, 1)
                    if s.last_served else None,
                }
                for agent, s in self._stats.items()
            }

    # --- lifecycle ---

    def start(self):
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        logger.info("Scheduler worker started")

    def stop(self):
        self._running = False
        with self._lock:
            self._wakeup.notify_all()

    # --- worker loop ---

    def _worker_loop(self):
        while self._running:
            with self._lock:
                while not self._heap and self._running:
                    self._wakeup.wait(timeout=1.0)
                if not self._running:
                    break

                # Pop highest priority
                while self._heap:
                    _, _, req = heapq.heappop(self._heap)
                    if req.status == "queued" and not req._cancelled:
                        break
                else:
                    continue

                # Fair-use check: if agent is over share and others waiting,
                # requeue at back of same priority band
                if self.fair_use and self._heap:
                    over, reason = self.fair_use.check_agent(
                        self._stats[req.agent],
                        [self._stats[r.agent] for _, _, r in self._heap],
                    )
                    if over:
                        logger.debug("Fair-use defer %s agent=%s: %s", req.id, req.agent, reason)
                        req.sort_key = (int(req.priority), next(self._seq_counter))
                        heapq.heappush(self._heap, [req.sort_key, next(self._counter), req])
                        continue

                # Cloud overflow check
                if self.cloud_bridge and self._should_overflow():
                    logger.info("Cloud overflow for %s", req.id)
                    req.started_at = time.time()
                    req.status = "running"
                    self._current = req
                    self._lock.release()
                    try:
                        result = self.cloud_bridge.infer(req)
                    except Exception as exc:
                        result = {"error": str(exc)}
                        req.error = str(exc)
                        req.status = "error"
                    finally:
                        self._lock.acquire()
                    self._current = None
                    req.completed_at = time.time()
                    if req.status != "error":
                        req.status = "done"
                    req.result = result
                    req.served_by = "cloud"
                    continue

                req.started_at = time.time()
                req.status = "running"
                self._current = req

            # Execute inference (outside lock — GPU bound)
            try:
                result = self._call_ollama(req)
                req.result = result
                req.status = "done"
                req.served_by = "local"
            except Exception as exc:
                logger.error("Inference failed for %s: %s", req.id, exc)
                if self.max_retries > 0:
                    # Single retry with smaller context
                    try:
                        req.options.setdefault("num_ctx", 2048)
                        result = self._call_ollama(req)
                        req.result = result
                        req.status = "done"
                        req.served_by = "local"
                    except Exception as exc2:
                        req.error = str(exc2)
                        req.status = "error"
                        self._stats[req.agent].requests_errors += 1
                else:
                    req.error = str(exc)
                    req.status = "error"
                    self._stats[req.agent].requests_errors += 1

            req.completed_at = time.time()
            gpu_ms = (req.completed_at - req.started_at) * 1000

            with self._lock:
                self._current = None
                stats = self._stats[req.agent]
                stats.agent = req.agent
                # Value score placeholder — real scoring from quality signals
                value = 1.0 if req.status == "done" else 0.0
                stats.record(gpu_ms, value)

    def _should_overflow(self) -> bool:
        """Check if we should route to cloud."""
        if not self.cloud_bridge:
            return False
        queued = sum(1 for _, _, r in self._heap if r.status == "queued")
        return self.cloud_bridge.should_overflow(queued)

    def _call_ollama(self, req: InferenceRequest) -> dict:
        """
        Call Ollama via curl. We use subprocess + curl rather than urllib
        because the design spec says "stdlib + curl only" and curl gives
        us better timeout handling and connection management.
        """
        url = f"{self.ollama_url}/api/generate"
        payload = json.dumps({
            "model": req.model,
            "prompt": req.prompt,
            "stream": False,
            "options": req.options,
        })

        cmd = [
            "curl", "-s", "-S",
            "--max-time", "120",
            "--connect-timeout", "5",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", payload,
            url,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=130)
        if proc.returncode != 0:
            raise RuntimeError(f"curl failed (rc={proc.returncode}): {proc.stderr}")

        data = json.loads(proc.stdout)
        if "error" in data:
            raise RuntimeError(data["error"])

        return data
