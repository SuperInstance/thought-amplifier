# Revised Dissertation Outline

**Author:** Ethos (evaluative faculty), synthesized from archaeological survey and EXP2 revision
**Date:** 2026-08-03
**Basis:** REVISED_FORMAL_MODEL.md (profile steering, Pareto frontier, ceiling effect), PAPER_CATALOG.md (80+ papers across 34 repos), EXPERIMENT_EVALUATION.md (EXP1/EXP2 results), STRATEGIC_PRIORITIES.md
**Status:** Replaces the original DISSERTATION_OUTLINE.md. Reflects the Branch B reframing ("cost-bounded, interpretable architecture for continuous LLM-directed agents") as recommended by the strategic assessment.

---

## The Reframing

The original dissertation argued that DCA constitutes a new subfield of AI. The evidence does not support this. What the evidence supports is a more honest and more defensible claim: DCA is a well-engineered architecture for shaping the output of a continuous LLM thought stream, with a validated sham-control methodology and a Pareto-steering mechanism that is real but not yet proven to improve total quality.

This outline reflects that repositioning. The contribution is architectural and methodological, not theoretical.

---

## Part I: Problem and Architecture

### Chapter 1: Introduction
- The problem: LLMs generate thoughts, but nobody shapes the stream
- The analogy: a foreman who directs a worker's attention in real time
- What we claim (revised):
  - C1: ≥50% zero-cost decisions (cost gate)
  - C2: ≥40% reflex hit rate after 1 hour
  - C3: Trust scores correlate ≥0.6 with directed profile movement (not total quality)
  - C4: Evolved policy outperforms hand-tuned weights
  - C5: Byte-for-byte replay determinism
- What we do NOT claim:
  - That the conductor improves total thought quality (not demonstrated)
  - That DCA is a new optimization paradigm (it is black-box policy optimization)
  - That "semantic gradient" is a new kind of math
- **Key revision from original:** dropped "new subfield" framing entirely

### Chapter 2: Background and Related Work
- The seven competing systems (address head-on, not dodge):
  - Voyager (LLM agent with skill library)
  - Reflexion (self-correcting agent)
  - TextGrad (gradient-like optimization over text)
  - DSPy (programmatic prompt optimization)
  - Generative Agents (park simulation)
  - SOAR chunking (1986 — the original reflex compiler)
  - FrugalGPT (cost-bounded LLM routing)
- What DCA shares with each and where it differs
- The honest framing: "DCA is a specific architecture within this design space, distinguished by its continuous thought stream, sham-controlled evaluation, and Pareto-steering target"
- The SuperInstance research context (PAPER_CATALOG):
  - Constraint theory and PLATO tiles as deterministic substrate
  - Cognitive conservation law (γ + H = C)
  - Fleet architecture (mycorrhizal trust)
  - These provide background, not direct dependency

### Chapter 3: System Architecture
- The three-gate cascade: exact match → similar match → LLM generation
- The reflex compiler and sqlite-vec store
- The conductor cycle: n=30 thoughts, trust table, self-model
- The quality scorer: four axes (novelty, specificity, engagement, spatial)
- The .bottle ledger and conservation laws (token, action, identity, evolution)
- The world port / thinker port / action port interface
- **Key revision:** the conductor's objective is now profile steering, not quality maximization

---

## Part II: Formal Model (Revised)

### Chapter 4: Profile Steering and the Pareto Frontier
- **The falsified model:** semantic gradient as quality-improving signal
  - Original claim: interventions produce ∇δq that improves quality
  - EXP2 data: total quality unchanged (Δ = 0.00, p = 1.0)
  - The model was wrong and we say so
- **The revised model: profile steering**
  - Quality profile ρ = q/‖q‖₁ (shape, not magnitude)
  - Interventions rotate the profile, they don't extend it
  - The Pareto frontier of quality: N + E ≤ C (capability constant)
  - For 12B models: C ≈ 1.87, baseline at 95.7% of ceiling
- **The ceiling effect**
  - H(μ, task, rubric) = 1 - q̄/d (headroom formula)
  - DCA is only testable when H >> 0
  - Binary scoring compresses the frontier
- **The corrected experiment: Granite 3.1 2B**
  - Predicted baseline: 1.40–2.00 (33–53% headroom)
  - EXP3 design: A-B-A-C, N=30 per phase, continuous scoring
  - The fork: if total improves → DCA helps weak models; if only profile shifts → DCA is purely a profile director

### Chapter 5: Trust Dynamics (Revised)
- **Old rule:** strict Pareto dominance (improve ≥1 axis, degrade on none)
  - EXP2 showed this almost never fires — real interventions trade off
  - The trust table would starve
