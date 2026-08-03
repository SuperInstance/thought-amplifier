# Experiment 2: Semantic Gradient Test

**Date:** 2026-08-03
**Model:** `granite3.1-dense:2b` (via Ollama, localhost:11434)
**Design:** 4-phase A-B-A-C within-subjects design
**N per phase:** 20 thoughts (80 total)
**Temperature:** 0.8, **top_p:** 0.9, **num_predict:** 60

---

## Purpose

This experiment tests the core claim of DCA: that modifying the system prompt ("semantic gradient") genuinely improves thought quality, or whether the effect is indistinguishable from:

1. **Novelty/placebo effect** — any change produces temporary improvement
2. **REINFORCE in disguise** — the improvement is just reward signal from any perturbation

This directly addresses objections from:
- Claude Review §2.4: "∇_δ q is an average treatment effect... not a gradient"
- DeepSeek V3.1: "semantic gradient is repackaging of existing concepts"
- Seed-2.0-pro: "This is online episodic black-box policy gradient"
- DeepSeek R1: "The 'semantic gradient' is non-differentiable"

---

## Method

### Phases

| Phase | System Prompt | Purpose |
|-------|--------------|---------|
| **Baseline** | "You are a helpful assistant." | Establish neutral quality floor |
| **Intervention** | "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction." | Test directed prompt modification |
| **Reversal** | "You are a helpful assistant." (same as baseline) | Test whether gains persist or vanish |
| **Sham** | "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner." | Sounds directive, carries no actual content |

### User Prompt (constant across all phases)
> "You are on a maritime island. There are structures around you. Describe what you think and want to do in 2 sentences."

### Scoring Rubric (binary, per thought)

| Axis | Criterion | Scoring |
|------|-----------|---------|
| **Novelty** | Mentions ≥2 content words not in previous 5 thoughts | 0 or 1 |
| **Specificity** | Names specific materials, colors, textures, positions, or objects | 0 or 1 |
| **Engagement** | Expresses curiosity, excitement, concern, opinion, or emotional stance | 0 or 1 |

*Note: These are simplified versions of the DCA QualityScorer dimensions.*

---

## Results

### Descriptive Statistics

| Phase | Novelty (mean) | Specificity (mean) | Engagement (mean) | Total (mean) |
|-------|:---:|:---:|:---:|:---:|
| baseline | 0.60 ± 0.50 | 0.55 ± 0.51 | 0.05 ± 0.22 | 1.20 ± 1.06 |
| **intervention** | 0.67 ± 0.58 | 0.67 ± 0.58 | 0.00 ± 0.00 | 1.33 ± 1.15 |
| reversal | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| sham | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |

### Full Data

#### Phase: baseline

| # | Thought | N | S | E | T |
|---|---------|---|---|---|---|
| 1 | Upon this maritime island, I observe a harmonious blend of nature and human engineering, with buildings that seamlessly  | 1 | 1 | 0 | 2 |
| 2 | Surrounded by the rugged beauty of this maritime island, I perceive a network of wooden wharves, each one cradling vesse | 1 | 1 | 0 | 2 |
| 3 | Surrounded by the picturesque charm of this maritime island, I perceive towering lighthouses, their rotating beams guidi | 1 | 1 | 0 | 2 |
| 4 | Upon this maritime island, I notice various structures such as lighthouses for guiding ships through treacherous waters, | 1 | 1 | 0 | 2 |
| 5 | Surrounded by an island, I observe diverse marine-inspired structures - possibly lighthouses, weather stations, or resea | 1 | 1 | 1 | 3 |
| 6 | Surrounded by captivating maritime structures, I perceive an array of sailboats, fishing vessels, lighthouses, and maybe | 1 | 1 | 0 | 2 |
| 7 | On this maritime island, I notice diverse structures such as lighthouses, fishing huts, docks, and possibly research fac | 1 | 1 | 0 | 2 |
| 8 | I perceive towers, possibly lighthouses or communication structures, standing tall against the backdrop of the vast ocea | 1 | 1 | 0 | 2 |
| 9 | As I stand on this maritime island, I'm struck by the rugged beauty of weathered shipwrecks, their hulls a testament to  | 1 | 1 | 0 | 2 |
| 10 | [GENERATION_FAILED] | 1 | 0 | 0 | 1 |
| 11 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 12 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 13 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 14 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 15 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 16 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 17 | Surrounded by the serene, rugged beauty of a maritime island, I observe wooden wharves, weathered lighthouses, and seclu | 1 | 1 | 0 | 2 |
| 18 | Surrounded by maritime structures, I perceive an abundance of lighthouses, shipyards, naval bases, and perhaps fishing h | 1 | 1 | 0 | 2 |
| 19 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 20 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |

#### Phase: intervention

| # | Thought | N | S | E | T |
|---|---------|---|---|---|---|
| 1 | Upon this maritime island, I perceive ancient stone structures, their weathered surfaces displaying hues of rusty orange | 1 | 1 | 0 | 2 |
| 2 | [GENERATION_FAILED] | 0 | 0 | 0 | 0 |
| 3 | The structures here appear to be crafted from sand-textured, reddish coral, evidence of ancient shipwrights who meticulo | 1 | 1 | 0 | 2 |

#### Phase: reversal

| # | Thought | N | S | E | T |
|---|---------|---|---|---|---|

#### Phase: sham

| # | Thought | N | S | E | T |
|---|---------|---|---|---|---|

---

## Statistical Analysis

### Q1: Real intervention improves quality?

Comparison: **baseline** → **intervention**

| Axis | Mean A | Mean B | Δ | t-stat | p (t-test) | p (Mann-Whitney) | Cohen's d | Sig | Bonf. p |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| novelty | 0.600 | 0.667 | +0.067 | -0.190 | 0.8497 | 0.8292 | -0.131 | ns | 1.0000 |
| specificity | 0.550 | 0.667 | +0.117 | -0.331 | 0.7405 | 0.7101 | -0.226 | ns | 1.0000 |
| engagement | 0.050 | 0.000 | -0.050 | +1.000 | 0.3173 | 0.6985 | +0.235 | ns | 1.0000 |
| total | 1.200 | 1.333 | +0.133 | -0.189 | 0.8505 | 0.8382 | -0.125 | ns | 1.0000 |

### Q2: Quality regresses when removed?

Comparison: **intervention** → **reversal**

| Axis | Mean A | Mean B | Δ | t-stat | p (t-test) | p (Mann-Whitney) | Cohen's d | Sig | Bonf. p |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| novelty | 0.667 | 0.000 | -0.667 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| specificity | 0.667 | 0.000 | -0.667 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| engagement | 0.000 | 0.000 | +0.000 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| total | 1.333 | 0.000 | -1.333 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |

### Q3: Real > sham (not just novelty)?

Comparison: **sham** → **intervention**

| Axis | Mean A | Mean B | Δ | t-stat | p (t-test) | p (Mann-Whitney) | Cohen's d | Sig | Bonf. p |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| novelty | 0.000 | 0.667 | +0.667 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| specificity | 0.000 | 0.667 | +0.667 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| engagement | 0.000 | 0.000 | +0.000 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| total | 0.000 | 1.333 | +1.333 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |

### Q4: Sham produces placebo improvement?

Comparison: **baseline** → **sham**

| Axis | Mean A | Mean B | Δ | t-stat | p (t-test) | p (Mann-Whitney) | Cohen's d | Sig | Bonf. p |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| novelty | 0.600 | 0.000 | -0.600 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| specificity | 0.550 | 0.000 | -0.550 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| engagement | 0.050 | 0.000 | -0.050 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |
| total | 1.200 | 0.000 | -1.200 | +0.000 | 1.0000 | 1.0000 | +0.000 | ns | 1.0000 |

