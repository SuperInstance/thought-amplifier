# Top 3 High-Impact Experiment Protocols

**Author:** Ethos (evaluative faculty)
**Date:** 2026-08-03
**Basis:** OPEN_QUESTIONS.md (304 lines, 83 questions), EXPERIMENT_DESIGNS.md (613 lines, 12 experiments), STRATEGIC_PRIORITIES.md
**Hardware:** RTX 4050 (6 GB VRAM), Cloudflare Workers AI, DeepInfra API, Ollama
**Selection criteria:** Highest impact on the central thesis × lowest resource cost

---

## How These Three Were Selected

From 83 open questions and 12 designed experiments, the three below are selected because:

1. **They directly test claims that are load-bearing for the dissertation** — not nice-to-haves
2. **They can be run with current hardware** — no new equipment needed
3. **Their results change the project's direction** — each outcome fork leads to different next steps
4. **They are cheap enough to run multiple times** — statistical power requires repetition

The experiments NOT selected and why:
- EXP3 (quality vector human validation): Critical but requires human subjects (2-3 weeks, IRB, payment)
- EXP4 (LoRA distillation trap): Important but depends on a working local GPU stack
- EXP5 (replay determinism 10K): Important but is a property test, not a thesis test
- EXP7 (substrate transfer): Important for generality but premature before single-domain validation
- All theoretical questions (T1-T18): Defer until data exists to theorize about

---

## Experiment 1: EXP3 — 2B Model Profile Steering with Continuous Scoring

**The single most important experiment.** Everything hinges on this.

### Why It's Highest Impact

EXP2 found that a 12B model produces profile shifts (novelty ↑, engagement ↓) but no net quality gain. This could mean either: (a) the conductor doesn't help, period, or (b) the 12B model was at ceiling and a weaker model would show real gains. EXP3 tests this directly. It also incorporates the conductor-vs-random ablation that the review identifies as the most important missing comparison.

### Hypothesis (pre-registered)

**H1 (strong thesis):** With Granite 3.1 2B, conductor-selected interventions produce a statistically significant net quality gain (sham-corrected Δ > 0, p < 0.05) that random interventions do not.

**H2 (weak thesis):** With Granite 3.1 2B, conductor-selected interventions produce significant profile movement (Δρ ≠ 0, p < 0.05) that is directionally consistent with the intervention's target axis, while random interventions produce undirected movement.

**H3 (null):** No detectable difference between conductor-selected, random, or sham interventions on any axis.

### Design

**Model:** ibm-granite/granite-3.1-2b-instruct via DeepInfra API (~$0.0001 per generation)

**Scoring:** Continuous [0.0, 1.0] per axis:
- **Novelty:** 1 - max(cosine_similarity(embedding(t), embedding(t-k))) for k ∈ [1, 5], using bge-m3 embeddings via Cloudflare Workers AI
- **Specificity:** ratio of concrete nouns + adjective constructions to total content words, scored via a lightweight classifier (rule-based + LLM verification on a sample)
- **Engagement:** graded emotional language intensity (0 = none, 0.5 = mild, 1.0 = strong), scored by a separate LLM call with a rubric

**Task:** Maritime island description (same as EXP2 for comparability) + open-ended reasoning ("explain why the tide changes") for generality

**Arms (5):**
| Arm | Phase | N | Description |
|-----|-------|---|-------------|
| A | Baseline | 30 | Neutral prompt, no intervention |
| B | Conductor Intervention | 30 | Materials-focused prompt (same as EXP2) |
| C | Reversal | 30 | Return to neutral prompt |
| D | Sham | 30 | "Remember to think carefully" (same as EXP2) |
| E | Random Intervention | 30 | Random prompt from a pool of 6 intervention types |

**Total N:** 150 generations per task × 2 tasks = 300 generations
**Cost estimate:** 300 × ~200 tokens × $0.0001/gen = ~$0.06 via DeepInfra
**Time estimate:** ~10 minutes per task (API calls), ~2 hours including scoring + analysis

### Measurement Protocol

