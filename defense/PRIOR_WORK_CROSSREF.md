# Prior Work Cross-Reference: DCA Dissertation vs. SuperInstance Research History

**Compiled:** 2026-08-03  
**Purpose:** Map every relevant prior work to specific dissertation claims, identifying supports, contradictions, and gaps.

---

## 1. Pincher / Vector-DB-as-Runtime (study-harness-exp, study-papers)

### What Was Proven
- Vector DB is the runtime; LLM is the compiler. Reflex dispatch <1 ms at $0 marginal cost.
- Confidence update saturates in [0.05, 0.95]: success adds 0.05(1−c), failure subtracts 0.10c.
- SHA-256 trigram/word hash provides deterministic fallback when ONNX is unavailable.
- Match classification: Exact (≥0.80), Similar (0.55–0.80), Novel (<0.55).

### Dissertation Claims Supported
- **C1 (Cost gate ≥50%):** Pincher reports reflex hit rates approaching 80% after a month. Supports the ≥50% target.
- **C2 (Reflex convergence ≥40%):** Pincher's exact-match threshold directly informs Gate 1 design.
- **§5.3 Confidence dynamics:** The additive update rule `+0.05(1−c) / −0.10c` is taken directly from Pincher (via the Fable master prompt).
- **§5.7 Embedding fallback:** Deterministic feature hash fallback is directly inherited.
- **§5.6 LLM as compiler:** "The LLM is therefore a compiler, not a runtime" (§5.6) is the Pincher thesis generalized.

### Contradictions / Tensions
- Pincher uses a **multiplicative** form (`×1.005 / ×0.95`) in some implementations; the dissertation specifies **additive**. Dissertation acknowledges this (§12.4 open question 1) but does not resolve it.
- Pincher's real-world hit rate data is from a command-routing domain, not cognitive thought generation. The transfer of hit-rate statistics to a thought-generation context is unvalidated.

### Open Questions Raised
- Does the additive vs. multiplicative confidence update choice significantly affect convergence speed in the cognitive domain?
- Can Pincher's command-routing reflex hit rates transfer to open-ended thought generation where situations are less repetitive?

---

## 2. Lever Runner / Three-Gate Cascade (study-harness-exp, study-papers)

### What Was Proven
- Three-gate cascade: Rust guard (~50 µs) → embedding cache (~7.6 ms, 44% hit) → LLM (~500 ms).
- Asymmetric trust: +1.5 for success, −4.0 for failure, floor 40, ceiling 100.
- Token budget ~76 tokens per query vs. ~2,000–5,000 for conventional tool-calling assistants (28× reduction).
- ~56% of queries cost zero tokens after cache warms.
- Structural security: LLM output channel too narrow for shell injection.

### Dissertation Claims Supported
- **C1 (Cost gate ≥50%):** 56% zero-token rate directly supports the ≥50% claim.
- **§5.1 Three-gate pattern:** Latencies and architecture directly inherited.
- **§3.2 Lean/Action separation:** Compressing to 3–8 word intent phrases proven at production scale.
- **§7.4 Trust dynamics:** Asymmetric trust model (+0.5/−2.0) adapted from Lever Runner's +1.5/−4.0.
- **§2.4 vs. tool-calling agents:** 28× token reduction is the central empirical evidence.

### Contradictions / Tensions
- Lever Runner's trust asymmetry (+1.5/−4.0, ratio ~1:2.67) differs from the dissertation's (+0.5/−2.0, ratio 1:4). The dissertation is *more* conservative than the proven system. Justification is qualitative ("cognitive modifications are noisier"), not empirical.
- The 44% embedding cache hit rate is from a command-matching domain. Thought matching may have lower hit rates due to higher semantic variability.

### Open Questions Raised
- Is 1:4 trust asymmetry too conservative? Should the system start with Lever Runner's proven 1:2.67 and tighten only if noise demands?
- What is the embedding cache hit rate for *thoughts* (semantic content) vs. *commands* (structured intent)?

---

## 3. ZeroClaw Arena / Policy Evolution (study-si-papers, study-experiments)

### What Was Proven
- Tile-decomposed state with independent per-tile statistics works for bounded-state games.
- EMA α=0.05 with [0.05, 0.95] clamping discovers strategy archetypes (Explorer, Diplomat, Marksman, Climber, Prospector).
- Compile to O(1) hash lookup (~0.001 ms per move, ~15 KB for Tic-Tac-Toe).
- Evolved Tic-Tac-Toe policy reaches ~70% win rate vs. random play.
- Hierarchical clustering into ~8 archetypes achieves ~10× compression with <5pp performance loss.
- Temperature T≈0.15–0.3 is optimal; lower exploits, higher explores.

