#!/usr/bin/env python3
"""
modes/watcher.py — URL Monitoring + Change Detection

The watcher mode periodically fetches a URL, compares it to the previous
version, and generates a thought about what changed. It's a sentry that
never sleeps — pointed at a page, it notices everything.

Usage:
    watcher = Watcher(thinker, journal, api_keys...)
    watcher.watch("https://news.ycombinator.com", interval=60, max_checks=5)

The watcher stores snapshots in journals/watcher_snapshots/ and uses
content hashing to detect changes. When something changes, it generates
an analytical thought about the difference.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import fetch_markdown, content_hash, llm_call


class Watcher:
    """URL monitoring mode: detect changes and analyze them."""

    def __init__(self, thinker: Thinker, journal: Journal,
                 api_key: str = "", deepseek_api_key: str = "",
                 glm_model: str = "glm-4-flash",
                 deepseek_model: str = "deepseek-chat",
                 snapshot_dir: str = "journals/watcher_snapshots") -> None:
        self.thinker = thinker
        self.journal = journal
        self.api_key = api_key
        self.deepseek_api_key = deepseek_api_key
        self.glm_model = glm_model
        self.deepseek_model = deepseek_model
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, url: str, check_num: int) -> Path:
        """Get the snapshot file path for a URL and check number."""
        # Create a safe filename from URL
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return self.snapshot_dir / f"{url_hash}_check_{check_num}.txt"

    def _load_snapshot(self, path: Path) -> str | None:
        """Load a previous snapshot."""
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def _save_snapshot(self, path: Path, content: str) -> None:
        """Save a snapshot."""
        path.write_text(content, encoding="utf-8")

    def _diff_analysis(self, old: str, new: str) -> str:
        """Generate a simple diff summary between two text versions."""
        old_lines = set(old.strip().split("\n"))
        new_lines = set(new.strip().split("\n"))

        added = new_lines - old_lines
        removed = old_lines - new_lines

        parts = []
        if added:
            parts.append(f"Added ({len(added)} lines):\n" + "\n".join(list(added)[:10]))
        if removed:
            parts.append(f"Removed ({len(removed)} lines):\n" + "\n".join(list(removed)[:10]))

        if not parts:
            return "No textual changes detected (content may have been reformatted)."

        return "\n\n".join(parts)

    def watch(self, url: str, interval: float = 60.0,
              max_checks: int = 5) -> list[dict[str, Any]]:
        """Watch a URL for changes, generating thoughts when content changes.

        Args:
            url: URL to monitor
            interval: Seconds between checks
            max_checks: Maximum number of checks before stopping

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Watcher mode: monitoring {url} (interval={interval}s, max_checks={max_checks})",
            {"mode": "watcher", "url": url, "interval": interval, "max_checks": max_checks},
        )

        entries: list[dict[str, Any]] = []
        previous_content: str | None = None
        previous_hash: str | None = None

        for check_num in range(1, max_checks + 1):
            timestamp = datetime.now(timezone.utc).isoformat()

            # Fetch current content
            content = fetch_markdown(url, max_chars=5000)
            current_hash = content_hash(content)

            if content.startswith("[Fetch error"):
                self.journal.write(
                    "mode_output",
                    f"Check #{check_num}: Fetch failed — {content[:200]}",
                    {"mode": "watcher", "url": url, "check": check_num, "error": True},
                )
            elif previous_hash is None:
                # First check — baseline
                self._save_snapshot(self._snapshot_path(url, check_num), content)
                entry = self.journal.write(
                    "mode_output",
                    f"**Check #{check_num}:** Baseline established. Content hash: {current_hash}.\n\n"
                    f"First 200 chars: {content[:200]}...",
                    {
                        "mode": "watcher", "url": url, "check": check_num,
                        "hash": current_hash, "baseline": True,
                    },
                )
                entries.append(entry)
                previous_content = content
                previous_hash = current_hash

            elif current_hash != previous_hash:
                # Change detected!
                diff = self._diff_analysis(previous_content, content)
                self._save_snapshot(self._snapshot_path(url, check_num), content)

                # Generate analysis of the change
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a change analyst. You notice what's different, "
                            "interpret what it means, and explain why it matters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"URL: {url}\n\n"
                            f"Changes detected:\n{diff[:2000]}\n\n"
                            f"What changed and why might it matter? 3-4 sentences."
                        ),
                    },
                ]

                analysis = llm_call(
                    messages,
                    api_key=self.api_key,
                    deepseek_api_key=self.deepseek_api_key,
                    model=self.glm_model,
                    deepseek_model=self.deepseek_model,
                    temperature=0.5,
                    max_tokens=300,
                )

                entry = self.journal.write(
                    "mode_output",
                    f"**🔔 Change detected at check #{check_num}**\n\n"
                    f"**Diff:**\n{diff[:500]}\n\n"
                    f"**Analysis:** {analysis}",
                    {
                        "mode": "watcher", "url": url, "check": check_num,
                        "old_hash": previous_hash, "new_hash": current_hash,
                        "changed": True,
                    },
                )
                entries.append(entry)

                previous_content = content
                previous_hash = current_hash

            else:
                # No change
                entry = self.journal.write(
                    "mode_output",
                    f"**Check #{check_num}:** No changes detected. Hash: {current_hash}",
                    {
                        "mode": "watcher", "url": url, "check": check_num,
                        "hash": current_hash, "changed": False,
                    },
                )
                entries.append(entry)

            # Wait for next interval (except on last check)
            if check_num < max_checks:
                waited = 0.0
                while waited < interval:
                    time.sleep(0.5)
                    waited += 0.5

        return entries
