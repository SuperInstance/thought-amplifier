#!/usr/bin/env python3
"""
modes/mirror.py — Creative reflection

The mirror mode takes a theme and refracts it through a fixed set of creative
lenses (metaphor, story, poetry, paradox, inversion, scale), then adds a
synthesis of what unifies the reflections. Each reflection and the synthesis
are written to the journal.

Usage:
    mirror = Mirror(thinker, journal, api_keys...)
    mirror.reflect("The way rivers reshape landscapes over millennia")

Single-shot: one `amplifier.py --mode mirror` run produces a bounded batch of
journal entries and returns. It is not part of the continuous thinking loop.
"""

from __future__ import annotations

import time
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import llm_call


# ─── Reflection Styles ──────────────────────────────────────────

REFLECTION_STYLES = [
    {
        "name": "metaphor",
        "instruction": (
            "Create a vivid, unexpected metaphor for this idea. "
            "The metaphor should reveal something non-obvious about the idea. "
            "Find the connection between this idea and something from a completely "
            "different domain (biology, music, architecture, cooking, etc.)."
        ),
    },
    {
        "name": "story",
        "instruction": (
            "Write a 3-sentence story fragment that embodies this idea. "
            "Make it concrete and specific — real characters, real actions, "
            "real stakes. The idea should be felt, not stated."
        ),
    },
    {
        "name": "poetry",
        "instruction": (
            "Write a short poem (4-6 lines) that captures the essence of this idea. "
            "Use concrete imagery, not abstractions. The poem should make the "
            "idea feel new."
        ),
    },
    {
        "name": "paradox",
        "instruction": (
            "Find the paradox hidden inside this idea. What about it is "
            "self-contradictory, circular, or impossible to fully resolve? "
            "State the paradox precisely and beautifully."
        ),
    },
    {
        "name": "inversion",
        "instruction": (
            "Invert this idea — turn it upside down. What would the world "
            "look like if this idea were false, reversed, or backward? "
            "What does the inversion reveal about the original?"
        ),
    },
    {
        "name": "scale",
        "instruction": (
            "Explore this idea at a completely different scale — either "
            "vastly larger (cosmic, civilizational) or vastly smaller "
            "(microscopic, momentary). How does the idea change when "
            "you zoom in or out?"
        ),
    },
]


class Mirror:
    """Creative reflection mode: refract ideas through artistic lenses."""

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

    def reflect(self, theme: str, num_reflections: int = 4,
                styles: list[str] | None = None) -> list[dict[str, Any]]:
        """Generate creative reflections of a theme.

        Args:
            theme: The idea or thought to reflect
            num_reflections: How many different reflections to generate
            styles: Optional list of style names to use (default: all)

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Mirror mode: reflecting \"{theme}\"",
            {"mode": "mirror", "theme": theme},
        )

        if styles:
            selected = [s for s in REFLECTION_STYLES if s["name"] in styles]
        else:
            selected = REFLECTION_STYLES[:num_reflections]

        entries: list[dict[str, Any]] = []

        for i, style in enumerate(selected):
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a brilliant creative writer who illuminates ideas "
                        "through art. Be vivid, specific, and surprising. Never cliché."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Idea to reflect: \"{theme}\"\n\n"
                        f"{style['instruction']}"
                    ),
                },
            ]

            reflection = llm_call(
                messages,
                api_key=self.api_key,
                deepseek_api_key=self.deepseek_api_key,
                model=self.glm_model,
                deepseek_model=self.deepseek_model,
                temperature=1.0,
                max_tokens=250,
            )

            entry = self.journal.write(
                "mode_output",
                f"**{style['name'].title()}:** {reflection}",
                {
                    "mode": "mirror",
                    "theme": theme,
                    "style": style["name"],
                    "reflection_index": i + 1,
                },
            )
            entries.append(entry)

            if i < len(selected) - 1:
                time.sleep(1)

        # Synthesis: what unifies these reflections?
        if len(entries) >= 2:
            reflections_text = "\n".join(
                f"- [{e['metadata'].get('style', '?')}]: {e['content'][:150]}"
                for e in entries
            )

            messages = [
                {
                    "role": "system",
                    "content": "You find the hidden unity in diverse creative expressions.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Here are {len(entries)} creative reflections on \"{theme}\":\n\n"
                        f"{reflections_text}\n\n"
                        f"What hidden unity connects these reflections? What is the "
                        f"essence that all these facets reveal? 2-3 sentences."
                    ),
                },
            ]

            synthesis = llm_call(
                messages,
                api_key=self.api_key,
                deepseek_api_key=self.deepseek_api_key,
                model=self.glm_model,
                deepseek_model=self.deepseek_model,
                temperature=0.6,
                max_tokens=200,
            )

            entry = self.journal.write(
                "mode_output",
                f"**Essence:** {synthesis}",
                {"mode": "mirror", "theme": theme, "synthesis": True},
            )
            entries.append(entry)

        return entries
