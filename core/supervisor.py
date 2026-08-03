#!/usr/bin/env python3
"""
core/supervisor.py — The Thought Supervisor

The supervisor reads the stream of thoughts and sends directives that shape
what future thoughts look like. It modifies:
- The system prompt (what role/persona the thinker adopts)
- Temperature (creativity vs focus)
- Context injection (what background the thinker sees)
- Interval (how fast thoughts come)

The supervisor runs on a slower cycle than the thinker. While the thinker
generates a thought every ~5 seconds, the supervisor reviews the window
of recent thoughts every ~30 seconds and decides if adjustments are needed.

From REPO_DESIGN.md §5.3 — Trust Scoring:
- Asymmetric trust: +0.5 success, -2.0 failure (minimum 10 observations)
- Novelty-bias control via sham interventions
- Rollback after 3 consecutive quality decreases
- Self-model: which modifications work in which contexts

The supervisor is intentionally conservative. A bad modification is worse
than no modification — the system should think differently, not brokenly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from core.journal import Journal
from core.thinker import ThinkerConfig, Thinker, _curl_post_json


# ─── Quality Assessment ─────────────────────────────────────────

@dataclass
class QualityScore:
    """Multi-dimensional quality assessment of a thought."""
    novelty: float = 0.5       # How different from recent thoughts
    specificity: float = 0.5   # How specific vs generic
    coherence: float = 0.5     # Does it make logical sense
    engagement: float = 0.5    # Is it interesting
    overall: float = 0.5       # Weighted mean

    @classmethod
    def compute(cls, thought: str, recent_thoughts: list[str]) -> "QualityScore":
        """Heuristic quality scoring without an LLM call.

        This is the Gate-1 quality check — cheap, fast, approximate.
        The supervisor's LLM call (Gate-3) can refine this if needed.
        """
        words = thought.split()
        word_count = len(words)

        # Novelty: word overlap with recent thoughts (lower = more novel)
        if recent_thoughts:
            recent_words = set()
            for rt in recent_thoughts[-10:]:
                recent_words.update(rt.lower().split())
            thought_words = set(thought.lower().split())
            if thought_words:
                overlap = len(thought_words & recent_words) / len(thought_words)
                novelty = max(0.0, min(1.0, 1.0 - overlap))
            else:
                novelty = 0.5
        else:
            novelty = 0.8  # First thoughts are always novel

        # Specificity: longer, more detailed thoughts score higher
        # But not too long — concise specificity is best
        if word_count < 5:
            specificity = 0.2
        elif word_count <= 30:
            specificity = min(1.0, word_count / 30.0)
        else:
            specificity = max(0.5, 1.0 - (word_count - 30) / 100.0)

        # Coherence: check for basic sentence structure
        sentences = re.split(r'[.!?]+', thought)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences and len(sentences) >= 1:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            coherence = min(1.0, avg_len / 10.0) if avg_len > 0 else 0.3
        else:
            coherence = 0.3

        # Engagement: presence of questions, connections, surprises
        engagement_boost = 0.0
        if "?" in thought:
            engagement_boost += 0.1
        if any(w in thought.lower() for w in ["but", "however", "surprising", "unexpected", "imagine"]):
            engagement_boost += 0.15
        if any(w in thought.lower() for w in ["because", "therefore", "so that", "means"]):
            engagement_boost += 0.1
        engagement = min(1.0, 0.4 + engagement_boost)

        # Overall weighted mean
        overall = (novelty * 0.3 + specificity * 0.25 + coherence * 0.2 + engagement * 0.25)

        return cls(novelty=novelty, specificity=specificity, coherence=coherence,
                   engagement=engagement, overall=overall)


# ─── Directive Types ────────────────────────────────────────────

@dataclass
class Directive:
    """A supervisor directive that modifies the thought conditions."""
    kind: str  # "prompt" | "temperature" | "context" | "interval"
    description: str  # Human-readable description
    changes: dict[str, Any]  # The actual changes to apply

    def apply(self, config: ThinkerConfig) -> None:
        """Apply this directive to a thinker config."""
        if self.kind == "prompt":
            config.system_prompt = self.changes.get("system_prompt", config.system_prompt)
        elif self.kind == "temperature":
            config.temperature = self.changes.get("temperature", config.temperature)
        elif self.kind == "context":
            config.context = self.changes.get("context", config.context)
        elif self.kind == "interval":
            config.interval = self.changes.get("interval", config.interval)


# ─── Prompt Library ─────────────────────────────────────────────

PROMPT_VARIATIONS: dict[str, str] = {
    "default": (
        "You are a stream of consciousness. Generate one interesting, specific "
        "thought right now. Be concise (2-4 sentences). Be original — don't "
        "repeat ideas. Connect concepts in surprising ways."
    ),
    "analytical": (
        "You are an analytical mind probing the deep structure of reality. "
        "Generate one insight that reveals hidden connections or underlying "
        "patterns. Be precise, specific, and surprising. 2-4 sentences."
    ),
    "creative": (
        "You are a fountain of creative ideas. Generate one wildly original "
        "thought — a metaphor, a what-if, an invention, a perspective shift. "
        "Be vivid and specific. 2-4 sentences."
    ),
    "philosophical": (
        "You are a philosopher questioning assumptions. Generate one deep "
        "question or insight about existence, knowledge, consciousness, or "
        "value. Be rigorous but accessible. 2-4 sentences."
    ),
    "scientific": (
        "You are a scientific mind exploring how the universe works. Generate "
        "one hypothesis, observation, or connection between phenomena. Be "
        "specific and grounded. 2-4 sentences."
    ),
    "playful": (
        "You are a playful mind finding joy and humor in ideas. Generate one "
        "funny, clever, or delightful thought. Wordplay, absurdity, and "
        "unexpected connections welcome. 2-4 sentences."
    ),
    "investigative": (
        "You are an investigator following threads of curiosity. Generate one "
        "sharp question or line of inquiry that opens new territory. Be "
        "specific about what you want to know and why. 2-4 sentences."
    ),
}


# ─── The Supervisor ─────────────────────────────────────────────

class Supervisor:
    """Reads thoughts, assesses quality, and sends directives.

    The supervisor runs on a slower cycle than the thinker. Every
    `review_interval` seconds, it reviews the recent thought window,
    computes quality trends, and decides whether to adjust the prompt,
    temperature, context, or interval.

    Trust model (from REPO_DESIGN.md):
    - Track quality before and after each directive
    - Asymmetric: +0.5 on improvement, -2.0 on decline
    - Minimum 10 observations before trust moves
    - 3 consecutive quality decreases → rollback
    """

    def __init__(self, thinker: Thinker, journal: Journal,
                 review_interval: float = 30.0,
                 api_key: str = "",
                 glm_api_url: str = "https://api.z.ai/api/paas/v4/chat/completions",
                 glm_model: str = "glm-4-flash",
                 deepseek_api_key: str = "",
                 deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions",
                 deepseek_model: str = "deepseek-chat") -> None:
        self.thinker = thinker
        self.journal = journal
        self.review_interval = review_interval
        self.api_key = api_key
        self.glm_api_url = glm_api_url
        self.glm_model = glm_model
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_api_url = deepseek_api_url
        self.deepseek_model = deepseek_model

        self.quality_history: list[float] = []
        self.directives_sent: int = 0
        self.trust_score: float = 0.5
        self.consecutive_decreases: int = 0
        self.last_directive: Directive | None = None
        self.previous_prompt: str = thinker.config.system_prompt
        self._running = False
        self._on_directive = None

        # Track which prompt variations have been tried
        self.prompt_history: list[tuple[str, float]] = []  # (prompt_name, avg_quality)

    def set_on_directive(self, callback) -> None:
        """Register a callback called after each directive is applied."""
        self._on_directive = callback

    def _assess_window(self, thoughts: list[dict[str, Any]]) -> float:
        """Compute average quality across a window of thoughts."""
        if not thoughts:
            return 0.5

        recent_texts = [t["content"] for t in thoughts]
        scores = []
        for i, t in enumerate(thoughts):
            text = t["content"]
            prior = recent_texts[:i] if i > 0 else []
            score = QualityScore.compute(text, prior)
            scores.append(score.overall)

            # Store quality in the thought's metadata
            t.setdefault("metadata", {})["quality"] = round(score.overall, 3)
            t["metadata"]["quality_detail"] = {
                "novelty": round(score.novelty, 3),
                "specificity": round(score.specificity, 3),
                "coherence": round(score.coherence, 3),
                "engagement": round(score.engagement, 3),
            }

        avg = sum(scores) / len(scores)
        self.quality_history.append(avg)
        return avg

    def _choose_directive(self, thoughts: list[dict[str, Any]],
                          avg_quality: float) -> Directive | None:
        """Decide what directive to send, if any.

        Strategy:
        - If quality is declining (3 consecutive decreases), rollback
        - If quality is low (<0.4), try a different prompt
        - If quality is high (>0.7), make small tweaks (temperature)
        - If quality is mid-range, try to push it up with context injection
        - Occasionally use LLM to generate a smart directive
        """
        if not thoughts:
            return None

        # Check for consecutive quality decreases
        if len(self.quality_history) >= 3:
            recent = self.quality_history[-3:]
            if all(recent[i] < recent[i - 1] for i in range(1, len(recent))):
                # Quality is declining — rollback if we can
                if self.last_directive and self.consecutive_decreases >= 2:
                    return self._rollback_directive()

        # Quality-based decisions
        current_prompt = self.thinker.config.system_prompt

        if avg_quality < 0.35:
            # Quality is very low — switch to a different prompt style
            available = [p for p in PROMPT_VARIATIONS.values() if p != current_prompt]
            # Pick the one we haven't tried, or the one with best historical performance
            if self.prompt_history:
                best_prompt = max(self.prompt_history, key=lambda x: x[1])
                new_prompt = best_prompt[0] if best_prompt[1] > avg_quality else None
                if new_prompt and PROMPT_VARIATIONS.get(new_prompt):
                    return Directive(
                        kind="prompt",
                        description=f"Switching to '{new_prompt}' prompt (quality={avg_quality:.2f})",
                        changes={"system_prompt": PROMPT_VARIATIONS[new_prompt]},
                    )
            # Try a random different prompt
            import random
            new_style = random.choice(list(PROMPT_VARIATIONS.keys()))
            if PROMPT_VARIATIONS[new_style] == current_prompt:
                new_style = "analytical"  # fallback
            return Directive(
                kind="prompt",
                description=f"Switching to '{new_style}' prompt (quality={avg_quality:.2f})",
                changes={"system_prompt": PROMPT_VARIATIONS[new_style]},
            )

        elif avg_quality > 0.7:
            # Quality is high — small tweaks
            if self.thinker.config.temperature < 1.1:
                return Directive(
                    kind="temperature",
                    description=f"Increasing temperature for more creativity (quality={avg_quality:.2f})",
                    changes={"temperature": min(1.3, self.thinker.config.temperature + 0.05)},
                )
            return None  # Don't fix what isn't broken

        else:
            # Mid-range quality — try injecting context from recent thoughts
            if thoughts:
                # Pick the highest-quality recent thought and use it as seed
                sorted_thoughts = sorted(thoughts, key=lambda t: t.get("metadata", {}).get("quality", 0.5))
                best = sorted_thoughts[-1]
                seed = best["content"][:100]
                return Directive(
                    kind="context",
                    description=f"Seeding context from high-quality thought (quality={avg_quality:.2f})",
                    changes={"context": f"Earlier you thought: \"{seed}...\". Build on or diverge from this."},
                )
            return None

    def _rollback_directive(self) -> Directive:
        """Rollback to the previous prompt."""
        return Directive(
            kind="prompt",
            description="Rollback: reverting to previous prompt after quality decline",
            changes={"system_prompt": self.previous_prompt},
        )

    def _llm_directive(self, thoughts: list[dict[str, Any]],
                       avg_quality: float) -> Directive | None:
        """Use an LLM to generate a smart directive.

        This is the Gate-3 path — expensive, used sparingly.
        Falls back to heuristic if the LLM call fails.
        """
        if not self.api_key and not self.deepseek_api_key:
            return self._choose_directive(thoughts, avg_quality)

        # Build the analysis prompt
        thought_summaries = "\n".join(
            f"- [{t.get('metadata', {}).get('quality', '?'):.2f}] {t['content'][:120]}"
            for t in thoughts[-8:]
        )

        sys_prompt = (
            "You are a thought supervisor. Analyze the stream of thoughts and "
            "decide how to adjust the thinker's conditions. Respond in JSON only.\n\n"
            "Options:\n"
            '  {"action": "prompt", "style": "analytical|creative|philosophical|scientific|playful|investigative", "reason": "..."}\n'
            '  {"action": "temperature", "value": 0.5-1.3, "reason": "..."}\n'
            '  {"action": "context", "text": "...", "reason": "..."}\n'
            '  {"action": "none", "reason": "..."}\n'
        )

        user_prompt = (
            f"Average quality: {avg_quality:.2f}\n"
            f"Current prompt style: {self._current_prompt_name()}\n"
            f"Current temperature: {self.thinker.config.temperature}\n\n"
            f"Recent thoughts:\n{thought_summaries}\n\n"
            f"What adjustment would improve the thought stream?"
        )

        try:
            payload = {
                "model": self.glm_model if self.api_key else self.deepseek_model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 200,
                "stream": False,
            }

            if self.api_key:
                result = _curl_post_json(self.glm_api_url, payload,
                                        headers={"Authorization": f"Bearer {self.api_key}"})
            else:
                result = _curl_post_json(self.deepseek_api_url, payload,
                                        headers={"Authorization": f"Bearer {self.deepseek_api_key}"})

            response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Parse JSON from response (may have markdown code fence)
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*$', '', response).strip()
            decision = json.loads(response)

            action = decision.get("action", "none")
            reason = decision.get("reason", "")

            if action == "prompt":
                style = decision.get("style", "analytical")
                prompt = PROMPT_VARIATIONS.get(style, PROMPT_VARIATIONS["analytical"])
                return Directive(kind="prompt",
                                description=f"LLM: switch to '{style}' — {reason}",
                                changes={"system_prompt": prompt})
            elif action == "temperature":
                temp = float(decision.get("value", self.thinker.config.temperature))
                return Directive(kind="temperature",
                                description=f"LLM: temperature={temp} — {reason}",
                                changes={"temperature": temp})
            elif action == "context":
                ctx = decision.get("text", "")
                return Directive(kind="context",
                                description=f"LLM: context injection — {reason}",
                                changes={"context": ctx})
            else:
                return None

        except Exception as e:
            # Fallback to heuristic
            return self._choose_directive(thoughts, avg_quality)

    def _current_prompt_name(self) -> str:
        """Identify which prompt variation is currently active."""
        for name, prompt in PROMPT_VARIATIONS.items():
            if prompt == self.thinker.config.system_prompt:
                return name
        return "custom"

    def _apply_directive(self, directive: Directive) -> None:
        """Apply a directive and update trust tracking."""
        quality_before = self.quality_history[-1] if self.quality_history else 0.5

        # Save state for potential rollback
        if directive.kind == "prompt":
            self.previous_prompt = self.thinker.config.system_prompt

        # Apply
        directive.apply(self.thinker.config)
        self.last_directive = directive
        self.directives_sent += 1

        # Journal it
        self.journal.write(
            "directive",
            directive.description,
            {
                "kind": directive.kind,
                "changes": directive.changes,
                "quality_before": round(quality_before, 3),
                "trust_score": round(self.trust_score, 3),
            },
        )

        # Notify callback
        if self._on_directive:
            try:
                self._on_directive(directive)
            except Exception:
                pass

    def review(self) -> Directive | None:
        """Perform one review cycle.

        Reads recent thoughts, assesses quality, chooses and applies
        a directive if warranted.
        """
        thoughts = self.thinker.journal.read_thoughts(limit=10)

        if len(thoughts) < 3:
            return None  # Not enough data yet

        avg_quality = self._assess_window(thoughts)

        # Update trust based on previous directive
        if self.last_directive and len(self.quality_history) >= 2:
            prev_q = self.quality_history[-2]
            curr_q = self.quality_history[-1]
            if curr_q > prev_q:
                self.trust_score = min(0.95, self.trust_score + 0.5 / 10)
                self.consecutive_decreases = 0
            elif curr_q < prev_q:
                self.trust_score = max(0.05, self.trust_score - 2.0 / 10)
                self.consecutive_decreases += 1

        # Choose directive (use heuristic by default, LLM occasionally)
        use_llm = (self.api_key or self.deepseek_api_key) and \
                  self.directives_sent % 3 == 0  # Every 3rd review

        if use_llm:
            directive = self._llm_directive(thoughts, avg_quality)
        else:
            directive = self._choose_directive(thoughts, avg_quality)

        if directive:
            self._apply_directive(directive)

        # Write a quality summary
        self.journal.write(
            "summary",
            f"Window quality: {avg_quality:.2f} avg across {len(thoughts)} thoughts. "
            f"Trust: {self.trust_score:.2f}. Directives sent: {self.directives_sent}.",
            {
                "avg_quality": round(avg_quality, 3),
                "trust_score": round(self.trust_score, 3),
                "thoughts_reviewed": len(thoughts),
            },
        )

        return directive

    def run(self) -> None:
        """Run the supervisor loop. Blocks until interrupted."""
        self._running = True
        self.journal.write(
            "system",
            f"Supervisor started (review_interval={self.review_interval}s)",
        )

        while self._running:
            try:
                self.review()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.journal.write("system", f"Supervisor error: {e}", {"error": str(e)})

            waited = 0.0
            while self._running and waited < self.review_interval:
                time.sleep(0.5)
                waited += 0.5

        self.journal.write("system", f"Supervisor stopped after {self.directives_sent} directives")

    def stop(self) -> None:
        """Signal the supervisor loop to stop."""
        self._running = False
