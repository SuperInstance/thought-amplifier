#!/usr/bin/env python3
"""
modes/reporter.py — URL research

The reporter mode fetches a URL once, injects the extracted text as context,
and generates a bounded batch of analytical thoughts about it from a fixed
set of angles, followed by a synthesis. Each thought and the synthesis are
written to the journal.

Usage:
    reporter = Reporter(thinker, journal, api_keys...)
    reporter.research("https://example.com/article", num_thoughts=5)

Single-shot: one `amplifier.py --mode reporter` run does one fetch, emits its
entries, and returns. It is not the continuous thinking loop and does not
re-fetch or poll.
"""

from __future__ import annotations

import time
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import fetch_markdown, llm_call


class Reporter:
    """Research mode: fetch URLs, generate analytical thoughts about them."""

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

    def research(self, url: str, num_thoughts: int = 5) -> list[dict[str, Any]]:
        """Research a URL: fetch content, generate analytical thoughts.

        Args:
            url: The URL to research
            num_thoughts: How many research thoughts to generate

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Reporter mode: researching {url}",
            {"mode": "reporter", "url": url},
        )

        content = fetch_markdown(url, max_chars=8000)

        if content.startswith("[Fetch error"):
            self.journal.write(
                "mode_output",
                f"Failed to fetch {url}: {content}",
                {"mode": "reporter", "url": url, "error": True},
            )
            return []

        self.journal.write(
            "mode_output",
            f"**Source:** {url}\n\n**Content excerpt:**\n{content[:500]}...",
            {"mode": "reporter", "url": url, "content_length": len(content)},
        )

        entries: list[dict[str, Any]] = []

        analysis_angles = [
            "What are the key claims or findings in this source?",
            "What assumptions does this source make that might be questioned?",
            "How does this connect to broader themes or other fields?",
            "What would someone who disagrees say about this?",
            "What are the practical implications or applications?",
            "What's missing from this source — what questions does it leave unanswered?",
        ]

        for i in range(min(num_thoughts, len(analysis_angles))):
            angle = analysis_angles[i]

            prompt = (
                f"You are a research analyst. You just read this content:\n\n"
                f"{content[:4000]}\n\n"
                f"Now address this angle: {angle}\n"
                f"Be specific, cite details from the source. 3-5 sentences."
            )

            messages = [
                {"role": "system", "content": "You are a sharp research analyst who finds insights others miss."},
                {"role": "user", "content": prompt},
            ]

            thought = llm_call(
                messages,
                api_key=self.api_key,
                deepseek_api_key=self.deepseek_api_key,
                model=self.glm_model,
                deepseek_model=self.deepseek_model,
                temperature=0.6,
                max_tokens=300,
            )

            entry = self.journal.write(
                "mode_output",
                f"**[{i+1}/{num_thoughts}] {angle}**\n\n{thought}",
                {
                    "mode": "reporter",
                    "url": url,
                    "angle": angle,
                    "thought_index": i + 1,
                    "total_thoughts": num_thoughts,
                },
            )
            entries.append(entry)

            if i < num_thoughts - 1:
                time.sleep(1)

        summary_prompt = (
            f"You analyzed this source in {num_thoughts} different ways.\n\n"
            f"Source: {url}\n"
            f"Content excerpt: {content[:1000]}\n\n"
            f"Synthesize your analysis into one key insight (2-3 sentences)."
        )

        messages = [
            {"role": "system", "content": "You synthesize research into crystalline insights."},
            {"role": "user", "content": summary_prompt},
        ]

        summary = llm_call(
            messages,
            api_key=self.api_key,
            deepseek_api_key=self.deepseek_api_key,
            model=self.glm_model,
            deepseek_model=self.deepseek_model,
            temperature=0.5,
            max_tokens=200,
        )

        entry = self.journal.write(
            "mode_output",
            f"**Research Synthesis:** {summary}",
            {"mode": "reporter", "url": url, "synthesis": True},
        )
        entries.append(entry)

        return entries
