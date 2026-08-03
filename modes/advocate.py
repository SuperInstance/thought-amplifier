#!/usr/bin/env python3
"""
modes/advocate.py — Devil's Advocate Counter-Arguments

The advocate mode takes a claim or position and generates the strongest
possible counter-arguments. It's a steel-man machine: it doesn't attack
strawmen, it builds the best possible opposition.

Usage:
    advocate = Advocate(thinker, journal, api_keys...)
    advocate.argue("Free trade always benefits both countries")

The advocate generates multiple independent counter-arguments, rates
their strength, and then identifies the meta-pattern: what kind of
position is this claim most vulnerable to?
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import llm_call


class Advocate:
    """Devil's advocate mode: generate strong counter-arguments."""

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

    def argue(self, claim: str, num_arguments: int = 4) -> list[dict[str, Any]]:
        """Generate counter-arguments against a claim.

        Args:
            claim: The position to argue against
            num_arguments: How many distinct counter-arguments to generate

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Advocate mode: arguing against \"{claim}\"",
            {"mode": "advocate", "claim": claim},
        )

        # Strategy types for diverse arguments
        strategies = [
            ("empirical", "Challenge the factual basis. What evidence contradicts or complicates this claim?"),
            ("logical", "Challenge the reasoning. What logical fallacies or gaps exist in the argument?"),
            ("practical", "Challenge the real-world consequences. What happens if we act on this claim?"),
            ("moral", "Challenge the values. What ethical concerns does this position raise?"),
            ("historical", "Challenge from history. When has this been tried before and what happened?"),
            ("systemic", "Challenge the framing. What does this claim assume about how the world works?"),
        ]

        entries: list[dict[str, Any]] = []

        for i in range(min(num_arguments, len(strategies))):
            strategy_name, strategy_desc = strategies[i]

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a brilliant devil's advocate. You steel-man arguments: "
                        "you build the STRONGEST possible counter-argument, not a strawman. "
                        "You are fair, precise, and devastating. Respond in 4-6 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Claim to argue against: \"{claim}\"\n\n"
                        f"Your approach: {strategy_desc}\n\n"
                        f"Build the strongest counter-argument from this angle."
                    ),
                },
            ]

            argument = llm_call(
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
                f"**Counter-argument [{strategy_name}]:**\n\n{argument}",
                {
                    "mode": "advocate",
                    "claim": claim,
                    "strategy": strategy_name,
                    "argument_index": i + 1,
                },
            )
            entries.append(entry)

            if i < num_arguments - 1:
                time.sleep(1)

        # Meta-analysis: what is this claim most vulnerable to?
        meta_prompt = (
            f"You generated {num_arguments} counter-arguments against this claim:\n"
            f"\"{claim}\"\n\n"
            f"The strategies used were: {', '.join(s[0] for s in strategies[:num_arguments])}.\n\n"
            f"Which type of counter-argument is this claim MOST vulnerable to, and why? "
            f"What does this reveal about the claim's fundamental weakness? 2-3 sentences."
        )

        messages = [
            {"role": "system", "content": "You identify the structural weakness in arguments."},
            {"role": "user", "content": meta_prompt},
        ]

        meta = llm_call(
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
            f"**Vulnerability Analysis:** {meta}",
            {"mode": "advocate", "claim": claim, "meta_analysis": True},
        )
        entries.append(entry)

        return entries