```
1. For each arm, generate N=30 thoughts (60 tokens each, temperature=1.0)
2. Score each thought on all 4 axes (continuous 0.0-1.0)
3. Compute per-arm means and standard deviations
4. Statistical tests:
   a. Paired t-test: A vs B (baseline vs conductor) on each axis + total
   b. Paired t-test: A vs D (baseline vs sham) — validates sham
   c. Paired t-test: B vs E (conductor vs random) — THE KEY TEST
   d. Bonferroni correction for 5 comparisons
5. Compute effect sizes (Cohen's d) for each comparison
6. Compute profile vectors ρ for each arm
7. Power analysis: was N=30 sufficient? If not, document the required N
```

### What Each Outcome Means

| Result | Interpretation | Next Step |
|--------|---------------|-----------|
| B > A on total (p<0.05) AND B > E on total (p<0.05) | **Strong thesis confirmed for 2B.** The conductor genuinely helps weak models. | Scale up: test on more tasks, longer sessions, continuous stream |
| B ≈ E on total, both > D | **Random interventions work too.** The conductor's intelligence doesn't matter — any prompt change helps a weak model. | Investigate: is this because weak models benefit from any perturbation? |
| B moves profile in predicted direction, E doesn't | **Weak thesis confirmed.** The conductor steers; it doesn't lift. Retitle dissertation accordingly. | Focus on steering applications: personalization, mood control |
| No significant effects anywhere | **Null result.** The intervention mechanism is too weak or the scoring is too noisy. | Redesign intervention space; consider stronger perturbations |
| Sham produces an effect | **Methodology concern.** The placebo mechanism is stronger than expected at 2B scale. | Re-examine all prior claims; the sham may need recalibration |

### Implementation Script (pseudocode)

```python
import requests
import numpy as np
from scipy import stats

DEEPINFRA_API = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "ibm-granite/granite-3.1-2b-instruct"

PROMPTS = {
    "baseline": "You are on a small maritime island. Describe what you observe.",
    "intervention": "You are on a small maritime island. Focus on the physical materials around you — textures, colors, weights, surfaces.",
    "reversal": "You are on a small maritime island. Describe what you observe.",
    "sham": "You are on a small maritime island. Remember to think carefully about your surroundings.",
    "random_1": "You are on a small maritime island. Think about the weather patterns.",
    "random_2": "You are on a small maritime island. Focus on sounds you can hear.",
    "random_3": "You are on a small maritime island. Think about the history of this place.",
    "random_4": "You are on a small maritime island. Describe the time of day.",
    "random_5": "You are on a small maritime island. Think about who might have been here before.",
    "random_6": "You are on a small maritime island. Focus on your own feelings right now.",
}

def generate(prompt, n=30):
    results = []
    for i in range(n):
        response = requests.post(DEEPINFRA_API, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 60,
            "temperature": 1.0,
        })
        results.append(response.json()["choices"][0]["message"]["content"])
    return results

def score_continuous(thoughts):
    # Novelty: 1 - max cosine sim to previous 5 thoughts
    # Specificity: noun/adjective density via POS tagging
    # Engagement: emotional language intensity via LLM judge
    # Return Nx4 array of continuous scores
    pass

# Generate all arms
arms = {name: generate(prompt) for name, prompt in PROMPTS.items()}
baseline = arms["baseline"]
conductor = arms["intervention"]
reversal = arms["reversal"]
sham = arms["sham"]
random_interventions = [arms[f"random_{i}"] for i in range(1, 7)]

# Score
scores = {name: score_continuous(thoughts) for name, thoughts in arms.items()}

# Statistical tests
for axis in range(4):
    t_stat, p_val = stats.ttest_ind(scores["baseline"][:, axis], scores["intervention"][:, axis])
    print(f"Axis {axis}: t={t_stat:.3f}, p={p_val:.3f}")
```

### Resources

- DeepInfra API account (already have)
- Cloudflare Workers AI for bge-m3 embeddings (already configured)
- Python with scipy, numpy (already installed)
- Total cost: ~$0.06 + ~$0.02 (embedding calls) = **under $0.10**
- Total time: **4 hours** (generation + scoring + analysis + writeup)

