"""
Tests for events_distiller.py — the kid-events pathway.

Heuristic distillation (deterministic, no network), LLM path (mocked),
graceful fallback, the two-tier law (never writes scope='global'),
and event validation.
"""

import json
from pathlib import Path

import pytest

import events_distiller as ed
from events_distiller import (
    EventStore,
    EventValidationError,
    digest_events,
    distill_player_lessons,
    heuristic_lessons,
    llm_lessons,
)
from lesson_store import LessonStore


@pytest.fixture
def store_dir(tmp_path):
    return tmp_path


@pytest.fixture
def lesson_store(store_dir):
    return LessonStore(store_dir)


@pytest.fixture
def event_store(store_dir):
    return EventStore(store_dir)


def request_event(i, text, player="wren"):
    return {"id": f"evt_r{i}", "player_id": player, "kind": "vibe_request",
            "payload": {"text": text}}


def verdict_event(i, verdict, tiles, player="wren"):
    return {"id": f"evt_v{i}", "player_id": player, "kind": "vibe_verdict",
            "payload": {"verdict": verdict, "suggestion_tiles": tiles}}


def rewire_event(i, tiles, player="wren"):
    return {"id": f"evt_w{i}", "player_id": player, "kind": "play_rewire",
            "payload": {"tiles": tiles}}


# ─── event validation ──────────────────────────────────────────

class TestEventValidation:
    def test_valid_event_passes(self):
        out = ed.validate_event(request_event(1, "hi"))
        assert out["ts"]  # ts defaulted

    def test_missing_id_rejected(self):
        bad = request_event(1, "hi")
        del bad["id"]
        with pytest.raises(EventValidationError):
            ed.validate_event(bad)

    def test_missing_player_rejected(self):
        with pytest.raises(EventValidationError):
            ed.validate_event({**request_event(1, "hi"), "player_id": ""})

    def test_bad_kind_rejected(self):
        with pytest.raises(EventValidationError):
            ed.validate_event({**request_event(1, "hi"), "kind": "keystroke"})

    def test_bad_verdict_rejected(self):
        with pytest.raises(EventValidationError):
            ed.validate_event(verdict_event(1, "maybe", ["personality"]))

    def test_store_extend_rejects_batch_with_bad_row(self, event_store):
        with pytest.raises(EventValidationError):
            event_store.extend([request_event(1, "ok"), {"id": "evt_bad"}])
        assert event_store.count() == 0, "batch is atomic — nothing stored on error"


# ─── digest ────────────────────────────────────────────────────

class TestDigest:
    def test_digest_counts(self):
        events = [
            verdict_event(1, "applied", ["personality"]),
            verdict_event(2, "applied", ["personality", "actor"]),
            verdict_event(3, "discarded", ["bullet"]),
            rewire_event(1, ["crumble"]),
            request_event(1, "make my ship bounce"),
        ]
        d = digest_events(events)
        assert d["verdicts"] == {"applied": 2, "discarded": 1}
        assert d["applied_tiles"]["personality"] == 2
        assert d["discarded_tiles"]["bullet"] == 1
        assert d["wired_tiles"]["crumble"] == 1
        assert d["recent_requests"] == ["make my ship bounce"]


# ─── heuristic lessons ─────────────────────────────────────────

class TestHeuristicLessons:
    def test_strong_apply_pattern_produces_preference_lesson(self):
        events = [
            verdict_event(1, "applied", ["personality"]),
            verdict_event(2, "applied", ["personality"]),
            verdict_event(3, "applied", ["personality"]),
        ]
        lessons = heuristic_lessons("wren", digest_events(events), ["e1", "e2", "e3"])
        assert any("personality" in l["lesson"] and "tile-personality" in l["tags"] for l in lessons)
        assert all(l["source_streams"]["events"] == ["e1", "e2", "e3"] for l in lessons)

    def test_discard_pattern_produces_avoid_lesson(self):
        events = [
            verdict_event(1, "discarded", ["bullet"]),
            verdict_event(2, "discarded", ["bullet"]),
            verdict_event(3, "discarded", ["bullet"]),
        ]
        lessons = heuristic_lessons("wren", digest_events(events), [])
        assert any("Avoid" in l["lesson"] and "avoid" in l["tags"] for l in lessons)

    def test_cold_start_single_event(self):
        lessons = heuristic_lessons("wren", digest_events([request_event(1, "hi")]), ["e1"])
        assert len(lessons) == 1
        assert "cold-start" in lessons[0]["tags"]

    def test_no_events_no_lessons(self):
        assert heuristic_lessons("wren", digest_events([]), []) == []


# ─── distill end-to-end (heuristic) ────────────────────────────

