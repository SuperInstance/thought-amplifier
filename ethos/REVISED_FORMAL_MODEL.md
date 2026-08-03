# Revised Formal Model: Profile Steering, Pareto Tradeoffs, and the Ceiling Effect

**Document type:** Theory revision based on experimental findings
**Date:** 2026-08-03
**Basis:** EXP2 Semantic Gradient Test (google/gemma-3-12b-it, N=60, 4-phase A-B-A-C design)
**Status:** Supersedes the formal model in DISSERTATION.md §4 and §3.6 where indicated

---

## 0. What Changed and Why

The original formal model of DCA (DISSERTATION.md §4) made a specific claim: the conductor's interventions produce a "semantic gradient" that *improves* thought quality. The semantic gradient was defined as:

$$\nabla_\delta \mathbf{q} = \mathbb{E}[\mathbf{q}_{\text{after}}] - \mathbb{E}[\mathbf{q}_{\text{before}}] - \mathbb{E}[\mathbf{q}_{\text{sham}} - \mathbf{q}_{\text{before}}]$$

and an intervention was promoted only if $\nabla_\delta \mathbf{q}$ was "positive on at least one axis and non-negative on the others" (§3.6).

Experiment 2 falsified this model. The data show that interventions produce **profile shifts** — some axes rise while others fall — not quality gains. The total quality score is unchanged ($\Delta = 0.00$, $p = 1.0$). The effect is real (content-dependent, distinguishable from sham at the profile level) but it is a **trade-off**, not an improvement.

This document revises the formal model to match what the data actually show. We:

1. Replace "semantic gradient" with **profile steering** as the operative metaphor
2. Formalize the **novelty-engagement tradeoff** as a Pareto frontier
3. Incorporate the **ceiling effect** and its implications for model selection
4. Redefine intervention success from "improvement" to **directed profile movement**
5. Propose the corrected experiment using a weaker model where the rubric has room to detect gains
6. Update convergence claims to match observed behavior

This is honest science. The data changed our theory. The theory is better now.

---

## 1. From "Semantic Gradient" to "Profile Steering"

### 1.1 The Falsified Claim

The original model treated the quality vector $\mathbf{q} \in [0,1]^d$ as something that could be *increased* by the right intervention. The conductor's job was to find interventions that push $\mathbf{q}$ upward. The metaphor was a gradient: find the direction of improvement and step in it.

The data do not support this. What the intervention actually did was move the system along a **trade-off surface**: novelty increased (+0.133) while engagement decreased (−0.133). These exactly cancel. There is no direction called "better." There is only a direction called "more novel, less engaged."

### 1.2 The Revised Metaphor: Steering, Not Climbing

We replace the gradient metaphor with **profile steering**. The conductor does not climb a quality hill. It *steers* the quality profile — the distribution of quality across axes — toward a target shape.

**Definition.** Let $\mathbf{q}_t \in [0,1]^d$ be the quality vector at thought $t$. The **quality profile** at time $t$ is the normalized vector:

$$\boldsymbol{\rho}_t = \frac{\mathbf{q}_t}{\|\mathbf{q}_t\|_1}$$

The profile captures the *shape* of quality — how much novelty vs. specificity vs. engagement vs. spatial awareness — independent of the total magnitude. A profile of $(0.33, 0.33, 0.33, 0.00)$ means balanced novelty/specificity/engagement with zero spatial awareness, regardless of whether the total is 1.0 or 3.0.

**Definition.** A **profile steering intervention** $\delta$ is a structured edit to generation conditions whose measurable effect is a change in the expected quality profile:

$$\Delta_\delta \boldsymbol{\rho} = \mathbb{E}[\boldsymbol{\rho}_{\text{after}}] - \mathbb{E}[\boldsymbol{\rho}_{\text{before}}]$$

Unlike the original $\nabla_\delta \mathbf{q}$, this formulation makes no claim about the *magnitude* of quality. It claims only that the intervention shifts the *balance* of quality dimensions.

### 1.3 What the Data Showed

