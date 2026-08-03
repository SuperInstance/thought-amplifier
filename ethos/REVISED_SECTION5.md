# Revision: Intervention Effects and Trust Dynamics — Accounting for Profile Shifts

**Author:** Claude Opus, acting as Ethos (evaluative faculty)
**Date:** 2026-08-03
**Triggered by:** `experiments/EXP2_SEMANTIC_GRADIENT.md` (rerun via DeepInfra API, `gemma-3-12b-it`, N=15/phase, sham-validated)

## A section-numbering correction, stated up front

The request was to revise "Section 5 (formal model)." In the current `DISSERTATION.md`, **Section 5 is "The Three-Gate Cascade and Reflex Compiler"** — reflex dispatch, confidence clamps, the embedding pipeline. It has nothing to do with intervention effects or quality trade-offs. **The actual formal model is Section 4** ("A Formal Model of Dynamic Cognition Amplification"), and the specific machinery that EXP2's finding bears on lives in **§3.6** (the semantic-gradient definition), **§4.5** (Conductor Interventions), and **§4.6** (Trust Dynamics) — with a secondary consequence for **§6.1** (the evolution engine's scalarization) and the `Intervention` dataclass in **§7.2**. This document revises those, under the filename requested. If "Section 5" was meant literally, there is nothing in the current reflex-cascade chapter that this finding touches; say so and I'll redirect.

## Epistemic status of the finding this revision is based on

EXP2 found: total quality score flat across all four phases (2.80–2.87), sham arm correctly indistinguishable from baseline (validating the control), and a directional pattern — novelty up (0.867→1.000), engagement down (1.000→0.867) under intervention — that is *not* statistically significant at conventional thresholds (p=0.14 uncorrected, Bonferroni p=1.0, n=15/arm, roughly 55–60/arm needed for adequate power at the observed effect size). My own evaluation (`ethos/EXPERIMENT_EVALUATION.md`) treats this as a mechanistically plausible, worth-taking-seriously trend, not an established empirical law.

That distinction matters for how this revision should be read: **the specific numbers should not be treated as validated**, but **the conceptual point — that a targeted intervention can move its target axis while costing a different, non-target axis, within a fixed generation budget — is sound on its own logical merits**, independent of whether this particular n=15 run replicates. The revision below is written to be correct regardless of replication; it should be marked as a proposed ADR (matching the dissertation's own §12.4 practice) pending a properly powered rerun, not committed as settled doctrine.

---

## The problem: two parts of the current formal model disagree with each other

**§3.3 describes a *targeted, single-axis* diagnostic model.** The conductor doesn't optimize a blend — it inspects the quality vector, finds the weak axis, and prescribes a fix for that axis specifically: *"If specificity is low, it injects a prompt urging material detail. If novelty is low, it boosts temperature or adds exploration cues."* This is a per-axis, one-at-a-time model of intervention.

**§4.6 evaluates intervention success against *all four axes jointly*, with zero tolerance for cost.** The current trust update:

> \[
> T(c, k) \leftarrow T(c, k) + \eta_+ \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \succ 0] - \eta_- \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \prec 0],
> \]
>
> where \(\succ\) means *"improves relative to the sham arm on at least one quality axis without degrading on any other."*

`CLAUDE_REVIEW.md` §2.7 already flagged that strict Pareto dominance across four noisy axes will rarely fire, for statistical reasons — most comparisons land in the incomparable region, and with \(N_{\min}=10\) required per cell, filling the trust table could take weeks. EXP2 supplies a second, structural reason that compounds the statistical one: **even a working intervention, doing exactly what it was diagnosed to do, is not guaranteed to be Pareto-dominant, because targeting one axis inside a fixed token/attention budget can predictably cost a different axis.** The materials-focused intervention in EXP2 plausibly did exactly what §3.3 says a diagnosis should do — it pushed novelty (via more varied descriptive vocabulary) at the cost of engagement (less room for first-person emotional language in 60 tokens). Under the current §4.6 rule, this intervention is neither \(\succ\) nor \(\prec\) — it's Pareto-incomparable — so it produces **no trust update at all**, indistinguishable from an intervention that did nothing. The diagnostic model in §3.3 and the evaluation rule in §4.6 are not currently compatible: one assumes trade-offs are the normal mechanism of action, the other treats any trade-off as disqualifying.

---

## Revised §3.6: axis-indexed semantic gradient