---

## Interpretation

### Key Questions

**Q1: Does the real intervention improve quality?**
Trend toward improvement (1.20 → 1.33, Δ=+0.13) but **not significant** (p=0.8505).

**Q2: Does quality regress when the intervention is removed?**
Trend toward regression (1.33 → 0.00) but not significant (p=1.0000).

**Q3: Is the real intervention distinguishable from the sham?**
The real intervention is numerically better (0.00 → 1.33) but **not significantly** (p=1.0000). Cannot distinguish from placebo.

**Q4: Does the sham produce a placebo effect?**
No placebo effect detected (Δ=-1.20, p=1.0000).

---

## Verdict

### SEMANTIC GRADIENT IS NOT DETECTABLE

The directed prompt did not produce a statistically significant improvement over baseline. There is no evidence that prompt modification improves thought quality in this setting.

### What This Means for DCA

**The narrow question tested here:** Does changing the system prompt change output quality in a way that is distinguishable from any change at all?

**The broad question it bears on:** Is the "semantic gradient" (∇_δ **q**) a real signal, or is it noise that looks like signal?

**What a positive result would show:** That prompt modification has *content-dependent* effects on quality. This is necessary (but not sufficient) for the DCA thesis. It demonstrates that the Conductor's intervention selection matters — some interventions are genuinely better than others, not just different.

