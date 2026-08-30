#!/usr/bin/env python3
"""
modes/connector.py — Multi-document pattern finding

The connector mode takes two or more sources (URLs or literal text strings),
fetches any URLs once, and runs a fixed multi-layer analysis across all of
them, writing each layer to the journal:
1. Surface patterns (shared vocabulary, themes)
2. Structural patterns (similar arguments, parallel logic)
3. Hidden connections (one idea resolves a tension in another)
4. Contradictions (where the sources conflict)
5. Synthesis (what emerges when you hold them together)

Usage:
    connector = Connector(thinker, journal, api_keys...)
    connector.connect([
        "https://example.com/article1",
        "https://example.com/article2",
        "Some pasted text about a third topic",
    ])

Single-shot: one `amplifier.py --mode connector` run produces a bounded batch
of journal entries and returns. It is not part of the continuous thinking loop.
"""

from __future__ import annotations

import time
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import fetch_markdown, llm_call


class Connector:
    """Multi-document pattern finding mode."""

    def __init__(self, thinker: Thinker, journal: Journal,
                 api_key: str = "", deepseek_api_key: str = "",
                 glm_model: str = "glm-4-flash",
                 deepseek_model: str = "deepseek-chat") -> None:
        self.thinker = thinker
        self.journal = journal
        self.api_key = api_key
        self.deepseek_api_key = deepseek_api_key
        self.glm_model = glm_model
        self.deepseek_model = deepseek_model

    def _get_content(self, source: str) -> str:
        """Get text content from a URL or use the string directly."""
        if source.startswith("http"):
            content = fetch_markdown(source, max_chars=4000)
            if not content.startswith("[Fetch error"):
                return content
            return source  # Fall back to using the URL string itself
        return source

    def connect(self, sources: list[str]) -> list[dict[str, Any]]:
        """Find patterns and connections between multiple sources.

        Args:
            sources: List of URLs or text strings to connect

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Connector mode: analyzing {len(sources)} sources",
            {"mode": "connector", "num_sources": len(sources), "sources": sources},
        )

        contents: list[tuple[str, str]] = []  # (source_label, content)
        for i, source in enumerate(sources):
            content = self._get_content(source)
            label = source[:80] + "..." if len(source) > 80 else source
            contents.append((label, content[:3000]))

            self.journal.write(
                "mode_output",
                f"**Source {i+1}:** {label}\n\nContent excerpt:\n{content[:300]}...",
                {"mode": "connector", "source_index": i + 1, "source": label},
            )

        if len(contents) < 2:
            self.journal.write(
                "mode_output",
                "Connector needs at least 2 sources to find patterns.",
                {"mode": "connector", "error": True},
            )
            return []

        entries: list[dict[str, Any]] = []

        entries.append(self._analyze_layer(
            contents,
            "Surface Patterns",
            "Find shared vocabulary, recurring themes, and common motifs across these sources. "
            "What words, concepts, or images appear in multiple texts?",
            "surface",
        ))
        time.sleep(1)

        entries.append(self._analyze_layer(
            contents,
            "Structural Patterns",
            "Find structural similarities: parallel arguments, similar reasoning patterns, "
            "analogous logic. Do these sources make their points in similar ways?",
            "structural",
        ))
        time.sleep(1)

        entries.append(self._analyze_layer(
            contents,
            "Hidden Connections",
            "Find connections that aren't obvious when reading separately. "
            "Does an idea in one source resolve a tension or answer a question in another? "
            "This is where the most valuable insights live.",
            "hidden",
        ))
        time.sleep(1)

        entries.append(self._analyze_layer(
            contents,
            "Contradictions",
            "Find where these sources conflict, contradict, or create tension. "
            "Where do they disagree? What can't both be true simultaneously?",
            "contradictions",
        ))
        time.sleep(1)

        # Layer 5: synthesis across all sources at once
        all_content = "\n\n---\n\n".join(
            f"[Source {i+1}]: {label}\n{content[:2000]}"
            for i, (label, content) in enumerate(contents)
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a master synthesizer. You hold multiple texts in mind "
                    "simultaneously and find what emerges from their interaction — "
                    "insights that belong to none of them individually."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Sources:\n\n{all_content}\n\n"
                    f"What emerges when you hold all {len(contents)} sources together? "
                    f"What is the meta-pattern — the insight that only becomes visible "
                    f"when these texts interact? Be specific and surprising. 3-5 sentences."
                ),
            },
        ]

        synthesis = llm_call(
            messages,
            api_key=self.api_key,
            deepseek_api_key=self.deepseek_api_key,
            model=self.glm_model,
            deepseek_model=self.deepseek_model,
            temperature=0.7,
            max_tokens=300,
        )

        entry = self.journal.write(
            "mode_output",
            f"**Synthesis:** {synthesis}",
            {"mode": "connector", "synthesis": True, "num_sources": len(contents)},
        )
        entries.append(entry)

        return entries

    def _analyze_layer(self, contents: list[tuple[str, str]],
                       layer_name: str, instruction: str,
                       layer_id: str) -> dict[str, Any]:
        """Analyze one layer of connection between sources."""
        all_content = "\n\n---\n\n".join(
            f"[Source {i+1}]: {label}\n{content[:2000]}"
            for i, (label, content) in enumerate(contents)
        )

        messages = [
            {
                "role": "system",
                "content": "You are a pattern-finder who sees what others miss between texts.",
            },
            {
                "role": "user",
                "content": f"{instruction}\n\nSources:\n\n{all_content}",
            },
        ]

        analysis = llm_call(
            messages,
            api_key=self.api_key,
            deepseek_api_key=self.deepseek_api_key,
            model=self.glm_model,
            deepseek_model=self.deepseek_model,
            temperature=0.6,
            max_tokens=300,
        )

        return self.journal.write(
            "mode_output",
            f"**{layer_name}:** {analysis}",
            {"mode": "connector", "layer": layer_id, "layer_name": layer_name},
        )