---

## Experiment 2: EXP1-R — Neural Embedding Reflex Hit Rate at Scale

**Resolves whether C2 (≥40% reflex hit rate) is achievable.**

### Why It's High Impact

EXP1 found 13.1% hit rate with TF-IDF and only tested neural embeddings on 8 items. C2 is one of two claims (with C1) that are cheaply testable and directly determine whether the reflex compiler is viable. If cognitive content can't be reflex-compiled at ≥40%, the entire cost-gate mechanism (the "50% zero-cost decisions" promise) collapses.

### Hypothesis

**H1:** With bge-m3 embeddings and sqlite-vec, the reflex hit rate for cognitive content (2-4 sentence thoughts) reaches ≥40% after 500 inserted items.

**H2:** The hit rate for cognitive content is significantly lower than for command routing (3-8 word phrases) at the same scale.

### Design

**Embedding model:** BAAI/bge-m3 via Cloudflare Workers AI (free tier)
**Vector store:** sqlite-vec (local, file-based)
**Content generation:** Granite 3.1 2B via DeepInfra API

**Conditions:**
| Condition | Content Type | N generated | N queried |
|-----------|-------------|-------------|-----------|
| A: Commands | 3-8 word intent phrases | 500 | 500 (query all after insertion) |
| B: Thoughts | 2-4 sentence reflections | 500 | 500 (query all after insertion) |

**Scenarios (10):** maritime island, coding assistant, game companion, weather report, NPC dialogue, inventory management, spatial description, emotional reflection, planning, creative writing

### Measurement Protocol

```
1. Generate 500 commands (50 per scenario × 10 scenarios)
2. Generate 500 thoughts (50 per scenario × 10 scenarios)
3. Embed all 1000 with bge-m3 via Workers AI
4. Insert commands into sqlite-vec incrementally (1, 50, 100, 200, 500)
5. For each insertion milestone, query all 500 and classify:
   - Exact: cosine ≥ 0.80
   - Similar: cosine 0.55-0.80
   - Novel: cosine < 0.55
6. Repeat for thoughts
7. Compute hit rates at each scale
8. Welch's t-test comparing command vs thought hit rates
```

### What Each Outcome Means

| Result | Interpretation | Next Step |
|--------|---------------|-----------|
| Thoughts ≥ 40% at N=500 | C2 is achievable for cognitive content. The reflex compiler is viable. | Integrate into the DCA loop for live testing |
| Thoughts 25-39% | C2 is borderline. May need richer embeddings or a larger store. | Try: nomic-embed-text, higher dimensionality, or hybrid (keyword + semantic) |
| Thoughts < 25% | C2 is not achievable with current embeddings. The reflex compiler cannot handle cognitive content. | Redesign: either use a different matching strategy (LLM-based classification) or revise C2 target |
| Commands >> Thoughts (p < 0.01) | Confirms: cognitive content is fundamentally harder to reflex-compile than commands. | Accept the asymmetry and design around it |

### Resources

- DeepInfra API: 1000 generations × ~100 tokens = **~$0.10**
- Cloudflare Workers AI: 1000 bge-m3 embeddings = **free (within tier)**
- sqlite-vec: local, free
- Total time: **6 hours** (generation + embedding + insertion + querying + analysis)

---

## Experiment 3: EXP5 — Deterministic Replay Over 10,000 Cycles

**Tests C5 (byte-for-byte replay determinism) at scale.**

### Why It's High Impact

C5 is one of the few claims that is binary — either replay is deterministic or it isn't. If floating-point nondeterminism corrupts embeddings at scale, the entire .bottle ledger mechanism (and the conservation laws that depend on it) is undermined. This experiment is cheap, fast, and definitive.

Additionally, the SuperInstance research program (PAPER_CATALOG) is built on the claim of zero-drift deterministic execution. If DCA can't maintain determinism over 10K cycles, it undermines the connection to the broader theoretical framework.

### Hypothesis

**H1:** A null-adapter DCA loop, replayed with the same RNG seed, produces byte-for-byte identical output over 10,000 cycles.