Current text defines \(\nabla_\delta \mathbf{q}\) as a single vector-valued difference of means, with a scalar-flavored promotion rule bolted on ("positive on at least one axis and non-negative on the others"). Make the per-axis structure explicit rather than implicit, and drop the promotion clause from this section — it belongs in the trust-update rule below, not the definition of the gradient itself.

> **Revised:** The "semantic gradient" is the per-axis measured effect of an intervention relative to its sham control, over the window:
>
> \[
> \nabla_\delta q_j = \bar{q}_{\text{after}, j} - \bar{q}_{\text{sham}, j}, \qquad j \in \{\text{novelty}, \text{specificity}, \text{engagement}, \text{spatial}\}.
> \]
>
> (The four-term form in the original — subtracting \(\bar q_{\text{before}}\) from both the treatment and sham arms — algebraically cancels to this two-term difference; write it this way to avoid the confusion `CLAUDE_REVIEW.md` §2.4 flagged.) \(\nabla_\delta \mathbf{q} = (\nabla_\delta q_1, \ldots, \nabla_\delta q_4)\) is the vector of per-axis effects, not a single scalar or a single pass/fail judgment. Whether an intervention counts as successful is a property of the *trust update rule* (§4.6), not of the gradient itself — the gradient is a measurement, not a verdict.

---

## Revised §4.5: interventions carry a declared target axis

The `Intervention` record (§7.2) already has a `target` field, but it denotes *which configuration value changed* (`"system_prompt"`, `"temperature"`) — not *which quality axis the change was meant to fix*. These are different things and the current schema conflates them by omission: nothing currently records what the conductor was trying to accomplish, only what it edited. Add the missing field.

> **Revised `Intervention` dataclass (§7.2), amending the field list:**
> ```python
> @dataclass(frozen=True)
> class Intervention:
>     kind: Literal["prompt", "parameter", "policy"]
>     target: str                          # config value changed, e.g. "system_prompt"
>     target_axis: Literal["novelty", "specificity", "engagement", "spatial"]
>     before: Any
>     after: Any
>     context_key: str
>     applied_at: float
>     quality_before: Quality
>     quality_after: Quality | None
> ```
>
> **Revised §4.5, appending after the existing candidate-scoring paragraph:** Each candidate intervention \(\delta_i\) is generated in response to a diagnosed deficiency on a specific axis \(k^*(\delta_i)\) (per §3.3) — e.g., an intervention that urges material detail declares \(k^* = \text{specificity}\), or in EXP2's case, produced its largest effect on novelty regardless of what it was nominally aimed at, which the trust update below must be able to detect and record rather than average away. The conductor's diagnosis of \(k^*\) is a hypothesis, not a guarantee — an intervention aimed at one axis may, as EXP2 shows, land its largest measured effect elsewhere. The trust update should score against the axis where the effect actually landed, using \(k^*\) only as the intervention's *declared intent* for auditing and self-model purposes (§7.7), not as a constraint on which axis "counts."

---

## Revised §4.6: bounded-cost trust update, replacing strict dominance

This is the core fix. Replace the zero-tolerance dominance rule with an explicit, tunable, auditable cost tolerance — converting an implicit \(\varepsilon = 0\) (any cost anywhere disqualifies) into an explicit, versioned \(\varepsilon\) that the system can reason about and the conservation-law audit trail can log.

> **Revised trust update:**
>
> Let \(k^*\) be the intervention's declared target axis and \(\varepsilon_j \geq 0\) be an axis-specific, versioned tolerance for acceptable degradation on non-target axis \(j\) (§4.6.1 below). Define the outcome of a measured intervention as:
>
> \[
> \text{outcome}(\delta) = \begin{cases}
> \text{success} & \text{if } \nabla_\delta q_{k^*} > 0 \text{ and } \nabla_\delta q_j \geq -\varepsilon_j \ \forall j \neq k^*, \\
> \text{failure} & \text{if } \nabla_\delta q_{k^*} \leq 0, \\
> \text{overcost} & \text{if } \nabla_\delta q_{k^*} > 0 \text{ but } \nabla_\delta q_j < -\varepsilon_j \text{ for some } j \neq k^*.
> \end{cases}
> \]
>
> \[
> T(c, k) \leftarrow T(c, k) + \eta_+ \cdot \mathbb{1}[\text{outcome} = \text{success}] - \eta_- \cdot \mathbb{1}[\text{outcome} \in \{\text{failure}, \text{overcost}\}],
> \]
>
> with \(\eta_+ = 0.5\), \(\eta_- = 2.0\), and \(N_{\min}=10\) as before. **The key change from the original \(\succ\)/\(\prec\) rule:** `overcost` is now treated the same as `failure` for the trust penalty (an intervention that blows its cost budget is still discouraged — this is not a license to trade freely), but the *bar for success* no longer requires zero cost everywhere, only bounded cost on the axes the conductor wasn't trying to fix. Under this rule, applied retroactively to EXP2's numbers (target axis = novelty, observed engagement cost = 0.133): if \(\varepsilon_{\text{engagement}} \geq 0.133\), the intervention scores as `success`; if \(\varepsilon_{\text{engagement}} < 0.133\), it scores `overcost`. Either way, the intervention now produces *a* trust update — success or a penalized failure — instead of the silent no-op the original incomparable-outcome case produced. This directly addresses the "trust table starves for weeks" problem `CLAUDE_REVIEW.md` §2.7 identified: incomparability is no longer a third silent outcome, it's resolved into one of the two the trust table already knows how to use.

