# Cognitive Router — The Epistemic Frontier

**Status:** Built and tested (37/37 tests passing)
**Date:** 2026-08-03
**Location:** `/home/eileen/projects/thought-amplifier/router/`
**Depends on:** `scheduler/` (Logos), experiments EXP2/EXP3 (empirical data)
**Stdlib only.** Zero external dependencies.

---

## The Thesis

> *Every inference request exists in one of three epistemic states. The router's job is to detect which one, route accordingly, and ensure that over time, the unknown becomes known.*

An RTX 4050 with 6GB VRAM sits at the boundary between local and cloud compute. It's powerful enough to run real models (Granite 2B at 76.8 tok/s, Qwen 0.5B at 178.8 tok/s — both under 1.5s latency on GPU), but not powerful enough for everything. The question is never "can we run this locally?" — it's "SHOULD we?"

The Cognitive Router answers that question by detecting the **epistemic state** of each request: what is the system's relationship to this particular kind of problem?

---

## The Three Epistemic States

### State 1: KNOWN-KNOWN — "We've been here before"

The system has seen this exact problem (or one close enough) and has a cached answer. No model call needed. The vector DB IS the runtime — this is Pincher's inversion.

```
confidence > 0.85 → reflex cache hit
latency: < 1ms
cost: $0
```

**The escape hatch:** Every reflex carries `max_consecutive_uses`. After N identical dispatches, the reflex is force-invalidated. The system MUST re-check its most trusted conclusions. Without this, a high-confidence wrong reflex is a permanent blind spot — the system stops sampling the very evidence that would correct it.

This is not a bug. It's the epistemological humility of the entire architecture: confidence never becomes certainty. There is always a gap.

### State 2: KNOWN-UNKNOWN — "We know what this is"

The system recognizes the TYPE of problem (analytical, creative, code, etc.) and knows that a local model has sufficient capability to handle it. It hasn't processed THIS exact request, but it knows the territory.

```
0.40 ≤ confidence ≤ 0.85 → route to fastest sufficient local model
latency: 0.5-1.1 seconds (GPU-accelerated)
cost: $0
```

**Model selection** is quality-first (not speed-first), because at GPU speeds both models respond in under 1.5s. The 0.6s difference between Granite (1.1s) and Qwen (0.5s) is barely perceptible. What matters is which model will produce better output for THIS task type.

From EXP3 data:
- **Granite 2B** for analytical, problem-solving, empathy, reflection, pattern recognition
- **Qwen 0.5B** for creative, emotional, instructional, social, personality voice
- **Granite always** when character consistency matters (Qwen breaks character ~20% of the time)

### State 3: UNKNOWN-UNKNOWN — "We don't even know what shape this is"

No pattern matches. The puzzle pieces don't fit. The prompt is novel, complex, and outside the local models' demonstrated capability envelope. This needs a LARGER MODEL OF UNDERSTANDING — not just a faster or better version of what we have, but a fundamentally bigger capacity to shape the problem.

```
confidence < 0.40 → cascade to cloud
latency: 10-30 seconds
cost: $0.0003 - $0.002 per request (DeepSeek V3, Qwen-Coder-480B, Hermes-405B)
```

**Cloud model routing by specialty:**
- **DeepSeek V3** — reasoning, planning, multi-step analysis (cheapest: $0.00027/1K input)
- **Qwen3-Coder-480B** — code generation, debugging, refactoring
- **Hermes-405B** — creative voice, personality, nuanced emotional content
- **Cloudflare Llama-3.1-8B** — free overflow when budget is exhausted

This is worth the cost because State 3 creates NEW KNOWLEDGE. The cloud model produces an answer that didn't exist in the system before. And that answer gets written back as a reflex — a piece of the UNKNOWN becomes KNOWN.

---

## The Profound Part: The Boundary Evolves

The system is not static. It learns.

```
Time 0:      ▓▓▓▓▓▓▓▓▓▓ UNKNOWN-UNKNOWN (everything is new)
Time 1 hour:  ▓▓▓▓▓▓▓ UNKNOWN-UNKNOWN, ▓▓▓ KNOWN-UNKNOWN, ▓ KNOWN-KNOWN
Time 1 day:   ▓▓▓▓ UNKNOWN-UNKNOWN, ▓▓▓▓ KNOWN-UNKNOWN, ▓▓▓ KNOWN-KNOWN
Time 1 week:  ▓▓ UNKNOWN-UNKNOWN, ▓▓▓ KNOWN-UNKNOWN, ▓▓▓▓▓ KNOWN-KNOWN
```

### The Pincher Write-Back

When a cloud response (State 3) succeeds with high quality, the answer is compiled into a reflex. Next time the same prompt arrives, it's a reflex hit (State 1) — sub-1ms, $0.

The cloud solution became a local reflex. A piece of the unknown frontier became known territory. And the system didn't just learn the answer — it learned that it CAN handle this kind of problem.