- **New rule: profile-targeted credit**
  - Intervention specifies target axis i*
  - Success: Δδqi* > 0 AND Δδqj > -ε for all j ≠ i*
  - Tolerance ε defaults to sham arm's σ on that axis
  - Trust indexed by (intervention_type, archetype, target_axis)
- **The self-model as a Pareto map**
  - χ: (intervention_type, archetype) → Δρ
  - Predicts direction of profile movement, not scalar gain
  - Enables sequencing: if bored (low E) and repetitive (low N), chain two interventions
- **Convergence (revised claims)**
  - Profile prediction: self-model converges to empirical mean Δρ
  - Profile targeting: hit rate for specified target regions
  - Frontier mapping: knowing which directions are achievable

### Chapter 6: Conservation Laws and Determinism
- The four conservation laws (unchanged by EXP2):
  - Token: fixed budget per cycle, downshift when exhausted
  - Action: no action without a command bottle
  - Identity: no artifact without metadata
  - Evolution: no parameter change without intervention bottle
- The .bottle ledger as a causal DAG
- Determinism claim C5: byte-for-byte replay
- Connection to SuperInstance constraint theory:
  - PLATO tiles as deterministic IR
  - FLUX bytecode for zero-drift execution
  - 657 tests, zero external dependencies in core

---

## Part III: Experimental Evidence

### Chapter 7: EXP1 — Reflex Hit Rate
- Design: 100 cognitive thoughts vs. 100 command phrases
- Result: cognitive 13.1%, command 6.1% at threshold 0.55 (TF-IDF)
- The hypothesis was falsified — cognitive > command, not <
- The synthetic data caveat: uniform sampling ≠ Zipfian real traffic
- The neural embedding spot-check (n=8): promising but underpowered
- **Verdict:** C2 unsupported at production scale; needs rerun with real embeddings

### Chapter 8: EXP2 — Semantic Gradient (Now Sham-Validated)
- Design: A-B-A-C, N=15, gemma-3-12b, maritime island task, binary scoring
- **Solid finding 1:** ceiling effect — specificity pinned at 1.000 across all 60 generations
- **Solid finding 2:** sham arm validated — baseline vs. sham not significant (Δ=-0.067, p=0.63)
- **Overclaimed finding:** profile shift (novelty ↑, engagement ↓) is a trend, not significant (p=0.14 uncorrected)
  - But mechanistically plausible and directionally coherent
- The Pareto tradeoff: N + E ≈ 1.87 = constant
- **What this means for DCA:** no net quality gain detected; the effect (if real) is a redistribution
- The 12B model is outside the target population

### Chapter 9: The EXP3 Fork (Proposed, Not Yet Run)
- Granite 3.1 2B via DeepInfra API (avoid local GPU issues)
- Continuous scoring (not binary)
- N=30 per phase (powered for d≈0.5)
- Two tasks (maritime + reasoning) for generality
- Conductor-vs-random-intervention arm (the missing ablation)
- **Four possible outcomes and what each means** (see REVISED_FORMAL_MODEL.md §4.4)

---

## Part IV: The Archaeological Context

### Chapter 10: The SuperInstance Research Foundation
This chapter positions DCA within the broader research program revealed by the PAPER_CATALOG survey of 80+ papers across 34 repos:

- **Constraint theory** (880:1 compression, zero-drift, PLATO tiles)
  - Provides the deterministic substrate DCA requires
  - Not a dependency — DCA can run without it — but explains WHY determinism matters
- **Cognitive conservation law** (γ + H = 1.283 - 0.159 ln V, R² = 0.9602)
  - The deeper principle behind DCA's conservation laws
  - You cannot maximize connectivity AND diversity simultaneously
  - DCA's Pareto frontier is a manifestation of this at the thought-stream level
- **Activation-key model** (~6,000 trials, 12 models)
  - LLMs store procedures as vocabulary-gated patterns
  - Implications for conductor intervention design: the prompt wording IS the activation key
- **Negative knowledge as primary computational resource** (4.8/5 cross-model rating)
  - DCA's sham arm IS a negative-knowledge mechanism
  - Knowing what doesn't work (sham) is the primary signal for trust calibration
- **FLUX bytecode** (zero drift, 58 opcodes)
  - The execution layer for deterministic thought replay
  - Enables the C5 determinism claim at a deep architectural level

### Chapter 11: The Mycorrhizal Fleet and Multi-Instance DCA
- Trust-weighted agent communication across 1,400+ repos
- Git commits as transport layer (auditable, replayable)
- Implications for DCA fleet deployment:
  - Can multiple DCA instances share a conductor?
  - Does trust generalize across instances?
  - The conservation law in a distributed setting

---

## Part V: Honest Assessment

### Chapter 12: What Works, What Doesn't, What's Next

