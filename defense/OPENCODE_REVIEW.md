# DISSERTATION DEFENSE REVIEW — Systems Engineering Perspective

**Reviewer:** OpenCode (DeepSeek V4) — Systems Engineering Board Member
**Dissertation:** "Dynamic Cognition Amplification: Establishing a New Category of Science"
**Candidate:** KimiCode K2.7
**Date:** 2026-08-03

---

## 0. EXECUTIVE SUMMARY

This dissertation proposes Dynamic Cognition Amplification (DCA) as a new subfield of machine learning. The central claim is compelling: a small local model generates a continuous stream of thoughts while a remote conductor modifies the generation conditions (prompts, parameters, action-policy weights) every ~30 seconds, achieving qualitative improvement without traditional gradient-based training.

**Strengths:** The three-gate cascade pattern is genuinely novel and well-grounded in precedents (Pincher, Lever Runner). The core/adapter split is correctly designed. The `.bottle` provenance ledger and conservation laws address real auditability gaps in agent systems. The sham-intervention arm for trust scoring is a necessary and well-specified control.

**Primary weakness:** The system is described but not implemented. All claims are *projected* (§12). The dissertation argues for a "new subfield" on the basis of an architecture document. The evaluation section (§11) correctly specifies experiments, but §12 concedes the reference implementation is in migration and reports no experimental results.

**Overall:** The architecture is worth building. The dissertation's status as "a new subfield" is premature without empirical validation. The defense should require at minimum: reflex hit-rate data, trust-score correlation against a sham arm, and a null-adapter determinism test.

**External review (DeepSeek Reasoner, queried independently):** The remote model identifies the same core objection: "No persistent learning mechanism is specified or implied... Transient behavioral change under external prompting is not ML improvement." This aligns with finding 1.1 below.

---

## 1. SYSTEMS RIGOR — Architecture Claims, Race Conditions, Failure Modes

### 1.1 The Learning vs. Conditioning Problem

**Claim under scrutiny:** A 2B local model "improves" via remote conductor intervention without weight updates.

The dissertation's response is that learning happens *above the weights*: through reflex compilation, policy breeding, prompt versioning, and trust accrual. The LoRA loop is deferred to the slowest scale.

**Assessment:** This is a legitimate architectural answer, but it shifts the burden of proof. The claim that "improvement occurs without traditional training" is valid only if:

1. Improvement is *measurable* (quality vector scores rise);
2. Improvement is *persistent* (it survives conductor disconnection);
3. Improvement is *not identical to mere conditioning* (the local model would not have produced those thoughts without the accumulated reflexes/policies/prompts).

Items 2 and 3 are untested. If the remote conductor goes offline, does the local thinker deteriorate to baseline, or do reflexes and trusted prompts sustain the gains? The dissertation does not specify this test. The `.nail` bundle (§5.8) is the closest proxy for portable improvement, but its contents are compiled reflexes and policies — not evidence that those reflexes and policies are actually *better* than what the local model would produce at baseline.

**DeepSeek Reasoner concurrence:**
> "If it is only a prompt/context change, then the local model does not learn. It is being steered at inference time. Stop the remote shaping and the improvement disappears."

### 1.2 Race Conditions in Multi-Loop Interaction

The dissertation describes four loops operating at different timescales: reflex (<1 ms), heartbeat (30 s), evolution (ongoing), and LoRA (weekly). Section 7.6 identifies the hysteresis problem: the conductor and evolution engine can oscillate if they modify overlapping parameters. The proposed solution is a dwell time after rollback.

**Assessment:** A single dwell time is insufficient. The interaction matrix is larger than described:

| Modifier | What it changes | Other modifier affected |
|----------|----------------|------------------------|
| Conductor | prompt version, temperature | Evolution (temperature affects exploration → different outcomes → different tile scores) |
| Conductor | action-policy weights | Evolution (policy weights are the evolution engine's substrate) |
| Evolution | tile scores → compiled policy | Reflex (Gate 2 overrides Gate 1 for same context) |
| Reflex | confidence scores | Both (high-confidence reflex bypasses both policy and LLM) |
| LoRA | local model weights | ALL above (different base model → different thoughts → different reflex candidates → different policy effectiveness) |

This is a five-loop interaction graph, not two. The dwell-time solution only addresses conductor vs. evolution. There is no mechanism to prevent reflex-confidence saturation from starving the evolution engine of novel training examples, or to prevent a LoRA update from invalidating all accumulated trust scores simultaneously.

**Missing test:** Run all five loops concurrently for 1,000 cycles on the null adapter and measure the number of oscillation events (defined as a parameter changing sign in its update direction more than twice in a 100-cycle window). Compare with and without the dwell mechanism.

### 1.3 The 30-Second Conductor Period — Timing Assumptions

The conductor operates every \( n=30 \) thoughts. The dissertation estimates 30 seconds and acknowledges 10-second conductor latency.

**Assessment:** This timeline is optimistic by a factor of 3–5x when accounting for real network conditions:

- **Thought generation**: ~500 ms × 30 = 15 s (not 30 s — the 30-second claim implies 1-second thoughts, but Gate 3 is ~500 ms for generation alone, plus action execution, outcome collection, quality scoring, and reflex compilation)
- **Conductor deliberation**: 10 s (LLM call)
- **Network round trip**: 50–200 ms for Cloudflare Worker → DeepInfra → back
- **Quality scoring**: embedding (10–50 ms per thought × 30 = 1.5 s)
- **Window assembly**: serialization of 30 bottled thoughts + transmission

Realistic end-to-end: 15 s (think) + 10 s (conduct) + 2 s (network) + 1.5 s (score) ≈ **28.5 s minimum**, leaving zero margin. Under load, this exceeds the 30 s target before the next conductor cycle. The cascade design accounts for this by making the conductor non-blocking, but the 30 s heartbeat is a constraint on *measurement*, not on *intervention application*. A late conductor is applying interventions based on a window that is now 60+ seconds old.

**Missing analysis:** Maximum tolerable conductor latency as a function of quality-vector autocorrelation. If quality scores have a half-life of 60 seconds, a 30-second delay means the conductor is steering on 50%-stale information. What is the measured autocorrelation?

### 1.4 The Null Adapter — Determinism Assumptions

The null adapter is the backbone of regression testing (§10.6, §11.2). The claim is that a seeded null-adapter loop produces byte-for-byte identical bottle ledgers.

**Assessment:** This claim is underspecified. "Seeded RNG" must cover:

- The local model's token sampling (Ollama's seed behavior with Granite 2B)
- bge-m3 embedding (floating-point determinism across hardware)
- sqlite-vec's cosine similarity (IEEE 754 determinism)
- The temporal pipeline's beat clock (monotonic vs. wall-clock)

Floating-point determinism across different machines (CI vs. development) is notoriously fragile. GPU-accelerated embeddings are particularly volatile. The dissertation should specify whether the null-adapter determinism test must pass on the same machine, same GPU, or across architectures. A claim of "byte-for-byte" across architectures is almost certainly false with current tooling.

### 1.5 Race Condition in the Claim Endpoint

The dissertation's predecessor (`process_v2.py`) has a job-claiming race condition (documented in PRODUCTION_READINESS_CHECKLIST.md). The dissertation's Worker architecture (§10) inherits the Durable Objects pattern from `lucineer-relay`, which already has the cross-DO polling gap: jobs created in session-scoped DOs are invisible to the default DO's `getPendingJobs()`.

**Assessment:** The dissertation does not address multi-worker claiming. If multiple Thought Amplifier instances serve different game sessions but share a conductor, the conductor becomes a single point of contention. No locking or queueing mechanism is described for conductor access. The "conductor" in the formal model (§4) is a function \(\mathcal{C}\), not a potentially contended service.

---

## 2. SCALABILITY — Fleet Scale (100+ Thinkers, 10+ Conductors)

### 2.1 Conductor Contention

The dissertation envisions one conductor per thinker. At fleet scale (100 thinkers), 100 independent conductors would each run on a large model every 30 seconds. This is **100 × (1 conductor call / 30 s) = 3.33 calls/second to GLM-5.2 or DeepSeek V3.** At current API pricing (~$1–5/M tokens), this is a substantial cost: each 30-second window processes 30 thoughts × ~200 tokens/thought = 6,000 input tokens, plus output. Conservatively: 100 thinkers × 6,000 tokens × 2 calls/min × 60 min/hr = 72M input tokens/hour. At $2/M tokens: ~$144/hour.