The compiled reflex starts at confidence 0.80-0.90 (high but not certain). It earns the last bit through repeated successful use. If it fails, confidence drops fast (asymmetric update: +0.05×(1-c) on success, −0.10×c on failure).

### The Boundary IS the Knowledge Frontier

The `BoundaryTracker` records every routing decision and its outcome. The distribution of states over time IS the system's growth metric:

- **State distribution** — what fraction of requests are KNOWN-KNOWN vs KNOWN-UNKNOWN vs UNKNOWN-UNKNOWN?
- **Routing accuracy** — did the router make the right call? Were local requests handled adequately? Were cloud requests genuinely beyond local capability?
- **Calibration error** — does the router's confidence match the actual success rate? Well-calibrated routers have confidence ≈ success rate.
- **Reflex growth rate** — how many cloud solutions per hour are becoming local reflexes?
- **Cost trend** — as reflexes accumulate, the average cost per request should trend toward $0.

This is the production line thesis, made measurable: **the hardware gets better at producing value.**

---

## The University Supercomputer Metaphor

The Cognitive Router inherits the scheduler's university supercomputer model and extends it with epistemic intelligence.

A university supercomputer serves hundreds of labs:
- The **physics lab** needs massive parallel jobs → deep reasoning → DeepSeek V3
- The **biology lab** needs steady moderate jobs → analytical thinking → Granite 2B
- The **CS department** writes code → Qwen-Coder-480B for hard problems, Granite for simple ones
- The **humanities lab** writes stories → Hermes-405B for novels, Qwen for quick prose
- The **math department** proofs and logic → reflex cache (these are always the same)

The supercomputer's scheduler doesn't just allocate GPU time — it decides WHICH MACHINE to run each job on. A job that needs the BlueGene doesn't go to the GPU cluster. A job that fits on a workstation doesn't waste supercomputer hours.

The Cognitive Router makes the same decision for inference: which model (which machine) should handle this request? The scheduler (Logos) decides when. The router decides where.

---

## The Tripartite Connection

The Cognitive Router is the missing link between the three faculties:

### Logos (The Rational Principle) — Routing Decision
The router IS a Logos function. It applies rules: confidence thresholds, capability maps, cost estimates. It follows the three-gate cascade pattern (reflex → local → cloud) that recurs throughout the architecture. Perfectly rational, perfectly consistent.

### Pathos (The Emotional Principle) — Quality Signals
The router doesn't just follow rules — it FEELS whether its decisions were good. The quality feedback loop (`record_outcome`) is Pathos: the capacity to sense whether an outcome was valuable, and to let that feeling change future behavior. The confidence EMAs, the model preference scores, the calibration tracking — these are all the router's emotional memory.

### Ethos (The Ethical Principle) — Cost and Fairness
The cloud budget tracker is Ethos. It ensures the system doesn't spend recklessly. When the budget is exhausted, the system gracefully degrades to the free Cloudflare tier rather than failing. The guarantee that every request gets served (even if at lower quality) is the ethical commitment. And the long-term trend toward $0 average cost — as reflexes accumulate and the known territory expands — is the system becoming more generous over time.

---

## Confidence Assessment: The Signal Ensemble

How does the router know if a local model CAN handle a request? Five signals, combined as a weighted geometric mean:

| Signal | Weight | Source | Rationale |
|--------|--------|--------|-----------|
| Model capability | 0.30 | EXP3 data (task-type × model matrix) | Can ANY local model theoretically handle this? |
| Historical success | 0.25 | Per-task-type EMA (α=0.05) | Have local models ACTUALLY handled this before? |
| Novelty | 0.25 | Prompt-shape hash counter | Is this completely new territory? |
| Complexity | 0.20 | Structural analysis (length, depth, code, multi-step) | Is the prompt tractable for a 2B/0.5B model? |

The geometric mean is deliberately conservative. A single very low signal (e.g., novelty = 0.05 on first-seen prompt) drags the whole score down, even if other signals are moderate. This is the right bias: **we'd rather over-escalate to cloud than produce a confident-sounding wrong answer locally.**

As the system sees more prompts, novelty decreases and historical success accumulates. The confidence for familiar task types rises, and more requests qualify as KNOWN-UNKNOWN (local). The boundary moves.

---

## Architecture