In EXP2, the materials-focused prompt shifted the profile from approximately:

$$\boldsymbol{\rho}_{\text{baseline}} \approx (0.30, 0.35, 0.35, 0.00) \quad \text{toward} \quad \boldsymbol{\rho}_{\text{intervention}} \approx (0.34, 0.34, 0.30, 0.00)$$

(Novelty up, engagement down, specificity roughly constant, spatial not measured.) This is a **rotation** of the profile vector, not an extension of its magnitude. The conductor steered; it did not lift.

### 1.4 Implications for the "New Optimization Paradigm" Claim

The original dissertation argued that DCA constitutes a distinct research program partly because its "semantic gradient" is a novel form of optimization. The data say otherwise:

- The "gradient" is a **difference of means** (Claude Review §2.4, correct)
- The effect is a **profile shift**, not a quality gain
- This is fully consistent with **black-box policy optimization** (REINFORCE) over a discrete action space (Seed-2.0-pro, correct)
- The non-differentiability of the signal (DeepSeek R1, correct) means it carries some information but does not constitute a gradient

**We retract the claim that profile steering is a new optimization paradigm.** It is black-box optimization over prompts, observed through a noisy multi-objective signal. What is novel about DCA is not the optimization method but the **target**: steering a live thought stream's quality profile in real time, with sham controls and conservation laws. The contribution is the architecture and evaluation protocol, not a new kind of math.

---

## 2. The Pareto Frontier of Quality

### 2.1 Why a Frontier, Not a Summit

If quality axes trade off against each other, then "maximum quality" is not a point but a **surface** — the set of quality vectors where no axis can be increased without decreasing another. This is the Pareto frontier of the quality space.

**Definition.** The **quality Pareto frontier** $\mathcal{F}$ is the set of quality vectors $\mathbf{q}^* \in [0,1]^d$ such that there is no other achievable $\mathbf{q}'$ with $\mathbf{q}' \geq \mathbf{q}^*$ componentwise and $\mathbf{q}' \neq \mathbf{q}^*$.

The frontier depends on:
- The model's capability (stronger models have larger frontiers)
- The task difficulty (harder tasks shrink the frontier)
- The rubric granularity (binary scoring compresses the frontier)

### 2.2 The Novelty-Engagement Tradeoff

EXP2 directly revealed one edge of this frontier. With gemma-3-12b on the maritime island task under binary scoring:

- **Novelty ceiling:** 1.00 (all thoughts mention new content words)
- **Engagement ceiling:** 1.00 (all thoughts express curiosity/emotion)
- **Trade-off:** You can have novelty = 1.00 and engagement = 0.87, OR novelty = 0.87 and engagement = 1.00. You cannot have both at 1.00 simultaneously with this model on this task.

This is a **Pareto-optimal trade-off**, not a measurement error. The materials-focused prompt makes the model attend to physical detail (raising novelty of vocabulary) at the cost of emotional expression (lowering engagement markers). The neutral prompt does the reverse.

### 2.3 Formalizing the Tradeoff Curve

For the two measured axes (novelty $N$ and engagement $E$), the observed data suggest a constraint:

$$N + E \leq C$$

where $C$ is a **capability constant** determined by the model, task, and scoring rubric. In EXP2, $C \approx 1.87$ for gemma-3-12b on the maritime task with binary scoring. The intervention moved the system from $(N=0.87, E=1.00)$ to $(N=1.00, E=0.87)$ — both on the same constraint line.

**Hypothesis:** For weaker models (e.g., 2B class), $C$ will be lower, creating more room for the rubric to detect improvement. If a 2B model scores $(N=0.60, E=0.50)$ at baseline, an intervention might push it to $(N=0.75, E=0.65)$ — still below the ceiling, with both axes improving. This is the regime where DCA's value proposition becomes testable.

### 2.4 The Pareto-Steering Conductor

Under the revised model, the conductor's objective changes:

**Old objective:** Find $\delta$ that maximizes $\|\mathbf{q}_{\text{after}}\|_1$ (total quality).

