#!/usr/bin/env python3
"""
modes/simulator.py — Thought Experiments

The simulator mode runs thought experiments: it takes a premise and
explores what would happen if it were true, tracing implications
forward until they reach a surprising conclusion or a contradiction.

Usage:
    simulator = Simulator(thinker, journal, api_keys...)
    simulator.simulate("What if humans could photosynthesize?")

The simulator explores multiple trajectories:
1. First-order consequences (immediate effects)
2. Second-order consequences (systemic effects)
3. Edge cases (what breaks the model?)
4. Historical parallels (when has something similar happened?)
5. The reductio (where does this lead if taken to the extreme?)
"""

from __future__ import annotations

import time
from typing import Any

from core.journal import Journal
from core.thinker import Thinker
from modes.common import llm_call


# ─── Simulation Trajectories ────────────────────────────────────

TRAJECTORIES = [
    {
        "name": "First-Order",
        "instruction": (
            "Trace the immediate, direct consequences of this premise. "
            "What changes right away? What becomes possible or impossible? "
            "Focus on concrete, specific effects — not abstractions."
        ),
    },
    {
        "name": "Second-Order",
        "instruction": (
            "Trace the systemic consequences — how does the world adapt? "
            "What new equilibria emerge? What institutions, norms, or "
            "practices would form around this reality?"
        ),
    },
    {
        "name": "Edge Cases",
        "instruction": (
            "Find the boundary conditions. Where does this premise break down? "
            "What's the weirdest, hardest, or most extreme case to handle? "
            "What paradoxes or contradictions emerge at the edges?"
        ),
    },
    {
        "name": "Historical Parallel",
        "instruction": (
            "Find a moment in history when something analogous to this premise "
            "was true (or nearly true). What happened? Does the historical "
            "parallel validate or undermine the premise?"
        ),
    },
    {
        "name": "Reductio",
        "instruction": (
            "Take this premise to its logical extreme. If we follow it "
            "as far as it goes, where do we end up? Is the destination "
            "surprising, absurd, illuminating, or terrifying?"
        ),
    },
    {
        "name": "Inversion",
        "instruction": (
            "Now consider the OPPOSITE of this premise. What if the "
            "opposite were true instead? Does exploring the opposite "
            "reveal something hidden about the original premise?"
        ),
    },
]


class Simulator:
    """Thought experiment mode: trace premises to their conclusions."""

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

    def simulate(self, premise: str, num_trajectories: int = 4) -> list[dict[str, Any]]:
        """Run a thought experiment on a premise.

        Args:
            premise: The hypothetical to explore
            num_trajectories: How many trajectories to trace

        Returns:
            List of journal entries created.
        """
        self.journal.write(
            "system",
            f"Simulator mode: exploring \"{premise}\"",
            {"mode": "simulator", "premise": premise},
        )

        selected = TRAJECTORIES[:num_trajectories]
        entries: list[dict[str, Any]] = []

        for i, traj in enumerate(selected):
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a brilliant thought experimenter in the tradition of "
                        "Galileo, Einstein, and Dennett. You explore ideas with rigor "
                        "and imagination. You follow implications wherever they lead."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Premise: {premise}\n\n"
                        f"{traj['instruction']}\n\n"
                        f"Be specific and rigorous. 4-6 sentences."
                    ),
                },
            ]

            result = llm_call(
                messages,
                api_key=self.api_key,
                deepseek_api_key=self.deepseek_api_key,
                model=self.glm_model,
                deepseek_model=self.deepseek_model,
                temperature=0.7,
                max_tokens=350,
            )

            entry = self.journal.write(
                "mode_output",
                f"**{traj['name']}:** {result}",
                {
                    "mode": "simulator",
                    "premise": premise,
                    "trajectory": traj["name"],
                    "trajectory_index": i + 1,
                },
            )
            entries.append(entry)

            if i < len(selected) - 1:
                time.sleep(1)

        # Meta-synthesis: what did we learn?
        results_summary = "\n".join(
            f"- [{e['metadata'].get('trajectory', '?')}]: {e['content'][:150]}"
            for e in entries
        )

        messages = [
            {
                "role": "system",
                "content": "You extract insight from thought experiments.",
            },
            {
                "role": "user",
                "content": (
                    f"You ran a thought experiment on: \"{premise}\"\n\n"
                    f"Trajectories explored:\n{results_summary}\n\n"
                    f"What is the most important insight from this experiment? "
                    f"What did exploring this premise teach us about reality? "
                    f"2-3 sentences."
                ),
            },
        ]

        insight = llm_call(
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
            f"**Experiment Conclusion:** {insight}",
            {"mode": "simulator", "premise": premise, "conclusion": True},
        )
        entries.append(entry)

        return entries