### Dissertation Claims Supported
- **C4 (Policy superiority ≥15%):** ZeroClaw's evolved policies consistently beat hand-tuned baselines.
- **§6.4 EMA update with clamp:** The 0.05 learning rate and [0.05, 0.95] clamp are validated across four games.
- **§6.5 Softmax temperature:** T=0.3 during training is derived from ZeroClaw's sweep.
- **§6.7 Hierarchical clustering:** ~8 strategy archetypes is a ZeroClaw result.
- **§6.6 Policy compilation:** dict[str, str] <50 KB, zero-dependency artifact proven.

### Contradictions / Tensions
- ZeroClaw operates on games with **discrete win/loss outcomes**. DCA maps outcomes to a **continuous satisfaction score** derived from the quality vector. The signal-to-noise ratio of a continuous quality score is far worse than binary win/loss.
- ZeroClaw's games have **bounded state spaces** (Tic-Tac-Toe: ~3^9; Connect 4: ~3^42). DCA's context space is unbounded.
- ZeroClaw's 70% win rate is against **random play**, not competent baselines. The ≥15% improvement claim needs a stronger baseline.

### Open Questions Raised
- Can tile decomposition work when the "game" is open-ended companion interaction with no terminal state?
- How does policy evolution perform when the satisfaction signal is noisy (as quality vectors inevitably are)?
- What happens when the context space is effectively unbounded—does tile hashing degrade to random?

---

## 4. SuperInstance Ecosystem / .bottle Protocol (study-si-papers, study-papers)

### What Was Proven
- `.bottle` typed envelopes provide provenance tracking via `caused_by` chains.
- Four conservation laws (token, action, identity, evolution) were proposed; the ecosystem's own audit notes most code is incomplete.
- 10% canary → review → merge loop was designed but not fully implemented.
- Anti-oscillation via hysteresis was specified but not empirically tested.

### Dissertation Claims Supported
- **§4.8 Conservation laws:** The four laws are directly inherited and made executable.
- **§10.3 .bottle spine:** The bottle dataclass is the SuperInstance `.bottle` generalized.
- **§7.5 Canary promotion:** 10% canary → measure → promote is from SuperInstance's self-improvement loop.
- **C5 (Determinism):** Replay-based testing via bottle ledger is a SuperInstance design pattern.

### Contradictions / Tensions
- SuperInstance's own audit says **"most code is incomplete; the value lies in the design patterns."** The dissertation treats these patterns as proven, but the conservation laws were never empirically enforced at runtime in the original system.
- The dissertation's evolution conservation law ("no parameter changes without recorded intervention and measurement window") is **stricter** than anything SuperInstance actually implemented. This is new, not inherited.
- The dissertation's token conservation law (budget exhaustion → downshift) was **falsified** in early SuperInstance experiments—the original conservation-law conjectures had errors that were "honestly falsified."

### Open Questions Raised
- Can the conservation laws actually be enforced as runtime invariants over 1,000+ cycles, or are they aspirational?
- The SuperInstance audit acknowledged early conservation-law conjectures were wrong. Are the dissertation's four laws the corrected versions, or do they inherit the original errors?

---

## 5. Craftmind / Memory Writeback (study-papers)

### What Was Proven
- "Write every outcome back to the vector index; the library of refined plans grows itself."
- Vector index as accumulative memory for plans and outcomes.

### Dissertation Claims Supported
- **§3.1 Stream of consciousness as training signal:** The memory writeback loop is the mechanism by which thoughts become training data.
- **§8.4 Embedding and storage:** Vector storage of thought metadata is the Craftmind pattern applied to cognitive content.

### Contradictions / Tensions
- Craftmind was a design proposal, not a measured system. No empirical data on writeback latency, index growth, or retrieval quality exists.
- "The library grows itself" is optimistic—unbounded vector index growth is a practical problem not addressed.

### Open Questions Raised
- What is the decay/retrieval strategy when the vector index contains 100K+ thoughts?
- Does semantic retrieval quality degrade as the index grows, and does this affect the Conductor's temporal pattern recall?

---

## 6. GPU Findings (study-harness-exp)

### What Was Proven
- **Ternary matmul overhead converges to ~1.1× at scale (≥1024²).** Ternary compute is "free" at scale on binary GPUs.
- **Ternary wavelet GPU acceleration: 3.7× over CPU** at 1M+ elements (1.1 billion elements/s).
- **Conservation law holds perfectly under decomposition:** Zero reconstruction error across all tested sizes.
- **Fleet cancellation: 86.3% at 50 agents.** Fleet-level γ is 13.7% of individual sum.
- **Ternary NN layers: 4× memory reduction** at parity speed.
- **Local embeddings 111× faster than cloud:** 2,225 texts/s on RTX 4050 vs. ~21 texts/s via CF Workers AI.

