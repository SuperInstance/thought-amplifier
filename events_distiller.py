"""
Events Distiller — the kid-events pathway into the lesson store.

Phase 2 of the quilt-scratch integration (2026-08-30): the ta-bridge Worker
forwards batches of play + vibe-coder IO events here; this module distills
them into STRUCTURED per-player lessons (the two-tier law: scope is always
"player" — global promotion happens only in the Worker's human review flow,
never here).

Two generators, in priority order:
  1. LLM path — GLM (via the repo's existing _curl_post_json infra) reads an
     event digest and returns lesson JSON. Used when TA_USE_LLM=1 and a key
     is present. Falls back to (2) on ANY failure.
  2. Heuristic path — deterministic stats over the events (verdict ratios,
     tile-type preferences, request patterns). No LLM, no network; this is
     the default and the guaranteed floor.

Event contract (matches quilt-scratch/docs/TA-BRIDGE.md):
{
  "id": "evt_...",                  # unique, required
  "ts": "2026-08-30T...",           # ISO, optional
  "player_id": "wren",              # required
  "kind": "vibe_request" | "vibe_verdict" | "play_rewire" | "play_save"
                                   # | "fabric_snapshot"
  "payload": { ... }                # kind-specific:
                                   #   vibe_request:  {text, fabric_digest?}
                                   #   vibe_verdict:  {verdict: applied|discarded
                                   #                   |thumb_up|thumb_down,
                                   #                   suggestion_tiles?: [types]}
                                   #   play_rewire:   {tiles?: [types]}
                                   #   play_save:     {tiles?: [types]}
                                   #   fabric_snapshot: {tiles: [types], wires: n}
}
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from distillation_loop import GLM_API_KEY, GLM_API_URL, GLM_MODEL, _curl_post_json, score_response, composite_score
from lesson_store import LessonStore, new_lesson_id

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_EVENTS_DIR = Path(
    os.environ.get("TA_STORE_DIR", REPO_ROOT / "distillation-output" / "lessons")
) / "events"

EVENT_KINDS = {"vibe_request", "vibe_verdict", "play_rewire", "play_save", "fabric_snapshot"}
VERDICT_KINDS = {"applied", "discarded", "thumb_up", "thumb_down"}

LLM_LESSON_PROMPT = """You distill play-telemetry from a no-code game engine for kids into teaching lessons for a helper agent.

You will see a digest of one player's recent events: what they asked the helper for, whether they applied or discarded each suggestion, and which tile types they wired themselves.

Produce 1-3 SHORT lessons (one sentence each, kid-agent voice, concrete) that tell the helper agent what to suggest MORE of, what to AVOID, and any pattern in how this kid builds. Return ONLY a JSON array of objects:
[{"lesson": "...", "tags": ["tile-type-or-pattern", ...]}]