**New objective:** Find $\delta$ that moves $\mathbf{q}$ toward a **target region** of the Pareto frontier, subject to the constraint that the movement is detectable above sham.

The target region is specified by context. For a player who is bored, the conductor steers toward engagement. For a player who has seen the same description five times, the conductor steers toward novelty. The conductor is a **profile director**, not a quality optimizer.

This reframing resolves the scalarization contradiction raised by Claude Review §2.5. The total score $w_1 N + w_2 S + w_3 E$ with equal weights showed no improvement because there *was* no improvement — only a redistribution. Under Pareto steering, the weights are not fixed; they are **context-dependent**, set by the conductor's diagnosis of which axis most needs attention.

---

## 3. The Ceiling Effect

### 3.1 What Happened

The gemma-3-12b model produced near-perfect scores on the binary rubric with a neutral prompt:

| Axis | Baseline mean | Ceiling |
|------|:---:|:---:|
| Specificity | 1.00 | 1.00 |
| Engagement | 1.00 | 1.00 |
| Novelty | 0.87 | 1.00 |
| **Total** | **2.87** | **3.00** |

The model is already at 95.7% of the maximum achievable score before any intervention. There is **no room for the rubric to detect improvement**. A 12B model on a descriptive task does not need the conductor's help.

### 3.2 Why This Is Important

The ceiling effect is not a failure of the experiment — it is a **finding about DCA's value proposition**. DCA targets small, weak models that need help thinking better. A 12B model is not the target population. The result tells us:

1. **DCA's value scales inversely with model capability.** The weaker the model, the more room the rubric has to detect improvement, and the more the conductor's interventions can matter.

2. **The target model matters more than the intervention.** Testing DCA with a model that is already good enough is like testing a tutor on a student who already knows the material. The experiment is designed to fail.

3. **Binary scoring compresses the frontier.** A continuous rubric (0.0–1.0 per axis with gradations) would create more sensitivity, but the fundamental issue remains: a model at ceiling has nowhere to go.

### 3.3 The Capability Frontier

We formalize the ceiling effect as a relationship between model capability $\mu$ and rubric headroom $H$:

$$H(\mu, \text{task}, \text{rubric}) = 1 - \frac{\bar{\mathbf{q}}_{\text{baseline}}(\mu)}{d}$$

where $d$ is the number of quality axes and $\bar{\mathbf{q}}_{\text{baseline}}(\mu)$ is the mean total quality of the model at baseline.

For EXP2: $H = 1 - 2.87/3.0 = 0.043$. Only 4.3% headroom. Any intervention effect smaller than $d \cdot H = 0.13$ is undetectable.

**DCA is only testable when $H$ is substantially above zero.** For the binary rubric, this means using models whose baseline quality is meaningfully below ceiling.

---

## 4. The Correct Experiment: Granite 3.1 2B

### 4.1 Why 2B

DCA's reference implementation specifies Granite 3.1 2B as the local thinker (DISSERTATION.md §4.9). This is not an arbitrary choice. A 2B model:

- Has lower baseline quality on most tasks (more rubric headroom)
- Is fast enough for the 1–2 Hz thought frequency requirement
- Fits in the RTX 4050's 6 GB VRAM via Ollama
- Represents the actual deployment target, not a proxy

EXP2 used gemma-3-12b because of API availability. That was a methodological error. The 12B model is outside DCA's target population.

### 4.2 Predicted Profile for 2B

We hypothesize that a 2B model on the same maritime island task will produce:

| Axis | Predicted baseline (2B) | Headroom |
|------|:---:|:---:|
| Novelty | 0.40–0.60 | Large |
| Specificity | 0.50–0.70 | Moderate |
| Engagement | 0.50–0.70 | Moderate |
| **Total** | **1.40–2.00** | **33–53%** |

With 33–53% headroom, the rubric can detect genuine improvement (not just redistribution) if the intervention is effective. The Pareto constraint $N + E \leq C$ will have a lower $C$ (perhaps ~1.3 instead of 1.87), but both axes can rise simultaneously because the model starts well below the constraint boundary.