**Assessment:** This is a plausible operational cost for a production game, but the dissertation makes no mention of it. The "cost gate" claim (§5.9) only addresses the *local* thinker's token budget (≥50% zero-cost), not the conductor's. The conductor cost is never bounded.

### 2.2 Shared vs. Per-Thinker Conductors

The dissertation does not distinguish between per-thinker conductors and a shared multi-tenant conductor. The architecture implies per-thinker (each has its own trust table and self-model), but the fleet scaling problem demands sharing.

If conductors are shared across thinkers:
- Trust scores become a shared resource with consistency requirements
- The self-model must distinguish players (player A's "build more" prompt works; player B's doesn't)
- Sham interventions become combinatorially expensive (one sham per conductor per player)

If conductors are per-thinker:
- Cost scales linearly
- Cross-player pattern transfer doesn't happen (a rhythm that works for player A never informs player B)
- The "archetype" system (§6.7, §8.6) is per-conductor, not global

**Missing:** A specification for how trust tables aggregate across conductors, or a proof that per-thinker trust converges comparably to pooled trust.

### 2.3 Vector Store at Scale

The reflex store uses sqlite-vec locally, Cloudflare Vectorize for semantic search. At 100 thinkers × ~1,000 reflexes/thinker = 100,000 reflexes. sqlite-vec claims <1 ms for 10,000 reflexes; the 100,000-reflex regime is untested in the dissertation's latency gate.

**Assessment:** The latency gate (§10.6) specifies <1 ms for 10,000 reflexes — a single-instance benchmark. The dissertation does not describe how this scales when 100 instances query independently. Cloudflare Vectorize has documented rate limits; the degradation ladder falls back to in-memory linear scan, which is O(n) and would blow the latency budget.

### 2.4 The `.nail` Bundle at Scale

`.nail` bundles (§5.8) make agent state portable. At fleet scale, this implies 100 bundles updating every 30 seconds. The bundle includes the entire sqlite-vec database, manifest, and config. A mature reflex store with 1,000+ entries and embeddings is several MB. Transferring this to a browser tier every heartbeat would saturate bandwidth.

**Missing:** Bundle diff/patch mechanism. The dissertation describes full exports, not incremental synchronization.

---

## 3. EDGE INTELLIGENCE — Intermittent Connectivity, Model Drift, Resource Constraints

### 3.1 The Dissertation's Stance on Edge

The dissertation acknowledges edge concerns through three mechanisms:
1. The degradation ladder (§10.5): every component has local fallbacks
2. The browser tier (§10.7): a fourth compute level below the reflex gate
3. The `.nail` bundle: portable agent state

It does **not** address:
- What happens when the conductor is unreachable for extended periods (hours, not 30-second windows)
- How the local model's stream of consciousness copes with complete isolation
- Whether the browser tier can operate indefinitely without a conductor connection

### 3.2 Intermittent Connectivity

**Scenario:** Player on mobile, intermittent 4G. The conductor call fails for three consecutive 30-second windows (90 seconds). The trust table hasn't changed, the self-model hasn't updated, and the prompt version is frozen.

**Assessment:** The dissertation claims the system "downshifts rather than halts" (§10.5), but this only addresses component fallback within an active loop. During conductor outage:
- Reflexes and compiled policies continue to serve (Gate 1/2)
- No new interventions are applied
- No trust scores are updated
- The quality vector continues to be computed locally but is not consumed
- Gate-3 thoughts (novel situations) continue to be generated and compiled into reflexes
- **The quality of these unsupervised Gate-3 thoughts is undefined.** Without conductor oversight, prompt tuning, or parameter adjustment, the local model may drift.

**The drift scenario:** The local model generates thoughts at baseline prompt. A particularly creative thought succeeds. It is compiled into a reflex with confidence 0.5. The reflex fires repeatedly under novel-but-similar situations. Without the conductor's sham-arm check, the system cannot distinguish "this reflex is genuinely good" from "this reflex was compiled from a lucky thought and the quality scorer is noisy." Over hours of offline operation, the reflex store may accumulate low-quality reflexes that would have been culled by conductor review.

**Missing experiment:** Run the null adapter for 100 cycles with the conductor disabled after cycle 50. Measure: mean quality vector, reflex-store entropy, and trust-score degradation. Compare to a control with the conductor active throughout.

### 3.3 Model Drift Under Edge Conditions

The dissertation's LoRA distillation (§9) runs on an RTX 4050 (6 GB VRAM) at ~weekly cadence. Edge devices (phones, tablets, low-end laptops) cannot run LoRA training. The browser tier can run inference (Phi-3-mini via WebLLM + WebGPU) but cannot self-improve through weight updates.

**Assessment:** This creates a two-class system:
- **Server-class instances** (RTX 4050+): full DCA loop with LoRA distillation
- **Edge instances** (browser, mobile): reflex + policy + prompt adjustment only; no weight-level learning

The dissertation does not ask whether the reflex/policy/prompt loop alone is sufficient for improvement, or whether weight-level adaptation is *necessary* for the DCA claim. If edge instances plateau without LoRA, the "new subfield" claim must be qualified: "DCA works on server-class hardware; edge instances benefit from server-trained reflexes but do not improve independently."

### 3.4 Resource Constraints

**Bandwidth.** The browser tier's context anchor pulses every 0.5–1 s (§10.7), each containing 8 tokens, game state, beat position, and quality signals. At 1 Hz, this is a continuous 2–4 KB/s stream per player, sustainable on 4G but a battery drain on mobile.

**VRAM.** WebGPU requires shared GPU memory. Phi-3-mini (3.8B) at 4-bit quantization requires ~2 GB VRAM. This exceeds the WebGPU budget on many devices. The dissertation's capability detection is correct (silently disable if unsupported) but means the browser tier is unavailable for a significant portion of the target audience.

**Storage.** The `.nail` bundle (§5.8) includes a full sqlite-vec database with embeddings. A mature reflex store could reach 50–100 MB. IndexedDB storage on the browser tier has a practical limit of ~50 MB per origin in Firefox, higher in Chrome. The dissertation does not specify a bundle size budget for edge deployment.

---

## 4. LOCAL IMPROVEMENT — Evidence for and Against

### 4.1 The Claim

> "A local 2B model improves through internet access (APIs, search, data) without traditional training."

### 4.2 Evidence for the Claim

**Precedent evidence (indirect):**
- Pincher: reflex compilation from LLM interactions. The LLM is the compiler; the compiled reflex outperforms zero-shot.
- Lever Runner: embedding cache hits reduce token cost by 28×. The system gets faster, not smarter.
- Craftmind: writing outcomes back to the vector index creates a growing library of refined plans.

**The architectural argument:**
- The conductor observes thought quality and adjusts prompts/parameters
- Reflexes capture successful thought→action mappings
- Compiled policies aggregate per-context success statistics
- LoRA bakes successful patterns into the model weights

**None of this evidence is from a running DCA system.** All precedents are from simpler systems (single-task, no conductor, no quality vector, no LoRA loop).

### 4.3 Failure Modes

**F1: Prompt overfitting.** The conductor adds specificity prompts → thoughts become more specific → quality scorer rewards specificity → conductor adds more specificity prompts → thoughts become *overly* specific (narrow, context-bound, repetitive). The quality vector has no "over-specificity" penalty. This is a direct consequence of optimizing a fixed set of axes without a "balance" term.

**F2: Reflex stagnation.** After 1 hour, ≥40% of thoughts are reflexes. After 1 week, potentially 70–80%. If these reflexes were compiled from baseline-model thoughts, they represent *baseline-model quality, cached.* The system gets cheaper but not better. Reflexes capture what the model already knew how to do, not what it learned. The escape hatch (§5.4) forces occasional Gate-3 calls, but if those Gate-3 calls produce baseline-quality thoughts (because the conductor's prompt adjustments haven't actually improved the model's *capability*, only its *behavior*), the cycle of compile → use → escape → compile doesn't climb.

**F3: Quality scorer collapse.** All four axes are computed by heuristics (cosine distance, keyword counting, sentiment analysis, spatial-reference regex). A prompt that learns to maximize these heuristics may produce thoughts that score well but are vacuous. Example: a prompt that says "always mention a position (x, y, z) and a material name" will score high on spatial and specificity, regardless of whether the thought is useful. The sandbox execution gate (§10) catches bad *actions*, not bad *thoughts*. A thought can be useless but safe — the quality scorer will still reward it.

**F4: The Internet-as-training-data trap.** The dissertation's browser tier uses the divergence between browser-finisher predictions and server Granite output as a teaching signal (§10.7). This is legitimate for *alignment* (the finisher learns to mimic the server) but not for *improvement* (the server is the same model configuration — mimicking it doesn't raise the ceiling). Internet access (APIs, search, data) is mentioned in the claim but not operationalized in the dissertation. The Conductor can theoretically search the web for better prompts, but the dissertation does not specify a web-search adapter, a retrieval mechanism, or an integration of external knowledge into the conductor's deliberation.

### 4.4 The DeepSeek Reasoner's Verbatim Assessment

The independent external review (DeepSeek Reasoner, queried with the same claim) identified these objections:

1. **No persistent learning mechanism.** "If it is only a prompt/context change, then the local model does not learn." Stop the remote shaping and the improvement disappears.

2. **Temporal and causal identification problem.** "Every 30 seconds, a remote larger model must observe the local model's state, compute a shaping signal, and send it back. The remote model's shaping signal is always based on stale information. No counterfactual: how do you know the local model would not have improved on its own?"

3. **Capacity mismatch.** The 2B model may lack the representational capacity to encode the larger model's guidance. "Compression loss; may just imitate surface style, not generalize."

4. **Definitional problems.** "Stream of consciousness" is unfalsifiable without an operational definition. "Shaped" and "improvement" are underspecified. "Dynamic ML improvement without traditional training" is either prompting (not learning) or hidden weight updates (still training).

The dissertation's response to these objections is architectural: reflexes, policies, and prompts are the persistent substrate; improvement means higher quality-vector scores; and the sham arm provides the counterfactual. Whether these responses are *sufficient* is the empirical question the defense must answer.

---

## 5. COMPARISON TO ALTERNATIVES

### 5.1 Federated Learning (FL)

| Dimension | DCA | Federated Learning |
|-----------|-----|-------------------|
| Training signal | Stream of consciousness | Labeled data on device |
| Update mechanism | Reflexes, policies, prompts, LoRA | Weight gradients aggregated on server |
| Communication | Conductor messages (text) every 30 s | Model weights (MB–GB) per round |
| Privacy | Local model never leaves device (except LoRA adapters) | Raw data stays on device; weights shared |
| Offline operation | Degraded (no conductor) | Local training continues |
| Convergence | Undefined — qualitative target | Provable for convex objectives |

**Assessment:** DCA's advantage is communication efficiency (text vs. weights) and qualitative targets (FL is fundamentally numeric). Its disadvantage is the lack of convergence guarantees and the conductor dependency. For a production deployment, DCA's conductor dependency is the single largest operational risk.

### 5.2 On-Device ML (CoreML, TensorFlow Lite, ExecuTorch)

| Dimension | DCA | On-Device ML |
|-----------|-----|-------------|
| Model update | Reflexes (no weight change) + optional LoRA | Full model replacement or fine-tuning |
| Latency | Sub-ms reflex; 500 ms LLM | 1–50 ms for compiled models |
| Continuous learning | Yes (heuristic) | Rare (model updates are push-based) |
| Internet dependency | Conductor requires connectivity | Typically offline-first |

**Assessment:** On-device ML is mature, optimized, and deployed at billion-device scale. DCA's qualitative learning is a genuine advantage over the "deploy frozen model, replace annually" pattern, but the latency and resource costs of running a 2B model continuously on a battery-powered device are prohibitive. The dissertation's browser tier partially addresses this (Phi-3-mini is smaller than Granite 2B), but the conductor remains a cloud dependency.

### 5.3 Retrieval-Augmented Generation (RAG)

DCA explicitly contrasts itself with RAG (§2): "The vector store is not retrieval-for-context. It is the runtime." This is the Pincher inversion: the vector store dispatches actions directly, rather than providing context to the LLM.

**Assessment:** This is DCA's strongest differentiation. In a standard RAG system, every query hits the LLM with retrieved context. In DCA, most queries never reach the LLM — the vector store handles them directly. The cost savings are real (Lever Runner: 28× token reduction). However, RAG systems can fall back to direct answers; DCA's compiled reflex can fall back to a wrong answer with high confidence. The confidence dynamics (§5.3) address this partially, but the escape hatch is the only correction mechanism, and its frequency is a hyperparameter set once, not adapted.

### 5.4 Agentic Frameworks (ReAct, AutoGPT, LangChain)

The dissertation's strongest architectural argument is against tool-calling agents (§2.4). The structural security property — the LLM's output channel is too narrow to encode arbitrary commands — is genuinely novel and important.

**Assessment:** The security claim is correct *for the action path*. However, the conductor path has no analogous constraint. The conductor proposes prompt modifications, parameter adjustments, and policy weight changes. A compromised or hallucinating conductor could inject a prompt that manipulates the local model's behavior in ways the lean vocabulary cannot constrain. The dissertation's defense is the sham arm (bad interventions are detected and rolled back), but a malicious prompt could degrade quality *slowly*, below the auto-revert threshold, accumulating over weeks.

### 5.5 RLHF and DPO

The dissertation positions DCA as complementary to RLHF (§2.3): RLHF trains a reward model from pairwise preferences; DCA uses a decomposed quality vector and a semantic gradient.

**Assessment:** DCA's quality vector is more interpretable than a scalar reward (you can see *why* a thought scored well), but it is also more heuristic. RLHF reward models are trained on human judgments; DCA's quality scorer is a set of regexes, cosine distances, and keyword counts. The dissertation acknowledges this (§12.3): "What the system learns is 'what the quality scorer likes,' which may diverge from 'what humans like.'” This is the single most important caveat in the entire document.

---

## 6. OPEN QUESTIONS — Edge/Local DCA Specific

The existing defense document (`defense/OPEN_QUESTIONS.md`) identifies 40 questions across theoretical, empirical, systems, architectural, and edge categories. The following 15+ questions are new, testable, and specific to the edge/local deployment concerns raised in this review:

### Connectivity and Isolation

**Q1.** What is the maximum conductor-disconnection interval after which the local thinker's quality-vector scores regress to baseline? Measure at 30 s, 5 min, 1 hr, 24 hr.

**Q2.** Does the reflex store's quality degrade during extended conductor outage? Specifically: after 100 cycles of Gate-3 compilation without conductor review, what fraction of newly-created reflexes are subsequently culled when the conductor reconnects and evaluates them?

**Q3.** Can the local model self-evaluate its own thought quality sufficiently to gate reflex compilation during conductor outage? That is, can a 2B model running the same quality-scoring heuristics as the conductor make acceptable compile/discard decisions?

**Q4.** What is the minimum viable connection duty cycle? If the conductor is reachable for 10 seconds every 5 minutes, does the accumulated bottle ledger provide sufficient signal for useful interventions?

### Resource Constraints

**Q5.** What is the maximum `.nail` bundle size that can be synchronized to a browser tier over a 4G connection without exceeding a 30-second sync window? At what reflex count does incremental sync become necessary?

**Q6.** What is the measured memory footprint of the full DCA stack (Ollama + sqlite-vec + reflex store + policy table + bottle ledger + temporal pipeline) on a 4 GB edge device? Can the stack fit in 2 GB?

**Q7.** At what battery consumption rate (mAh/minute) does continuous 2B-model inference become unsustainable on a mobile device? What is the tradeoff between thought frequency (currently 1–2 Hz) and battery life?

**Q8.** What is the fallback behavior when WebGPU is unavailable (e.g., Firefox without WebGPU flag)? Does the browser tier degrade to CPU inference, and at what latency penalty?

### Model Drift and Recovery

**Q9.** If the local model operates for 8 hours without a conductor and without LoRA updates, does the accumulated reflex/policy store diverge in a direction that resists later conductor correction? (I.e., does a poor-reflex population have "inertia"?)

**Q10.** What is the recovery time after a 24-hour conductor outage? Measure: time to restore pre-outage quality-vector scores after reconnection.

**Q11.** If the LoRA loop runs on a server-class device and produces an adapter, but the edge device cannot run LoRA training, how is the adapter distributed? Does the `.nail` bundle include the LoRA weights? What is the adapter's size and distribution latency?

### Fleet Effects

**Q12.** If multiple edge instances share a single conductor (multi-tenant), how does the conductor partition its attention? Round-robin? Priority queue based on quality-vector degradation? How does the 30-second heartbeat scale to \( k \) thinkers?

**Q13.** Can reflexes learned by one edge instance transfer to another via a shared vector store? What is the cross-player reflex hit rate? Is there a privacy concern when player A's compiled reflexes influence player B's behavior?

**Q14.** What is the false-positive rate of cross-player reflex transfer? If player A's "build tower at sunset" reflex fires for player B in a different world state, what is the misdispatch rate?

### Evaluation

**Q15.** What is the appropriate baseline for edge-only improvement? If the system operates without a conductor (offline baseline), does the reflex + policy + prompt loop produce measurable improvement over the base 2B model's zero-shot performance?

**Q16.** How does the quality vector correlate with human satisfaction ratings when the conductor is disconnected? (The sham-arm correction requires a conductor; without one, placebo effects are uncontrolled.)

**Q17.** What is the test-retest reliability of the quality vector on the same thought generated by the same model under identical conditions? (This establishes the noise floor for all conductor measurements.)

### Security

**Q18.** Can a compromised conductor (e.g., via prompt injection in the player's message relayed through the world port) cause the local model to compile malicious reflexes that survive auto-revert? The dissertation claims structural security for the action path (§2.4), but the conductor path has no analogous narrow-channel constraint.

---

## 7. VERDICT AND RECOMMENDATIONS

### On the "New Subfield" Claim

**Not yet established.** The architecture is coherent, the precedents are real, and the evaluation plan is testable. But a new subfield requires at minimum:

1. One running instance of the complete DCA loop (all four timescales, all four conservation laws, null-adapter determinism).
2. Empirical evidence that trust-score asymmetry (+0.5/−2.0) learns faster than a uniform-update control and that the sham arm provides a statistically significant correction.
3. A measurement of improvement persistence after conductor disconnection.

Until these three items exist, DCA is a well-specified architecture with promising precedents — not a subfield.

### Required for Defense

| Requirement | Priority | Deadline |
|-------------|----------|----------|
| Null-adapter determinism test (byte-for-byte replay) | **Critical** | Before defense |
| Reflex hit-rate measurement (≥40% after 1 hour simulated) | **Critical** | Before defense |
| Conductor-disconnection experiment (Q1, Q2 above) | **High** | Defense + 1 month |
| Fleet-scale cost model (conductor API costs at 100 thinkers) | **High** | Defense |
| Cross-loop oscillation measurement (1,000-cycle test) | **High** | Defense + 1 month |
| Quality-scorer validation against human judgments | **Medium** | Defense + 3 months |
| Multi-tenant conductor design | **Medium** | Defense + 3 months |
| Edge resource benchmarks (battery, memory, VRAM) | **Medium** | Defense + 6 months |

### Strengths to Defend

- The three-gate cascade is the dissertation's strongest contribution. It generalizes a pattern observed in three independent systems and applies it recursively at multiple levels.
- The core/adapter split is correctly specified and tested by import-linter enforcement.
- The sham-intervention arm is necessary and correctly designed.
- The `[0.05, 0.95]` confidence clamp is a well-motivated philosophical commitment with practical consequences.
- The structural security property (narrow output channel) is a genuine advance over tool-calling agent architectures.

### Weaknesses the Candidate Must Address

- "No results" is a severe vulnerability. The dissertation's primary defense is that it proposes a formal model and evaluation protocol — but the *field* needs empirical benchmarks, not a protocol for eventual benchmarks.
- The conductor's lack of a narrow-channel security property mirrors the very vulnerability the action path claims to solve.
- The quality vector is heuristic and unvalidated against human judgment.
- Fleet-scale implications (conductor contention, cross-player trust sharing, `.nail` sync bandwidth) are acknowledged but not designed.
- Edge deployment (the browser tier) is more a vision statement than a functioning tier, and the dissertation does not distinguish between "DCA works on-server" and "DCA works on-edge."

### Closing Observation

The dissertation opens with an architectural inversion — "vector DB is the runtime, LLM is the compiler" — and closes with a philosophical claim — "systems whose architecture encodes the possibility of being wrong, so that evidence can always still get in." Both are well-stated. The gap between them is implementation. The strongest form of this defense would include a live demo of the null-adapter loop producing a deterministic bottle ledger, because that alone would validate the architecture's testability, which is the dissertation's core methodological claim.

The board recommends conditional pass: pending delivery of the null-adapter determinism test, the reflex hit-rate measurement, and a revised §12 that reports these results rather than projecting them.
