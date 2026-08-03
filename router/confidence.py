"""
confidence.py — Local Confidence Assessment

How does the router know if a local model CAN handle a request?

This is the crux of the KNOWN-UNKNOWN vs UNKNOWN-UNKNOWN decision.
Get this wrong and either:
  - You over-escalate to cloud (wasting money on things the local
    model could handle) — false UNKNOWN-UNKNOWN
  - You under-escalate and the local model produces garbage —
    false KNOWN-UNKNOWN

We use multiple weak signals and combine them into a single confidence
score. No single signal is reliable. The ensemble is.

Signals (from experimental data and architectural reasoning):

1. REFLEX MATCH SCORE
   If there's a partial match to an existing reflex (similar prompt
   shape, same domain), the local model likely can handle it. The
   reflex cache didn't hit (this isn't a KNOWN-KNOWN), but a nearby
   reflex means we're in familiar territory.

2. PROMPT COMPLEXITY
   Word count, nesting depth, question type. Short, direct prompts
   are easy for local models. Long, multi-step reasoning chains
   are harder. From EXP3: Granite 2B wins on analytical tasks
   (comparisons, pattern recognition, problem solving) but struggles
   with creative/emotional depth.

3. HISTORICAL SUCCESS RATE
   Have similar prompts (by category) succeeded locally before?
   This is a per-category EMA of local success rate.

4. MODEL CAPABILITY MAP
   What is each local model known to be good at?
   From EXP3 GPU data:
     Granite 2B: analytical, problem-solving, empathy, reflection
     Qwen 0.5B: creative, emotional, instructional, quick filler
   If the task falls in either model's strength zone, confidence rises.

5. NOVELTY DETECTION
   Is this prompt type completely new? If we've never seen anything
   like it, confidence drops. Novel prompts might require a larger
   model of understanding.

The ensemble: weighted geometric mean of signals. Geometric mean
because a single very low signal (e.g., extreme novelty = 0.1)
should pull down the overall confidence even if other signals are
moderate. This is conservative — we'd rather over-escalate to cloud
than produce a confident-sounding wrong answer locally.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("router.confidence")


# ---------------------------------------------------------------------------
# Prompt Complexity Analyzer
# ---------------------------------------------------------------------------

# Task type classification — derived from EXP3 prompt categories
TASK_PATTERNS = {
    "analytical": [
        r"\b(compar|analyz|evaluat|assess|determin|calcul)",
        r"\b(differ|similar|better|worse|versus|vs)\b",
        r"\b(pros|cons|advantage|disadvantage)\b",
        r"\b(logic|reason|deduc|infer|conclud)\b",
    ],
    "problem_solving": [
        r"\b(how (do|to|can)|what (do|should|can))\b",
        r"\b(solve|fix|repair|build|creat|design|implement)\b",
        r"\b(step|process|procedure|method|approach)\b",
        r"\b(problem|issue|error|bug|fail)\b",
    ],
    "creative": [
        r"\b(story|poem|imag|describ|narrat|character)\b",
        r"\b(dream|fanasy|magic|wonder|beautif)\b",
        r"\b(scene|setting|atmosphere|mood)\b",
        r"\b(write|compos|draft|pen)\b",
    ],
    "emotional": [
        r"\b(feel|emotion|sad|happy|angry|afraid|worried)\b",
        r"\b(love|hate|fear|hope|regret|miss)\b",
        r"\b(empathy|sympath|comfort|reassur)\b",
        r"\b(relationship|friend|family|trust)\b",
    ],
    "instructional": [
        r"\b(explain|teach|show|guide|instruct|tutorial)\b",
        r"\b(what is|define|meaning|example of)\b",
        r"\b(list|steps?|how (do|to))\b",
        r"\b(simple|basic|beginner|overview)\b",
    ],
    "spatial": [
        r"\b(where|location|position|place|direction)\b",
        r"\b(north|south|east|west|up|down|left|right)\b",
        r"\b(distan|near|far|beside|behind|front)\b",
        r"\b(layout|map|area|zone|region)\b",
    ],
    "code": [
        r"\b(code|function|class|method|variable|import)\b",
        r"\b(python|javascript|lua|rust|golang|java)\b",
        r"\b(debug|compile|runtime|syntax|error)\b",
        r"\b(API|endpoint|request|response|HTTP)\b",
    ],
    "reflection": [
        r"\b(why|meaning|purpose|reflect|ponder)\b",
        r"\b(philosoph|exist|moral|ethic|value)\b",
        r"\b(believe|think|opinion|perspective)\b",
        r"\b(imply|suggest|indicat|signif)\b",
    ],
    "causal": [
        r"\b(because|therefore|thus|hence|consequent)\b",
        r"\b(cause|effect|result|impact|influence)\b",
        r"\b(if.*then|depend|lead to|result in)\b",
        r"\b(why did|how come|what caused)\b",
    ],
    "social": [
        r"\b(people|person|someone|they|their)\b",
        r"\b(social|community|group|team|crowd)\b",
        r"\b(interact|communicat|convers|dialog)\b",
        r"\b(relationship|friendship|conflict)\b",
    ],
}


@dataclass
class ComplexityScore:
    """Result of prompt complexity analysis."""
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    question_depth: int       # how many nested questions
    has_code: bool
    has_multi_step: bool      # "first... then... finally..."
    task_type: str            # classified task type
    task_confidence: float    # how confident the classification is
    complexity: float         # 0.0 (trivial) to 1.0 (very complex)


def analyze_complexity(prompt: str) -> ComplexityScore:
    """
    Analyze prompt complexity from structural features.

    This is intentionally simple — keyword and pattern based.
    No ML needed. The signal doesn't need to be perfect; it just
    needs to be one input to the ensemble.
    """
    # Basic counts
    words = prompt.split()
    word_count = len(words)

    # Sentence splitting (rough)
    sentences = re.split(r'[.!?]+', prompt)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = max(1, len(sentences))
    avg_sentence_length = word_count / sentence_count

    # Question depth (count question marks, nested questions)
    question_marks = prompt.count('?')
    # Nested: "Why does X happen when Y occurs because Z?"
    nested_indicators = len(re.findall(
        r'\b(why|how).*(when|because|if|while|whereas)\b', prompt, re.IGNORECASE
    ))
    question_depth = question_marks + nested_indicators

    # Code presence
    has_code = bool(re.search(
        r'(```|def |function |class |import |#include|<\?php|public |private )',
        prompt
    ))

    # Multi-step instruction
    has_multi_step = bool(re.search(
        r'\b(first|second|third|then|next|finally|step \d|1\.|2\.|3\.)\b',
        prompt, re.IGNORECASE
    ))

    # Task type classification
    task_type, task_confidence = _classify_task(prompt)

    # Overall complexity score
    # Each component contributes, clamped to [0, 1]
    length_score = min(1.0, word_count / 200.0)        # 200+ words = max complexity
    depth_score = min(1.0, question_depth / 3.0)       # 3+ nested questions = max
    sentence_score = min(1.0, avg_sentence_length / 40.0)  # 40+ words/sentence = complex
    code_bonus = 0.15 if has_code else 0.0
    multi_step_bonus = 0.10 if has_multi_step else 0.0

    complexity = min(1.0, (
        0.35 * length_score +
        0.25 * depth_score +
        0.20 * sentence_score +
        code_bonus +
        multi_step_bonus
    ))

    return ComplexityScore(
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=round(avg_sentence_length, 1),
        question_depth=question_depth,
        has_code=has_code,
        has_multi_step=has_multi_step,
        task_type=task_type,
        task_confidence=round(task_confidence, 3),
        complexity=round(complexity, 3),
    )


def _classify_task(prompt: str) -> tuple[str, float]:
    """
    Classify the prompt into a task type using keyword patterns.

    Returns (task_type, confidence) where confidence is the
    proportion of matched patterns for the winning category.
    """
    prompt_lower = prompt.lower()
    scores: dict[str, int] = defaultdict(int)

    for task_type, patterns in TASK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                scores[task_type] += 1

    if not scores:
        return "general", 0.0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    total_matches = sum(scores.values())
    confidence = best_score / total_matches if total_matches > 0 else 0.0

    return best_type, confidence


# ---------------------------------------------------------------------------
# Model Capability Map
# ---------------------------------------------------------------------------

# From EXP3 GPU RERUN data:
# Granite 2B wins: analytical compare, problem solving, hypothetical,
#                  empathy, pattern recognition, narrative, reflection
# Qwen 0.5B wins: creative describe, emotional response, social,
#                  instructional, constraint reasoning, personality voice
#
# Capability is scored 0.0-1.0 per task type per model.
# These are PRIORS — adjusted by historical success data over time.

MODEL_CAPABILITY = {
    "granite3.1-dense:2b": {
        "analytical": 0.85,
        "problem_solving": 0.80,
        "reflection": 0.75,
        "causal": 0.70,
        "code": 0.65,
        "spatial": 0.60,
        "instructional": 0.55,
        "narrative": 0.50,
        "social": 0.45,
        "emotional": 0.40,
        "creative": 0.35,
        "general": 0.55,
    },
    "qwen2.5:0.5b": {
        "creative": 0.75,
        "emotional": 0.70,
        "instructional": 0.65,
        "social": 0.60,
        "narrative": 0.55,
        "spatial": 0.50,
        "general": 0.50,
        "analytical": 0.45,
        "problem_solving": 0.40,
        "causal": 0.40,
        "code": 0.30,
        "reflection": 0.35,
    },
}


def best_model_for_task(task_type: str) -> tuple[str, float]:
    """Return (model_name, capability_score) for the best model for a task."""
    best_model = ""
    best_score = 0.0
    for model, caps in MODEL_CAPABILITY.items():
        score = caps.get(task_type, 0.5)
        if score > best_score:
            best_score = score
            best_model = model
    return best_model, best_score


def max_capability(task_type: str) -> float:
    """Return the highest capability score across all models for a task."""
    return max(caps.get(task_type, 0.5) for caps in MODEL_CAPABILITY.values())


# ---------------------------------------------------------------------------
# Historical Success Tracker
# ---------------------------------------------------------------------------

class SuccessHistory:
    """
    Tracks local model success rate per task type.

    Uses an exponential moving average (α=0.05, same as ZeroClaw
    Arena's policy evolution — slow adaptation, noise resistant).

    Minimum 5 observations before the EMA is trusted. Below that,
    we fall back to the prior (MODEL_CAPABILITY map).
    """

    EMA_ALPHA = 0.05
    MIN_OBSERVATIONS = 5

    def __init__(self):
        # task_type -> list of (success: bool, quality: float)
        self._observations: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )
        # task_type -> current EMA
        self._ema: dict[str, float] = {}
        # task_type -> count
        self._counts: dict[str, int] = defaultdict(int)

    def record(self, task_type: str, success: bool, quality: float = 0.0):
        """Record a local model outcome."""
        score = quality if quality > 0 else (1.0 if success else 0.0)
        self._observations[task_type].append((success, quality))
        self._counts[task_type] += 1

        prev = self._ema.get(task_type, score)  # cold start = first observation
        self._ema[task_type] = prev + self.EMA_ALPHA * (score - prev)

    def success_rate(self, task_type: str) -> float | None:
        """
        Get the historical success rate for a task type.

        Returns None if insufficient data (< MIN_OBSERVATIONS).
        """
        count = self._counts.get(task_type, 0)
        if count < self.MIN_OBSERVATIONS:
            return None
        return self._ema.get(task_type)

    def stats(self) -> dict:
        return {
            tt: {
                "count": self._counts[tt],
                "ema": round(self._ema.get(tt, 0.0), 4),
            }
            for tt in sorted(self._counts)
        }


# ---------------------------------------------------------------------------
# Novelty Detector
# ---------------------------------------------------------------------------

class NoveltyDetector:
    """
    Detects whether a prompt is unlike anything seen before.

    Uses a simple prompt-shape hash: the set of task-type keywords
    detected, plus length bucket. Two prompts with the same shape hash
    are "the same kind of question" even if the content differs.

    High novelty = we've never seen this shape → lower confidence.
    """

    LENGTH_BUCKETS = [(0, 10), (10, 30), (30, 80), (80, 200), (200, 99999)]

    def __init__(self):
        self._seen_shapes: dict[str, int] = defaultdict(int)

    def _shape_hash(self, prompt: str, task_type: str) -> str:
        wc = len(prompt.split())
        bucket = "L0"
        for i, (lo, hi) in enumerate(self.LENGTH_BUCKETS):
            if lo <= wc < hi:
                bucket = f"L{i}"
                break
        return f"{task_type}:{bucket}"

    def observe(self, prompt: str, task_type: str) -> float:
        """
        Record a prompt and return its novelty score.

        novelty = 1.0 - min(1.0, seen_count / 20)
        First time seeing a shape → 1.0 (maximally novel)
        After 20+ times → 0.0 (well-known shape)
        """
        shape = self._shape_hash(prompt, task_type)
        self._seen_shapes[shape] += 1
        count = self._seen_shapes[shape]
        return max(0.0, 1.0 - count / 20.0)

    def novelty_of(self, prompt: str, task_type: str) -> float:
        """Check novelty without recording a new observation."""
        shape = self._shape_hash(prompt, task_type)
        count = self._seen_shapes.get(shape, 0)
        return max(0.0, 1.0 - count / 20.0)


# ---------------------------------------------------------------------------
# Confidence Assessor
# ---------------------------------------------------------------------------

class ConfidenceAssessor:
    """
    The full confidence assessment pipeline.

    Combines multiple signals into a single confidence score that
    determines the KNOWN-UNKNOWN vs UNKNOWN-UNKNOWN boundary.

    Signal weights (sum to 1.0):
      - Model capability   : 0.35  (can ANY local model do this?)
      - Historical success  : 0.25  (have local models done this before?)
      - Prompt complexity   : 0.20  (is the prompt tractable?)
      - Novelty             : 0.20  (is this completely new territory?)

    The ensemble is a weighted geometric mean, which is conservative:
    a single very low signal drags the whole score down. This prevents
    false confidence in unknown territory.
    """

    def __init__(
        self,
        success_history: SuccessHistory | None = None,
        novelty_detector: NoveltyDetector | None = None,
    ):
        self.success_history = success_history or SuccessHistory()
        self.novelty_detector = novelty_detector or NoveltyDetector()

    def assess(
        self,
        prompt: str,
        agent: str = "default",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Assess local confidence for a prompt.

        Returns a dict with:
          confidence: float (0.0 to 1.0)
          task_type: str
          signals: dict of individual signal scores
          recommended_model: str (the model with highest capability for this task)
        """
        context = context or {}

        # Analyze prompt
        complexity = analyze_complexity(prompt)

        # Signal 1: Model capability — can any local model handle this task?
        best_model, best_cap = best_model_for_task(complexity.task_type)
        capability_signal = best_cap

        # Signal 2: Historical success
        hist_rate = self.success_history.success_rate(complexity.task_type)
        if hist_rate is not None:
            history_signal = hist_rate
        else:
            # Cold start: trust the prior (capability map)
            history_signal = best_cap * 0.8  # slight discount for no data

        # Signal 3: Complexity (inverse — high complexity = lower confidence)
        complexity_signal = 1.0 - complexity.complexity

        # Signal 4: Novelty (inverse — high novelty = lower confidence)
        novelty = self.novelty_detector.observe(prompt, complexity.task_type)
        novelty_signal = 1.0 - novelty

        # Geometric weighted mean
        weights = {
            "capability": 0.35,
            "history": 0.25,
            "complexity": 0.20,
            "novelty": 0.20,
        }

        signals = {
            "capability": capability_signal,
            "history": history_signal,
            "complexity": complexity_signal,
            "novelty": novelty_signal,
            "novelty_raw": novelty,
            "complexity_raw": complexity.complexity,
        }

        # Geometric mean: product of (signal^weight)
        log_sum = sum(
            weights[k] * math.log(max(0.01, signals[k]))
            for k in ["capability", "history", "complexity", "novelty"]
        )
        confidence = math.exp(log_sum)

        return {
            "confidence": round(confidence, 4),
            "task_type": complexity.task_type,
            "task_confidence": complexity.task_confidence,
            "complexity": complexity.complexity,
            "word_count": complexity.word_count,
            "recommended_model": best_model,
            "signals": {k: round(v, 4) for k, v in signals.items()},
        }

    def record_outcome(
        self,
        task_type: str,
        success: bool,
        quality: float = 0.0,
    ):
        """Record a local model outcome for future confidence assessments."""
        self.success_history.record(task_type, success, quality)
