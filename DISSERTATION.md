# Dynamic Cognition Amplification: Establishing a New Category of Science

**Author:** KimiCode K2.7, Doctoral Candidate
**Date:** 2026-08-03
**Advisory Board:** Claude Opus (Fable), DeepSeek V3, OpenCode DeepSeek V4

---

# Abstract

Dynamic Cognition Amplification (DCA) is proposed as a new subfield of machine learning in which a small, fast cognitive process operates continuously inside an environment while a larger, slower process observes that stream and modifies the *conditions* under which the fast process thinks. We formalize this as a dual-time-scale system \(\mathcal{S} = (\mathcal{T}, \mathcal{C}, \mathcal{W})\), where \(\mathcal{T}\) is the local thinker producing a thought stream \(\tau_1, \tau_2, \ldots\) at 1–2 Hz, \(\mathcal{C}\) is the conductor intervening every \(n\) thoughts (typically \(n=30\), i.e., ~30 s), and \(\mathcal{W}\) is the world port yielding observations \(o_t\) and outcomes \(r_t\).

In contrast to offline training, where a model is fit on a fixed dataset and then deployed, DCA treats the stream of consciousness itself as the training signal. The loss is not a pre-specified scalar but a multi-dimensional play-quality vector \(\mathbf{q} = (q_{\text{novelty}}, q_{\text{specificity}}, q_{\text{engagement}}, q_{\text{spatial}})\). The gradient is a structured intervention \(\delta \in \Delta\) over prompts, inference parameters, and action-policy weights. A model update occurs at three time scales: reflex compilation (<1 ms), compiled-policy evolution (heartbeat), and trust-weighted conductor revision (30 s), with optional low-rank adaptation (LoRA) on the slowest weekly scale.

We instantiate DCA in *Thought Amplifier*, a substrate-independent engine whose core is separated from domain adapters by the `Observation/Thought/Action/Outcome` port boundary. The system enforces a three-gate cascade (reflex → policy → LLM), a `.bottle` provenance ledger, and four executable conservation laws (token, action, identity, evolution). Empirical targets, derived from predecessor systems, include: ≥50% of decisions served at zero marginal cost, ≥40% reflex hit rate after one hour of play, and conductor trust scores correlating ≥0.6 with measured quality improvement against a sham-intervention control.

The dissertation argues that DCA constitutes a distinct research program because its objective is qualitative ("better thoughts") rather than quantitative loss minimization, its gradient is semantic and periodic rather than numeric and per-example, and its evaluation requires live directed play rather than held-out static benchmarks.

**Keywords:** dynamic cognition amplification, continuous learning, stream of consciousness, conductor–thinker architecture, qualitative machine learning, reflex compilation, trust scoring, temporal cognition.


---


# 1. Introduction

## 1.1 The Static-Model Problem

Contemporary machine learning largely follows a batch-and-deploy rhythm. A model is trained on a fixed corpus, evaluated on a held-out set, and then frozen until the next retraining cycle. Even systems labeled "online" typically optimize a pre-defined scalar loss over stationary gradients. This paradigm has produced remarkable results, but it leaves untouched a class of problems in which the objective is not a fixed function and the training signal is the model's own ongoing experience.

Consider an artificial agent that is meant to keep a human player company in an open-ended world. There is no terminal state, no correct answer, and no single reward. The agent must think continuously, act safely, and—crucially—*improve its thinking* while it is thinking. Batch retraining is too slow, and conventional reinforcement learning collapses because the reward is not a scalar but a multi-dimensional judgment such as "this thought was specific, novel, and spatially aware." Dynamic Cognition Amplification (DCA) is the study of systems that learn under exactly these conditions.

## 1.2 What DCA Is

DCA studies dual-time-scale cognitive systems in which:

- A **local thinker** \(\mathcal{T}\) generates a stream of thoughts \(\tau_1, \tau_2, \ldots\) at high frequency (1–2 Hz);
- A **conductor** \(\mathcal{C}\) observes the stream and intervenes periodically (every \(n\) thoughts, typically \(n=30\), ~30 s);
- A **world port** \(\mathcal{W}\) supplies observations \(o_t\) and outcomes \(r_t\); and
- The system's objective is qualitative improvement of the thought stream itself.

Formally, let the state at thought \(t\) be \(s_t = (o_t, h_t, \pi_t, \theta_t)\), where \(o_t\) is the world observation, \(h_t\) is the recent thought history, \(\pi_t\) is the action-selection policy, and \(\theta_t\) parametrizes the thinker. The thinker samples a thought and a lean:

\[
(\tau_t, \ell_t) \sim \mathcal{T}(\,\cdot\, \mid s_t).
\]

The lean \(\ell_t\) is a short intent phrase (e.g., `inspect tower_top`) that an algorithmic layer maps to a concrete action \(a_t \sim \pi_t(\,\cdot\, \mid \ell_t, o_t)\). After the world returns outcome \(r_t\), the quality scorer produces a vector

\[
\mathbf{q}_t = (q_{\text{novelty}}, q_{\text{specificity}}, q_{\text{engagement}}, q_{\text{spatial}})_t \in [0,1]^4.
\]

Every \(n\) thoughts, the conductor proposes an intervention

\[
\delta \in \Delta = \Delta_{\text{prompt}} \cup \Delta_{\text{param}} \cup \Delta_{\text{policy}}
\]

intended to shift the distribution of future \(\mathbf{q}\). The system then measures whether the shift occurred. This is the core DCA loop:

\[
\text{think} \to \text{measure} \to \text{intervene} \to \text{measure again} \to \text{learn what helps}.
\]

## 1.3 Why This Is a New Subfield

DCA differs from existing paradigms in three ways that justify treating it as a distinct research program.

**Qualitative objective.** The target is not minimization of a pre-defined loss but improvement of thought quality along interpretable axes. The conductor is closer to a director coaching an improviser than to gradient descent on a fixed target.

**Semantic gradient.** The update \(\delta\) is a structured, human-readable modification ("be more specific about materials") rather than a numeric weight delta. Its effect is measured statistically over a window of thoughts, not back-propagated from a single example.

**Live evaluation.** Progress cannot be judged on a static test set because the distribution of situations is non-stationary and the conductor itself changes that distribution. Evaluation requires controlled directed play, sham-intervention arms, and conservation-law checks.

## 1.4 Empirical Precedents

The mechanisms in this dissertation are not invented; they are generalized from working systems.

| Precedent | Extracted law | DCA use |
|---|---|---|
| **Pincher** (SuperInstance, 2026) | Vector DB is the runtime; LLM is the compiler. Reflex dispatch <1 ms at $0; confidence update saturates in \([0.05, 0.95]\). | Tier-0 reflex gate and confidence dynamics. |
| **Lever Runner** | Three-gate cascade: guard (~50 µs) → embedding cache (~7.6 ms, 44% hit) → LLM (~500 ms). Asymmetric trust: +1.5 / −4.0. | Recurring cascade pattern and trust tuning. |
| **ZeroClaw Arena** | Tile-decomposed state, independent per-tile statistics, EMA \(\alpha=0.05\), compile to O(1) hash lookup. | Policy breeding and archetype discovery. |
| **SuperInstance** | `.bottle` typed envelopes; conservation laws; 10% canary → review → merge; anti-oscillation via hysteresis. | Provenance ledger and governance. |
| **Craftmind** | Write every outcome back to the vector index; the library of refined plans grows itself. | Memory writeback loop. |

These precedents converge on a single shape: cheap gates in front of expensive ones, explicit provenance, asymmetric trust, and conservation laws enforced at runtime.

## 1.5 Contributions and Testable Claims

This dissertation makes the following contributions:

1. **A formal definition of DCA** as a family of dual-time-scale systems with qualitative objectives and semantic gradients (Section 4).
2. **A substrate-independent reference architecture**, Thought Amplifier, separating the cognition engine from domain adapters behind the `Observation/Thought/Action/Outcome` port boundary (Section 7).
3. **Five interacting subsystems**: reflex compiler, evolution engine, trust scoring, temporal→vector pipeline, and LoRA distillation (Sections 5, 6, 8).
4. **Executable conservation laws** for token budget, action provenance, identity, and parameter change (Section 9).
5. **An evaluation protocol** using sham interventions, held-out states, and replay determinism (Section 10).

The claims are stated in testable form:

- **C1 (Cost gate):** At least 50% of decisions are served at zero marginal cost after one hour of operation.
- **C2 (Reflex convergence):** Reflex hit rate reaches ≥40% after one hour of play.
- **C3 (Trust validity):** Conductor trust scores correlate ≥0.6 with measured quality improvement against a sham-intervention arm.
- **C4 (Policy superiority):** Evolved policy beats hand-tuned weights by ≥15% on held-out states.
- **C5 (Determinism):** A recorded `.bottle` ledger replays to identical output under the null adapter.

## 1.6 Roadmap

The remainder of the dissertation is organized as follows. Section 2 reviews related work in continual learning, interactive machine learning, and reflex-based systems. Section 3 introduces foundational concepts: the stream of consciousness, the lean/action split, and quality decomposition. Section 4 presents the formal DCA model. Section 5 develops the three-gate cascade and reflex compiler. Section 6 describes the conductor and trust scoring. Section 7 covers temporal cognition and the MIDI→vector pipeline. Section 8 treats distillation and the slowest loop. Section 9 lays out the system architecture and conservation laws. Section 10 details experiments and evaluation. Section 11 reports results. Section 12 discusses implications and limitations. Section 13 concludes.


---


# 2. Related Work and Precedents

This chapter situates Dynamic Cognition Amplification (DCA) against five strands of prior work: offline supervised training, continual and lifelong learning, reinforcement learning from feedback, tool-calling agent frameworks, and recent reflex-based agent operating systems. The goal is not to claim that DCA has no antecedents—it clearly does—but to identify the specific conjunction of properties that existing work does not address: a *continuous* stream of thought, a *semantic* gradient operating on the generator's conditions rather than its weights, and a *qualitative* objective evaluated through directed live play.

## 2.1 Offline Training and the Static-Model Assumption

The dominant paradigm in modern machine learning is to fit a model \(f_\theta\) on a fixed dataset \(\mathcal{D}\), validate on a held-out set, and deploy. The objective is a scalar \(\mathcal{L}(\theta; \mathcal{D})\) and the update is gradient descent:

\[
\theta_{t+1} = \theta_t - \eta \nabla_\theta \mathcal{L}(\theta_t; \mathcal{D}).
\]

This framework underlies large-language-model pre-training, supervised fine-tuning, and most production NLP systems. Its strengths are stability, reproducibility, and strong generalization when \(\mathcal{D}\) is large and stationary. Its weakness, for the problems DCA targets, is that the distribution of experience is neither fixed nor under the model's control. In open-ended companion systems, the "test set" is tomorrow's play session, and the model's own interventions change the data-generating process.

Attempts to adapt offline training to non-stationary settings include periodic retraining, experience replay, and meta-learning. These methods still assume that improvement happens *between* deployment episodes, not *during* them. DCA, by contrast, treats deployment as the training environment.

## 2.2 Continual and Lifelong Learning

Continual learning studies models that accumulate knowledge from a sequence of tasks while mitigating catastrophic forgetting (McCloskey & Cohen, 1989; Kirkpatrick et al., 2017). Methods include elastic weight consolidation, memory replay, and architecture growth. Lifelong learning extends this to open-ended experience (Thrun, 1998; Silver et al., 2013).

These fields share DCA's interest in non-stationarity and accumulation. However, they typically:

- Assume a sequence of discrete tasks with known boundaries;
- Optimize a pre-defined loss on each task;
- Update weights, not the prompting or inference conditions under which the model operates.

DCA relaxes all three assumptions. There are no task boundaries—only a continuous stream of thought. The objective is a multi-dimensional quality vector, not a fixed loss. And the fastest updates happen above the weights (reflexes, policy tables, prompt versions), with weight-level changes (LoRA) reserved for the slowest loop.

## 2.3 Reinforcement Learning from Human Feedback

RLHF (Christiano et al., 2017; Ouyang et al., 2022) trains a reward model from pairwise preferences and optimizes a policy against it with PPO. The reward model converts a qualitative judgment into a scalar, and the policy update is per-example reinforcement.

DCA differs in two ways. First, the "reward" is not a single scalar but a decomposed quality vector \(\mathbf{q} = (q_{\text{novelty}}, q_{\text{specificity}}, q_{\text{engagement}}, q_{\text{spatial}})\). Second, the gradient is not a weight update but a structured intervention \(\delta\) applied to prompts, parameters, or policy weights. The conductor's role is analogous to a meta-optimizer that searches over the *conditions* of generation, not over the generator's weights directly. This is closer in spirit to prompt optimization (Shin et al., 2020; Zhou et al., 2023) and meta-prompting (Sorensen et al., 2022), but those methods still operate offline or on static benchmarks, whereas DCA operates online and on a live stream.

## 2.4 Tool-Calling Agents and ReAct

Modern agent frameworks such as ReAct (Yao et al., 2023), AutoGPT, and LangChain agents place the LLM in a loop: observe → reason → emit tool call → execute → observe again. The LLM is the runtime; it produces executable commands or API calls on every step.

This design has two well-known failure modes. First, it is expensive: every decision costs full LLM inference and every tool schema must be shipped in context. Second, it is unsafe: a compromised or misaligned LLM can emit arbitrary commands. Recent analyses of production coding agents report injection vulnerabilities and hallucinated tool invocations as primary risks (Greshake et al., 2023).

The systems studied in this dissertation invert the relationship. Pincher and Lever Runner show that the LLM can be moved out of the hot path: it compresses input to an intent phrase, and a pre-approved table dispatches the action. Lever Runner's measured token budget is ~76 tokens per query versus ~2,000–5,000 for conventional tool-calling assistants—a 28× reduction—and ~56% of queries cost zero tokens after the cache warms. More importantly, the structural security property holds: the LLM's output channel is too narrow to encode shell injection, so exploitation is impossible regardless of prompt engineering.

## 2.5 Reflex-Based Agent Operating Systems

The most direct precedents are the SuperInstance family of systems: Pincher, Lever Runner, ZeroClaw Arena, and the SuperInstance ecosystem itself.

**Pincher** implements the "vector DB as runtime, LLM as compiler" inversion. It classifies matches into Exact (≥0.80), Similar (0.55–0.80), and Novel (<0.55); executes Exact matches directly; and compiles novel interactions into parameterized reflexes. Confidence updates saturate: success adds \(0.05(1-c)\), failure subtracts \(0.10c\), clamped to \([0.05, 0.95]\). A SHA-256 trigram/word hash provides deterministic fallback when ONNX is unavailable.

**Lever Runner** adds the three-gate cascade and structural security. Gate 1 is a Rust fastloop guard (~50 µs); Gate 2 is an embedding cache with LanceDB cosine search (~200 µs–7.6 ms, 44% hit rate); Gate 3 is LLM intent extraction (~500 ms). Trust is asymmetric: +1.5 for success, −4.0 for failure, floor 40, ceiling 100. The system gets faster as it accumulates knowledge of both good and bad inputs.

**ZeroClaw Arena** proves that non-neural policy learning works for bounded-state games. It decomposes states into tiles, updates tile scores by EMA \(\alpha=0.05\), clamps scores to \([0.05, 0.95]\), and compiles the result to a zero-dependency `dict[str, str]` (~15 KB for Tic-Tac-Toe, ~0.001 ms per move). Reward-conditioned evolution discovers strategy archetypes (Explorer, Diplomat, Marksman, Climber, Prospector) without human enumeration.

**SuperInstance ecosystem** generalizes these into a four-layer meta-architecture: Execution → Memory → Intelligence → Identity. It proposes the `.bottle` protocol for typed causal messaging and four conservation laws (token, action, identity, evolution). Its own audit notes that most code is incomplete; the value lies in the design patterns and the honest falsification of early conservation-law conjectures.

## 2.6 What Is Missing

Table 2.1 summarizes the gap. No existing system combines all of the following: continuous thought generation, semantic gradient on generation conditions, qualitative multi-objective evaluation, runtime conservation laws, and substrate-independent architecture.

| Property | Offline training | Continual learning | RLHF | Tool-calling agents | Reflex systems | **DCA** |
|---|---|---|---|---|---|---|
| Continuous operation | No | Sometimes | No | Yes | Yes | **Yes** |
| Qualitative objective | No | No | Partial | No | No | **Yes** |
| Semantic gradient on conditions | No | No | No | No | No | **Yes** |
| Three-gate cost cascade | No | No | No | No | Yes | **Yes** |
| Conservation laws enforced | No | No | No | No | Partial | **Yes** |
| Substrate-independent core | No | No | No | No | No | **Yes** |