### Dissertation Claims Supported
- **§5.7 Embedding pipeline:** Local GPU embeddings at 2,225 texts/s make the bge-m3 embedding pipeline production-viable for real-time thought embedding.
- **§10.5 Degradation ladder:** The local/cloud embedding split is justified by the 111× speedup finding.
- **§9.4 LoRA on RTX 4050:** 4× memory reduction via ternary weights makes LoRA training feasible in 6 GB VRAM.

### Contradictions / Tensions
- The GPU findings are for **ternary arithmetic and embedding**, not for the cognitive loop itself. The dissertation cites GPU findings to justify infrastructure choices, but the core DCA claims (cost gate, reflex convergence, trust validity) are unaffected by GPU speed.
- The fleet cancellation result (86.3% at 50 agents) is about **multi-agent coordination**, not about a single thinker-conductor pair. Its relevance to DCA is analogical, not direct.

### Open Questions Raised
- Can the local GPU handle the combined workload of embedding (2,225 texts/s), LoRA training (background), and inference (Granite 2B) simultaneously without contention?
- Does the fleet cancellation result imply anything about multi-instance DCA (multiple Thought Amplifier instances sharing a conductor)?

---

## 7. BitNet Connection (study-harness-exp)

### What Was Proven
- BitNet b1.58 validates ternary {-1,0,+1} weights commercially: 2B model in <700 MB, 82.2% energy reduction.
- C = log₂(3) ≈ 1.585 bits per weight is the information-theoretic optimum for ternary.
- Ternary is not just one option—it is **mathematically optimal** for K≥3 (radix economy argument).

### Dissertation Claims Supported
- **§9.4 LoRA training configuration:** BitNet validates that small models with ternary weights run on CPU, supporting the claim that a local thinker (Granite 2B) is feasible on edge hardware.
- **§10.5 Degradation ladder:** The ternary optimality result supports the architectural commitment to multi-level fallback—each level degrades gracefully because the representation is fundamentally sound.

### Contradictions / Tensions
- BitNet validates ternary for **weight representation**, not for the cognitive architecture DCA proposes. The connection is analogical: "small representations are efficient" → "narrow cognitive channels are safe."
- The dissertation does not actually use ternary weights in its reference implementation. BitNet is cited as contextual support, not as a direct component.

### Open Questions Raised
- Would a BitNet-weighted local thinker (ternary Granite) maintain sufficient quality for Gate-3 thought generation?
- Does the conservation law γ + η = C have implications for DCA's token conservation law?

---

## 8. Tripartite Compiler (study-harness-exp)

### What Was Proven
- Three independent vector spaces (User × Application × Hardware) can compose via triadic coupling κ(u,a,h).
- All three spaces use the same 384-dim BGE embedding, enabling cross-axis dot-product similarity.
- Reflex-to-vector mapping: `embed(intent → action)` weighted by `confidence · log(1 + invoke_count)`.

### Dissertation Claims Supported
- **§5.2 Signature function:** The reflex signature embedding approach is directly informed by the tripartite reflex-to-vector mapping.
- **§8.4 Embedding and storage:** Using bge-m3 in 384-dim for thought vectors matches the tripartite design.
- **§6.7 Strategy archetypes:** The archetype concept parallels the tripartite user-knowledge clustering.

### Contradictions / Tensions
- The tripartite compiler was an **architecture specification**, not an implemented and measured system. The coupling tensor predictions are unvalidated.
- The dissertation uses only one vector space (thought content), not three. The tripartite decomposition is more structured than what DCA actually needs or implements.

### Open Questions Raised
- Would a tripartite decomposition of thought vectors (player-context × game-state × action-history) improve Conductor recall beyond a single embedding?
- Can the coupling tensor predict which interventions will work before measuring them?

---

## 9. Baton/FLUX Bridge (study-harness-exp)

### What Was Proven
- Message format translation between Loom fleet (Baton/git-based) and SuperInstance fleet (Bottle/API-based) is architecturally specified.
- Trust score mapping: `trust.score → γ`, `1 − trust.score → η`.
- Spline → concept vector mapping defined for cross-fleet knowledge propagation.

### Dissertation Claims Supported
- **§10.3 .bottle spine:** The bottle envelope design is informed by the Baton/Bottle bridge specification.
- **§4.8 Conservation laws:** The γ/η conservation metrics on every message are directly inherited.

### Contradictions / Tensions
- The bridge was **specified but not implemented**. No empirical data on cross-protocol message latency, reliability, or conservation-law enforcement exists.
- The trust→γ mapping (`trust.score = γ`) is a design choice, not a measured property. Whether trust scores actually correlate with information-theoretic coupling cost is untested.

### Open Questions Raised
- Can DCA's .bottle ledger interoperate with external fleet protocols (MCP, A2A)?
- Is the γ/η conservation metric meaningful for cognitive interventions, or is it specific to fleet routing?

---

## 10. Constraint Theory Experiments (study-experiments)