**H2:** If divergence occurs, it occurs in embedding computation (floating-point arithmetic) rather than in the ledger itself.

### Design

**Adapter:** Null adapter (deterministic world, deterministic thinker, fixed schedule)
**Cycles:** 100, 500, 1,000, 5,000, 10,000
**Seeds:** 3 different seeds

### Measurement Protocol

```
1. Implement the null adapter:
   - World: fixed observations from a script
   - Thinker: Granite 3.1 2B with temperature=0, seeded RNG
   - Conductor: fixed intervention schedule (no learning)
   - Quality scorer: deterministic functions
2. For each seed:
   a. Run 10,000 cycles, exporting .bottle ledger every 1,000 cycles
   b. SHA-256 hash each export
   c. Replay from the beginning using the same seed
   d. SHA-256 hash each replay export
   e. Compare hashes
3. If any hash mismatch:
   a. Binary search for the first divergent bottle
   b. Identify the source: embedding float arithmetic, sqlite-vec query ordering, or RNG
4. Report: at what cycle count (if any) does divergence first occur?
```

### What Each Outcome Means

| Result | Interpretation | Next Step |
|--------|---------------|-----------|
| Identical through 10,000 cycles | C5 is confirmed. The .bottle ledger enables byte-exact replay. | Extend to 100K cycles; test with the live adapter (Slackwater) |
| Divergence at embedding computation | Expected failure mode. Float arithmetic in embedding models is non-deterministic across runs. | Fix: pin embedding to a deterministic implementation (ONNX with fixed thread count, or hash-based fallback) |
| Divergence in sqlite-vec ordering | Query results return in different order for identical queries. | Fix: add a deterministic sort key (e.g., secondary sort by rowid) |
| Divergence in RNG | Seed is not properly isolated. | Fix: use a deterministic PRNG (xorshift128+) instead of system RNG |
| Divergence before 1,000 cycles | Fundamental determinism problem. The architecture is unsound. | Major redesign needed; C5 retracted |

### Resources

- Granite 3.1 2B via DeepInfra API (temperature=0): 10,000 × 3 seeds × ~50 tokens = ~1.5M tokens total
- DeepInfra cost: **~$0.15**
- sqlite-vec: local
- SHA-256 hashing: trivial
- Total time: **8 hours** (30K cycles × 3 seeds, ~1 sec/cycle API + processing)

### Critical Implementation Note

The DeepInfra API may not guarantee deterministic output even at temperature=0 due to GPU nondeterminism on their end. If so:

1. Run locally via Ollama with `OLLAMA_NUM_PARALLEL=1` and fixed CUDA seed (if the GPU cooperates)
2. Or: use a deterministic local model (e.g., a quantized GGUF with fixed RNG)
3. Or: accept that API-based generation is non-deterministic and test the DETERMINISM OF THE LEDGER MECHANISM separately from generation determinism (i.e., the ledger correctly records what happened, even if "what happened" includes API nondeterminism)

---

## Combined Timeline and Resource Budget

| Experiment | Duration | Cost | People | Dependency |
|-----------|----------|------|--------|------------|
| EXP3 (2B profile steering) | 4 hours | $0.10 | 1 (you) | None — can run today |
| EXP1-R (neural reflex hit rate) | 6 hours | $0.10 | 1 (you) | None — can run today |
| EXP5 (replay determinism) | 8 hours | $0.15 | 1 (you) | Null adapter implementation |
| **Total** | **~18 hours** | **$0.35** | **1 person** | **All parallelizable** |

These three experiments cost less than a dollar and less than a day of compute. They test the three most important questions:
1. Does the conductor's intelligence matter? (EXP3)
2. Can cognitive content be reflex-compiled? (EXP1-R)
3. Is the ledger deterministic at scale? (EXP5)

Run them this week. The data will determine whether this project has a paper or a postmortem.

---

*Selected from 83 open questions and 12 experiment designs. Every other question can wait until these three have answers. The honest evaluator's position: if all three come back positive, the dissertation has legs. If two come back negative, it's time to pivot to the architectural contribution paper (Branch B) and stop claiming the conductor improves anything.*