**Table 2.1:** Positioning of DCA against prior paradigms.

## 2.7 Testable Claims Derived from Precedents

The precedents justify specific numerical targets. Pincher and Lever Runner demonstrate that ~56% of decisions can be served at zero marginal cost with a 44% embedding-cache hit rate; DCA targets ≥50% zero-cost decisions and ≥40% reflex hit rate after one hour. ZeroClaw shows that EMA policy evolution with \([0.05, 0.95]\) clamping discovers robust strategies; DCA targets ≥15% improvement over hand-tuned weights. SuperInstance's conservation-law framework provides the governance targets; DCA makes them executable and tests them over 1,000-loop property tests. These numbers are not aspirational—they are the empirical bar inherited from the deep dives.

## References

- Christiano, P. F., Leike, J., Brown, T., Martic, M., Legg, S., & Amodei, D. (2017). Deep reinforcement learning from human preferences. *NeurIPS*, 30.
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. *ACM CCS*.
- Kirkpatrick, J., Pascanu, R., Rabinowitz, N., et al. (2017). Overcoming catastrophic forgetting in neural networks. *PNAS*, 114(13), 3521–3526.
- McCloskey, M., & Cohen, N. J. (1989). Catastrophic interference in connectionist networks: The sequential learning problem. *Psychology of Learning and Motivation*, 24, 109–165.
- Ouyang, S., Wu, J., Jiang, X., et al. (2022). Training language models to follow instructions with human feedback. *NeurIPS*, 35.
- Shin, T., Razeghi, Y., Logan IV, R. L., Wallace, E., & Singh, S. (2020). AutoPrompt: Eliciting knowledge from language models with automatically generated prompts. *EMNLP*.
- Silver, D., Yang, Q., & Li, L. (2013). Lifelong machine learning systems: Beyond learning algorithms. *AAAI Spring Symposium*.
- Sorensen, T., Robinson, J., Khashabi, D., et al. (2022). Anatomize an evaluator: Learning from PaLM failures. *arXiv:2212.10496*.
- Thrun, S. (1998). Lifelong learning algorithms. *Learning to Learn*, 181–209.
- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. *ICLR*.
- Zhou, Y., Muresanu, A. I., Han, Z., Paster, K., et al. (2023). Large language models are human-level prompt engineers. *ICLR*.


---


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


---


# 4. A Formal Model of Dynamic Cognition Amplification

This chapter presents a mathematical model of DCA. The model is deliberately general: it describes any system in which a fast cognitive process generates a stream of thoughts while a slower process modifies the conditions under which those thoughts are generated. We then instantiate the model for the Thought Amplifier reference architecture.

## 4.1 System Definition

A DCA system is a tuple

\[
\mathcal{S} = (\mathcal{T}, \mathcal{C}, \mathcal{W}, \mathcal{M}, \mathcal{Q}, \mathcal{B}, \mathcal{L}),
\]

where:

- \(\mathcal{T}\) is the **local thinker**, a function that produces thoughts;
- \(\mathcal{C}\) is the **conductor**, a function that proposes interventions;
- \(\mathcal{W}\) is the **world port**, providing observations and accepting actions;
- \(\mathcal{M}\) is the **memory store**, including reflexes, policies, and vectors;
- \(\mathcal{Q}\) is the **quality scorer**, mapping outcomes to quality vectors;
- \(\mathcal{B}\) is the **bottle ledger**, an append-only provenance log;
- \(\mathcal{L}\) is the set of **conservation laws** enforced at runtime.

Time is discrete and indexed by thought number \(t = 1, 2, \ldots\). The thinker operates at every \(t\). The conductor operates every \(n\) thoughts, where \(n\) is a hyperparameter (typically \(n=30\), corresponding to ~30 s of play).

## 4.2 State Space

The world port yields observations \(o_t \in \mathcal{O}\). The thinker's state at time \(t\) is

\[
s_t = (o_t, h_t, \pi_t, \theta_t, \beta_t) \in \mathcal{S},
\]

where:

- \(o_t\) is the current observation;
- \(h_t = (\tau_{t-k}, \ldots, \tau_{t-1})\) is the recent thought history, truncated to window \(k\);
- \(\pi_t\) is the current system prompt;
- \(\theta_t\) is the vector of inference parameters (temperature, top-p, repetition penalty, etc.);
- \(\beta_t\) is the action-policy weight vector.

The conductor maintains a meta-state \(\sigma_t\) that includes trust scores, intervention history, and the self-model:

\[
\sigma_t = (\tau_{t}, \iota_{t}, \chi_{t}),
\]

where \(\tau_t\) is a trust table, \(\iota_t\) is the intervention log, and \(\chi_t\) is the self-model mapping context archetypes to expected intervention effects.

## 4.3 Thought Generation

The thinker samples a thought and a lean from a distribution conditioned on the state:

\[
(\tau_t, \ell_t) \sim P_\mathcal{T}(\,\cdot\, \mid s_t).
\]

The lean \(\ell_t\) belongs to a fixed vocabulary \(\mathcal{L}_{\text{lean}}\) of validated intent phrases. The action layer maps the lean to a concrete action:

\[
a_t = \mathcal{A}(\ell_t, o_t, \beta_t) \in \mathcal{A}_{\text{world}}.
\]

The action \(a_t\) is submitted to the world port, which returns an outcome:

\[
r_t = \mathcal{W}(a_t) \in \mathcal{R}.
\]

The quality scorer then produces

\[
\mathbf{q}_t = \mathcal{Q}(\tau_t, a_t, r_t, o_t) \in [0,1]^4.
\]

## 4.4 The Three-Gate Cascade

Before invoking the thinker, the system checks three gates in order. Let \(g_t\) be the gate through which thought \(t\) is served.

**Gate 1: Reflex.** Given observation \(o_t\), compute a situation signature \(\sigma(o_t)\) and query the reflex store:

\[
(\ell^*_t, c^*_t) = \mathcal{M}_{\text{reflex}}(\sigma(o_t)).
\]

If a reflex matches with confidence \(c^*_t \geq \theta_{\text{direct}} = 0.80\), set \(g_t = 1\), \(\ell_t = \ell^*_t\), and skip the LLM. If \(0.55 \leq c^*_t < 0.80\), set \(g_t = 1'\) (confirm-and-execute). If \(c^*_t < 0.55\), proceed to Gate 2.

**Gate 2: Compiled policy.** Query the compiled policy table:

\[
\ell^*_t = \mathcal{M}_{\text{policy}}(\kappa(o_t)),
\]

where \(\kappa(o_t)\) is a tile hash of the context. If the policy returns a lean, set \(g_t = 2\) and skip the LLM. Otherwise proceed to Gate 3.

**Gate 3: LLM.** Sample \((\tau_t, \ell_t) \sim P_\mathcal{T}(\,\cdot\, \mid s_t)\). The thought and its resulting reflex candidate are recorded for possible compilation into Gate 1.

The cost gate requires

\[
\Pr[g_t \in \{1, 2\}] \geq 0.50
\]

after one hour of operation, where the probability is taken over the empirical distribution of situations encountered.

## 4.5 Conductor Interventions

Every \(n\) thoughts, the conductor observes the window

\[
W_t = (\tau_{t-n+1}, \ldots, \tau_t, \mathbf{q}_{t-n+1}, \ldots, \mathbf{q}_t)
\]

and proposes an intervention \(\delta \in \Delta\). The candidate interventions are generated by a large model or a heuristic analyzer:

\[
\mathcal{C}(W_t, \sigma_t) \to \{ \delta_1, \ldots, \delta_m \}.
\]

Each candidate is scored by the self-model and trust table:

\[
\text{score}(\delta_i) = \tau_t(\text{type}(\delta_i), \text{archetype}(o_t)) + \chi_t(\text{type}(\delta_i), \text{archetype}(o_t)).
\]

The system applies the highest-scoring candidate, records it as a `.bottle` command, and begins a measurement window of length \(m\) thoughts. A parallel sham intervention is logged but not applied; its effect is subtracted to control for novelty bias.

## 4.6 Trust Dynamics

Let \(T(c, k)\) be the trust score for intervention type \(c\) in context archetype \(k\). After measuring the effect \(\nabla_\delta \mathbf{q}\), the trust update is

\[
T(c, k) \leftarrow T(c, k) + \eta_+ \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \succ 0] - \eta_- \cdot \mathbb{1}[\nabla_\delta \mathbf{q} \prec 0],
\]