**What works:**
- The sham arm is validated — the project's single best idea, now demonstrated
- The ceiling effect is a real, well-characterized finding
- The Pareto tradeoff is mechanistically plausible
- The conservation laws and .bottle ledger are sound (by construction)
- The three-gate cascade is architecturally sound (untested at production scale)
- The determinism substrate (PLATO/FLUX) is proven across 657 tests

**What doesn't work:**
- The "semantic gradient" as quality improvement — falsified
- The "new subfield" claim — indefensible against seven competing systems
- The strict Pareto dominance trust rule — structurally cannot fire
- EXP1's reflex hit rate for cognitive content — far below target
- The local GPU stack (Ollama/CUDA) — unreliable, blocks all local experiments

**What's next (priority order):**
1. EXP3: 2B model with continuous scoring and conductor-vs-random arm
2. Neural embedding rerun of EXP1 at n=100
3. Human validation pilot of the quality vector (20-30 thoughts, 2-3 raters)
4. Replay determinism test over 10K cycles
5. Continuous DCA loop latency measurement

**What we're explicitly deferring:**
- All theoretical questions requiring new math (Lyapunov, regret bounds)
- Fleet-level and multi-instance questions
- Browser-tier experiments
- Most ethics questions (important before live deployment, not before validation)

### Chapter 13: Limitations and Threats to Validity
- The quality vector is unvalidated by human judgment (circular without it)
- The scorer is a heuristic, not a proven measurement instrument
- Binary scoring compresses the Pareto frontier (ceiling effect)
- All experiments used independent generations, not a continuous thought stream
- No conductor-vs-random comparison has been run
- The local GPU reliability problem is unsolved (worked around, not fixed)
- The model used (12B) is 6× larger than the deployment target (2B)
- Single-task evaluation (maritime island) limits generality claims

### Chapter 14: Conclusion
- DCA's contribution is architectural and methodological, not theoretical
- The sham arm is a genuine methodological innovation
- The Pareto-steering framework is a productive reframing
- The ceiling effect finding has implications beyond DCA (model evaluation methodology)
- The honest position: the data changed our theory, the theory is better now, and EXP3 will determine whether DCA's value proposition survives in restricted form

---

## Appendix A: Claim Status Matrix

| Claim | Original Form | Current Status | Evidence |
|-------|--------------|----------------|----------|
| C1 (cost gate ≥50%) | ≥50% zero-cost decisions | Untested | Architecturally sound; no data |
| C2 (reflex ≥40%) | ≥40% hit rate after 1h | Unsupported | EXP1: 13.1% (TF-IDF); n=8 spot-check promising |
| C3 (trust ≥0.6) | Correlates with quality improvement | Revised | Now "correlates with profile movement"; not tested |
| C4 (policy ≥15%) | Evolved beats hand-tuned by 15% | Untested | ZeroClaw shows 70% vs random, not vs expert |
| C5 (determinism) | Byte-for-byte replay | Untested at scale | Architecturally sound; PLATO/FLUX proven |

## Appendix B: Cross-Reference to PAPER_CATALOG

| Dissertation Concept | Supporting Paper | Strength |
|---------------------|-----------------|----------|
| Deterministic substrate | Constraint Theory (§1.1), FLUX (§7.1) | Strong — 657 tests, zero drift |
| Conservation laws | Cognitive Conservation Law (§2.1) | Strong — R²=0.96, 35K samples |
| Sham arm as negative knowledge | Negative Knowledge (§10.1) | Moderate — conceptual parallel |
| Pareto frontier | Fleet Conservation (§3.5) | Moderate — PID governor analogy |
| Profile steering | Seed Information Theory (§4.1) | Weak — different formalism |
| Trust propagation | Mycorrhizal Fleet (§3.1) | Moderate — fleet-level validation |
| Activation keys for intervention design | EMNLP Activation-Key (§5.1) | Strong — 6,000 trials, 12 models |

## Appendix C: What the Reviewer Said vs What We Did

| Reviewer Finding | Response | Status |
|-----------------|----------|--------|
| No sham arm validation | Ran EXP2 with sham arm | Fixed — sham validated |
| No real experiments | Ran EXP1 and EXP2 | Fixed — both complete |
| Rigged Table 2.1 | Drop "new subfield" claim | Accepted — reframe to Branch B |
| ≻ Pareto dominance won't fire | Revised to bounded-cost rule | Fixed — REVISED_FORMAL_MODEL.md §5 |
| Hamming fallback is wrong | Acknowledged, not yet fixed | Open |
| Fabricated citation | Not yet checked | Open |
| Missing related work | 7 systems catalogued | Addressed in Ch.2 outline |

---

*This outline integrates 1098 lines of formal model revision, 720 lines of archaeological survey across 80+ papers, and the experimental evaluations into a single coherent structure. It is honest about what is proven, what is revised, and what remains open.*