> **New §4.6.1: setting \(\varepsilon_j\).** \(\varepsilon_j\) is a per-axis, per-archetype parameter, not a global constant — cheap axes to sacrifice in one context (e.g., engagement, briefly, in an inspection-focused moment) may be expensive in another (e.g., engagement during a low-bond-tier first encounter, where the system's whole purpose is building rapport). Two guardrails are required, both direct responses to `CLAUDE_REVIEW.md` §2.6's novelty-gaming concern: (1) \(\varepsilon_j\) must be explicitly versioned and logged in the `.bottle` ledger alongside the intervention record, satisfying evolution conservation (§4.8) — no silent tolerance changes; (2) \(\varepsilon_j\) must be bounded below a value that would allow an axis to be driven toward its floor over repeated interventions — e.g., a rolling cap on cumulative engagement cost per session, not just per-intervention cost, to prevent a conductor from "solving" specificity by slowly bankrupting engagement one small, individually-tolerable overcost at a time. This is the same failure mode as reward hacking via novelty (degenerate output maximizes novelty trivially); a per-intervention \(\varepsilon\) without a cumulative cap has the identical exploit shape one axis over.

---

## Consequence for §6.1: the evolution engine's scalar is a different, coarser instrument

Not a rewrite of Chapter 6 — out of scope here — but the tension is real and should be flagged as a cross-reference. §6.1 scores actions by \(s = w_1 q_{\text{novelty}} + w_2 q_{\text{specificity}} + w_3 q_{\text{engagement}} + w_4 q_{\text{spatial}}\), a fixed-weight scalar. If the revised §4.6 above is adopted, the Conductor's trust evaluation is now explicitly axis-aware and cost-bounded — while the evolution engine's action-selection score would still collapse exactly the trade-off §4.6 is now built to detect. EXP2's own finding (novelty +0.133, engagement -0.133, canceling exactly in an equal-weighted sum) is a direct demonstration of how a scalar objective hides this: any \(w_1 \approx w_3\) makes the scalar blind to a trade-off the multi-axis trust rule now explicitly resolves. **Recommendation, not implemented here:** the evolution engine's scalar \(s\) should remain scoped to within-tile action selection (choosing among leans given a context), and should not be reused to evaluate Conductor interventions — those should go through the axis-aware §4.6 rule exclusively, so the architecture doesn't reintroduce, in Chapter 6, the exact hiding-of-trade-offs problem the multi-objective vector in Chapter 3 was built to avoid.

---

## What would confirm or kill this revision

Two independent checks, neither requiring new LLM calls:

1. **Simulation check (fast, do this first):** replay EXP2's own per-item data through both the original \(\succ\)/\(\prec\) rule and the revised bounded-cost rule, and count how often each produces a trust update vs. a silent no-op. If the revised rule doesn't measurably reduce the no-op rate on existing data, the fix isn't earning its added complexity.
2. **Properly powered rerun (per `ethos/EXPERIMENT_EVALUATION.md`):** at 2B model scale, continuous scoring, N≈60/arm, confirm whether the novelty/engagement trade-off pattern replicates with significance. If it doesn't replicate at all, the motivating case for this revision weakens considerably — the fix would then be solving a problem that hasn't been shown to recur, and should be held as an ADR rather than merged into the formal model text.

Until either check runs, this document should be treated as a proposed revision, not an accepted one.