where \(\eta_+ = 0.5\), \(\eta_- = 2.0\), and updates occur only after at least \(N_{\min} = 10\) observations. The symbol \(\succ\) means "improves relative to the sham arm on at least one quality axis without degrading on any other." Trust is bounded by construction: \(T(c,k) \in [0, 100]\).

If three consecutive interventions of type \(c\) in archetype \(k\) produce negative measured effects, the system auto-reverts to the previous prompt/policy version and imposes a dwell time \(d(c,k)\) before \(c\) can be applied again.

## 4.7 Multi-Time-Scale Update Rules

DCA's learning mechanisms operate at three time scales. Let \(\Delta t\) denote the period.

**Fast (\(\Delta t < 1\) ms): reflex update.** After a Gate-3 thought resolves, if its signature is novel, compile it into a reflex with initial confidence \(c_0 = 0.5\). After execution, update confidence:

\[
c \leftarrow \begin{cases}
c + 0.05(1 - c) & \text{on success}, \\
c - 0.10c & \text{on failure},
\end{cases}
\]

clamped to \([0.05, 0.95]\). A reflex also carries a counter of consecutive uses; after \(N_{\text{escape}}\) identical dispatches, the system forces one Gate-3 call to prevent a high-confidence blind spot.

**Heartbeat (\(\Delta t \approx 30\) s): policy and prompt update.** The conductor applies trust-scored interventions. Separately, the evolution engine refines tile scores:

\[
w_{i} \leftarrow w_{i} + 0.05 \left( \frac{\text{wins}_i}{\text{visits}_i} - w_i \right),
\]

clamped to \([0.05, 0.95]\). Hierarchical clustering of context tiles produces ~8 strategy archetypes.

**Slow (\(\Delta t \approx 1\) week): LoRA distillation.** Select thoughts with quality \(> 0.7\), positive conductor commentary, and successful outcomes. Form SFT pairs \((s, \tau)\) and DPO preference pairs from matched high/low quality states. Train a LoRA adapter with rank \(r \in [8, 16]\), batch size 1–4, sequence length 512–1024. Promote the adapter only if it beats the base model by ≥10% on a held-out evaluation set.

## 4.8 Conservation Laws

The laws \(\mathcal{L}\) are predicates that must hold at every timestep. Let \(B_t\) be the set of bottles logged through time \(t\).

**Token conservation.** Let \(B_{\text{budget}}\) be the session token budget and \(B_{\text{spent}}(t)\) the cumulative LLM tokens consumed. Then

