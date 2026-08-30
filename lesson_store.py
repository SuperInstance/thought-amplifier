"""
Lesson Store — structured, persisted, re-servable lessons.

The distillation loop's output used to be scattered across .nail reflexes
and per-iteration artifacts. This module is the single canonical store:
every lesson the system produces (domain-teaching reflexes AND
event-distilled player lessons) lands here as structured JSON and is
re-servable by id/player/domain/tag via serve.py.

Schema (one JSON object per line in lessons.jsonl):

{
  "id": "les_<16hex>",            # stable id (assigned if missing)
  "created": "2026-08-30T...",    # ISO-8601 UTC (assigned if missing)
  "scope": "player" | "global",   # the two-tier law: the amplifier only
                                   # ever WRITES "player"; "global" rows can
                                   # only be minted by the human review flow
                                   # on the bridge side (quilt-scratch).
  "player_id": "wren" | null,     # required for player scope
  "domain": "quilt-scratch",      # source system / distillation domain
  "source_streams": {...},        # provenance: event ids / iteration refs
  "lesson": "...",                # the lesson text itself
  "quality": {                    # quality scores (0..1)
    "novelty", "specificity", "engagement", "spatial",
    "composite",                  # weighted composite
    "coverage",                   # fraction of source events reflected
    "confidence"                  # sample-size / evidence confidence
  },
  "tags": ["personality", "verdict-good"],
  "teaching_helped": true/false/null,  # delta-based loops only
  "generator": "heuristic" | "glm-..." # what produced it
}

Design notes:
  - stdlib only (json, hashlib, pathlib) — no deps, matches the repo law.
  - append-only file; query() dedupes by id keeping the latest row.
  - corrupt lines are skipped (counted in stats), never crash the store.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_STORE_DIR = Path(
    os.environ.get("TA_STORE_DIR", REPO_ROOT / "distillation-output" / "lessons")
)

QUALITY_KEYS = ("novelty", "specificity", "engagement", "spatial", "composite")


class LessonValidationError(ValueError):
    """A lesson record doesn't match the contract."""


def new_lesson_id(seed: str = "") -> str:
    """Stable-ish id: random-ish hash of seed + time, 16 hex chars."""
    raw = f"{seed}|{datetime.now(timezone.utc).isoformat()}|{os.urandom(4).hex()}"
    return "les_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def validate_lesson(record: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a lesson record. Raises LessonValidationError."""
    if not isinstance(record, dict):
        raise LessonValidationError("lesson must be a JSON object")

    lesson_text = record.get("lesson")
    if not isinstance(lesson_text, str) or not lesson_text.strip():
        raise LessonValidationError("lesson text must be a non-empty string")

    scope = record.get("scope", "player")
    if scope not in ("player", "global"):
        raise LessonValidationError("scope must be 'player' or 'global'")

    player_id = record.get("player_id")
    if scope == "player" and not player_id:
        raise LessonValidationError("player scope requires player_id")

    quality = record.get("quality") or {}
    if not isinstance(quality, dict) or not isinstance(quality.get("composite"), (int, float)):
        raise LessonValidationError("quality.composite (number) is required")

    tags = record.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise LessonValidationError("tags must be a list of strings")

    normalized = dict(record)
    normalized["scope"] = scope
    normalized["lesson"] = lesson_text.strip()
    normalized["quality"] = quality
    normalized["tags"] = tags
    normalized.setdefault("id", new_lesson_id(lesson_text[:64]))
    normalized.setdefault("created", datetime.now(timezone.utc).isoformat())
    normalized.setdefault("domain", "unspecified")
    normalized.setdefault("source_streams", {})
    normalized.setdefault("teaching_helped", None)
    normalized.setdefault("generator", "unknown")
    return normalized


class LessonStore:
    """Append-only JSONL store with id-deduped queries."""

    def __init__(self, store_dir: Path | str | None = None):
        self.dir = Path(store_dir) if store_dir else DEFAULT_STORE_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "lessons.jsonl"

    # ── writes ─────────────────────────────────────────────

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        """Validate, assign id/created if missing, append. Returns stored record."""
        lesson = validate_lesson(record)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
        return lesson

    # ── reads ──────────────────────────────────────────────

    def _rows(self) -> list[dict[str, Any]]:
        """All rows; corrupt lines skipped (counted via stats())."""
        rows: list[dict[str, Any]] = []
        if not self.path.exists():
            return rows
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except json.JSONDecodeError:
                continue
        return rows

    def _dedupe_latest(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep the LAST row per id (re-appends supersede)."""
        latest: dict[str, Any] = {}
        for row in rows:
            latest[row.get("id", "")] = row
        return list(latest.values())

    def query(
        self,
        player_id: str | None = None,
        domain: str | None = None,
        scope: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query lessons, newest-first (by created). Deduped by id."""
        rows = self._dedupe_latest(self._rows())
        if player_id is not None:
            rows = [r for r in rows if r.get("player_id") == player_id]
        if domain is not None:
            rows = [r for r in rows if r.get("domain") == domain]
        if scope is not None:
            rows = [r for r in rows if r.get("scope") == scope]
        if tag is not None:
            rows = [r for r in rows if tag in (r.get("tags") or [])]
        rows.sort(key=lambda r: r.get("created", ""), reverse=True)
        return rows[:limit]

    def get(self, lesson_id: str) -> dict[str, Any] | None:
        for row in self._dedupe_latest(self._rows()):
            if row.get("id") == lesson_id:
                return row
        return None

    def count(self) -> int:
        return len(self._dedupe_latest(self._rows()))

    def stats(self) -> dict[str, Any]:
        """Counts by scope/domain + top players."""
        rows = self._dedupe_latest(self._rows())
        by_domain: dict[str, int] = {}
        by_scope: dict[str, int] = {}
        by_player: dict[str, int] = {}
        for r in rows:
            by_domain[r.get("domain", "unspecified")] = by_domain.get(r.get("domain", "unspecified"), 0) + 1
            by_scope[r.get("scope", "?")] = by_scope.get(r.get("scope", "?"), 0) + 1
            pid = r.get("player_id")
            if pid:
                by_player[pid] = by_player.get(pid, 0) + 1
        return {
            "total": len(rows),
            "by_domain": by_domain,
            "by_scope": by_scope,
            "top_players": dict(sorted(by_player.items(), key=lambda kv: -kv[1])[:10]),
        }