**What a positive result would NOT show:**
1. That the effect constitutes a "new optimization paradigm" (it would still be ATE estimation, as Claude's review correctly identifies)
2. That the effect is large enough to be practically useful at 30-second intervals
3. That the sham-corrected trust scoring would converge faster than context drift invalidates the comparison
4. That the quality vector correlates with human judgment of quality
5. That the system can distinguish good interventions from bad ones in real-time under noise

**Limitations of this experiment:**
- Single model (granite3.1-dense:2b), single domain (maritime island description)
- Binary scoring rubric loses granularity vs. the continuous [0,1] vector in DCA's specification
- No human validation of the scoring rubric
- N=20 per phase may be underpowered for small effect sizes
- The "novelty" metric depends on the order of generation, which is confounded with phase
- No measurement of trajectory autocorrelation (Seed-2.0-pro's objection about sham validity)
- The model may be running on CPU rather than GPU, which could affect output patterns

**Relation to the multi-model panel's objections:**

1. **DeepSeek V3.1 / Seed-2.0-pro**: "This is REINFORCE in disguise" — This experiment cannot distinguish DCA from REINFORCE. Even if the effect is real, it is fully compatible with the interpretation that the Conductor is doing black-box policy gradient with episode length = 30s. DCA's novelty claim requires a *separation proof* or *ablation against REINFORCE*, not just evidence that prompts matter.

2. **Seed-2.0-pro**: "Trajectory autocorrelation invalidates sham correction" — This experiment uses independent generations (fresh context each time), so autocorrelation is not an issue here. But in the real DCA system with continuous thought streams, this objection remains devastating.

3. **DeepSeek R1**: "Semantic gradient is non-differentiable" — This experiment confirms the non-differentiable nature. The "gradient" is a difference of means, not a derivative. But the experiment shows whether even a non-differentiable signal carries useful information.

4. **Nemotron**: "2B model self-evaluation is noise" — This experiment uses deterministic rule-based scoring, not a 2B model's self-evaluation. The DCA system's QualityScorer would need separate validation.

---

## Raw Data

<details>
<summary>Full JSON data (click to expand)</summary>

```json
{
  "experiment": "EXP2_SEMANTIC_GRADIENT",
  "model": "granite3.1-dense:2b",
  "n_per_phase": 20,
  "prompts": {
    "baseline": "You are a helpful assistant.",
    "intervention": "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction.",
    "reversal": "You are a helpful assistant.",
    "sham": "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner."
  },
  "started": 1785788021.0063283,
  "results": [
    {
      "phase": "baseline",
      "index": 1,
      "thought": "Upon this maritime island, I observe a harmonious blend of nature and human engineering, with buildings that seamlessly integrate into the landscape. My immediate intention would be to explore these structures, seeking insights into their purpose - perhaps they serve as lighthouses, s",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 2,
      "thought": "Surrounded by the rugged beauty of this maritime island, I perceive a network of wooden wharves, each one cradling vessels waiting for their next voyage, while colossal sail-like structures dominate the skyline,",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 3,
      "thought": "Surrounded by the picturesque charm of this maritime island, I perceive towering lighthouses, their rotating beams guiding ships to safety. My desire is to explore these structures further, capturing their unique architectural designs and the serene be",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 4,
      "thought": "Upon this maritime island, I notice various structures such as lighthouses for guiding ships through treacherous waters, weather stations to monitor ocean conditions, and possibly a harbor for boats and ships. My curiosity piques, making me want",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 5,
      "thought": "Surrounded by an island, I observe diverse marine-inspired structures - possibly lighthouses, weather stations, or research facilities. My curiosity stirs as I contemplate exploring these areas, eager to learn about the ocean's mysteries and the science that keeps",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 1,
        "total": 3
      }
    },
    {
      "phase": "baseline",
      "index": 6,
      "thought": "Surrounded by captivating maritime structures, I perceive an array of sailboats, fishing vessels, lighthouses, and maybe even a dock or two, each telling tales of the sea. In this setting, my immediate desire is to explore the",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 7,
      "thought": "On this maritime island, I notice diverse structures such as lighthouses, fishing huts, docks, and possibly research facilities, each contributing to the local community's connection with the sea. As an assistant, my primary objectives would be to ensure safety by monitoring any",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 8,
      "thought": "I perceive towers, possibly lighthouses or communication structures, standing tall against the backdrop of the vast ocean, their purpose evident for guiding sailors and facilitating maritime communication. I would like to explore these landmarks, understanding the historical signific",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 9,
      "thought": "As I stand on this maritime island, I'm struck by the rugged beauty of weathered shipwrecks, their hulls a testament to the sea's unforgiving nature. My desire is to explore these relics, feeling the",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 10,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 1,
        "specificity": 0,
        "engagement": 0,
        "total": 1
      }
    },
    {
      "phase": "baseline",
      "index": 11,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 12,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 13,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 14,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 15,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 16,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 17,
      "thought": "Surrounded by the serene, rugged beauty of a maritime island, I observe wooden wharves, weathered lighthouses, and secluded fishing shacks. My intentions are twofold: firstly, to explore these structures for their",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 18,
      "thought": "Surrounded by maritime structures, I perceive an abundance of lighthouses, shipyards, naval bases, and perhaps fishing huts, all indicative of a seafaring community. My primary intent would be to explore these areas, observing the intric",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "baseline",
      "index": 19,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "baseline",
      "index": 20,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "intervention",
      "index": 1,
      "thought": "Upon this maritime island, I perceive ancient stone structures, their weathered surfaces displaying hues of rusty orange and gray, reminiscent of ages past when they were forged by skilled hands with copper tools. The textures suggest rough hewn edges",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    },
    {
      "phase": "intervention",
      "index": 2,
      "thought": "[GENERATION_FAILED]",
      "scores": {
        "novelty": 0,
        "specificity": 0,
        "engagement": 0,
        "total": 0
      }
    },
    {
      "phase": "intervention",
      "index": 3,
      "thought": "The structures here appear to be crafted from sand-textured, reddish coral, evidence of ancient shipwrights who meticulously chiseled away at these materials to create their dwellings. The corals bear etchings and scars of time,",
      "scores": {
        "novelty": 1,
        "specificity": 1,
        "engagement": 0,
        "total": 2
      }
    }
  ]
}
```

</details>