class TestDistillPlayerLessons:
    def test_two_tier_law_never_global(self, lesson_store):
        events = [verdict_event(i, "applied", ["personality"]) for i in range(1, 4)]
        stored = distill_player_lessons("wren", events, use_llm=False, store=lesson_store)
        assert stored
        assert all(l["scope"] == "player" for l in stored)
        assert all(l["player_id"] == "wren" for l in stored)

    def test_lessons_are_structured_and_persisted(self, lesson_store):
        events = [verdict_event(i, "applied", ["personality"]) for i in range(1, 4)]
        stored = distill_player_lessons("wren", events, use_llm=False, store=lesson_store)
        for l in stored:
            assert l["id"].startswith("les_")
            assert l["domain"] == "quilt-scratch"
            assert isinstance(l["quality"]["composite"], float)
            assert 0.0 <= l["quality"]["confidence"] <= 1.0
            assert l["generator"] == "heuristic"
            assert isinstance(l["tags"], list)
        assert lesson_store.query(player_id="wren"), "must persist to the store"

    def test_filters_other_players_events(self, lesson_store):
        events = [
            *([verdict_event(i, "applied", ["personality"]) for i in range(1, 4)]),
            verdict_event(9, "discarded", ["bullet"], player="theo"),
        ]
        stored = distill_player_lessons("wren", events, use_llm=False, store=lesson_store)
        assert all("theo" not in (l.get("lesson") or "") for l in stored)

    def test_empty_events_returns_empty(self, lesson_store):
        assert distill_player_lessons("wren", [], use_llm=False, store=lesson_store) == []


# ─── LLM path (mocked) ─────────────────────────────────────────

def make_llm_post(content):
    calls = []

    def post(url, headers, data, **kw):
        calls.append(data)
        return {"choices": [{"message": {"content": content}}]}

    post.calls = calls
    return post


class TestLlmPath:
    @pytest.fixture(autouse=True)
    def fake_key(self, monkeypatch):
        """Pin a key so outcomes come from the mocked transport, not early exit."""
        monkeypatch.setattr(ed, "GLM_API_KEY", "fake-key")

    def test_llm_lessons_parsed(self):
        content = 'Here you go:\n[{"lesson": "Suggest bouncy personality tiles first.", "tags": ["personality"]}]'
        post = make_llm_post(content)
        raw = llm_lessons("wren", {"event_count": 5}, http_post=post)
        assert raw == [{"lesson": "Suggest bouncy personality tiles first.", "tags": ["personality"]}]

    def test_llm_failure_returns_none(self):
        def failing_post(url, headers, data, **kw):
            return {"error": "HTTP 429"}

        assert llm_lessons("wren", {"event_count": 5}, http_post=failing_post) is None

    def test_llm_garbage_returns_none(self):
        post = make_llm_post("I cannot answer that in JSON, sorry!")
        assert llm_lessons("wren", {"event_count": 5}, http_post=post) is None

    def test_distill_uses_llm_then_falls_back(self, lesson_store, monkeypatch):
        monkeypatch.setenv("TA_USE_LLM", "1")
        monkeypatch.setattr(ed, "GLM_API_KEY", "fake-key")

        # LLM returns one good lesson
        post = make_llm_post('[{"lesson": "Lead with playful personality wiring.", "tags": ["personality"]}]')
        stored = distill_player_lessons("wren", [verdict_event(i, "applied", ["personality"]) for i in range(1, 4)], http_post=post, store=lesson_store)
        assert any(l["generator"] == "glm-4.5-flash" for l in stored)

        # LLM dies -> heuristic fallback, still produces lessons
        def dead_post(url, headers, data, **kw):
            return {"error": "connection refused"}

        stored2 = distill_player_lessons("wren", [verdict_event(i, "discarded", ["bullet"]) for i in range(1, 4)], http_post=dead_post, store=lesson_store)
        assert stored2 and all(l["generator"] == "heuristic" for l in stored2)

    def test_no_api_key_means_no_llm_call(self, lesson_store, monkeypatch):
        """No key configured -> LLM path declines BEFORE any transport call."""
        monkeypatch.setattr(ed, "GLM_API_KEY", "")
        monkeypatch.delenv("GLM_API_KEY", raising=False)
        post = make_llm_post('[{"lesson": "x", "tags": []}]')
        assert llm_lessons("wren", {"event_count": 5}, http_post=post) is None
        assert post.calls == [], "no transport call when key is absent"


# ─── event store ───────────────────────────────────────────────

class TestEventStore:
    def test_extend_and_all_for_player(self, event_store):
        event_store.extend([request_event(1, "a"), request_event(2, "b", player="theo")])
        assert event_store.count() == 2
        rows = event_store.all_for_player("wren")
        assert len(rows) == 1 and rows[0]["id"] == "evt_r1"

    def test_ts_defaulted_iso(self, event_store):
        event_store.extend([request_event(1, "a")])
        assert "T" in event_store.all_for_player("wren")[0]["ts"]
