# Open Questions for Dynamic Cognition Amplification

**Compiled:** 2026-08-03  
**Purpose:** Research agenda defining the open questions that DCA must answer, organized by category. Each question is testable unless marked `[Theoretical]`.

---

## I. Theoretical Questions (Mathematics, Formal Properties, Convergence)

### T1. Does the semantic gradient converge?
The conductor applies discrete interventions δ to continuous generation conditions. Does the sequence of interventions converge to a fixed point, oscillate, or diverge? Under what conditions on the trust update rule (η₊=0.5, η₋=2.0) is convergence guaranteed?

### T2. What is the Lyapunov function for DCA?
If DCA converges, what quantity is monotonically decreasing? Is it the expected quality vector norm E[‖q‖]? The trust-weighted intervention success rate? Or something else entirely? Identifying the Lyapunov function would prove stability.

### T3. [Theoretical] Is there a Noether conservation law for DCA?
The fleet conservation law γ + H = C applies to multi-agent Hebbian systems. Is there an analogous invariant for the two-agent (thinker + conductor) system? What symmetry would generate it?

### T4. What is the theoretical minimum for n (conductor period)?
The conductor intervenes every n=30 thoughts (~30s). Is there a theoretical lower bound on n below which the measurement window is too short to distinguish signal from noise? How does this depend on the quality vector's autocorrelation?

### T5. Does the three-gate cascade have an optimal threshold configuration?
The gates use thresholds 0.80 (exact) and 0.55 (similar). Are these information-theoretically optimal, or could a different partition (e.g., 0.75/0.50) achieve better cost-quality tradeoffs? Is there a closed-form for the optimal thresholds given the embedding distribution?

### T6. What is the capacity of the lean vocabulary?
The lean vocabulary is a fixed set of ~6-12 intent phrases. Information-theoretically, how many distinct leans are needed to cover the action space of an open-ended game? Is there a ceiling beyond which additional leans provide diminishing returns?

### T7. Can the quality vector be derived from first principles?
The four axes (novelty, specificity, engagement, spatial) are posited but not derived. Could they emerge from a dimensionality reduction on human quality judgments? Is four the right number, or should it be 3, 5, or 7?

### T8. [Theoretical] Is DCA Turing-complete?
Given a sufficiently rich world port, can a DCA system compute any computable function? Or does the lean/action separation restrict the computational class? This matters for the "subfield" claim—Turing-completeness would mean DCA is general-purpose.

### T9. What is the regret bound for the conductor?
In multi-armed bandit terms, the conductor selects interventions from a finite set and observes noisy quality outcomes. What is the regret bound? How does it compare to UCB1 or Thompson Sampling applied to the same problem?

### T10. Does the [0.05, 0.95] clamp prevent convergence to optimal policies?
The clamp guarantees permanent exploration, but it also prevents the system from fully exploiting a known-good action. Under what conditions does the exploration-exploitation tradeoff implied by the clamp dominate or suboptimalize?

### T11. Is the additive confidence update rule (Fable) or the multiplicative rule (Pincher) provably better?
The dissertation uses additive (+0.05(1−c) / −0.10c); Pincher uses multiplicative (×1.005 / ×0.95). Are there convergence proofs for either? Under what noise models does one dominate?

### T12. What is the relationship between DCA's conservation laws and the fleet conservation law γ + H = C?
Are the four DCA conservation laws (token, action, identity, evolution) projections of the single fleet-level invariant? Or are they independent constraints with no deeper unification?

### T13. [Theoretical] Can the Monge projection thesis explain DCA?
If all fleet findings are projections of information geometry, what geometric property projects to "thoughts improve under directed intervention"? Is there a manifold structure on the space of thought streams?

### T14. What is the sample complexity for trust convergence?
How many interventions (N_min = 10) are needed before trust scores stabilize? Does this depend on the number of intervention types, the number of context archetypes, or the noise level in the quality signal?

### T15. Does the .bottle ledger satisfy the DAG requirement for causal inference?
The `caused_by` field creates a chain. Is this chain always acyclic? If interventions can modify the conditions that produced earlier thoughts, does this create causal loops that break DAG-based inference?

