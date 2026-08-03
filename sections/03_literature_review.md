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
