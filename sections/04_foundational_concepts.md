# 3. Foundational Concepts

Before presenting the formal model, we introduce the primitives that DCA manipulates: the stream of consciousness, the lean/action separation, the quality vector, the three time scales of adaptation, and tempo as a first-class substrate. Each concept is defined precisely enough to be implemented and measured.

## 3.1 The Stream of Consciousness

In DCA, the basic datum is not a query–response pair but a continuous stream of thoughts. A thought \(\tau_t\) is a short natural-language reflection produced by the local thinker at time \(t\), together with metadata that makes it interpretable and actionable:

\[
\tau_t = (\text{text}_t, \ell_t, o_t, \pi_t, v_t, b_t, q_t, m_t),
\]

where:

- \(\text{text}_t\) is the generated reflection (2–4 sentences);
- \(\ell_t\) is the **lean**, a 3–8 word intent phrase such as `inspect tower_top`;
- \(o_t\) is the observation that triggered the thought;
- \(\pi_t\) is the prompt version under which the thought was generated;
- \(v_t\) is the vector embedding of the thought text;
- \(b_t\) is the beat position in the shared tempo map;
- \(q_t\) is the quality vector assigned after the thought leads to action;
- \(m_t\) is provenance metadata (model version, session id, trace id).

The stream \((\tau_1, \tau_2, \ldots)\) is the training signal. Every thought is an example of what the thinker does in a particular state under particular conditions. The conductor's job is to change those conditions so that future samples are better.

## 3.2 The Lean / Action Separation

A central structural decision in DCA is that the LLM does not select actions directly. It emits a **lean** \(\ell\), and a separate algorithmic layer maps the lean to a concrete action \(a\):

\[
\ell_t \sim \mathcal{T}(\,\cdot\, \mid s_t), \qquad a_t \sim \mathcal{A}(\,\cdot\, \mid \ell_t, o_t).
\]

The lean vocabulary is fixed and pre-approved. Example leans include `explore`, `approach`, `build`, `inspect`, `wait`, and `speak`. The action layer applies deterministic guards: confidence thresholding, cooldown timers, novelty detection, and curiosity bonuses. This separation yields two benefits:

1. **Security.** The LLM's output channel is too narrow to encode arbitrary commands. Even if the model is compromised by prompt injection, it can only request an action from a known set.
2. **Interpretability.** Every action traces to a lean, and every lean traces to a thought. The causal chain from observation to action is explicit and auditable.

Lever Runner provides the empirical precedent: compressing user input to a 3–8 word intent phrase reduces token spend from ~2,000–5,000 to ~76 tokens and enables a structural security property that tool-calling agents lack.

## 3.3 The Quality Vector

DCA rejects a single scalar reward in favor of a decomposed quality vector. For each thought, we compute

\[
\mathbf{q} = (q_{\text{novelty}}, q_{\text{specificity}}, q_{\text{engagement}}, q_{\text{spatial}}) \in [0,1]^4.
\]

The axes are defined operationally:

- **Novelty** measures how much the thought differs from recent thoughts in the same session, via cosine distance of embeddings:
  \[
  q_{\text{novelty}} = 1 - \max_{\tau' \in \text{recent}} \cos(v_\tau, v_{\tau'}).
  \]
- **Specificity** scores the density of concrete nouns, materials, and spatial references relative to generic placeholders.
- **Engagement** estimates emotional and relational salience, including bond-tier-appropriate tone.
- **Spatial awareness** checks whether the thought references positions, distances, or structural relations in the world.

The conductor does not maximize a weighted sum; it diagnoses. If specificity is low, it injects a prompt urging material detail. If novelty is low, it boosts temperature or adds exploration cues. The multi-objective formulation prevents the system from gaming a single metric at the expense of others.

## 3.4 Three Time Scales of Adaptation

DCA organizes learning into three time scales, each with its own mechanism and risk profile:

| Time scale | Latency | Mechanism | What it changes |
|---|---|---|---|
| **Fast** | <1 ms | Reflex lookup | Which known situation dispatches which lean |
| **Heartbeat** | ~30 s | Conductor intervention | Prompt version, inference parameters, action-policy weights |
| **Slow** | ~1 week | LoRA distillation | Low-rank weights of the local thinker |