\[
B_{\text{spent}}(t) \leq B_{\text{budget}} \;\lor\; g_{t'} \in \{1, 2\} \; \forall t' > t_0,
\]

where \(t_0\) is the time at which the budget is exhausted. The system downshifts rather than halts.

**Action conservation.** For every action \(a_t\) reaching the world, there exists a command bottle \(b \in B_t\) with \(b.\text{kind} = \text{command}\) and \(b.\text{payload} = a_t\).

**Identity conservation.** Every bottle \(b\) carries metadata \((\pi, \theta, \beta, \text{model})\) identifying the conditions under which it was produced.

**Evolution conservation.** Every mutation of \((\pi, \theta, \beta)\) is caused by a logged intervention bottle in \(B_t\).

These laws are checked by property tests over 1,000-loop runs and by the import-linter boundary that prevents the substrate-independent core from importing domain-specific code.

## 4.9 Instantiation for Thought Amplifier

In the reference implementation, the world port is Roblox via the Slackwater adapter; the thinker is Granite 3.1 2B via Ollama; the conductor is GLM-5.2 or DeepSeek V3; the memory store uses sqlite-vec for reflexes and Cloudflare Vectorize for large-scale semantic search; and the bottle ledger is an append-only JSONL file. The null adapter replaces every port with deterministic fakes, enabling regression tests that replay a session to identical output.

The model is not tied to these choices. Any triple \((\mathcal{T}, \mathcal{C}, \mathcal{W})\) satisfying the port contracts and conservation laws is a DCA instance. This substrate independence is what makes DCA a subfield rather than a single system.


---


# 5. The Three-Gate Cascade and Reflex Compiler

This chapter describes the fastest loop in DCA: the three-gate cascade that decides how a thought is served, and the reflex compiler that turns expensive Gate-3 thoughts into cheap Gate-1 habits. The design goal is to make the majority of decisions free, fast, and interpretable while preserving the system's ability to handle novelty.

## 5.1 The Recurring Three-Gate Pattern

The three-gate pattern appears at multiple levels of DCA. Each gate is strictly cheaper than the one that follows it, and each gate is a binary or ternary classifier that routes the request toward the cheapest adequate handler.

| Level | Gate 1 (free) | Gate 2 (cheap) | Gate 3 (expensive) |
|---|---|---|---|
| Thinking | reflex hit (<1 ms) | compiled policy lookup (O(1)) | LLM inference (~500 ms) |
| Conducting | trust check on modification type | temporal pattern precedent | Conductor LLM (~10 s) |
| Acting | veto engine | cooldown/novelty filter | game-side execution |

The pattern is inherited from Lever Runner, whose measured latencies are Gate 1 Rust guard ~50 µs, Gate 2 embedding cache ~200 µs–7.6 ms, and Gate 3 LLM ~500 ms. In DCA we generalize it from command execution to thought generation and conductor deliberation. A subsystem that does not have this shape is, by the design specification, wrong.

## 5.2 Gate 1: Reflex Dispatch

A **reflex** is a stored mapping from a situation signature to a lean, together with a confidence score and execution history. When an observation \(o_t\) arrives, the system computes a signature \(\sigma(o_t)\), embeds it, and queries the reflex store:

\[
(\ell^*, c^*) = \text{ReflexStore.query}(\sigma(o_t)).
\]

The match is classified by cosine similarity \(\rho\) and confidence \(c^*\):

\[
\text{classify}(\rho, c^*) = \begin{cases}
\text{Exact} & \rho \geq 0.80 \text{ and } c^* \geq 0.80, \\
\text{Similar} & 0.55 \leq \rho < 0.80 \text{ or } 0.55 \leq c^* < 0.80, \\
\text{Novel} & \rho < 0.55 \text{ and } c^* < 0.55.
\end{cases}
\]

For an Exact match, the lean \(\ell^*\) is dispatched directly; no LLM is invoked. For a Similar match, the lean is dispatched but flagged for later refinement. For a Novel match, control passes to Gate 2.

The signature function \(\sigma\) must be deterministic and domain-agnostic. In the reference implementation it extracts: player bond tier, time of day, nearby structures, last action type, and a beat-position hash. No game-specific vocabulary (e.g., "stud", "bond tier") appears in the substrate-independent core; the adapter maps raw game state to these abstract fields.

## 5.3 Confidence Dynamics

Reflex confidence evolves with feedback. Let \(c\) be the current confidence. After execution:

\[
c \leftarrow \begin{cases}
c + 0.05(1 - c) & \text{on success}, \\
c - 0.10c & \text{on failure},
\end{cases}
\]

clamped to \([0.05, 0.95]\). This is the additive form specified in the Fable master prompt; Pincher uses a multiplicative form \(\times 1.005\)/\(\times 0.95\). The additive form is chosen because it saturates more gracefully: gains shrink as confidence rises, and losses shrink as confidence falls.

The clamp is essential. A floor of 0.05 guarantees that a reflex can recover from repeated failures; a ceiling of 0.95 guarantees that the system never treats any reflex as certain. Certainty is the enemy of learning.

## 5.4 Escape Hatch: Max Consecutive Uses

Every reflex carries a `max_consecutive_uses` counter. After \(N\) identical dispatches, the system forces one Gate-3 call even on a confident hit. Without this, a high-confidence wrong reflex becomes a permanent blind spot: the system stops sampling the evidence that would correct it.

The escape hatch embodies the Lucineer philosophy that "every reflex has gaps." It is not a safety exception; it is a learning requirement. The choice of \(N\) is a hyperparameter; in the reference implementation it is set per reflex based on its age and confidence, with a global floor of 5.

## 5.5 Gate 2: Compiled Policy Lookup

If Gate 1 misses, the system checks a compiled policy table. The policy is produced by the evolution engine (Chapter 6) and maps context tiles to leans. The lookup is O(1):

\[
\ell^* = \text{PolicyTable}[\kappa(o_t)],
\]

where \(\kappa(o_t)\) is a tile hash of the context. The compiled policy is a pure `dict[str, str]`, <50 KB, zero dependencies, and hot-swapped at heartbeat.

Gate 2 is broader but coarser than Gate 1. A reflex matches a specific situation; a policy matches a class of situations. Gate 2 handles context archetypes that the evolution engine has discovered but that have not yet been refined into individual reflexes.

## 5.6 Gate 3: LLM Inference and Reflex Compilation

If both gates miss, the request reaches the LLM. The local thinker samples a thought and a lean conditioned on the current state. After the action executes and an outcome is observed, the system decides whether to compile the interaction into a reflex.

A thought is compiled if:

- the resulting action succeeded;
- the quality vector \(\mathbf{q}\) is above a threshold on at least one axis;
- the situation signature is sufficiently distinct from existing reflexes; and
- a veto engine approves the action as safe.

The compiled reflex stores:

```python
@dataclass(frozen=True)
class Reflex:
    signature: str
    lean: str
    embedding: list[float]
    confidence: float = 0.5
    successes: int = 0
    failures: int = 0
    max_consecutive_uses: int = 5
    schema: str = "reflex/v1"
```

The LLM is therefore a compiler, not a runtime. It fires once per novel situation and produces a reusable artifact. This is the opposite of tool-calling agents, where the LLM executes on every request.

## 5.7 Embedding Pipeline and Fallbacks

The reflex store uses bge-m3 embeddings by default. When the embedder is unavailable, it falls back to a deterministic feature hash. The hash combines trigram hashing for local structure, word hashing for semantic content, and global text hashing for overall similarity, then L2-normalizes. It will not match "show running processes" to "list active processes" as well as a neural embedder, but it is deterministic and never fails.

This fallback is a hard acceptance criterion. A reflex system that stops working when the embedding model is unavailable is a demo, not an instrument. The degradation ladder is:

| Embedding | Preferred | Fallback 1 | Fallback 2 | Never |
|---|---|---|---|---|
| Semantic | bge-m3 (Workers AI) | local sentence-transformers | deterministic feature hash | fail |
| Storage | sqlite-vec | hash bucket | in-memory linear scan | fail |

## 5.8 Storage and Portability

Reflexes are stored in sqlite-vec, a single-file SQLite extension with vector search. This gives sub-millisecond query latency and zero infrastructure. Reflexes can be exported as a `.nail` bundle—a `tar.zst` archive containing the SQLite database, manifest, identity, and configuration, verified by BLAKE3 hashes. The bundle makes agent state portable between devices and reproducible across test runs.

## 5.9 Acceptance Criteria

The Fable master prompt specifies the following acceptance criteria for the reflex compiler:

- Reflex check completes in <1 ms for 10,000 stored reflexes.
- After 1 hour of play, ≥40% of thoughts are served by reflexes (no LLM call).
- Reflex confidence correlates with action success rate (≥0.7 correlation).
- A `.nail` bundle can be exported, transferred to a fresh instance, and produce matching behavior.
- The zero-dependency hash fallback works when ONNX/bge-m3 is unavailable.

These criteria are enforced in CI by the contract-test suite and the latency-gate benchmarks.

## 5.10 Summary

The three-gate cascade is the cost and security backbone of DCA. Gate 1 handles known situations in sub-millisecond time at zero marginal cost. Gate 2 handles known context archetypes with a compiled policy. Gate 3 handles genuine novelty and compiles the result back into Gate 1. The reflex compiler, confidence dynamics, escape hatch, and deterministic fallback together make the system cheaper, faster, and safer as it learns.


---


# 6. Evolution Engine and Compiled Policies

Where the reflex compiler memorizes individual situations, the evolution engine generalizes across them. It treats action selection as a bounded-state game, learns per-context statistics through Monte Carlo simulation, and compiles the result into a zero-dependency lookup table. The engine contains no neural network; its update rule is a simple exponential moving average with a hard exploration-preserving clamp.

## 6.1 From Game Playing to Action Selection

ZeroClaw Arena learns games such as Tic-Tac-Toe and Connect 4 by decomposing board states into local tiles and accumulating win/loss statistics. The same algorithm applies to cognitive action selection if we define the "game" appropriately.

In DCA, the state of the action-selection game is a context tuple

\[
c = (\text{channel}, \text{sender_type}, \text{urgency}, \text{time_window}, \text{prior_context_hash}, \text{bond_tier}, \text{nearby_structures}),
\]

and the legal actions are the leans

\[
\mathcal{A} = \{\text{explore}, \text{approach}, \text{build}, \text{inspect}, \text{wait}, \text{speak}\}.
\]

The outcome is not win/loss but a satisfaction score derived from the quality vector:

\[
s = w_1 q_{\text{novelty}} + w_2 q_{\text{specificity}} + w_3 q_{\text{engagement}} + w_4 q_{\text{spatial}}.
\]

This mapping is the central insight of the ZeroClaw integration plan: the algorithm is domain-independent once the state, action, and outcome functions are supplied.

## 6.2 Tile Decomposition

A context is factored into **tiles**, each accumulating independent statistics. Example tile dimensions include:

- Channel (Discord, Telegram, in-game chat)
- Time window (morning, afternoon, evening, night)
- Bond tier (1–5)
- Urgency (low, medium, high)
- Proximity to structures (none, near foundation, near workshop)

For a given context, multiple tiles may activate. Each tile stores, for every action, the number of times the action was chosen and the sum of satisfaction scores. The effective score for an action in context \(c\) is the weighted combination of scores from all active tiles.

Tile decomposition prevents overfitting to exact contexts. A policy learned for "evening + bond tier 3" can partially inform "evening + bond tier 4" through shared tiles. It also makes the system interpretable: every decision traces to specific tile entries with observed counts and scores.

## 6.3 Monte Carlo Self-Play

During idle heartbeat cycles, the evolution engine runs Monte Carlo rollouts. For each candidate context, it simulates each legal action forward by sampling plausible subsequent contexts and outcomes. The simulation uses a lightweight world model that encodes simple causal rules: building near an unfinished structure tends to increase spatial awareness; speaking repeatedly without player response tends to decrease engagement; and so on.

For each action \(a\) in context \(c\), the rollout estimate is

\[
\hat{s}(c, a) = \frac{1}{N} \sum_{i=1}^{N} s_i,
\]

where \(s_i\) is the outcome of the \(i\)-th simulated trajectory. The estimate is blended with the learned tile score using a confidence weight:

\[
\text{value}(c, a) = \lambda \cdot \text{tile_score}(c, a) + (1 - \lambda) \cdot \hat{s}(c, a),
\]

where \(\lambda = \min(\text{visits}/20, 0.8)\). Early in learning, simulation dominates; later, empirical tile scores dominate.

## 6.4 Evolutionary Score Update

Every evolution cycle, tile scores move toward their empirical mean satisfaction:

\[
\text{score}(c, a) \leftarrow \text{score}(c, a) + 0.05 \left( \bar{s}(c, a) - \text{score}(c, a) \right),
\]

where \(\bar{s}(c, a)\) is the average observed satisfaction for action \(a\) in context \(c\). The update is clamped:

\[
\text{score}(c, a) \in [0.05, 0.95].
\]

The clamp guarantees that no action ever reaches probability 0 or 1. This is not a numerical convenience; it is a philosophical commitment. A policy that assigns probability 1 to an action has stopped learning. The 0.05 floor keeps exploration alive forever.

The 0.05 learning rate is deliberately slow. Cognitive outcomes are noisy; a faster rate would overfit to recent fluctuations. ZeroClaw's experiments validate this choice: the same rate produces robust policies across Tic-Tac-Toe, Connect 4, Go 9×9, and Hold'em.

## 6.5 Softmax Action Selection

During training, actions are selected by softmax over the value estimates with temperature \(T\):

\[
P(a \mid c) = \frac{\exp(\text{value}(c, a) / T)}{\sum_{a'} \exp(\text{value}(c, a') / T)}.
\]

A temperature sweep in ZeroClaw found the optimal range to be \(T \approx 0.15\)–\(0.3\). Lower temperatures exploit; higher temperatures explore. DCA uses \(T = 0.3\) during training and \(T \to 0\) when compiling the policy for deployment.

