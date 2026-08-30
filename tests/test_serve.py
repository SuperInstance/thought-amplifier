"""
Tests for serve.py — the HTTP serve mode.

Real HTTP over an ephemeral port (ThreadingHTTPServer in a thread), stdlib
urllib client. Auth red/green, event ingest -> lesson round trip, stats.
No network beyond localhost; LLM path disabled (heuristic only).
"""

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import serve


TOKEN = "test-token-abc123"


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(serve, "INGEST_TOKEN", TOKEN)
    # Point both stores at tmp (serve constructs them per-request)
    monkeypatch.setattr("lesson_store.DEFAULT_STORE_DIR", tmp_path)
    monkeypatch.setattr("events_distiller.DEFAULT_EVENTS_DIR", tmp_path / "events")
    monkeypatch.setenv("TA_USE_LLM", "0")
    httpd = serve.make_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, json.loads(r.read())


def post(base, path, body, token=TOKEN):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def kid_events(player="wren"):
    return [
        {"id": "evt_r1", "player_id": player, "kind": "vibe_request",
         "payload": {"text": "make my ship bounce funny"}},
        {"id": "evt_v1", "player_id": player, "kind": "vibe_verdict",
         "payload": {"verdict": "applied", "suggestion_tiles": ["personality"]}},
        {"id": "evt_v2", "player_id": player, "kind": "vibe_verdict",
         "payload": {"verdict": "applied", "suggestion_tiles": ["personality"]}},
        {"id": "evt_v3", "player_id": player, "kind": "vibe_verdict",
         "payload": {"verdict": "discarded", "suggestion_tiles": ["bullet"]}},
    ]


# ─── open GET endpoints ────────────────────────────────────────

class TestGetEndpoints:
    def test_health(self, server):
        status, body = get(server, "/health")
        assert status == 200 and body["ok"] is True
        assert body["service"] == "thought-amplifier"
        assert "lessons" in body and "events" in body

    def test_stats_empty(self, server):
        status, body = get(server, "/stats")
        assert status == 200 and body["total"] == 0

    def test_lessons_empty_player(self, server):
        status, body = get(server, "/lessons?player=nobody")
        assert status == 200
        assert body["player"] == [] and body["global"] == []

    def test_unknown_route_404(self, server):
        with pytest.raises(urllib.error.HTTPError) as e:
            get(server, "/nope")
        assert e.value.code == 404


# ─── auth ──────────────────────────────────────────────────────

class TestAuth:
    def test_post_events_without_token_401(self, server):
        status, body = post(server, "/events", {"events": kid_events()}, token=None)
        assert status == 401 and body["error"] == "unauthorized"

    def test_post_events_with_wrong_token_401(self, server):
        status, body = post(server, "/events", {"events": kid_events()}, token="wrong")
        assert status == 401

    def test_post_disabled_without_configured_token(self, server, monkeypatch):
        monkeypatch.setattr(serve, "INGEST_TOKEN", "")
        status, body = post(server, "/events", {"events": kid_events()}, token="anything")
        assert status == 503  # clear "not configured" — never silent open


# ─── event ingest → lessons round trip ────────────────────────

class TestIngestRoundTrip:
    def test_ingest_creates_lessons(self, server):
        status, body = post(server, "/events", {"events": kid_events()})
        assert status == 200
        assert body["stored"] == 4
        assert body["players"] == ["wren"]
        assert len(body["lessons_created"]) >= 1
        lesson = body["lessons_created"][0]
        assert lesson["id"].startswith("les_")
        assert lesson["scope"] == "player"
        assert lesson["quality"]["composite"] > 0

    def test_lessons_endpoint_serves_player_lessons(self, server):
        post(server, "/events", {"events": kid_events()})
        status, body = get(server, "/lessons?player=wren")
        assert status == 200
        assert len(body["player"]) >= 1
        assert all(l["player_id"] == "wren" for l in body["player"])
        assert body["global"] == [], "amplifier never serves global lessons it distilled itself"

    def test_players_are_isolated(self, server):
        post(server, "/events", {"events": kid_events("wren")})
        status, body = get(server, "/lessons?player=theo")
        assert status == 200 and body["player"] == []

    def test_bad_event_shape_400(self, server):
        status, body = post(server, "/events", {"events": [{"id": "x"}]})
        assert status == 400 and body["error"] == "bad_request"

    def test_empty_events_400(self, server):
        status, body = post(server, "/events", {"events": []})
        assert status == 400

    def test_health_counts_after_ingest(self, server):
        post(server, "/events", {"events": kid_events()})
        status, body = get(server, "/health")
        assert body["lessons"] >= 1 and body["events"] == 4

    def test_stats_after_ingest(self, server):
        post(server, "/events", {"events": kid_events()})
        status, body = get(server, "/stats")
        assert body["total"] >= 1
        assert body["by_scope"]["player"] >= 1
        assert body["top_players"].get("wren") >= 1

    def test_redistill_from_stored_events(self, server):
        post(server, "/events", {"events": kid_events()})
        status, body = post(server, "/distill", {"player_id": "wren"})
        assert status == 200
        assert body["player_id"] == "wren"
        assert len(body["lessons_created"]) >= 1

    def test_lessons_limit_param(self, server):
        post(server, "/events", {"events": kid_events()})
        status, body = get(server, "/lessons?player=wren&limit=1")
        assert len(body["player"]) == 1