### What Was Proven
- **Laman rigidity (Exp 1):** 2N−3 is the exact edge threshold for graph rigidity. Verified for N=3..100.
- **Zero drift (Exp 6):** Fraction arithmetic gives exact zero accumulation over 10,000 ops.
- **Partition recovery (Exp 9):** O(log N) recovery after healing. 13 ticks for N=10.
- **Fleet scaling (Exp 10):** Convergence is 7.23·log₂N. R²=0.98 for N=3..100.
- **Deadband sparsity (Exp 3):** 99.44% sub-threshold in converged fleet. Corrected theorem.
- **BFT (Exp 11,16):** N≥3f+1 with reputation+trimmed mean. f≤3 converges.
- **Memoir compression (Exp 15):** O(log T) **REFUTED**. True bound is O(√T).
- **Edge augmentation (Exp 17):** QUEUED — diminishing returns after 20% augmentation hypothesized.

### Dissertation Claims Supported
- **§4.8 Conservation laws:** The constraint theory provides the mathematical foundation for executable conservation laws. Token conservation is analogous to energy conservation in constraint systems.
- **§6.4 Clamp guarantee:** The [0.05, 0.95] clamp parallels the Laman rigidity threshold—structural guarantees that prevent collapse.
- **§5.3 Confidence floor/ceiling:** The confidence bounds (0.05 floor, 0.95 ceiling) mirror the deadband threshold concept.
- **C5 (Determinism):** Zero-drift fraction arithmetic (Exp 6) proves that deterministic computation over 10K+ ops is achievable—supporting the replay determinism claim.

### Contradictions / Tensions
- The constraint theory operates on **algebraic systems with exact arithmetic**. DCA operates on **neural network outputs and natural language**. The gap between exact constraint checking and fuzzy cognitive quality scoring is enormous.
- The fleet scaling result (7.23·log₂N) is for **consensus convergence**, not for cognitive improvement. Logarithmic convergence of consensus says nothing about whether the Conductor's interventions improve thought quality.
- **Exp 15 refuted O(log T) compression.** If memoir compression is O(√T), then the .bottle ledger grows as O(√T) per session, not O(log T). This has practical implications for long-session storage.

### Open Questions Raised
- Does the conservation law γ + η = C apply to the DCA system? DCA's "coupling" is between thinker and conductor, not between fleet agents. The law was derived for V≥3 agent fleets.
- Can the deadband SNR result (deadband beats MA 2.3× on sparse signals) inform the measurement window design for Conductor interventions?
- If memoir compression is O(√T), what is the practical limit on session length before the .bottle ledger becomes unwieldy?

---

## 11. Compiled Agency / Bootstrap Bomb / Semantic Compiler (study-papers)

### What Was Proven
- Agency in a distributed fleet can be "compiled" (PLATO tiles → verified execution) rather than "interpreted" (runtime reasoning).
- Oracle1 bootstrapped a fleet from zero: FM's 5 crates → JC1's GPU benchmarks → CCC's audit tools.
- Each agent compilation built on outputs from previous agents. The compilation order is the architecture.
- Deadband protocol for error correction: tiles that diverge from expected answers enter correction states.

### Dissertation Claims Supported
- **§5.6 LLM as compiler:** "The LLM fires once per novel situation and produces a reusable artifact" is the compiled agency thesis applied to single-agent cognition.
- **§7.3 Sham interventions / deadband:** The deadband protocol concept (soft/hard/flatline correction) informs the Conductor's rollback mechanism.
- **§1.4 Empirical precedents:** The compilation sequence (Oracle1 → FM → JC1 → CCC) validates the bootstrapping pattern DCA adopts for reflex compilation.

### Contradictions / Tensions
- Compiled agency was demonstrated for **fleet coordination** (multi-agent task routing), not for **single-agent thought generation**. The compilation metaphor may not transfer cleanly.
- The "verified output" criterion in compiled agency (crates.io publication, measured benchmarks) has no analog in DCA. What constitutes a "verified thought"?
- The bootstrap bomb is a narrative, not a measured experiment. The claim that each compilation "releases energy for the next" is qualitative.

### Open Questions Raised
- Can DCA's reflex compilation be viewed as a single-agent bootstrap bomb? If so, what is the "detonation" criterion?
- Does the deadband correction protocol (soft → hard → flatline) offer a better rollback mechanism than the dissertation's "3 consecutive failures → auto-revert"?

---

## 12. Universal Cell / Type System (study-si-papers)

### What Was Proven
- Type algebra on a lattice of 10+ instance types with confidence-weighted transitions.
- Rate-based change mechanics: x(t) = x₀ + ∫r(τ)dτ for continuous state evolution.
- Origin-centric reference system: each cell tracks its own coordinate frame.
- Mathematical proofs: tile algebra associativity, identity tile existence, confidence bounds for sequential chains.