```
                    ┌──────────────────────────┐
                    │     Cognitive Router      │
                    │                          │
                    │  ┌─────────────────────┐ │
                    │  │ Gate 1: Reflex Cache│ │  KNOWN-KNOWN (< 1ms, $0)
                    │  │ confidence > 0.85   │ │
                    │  └─────────┬───────────┘ │
                    │            ↓ miss        │
                    │  ┌─────────────────────┐ │
                    │  │ Gate 2: Confidence  │ │
                    │  │ Assessment          │ │
                    │  │ (5-signal ensemble) │ │
                    │  └─────────┬───────────┘ │
                    │       ≥0.40│<0.40        │
                    │    ↓       ↓             │
                    │  LOCAL    CLOUD          │
                    │  (Gate 2) (Gate 3)       │
                    │  1-3s     10-30s         │  KNOWN-UNKNOWN / UNKNOWN-UNKNOWN
                    │  $0       $0.0003-0.002  │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌────▼──────────┐
                    │ Ollama  │  │ Cloud Models  │
                    │ Granite │  │ DeepSeek V3   │
                    │   or    │  │ Qwen-Coder    │
                    │  Qwen   │  │ Hermes-405B   │
                    └─────────┘  └───────┬───────┘
                                         │
                              success + quality > 0.6
                                         │
                    ┌────────────────────▼────────┐
                    │  Pincher Write-Back         │
                    │  Cloud answer → Reflex      │
                    │  UNKNOWN → KNOWN            │
                    └─────────────────────────────┘
```

### Files

| File | Purpose | Key Classes |
|------|---------|-------------|
| `router.py` | Core routing decision + reflex cache | `CognitiveRouter`, `RouteDecision`, `ReflexCache` |
| `confidence.py` | 5-signal confidence ensemble | `ConfidenceAssessor`, `SuccessHistory`, `NoveltyDetector` |
| `model_selector.py` | Local model selection (Granite vs Qwen) | `LocalModelSelector`, `ModelProfile` |
| `cloud_cascade.py` | Cloud model selection + budget | `CloudCascade`, `CloudBudget`, `CloudModel` |
| `boundary_tracker.py` | Knowledge frontier tracking | `BoundaryTracker`, `RequestRecord` |
| `tests/test_router.py` | 37 tests covering all states + evolution | — |

### Integration with the Scheduler

The router sits IN FRONT of the existing scheduler:

```
agent → router.route(prompt) → RouteDecision
                                      │
                    ┌─────────────────┘
                    │
                    ├─ REFLEX → return cached answer (< 1ms)
                    │
                    ├─ LOCAL  → scheduler.submit(prompt, model=decision.model)
                    │           scheduler handles GPU serialization + fair use
                    │
                    └─ CLOUD  → cloud_cascade.escalate(prompt, decision.model)
                                (or scheduler.submit with cloud bridge)
```

The router decides WHERE. The scheduler decides WHEN. Together they form the complete Logos.

---

## Experimental Foundation

Every threshold and capability score traces to measured data:

| Parameter | Value | Source |
|-----------|-------|--------|
| Granite tok/s | 76.8 | EXP3 GPU RERUN |
| Qwen tok/s | 178.8 | EXP3 GPU RERUN |
| Granite latency | 1.1s | EXP3 GPU RERUN |
| Qwen latency | 0.5s | EXP3 GPU RERUN |
| Granite analytical quality | 0.85 (7/20 wins, highest on analytical) | EXP3 task-type breakdown |
| Qwen creative quality | 0.75 (10/20 wins, highest on creative) | EXP3 task-type breakdown |
| Qwen breaks character | ~20% of prompts | EXP3 observation |
| Granite never breaks character | 0/20 | EXP3 observation |
| Reflex confidence update | +0.05×(1-c) / −0.10×c | Pincher study, REPO_DESIGN §5.1 |
| Confidence clamp | [0.05, 0.95] | ZeroClaw Arena (guaranteed exploration) |
| EMA α | 0.05 | ZeroClaw Arena, Lever Runner |

---

## What Is Deliberately Unfinished

Following the Thought Amplifier philosophy:

1. **The confidence thresholds start conservative.** LOCAL_CONFIDENCE=0.40 and REFLEX_CONFIDENCE=0.85 are starting positions. The real values will emerge from observed calibration error. If the router is overconfident, the threshold rises; if underconfident, it falls. The `BoundaryTracker.calibration_error()` metric tells us which.

2. **The model capability map is static priors.** These are EXP3 measurements, not universal truths. The `LocalModelSelector` learns from outcomes (EMA α=0.05) and can eventually override the priors entirely. If a new model is loaded that's better at everything, the priors will be wrong until enough data accumulates.

3. **No automatic threshold tuning.** The router doesn't adjust its own thresholds based on calibration error. That's a future enhancement — potentially dangerous (the system optimizing its own decision boundary). For now, threshold adjustment is a human decision informed by the boundary report.

4. **Novelty detection is structural, not semantic.** The prompt-shape hash catches "same kind of question" but misses "semantically equivalent question rephrased." A proper semantic novelty detector needs embeddings — which requires the embedder port from the Thought Amplifier core. The structural detector is the hash fallback: it degrades gracefully, never fails.

5. **No persistence.** The reflex cache and boundary tracker are in-memory. If the router restarts, all learning is lost. Checkpointing to disk (or the scheduler's policy export) is the natural next step.

The gaps are where the growth happens.

---

*Built 2026-08-03. The epistemic frontier, made executable. The production line thesis, made measurable. The boundary evolves, known grows, unknown shrinks — and the hardware gets better at producing value.*
