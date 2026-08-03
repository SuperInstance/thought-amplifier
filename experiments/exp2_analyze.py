#!/usr/bin/env python3
"""
Analysis script for Experiment 2: Semantic Gradient Test.
Reads exp2_raw_data.json and produces full statistical analysis.
Also generates the final markdown report.
"""

import json
import os
import math
from datetime import datetime

RAW_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp2_raw_data.json"
REPORT_FILE = "/home/eileen/projects/thought-amplifier/experiments/EXP2_SEMANTIC_GRADIENT.md"

def mean(vals):
    return sum(vals) / len(vals) if vals else 0

def std(vals):
    if len(vals) < 2:
        return 0
    m = mean(vals)
    return math.sqrt(sum((x - m)**2 for x in vals) / (len(vals) - 1))

def t_test(g1, g2):
    """Welch's t-test"""
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return 0, 1.0
    m1, m2 = mean(g1), mean(g2)
    v1 = sum((x - m1)**2 for x in g1) / (n1 - 1)
    v2 = sum((x - m2)**2 for x in g2) / (n2 - 1)
    se = (v1/n1 + v2/n2) ** 0.5
    if se == 0:
        return float('inf') if m1 != m2 else 0, 1.0
    t = (m1 - m2) / se
    df_num = (v1/n1 + v2/n2)**2
    df_den = (v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1)
    df = df_num / df_den if df_den > 0 else n1 + n2 - 2
    # Normal approx p-value (good for df > 30)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return t, p

def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return 0
    m1, m2 = mean(g1), mean(g2)
    v1 = sum((x - m1)**2 for x in g1) / (n1 - 1)
    v2 = sum((x - m2)**2 for x in g2) / (n2 - 1)
    pooled = math.sqrt((v1*(n1-1) + v2*(n2-1)) / (n1 + n2 - 2))
    if pooled == 0:
        return float('inf') if m1 != m2 else 0
    return (m1 - m2) / pooled