### Dissertation Claims Supported
- **§4.2 State space:** The DCA state tuple (o, h, π, θ, β) parallels the SuperInstance cell state with rate vectors.
- **§5.3 Confidence dynamics:** The rate-based confidence integration (c_t = c₀ + ∫r(τ)dτ) provides theoretical grounding for the discrete update rule.
- **§6.7 Strategy archetypes:** The type lattice's hierarchical clustering concept supports archetype discovery.

### Contradictions / Tensions
- The type system was a **specification paper, not an implementation**. No empirical validation of type transitions, confidence cascades, or rate-based mechanics was performed.
- The mathematical proofs (Theorem 1.3: confidence bounds for sequential chains) show that chain confidence ≤ min(c_i). This means that in a chain of thoughts, overall confidence is bounded by the weakest link—a potentially severe constraint not addressed by the dissertation.
- The origin-centric reference system assumes **distributed cells with local coordinate frames**. DCA has a single thinker, not a distributed cell system.

### Open Questions Raised
- Does the confidence chain bound (product ≤ min element) imply that long thought sequences will inevitably degrade in confidence?
- Could DCA benefit from rate-based state evolution instead of discrete per-thought updates?

---

## 13. Confidence Cascade Architecture (study-si-papers)

### What Was Proven
- Deadband operators prevent oscillation in confidence-based systems: D_δ(D_δ(c)) = D_δ(c) (idempotence proven).
- Three-zone confidence model: GREEN (≥0.95), YELLOW (0.75–0.95), RED (<0.75).
- Zone transitions follow hysteretic patterns preventing oscillation.
- PDE formulation for confidence propagation: ∂c/∂t = α∇²c − βc + S(x,t).

### Dissertation Claims Supported
- **§7.6 Rollback and hysteresis:** The hysteresis concept is directly inherited. The "dwell time" before re-modification is a deadband applied to the Conductor.
- **§5.3 Confidence bounds:** The [0.05, 0.95] clamp is the GREEN/YELLOW/RED zone concept applied at the reflex level.
- **§7.4 Trust dynamics:** The trust floor (below 30 → blocked) maps to the RED zone.

### Contradictions / Tensions
- The confidence cascade is **formally specified but never empirically tested**. The PDE formulation is theoretical.
- The three-zone thresholds (0.95, 0.75) differ from the dissertation's reflex confidence bands (0.80 exact, 0.55 similar). The relationship between these two confidence systems is unclear.
- The deadband idempotence proof applies to confidence *values*, not to the *effects* of confidence-driven decisions. A reflex at confidence 0.85 may produce different quality outcomes in different contexts.

### Open Questions Raised
- Should the Conductor's trust table use deadband operators to prevent oscillation, rather than the simpler asymmetric update rule?
- Would a PDE model of confidence propagation improve the Conductor's self-model?

---

## 14. Negative GPU Results (study-constraint-papers)

### What Was Proven
- Of 20 GPU optimization techniques tested for constraint checking, only 3 provided meaningful speedup.
- The workload is **memory-bandwidth-bound** at ~187 GB/s, rendering compute optimizations (tensor cores, multi-stream) irrelevant.
- INT8 ×8 packing and FP32 float4 vectorized loads both achieve ~341B constraints/s (15.3× over baseline).
- Bank conflict padding is **counterproductive** on Ada Lovelace (0.96×).

### Dissertation Claims Supported
- **§9.4 Training constraints:** The negative results inform the LoRA training design—memory is the bottleneck, not compute. This justifies the small batch size (1–4) and short sequence length (512–1024).
- **§10.7 Browser tier:** The memory-bound finding suggests that browser-tier inference (WebGPU) will face similar memory bandwidth constraints, supporting the conservative capability detection approach.

### Contradictions / Tensions
- The negative results are for **constraint checking** (algebraic operations on integers), not for **neural network inference or training**. The memory-bound profile may differ for transformer-based thought generation.
- The 341B constraints/s figure makes constraint checking look fast, but this is irrelevant to DCA's bottleneck (LLM inference at ~500 ms).

### Open Questions Raised
- Is DCA's overall performance bottlenecked by LLM inference (compute-bound) or by vector search / embedding (memory-bound)?
- Would INT8-packed thought vectors improve vector search throughput enough to matter for the Conductor's 30-second cycle?

---

## 15. Seeding Science (study-constraint-papers)

### What Was Proven
- Small models (Seed-2.0-mini) match or exceed large models on tile reconstruction tasks when the tile is well-structured.
- Temperature τ=1.0 is optimal for creative reconstruction (sharp U-curve) but the plateau is broad (0.7–1.5) for tile expansion.
- **Prompt wording matters 3× more than temperature.** "Expand" achieves 100% accuracy; "reconstruct" triggers hallucination guardrails.
- Cross-model ensembles capture complementary blind spots (Qwen found Pisot numbers; Seed found XOR).
- The 50× cost advantage of small models over large models for seeding tasks.