The fast scale is cheap and safe but can only repeat what has been learned. The heartbeat scale is where most qualitative improvement happens; it is also where the system can fool itself with placebo effects, which is why trust scoring and sham interventions are required. The slow scale is the most dangerous: a fine-tuned adapter can entrench existing biases, so promotion is gated on held-out gains of at least 10%.

## 3.5 Tempo as a First-Class Substrate

In standard AI systems, time is either ignored or represented as a timestamp. DCA treats tempo as a first-class substrate. Every event is placed on a shared tempo map characterized by:

\[
\mathcal{M} = (\text{BPM}, \text{beat}, \text{measure}, \text{phrase}, \text{groove}, \text{channel}, \text{velocity}).
\]

A build command is not merely `place block at (x,y,z)`; it is `place block at tick 48, beat 1 of measure 3, channel 0 (Lucineer), velocity 87, after a 16th-note rest`. This encoding captures:

- **When** the action occurs in musical time;
- **Who** performs it;
- **How much weight** it carries;
- **How it relates** to the preceding and following events.

The MIDI-like representation enables pattern matching over rhythms of play. A session becomes a sequence

\[
B_8{:}E_{72}{:}v_{85} \;\to\; B_{16}{:}I_{67}{:}v_{60} \;\to\; B_4{:}W{:}v_{30},
\]

where \(B\) is beat, \(E\)/\(I\)/\(W\) are explore/inspect/wait, and \(v\) is velocity. This string is embedded with bge-m3 and stored in the vector index, making temporal patterns searchable.

The philosophical claim—drawn from the Slackwater design—is that "in the pocket" is a measurable system state. When agents and player share the tempo map, a harmony error signal \(\Phi\) drops toward zero. Tempo is not decoration; it is the coordination substrate.

## 3.6 Interventions and the Semantic Gradient

The conductor's output is an **intervention** \(\delta\). Unlike a gradient \(\nabla_\theta \mathcal{L}\), which is a numeric vector in weight space, an intervention is a structured edit to the conditions of generation:

\[
\delta_{\text{prompt}}: \pi \mapsto \pi' \quad \text{(e.g., "urge specificity about materials")},
\]
\[
\delta_{\text{param}}: \theta \mapsto \theta' \quad \text{(e.g., temperature } T \mapsto T + 0.1\text{)},
\]
\[
\delta_{\text{policy}}: w \mapsto w' \quad \text{(e.g., boost curiosity weight when stuck)}.
\]

The set of allowable interventions is finite and versioned. Each intervention records a before-state, an after-state, the context archetype in which it was applied, and a measurement window. This makes every conductor decision auditable and revertible.

The "semantic gradient" is the measured effect of an intervention on the quality vector over the window:

\[
\nabla_\delta \mathbf{q} = \mathbb{E}[\mathbf{q}_{\text{after}}] - \mathbb{E}[\mathbf{q}_{\text{before}}] - \mathbb{E}[\mathbf{q}_{\text{sham}} - \mathbf{q}_{\text{before}}],
\]

where the sham term corrects for the placebo effect that any change produces temporary improvement. An intervention is promoted only if \(\nabla_\delta \mathbf{q}\) is positive on at least one axis and non-negative on the others, relative to the sham arm.

## 3.7 Conservation Laws as Runtime Invariants

The final foundational concept is that conservation laws are not design aspirations but executable invariants. Four laws govern every DCA instance:

1. **Token conservation.** Every LLM call debits a session budget. Exhaustion downshifts the cascade to Gate 1/2 rather than blocking.
2. **Action conservation.** No action reaches the world without a logged command bottle.
3. **Identity conservation.** Every artifact carries the prompt, policy, and model version that produced it.
4. **Evolution conservation.** No parameter changes without a recorded intervention and a measurement window.

These laws make the system accountable. They also make regression testing possible: a recorded bottle ledger can be replayed against a null adapter, and the same seed must produce the same ledger byte-for-byte.

## 3.8 Summary

DCA is built from a small set of precisely defined concepts: a stream of thoughts, a narrow intent channel, a multi-dimensional quality vector, three time scales of adaptation, a tempo substrate, semantic interventions, and conservation laws. The next section assembles these primitives into a formal model.