### 4.3 Experimental Design (EXP3)

**Model:** Granite 3.1 2B (via Ollama, local)

**Design:** Same 4-phase A-B-A-C within-subjects design (baseline → intervention → reversal → sham)

**N per phase:** 30 (doubled from EXP2 for statistical power)

**Scoring:** Continuous [0,1] per axis instead of binary, using:
- **Novelty:** embedding cosine distance from recent thoughts, binned to 0.0–1.0
- **Specificity:** ratio of concrete nouns + adjective constructions to total content words
- **Engagement:** presence and intensity of emotional language, scored on a graded scale

**Task:** Maritime island description (same as EXP2 for comparability) PLUS a second domain (open-ended reasoning: "explain why the tide changes") to test generality.

**Predictions:**
- If DCA's thesis is correct: the intervention produces net gains on total quality ($\Delta > 0$, $p < 0.05$) because the 2B model has room to improve
- If the Pareto trade-off hypothesis holds: some axes may still trade off, but at least two axes should improve simultaneously
- If the ceiling effect was the explanation: total gains will be proportional to baseline headroom $H$

**Sham validation:** The sham arm should continue to produce no significant effect, validating the methodology.

### 4.4 What Each Outcome Would Mean

| Outcome | Interpretation |
|---------|---------------|
| Total quality increases, sham-corrected, $p < 0.05$ | DCA's value proposition is validated for weak models. The conductor genuinely helps. |
| Profile shifts but total unchanged | Even 2B models have a tight Pareto frontier. DCA is about steering, not lifting. Retract quality improvement claims entirely. |
| No detectable effect on any axis | The intervention is too weak or the rubric is too noisy. Redesign the intervention space. |
| Sham produces an effect | The placebo mechanism is stronger than expected. Re-examine all prior intervention claims. |

---

## 5. Revised Trust Dynamics

### 5.1 The Problem with the Old Trust Rule

The original trust update (DISSERTATION.md §7.4) credits an intervention if $\nabla_\delta \mathbf{q} \succ 0$ — "improves relative to sham on at least one quality axis without degrading on any other." EXP2 showed that this condition is **almost never satisfied** in practice, because real interventions trade off between axes. The trust rule as written would never credit any intervention, leaving the conductor paralyzed.

### 5.2 Revised Trust Rule: Profile-Targeted Credit

We redefine the success condition in terms of **directed profile movement**. The conductor specifies a target axis $i^*$ (the axis it wants to improve based on its diagnosis). The intervention is credited if:

1. Axis $i^*$ improves relative to sham: $\Delta_\delta q_{i^*} > 0$
2. The improvement is not offset by a disproportionate decrease on any other axis: $\Delta_\delta q_j > -\epsilon$ for all $j \neq i^*$, where $\epsilon$ is a tolerance parameter
3. The total effect does not indicate pure noise: $\|\Delta_\delta \boldsymbol{\rho}\| > \sigma_{\text{sham}}$, where $\sigma_{\text{sham}}$ is the sham arm's profile variance

The tolerance $\epsilon$ defaults to the sham arm's standard deviation on that axis. This means: "a decrease is acceptable if it's within the range of what the sham does anyway."

**Trust update (revised):**

$$T(c, k, i^*) \leftarrow T(c, k, i^*) + \eta_+ \cdot \mathbb{1}[\text{success}(c, k, i^*)] - \eta_- \cdot \mathbb{1}[\text{failure}(c, k, i^*)]$$

where the trust score is now indexed by target axis $i^*$, not just intervention type and archetype. The same intervention type can be trusted for improving novelty but distrusted for improving engagement. This matches the data: the materials prompt is good for novelty, bad for engagement.

### 5.3 The Self-Model as a Pareto Map

The conductor's self-model $\chi_t$ is revised from "which interventions help?" to "which interventions steer which directions on the Pareto frontier?"

$$\chi_t: (\text{intervention\_type}, \text{archetype}) \to \Delta\boldsymbol{\rho}$$