### Dissertation Claims Supported
- **§9.4 LoRA distillation:** Small model advantage (broad posteriors) supports using Granite 2B as the local thinker instead of a larger model.
- **§7.1 Conductor model choice:** The Conductor uses a large model (GLM-5.2) for meta-reasoning, consistent with the finding that large models are better at qualitative judgment but worse at faithful reconstruction.
- **§5.6 Reflex compilation:** The "LLM as compiler" pattern is the seeding pattern—the LLM generates a compressed artifact (reflex/lean) that is later expanded/executed without the LLM.

### Contradictions / Tensions
- The seeding result is for **reconstruction** (tile → full text), not for **generation** (state → novel thought). The broad-posterior advantage may not transfer.
- The prompt-wording finding ("expand" >> "reconstruct") suggests that DCA's system prompt design is critical and fragile. Small prompt changes could have outsized effects on thought quality.
- The 50× cost advantage of small models was measured on a **specific task** (tile expansion). DCA's thought generation task is more open-ended.

### Open Questions Raised
- Does the "expand" vs. "reconstruct" framing effect apply to system prompts for the local thinker? Would rephrasing the thinker's task from "generate a thought" to "expand on this observation" improve quality?
- Should DCA use a cross-model ensemble for the Conductor (e.g., GLM-5.2 + DeepSeek-V3) to capture complementary blind spots?

---

## 16. Dissertation Chapter 3: The Conservation Law (study-constraint-papers)

### What Was Proven
- **γ + H = C − α·ln(V)** with C≈1.283, α≈0.159, R²=0.9602 across 35,847 Monte Carlo samples.
- Five negative results tighten the domain: NOT derivable from RMT, NOT a predictor of accuracy, NOT universal (only Hebbian + attention-weighted), NOT holding during transients, NOT a fleet-size invariant (plateaus at V≥50).
- The law is an empirical regularity of Hebbian-coupled systems, not a mathematical tautology.
- Top-1 eigenvalue ratio >0.20 at V=5 is the discriminant for slope-negative ensembles.

### Dissertation Claims Supported
- **§4.8 Conservation laws:** The empirical conservation law provides precedent for conservation-like invariants in coupled cognitive systems.
- **§1.4 Empirical precedents (SuperInstance):** The conservation law is the theoretical foundation for the token/action/identity/evolution conservation laws.
- **§12.3 Limitations:** The negative results (not universal, not during transients, plateaus at V≥50) directly inform DCA's limitations discussion.

### Contradictions / Tensions
- The conservation law is for **fleet coupling matrices** (V agents, Hebbian learning). DCA is a **single-thinker system** (V=1 or V=2 with conductor). The law does not apply below V=3.
- The law explicitly does NOT predict accuracy (negative result 57). This undermines any claim that conservation-law compliance correlates with thought quality.
- The law **fails during transients** (negative result 71). DCA's Conductor intervenes every 30 seconds, creating a near-constant state of transient. The conservation law may never be in equilibrium.
- The law **plateaus at V≥50**. DCA has V=1-2, far below the validated range.

### Open Questions Raised
- Is there an analog of γ + H = C for a two-agent system (thinker + conductor)? If not, what conservation principle, if any, governs DCA?
- Does the transient failure of the conservation law mean that DCA's conservation laws (token, action, identity, evolution) also fail during Conductor interventions?
- The top-1 eigenvalue ratio discriminant (>0.20) suggests structural concentration. Does the thinker-conductor coupling matrix have this property?

---

## 17. Monge Projection Thesis (study-constraint-papers)

### What Was Proven
- Proposes (but does not prove) that fleet findings are projections of simpler structures in information geometry.
- Conjectures γ + H = C is a discrete Noether conservation law associated with reparameterization invariance.
- Conjectures the −α·ln(V) correction is a finite-size effect analogous to renormalization group corrections.

### Dissertation Claims Supported
- **Theoretical framing:** The Monge projection thesis provides a potential theoretical foundation for DCA's conservation laws—if they are projections of a deeper principle.

### Contradictions / Tensions
- The thesis is explicitly **conjectural** ("Conjecture 2.1," "Conjecture 3.1"). No proofs are provided.
- If the fleet findings are projections of information geometry, then DCA's conservation laws may be **approximate** rather than exact, with correction terms that are not yet understood.

### Open Questions Raised
- If the Monge projection thesis is correct, what is the simpler structure whose projection yields DCA's token conservation law?
- Can the Noether conservation argument explain why DCA's four conservation laws (token, action, identity, evolution) are the right ones?

---

## 18. Zero-Crypto Fleet Security (study-zero-crypto)