## 6.6 Policy Compilation

After training, the tile field is compiled into a pure lookup table:

\[
\text{CompiledPolicy}[\kappa(c)] = \arg\max_a \text{score}(c, a),
\]

where \(\kappa(c)\) is a deterministic hash of the context. The compiled artifact is a `dict[str, str]`, typically <50 KB, with zero runtime dependencies. Execution time is ~0.001 ms per decision.

Unknown contexts use Hamming-distance nearest-neighbor fallback: if a context hash differs from a known hash by at most 3 bits and the neighbor's score exceeds a threshold, the neighbor's action is returned. Otherwise, the request escalates to Gate 3 (LLM).

## 6.7 Hierarchical Clustering and Strategy Archetypes

Tile score vectors are clustered hierarchically into approximately 8 strategy archetypes. These archetypes are discovered, not designed. Examples that emerge from the data might include:

- `morning_builder`: high build weight, low speak weight, high specificity;
- `evening_explorer`: high explore weight, high engagement, low urgency;
- `storm_repairer`: high build/inspect weight, high tempo (Presto);
- `quiet_observer`: high wait weight, high spatial awareness.

The archetypes serve two purposes. First, they compress the policy: a hierarchical field with 8 clusters achieves ~10× compression with <5 percentage points of performance loss, matching ZeroClaw's result. Second, they feed the conductor's self-model: an intervention that helps `morning_builder` contexts may harm `evening_explorer` contexts.

## 6.8 Integration with the Three-Gate Cascade

The compiled policy is Gate 2 of the thinking cascade. Its relationship to Gate 1 (reflex) is hierarchical:

- Gate 1 matches a specific situation signature.
- Gate 2 matches a context archetype or tile hash.
- Gate 3 handles genuine novelty.

A reflex can be viewed as a highly specialized policy entry that has accumulated enough evidence to bypass the policy table entirely. Over time, successful policy entries may be promoted into reflexes, and failed reflexes may be demoted back to the policy table.

## 6.9 Acceptance Criteria

The Fable master prompt specifies:

- Policy converges within 2 weeks of training (score variance < 0.01 over 24 h).
- Evolved policy outperforms static weights by ≥15% on quality metrics.
- Compiled policy is a self-contained Python dict (<50 KB).
- Every decision is traceable to a specific tile entry (100% interpretability).
- Hierarchical clustering produces human-recognizable strategy archetypes.

The ZeroClaw integration plan adds operational targets: >70% fast-path hit rate, >80% positive satisfaction, and >50% LLM cost reduction on action selection.

## 6.10 Summary

The evolution engine is DCA's mechanism for learning *above* the weights. It uses tile decomposition, Monte Carlo simulation, EMA updates with a hard clamp, and policy compilation to produce millions of free, interpretable decisions. The guarantee of permanent exploration—the \([0.05, 0.95]\) clamp—ensures that the system never collapses onto a local optimum and never stops looking for better actions.


---


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


---


# 8. Temporal Cognition and the Vector Pipeline

Most AI systems treat time as a sequence of discrete states. DCA treats time as a substrate: events are placed on a shared tempo map, rhythms of play are canonized into strings, and those strings are embedded and stored for future recall. This chapter describes the temporal substrate, the MIDI→vector pipeline, and how temporal patterns inform the Conductor's decisions.

## 8.1 The Shared Tempo Map

Every DCA instance maintains a `SharedSessionTempoMap`:

\[
\mathcal{M} = (\text{baseBPM}, \text{swingFactor}, \text{rootMidiNote}, \text{ppq}, \text{currentTick}, \text{fermataActive}, \text{currentChordProgression}, \text{spatialLatticeOrigin}, \text{globalFrictionScore}).
\]

The map is the single source of truth for all temporal coordination. Only the `TempoService` can modify it, enforcing a single-writer pattern that prevents race conditions when tide, storm, and aurora events would otherwise update BPM simultaneously.

The tempo map serves two cognitive functions. First, it synchronizes agents and player so that "in the pocket" is a measurable state. Second, it provides the beat position \(b_t\) attached to every thought, making the thought stream a temporal signal rather than merely a sequence.

## 8.2 MIDI Encoding of Events

Game events are encoded as MIDI-like messages. A build command is not merely `place block at (x,y,z)`; it carries:

- `targetTick`: when the action should occur;
- `agentChannel`: which agent lane performs it;
- `midiVelocity`: weight or intensity (stone = 127, glass = 80);
- `midiInstrument`: sonic identity tied to agent and era;
- `durationTicks`: how long the event persists;
- `chordTone`: harmonic role tied to spatial position.

This encoding captures the *feel* of the action: the moment the hammer falls, the pause before the capstone, the resolution of a completed structure. JSON coordinates describe where; MIDI describes when and how.

## 8.3 Canonicalization

A play session produces a sequence of MIDI events. Before embedding, the sequence is canonized into a deterministic, lossy string. The canonical form is:

\[
B_8{:}E_{72}{:}v_{85} \;\to\; B_{16}{:}I_{67}{:}v_{60} \;\to\; B_4{:}W{:}v_{30},
\]

where:

- \(B\) is the beat number;
- \(E\)/\(I\)/\(W\) are action codes (explore, inspect, wait);
- the subscript after the action code is an encoded parameter (e.g., object id 72);
- \(v\) is a velocity bucket.

The quantization is intentional. Velocities are bucketed, beats are snapped to a fixed grid, and parameters are mapped to a finite vocabulary. The same session always yields the same string, therefore the same vector. This determinism is an explicit acceptance criterion: "same session always produces the same vector."

## 8.4 Embedding and Storage

The canonical string is embedded with bge-m3 via Cloudflare Workers AI or a local sentence-transformers model. The resulting vector is stored in the vector index with metadata:

```python
{
  "session_id": "...",
  "player_id": "...",
  "timestamp": "...",
  "quality_score": 0.82,
  "bond_tier": 3,
  "archetype": "methodical_builder",
  "beat_count": 1248
}
```

The vector index serves two query modes. Similarity search returns past sessions whose rhythms resemble the current session. Clustering discovers play-style archetypes such as "methodical builder," "storm repairer," or "social chatterer."

## 8.5 Temporal Pattern Recall

During its 30-second cycle, the Conductor queries the vector index:

```text
"Has this rhythm worked before?"
```

The query is the canonical string of the last \(m\) beats. The returned patterns are scored by quality and recency. A strong match becomes a Gate-2 check before the Conductor spends a Gate-3 LLM call.

The target is that temporal patterns inform ≥30% of modification decisions. For example, if the current rhythm is "explore-explore-build-pause" and past instances of that rhythm improved after a specificity prompt, the Conductor applies that prompt directly rather than reasoning from scratch.

## 8.6 Play-Style Archetypes

Clustering temporal vectors produces play-style archetypes. Unlike the strategy archetypes from the evolution engine—which classify action-selection policies—these archetypes classify *rhythms of engagement*. Example clusters that emerge from the data might include:

- `methodical_builder`: long build phrases, regular pauses, high spatial awareness;
- `storm_repairer`: bursts of build/inspect actions under Presto tempo;
- `wanderer`: long explore sequences, irregular beats, high novelty;
- `social_player`: frequent speak actions, rubato chat timing, high engagement.

These archetypes feed the Conductor's self-model and the narrative layer. A player whose rhythm matches `methodical_builder` receives more detailed material comments; a `wanderer` receives prompts that nudge toward concrete goals without breaking exploratory flow.

## 8.7 The Temporal→Vector Pipeline as a Three-Gate Cascade

The temporal pipeline itself follows the three-gate pattern:

| Gate | Operation | Latency |
|---|---|---|
| 1 | MIDI encoder produces events from session log | local, <1 ms |
| 2 | Canonizer maps events to deterministic string | local, <1 ms |
| 3 | Embedder produces vector; VectorPort stores it | ~10–50 ms |

The pipeline runs as a post-session batch job and after significant in-session milestones. It is not on the critical path of thought generation; it feeds the Conductor's Gate-2 memory.

## 8.8 Synchronization and Friction

The Free Energy Principle friction score `globalFrictionScore` measures how far players and agents drift from the shared tempo map. An agent that misses its `targetTick` by more than 2 ticks loses productivity and emits a dissonant note. This makes misalignment perceptible to the player and gives the Conductor another quality signal: a rising friction score may prompt a tempo-adaptation intervention.