def mann_whitney_u(g1, g2):
    """Mann-Whitney U test with normal approximation."""
    n1, n2 = len(g1), len(g2)
    if n1 == 0 or n2 == 0:
        return 0, 1.0
    combined = [(v, 0) for v in g1] + [(v, 1) for v in g2]
    combined.sort(key=lambda x: x[0])
    
    # Assign ranks with tie correction
    ranks = [0] * len(combined)
    i = 0
    tie_correction = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks[k] = avg_rank
        if j - i > 1:
            tie_correction += (j - i) ** 3 - (j - i)
        i = j
    
    r1 = sum(ranks[i] for i in range(len(combined)) if combined[i][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    
    mu = n1 * n2 / 2
    sigma = math.sqrt((n1 * n2 * (n1 + n2 + 1) - tie_correction / 2) / 12)
    if sigma == 0:
        return min(u1, u2), 1.0
    
    z = (u1 - mu) / sigma
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return min(u1, u2), p

def bonferroni(p, n_tests):
    return min(p * n_tests, 1.0)

def main():
    with open(RAW_FILE) as f:
        data = json.load(f)
    
    results = data["results"]
    model = data.get("model", "unknown")
    n_per_phase = data.get("n_per_phase", "?")
    
    phases = ["baseline", "intervention", "reversal", "sham"]
    scores_by_phase = {}
    for p in phases:
        scores_by_phase[p] = [r["scores"] for r in results if r["phase"] == p]
    
    # --- Statistical Analysis ---
    comparisons = [
        ("baseline", "intervention", "Q1: Real intervention improves quality?"),
        ("intervention", "reversal", "Q2: Quality regresses when removed?"),
        ("sham", "intervention", "Q3: Real > sham (not just novelty)?"),
        ("baseline", "sham", "Q4: Sham produces placebo improvement?"),
    ]
    
    axes = ["novelty", "specificity", "engagement", "total"]
    
    analysis = {}
    for a, b, label in comparisons:
        analysis[label] = {}
        for axis in axes:
            va = [s[axis] for s in scores_by_phase[a]]
            vb = [s[axis] for s in scores_by_phase[b]]
            t, tp = t_test(va, vb)
            u, up = mann_whitney_u(va, vb)
            d = cohens_d(va, vb)
            analysis[label][axis] = {
                "mean_a": round(mean(va), 3),
                "mean_b": round(mean(vb), 3),
                "delta": round(mean(vb) - mean(va), 3),
                "t": round(t, 3),
                "t_p": round(tp, 4),
                "u_p": round(up, 4),
                "d": round(d, 3) if abs(d) < 100 else ">100",
                "bonferroni_t": round(bonferroni(tp, 16), 4),  # 4 comparisons x 4 axes = 16 tests
                "bonferroni_u": round(bonferroni(up, 16), 4),
            }
    
    # --- Generate Report ---
    report = f"""# Experiment 2: Semantic Gradient Test

**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Model:** `{model}` (via Ollama, localhost:11434)
**Design:** 4-phase A-B-A-C within-subjects design
**N per phase:** {n_per_phase} thoughts ({n_per_phase * 4} total)
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
"""
    
    for p in phases:
        s = scores_by_phase[p]
        n_m = mean([x["novelty"] for x in s])
        sp_m = mean([x["specificity"] for x in s])
        e_m = mean([x["engagement"] for x in s])
        t_m = mean([x["total"] for x in s])
        n_sd = std([x["novelty"] for x in s])
        sp_sd = std([x["specificity"] for x in s])
        e_sd = std([x["engagement"] for x in s])
        t_sd = std([x["total"] for x in s])
        
        bold = "**" if p == "intervention" else ""
        report += f"| {bold}{p}{bold} | {n_m:.2f} ± {n_sd:.2f} | {sp_m:.2f} ± {sp_sd:.2f} | {e_m:.2f} ± {e_sd:.2f} | {t_m:.2f} ± {t_sd:.2f} |\n"
    
    report += "\n### Full Data\n\n"
    
    for p in phases:
        report += f"#### Phase: {p}\n\n"
        report += "| # | Thought | N | S | E | T |\n|---|---------|---|---|---|---|\n"
        for r in results:
            if r["phase"] != p:
                continue
            thought_short = r["thought"][:120].replace("|", "\\|").replace("\n", " ")
            s = r["scores"]
            report += f"| {r['index']} | {thought_short} | {s['novelty']} | {s['specificity']} | {s['engagement']} | {s['total']} |\n"
        report += "\n"
    
    report += "---\n\n## Statistical Analysis\n\n"
    
    for a, b, label in comparisons:
        report += f"### {label}\n\n"
        report += f"Comparison: **{a}** → **{b}**\n\n"
        report += "| Axis | Mean A | Mean B | Δ | t-stat | p (t-test) | p (Mann-Whitney) | Cohen's d | Sig | Bonf. p |\n"
        report += "|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        
        for axis in axes:
            r = analysis[label][axis]
            sig = "***" if r["t_p"] < 0.001 else "**" if r["t_p"] < 0.01 else "*" if r["t_p"] < 0.05 else "ns"
            report += f"| {axis} | {r['mean_a']:.3f} | {r['mean_b']:.3f} | {r['delta']:+.3f} | {r['t']:+.3f} | {r['t_p']:.4f} | {r['u_p']:.4f} | {r['d']:+.3f} | {sig} | {r['bonferroni_t']:.4f} |\n"
        report += "\n"
    
    report += """---

## Interpretation

### Key Questions

**Q1: Does the real intervention improve quality?**
"""
    
    q1 = analysis["Q1: Real intervention improves quality?"]
    q1_total = q1["total"]
    if q1_total["delta"] > 0 and q1_total["t_p"] < 0.05:
        report += f"Yes. Total quality improved from {q1_total['mean_a']:.2f} to {q1_total['mean_b']:.2f} (Δ={q1_total['delta']:+.2f}, t={q1_total['t']:.2f}, p={q1_total['t_p']:.4f}, d={q1_total['d']:.2f}).\n"
    elif q1_total["delta"] > 0:
        report += f"Trend toward improvement ({q1_total['mean_a']:.2f} → {q1_total['mean_b']:.2f}, Δ={q1_total['delta']:+.2f}) but **not significant** (p={q1_total['t_p']:.4f}).\n"
    else:
        report += f"**No improvement detected.** Delta = {q1_total['delta']:+.2f} (p={q1_total['t_p']:.4f}).\n"
    
    report += "\n**Q2: Does quality regress when the intervention is removed?**\n"
    q2 = analysis["Q2: Quality regresses when removed?"]
    q2_total = q2["total"]
    if q2_total["delta"] < 0 and q2_total["t_p"] < 0.05:
        report += f"Yes. Quality dropped from {q2_total['mean_a']:.2f} to {q2_total['mean_b']:.2f} when reverting to the neutral prompt (Δ={q2_total['delta']:+.2f}, p={q2_total['t_p']:.4f}).\n"
    elif q2_total["delta"] < 0:
        report += f"Trend toward regression ({q2_total['mean_a']:.2f} → {q2_total['mean_b']:.2f}) but not significant (p={q2_total['t_p']:.4f}).\n"
    else:
        report += f"**No regression detected** when removing the intervention (Δ={q2_total['delta']:+.2f}, p={q2_total['t_p']:.4f}).\n"
    
    report += "\n**Q3: Is the real intervention distinguishable from the sham?**\n"
    q3 = analysis["Q3: Real > sham (not just novelty)?"]
    q3_total = q3["total"]
    if q3_total["delta"] > 0 and q3_total["t_p"] < 0.05:
        report += f"Yes. The real intervention ({q3_total['mean_b']:.2f}) significantly outperforms the sham ({q3_total['mean_a']:.2f}) (Δ={q3_total['delta']:+.2f}, p={q3_total['t_p']:.4f}, d={q3_total['d']:.2f}).\n"
    elif q3_total["delta"] > 0:
        report += f"The real intervention is numerically better ({q3_total['mean_a']:.2f} → {q3_total['mean_b']:.2f}) but **not significantly** (p={q3_total['t_p']:.4f}). Cannot distinguish from placebo.\n"
    else:
        report += f"**No difference between real and sham** (Δ={q3_total['delta']:+.2f}, p={q3_total['t_p']:.4f}). The intervention content provides no measurable benefit over a vacuous prompt.\n"
    
    report += "\n**Q4: Does the sham produce a placebo effect?**\n"
    q4 = analysis["Q4: Sham produces placebo improvement?"]
    q4_total = q4["total"]
    if q4_total["delta"] > 0 and q4_total["t_p"] < 0.05:
        report += f"Yes. Even the vacuous sham prompt improved quality ({q4_total['mean_a']:.2f} → {q4_total['mean_b']:.2f}, Δ={q4_total['delta']:+.2f}, p={q4_total['t_p']:.4f}), confirming a **novelty/placebo effect**.\n"
    elif q4_total["delta"] > 0:
        report += f"Trend toward placebo effect ({q4_total['mean_a']:.2f} → {q4_total['mean_b']:.2f}, Δ={q4_total['delta']:+.2f}) but not significant (p={q4_total['t_p']:.4f}).\n"
    else:
        report += f"No placebo effect detected (Δ={q4_total['delta']:+.2f}, p={q4_total['t_p']:.4f}).\n"
    
    # --- Verdict ---
    report += "\n---\n\n## Verdict\n\n"
    
    # Determine overall verdict
    real_improves = q1_total["delta"] > 0 and q1_total["t_p"] < 0.05
    sham_indistinguishable = q3_total["t_p"] >= 0.05
    placebo_exists = q4_total["delta"] > 0 and q4_total["t_p"] < 0.05
    regression_confirmed = q2_total["delta"] < 0 and q2_total["t_p"] < 0.05
    
    if real_improves and not sham_indistinguishable:
        verdict = "SEMANTIC GRADIENT IS REAL (with caveats)"
        explanation = f"The directed prompt significantly improved quality beyond baseline, AND this improvement was distinguishable from a sham intervention. The 'semantic gradient' is not merely a novelty effect. However, this does not establish it as a *new optimization paradigm* — it simply demonstrates that better prompts produce better output, which is the foundational assumption of prompt engineering, OPRO, DSPy, and TextGrad."
    elif real_improves and sham_indistinguishable:
        verdict = "EFFECT IS REAL BUT INDISTINGUISHABLE FROM PLACEBO"
        explanation = f"The directed prompt improved quality, but so did the sham. The intervention's content provides no measurable benefit beyond the novelty of any prompt change. This supports the critique that the 'semantic gradient' is simply REINFORCE/noise — any perturbation to the system produces transient improvement."
    elif not real_improves:
        verdict = "SEMANTIC GRADIENT IS NOT DETECTABLE"
        explanation = "The directed prompt did not produce a statistically significant improvement over baseline. There is no evidence that prompt modification improves thought quality in this setting."
    else:
        verdict = "INCONCLUSIVE"
        explanation = "The results do not clearly support or refute the semantic gradient claim."
    
    if placebo_exists:
        explanation += f" Critically, the sham intervention ALSO produced significant improvement over baseline, confirming the existence of a novelty/placebo effect that the DCA architecture's sham arm is designed to control for. This validates the sham-arm design as methodologically necessary."
    
    if regression_confirmed:
        explanation += f" The reversal phase confirmed that quality regressed when the intervention was removed, demonstrating the effect is prompt-dependent (not a permanent learning gain)."
    
    report += f"### {verdict}\n\n{explanation}\n\n"
    
    report += """### What This Means for DCA

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
"""
    
    with open(RAW_FILE) as f:
        raw_json = f.read()
    report += raw_json
    
    report += "\n```\n\n</details>\n"
    
    # Write report
    with open(REPORT_FILE, "w") as f:
        f.write(report)
    
    print(f"Report written to {REPORT_FILE}")
    print(f"Analysis complete.")

if __name__ == "__main__":
    main()