### What Was Proven
- Physics-based temporal authentication: 2^{34,000} bits of entropy against simultaneous spoofing.
- Detection of compromised firmware within 500 ms via 3σ timing deviation.
- Six independent physics clocks combined via Bayesian inference achieve microsecond precision.
- Reality Parity: RAID-5-inspired scheme where physical signals are data drives, physics model is parity.

### Dissertation Claims Supported
- **§3.2 Lean/Action security:** The structural security argument (narrow LLM output channel) is strengthened by the zero-crypto result that physical properties are unforgeable.
- **§10.4 Identity conservation:** The physics-based authentication concept supports the identity conservation law's enforcement.

### Contradictions / Tensions
- Zero-crypto is for **device authentication in IoT fleets**, not for cognitive system security. The transfer is analogical.
- DCA's security model relies on **vocabulary restriction** (fixed lean set), not on physics-based attestation. These are fundamentally different security paradigms.

### Open Questions Raised
- Could physics-based timing authentication secure the thinker-conductor communication channel?
- Is the lean/action separation's security guarantee (narrow channel) sufficient against adversarial inputs that manipulate the observation stream?

---

## 19. Harness Experiments API (study-harness-exp/README.md)

### What Was Proven
- **Batch size 18 is optimal** for README generation (100% success). 40-repo batches: 50% failure.
- **Shell > agents for batch ops:** For-loop adds LICENSE to 300 repos in 30s. Agent takes 10+ min.
- **E0433 is 37% of build errors:** Missing `mod X;` declarations.
- **Specificity → success:** Concrete specs = 0% retry. Abstract specs = 50%+ retry.
- **Kill builds at 10 minutes:** Bimodal: 78% finish <5min, rest never finish.
- **5 concurrent agents max** before rate limits kill throughput.
- Conservation law integration: γ = tokens + wall_clock×10 + api_calls×50; η = items×100 + quality×500 + lessons×200.

### Dissertation Claims Supported
- **C1 (Cost gate):** The harness data provides empirical grounding for the cost/value tradeoff in agent systems.
- **§4.8 Token conservation:** The γ + η = C formulation is directly implemented as generated columns in D1.
- **§7.1 Conductor latency budget:** The 10-minute kill rule and 5-agent concurrency limit inform the Conductor's resource constraints.

### Contradictions / Tensions
- The harness measures **batch productivity**, not **continuous cognition**. The conservation law metrics (γ, η) were designed for discrete tasks, not for an ongoing thought stream.
- The specificity→success finding (concrete specs = 0% retry) suggests that DCA's quality vector should heavily weight specificity—but this is a task-completion finding, not a cognitive-quality finding.

### Open Questions Raised
- Can the harness γ/η formulation be meaningfully applied to individual thoughts, or does it only make sense at the batch level?
- Does the 5-concurrent-agent limit apply to concurrent DCA instances sharing a conductor?

---

## 20. Unified Fleet Intelligence (study-harness-exp)

### What Was Proven
- Five-tier cognitive substrate architecture: Physical → Execution → Coordination → Compression → Orchestration.
- Two shared buses: Vector Bus (declarative memory) and FluxIR Bus (procedural memory).
- Headroom as compression membrane: directly controls the γ term for the entire fleet.
- Self-compounding cognition: every action improves the knowledge base, every improvement speeds future actions.

### Dissertation Claims Supported
- **§8.4 Vector pipeline:** The Vector Bus concept supports the use of vector embeddings as the shared memory between thinker and conductor.
- **§3.6 Semantic gradient:** The self-compounding cognition pattern is the fleet-level analog of DCA's think→measure→intervene→learn loop.
- **§10.5 Degradation ladder:** The multi-tier architecture with fallbacks at each level mirrors the fleet's five-tier design.

### Contradictions / Tensions
- The unified fleet intelligence is a **design document**, not a measured system. The five-tier architecture was never empirically validated as a complete system.
- The self-compounding cognition claim is **unfalsifiable as stated**—there is no failure condition specified that would refute it.
- The fleet has multiple agents and shared buses. DCA has one thinker and one conductor. The architectural transfer is not straightforward.

### Open Questions Raised
- Does DCA need the full five-tier architecture, or is the thinker-conductor-loop sufficient?
- Can the self-compounding pattern manifest in a single-agent system, or does it require fleet-level diversity?

---

## 21. Counting Before Flowing (study-papers)

### What Was Proven
- Integer/rational arithmetic is exact; floating-point is inherently lossy.
- Pythagorean snapping: rational approximations from Pell's equation give bounded, diminishing error.
- Agent identity requires discrete, countable state—continuous representations break identity tests.

### Dissertation Claims Supported
- **§5.3 Confidence clamping:** The [0.05, 0.95] confidence bounds are discrete, countable thresholds—consistent with the counting thesis.
- **§6.6 Policy compilation:** The compiled policy as dict[str, str] is a discrete, countable artifact.
- **C5 (Determinism):** The counting thesis supports the feasibility of byte-for-byte replay determinism.