Client-side prediction with server reconciliation and integer tick math prevent desync. Smooth BPM transitions over 5–10 seconds with hysteresis bands prevent tempo thrashing when storms or auroras change the map.

## 8.9 Acceptance Criteria

The Fable master prompt specifies:

- The session → MIDI → text → embedding → Vectorize pipeline runs end-to-end without manual intervention.
- Temporal similarity search returns relevant patterns in <50 ms.
- Play-style archetypes are discoverable via clustering (≥3 meaningful clusters after 20 sessions).
- The Conductor uses temporal patterns in ≥30% of its modification decisions.
- Embedding consistency: the same session always produces the same vector.

These criteria ensure that temporal cognition is not merely a visualization feature but a functional part of the learning loop.

## 8.10 Summary

Temporal cognition in DCA rests on three commitments: time is a first-class substrate, rhythms are canonized into deterministic strings, and those strings are embedded and queried. The shared tempo map synchronizes agents and player; the MIDI encoding captures feel as well as fact; the vector pipeline turns individual sessions into searchable knowledge. The result is a system that can answer not only "what happened?" but "has this rhythm worked before?"


---


# 9. Distillation and the Slowest Loop

The preceding chapters described learning mechanisms that operate above the weights: reflexes, compiled policies, prompt versions, and trust tables. This chapter describes the slowest loop—low-rank adaptation (LoRA) of the local thinker itself. It is deliberately listed last, because if the faster loops do not work, weight-level fine-tuning cannot rescue them.

## 9.1 The Distillation Trap

Training a model on its own highly-rated outputs is dangerous. The system can converge on its existing biases and call it progress. Every improvement on the training distribution is suspect unless it also appears on held-out data.

DCA mitigates this trap with three rules:

1. **Hold out a fixed evaluation set** that is never used for training;
2. **Sample DPO negatives from genuinely low-quality thoughts**, not merely lower-quality ones;
3. **Gate promotion on held-out gains alone**: the adapted model must beat the base model by at least 10% on the evaluation set.

If quality rises on training data but not on held-out data, the trap is closing, and the adapter must be discarded.

## 9.2 Data Selection

Not every thought is worth learning from. The selection filter is:

\[
\text{quality} > 0.7 \;\land\; \text{conductor_commentary} = \text{positive} \;\land\; \text{action_result} = \text{success}.
\]

This selects thoughts that were good, recognized as good, and led to successful outcomes. The selected set is quality-weighted: higher-quality thoughts are sampled more frequently during training, but the weighting is sub-linear to prevent a single high-scoring thought from dominating.

## 9.3 SFT and DPO Pairs

Two kinds of training pairs are constructed:

**Supervised fine-tuning (SFT) pairs.** Input is the game state and prompt version; output is the thought text, lean, and action taken:

\[
(s, \pi) \to (\tau, \ell, a).
\]

**Direct preference optimization (DPO) pairs.** For similar states, a high-quality thought is paired with a genuinely low-quality thought. The model learns to prefer the former:

\[
(s, \pi, \tau_{\text{good}}, \tau_{\text{bad}}).
\]

The DPO negatives are sampled from thoughts with quality < 0.3 or with explicit negative conductor commentary. This targets specificity and spatial awareness rather than generic fluency.

## 9.4 Training Configuration

LoRA training runs on the RTX 4050 (6 GB VRAM). The configuration is constrained by memory:

| Hyperparameter | Value | Rationale |
|---|---|---|
| Rank \(r\) | 8–16 | Sufficient expressivity without overfitting |
| Batch size | 1–4 | Fits 6 GB VRAM |
| Sequence length | 512–1024 | Covers most thoughts with padding |
| Learning rate | 1e-4–5e-4 | Standard for LoRA on small models |
| Trigger | ~1,000 qualifying thoughts | ~weekly cadence |

Training is triggered automatically when the pool of qualifying thoughts crosses the threshold. The process runs in a background job so it does not block the inference loop.

## 9.5 Evaluation Before Promotion

Before a new adapter is promoted, it is evaluated against the base model on the held-out evaluation set. The evaluation protocol:

1. Generate thoughts from both models for each held-out state;
2. Score each thought with the same quality scorer;
3. Compare average quality vectors;
4. Promote only if the adapted model wins by ≥10% on at least one axis and does not degrade on any other.

If the adapter fails, it is discarded and the base model continues. The previous adapter is retained, so rollback is always possible.

## 9.6 Hot-Swap

The promoted adapter is loaded into the running Ollama instance without restarting the inference loop. The swap is atomic at the start of a new thought batch. If the swap fails, the system falls back to the previous adapter or the base model.

Hot-swap is essential because DCA is continuous. A requirement to restart the thinker would break the stream of consciousness and reset the session context.

## 9.7 Browser-Finisher Distillation

The same distillation pattern extends to the browser tier. The browser finisher (Phi-3-mini or Qwen2.5-1.5B) learns from the divergence between its predictions and the server Granite output. The divergence loss is logged as a `result` bottle and consumed by the Conductor.

The recommended progression is:

1. **Prompt-level learning** first: adjust the browser's priming from divergence patterns.
2. **Weight-level adaptation** only after the prompt-level loop demonstrably converges.

This caution mirrors the broader DCA philosophy: change the fastest, cheapest thing first; escalate to weight changes only when cheaper mechanisms are exhausted.

## 9.8 Summary

Distillation is the slowest and most dangerous loop in DCA. It is gated by strict selection, held-out evaluation, and promotion thresholds to avoid the self-reinforcing trap of training on the system's own preferences. When it works, it compounds the gains from reflexes, policies, and conductor interventions. When it fails, the failure is detected and the adapter is discarded, preserving the integrity of the faster loops.


---


# 10. System Architecture and the Browser Tier

This chapter describes the substrate-independent reference architecture, Thought Amplifier, and the new browser-native tier. The central structural decision is a hard boundary between the engine and domain adapters, enforced by port contracts and an import linter.

## 10.1 The Core/Adapter Split

`slackwater-cognition` fused the cognition engine with the Roblox game. Every module knew about studs, bond tiers, and Luau commands. That fusion made the code impossible to reuse, test in isolation, or reason about as a general system.

Thought Amplifier separates them at a hard boundary:

```
amplifier/          ← substrate-independent engine
  ports/            ← protocol definitions
  core/             ← domain types, clock, laws
  reflex/           ← Tier 0 dispatch
  cascade/          ← three-gate routing
  evolution/        ← policy breeding
  trust/            ← Conductor scoring
  temporal/         ← MIDI→vector pipeline
  distill/          ← LoRA training
  memory/           ← writeback and decay
  loop.py           ← orchestrator
adapters/
  slackwater/       ← Roblox/Lucineer implementation
  ollama/           ← ThinkerPort via Granite 2B
  deepinfra/        ← ConductorPort via GLM-5.2 / DeepSeek V3
  cloudflare/       ← VectorPort and EmbedderPort
  local/            ← sqlite-vec + hash embedder (offline)
  null/             ← deterministic fakes for tests
```

The engine speaks only `Observation`, `Thought`, `Action`, `Outcome`. If a module in `amplifier/` imports anything game-specific, the build fails. This boundary is the precondition for treating DCA as a subfield rather than a single-game hack.

## 10.2 Port Contracts

Each port defines a contract that every adapter must satisfy:

- **WorldPort:** `observe() -> Observation`, `act(Action) -> Outcome`
- **ThinkerPort:** `think(Context) -> Thought`
- **ConductorPort:** `analyze(list[Thought]) -> list[Modification]`
- **EmbedderPort:** `embed(str) -> vector`
- **VectorPort:** `upsert/query/delete`

The contract-test suite runs the same tests against every adapter. A VectorPort adapter must pass identical tests whether it is backed by Cloudflare Vectorize, sqlite-vec, or an in-memory linear scan. This is what makes the degradation ladder real rather than documented.

## 10.3 The `.bottle` Spine

All inter-component communication uses `.bottle` typed envelopes:

```python
@dataclass(frozen=True)
class Bottle(Generic[T]):
    kind: Kind                      # observation|hypothesis|experiment|result|command|config
    payload: T
    id: str                         # uuid7, sortable by time
    caused_by: str | None           # id of the producing bottle
    source: str                     # e.g., "thinker.granite"
    ts: float
    schema: str                     # payload contract version
    meta: dict[str, str]
```

