#!/usr/bin/env python3
"""
core/journal.py — JSONL + Markdown Journal Writer

Every thought, supervisor directive, and mode output is logged in two formats:
1. JSONL (machine-readable, append-only, one JSON object per line)
2. Markdown (human-readable, organized by session)

The journal is the system's memory. The supervisor reads it to assess
thought quality. Modes read it for context. The viewer streams from it.

Design: pure stdlib, no external dependencies.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─── Journal Entry Types ────────────────────────────────────────

ENTRY_TYPES = {
    "thought": "A generated thought from the thinker",
    "directive": "A supervisor directive modifying the thought conditions",
    "mode_output": "Output from a specialized mode (reporter, advocate, etc.)",
    "system": "System event (startup, shutdown, mode change, error)",
    "intervention": "Human intervention via viewer or CLI",
    "summary": "Periodic summary of recent thoughts",
}


# ─── Journal Writer ─────────────────────────────────────────────

class Journal:
    """Dual-format journal: JSONL for machines, Markdown for humans."""

    def __init__(self, journal_dir: str | Path = "journals") -> None:
        self.dir = Path(journal_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.jsonl_path = self.dir / f"session_{self.session_id}.jsonl"
        self.md_path = self.dir / f"session_{self.session_id}.md"
        self._md_initialized = False

    def write(self, entry_type: str, content: str | dict[str, Any],
              metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Write a journal entry to both JSONL and Markdown.

        Args:
            entry_type: One of ENTRY_TYPES
            content: The thought text or structured data
            metadata: Additional context (mode, prompt_version, quality, etc.)

        Returns:
            The complete entry dict that was written.
        """
        timestamp = datetime.now(timezone.utc)
        entry = {
            "id": f"{timestamp.strftime('%H%M%S%f')}",
            "timestamp": timestamp.isoformat(),
            "type": entry_type,
            "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            "metadata": metadata or {},
            "session": self.session_id,
        }

        # Append to JSONL
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Append to Markdown
        self._write_markdown(entry)

        return entry

    def _write_markdown(self, entry: dict[str, Any]) -> None:
        """Write an entry to the markdown journal."""
        if not self._md_initialized:
            self._init_markdown()
            self._md_initialized = True

        ts = entry["timestamp"][11:19]  # HH:MM:SS
        etype = entry["type"]
        content = entry["content"]
        meta = entry.get("metadata", {})

        with open(self.md_path, "a", encoding="utf-8") as f:
            if etype == "thought":
                quality_str = f" (q={meta.get('quality', '?')})" if "quality" in meta else ""
                f.write(f"\n### [{ts}] Thought{quality_str}\n\n{content}\n")
            elif etype == "directive":
                f.write(f"\n### [{ts}] 🎯 Directive\n\n> {content}\n")
                if meta:
                    for k, v in meta.items():
                        f.write(f"> **{k}**: {v}\n")
                f.write("\n")
            elif etype == "mode_output":
                mode = meta.get("mode", "unknown")
                f.write(f"\n### [{ts}] 📋 {mode.title()} Output\n\n{content}\n")
            elif etype == "system":
                f.write(f"\n### [{ts}] ⚙️ System\n\n{content}\n")
            elif etype == "intervention":
                f.write(f"\n### [{ts}] 👤 Intervention\n\n{content}\n")
            elif etype == "summary":
                f.write(f"\n### [{ts}] 📊 Summary\n\n{content}\n")
            else:
                f.write(f"\n### [{ts}] {etype.title()}\n\n{content}\n")

    def _init_markdown(self) -> None:
        """Write the markdown header."""
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(f"# Thought Stream — Session {self.session_id}\n\n")
            f.write(f"**Started:** {datetime.now(timezone.utc).isoformat()}\n\n")
            f.write("---\n")

    # ─── Reading ────────────────────────────────────────────────

    def read_entries(self, limit: int = 100, entry_type: str | None = None) -> list[dict[str, Any]]:
        """Read entries from the current session's JSONL file.

        Args:
            limit: Maximum entries to return (most recent)
            entry_type: Filter by type (None = all)

        Returns:
            List of entry dicts, most recent first.
        """
        if not self.jsonl_path.exists():
            return []

        entries: list[dict[str, Any]] = []
        try:
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry_type is None or entry.get("type") == entry_type:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        entries.reverse()  # Most recent first
        return entries[:limit]

    def read_thoughts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Shortcut to read only thought entries."""
        return self.read_entries(limit=limit, entry_type="thought")

    def read_directives(self, limit: int = 20) -> list[dict[str, Any]]:
        """Shortcut to read only directive entries."""
        return self.read_entries(limit=limit, entry_type="directive")

    @staticmethod
    def read_all_sessions(journal_dir: str | Path = "journals", limit: int = 200) -> list[dict[str, Any]]:
        """Read entries across all session files."""
        jdir = Path(journal_dir)
        if not jdir.exists():
            return []

        files = sorted(jdir.glob("session_*.jsonl"))
        entries: list[dict[str, Any]] = []

        for f in reversed(files):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except OSError:
                continue
            if len(entries) >= limit:
                break

        return entries[:limit]

    @staticmethod
    def get_latest_session(journal_dir: str | Path = "journals") -> Path | None:
        """Get the path to the most recent session JSONL file."""
        jdir = Path(journal_dir)
        if not jdir.exists():
            return None
        files = sorted(jdir.glob("session_*.jsonl"))
        return files[-1] if files else None