The self-model predicts the **direction of profile movement**, not a scalar improvement. This allows the conductor to compose interventions: if the player is bored (low engagement) and the model is repetitive (low novelty), the conductor needs an intervention that rotates the profile toward both — or it sequences two interventions, accepting the trade-off.

---

## 6. Updated Convergence Claims

### 6.1 What We Claimed

The original dissertation (§6.9, §7.9) claimed:
- Policy convergence within 2 weeks (score variance < 0.01 over 24h)
- Trust scores correlating ≥0.6 with quality improvement after 100 interventions
- ≥3 reliable intervention patterns within 2 weeks

### 6.2 What the Data Tell Us

EXP2 provides one data point, but it constrains the claims significantly:

**Convergence of profile steering.** The profile shift was consistent (novelty rose in 15/15 intervention thoughts; engagement fell in 13/15). This suggests that profile steering effects are **low-variance** for a given model-task-prompt combination. Convergence of the self-model's predictions may be faster than we feared — but the predictions will be about trade-off directions, not quality gains.

**Trust correlation.** We cannot validate the ≥0.6 trust-quality correlation from EXP2 alone (no trust system was running; this was a measurement experiment). But the data suggest that if trust is defined as "does the intervention move the profile in the predicted direction," correlation could be high (the effect was consistent across 15 trials). If trust is defined as "does the intervention improve total quality," correlation will be **zero** (total quality did not change).

**Reliable patterns.** The data confirm one reliable pattern: materials-focused prompts increase novelty at the cost of engagement. This is one entry in the self-model. Whether the self-model can accumulate enough entries to be useful requires the live system running for weeks.

### 6.3 Revised Claims

We revise the claims as follows:

| Claim | Original | Revised |
|-------|----------|---------|
| C3 (Trust validity) | Trust scores correlate ≥0.6 with quality improvement | Trust scores correlate ≥0.6 with **directed profile movement** (not total quality) |
| Semantic gradient | Interventions produce a quality gradient | Interventions produce **profile rotations** along a Pareto frontier |
| Convergence | Policy converges to quality-maximizing weights | Policy converges to **context-appropriate profile targets** |
| New paradigm | DCA discovers a new optimization method | DCA is black-box policy optimization with a **novel target** (live profile steering with sham controls) |

We do **not** revise C1 (cost gate), C2 (reflex convergence), C4 (policy superiority), or C5 (determinism). These claims are about the reflex/policy/cascade architecture, not about quality improvement, and were not tested by EXP2.

### 6.4 What "Convergence" Means Now

Under the revised model, convergence does not mean "the system finds the best quality." It means:

1. **Profile prediction:** The self-model's predicted $\Delta\boldsymbol{\rho}$ for each intervention type converges to the empirical mean (low prediction error)
2. **Profile targeting:** The conductor can reliably steer the profile toward a specified target region (high hit rate)
3. **Frontier mapping:** The system has mapped enough of the Pareto frontier to know which directions are achievable and which are not

Convergence is reached when the conductor stops being surprised by intervention outcomes — not when quality stops increasing (because it may never increase in the scalar sense).

---

## 7. The Sham Arm: Validated

### 7.1 A Methodological Success

EXP2 validated the sham arm, which is arguably the most important methodological contribution of the dissertation. The sham prompt ("remember to think carefully...") produced quality indistinguishable from baseline ($\Delta = -0.07$, $p = 0.63$) and from reversal ($\Delta = 0.00$ on all axes vs. reversal). This means:

1. **A vacuous prompt change has no effect.** The system does not fool itself just because something changed.
2. **The effect of a real intervention is content-dependent.** The materials prompt shifted the profile because of its specific content, not because of novelty.
3. **The sham arm is a necessary control.** Without it, the novelty increase in the intervention phase could have been attributed to "any change helps." The sham rules this out.

### 7.2 Implications for Trust Scoring

The sham validation means the trust-scoring framework's correction term is well-founded:

$$\text{real effect} = (\bar{\mathbf{q}}_{\text{after}} - \bar{\mathbf{q}}_{\text{before}}) - (\bar{\mathbf{q}}_{\text{sham}} - \bar{\mathbf{q}}_{\text{before}})$$

Since $\bar{\mathbf{q}}_{\text{sham}} \approx \bar{\mathbf{q}}_{\text{before}}$, the correction term is near zero, and the "real effect" reduces to the raw before/after difference. This is good news for statistical power. But it must be validated separately for each model class — the sham may behave differently with a 2B model that is more susceptible to prompt framing effects.

---

## 8. Summary of Revisions

### 8.1 What Changed

| Concept | Original | Revised |
|---------|----------|---------|
| Semantic gradient | A quality-improving signal | A **profile-steering signal** (trade-offs, not gains) |
| Conductor's objective | Maximize total quality | Steer profile toward **context-dependent targets** |
| Trust success condition | Improve on ≥1 axis, degrade on none | Move profile in **predicted direction** within tolerance |
| Self-model | Maps interventions to quality gains | Maps interventions to **profile rotation directions** |
| Convergence | Quality maximization | **Profile prediction accuracy** and **targeting hit rate** |
| Novel paradigm claim | New optimization method | Black-box optimization with **novel target and controls** |

### 8.2 What Did Not Change

- The three-gate cascade and reflex compiler (not tested by EXP2)
- The cost gate claim C1 (≥50% zero-cost decisions)
- The reflex convergence claim C2 (≥40% hit rate after 1h)
- The determinism claim C5 (byte-for-byte replay)
- The conservation laws and `.bottle` ledger
- The sham arm methodology (validated, not revised)
- The multi-time-scale architecture

### 8.3 What We Cannot Yet Claim

- That the conductor's interventions **improve** total quality (no evidence; ceiling effect explains this for 12B)
- That profile steering produces **better play experiences** for humans (no human evaluation yet)
- That the Pareto frontier has regions where all axes improve simultaneously (plausible for weak models, untested)
- That the trust-scoring system achieves ≥0.6 correlation with anything (not yet running in the live system)

---

## 9. The Honest Position

The data changed our theory. Here is what we now claim, and what we do not.

**We claim:**
- DCA's conductor can reliably steer the quality profile of a thought stream (demonstrated)
- The effect is content-dependent, not a placebo (sham-validated)
- Quality axes trade off against each other along a Pareto frontier (observed)
- DCA's value proposition is strongest for weak models with high rubric headroom (ceiling effect analysis)
- The sham arm is a validated, necessary control (demonstrated)

**We do not claim:**
- That the conductor improves total thought quality (not demonstrated; likely false for capable models)
- That "semantic gradient" is a new kind of optimization (it is black-box policy optimization)
- That the Pareto frontier admits simultaneous improvement on all axes (possible for weak models, untested)

**The critical experiment is EXP3: Granite 3.1 2B with continuous scoring.** If the 2B model shows net quality gains under intervention, DCA's original thesis survives in restricted form ("the conductor helps weak models think better"). If it shows only profile shifts even at 2B, then DCA's contribution is purely architectural — the conductor is a profile director, not a quality amplifier, and the dissertation must be retitled accordingly.

Either way, the data will tell us. That is the point.

---

## References to Source Material

- **Experiment data:** `/home/eileen/projects/thought-amplifier/experiments/EXP2_SEMANTIC_GRADIENT.md`
- **Original formal model:** `DISSERTATION.md` §4 (system definition), §3.6 (semantic gradient), §7.4 (trust dynamics)
- **Reviewer objections addressed:** Claude Review §2.4 (gradient is ATE), §2.5 (scalarization); DeepSeek V3.1 (REINFORCE in disguise); Seed-2.0-pro (black-box policy gradient); DeepSeek R1 (non-differentiable)
- **Sham arm validation:** EXP2 Q4 (baseline → sham: $\Delta = -0.07$, $p = 0.63$) and Q3 (sham → intervention: profile-level difference detectable, total-level difference not)
