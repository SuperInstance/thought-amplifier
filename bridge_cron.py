#!/usr/bin/env python3
"""
bridge_cron.py — the amplifier-side pull loop for quilt-scratch's ta-bridge.

PRODUCTION TOPOLOGY (the honest one, from quilt-scratch/docs/TA-BRIDGE.md):
the amplifier box (WSL today, maybe the boat box tomorrow) sits behind NAT.
Cloudflare's edge cannot reach it, so instead of the Worker forwarding events
to the amplifier, the amplifier cron PULLS pending events from the Worker
(outbound HTTPS only), distills them locally with the same events_distiller,
pushes lessons back via POST /lessons/ingest, and acks the event ids.

Crash-safety: a crash between pull and ack just means the next run re-pulls
the same events — ingest is idempotent by event id and the bridge text-dedupes
lessons, so re-pulls are always safe.

Usage (cron, e.g. every 5 min):
  TA_BRIDGE_URL=https://ta-bridge.<subdomain>.workers.dev \
  TA_BRIDGE_TOKEN=<INGEST_TOKEN> \
  python3 bridge_cron.py [--limit 200] [--dry-run]

Env:
  TA_BRIDGE_URL    the deployed ta-bridge Worker URL (required)
  TA_BRIDGE_TOKEN  the bridge's INGEST_TOKEN (required)
  TA_USE_LLM       1 to use GLM for distillation (default heuristic floor)
  TA_STORE_DIR     store dir override (same as serve.py)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from events_distiller import EventStore, distill_player_lessons  # noqa: E402
from lesson_store import LessonStore  # noqa: E402


def bridge(base_url: str, token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict | None]:
    """One HTTP call to the bridge. Returns (status, parsed-json-or-None)."""
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    # Cloudflare's managed WAF blocks the default Python-urllib UA — name ourselves.
    req.add_header("User-Agent", "thought-amplifier-bridge-cron/1.0")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, {"error": str(e)}


def run(limit: int = 200, dry_run: bool = False) -> int:
    base_url = os.environ.get("TA_BRIDGE_URL", "")
    token = os.environ.get("TA_BRIDGE_TOKEN", "")
    if not base_url or not token:
        print("ERROR: TA_BRIDGE_URL and TA_BRIDGE_TOKEN must be set.")
        return 1

    # 1. Health check (cheap, honest)
    status, health = bridge(base_url, token, "GET", "/health")
    if status != 200 or not (health or {}).get("ok"):
        print(f"bridge unhealthy: HTTP {status} {health}")
        return 1

    # 2. Pull pending events
    status, pulled = bridge(base_url, token, "GET", f"/admin/pending?limit={limit}")
    if status != 200 or pulled is None:
        print(f"pull failed: HTTP {status} {pulled}")
        return 1
    events = pulled.get("events", [])
    print(f"pulled {len(events)} pending events (bridge reported {pulled.get('pending')})")
    if not events:
        print("nothing to distill.")
        return 0

    if dry_run:
        players = sorted({e["player_id"] for e in events})
        print(f"[dry-run] would distill for players: {players}; not pushing, not acking.")
        return 0

    # 3. Distill locally (idempotent: our event store dedupes by id)
    event_store = EventStore()
    lesson_store = LessonStore()
    stored_events = event_store.extend(events)

    lessons_created: list[dict] = []
    for player_id in sorted({e["player_id"] for e in events}):
        lessons_created.extend(
            distill_player_lessons(player_id, event_store.all_for_player(player_id), store=lesson_store)
        )
    print(f"distilled {len(lessons_created)} lessons for {len(set(e['player_id'] for e in events))} players")

    # 4. Push lessons to the bridge (player tier + review queue only)
    pushed = 0
    if lessons_created:
        status, res = bridge(
            base_url, token, "POST", "/lessons/ingest", {"lessons": lessons_created}
        )
        if status != 200:
            print(f"lesson push failed: HTTP {status} {res} — events NOT acked, will re-pull")
            return 1
        pushed = (res or {}).get("stored", 0)
        print(f"pushed {pushed} lessons to the bridge")

    # 5. Ack the event ids (only after a successful push)
    ids = [e["id"] for e in events]
    status, res = bridge(base_url, token, "POST", "/admin/ack", {"ids": ids})
    if status != 200:
        print(f"ack failed: HTTP {status} {res} — events will re-pull (safe, idempotent)")
        return 1
    print(f"acked {(res or {}).get('acked', 0)} events. cycle complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="amplifier-side pull loop for ta-bridge")
    parser.add_argument("--limit", type=int, default=200, help="max events per pull (default 200)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
