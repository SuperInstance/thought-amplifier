"""
api.py — HTTP API for the Inference Scheduler

A lightweight stdlib HTTP server (no Flask, no FastAPI, no deps).
Agents POST to this instead of calling Ollama directly. The scheduler
handles serialization, priority, fair use, and cloud overflow.

Endpoints:
  POST /infer              Submit inference request
    body: {prompt, agent, priority, model, options}
    returns: {id, status, position}

  GET  /status/:id         Check request status
    returns: {id, status, result?, error?, gpu_ms, served_by}

  GET  /queue              Current queue state
    returns: {current, queued, queue_depth}

  POST /priority/:id       Update priority of queued request
    body: {priority}
    returns: {ok, id, priority}

  POST /cancel/:id         Cancel a queued request
    returns: {ok, id}

  GET  /stats              Fair-use and scheduling stats
    returns: {agents: {...}, cloud: {...}, evolver: {...}}

  GET  /health             Health check
    returns: {ok, uptime_s, requests_handled}

  POST /quality/:id        Submit quality feedback for a completed request
    body: {quality, timeliness}
    returns: {ok}

  GET  /policy             Export current evolved policy
    returns: {policy, agent_quality, ...}

Architecture:
  Requests are served by ThreadingHTTPServer (one thread per request).
  Handlers only enqueue work and read state; the scheduler worker runs
  the actual Ollama inference on its own daemon thread, and a second
  daemon thread periodically triggers policy evolution.

Does NOT: authenticate callers, rate-limit, use TLS, or persist any
state across restarts.
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from scheduler import InferenceScheduler, Priority
from fair_use import FairUseTracker
from cloud_bridge import CloudBridge
from priority_evolver import PriorityEvolver, OutcomeRecord

logger = logging.getLogger("api")

DEFAULT_PORT = 8771


class SchedulerAPI:
    """Wires together all scheduler components."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        port: int = DEFAULT_PORT,
    ):
        self.fair_use = FairUseTracker(
            window_s=300,
            default_floor_ms=2000,
            ceiling_ms=60000,
        )
        self.cloud = CloudBridge(overflow_threshold=3)
        self.evolver = PriorityEvolver(
            ema_alpha=0.05,
            min_observations=10,
            evolution_interval_s=120,
        )
        self.scheduler = InferenceScheduler(
            ollama_url=ollama_url,
            cloud_bridge=self.cloud,
            fair_use=self.fair_use,
        )
        self.port = port
        self._start_time = time.time()
        self._requests_handled = 0
        # Quality feedback storage (request_id -> (quality, timeliness))
        self._feedback: dict[str, tuple[float, float]] = {}

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler API starting on port %d", self.port)

        # Start evolver check loop
        t = threading.Thread(target=self._evolver_loop, daemon=True)
        t.start()

        server = ThreadingHTTPServer(
            ("0.0.0.0", self.port),
            self._make_handler()
        )

        def handle_shutdown(signum, frame):
            logger.info("Shutting down...")
            self.scheduler.stop()
            server.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        server.serve_forever()

    def _evolver_loop(self):
        """Periodically check if the policy should evolve."""
        while True:
            time.sleep(10)
            if self.scheduler._running:
                self.evolver.maybe_evolve()

    def _make_handler(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug("%s - %s", self.client_address[0], fmt % args)

            def _send_json(self, code: int, data: dict):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_body(self) -> dict:
                length = int(self.headers.get("Content-Length", 0))
                if length == 0:
                    return {}
                raw = self.rfile.read(length)
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {}

            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path
                api._requests_handled += 1

                if path == "/infer":
                    body = self._read_body()
                    prompt = body.get("prompt", "")
                    if not prompt:
                        self._send_json(400, {"error": "prompt required"})
                        return

                    agent = body.get("agent", "default")
                    priority = body.get("priority", "NORMAL")
                    model = body.get("model", "granite3.1-dense:2b")
                    options = body.get("options", {})

                    # Register agent for fair-use tracking
                    api.fair_use.register(agent)

                    # Apply learned priority adjustment
                    base_pri = Priority.parse(priority) if isinstance(priority, str) else Priority(priority)
                    context = {
                        "agent": agent,
                        "time_of_day": time.localtime().tm_hour,
                        "queue_depth": len(api.scheduler._heap),
                        "recent_load": api._estimate_load(),
                    }
                    effective_pri = api.evolver.effective_priority(
                        int(base_pri), agent, context
                    )
                    effective_pri = Priority(effective_pri)

                    req = api.scheduler.submit(
                        prompt=prompt,
                        agent=agent,
                        priority=effective_pri,
                        model=model,
                        options=options,
                    )
                    self._send_json(200, {
                        "id": req.id,
                        "status": req.status,
                        "priority": effective_pri.name,
                        "base_priority": base_pri.name,
                        "position": sum(1 for _, _, r in api.scheduler._heap
                                       if r.status == "queued"),
                    })

                elif path.startswith("/priority/"):
                    req_id = path.split("/priority/")[-1]
                    body = self._read_body()
                    pri = body.get("priority")
                    if pri is None:
                        self._send_json(400, {"error": "priority required"})
                        return
                    ok = api.scheduler.update_priority(req_id, pri)
                    if ok:
                        self._send_json(200, {"ok": True, "id": req_id,
                                              "priority": Priority.parse(pri).name
                                              if isinstance(pri, str)
                                              else Priority(pri).name})
                    else:
                        self._send_json(404, {"error": "not found or not queued"})

                elif path.startswith("/cancel/"):
                    req_id = path.split("/cancel/")[-1]
                    ok = api.scheduler.cancel(req_id)
                    if ok:
                        self._send_json(200, {"ok": True, "id": req_id})
                    else:
                        self._send_json(404, {"error": "not found or not queued"})

                elif path.startswith("/quality/"):
                    req_id = path.split("/quality/")[-1]
                    body = self._read_body()
                    quality = body.get("quality", 0.5)
                    timeliness = body.get("timeliness", 0.5)

                    req = api.scheduler.get(req_id)
                    if not req:
                        self._send_json(404, {"error": "not found"})
                        return

                    api._feedback[req_id] = (quality, timeliness)

                    # Record outcome for evolution
                    gpu_ms = 0
                    if req.started_at and req.completed_at:
                        gpu_ms = (req.completed_at - req.started_at) * 1000

                    record = OutcomeRecord(
                        agent=req.agent,
                        assigned_priority=int(req.priority),
                        base_priority=int(req.priority),
                        quality=quality,
                        timeliness=timeliness,
                        gpu_ms=gpu_ms,
                        served_by=req.served_by,
                        timestamp=time.time(),
                        time_of_day=time.localtime().tm_hour,
                        queue_depth=0,
                        recent_load=api._estimate_load(),
                    )
                    api.evolver.record_outcome(record)

                    # Also update fair-use value score
                    api.fair_use.record(req.agent, gpu_ms, quality)

                    self._send_json(200, {"ok": True})

                else:
                    self._send_json(404, {"error": f"unknown path: {path}"})

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path

                if path == "/health":
                    self._send_json(200, {
                        "ok": True,
                        "uptime_s": round(time.time() - api._start_time, 1),
                        "requests_handled": api._requests_handled,
                    })

                elif path == "/queue":
                    self._send_json(200, api.scheduler.queue_snapshot())

                elif path.startswith("/status/"):
                    req_id = path.split("/status/")[-1]
                    req = api.scheduler.get(req_id)
                    if not req:
                        self._send_json(404, {"error": "not found"})
                        return
                    result = {
                        "id": req.id,
                        "status": req.status,
                        "agent": req.agent,
                        "priority": req.priority.name,
                        "model": req.model,
                        "served_by": req.served_by,
                        "submitted_at": req.submitted_at,
                        "started_at": req.started_at,
                        "completed_at": req.completed_at,
                        "wait_ms": ((req.started_at or time.time()) - req.submitted_at) * 1000,
                        "gpu_ms": ((req.completed_at - req.started_at) * 1000)
                                  if req.completed_at and req.started_at else None,
                        "error": req.error,
                    }
                    if req.result:
                        result["result"] = req.result
                    self._send_json(200, result)

                elif path == "/stats":
                    self._send_json(200, {
                        "agents": api.scheduler.all_stats(),
                        "fair_use": api.fair_use.stats(),
                        "cloud": api.cloud.stats(),
                        "evolver": api.evolver.stats(),
                        "uptime_s": round(time.time() - api._start_time, 1),
                    })

                elif path == "/policy":
                    self._send_json(200, api.evolver.export_policy())

                else:
                    self._send_json(404, {"error": f"unknown path: {path}"})

        return Handler

    def _estimate_load(self) -> float:
        """Rough estimate of current system load (0-1)."""
        stats = self.scheduler.all_stats()
        total_window = sum(s.get("window_gpu_ms", 0) for s in stats.values())
        capacity = self.fair_use.total_capacity()
        if capacity <= 0:
            return 0
        return min(1.0, total_window / capacity)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inference Scheduler")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ollama", default="http://localhost:11434",
                       help="Ollama URL")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    api = SchedulerAPI(ollama_url=args.ollama, port=args.port)
    api.start()


if __name__ == "__main__":
    main()