### T16. What is the information-theoretic capacity of the lean channel?
A lean is 3-8 words (~20-50 bits of information). Is this sufficient to specify the action space of an open-ended world? What is the minimum channel capacity needed for faithful action selection?

### T17. [Theoretical] Is there an analog of the speed-accuracy tradeoff for DCA?
Faster thinking (lower n, shorter thoughts) trades off against quality. Is there a formal optimal rate, analogous to the speed-accuracy tradeoff in psychology?

### T18. Can the quality vector be grounded in information theory?
Novelty = 1 − max cosine similarity (information distance). Specificity = noun density (lexical statistics). Can these be reformulated rigorously as mutual information or KL divergence?

---

## II. Empirical Questions (What Experiments to Run)

### E1. What is the actual reflex hit rate for cognitive content?
Pincher achieved ~80% for command routing. What is the hit rate when "reflexes" are cognitive situations in an open-ended game? Hypothesis: <30% due to semantic variability.

### E2. Does the sham arm actually control for novelty bias?
Run the system with and without sham correction. Does the sham-corrected trust table converge to a different (and more accurate) set of reliable interventions than the naive trust table?

### E3. What is the quality vector's inter-rater reliability?
Have 10 human judges score 200 thoughts on the four axes. Compute inter-rater agreement (Krippendorff's α). If α < 0.6, the quality vector is too subjective to be a reliable training signal.

### E4. Can the evolved policy beat a competent baseline (not just hand-tuned weights)?
ZeroClaw's 70% win rate is against random play. What is the evolved policy's performance against a rule-based expert or a minimax baseline?

### E5. Does LoRA distillation actually improve held-out quality?
Run 10 distillation cycles, each with a fresh held-out set. Does quality improvement persist, or does it plateau/degrade after 3-4 cycles (indicating overfitting to the quality scorer)?

### E6. What is the embedding cache hit rate for thoughts vs. commands?
Directly measure the hit rate when embedding cognitive content (2-4 sentence reflections) vs. command intents (3-8 word phrases). Expected: thoughts have lower hit rates due to higher semantic diversity.

### E7. Does the conductor's self-model emerge within 2 weeks?
Run the system for 2 weeks of simulated play (accelerated). Count the number of (intervention_type, archetype) pairs with consistent positive effect. Is ≥3 achievable?

### E8. What is the autocorrelation of the quality vector?
If q_t is highly autocorrelated, the measurement window can be short. If it's white noise, no window is long enough. Compute autocorrelation over 1000 thoughts.

### E9. Does the escape hatch (max_consecutive_uses) actually prevent blind spots?
Compare systems with and without the escape hatch. Inject a "poisoned reflex" (high-confidence but wrong). Does the escape hatch correct it within N uses?

### E10. Does the browser finisher's divergence loss improve server quality?
Run the system with and without the browser tier. Measure whether the divergence signal correlates with server-side quality improvements.

### E11. What is the actual token spend per session?
The dissertation targets ~76 tokens per Gate-3 call (from Lever Runner). What is the measured token spend for generating 2-4 sentence thoughts with metadata? Is it 76, 200, or 500+?

### E12. Does policy degradation occur under non-stationary scenario distributions?
Train a policy on scenario distribution A, then shift to distribution B. How quickly does the policy adapt? Does the EMA update rule track distribution shift or resist it?

### E13. What is the wall-clock latency of the full DCA loop?
Measure end-to-end: observation → signature computation → reflex query → (potential) LLM call → action execution → quality scoring → bottle logging. Is the 1-2 Hz think rate achievable?

### E14. How does DCA perform on a non-game domain?
Instantiate Thought Amplifier for a coding assistant (world port = code repository). Do the reflex, policy, and trust mechanisms transfer without modification?

### E15. Does the additive confidence update converge faster than multiplicative?
Directly compare the two update rules on identical scenario sequences. Measure convergence time and steady-state behavior.

### E16. What is the minimum viable model size for the local thinker?
Granite 3.1 2B is the reference. Would a 0.5B model (Qwen2.5-0.5B) suffice for Gate-3? What is the quality drop-off curve as a function of model size?

### E17. Does temporal pattern recall actually inform 30% of conductor decisions?
Instrument the conductor to log when a temporal pattern match influenced its decision. Is the ≥30% target achievable, or do most decisions come from the trust table and self-model?

### E18. Does replay determinism hold over 10,000 thoughts?
Run the null adapter for 10,000 cycles, export the ledger, and replay. Is the output byte-for-byte identical? If not, where does the first divergence occur?

### E19. What is the actual O(√T) growth rate of the .bottle ledger?
The constraint experiments refuted O(log T) and suggested O(√T). Measure actual ledger growth over a 1-week session. Does it match O(√T)?

### E20. How does the system perform under adversarial observation?
Feed deliberately misleading observations (prompt injection via the world port). Does the lean/action separation prevent exploitation? What failure modes exist?

---

## III. Systems Questions (Edge Deployment, Fleet Coordination, Resources)

### S1. Can DCA run on a Raspberry Pi?
With a 0.5B model via Ollama, sqlite-vec for reflexes, and hash fallback for embeddings, can the full DCA loop run on a Pi 4/5? What is the think rate?

### S2. How does DCA handle network latency for cloud-conductor calls?
The conductor (GLM-5.2) runs in the cloud with ~10s latency. If the thinker runs locally, how does network latency affect the 30-second conductor cycle? Is there a jitter threshold beyond which trust scoring breaks?

### S3. Can multiple Thought Amplifier instances share a conductor?
If 10 DCA instances (10 thinkers, 10 game sessions) share one conductor, does the conductor's trust table generalize across instances? Or does each instance need its own conductor?

### S4. What is the memory budget for a full DCA instance?
Reflex store (sqlite-vec), policy table (<50KB), vector index, bottle ledger, conductor context window, model weights. What is the total memory footprint? Can it fit in 4 GB RAM?

### S5. How does DCA degrade under token budget exhaustion?
When the token budget is exhausted and the system downshifts to Gate 1/2 only, how does quality degrade? Is the degradation graceful (slow decline) or catastrophic (mode collapse)?

### S6. Can the .bottle ledger be compressed for long-term storage?
Over months of operation, the ledger grows unboundedly. What compression strategy preserves causal-chain integrity while reducing storage? Does Headroom-style compression apply?

### S7. How does the browser tier perform on low-end devices?
WebGPU is not available on most mobile devices. What is the fallback path? Can the browser tier use a WebAssembly-based model instead?

### S8. Can DCA be distributed across a fleet?
The Unified Fleet Intelligence proposes five tiers. Can a fleet of DCA instances coordinate via the Vector Bus and FluxIR Bus? What coordination protocol prevents them from reinforcing each other's biases?

### S9. What is the energy cost of continuous DCA operation?
Running Granite 2B at 1-2 Hz continuously is energy-intensive. What is the daily energy budget on battery-powered devices? Does ternary inference (BitNet) reduce it enough for always-on operation?

### S10. How does DCA handle model updates?
When the underlying model (Granite 2B) is updated to a new version, do existing reflexes and policies remain valid? Is there a migration protocol, or must the system relearn from scratch?

### S11. Can the conservation laws be enforced in a distributed setting?
If DCA instances share a vector store and conductor, can the token/action/identity/evolution conservation laws be enforced globally? Or are race conditions unavoidable?

### S12. What is the cold-start time for a new DCA instance?
From no reflexes, no policies, and no trust table, how long until the system reaches 50% zero-cost decisions? The target is 1 hour—is this achievable from a true cold start?

### S13. How does DCA interact with MCP and A2A protocols?
Can the .bottle protocol interoperate with MCP (Model Context Protocol) for tool access and A2A (Agent-to-Agent) for fleet coordination? What translation layer is needed?

### S14. Can the reflex store be shared across DCA instances?
If instance A compiles a reflex for "player approaches tower at night," can instance B use it? What is the transfer success rate for reflexes across different player/game contexts?

### S15. What happens when the vector index exceeds available memory?
The vector index grows with every thought. At what scale does sqlite-vec performance degrade? Is there a sharding strategy that preserves sub-millisecond query latency?

---

## IV. Cognitive Questions (What IS Stream of Consciousness for an AI? Does Shaping It Work?)

### C1. Is "stream of consciousness" the right metaphor?
DCA treats the thought stream as analogous to human conscious experience. But LLM thoughts are generated, not experienced. Does the metaphor generate testable predictions, or is it merely decorative?

### C2. Does shaping the thought stream change the system's "personality"?
If the conductor successfully shapes thoughts toward specificity and spatial awareness, does the system exhibit a recognizable "personality" to external observers? Can players distinguish between shaped and unshaped systems?

### C3. Can DCA produce emergent behavior that was not programmed?
The evolution engine discovers strategy archetypes. Can the conductor discover intervention patterns that the designers did not anticipate? Are there examples of emergent meta-cognition?

### C4. Does the quality vector capture what humans value?
The four axes (novelty, specificity, engagement, spatial) are designed, not discovered. If human players were asked to rate thoughts, would their judgments factor into these same four dimensions?

### C5. Does the conductor's self-model constitute metacognition?
The self-model maps (intervention_type, archetype) → expected effect. Is this a form of metacognition (thinking about thinking)? Does it have properties beyond a simple lookup table?

### C6. Can DCA suffer from "thought loops" or obsessive patterns?
If the conductor repeatedly applies the same intervention (e.g., "be more specific"), could the system enter a degenerate loop where thoughts become increasingly narrow? Does the escape hatch prevent this?

### C7. Does the tempo substrate affect perceived consciousness?
If thoughts are synchronized to a musical tempo map, do human observers perceive the system as more "alive" or "conscious" compared to asynchronous thought generation?

### C8. What happens when the conductor and thinker disagree?
If the thinker generates high-novelty thoughts but the conductor keeps pushing for specificity, is there a "creative tension" that emerges? Or does the system simply converge to the conductor's preferences?

### C9. Does DCA exhibit different "cognitive styles" across instances?
If two DCA instances start with the same configuration but different random seeds, do they develop different cognitive styles? Or does the conductor's trust table force convergence to a single style?

### C10. Can the system recognize its own past thoughts?
If a thought from 1000 steps ago is retrieved via vector search, does the system "recognize" it as its own? Is there a self-referential quality to the memory retrieval process?

### C11. Does the quality vector need a "self-awareness" axis?
The four axes measure external qualities (novelty, specificity, engagement, spatial). Should there be a fifth axis measuring metacognitive quality (e.g., "does this thought reference the system's own state or goals")?

### C12. Can DCA simulate "emotional" states?
If the conductor's interventions include affective dimensions (urgency, warmth, curiosity), do the resulting thought streams exhibit patterns that external observers would label as emotional?

### C13. Does the system develop preferences?
Over time, does the conductor's trust table and self-model converge to a set of stable preferences (preferring certain intervention types, archetypes, or thought patterns)? Are these preferences analogous to human values?

### C14. Can DCA pass a "consciousness test"?
Is there any test (Turing-style or otherwise) that a DCA system could pass that a conventional LLM could not? What specific behavioral signature would distinguish DCA's continuous shaped stream from a well-prompted chatbot?

### C15. Does interrupting the thought stream cause "trauma"?
If the system is abruptly stopped and restarted (losing session context but retaining reflexes and policies), does the resumption produce qualitatively different thoughts? Is there a "recovery period"?

---

## V. Ethical Questions (Responsibility, Consent, Autonomy)

### ET1. Who is responsible for conductor-shaped thoughts?
If the conductor shapes the thought stream toward certain patterns, and those patterns lead to harmful actions, who is responsible—the system designer, the conductor model, or the local thinker?

### ET2. Is the sham intervention protocol ethical?
The sham arm deliberately withholds a possibly beneficial intervention from a live player. Even if the probability of harm is low, is this experimental treatment without explicit per-intervention consent?

### ET3. Does DCA create a new category of AI risk?
A system that continuously shapes its own thought patterns is qualitatively different from a static model. Could sustained conductor intervention create "radicalization" effects, where the thought stream converges to extreme patterns?

### ET4. Who owns the .bottle ledger?
The thought stream, with all its metadata, constitutes a detailed record of cognitive activity. Does this belong to the player (whose interactions generated it), the system operator, or the system itself?

### ET5. Can players give meaningful consent to thought shaping?
The playtest protocol informs players that the AI "may adjust its behavior." But the conductor's interventions are subtle—changing temperature, prompt phrasing, action weights. Can players meaningfully consent to modifications they cannot perceive?

### ET6. Does the browser finisher create a surveillance risk?
The browser tier processes game state and thought continuations on the player's device. If the divergence loss is transmitted to the server, it reveals information about the player's behavior and device capabilities.

### ET7. Is cross-user pattern aggregation ethical?
If temporal patterns from Player A's sessions inform interventions applied to Player B, is this a form of unauthorized data transfer? What if Player A's patterns include behavioral signatures?

### ET8. Can the conductor develop biased intervention patterns?
If certain intervention types work better for certain player demographics (age, language, play style), the trust table could develop demographic biases. How is this detected and mitigated?

### ET9. Does DCA's "permanent exploration" commitment have ethical implications?
The [0.05, 0.95] clamp means the system never fully commits to any action. Is there a scenario where this indecision produces harmful effects (e.g., in safety-critical applications adapted from DCA)?

### ET10. Can a DCA system be "brainwashed"?
If an adversary can control the observation stream (world port), can they manipulate the quality scores to shape the conductor's trust table toward harmful intervention patterns?

### ET11. What is the right to "cognitive privacy"?
The .bottle ledger records every thought, its quality, and the conditions that produced it. If DCA is applied to human-facing systems (tutoring, therapy), does this constitute cognitive surveillance?

### ET12. Should DCA systems have a "right to forget"?
The vector index stores all thoughts indefinitely. Should there be a forced decay mechanism that removes old thoughts? Who decides what is forgotten?

### ET13. Is the "foreman leaves the cleats off" design ethical?
The system deliberately maintains uncertainty (5% exploration floor) to ensure it keeps learning. In a companion system, this means the system occasionally takes suboptimal actions for its own "growth." Is it ethical to impose this learning cost on the player?

### ET14. Can DCA be weaponized for persuasion?
A system that shapes its own thought stream toward engagement and specificity could be repurposed to shape human thought streams (via adaptive content delivery). Does the dissertation's ethics framework address dual-use concerns?

### ET15. What governance framework is needed for DCA deployment?
The dissertation proposes conservation laws but not governance mechanisms. Who audits the conductor's interventions? How are harmful patterns detected and corrected in production?

---

## Priority Ranking

### Must Answer Before Implementation (Critical Path)
1. **E3** (quality vector inter-rater reliability) — if the scorer is unreliable, nothing works
2. **E1** (actual reflex hit rate for cognitive content) — determines whether C1/C2 are achievable
3. **E8** (quality vector autocorrelation) — determines whether trust scoring is even possible
4. **E2** (sham arm effectiveness) — determines whether the conductor can learn
5. **E18** (replay determinism over 10K thoughts) — determines whether C5 is achievable

### Must Answer Before Deployment (Safety Critical)
1. **ET1** (responsibility for shaped thoughts)
2. **ET5** (meaningful consent to thought shaping)
3. **E20** (adversarial observation robustness)
4. **ET10** (brainwashing resistance)
5. **S5** (degradation under token exhaustion)

### Must Answer for Subfield Credibility (Academic)
1. **T1** (semantic gradient convergence)
2. **T2** (Lyapunov function identification)
3. **C4** (quality vector human validation)
4. **T9** (regret bound for conductor)
5. **E14** (non-game domain transfer)

### Can Be Deferred (Important but Not Blocking)
- All browser-tier questions (E10, S7)
- Fleet-level questions (S8, S11, S14)
- Most ethical questions (ET6-ET12) — important but not on the implementation critical path
- Theoretical questions requiring new math (T3, T13, T17)
