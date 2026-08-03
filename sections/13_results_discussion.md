# 12. Projected Results and Discussion

This dissertation establishes the theoretical and architectural foundations of Dynamic Cognition Amplification. Because the reference implementation is in migration from `slackwater-cognition` to `thought-amplifier`, this chapter reports *projected* results derived from the deep-dive precedents and identifies the empirical questions that will decide whether DCA succeeds as a subfield.

## 12.1 Projected Results Against Testable Claims

Recall the five claims introduced in Chapter 2:

**C1: Cost gate.** At least 50% of decisions served at zero marginal cost after one hour.

*Projection.* Lever Runner already achieves ~56% zero-token decisions in production, and Pincher reports reflex hit rates approaching 80% after a month. DCA's additional Gate-2 compiled policy should produce a faster warm-up than Pincher's reflex store alone. A conservative projection is 50% zero-cost by 1 hour and 70% by 1 week.

**C2: Reflex convergence.** Reflex hit rate ≥40% after one hour.

*Projection.* Pincher's exact-match threshold (≥0.80) and Lever Runner's cache (44% hit at week 1) bracket the target. With escape-hatch sampling forcing some Gate-3 calls, 40% is achievable if the scenario distribution is not too thin.

**C3: Trust validity.** Conductor trust scores correlate ≥0.6 with measured quality improvement against a sham arm.

*Projection.* This is the riskiest claim. Without the sham arm, trust scores will likely correlate near zero with true effect because of the novelty bias. With the sham arm and a 10-observation minimum before updates, a 0.6 correlation is plausible after 100 interventions. The key determinant is whether the measurement window is long enough to average out noise without being so long that context drift swamps the effect.

**C4: Policy superiority.** Evolved policy beats hand-tuned weights by ≥15% on held-out states.

*Projection.* ZeroClaw's evolved Tic-Tac-Toe policy reaches ~70% win rate against random play, and the integration plan projects 80% fast-path hit rate with 80% cost reduction. A 15% quality improvement is consistent with these precedents if the satisfaction signal is clean.

**C5: Determinism.** A recorded `.bottle` ledger replays to identical output under the null adapter.

*Projection.* This is a property of the architecture, not an empirical measurement. The null adapter removes all sources of non-determinism (network, RNG seeding, hardware timing). Byte-for-byte replay should hold by construction, assuming the ledger captures all inputs.

## 12.2 What Success Would Mean

If the projected results hold, DCA would demonstrate a viable third path between offline training and tool-calling agents:

- **Cheaper than agent frameworks.** The three-gate cascade moves the majority of decisions out of the LLM, cutting token spend by 50–80% relative to tool-calling.
- **More continuous than offline training.** The system updates prompts, policies, and trust scores every 30 seconds, not every training run.
- **More interpretable than end-to-end models.** Every decision traces through a DAG of `.bottle` messages to a root observation.
- **More cautious than pure optimization.** Asymmetric trust, sham arms, and clamps prevent the system from declaring certainty prematurely.

## 12.3 Limitations

**Data efficiency.** DCA learns from its own stream, which is data-rich but label-poor. The quality vector is a heuristic, not ground truth. What the system learns is "what the quality scorer likes," which may diverge from "what humans like" if the scorer is misspecified.

**Evaluation cost.** Validating the Conductor requires running sham arms, which means running the system longer and possibly withholding beneficial interventions. Live playtest evaluation is expensive and ethically constrained.

**Generality ceiling.** The reflex and policy mechanisms work best when situations recur. A player who constantly creates genuinely novel scenarios will keep the system at Gate 3 and defeat the cost optimization. This is not a bug—it is the system's declared competence boundary.

**Multi-timescale interference.** Trust, evolution, and LoRA modify overlapping parameters at different periods. Even with dwell times, emergent oscillations are possible. The formal model predicts convergence under bounded noise, but the constants matter.

**Browser tier hardware dependence.** The browser finisher requires WebGPU and sufficient VRAM. On low-end devices, the tier disappears, and the server does all the work. The divergence-loss teaching signal is therefore available only for a subset of users.

## 12.4 Open Questions

Several questions remain unresolved and are flagged as Architecture Decision Records:

1. **Additive vs. multiplicative confidence updates.** The Fable master prompt specifies additive `+0.05(1−c)` / `−0.10c`; Pincher uses multiplicative `×1.005` / `×0.95`. The choice affects convergence speed and should be measured.

2. **Ownership of divergence loss.** Does the browser finisher's error signal belong to the individual player (personalization) or to the global system (shared prior)? This is a privacy decision before it is a technical one.

3. **Ethics of the sham arm.** Running a sham intervention against a live player withholds a possibly beneficial adjustment. Is replay-based sham estimation sufficient, or must live shams be disclosed and consented?

4. **Quality vector design.** The four axes (novelty, specificity, engagement, spatial awareness) are plausible but not validated. Factor analysis of human judgments could refine or expand them.

5. **Substrate transfer.** DCA is instantiated here for a game companion. Does it transfer to other domains—coding assistants, tutoring systems, creative tools—without changing the engine?

## 12.5 Relation to the Broader Field

DCA can be read as a synthesis of three existing ideas: continual learning's interest in non-stationarity, interactive machine learning's interest in human-in-the-loop adaptation, and reflex-based systems' interest in cheap execution. Its novelty lies in the conjunction: a continuous stream, a semantic gradient on generation conditions, a qualitative multi-objective target, and executable conservation laws.

The most controversial claim is that the objective is qualitative. Traditional ML prefers scalar objectives because they are easy to optimize and evaluate. DCA argues that for open-ended companion systems, scalar objectives are either wrong or gameable. The multi-objective quality vector and the conductor's diagnostic role are an alternative that trades optimization convenience for behavioral plausibility.

## 12.6 Summary

The projected results suggest that DCA is achievable, but the critical empirical question is whether the trust-scoring loop can overcome novelty bias. If it cannot, the Conductor will learn useless regularities and the system will not improve. If it can, DCA offers a new way to build AI systems that learn continuously, interpretably, and within explicit resource and safety budgets.
