#!/usr/bin/env python3
"""
serve.py — HTTP serve mode for the thought-amplifier lesson store.

The production face of the distillation loop: quilt-scratch's ta-bridge
Worker forwards kid play/vibe events here and pulls structured lessons back.
Pure Python stdlib (http.server) — no dependencies, by repo law.

Endpoints:
  GET  /health                 → {ok, lessons, events, ollama, breaker_open}
  GET  /stats                  → store stats (counts by domain/scope/player)
  GET  /lessons?player=&domain=&scope=&tag=&limit=
                               → {"player": [...], "global": [...]} — the
                                 player's distilled lessons plus any global
                                 (checked-off) lessons. Player tier is
                                 always served; global tier is read-only here.
  POST /events                 → Bearer TA_INGEST_TOKEN. Body {"events":[...]}
                                 → stores events, distills per-player lessons
                                 (heuristic by default; GLM when TA_USE_LLM=1),
                                 returns the lessons created.
  POST /distill                → Bearer token. Body {"player_id": "..."} —
                                 re-distill from the stored event history.

Auth law: GET endpoints are open (bind to localhost by default);
POST endpoints require TA_INGEST_TOKEN (constant-time compare) and are
disabled with a clear 503 when no token is configured.

Run:
  python3 serve.py --port 8772            # default localhost:8772
  python3 serve.py --selftest            # quick smoke test, no server
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from distillation_loop import breaker_is_open  # noqa: E402
from events_distiller import (  # noqa: E402
    EventStore,
    EventValidationError,
    distill_player_lessons,
)
from lesson_store import LessonStore, LessonValidationError  # noqa: E402

INGEST_TOKEN = os.environ.get("TA_INGEST_TOKEN", "")
SERVE_LOG = REPO_ROOT / "distillation-output" / "logs" / "serve.jsonl"
SERVE_LOG.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()  # serialize store writes across handler threads


def log_serve(event: dict) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    try:
        with _lock:
            with open(SERVE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ollama_up() -> bool:
    """Cheap liveness probe (connect-only; no inference)."""
    import subprocess

    try:
        r = subprocess.run(
            ["curl", "-s", "--connect-timeout", "2", "--max-time", "4",
             "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=6,
        )
        return r.returncode == 0 and "models" in r.stdout
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "thought-amplifier/1.0"

    # ── helpers ─────────────────────────────────────────────

    def _json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        presented = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if not INGEST_TOKEN:
            self._json(
                {"error": "unauthorized",
                 "hint": "TA_INGEST_TOKEN not configured on the server; POST is disabled."},
                503,
            )
            return False
        if not presented or not hmac.compare_digest(presented, INGEST_TOKEN):
            self._json(
                {"error": "unauthorized",
                 "hint": "POST endpoints require a valid bearer token (TA_INGEST_TOKEN)."},
                401,
            )
            return False
        return True

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:  # 2 MB cap
                self._json({"error": "bad_request", "detail": "Content-Length must be 1..2000000"}, 400)
                return None
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self._json({"error": "bad_request", "detail": "body must be valid JSON"}, 400)
            return None

    def log_message(self, fmt, *args):  # quiet default access log; serve.jsonl is the record
        pass

    # ── GET ─────────────────────────────────────────────────

    def do_GET(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)

        if url.path == "/health":
            self._json({
                "ok": True,
                "service": "thought-amplifier",
                "lessons": LessonStore().count(),
                "events": EventStore().count(),
                "ollama_up": _ollama_up(),
                "breaker_open": breaker_is_open(),
                "time": datetime.now(timezone.utc).isoformat(),
            })
            return

        if url.path == "/stats":
            self._json(LessonStore().stats())
            return

        if url.path == "/lessons":
            player = (params.get("player") or [None])[0]
            domain = (params.get("domain") or [None])[0]
            tag = (params.get("tag") or [None])[0]
            try:
                limit = min(200, max(1, int((params.get("limit") or ["50"])[0])))
            except ValueError:
                limit = 50
            store = LessonStore()
            player_lessons = (
                store.query(player_id=player, domain=domain, tag=tag, limit=limit)
                if player else []
            )
            global_lessons = store.query(scope="global", domain=domain, tag=tag, limit=limit)
            self._json({
                "player_id": player,
                "player": player_lessons,
                "global": global_lessons,
            })
            return

        self._json({"error": "not_found", "detail": f"no route for GET {url.path}"}, 404)

    # ── POST ────────────────────────────────────────────────

    def do_POST(self):
        url = urlparse(self.path)

        if url.path == "/events":
            if not self._authorized():
                return
            body = self._read_json()
            if body is None:
                return
            events = body.get("events")
            if not isinstance(events, list) or not events:
                self._json({"error": "bad_request", "detail": "body must be {events: [...]}"}, 400)
                return
            if len(events) > 500:
                self._json({"error": "bad_request", "detail": "max 500 events per batch"}, 400)
                return

            event_store = EventStore()
            lesson_store = LessonStore()
            try:
                with _lock:
                    stored = event_store.extend(events)
            except EventValidationError as e:
                self._json({"error": "bad_request", "detail": str(e)}, 400)
                return

            # Distill per distinct player (bounded work, synchronous).
            players = sorted({e["player_id"] for e in stored})
            created: list[dict] = []
            try:
                with _lock:
                    for pid in players:
                        player_events = event_store.all_for_player(pid)
                        created.extend(
                            distill_player_lessons(pid, player_events, store=lesson_store)
                        )
            except LessonValidationError as e:
                self._json({"error": "lesson_invalid", "detail": str(e)}, 500)
                return

            log_serve({"type": "events", "stored": len(stored), "players": players,
                       "lessons_created": len(created)})
            self._json({
                "stored": len(stored),
                "players": players,
                "lessons_created": created,
            })
            return

        if url.path == "/distill":
            if not self._authorized():
                return
            body = self._read_json()
            if body is None:
                return
            player_id = body.get("player_id")
            if not isinstance(player_id, str) or not player_id.strip():
                self._json({"error": "bad_request", "detail": "body must be {player_id: '...'}"}, 400)
                return
            event_store = EventStore()
            with _lock:
                lessons = distill_player_lessons(
                    player_id.strip(), event_store.all_for_player(player_id.strip())
                )
            log_serve({"type": "distill", "player_id": player_id, "lessons": len(lessons)})
            self._json({"player_id": player_id.strip(), "lessons_created": lessons})
            return

        self._json({"error": "not_found", "detail": f"no route for POST {url.path}"}, 404)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def selftest() -> int:
    """Smoke test the stores + distiller directly (no server, no network)."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        store = LessonStore(Path(td))
        events = EventStore(Path(td))
        evts = [
            {"id": "evt_1", "player_id": "wren", "kind": "vibe_request",
             "payload": {"text": "make my ship bounce funny"}},
            {"id": "evt_2", "player_id": "wren", "kind": "vibe_verdict",
             "payload": {"verdict": "applied", "suggestion_tiles": ["personality"]}},
            {"id": "evt_3", "player_id": "wren", "kind": "vibe_verdict",
             "payload": {"verdict": "applied", "suggestion_tiles": ["personality"]}},
            {"id": "evt_4", "player_id": "wren", "kind": "play_rewire",
             "payload": {"tiles": ["crumble"]}},
        ]
        events.extend(evts)
        lessons = distill_player_lessons("wren", events.all_for_player("wren"), store=store)
        assert lessons, "selftest: expected lessons"
        assert all(l["scope"] == "player" for l in lessons), "two-tier law"
        assert store.query(player_id="wren"), "selftest: query failed"
        print(f"selftest OK: {len(lessons)} lessons, ids={[l['id'] for l in lessons]}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="thought-amplifier serve mode")
    parser.add_argument("--host", default=os.environ.get("TA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TA_PORT", "8772")))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    server = make_server(args.host, args.port)
    print(f"thought-amplifier serving on http://{args.host}:{args.port}")
    print(f"  lessons store: {LessonStore().path}")
    print(f"  events store:  {EventStore().path}")
    print(f"  POST auth:     {'TA_INGEST_TOKEN set' if INGEST_TOKEN else 'NOT SET — POST disabled (503)'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
