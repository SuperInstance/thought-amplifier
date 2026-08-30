"""
Tests for lesson_store.py — the structured, persisted lesson store.

Red/green per feature: validation contract, id assignment, persistence,
dedup-by-id queries, scope/player/domain/tag filters, corrupt-line tolerance.
"""

import json
from pathlib import Path

import pytest

from lesson_store import LessonStore, LessonValidationError, new_lesson_id, validate_lesson


@pytest.fixture
def store(tmp_path):
    return LessonStore(tmp_path)


def valid_lesson(**overrides):
    base = {
        "scope": "player",
        "player_id": "wren",
        "domain": "quilt-scratch",
        "lesson": "Lead with personality tiles for wren — they applied 3 of those.",
        "quality": {"composite": 0.42, "novelty": 0.4, "confidence": 0.35},
        "tags": ["tile-personality", "preference"],
        "generator": "heuristic",
    }
    base.update(overrides)
    return base


# ─── validation ────────────────────────────────────────────────

class TestValidation:
    def test_valid_lesson_passes(self):
        out = validate_lesson(valid_lesson())
        assert out["scope"] == "player"

    def test_missing_lesson_text_rejected(self):
        bad = valid_lesson()
        del bad["lesson"]
        with pytest.raises(LessonValidationError):
            validate_lesson(bad)

    def test_empty_lesson_text_rejected(self):
        with pytest.raises(LessonValidationError):
            validate_lesson(valid_lesson(lesson="   "))

    def test_player_scope_requires_player_id(self):
        with pytest.raises(LessonValidationError):
            validate_lesson(valid_lesson(scope="player", player_id=None))

    def test_bad_scope_rejected(self):
        with pytest.raises(LessonValidationError):
            validate_lesson(valid_lesson(scope="universe"))

    def test_missing_composite_rejected(self):
        bad = valid_lesson(quality={"novelty": 0.5})
        with pytest.raises(LessonValidationError):
            validate_lesson(bad)

    def test_bad_tags_rejected(self):
        with pytest.raises(LessonValidationError):
            validate_lesson(valid_lesson(tags=["ok", 42]))


# ─── append + persistence ──────────────────────────────────────

class TestAppendAndPersistence:
    def test_append_assigns_id_and_created(self, store):
        rec = store.append(valid_lesson())
        assert rec["id"].startswith("les_") and len(rec["id"]) == 20
        assert "T" in rec["created"]  # ISO timestamp

    def test_append_persists_across_instances(self, store, tmp_path):
        store.append(valid_lesson())
        store2 = LessonStore(tmp_path)  # fresh handle, same dir
        assert store2.count() == 1

    def test_append_rejects_invalid(self, store):
        with pytest.raises(LessonValidationError):
            store.append({"lesson": ""})
        assert store.count() == 0

    def test_reappend_same_id_supersedes(self, store):
        first = store.append(valid_lesson())
        updated = dict(first)
        updated["lesson"] = "Updated lesson text with more detail"
        updated["quality"] = {**first["quality"], "composite": 0.6}
        store.append(updated)
        rows = store.query(player_id="wren")
        assert len(rows) == 1
        assert rows[0]["lesson"].startswith("Updated")


# ─── query filters ─────────────────────────────────────────────

class TestQueries:
    @pytest.fixture(autouse=True)
    def seed(self, store):
        store.append(valid_lesson(player_id="wren", tags=["a", "b"]))
        store.append(valid_lesson(player_id="theo", tags=["b"]))
        store.append(valid_lesson(scope="global", player_id=None, tags=["gold"]))
        store.append(valid_lesson(player_id="wren", domain="roblox", tags=["c"]))
        return store

    def test_query_by_player(self, store):
        rows = store.query(player_id="wren")
        assert len(rows) == 2
        assert all(r["player_id"] == "wren" for r in rows)

    def test_query_by_scope_global(self, store):
        rows = store.query(scope="global")
        assert len(rows) == 1
        assert rows[0]["player_id"] is None

    def test_query_by_domain(self, store):
        assert len(store.query(domain="roblox")) == 1

    def test_query_by_tag(self, store):
        assert len(store.query(tag="b")) == 2
        assert len(store.query(tag="gold")) == 1

    def test_query_limit(self, store):
        assert len(store.query(limit=2)) == 2

    def test_query_newest_first(self, store):
        rows = store.query()
        created = [r["created"] for r in rows]
        assert created == sorted(created, reverse=True)

    def test_get_by_id(self, store):
        rec = store.query(player_id="theo")[0]
        assert store.get(rec["id"])["player_id"] == "theo"
        assert store.get("les_nope") is None


# ─── robustness ────────────────────────────────────────────────

class TestRobustness:
    def test_corrupt_lines_skipped(self, store):
        store.append(valid_lesson())
        with open(store.path, "a", encoding="utf-8") as f:
            f.write("{this is not json\n\n")
        assert store.count() == 1
        assert len(store.query()) == 1

    def test_stats(self, store):
        store.append(valid_lesson(player_id="wren"))
        store.append(valid_lesson(player_id="wren"))
        store.append(valid_lesson(player_id="theo"))
        s = store.stats()
        assert s["total"] == 3
        assert s["by_scope"]["player"] == 3
        assert s["top_players"]["wren"] == 2

    def test_new_lesson_id_unique(self):
        ids = {new_lesson_id() for _ in range(50)}
        assert len(ids) == 50
