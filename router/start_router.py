#!/usr/bin/env python3
"""
start_router.py — Router Initialization for the Live Production Line

Initializes the CognitiveRouter with:
  1. Local Ollama models (Granite 2B, Qwen 0.5B) at localhost:11434
  2. DeepInfra as cloud fallback (key from /home/eileen/mcp-deeinfra/.env)
  3. Cloudflare Workers AI as second fallback (free tier)

The router sits in front of the scheduler:
  router → scheduler → model

The router decides WHERE (reflex/local/cloud), the scheduler decides WHEN.

This script can be run standalone for testing, or imported by process_v2.py
to get a pre-configured router instance.

Usage:
  python3 start_router.py              # test routing decisions
  python3 start_router.py --serve      # start HTTP router on port 8772
  from start_router import get_router  # import in other code
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add parent to path so 'router' package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from router import (
    CognitiveRouter,
    RouteDecision,
    EpistemicState,
    ConfidenceAssessor,
    LocalModelSelector,
    CloudCascade,
    BoundaryTracker,
)
from router.router import ReflexCache, RouteTarget

logger = logging.getLogger("router.startup")

# ─── Configuration ───────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"

# Local models available on this machine (verified via ollama list)
LOCAL_MODELS = {
    "granite3.1-dense:2b": {
        "speed_toks": 76.8,
        "strengths": ["analytical", "problem_solving", "empathy", "reflection", "narrative"],
        "voice": "formal, structured, museum curator",
        "never_breaks_character": True,
    },
    "qwen2.5:0.5b": {
        "speed_toks": 178.8,
        "strengths": ["creative", "emotional", "instructional", "social"],
        "voice": "conversational, warm",
        "never_breaks_character": False,
    },
}

# DeepInfra key
DEEPINFRA_KEY = ""
_env_path = Path("/home/eileen/mcp-deeinfra/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if line.startswith("DEEPINFRA_API_KEY="):
            DEEPINFRA_KEY = line.split("=", 1)[1].strip()
            break

# Cloudflare (second fallback) — free tier
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "")


# ─── Router Factory ──────────────────────────────────────────────────────────

def get_router() -> CognitiveRouter:
    """
    Build a fully-configured CognitiveRouter.

    Wiring:
      - ReflexCache (in-process, confidence threshold 0.85)
      - ConfidenceAssessor (ensemble of 5 signals)
      - LocalModelSelector (Granite vs Qwen based on task type)
      - CloudCascade (DeepInfra → Cloudflare fallback chain)
      - BoundaryTracker (logs the evolving knowledge frontier)
    """
    reflex_cache = ReflexCache(confidence_threshold=0.85)
    assessor = ConfidenceAssessor()
    model_selector = LocalModelSelector()
    cloud_cascade = CloudCascade()  # uses default $1/day budget
    boundary_tracker = BoundaryTracker()

    router = CognitiveRouter(
        reflex_cache=reflex_cache,
        confidence_assessor=assessor,
        model_selector=model_selector,
        cloud_cascade=cloud_cascade,
        boundary_tracker=boundary_tracker,
    )

    logger.info("CognitiveRouter initialized:")
    logger.info("  Local models: %s", ", ".join(LOCAL_MODELS.keys()))
    logger.info("  DeepInfra key: %s", "loaded" if DEEPINFRA_KEY else "MISSING")
    logger.info("  Cloudflare: %s", "configured" if CF_ACCOUNT_ID and CF_API_TOKEN else "not configured (env vars needed)")
    logger.info("  Reflex threshold: 0.85")
    logger.info("  Cloud budget: $1.00/day")

    return router


def route_through_scheduler(router: CognitiveRouter, prompt: str,
                            agent: str = "game-processor",
                            scheduler_url: str = "http://localhost:8771") -> dict:
    """
    Full routing pipeline: router decides target, then uses scheduler
    for local/cloud execution.

    Returns the inference result dict.

    Flow:
      1. Router makes routing decision
      2. If REFLEX → return cached answer immediately ($0, <1ms)
      3. If LOCAL → submit to scheduler, poll for result ($0, ~1s)
      4. If CLOUD → submit to scheduler with cloud model hint ($$, ~15s)
      5. Record outcome back to router for learning
    """
    import subprocess as sp

    # Step 1: Route
    decision = router.route(prompt, agent=agent)
    logger.info("Route: %s → %s (confidence=%.3f, model=%s)",
                decision.epistemic_state.value,
                decision.target.value,
                decision.confidence,
                decision.model or "reflex")

    # Step 2: Reflex hit — instant return
    if decision.target == RouteTarget.REFLEX and decision.reflex_text:
        return {
            "response": decision.reflex_text,
            "model": "reflex",
            "served_by": "reflex",
            "latency_ms": 0.5,
            "cost": 0.0,
            "_route": decision.as_dict(),
        }

    # Step 3/4: Submit to scheduler
    model = decision.model or "granite3.1-dense:2b"
    if decision.target == RouteTarget.CLOUD:
        # Map cloud model names to scheduler-understood models
        # Scheduler's cloud_bridge handles Cloudflare; DeepInfra goes through options
        if "deepseek" in model:
            model = "deepseek-chat"  # scheduler can route this
        # DeepInfra models pass through as-is

    submit_payload = json.dumps({
        "prompt": prompt,
        "agent": agent,
        "priority": "HIGH" if agent == "game-processor" else "NORMAL",
        "model": model,
        "options": {},
    })

    # POST /infer
    result = sp.run(
        ["curl", "-s", "--max-time", "5",
         "-X", "POST",
         "-H", "Content-Type: application/json",
         "-d", submit_payload,
         f"{scheduler_url}/infer"],
        capture_output=True, text=True, timeout=10
    )
    submit_resp = json.loads(result.stdout)
    req_id = submit_resp.get("id")
    if not req_id:
        return {
            "response": "",
            "error": f"Scheduler submit failed: {submit_resp}",
            "served_by": "error",
        }

    # Poll for completion (up to 120s for cloud, 30s for local)
    max_wait = 120 if decision.target == RouteTarget.CLOUD else 30
    start = time.time()
    while time.time() - start < max_wait:
        poll = sp.run(
            ["curl", "-s", "--max-time", "5",
             f"{scheduler_url}/status/{req_id}"],
            capture_output=True, text=True, timeout=10
        )
        status = json.loads(poll.stdout)
        if status.get("status") in ("done", "error", "cancelled"):
            break
        time.sleep(0.5)

    # Extract result
    final = status
    if final.get("status") != "done":
        return {
            "response": "",
            "error": f"Request {final.get('status')}: {final.get('error', 'timeout')}",
            "served_by": "error",
            "_route": decision.as_dict(),
        }

    resp_data = final.get("result", {})
    response_text = resp_data.get("response", "")
    gpu_ms = 0
    if final.get("started_at") and final.get("completed_at"):
        gpu_ms = (final["completed_at"] - final["started_at"]) * 1000

    # Step 5: Record outcome for learning
    success = bool(response_text) and len(response_text) > 10
    quality = 0.7 if success else 0.2  # placeholder; real quality from downstream
    router.record_outcome(
        prompt=prompt,
        decision=decision,
        success=success,
        quality=quality,
        response_text=response_text if decision.target == RouteTarget.CLOUD else None,
    )

    return {
        "response": response_text,
        "model": final.get("model", model),
        "served_by": final.get("served_by", decision.target.value),
        "latency_ms": gpu_ms,
        "cost": decision.cost_estimate,
        "_route": decision.as_dict(),
    }


# ─── HTTP Server Mode ────────────────────────────────────────────────────────

def serve(port: int = 8772):
    """Run the router as an HTTP service alongside the scheduler."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse

    router = get_router()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            logger.debug("%s - %s", self.client_address[0], fmt % args)

        def _send_json(self, code, data):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            return json.loads(self.rfile.read(length))

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/route":
                body = self._read_body()
                prompt = body.get("prompt", "")
                agent = body.get("agent", "default")
                if not prompt:
                    self._send_json(400, {"error": "prompt required"})
                    return
                decision = router.route(prompt, agent=agent)
                self._send_json(200, decision.as_dict())

            elif parsed.path == "/infer":
                body = self._read_body()
                prompt = body.get("prompt", "")
                agent = body.get("agent", "default")
                scheduler_url = body.get("scheduler_url", "http://localhost:8771")
                if not prompt:
                    self._send_json(400, {"error": "prompt required"})
                    return
                result = route_through_scheduler(router, prompt, agent, scheduler_url)
                self._send_json(200, result)
            else:
                self._send_json(404, {"error": f"unknown path: {parsed.path}"})

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json(200, {"ok": True, "router": "cognitive"})
            elif parsed.path == "/stats":
                self._send_json(200, router.get_stats())
            elif parsed.path == "/boundary":
                self._send_json(200, router.get_boundary_report())
            else:
                self._send_json(404, {"error": f"unknown path: {parsed.path}"})

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logger.info("Router HTTP API on port %d", port)
    server.serve_forever()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cognitive Router Startup")
    parser.add_argument("--serve", action="store_true",
                       help="Start HTTP router API on port 8772")
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument("--test", type=str, default=None,
                       help="Test route a specific prompt")
    parser.add_argument("--self-test", action="store_true",
                       help="Run built-in self-test with sample prompts")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.serve:
        serve(port=args.port)
    elif args.test:
        router = get_router()
        result = route_through_scheduler(router, args.test)
        print(json.dumps(result, indent=2))
    else:
        # Quick self-test
        router = get_router()
        test_prompts = [
            "Build a castle",
            "What is 2+2?",
            "Create a sprawling medieval marketplace with vendor stalls",
        ]
        for p in test_prompts:
            decision = router.route(p)
            print(f"\nPrompt: {p}")
            print(f"  → {decision.epistemic_state.value} / {decision.target.value}")
            print(f"  Model: {decision.model or 'reflex'}")
            print(f"  Confidence: {decision.confidence:.3f}")
            print(f"  Reasoning: {decision.reasoning}")


if __name__ == "__main__":
    main()