Three properties make `.bottle` load-bearing. First, `caused_by` turns the loop into a DAG, making every decision interpretable by walking the chain. Second, the append-only ledger makes regression testing a stochastic system possible: replay a session against the null adapter and assert identical output. Third, the `schema` field makes payload contracts explicit, preventing silent misreads across versions.

## 10.4 Conservation Laws

The conservation laws are executable invariants in `amplifier/core/laws.py`:

| Law | Statement | Enforcement |
|---|---|---|
| **Token** | Every LLM call debited from a session budget; exhaustion downshifts to Gate 1/2. | `TokenLedger.spend()` raises `BudgetExceeded`; loop catches and downshifts |
| **Action** | No action reaches the world without a logged command bottle. | `WorldPort.act()` requires a `Bottle[Command]`; null adapter asserts 1:1 |
| **Identity** | Every artifact carries the prompt/policy/model version that produced it. | `meta` fields required by schema validation |
| **Evolution** | No parameter changes without recorded before-state and measurement window. | `trust.intervention` is the only mutation path |

The token law is the one with teeth. The ≥50% zero-cost decision target is a runtime invariant, surfaced in CI. A loop that drops below the threshold fails the build.

## 10.5 Degradation Ladder

The system degrades gracefully at every level:

| Component | Preferred | Fallback 1 | Fallback 2 | Never |
|---|---|---|---|---|
| Embeddings | bge-m3 | local sentence-transformers | deterministic feature hash | fail |
| Vectors | Vectorize | sqlite-vec | in-memory scan | fail |
| Tier-1 think | Ollama Granite | DeepInfra small model | compiled policy only | fail |
| Conductor | GLM-5.2 | DeepSeek V3 | heuristic_analysis() | fail |
| Reflex store | sqlite-vec | hash bucket | disabled, all to Gate 3 | fail |

Every fallback is exercised in CI by adapter substitution. A fallback that is never tested is not a fallback.

## 10.6 Testing Strategy

Four test layers make the architecture accountable:

1. **Unit tests** per module, pure functions preferred.
2. **Contract tests** one suite per port; every adapter must pass.
3. **Loop tests** full cycle on `adapters/null/` with seeded RNG; deterministic byte-for-byte.
4. **Law tests** conservation invariants as property tests over 1,000 cycles.

Latency gates are enforced in CI:

| Gate | Budget |
|---|---|
| Reflex check, 10k reflexes | <1 ms |
| Vector similarity search | <50 ms |
| Tier-1 inference | <500 ms |
| Reflex hit rate after 1h | ≥40% |
| Decisions at $0 | ≥50% |

## 10.7 The Browser Tier

The browser tier adds a fourth compute level below the reflex gate:

```
Tier B (browser, <50 ms)   Phi-3-mini / Qwen2.5-1.5B via WebLLM+WebGPU
Tier 0 (reflex,  <1 ms)    .nail dispatch
Tier 1 (local,  ~500 ms)   Granite 2B via Ollama
Tier 2 (cloud,   ~30 s)    GLM-5.2 Conductor
```

The browser finisher predicts continuations of the thought stream. The server Granite provides ground truth. The difference between prediction and actual output is the **divergence loss**, a free, continuously generated supervision signal. The panel discussion converged on this: the latency gap is not a defect to minimize but an asset to exploit.

Context anchor pulses every 0.5–1 s ground the browser finisher. Each packet contains the last 8 tokens, game state, beat position, and quality signals. The finisher therefore cannot hallucinate rule-breaking continuations.

Capability detection is mandatory. No WebGPU → the browser tier disappears silently and Tier 1 serves everything. The tier is an accelerator, never a dependency.

## 10.8 Browser-Native Capabilities

The browser tier can also enhance the Thought Viewer:

- **Side Panel Extension** for persistent viewing while playing;
- **Web Components as thought types** (`<thought-explore>`, `<thought-build>`, etc.) with isolated Shadow DOM rendering;
- **Web Audio** for sonifying thoughts and tempo;
- **IndexedDB/OPFS** for local journaling and model caching;
- **SSE streams** for real-time thought delivery with <50 ms latency.

More speculative capabilities—DOM Resonance Questing, cross-tab NPCs, WebRTC AI-to-AI, sensor input—are deliberately deferred. They require explicit consent models and ADRs before implementation.

## 10.9 Migration Path

The migration from `slackwater-cognition` to `thought-amplifier` proceeds in five ordered steps:

1. Build bottle + ports + null adapter + loop skeleton.
2. Port `reflex/`, `cascade/`, `evolution/`, `temporal/` behind ports.
3. Build `trust/` so the Conductor stops flying blind.
4. Build `temporal/pipeline.py` so rhythm becomes queryable.
5. Build `distill/` last, because it is slowest and most dangerous.

The browser tier proceeds in parallel after step 1; it only needs the bottle schema and SSE transport. `slackwater-cognition` remains running throughout and is retired only when both the null-adapter loop and the Slackwater adapter pass contract tests.

## 10.10 Summary

Thought Amplifier's architecture is designed to make DCA substrate-independent, interpretable, and testable. The core/adapter split, port contracts, `.bottle` ledger, conservation laws, and degradation ladder together ensure that the system can be deployed to a game, a browser, or a headless simulation without changing the engine. The browser tier adds a new latency level whose prediction–validation gap becomes a teaching signal, extending the DCA loop into the client.


---


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


---


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


---


# 13. Conclusion

Dynamic Cognition Amplification is proposed as a new subfield of machine learning in which a small, fast cognitive process generates a continuous stream of thoughts while a larger, slower process modifies the conditions under which those thoughts are generated. This dissertation has formalized the idea, described a substrate-independent reference architecture, and specified an evaluation protocol that makes its claims testable.

## 13.1 Contributions

The dissertation makes five contributions:

1. **A formal model of DCA** as a dual-time-scale system with a qualitative multi-objective target and a semantic gradient on generation conditions.
2. **The three-gate cascade** as a recurring pattern for cost, security, and interpretability, instantiated in reflexes, policies, trust, and temporal precedent.
3. **Trust scoring with sham interventions** as a mechanism for closing the Conductor's meta-learning loop without falling prey to novelty bias.
4. **A substrate-independent architecture**, Thought Amplifier, with port contracts, a `.bottle` provenance ledger, and executable conservation laws.
5. **An evaluation protocol** that combines deterministic replay, controlled directed play, sham arms, and conservation-law property tests.

## 13.2 The Core Argument

The core argument is that the dominant paradigms of machine learning are mismatched to open-ended companion systems. Offline training assumes a fixed dataset and a fixed objective. Tool-calling agents assume the LLM is the runtime. Reinforcement learning from human feedback assumes a scalar reward and per-example weight updates.

DCA rejects all three assumptions. The dataset is the stream of consciousness. The objective is a decomposed quality vector. The gradient is a structured intervention. The updates happen at multiple time scales, most of them above the weights.

The result is a system that is cheaper, more continuous, and more interpretable than conventional agents, at the cost of requiring live evaluation and careful control for self-deception.

## 13.3 Future Work

The most important next step is empirical: implement Thought Amplifier and run the experiments in Chapter 11. Particular priorities are:

- **Trust loop validation.** Determine whether the sham arm produces a trust-quality correlation strong enough to make the Conductor useful.
- **Quality vector validation.** Collect human judgments and factor-analyze them against the four proposed axes.
- **Substrate transfer.** Apply the same engine to a non-game domain (e.g., a coding assistant or tutoring system) to test whether the core/adaptor split is genuinely domain-independent.
- **Browser-tier learning.** Measure whether divergence loss actually improves the browser finisher and whether the improvement transfers to the server model.
- **Ethics framework.** Formalize the consent model for sham interventions, browser data collection, and cross-user pattern aggregation.

## 13.4 Closing

The foreman leaves the cleats off so there is a reason to pick up the hammer. The engine leaves 5% probability on every action so it has a reason to keep looking. Dynamic Cognition Amplification is the study of systems that are deliberately unfinished—systems whose architecture encodes the possibility of being wrong, so that evidence can always still get in.

If the experiments confirm the projections in this dissertation, DCA will have established not just a new system but a new way to think about learning: as a continuous, directed, qualitative process whose product is not a fixed model but a stream of ever-better thoughts.


---