Rules: no filler, no preamble, plain JSON array, every lesson grounded in the digest (no invention), max 20 words per lesson."""


class EventValidationError(ValueError):
    """An event doesn't match the contract."""


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EventValidationError("event must be a JSON object")
    if not isinstance(event.get("id"), str) or not event["id"].strip():
        raise EventValidationError("event.id (string) is required")
    if not isinstance(event.get("player_id"), str) or not event["player_id"].strip():
        raise EventValidationError("event.player_id (string) is required")
    kind = event.get("kind")
    if kind not in EVENT_KINDS:
        raise EventValidationError(f"event.kind must be one of {sorted(EVENT_KINDS)}")
    payload = event.get("payload", {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise EventValidationError("event.payload must be a JSON object")
    if kind == "vibe_verdict":
        verdict = payload.get("verdict")
        if verdict not in VERDICT_KINDS:
            raise EventValidationError(
                f"vibe_verdict payload.verdict must be one of {sorted(VERDICT_KINDS)}"
            )
    normalized = dict(event)
    normalized["payload"] = payload
    normalized.setdefault(
        "ts", datetime.now(timezone.utc).isoformat()
    )
    return normalized


class EventStore:
    """Append-only JSONL event store (same laws as LessonStore)."""

    def __init__(self, store_dir: Path | str | None = None):
        self.dir = Path(store_dir) if store_dir else DEFAULT_EVENTS_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "events.jsonl"

    def extend(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate + append a batch, skipping event ids already stored
        (idempotent ingest — the bridge re-forwards on flush/retry, and a
        retried event must not double-count in the digest history).
        Raises EventValidationError on a contract-violating row (atomic:
        nothing stored when validation fails).
        """
        normalized = [validate_event(e) for e in events]
        known = {e.get("id") for e in self._rows()}
        fresh = [e for e in normalized if e["id"] not in known]
        if fresh:
            with open(self.path, "a", encoding="utf-8") as f:
                for e in fresh:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return fresh

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return rows

    def all_for_player(self, player_id: str) -> list[dict[str, Any]]:
        return [r for r in self._rows() if r.get("player_id") == player_id]

    def count(self) -> int:
        if not self.path.exists():
            return 0
        n = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                n += 1
        return n


# ─── Digest + heuristics ───────────────────────────────────────

def digest_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic stats digest of one player's events."""
    verdicts = Counter()
    applied_tiles = Counter()
    discarded_tiles = Counter()
    wired_tiles = Counter()
    requests: list[str] = []

    for e in events:
        kind = e.get("kind")
        payload = e.get("payload") or {}
        if kind == "vibe_verdict":
            verdicts[payload.get("verdict", "?")] += 1
            tiles = payload.get("suggestion_tiles") or []
            if payload.get("verdict") in ("applied", "thumb_up"):
                applied_tiles.update(tiles)
            elif payload.get("verdict") in ("discarded", "thumb_down"):
                discarded_tiles.update(tiles)
        elif kind in ("play_rewire", "play_save"):
            wired_tiles.update(payload.get("tiles") or [])
        elif kind == "vibe_request":
            text = payload.get("text")
            if isinstance(text, str) and text.strip():
                requests.append(text.strip()[:120])

    return {
        "event_count": len(events),
        "verdicts": dict(verdicts),
        "applied_tiles": dict(applied_tiles.most_common(8)),
        "discarded_tiles": dict(discarded_tiles.most_common(8)),
        "wired_tiles": dict(wired_tiles.most_common(8)),
        "recent_requests": requests[-5:],
    }


def heuristic_lessons(player_id: str, digest: dict[str, Any], event_ids: list[str]) -> list[dict[str, Any]]:
    """Deterministic lessons from the digest. No LLM, no network."""
    lessons: list[dict[str, Any]] = []
    verdicts = digest.get("verdicts", {})
    total_verdicts = sum(verdicts.values())

    if total_verdicts >= 2:
        applied = verdicts.get("applied", 0) + verdicts.get("thumb_up", 0)
        discarded = verdicts.get("discarded", 0) + verdicts.get("thumb_down", 0)
        rate = applied / max(1, total_verdicts)
        if rate >= 0.5 and applied >= 2:
            lessons.append({
                "lesson": (
                    f"Suggestions land well with {player_id} "
                    f"({applied} of {total_verdicts} applied) — keep offering similar builds."
                ),
                "tags": ["verdict-good"],
            })
        elif discarded >= 2:
            lessons.append({
                "lesson": (
                    f"{player_id} discards most suggestions ({discarded} of {total_verdicts}) — "
                    f"ask what they want before suggesting, and keep suggestions small."
                ),
                "tags": ["verdict-caution"],
            })

    applied_tiles = digest.get("applied_tiles", {})
    if applied_tiles:
        top_tile, top_n = next(iter(applied_tiles.items()))
        if top_n >= 2:
            lessons.append({
                "lesson": (
                    f"Lead with {top_tile} tiles for {player_id} — they applied "
                    f"{top_n} suggestions built around that type."
                ),
                "tags": [f"tile-{top_tile}", "preference"],
            })

    discarded_tiles = digest.get("discarded_tiles", {})
    if discarded_tiles:
        bad_tile, bad_n = next(iter(discarded_tiles.items()))
        if bad_n >= 2:
            lessons.append({
                "lesson": (
                    f"Avoid leading with {bad_tile} tiles for {player_id} — "
                    f"they discarded {bad_n} of those suggestions."
                ),
                "tags": [f"tile-{bad_tile}", "avoid"],
            })

    wired = digest.get("wired_tiles", {})
    if wired:
        own_tile, own_n = next(iter(wired.items()))
        if own_n >= 2:
            lessons.append({
                "lesson": (
                    f"{player_id} wires their own {own_tile} tiles often "
                    f"({own_n} times) — suggest ways to extend what they built, not replacements."
                ),
                "tags": [f"tile-{own_tile}", "builder-pattern"],
            })

    if not lessons and digest.get("event_count", 0) > 0:
        lessons.append({
            "lesson": (
                f"Early signal only ({digest['event_count']} events from {player_id}) — "
                f"no strong preference pattern yet; suggest simple, reversible builds."
            ),
            "tags": ["cold-start"],
        })

    for i, lesson in enumerate(lessons):
        lesson["source_streams"] = {
            "events": event_ids[:20],
            "event_count": digest.get("event_count", 0),
        }
    return lessons


# ─── LLM path ──────────────────────────────────────────────────

def llm_lessons(
    player_id: str,
    digest: dict[str, Any],
    http_post: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    """
    Ask GLM for lessons from the digest. Returns raw lesson dicts or None
    (any failure — caller falls back to heuristics).
    """
    post = http_post or _curl_post_json
    api_key = GLM_API_KEY or os.environ.get("GLM_API_KEY", "")
    if not api_key:
        return None

    user_msg = f"Player: {player_id}\nEvent digest:\n{json.dumps(digest, ensure_ascii=False)}"
    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": LLM_LESSON_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }
    try:
        result = post(
            GLM_API_URL,
            {"Authorization": f"Bearer {api_key}"},
            payload,
            timeout=30,
            retries=2,
        )
    except Exception:
        return None
    if "error" in result:
        return None
    choices = result.get("choices", [])
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    if not content:
        return None
    # Model may wrap the array in prose/fences — extract the first JSON array.
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        arr = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(arr, list):
        return None
    lessons = []
    for item in arr[:3]:
        if isinstance(item, dict) and isinstance(item.get("lesson"), str) and item["lesson"].strip():
            lessons.append({
                "lesson": item["lesson"].strip()[:400],
                "tags": [str(t)[:40] for t in (item.get("tags") or [])][:5],
            })
    return lessons or None


# ─── Entry point ───────────────────────────────────────────────

def _quality_for(text: str, digest: dict[str, Any]) -> dict[str, Any]:
    scores = score_response(text)
    composite = round(composite_score(scores), 3)
    n = max(1, digest.get("event_count", 1))
    # Coverage: heuristic floor — all events are reflected in the digest the
    # lesson came from; confidence scales with sample size (saturates at 20).
    confidence = round(min(1.0, n / 20), 3)
    quality = dict(scores)
    quality["composite"] = composite
    quality["coverage"] = 1.0
    quality["confidence"] = confidence
    return quality


def distill_player_lessons(
    player_id: str,
    events: list[dict[str, Any]],
    use_llm: bool | None = None,
    http_post: Callable[..., dict[str, Any]] | None = None,
    store: LessonStore | None = None,
) -> list[dict[str, Any]]:
    """
    Distill one player's events into structured lessons and persist them.

    use_llm: None (auto: TA_USE_LLM env + key present), True, or False.
    Returns the stored lesson records (possibly empty for no events).
    The amplifier NEVER writes scope='global' — two-tier law.
    """
    if use_llm is None:
        use_llm = os.environ.get("TA_USE_LLM", "0") == "1"
    store = store or LessonStore()

    events = [e for e in events if e.get("player_id") == player_id]
    if not events:
        return []

    digest = digest_events(events)
    event_ids = [e.get("id", "") for e in events]

    generator = "heuristic"
    raw = None
    if use_llm:
        raw = llm_lessons(player_id, digest, http_post=http_post)
        if raw is not None:
            generator = f"{GLM_MODEL}"
    if raw is None:
        raw = heuristic_lessons(player_id, digest, event_ids)
        generator = "heuristic"
    if raw is None:
        return []

    stored: list[dict[str, Any]] = []
    for item in raw:
        record = {
            "scope": "player",
            "player_id": player_id,
            "domain": "quilt-scratch",
            "lesson": item["lesson"],
            "quality": _quality_for(item["lesson"], digest),
            "tags": item.get("tags", []),
            "teaching_helped": None,
            "generator": generator,
            "source_streams": item.get(
                "source_streams",
                {"events": event_ids[:20], "event_count": digest.get("event_count", 0)},
            ),
        }
        stored.append(store.append(record))
    return stored