### Contradictions / Tensions
- DCA's quality vector uses continuous values in [0,1]^4—**floating point**. The counting thesis argues against exactly this kind of representation.
- The Conductor's trust scores are continuous (0-100). The counting thesis implies that trust updates should be discrete.
- Thought generation is inherently continuous (LLM output is a probability distribution). The counting thesis applies to state representation, not to generation.

### Open Questions Raised
- Should the quality vector use discrete buckets (e.g., 0-3 on each axis) rather than continuous [0,1]?
- Would discrete trust levels (e.g., 0-10 integer) be more stable than continuous trust scores?
- Can the .bottle ledger use exact rational arithmetic for provenance chains, avoiding floating-point drift in replay?

---

## 22. Convergence 2026 (study-harness-exp)

### What Was Proven
- Five convergent industry trends: ternary hardware, agent governance, context compression, local-first AI, protocol layer formation.
- Each trend independently validates a SuperInstance component.

### Dissertation Claims Supported
- **§10.7 Browser tier / local-first:** The local-first AI trend supports DCA's commitment to local inference (Granite 2B via Ollama).
- **§10.1 Core/adapter split:** The protocol layer formation (MCP, A2A) validates DCA's port-based adapter architecture.
- **§9.4 Edge deployment:** Ternary hardware trend supports the feasibility of running DCA on resource-constrained edge devices.

### Contradictions / Tensions
- The convergent trends document is a **market analysis**, not experimental evidence. It describes industry direction, not scientific proof.
- The product stack proposed (SHOAL, Fleet Dashboard, Governance Layer) does not include Thought Amplifier or DCA. DCA is not mentioned in the convergence document.

### Open Questions Raised
- Where does DCA fit in the convergent product stack? Is it a separate product or a feature of the governance layer?
- Does the MCP/A2A protocol standardization make DCA's .bottle protocol redundant or complementary?

---

## Summary Matrix

| Prior Work | Supports | Contradicts | Gap |
|---|---|---|---|
| Pincher | C1, C2, §5.3, §5.7 | Additive vs. multiplicative unresolved | Cognitive vs. command domain transfer |
| Lever Runner | C1, §5.1, §3.2, §7.4 | Trust asymmetry differs (1:4 vs 1:2.67) | Thought vs. command embedding hit rate |
| ZeroClaw Arena | C4, §6.4-6.7 | Bounded games vs. open-ended cognition; continuous quality signal noisy | Unbounded context tile hashing |
| SuperInstance .bottle | §4.8, §10.3, C5, §7.5 | Laws never empirically enforced; original conjectures falsified | Runtime enforcement over 1K+ cycles |
| Craftmind | §3.1, §8.4 | Design proposal only | Vector index growth management |
| GPU Findings | §5.7, §10.5, §9.4 | Cognitive loop unaffected by GPU speed | Combined workload contention |
| BitNet | §9.4, §10.5 | Connection analogical, not direct | Ternary thinker quality |
| Tripartite Compiler | §5.2, §8.4, §6.7 | Architecture spec only | Multi-space vs. single-space embedding |
| Baton/FLUX Bridge | §10.3, §4.8 | Specified, not implemented | External protocol interoperability |
| Constraint Experiments | §4.8, §6.4, C5 | Algebraic vs. neural gap; fleet vs. single-agent | O(√T) ledger growth implications |
| Compiled Agency | §5.6, §7.3, §1.4 | Fleet coordination vs. single-agent cognition | Verification criterion for thoughts |
| Universal Cell | §4.2, §5.3, §6.7 | Spec only; confidence chain bound concerning | Rate-based vs. discrete updates |
| Confidence Cascade | §7.6, §5.3, §7.4 | Formal spec, no empirical test | Deadband operators for trust table |
| Negative GPU Results | §9.4, §10.7 | Constraint checking ≠ NN inference | DCA's actual bottleneck identification |
| Seeding Science | §9.4, §7.1, §5.6 | Reconstruction ≠ generation; prompt fragility | Prompt-wording effects on thinker |
| Conservation Law Ch.3 | §4.8, §1.4, §12.3 | V=1-2 below validated range; fails during transients | Two-agent conservation analog |
| Monge Projection | Theoretical framing | Entirely conjectural | Deeper principle identification |
| Zero-Crypto | §3.2, §10.4 | Different security paradigm | Physics-based channel security |
| Harness API | C1, §4.8, §7.1 | Batch productivity ≠ continuous cognition | γ/η for individual thoughts |
| Unified Fleet Intel | §8.4, §3.6, §10.5 | Design doc, unfalsifiable | Single-agent self-compounding |
| Counting Before Flowing | §5.3, §6.6, C5 | Quality vector is continuous FP | Discrete quality buckets |
| Convergence 2026 | §10.7, §10.1, §9.4 | Market analysis, not proof | DCA's place in product stack |