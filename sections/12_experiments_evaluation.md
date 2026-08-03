# 11. Experiments and Evaluation

This chapter describes the evaluation protocol for DCA. Because DCA is continuous, qualitative, and self-modifying, standard static benchmarks are insufficient. The evaluation combines controlled directed play, sham-intervention arms, deterministic replay, and conservation-law property tests.

## 11.1 Evaluation Principles

Three principles guide the evaluation:

1. **Live evaluation.** Progress is measured during operation, not on a fixed test set, because the distribution of situations is non-stationary and the Conductor changes it.
2. **Controlled comparison.** Every intervention is compared against a sham arm to separate real effect from novelty bias.
3. **Multi-scale validation.** Each learning mechanism (reflex, policy, trust, LoRA) has its own metrics, and the system-level metrics enforce the budget and conservation laws.

## 11.2 Test Harness

The primary test harness is the `adapters/null/` configuration. Every port is replaced by a deterministic fake:

- `NullWorld` returns scripted observations and outcomes;
- `NullThinker` returns deterministic thoughts from a seeded RNG;
- `NullConductor` returns a fixed schedule of interventions;
- `NullVectorStore` and `NullEmbedder` provide deterministic vector operations.

Because the loop is deterministic, a recorded bottle ledger can be replayed and asserted to produce identical output. This is the only practical regression test for a stochastic system.

A secondary harness uses the Slackwater adapter for live playtests. Live sessions are instrumented with the same bottle ledger and compared against null-adapter simulations of the same scripted scenarios.

## 11.3 Reflex Compiler Experiments

**Experiment R1: Latency.** Insert 10,000 reflexes into sqlite-vec and measure query latency for 1,000 random signatures. Target: p99 <1 ms.

**Experiment R2: Hit-rate convergence.** Run a simulated 1-hour session with a fixed scenario distribution. Measure the fraction of thoughts served by Gate 1 (reflex) over time. Target: ≥40% after 1 hour.

**Experiment R3: Confidence calibration.** Bin reflexes by confidence and measure empirical success rate in each bin. Target: correlation between confidence and success rate ≥0.7.

**Experiment R4: Portability.** Export a `.nail` bundle, import it into a fresh instance, and rerun the same scenario. Target: identical behavior.

**Experiment R5: Fallback.** Disable the ONNX/bge-m3 embedder and verify that the hash fallback produces deterministic, degraded-but-functional dispatch.

## 11.4 Evolution Engine Experiments

**Experiment E1: Policy superiority.** Train an evolved policy for 2 weeks of simulated play and compare its quality scores to the static hand-tuned weights. Target: ≥15% improvement.

**Experiment E2: Convergence.** Plot the variance of tile scores over a sliding 24-hour window. Target: variance <0.01 after 2 weeks.

**Experiment E3: Interpretability.** For every decision, print the tile entry that produced it. Target: 100% traceability.

**Experiment E4: Compression.** Cluster context tiles into 8 archetypes and measure policy size and performance. Target: ~10× size reduction with <5 percentage points performance loss.

## 11.5 Trust Scoring Experiments

**Experiment T1: Correlation.** After 100 logged interventions, compute the Pearson correlation between trust score and sham-corrected quality improvement. Target: ≥0.6.

**Experiment T2: Rollback.** Inject a deliberately harmful intervention type and verify that 3 consecutive negative measurements trigger auto-revert. Target: 100% detection.

**Experiment T3: Sham control.** Compare naive before/after effect sizes to sham-corrected effect sizes. Target: naive effect is positive for >80% of interventions; sham-corrected effect is positive for <50% early in training, rising as trust accumulates.

**Experiment T4: Self-model emergence.** Track the number of (intervention_type, archetype) pairs with consistent positive effect. Target: ≥3 reliable patterns within 2 weeks.

## 11.6 Temporal Pipeline Experiments

**Experiment M1: End-to-end pipeline.** Run 20 sessions through MIDI encoding, canonicalization, embedding, and Vectorize storage. Target: zero manual intervention.

**Experiment M2: Recall latency.** Query the temporal vector index for similar rhythms. Target: p99 <50 ms.

**Experiment M3: Clustering.** Run hierarchical clustering on the 20 session vectors. Target: ≥3 human-interpretable clusters.

**Experiment M4: Conductor usage.** Log the fraction of Conductor modification decisions that referenced a temporal pattern match. Target: ≥30%.

**Experiment M5: Embedding consistency.** Run the same session through the pipeline twice. Target: cosine similarity = 1.0 between the two vectors.

## 11.7 Distillation Experiments

**Experiment D1: Data extraction.** Extract training examples from 1 week of journals. Target: ≥500 qualifying examples.

**Experiment D2: Training time.** Train a LoRA adapter on the RTX 4050. Target: <4 hours.

**Experiment D3: Held-out gain.** Evaluate the tuned model against the base model on a fixed held-out set. Target: ≥10% improvement on quality metrics.

**Experiment D4: DPO specificity.** Compare DPO-trained and SFT-only models on specificity and spatial awareness axes. Target: DPO improves these axes specifically.

**Experiment D5: Trap detection.** Deliberately train an adapter on a biased subset and verify that held-out quality stays flat while train quality rises. Target: promotion correctly rejected.

## 11.8 System-Level Experiments

**Experiment S1: Determinism.** Run the null-adapter loop with a fixed seed three times. Target: identical bottle ledger each time.

**Experiment S2: Conservation laws.** Run 1,000 cycles and assert: no action without a command bottle; no config mutation outside an intervention; token spend ≤ budget. Target: zero violations.

**Experiment S3: Cost gate.** Measure the fraction of decisions served at zero marginal cost over a 1-hour session. Target: ≥50%.

**Experiment S4: Degradation ladder.** Substitute each preferred adapter with its fallback and verify the loop continues. Target: no hard failures.

**Experiment S5: Import boundary.** Run the import-linter and assert zero game-specific imports in `amplifier/`. Target: clean.

## 11.9 Live Playtest Protocol

Live playtests with human players follow an ethics-reviewed protocol:

1. Players are informed that the AI may adjust its behavior and that some adjustments may be logged but not applied (sham arm).
2. Sessions are opt-in and recorded as bottle ledgers.
3. Quality metrics are computed from player behavior and optional explicit feedback.
4. No player-facing output is generated without Nemotron-Safety-3.5 filtering.
5. All interventions are revertible within three strikes.

The sham arm is essential for valid inference but raises an ethical question: it withholds possibly beneficial adjustments. The protocol mitigates this by keeping shams rare (<10% of interventions) and by using replay-based sham estimation when possible.

## 11.10 Summary

The evaluation protocol treats DCA as an experimental system. Every claim is operationalized as a measurement, every intervention is compared against a sham, and every subsystem is tested in isolation and in the full loop. The acceptance criteria from the Fable master prompt and REPO_DESIGN become the empirical bar that establishes DCA as a real subfield rather than an architecture sketch.
