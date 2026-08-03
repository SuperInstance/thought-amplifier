# 7. The Conductor and Trust Scoring

The Conductor is the slow, strategic component of DCA. Every 30 seconds it reads the recent stream of thoughts, diagnoses quality patterns, proposes changes to the thinker's conditions, and learns from whether those changes helped. This chapter describes the Conductor's architecture, the intervention types it can apply, and the trust-scoring system that prevents it from chasing noise.

## 7.1 The Conductor's Role

If the local thinker is an improvisational actor, the Conductor is the director. It does not generate thoughts itself; it modifies the conditions under which thoughts are generated. Its inputs are:

- the last \(n\) thoughts and their quality vectors;
- the current prompt version, parameter settings, and policy weights;
- historical patterns from the vector store, including temporal rhythms;
- its own trust table and self-model.

Its outputs are interventions of three kinds:

\[
\Delta_{\text{prompt}}: \text{edit the system prompt},
\]
\[
\Delta_{\text{param}}: \text{adjust temperature, top-p, repetition penalty, etc.},
\]
\[
\Delta_{\text{policy}}: \text{adjust action-policy weights}.
\]

The Conductor runs on a large model (GLM-5.2, Claude Opus, or DeepSeek V3) because its task requires long-context synthesis and qualitative judgment. It is not in the hot path; latency of ~10 s is acceptable.

## 7.2 Intervention Record

Every intervention is recorded as an immutable dataclass:

```python
@dataclass(frozen=True)
class Intervention:
    kind: Literal["prompt", "parameter", "policy"]
    target: str                      # e.g., "system_prompt" or "temperature"
    before: Any
    after: Any
    context_key: str                 # tile-hash / archetype of the situation
    applied_at: float
    quality_before: Quality          # trailing window mean
    quality_after: Quality | None    # filled after measurement window
```

The record is appended to the `.bottle` ledger as a `config` message. Because the ledger is append-only, every change is auditable and reversible. This is the implementation of the evolution conservation law.

## 7.3 The Placebo Problem and Sham Interventions

Any change tends to produce temporary improvement. A new prompt is novel; novelty increases engagement; the Conductor concludes the prompt helped. This is the single most likely way the system fools itself.

To control for the placebo effect, DCA maintains a **sham arm**. Periodically the Conductor logs an intervention but does not apply it. The measurement window is scored anyway. The real effect of an intervention is:

\[
\nabla_\delta \mathbf{q} = (\bar{\mathbf{q}}_{\text{after}} - \bar{\mathbf{q}}_{\text{before}}) - (\bar{\mathbf{q}}_{\text{sham}} - \bar{\mathbf{q}}_{\text{before}}).
\]

An intervention is credited only if it outperforms the sham arm. Without this correction, the Conductor would confidently learn that "changing things helps," which is not a useful discovery.

## 7.4 Trust Dynamics

Trust scoring for Conductor interventions adapts Lever Runner's asymmetric model but slows it down, because cognitive modifications are noisier than command routing. The update rule is:

\[
T(c, k) \leftarrow T(c, k) + 0.5 \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \succ 0] - 2.0 \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \prec 0],
\]

where \(c\) is the intervention type, \(k\) is the context archetype, and updates occur only after \(N_{\min} = 10\) observations. The symbol \(\succ\) means "improves relative to sham on at least one quality axis without degrading on any other."

New intervention types start at trust 50. The asymmetry (−2.0 vs +0.5) means roughly four successes are required to recover from one failure. This conservatism is intentional: a bad prompt modification can degrade the entire thought stream, while a good one produces only incremental gain.

Trust is bounded to \([0, 100]\). A trust score below a floor (e.g., 30) blocks further applications of that intervention type in that archetype until positive evidence accumulates.

## 7.5 Canary and Promotion

Before full promotion, an intervention is tested on a 10% canary. The canary runs for 50 thoughts (approximately 50 s). If the sham-corrected effect is positive, the intervention is promoted to 100% of traffic. If it is negative, it is discarded. If it is inconclusive, it remains in canary for another 50-thought window.

This procedure comes directly from SuperInstance's self-improvement loop: observe → hypothesize → A/B test (10% canary) → propose → review → merge. DCA automates the promotion decision while keeping the intervention record available for human audit.

## 7.6 Rollback and Hysteresis

If three consecutive interventions of the same type in the same archetype produce negative measured effects, the system auto-reverts to the previous prompt/policy version. A minimum **dwell time** is then imposed before that target can be modified again.

Hysteresis is essential because the Conductor (30 s period) and the evolution engine (heartbeat/daily period) operate at different frequencies. Without dwell, they can fight: the Conductor increases temperature to boost novelty while the evolution engine decreases a curiosity weight, producing oscillation. The dwell time ensures that one loop's change is measured before the other loop can counteract it.

## 7.7 Self-Model

The Conductor maintains a self-model \(\chi_t\) that maps pairs \((\text{intervention_type}, \text{context_archetype})\) to expected effects. For example:

- "temperature increase helps when novelty is low;"
- "prompt specificity helps when generic thoughts increase;"
- "curiosity weight boost helps when the player is near unexplored areas."

The self-model is updated from measured intervention effects. It is the bridge between the trust table ("does this work?") and the conductor's generation of candidate interventions ("what should I try next?"). The archetypes from the evolution engine pay for themselves twice: they compress the policy table and they index the self-model.

## 7.8 The Conducting Cascade

The three-gate pattern recurs at the conducting level:

| Gate | Check | Cost |
|---|---|---|
| 1 | Trust check on modification type | ~0 (table lookup) |
| 2 | Temporal pattern precedent | ~10–50 ms (vector search) |
| 3 | Conductor LLM deliberation | ~10 s |

If the trust table says "do not modify temperature in this archetype," the Conductor skips the expensive model call. If a temporal pattern query finds a strong precedent ("this rhythm of play improved after a specificity prompt"), the Conductor may use that as a cheap candidate. Only genuinely novel conducting situations reach Gate 3.

## 7.9 Acceptance Criteria

The Fable master prompt specifies:

- Every Conductor intervention is logged with before/after state.
- Trust scores correlate with actual quality improvement (≥0.6 correlation after 100 interventions).
- Auto-rollback triggers on 3 consecutive quality decreases from the same modification type.
- A/B canary runs for 50 thoughts before promotion.
- The Conductor self-model identifies ≥3 reliable modification patterns within 2 weeks.

These criteria are measured against the sham arm, not against the naive before/after difference.

## 7.10 Summary

The Conductor closes the meta-learning loop. It turns the stream of consciousness into structured experiments on the thinker's conditions, measures their effects with placebo controls, and accumulates trust only for interventions that genuinely help. The trust dynamics, canary procedure, rollback mechanism, and self-model together prevent the Conductor from chasing noise and oscillating against the evolution engine.
