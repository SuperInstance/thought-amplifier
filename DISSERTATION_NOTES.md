# Dynamic Cognition Amplification (DCA): Dissertation Notes

Working repository for doctoral dissertation establishing DCA as a new subfield.
Follow the read → note → write → section workflow. Never hold more than 3 documents of insight in working memory.

## Document Takeaways

### REPO_DESIGN.md
- **Substrate independence via hard core/adapter split.** `amplifier/` speaks only `Observation`, `Thought`, `Action`, `Outcome`; game-specific logic is banished to `adapters/`. This separation is the central architectural claim and the precondition for treating DCA as a general subfield rather than a single-game hack.
- **The four-line thesis of continuous cognition.** Training signal = stream of consciousness; loss = play quality (novelty, specificity, engagement, spatial awareness); gradient = prompt/parameter adjustment every 30 s; model update = reflex compilation, policy breeding, trust accrual, and LoRA baking happening in parallel loops.
- **Recurring three-gate cascade.** Every expensive operation is preceded by a free gate and a cheap gate: reflex (<1 ms) → compiled policy (O(1)) → LLM (~500 ms). The same pattern recurs at conducting and acting. A fallback ladder makes ≥50% decisions at $0 a runtime invariant, not a budget aspiration.
- **`.bottle` as the interpretability spine.** Typed envelopes with `caused_by` links turn the loop into a DAG; the append-only ledger makes a stochastic loop deterministic-for-replay. These are the mechanisms that make 100% interpretability and conservation-law enforcement possible.
- **Five subsystems and their actual gaps.** Reflex compiler, evolution engine, trust scoring (the real gap — scoring Conductor interventions, not cascade gates), temporal→vector pipeline, and LoRA distillation. Trust is highest value per line because the Conductor has been modifying prompts/parameters blindly.

### DYNAMIC_COGNITION_ARCHITECTURE.md
- **Three-layer cognitive stack.** The Local Thinker (Granite 3.1 2B, ~1–2 thoughts/s) produces a continuous stream of consciousness; the Conductor (GLM-5.2 / DeepSeek V3, every 30–60 s) performs deep meta-learning; the Game/World provides observations and outcomes. This split is the anatomical basis for DCA.
- **Algorithmic action selection from generative intent.** The LLM emits a 3–8 word "lean" (e.g., `inspect tower_top`); a lightweight, pre-approved policy table converts it to concrete action. This is the structural security property that prevents unconstrained tool execution.
- **Quality as loss function.** Play quality is decomposed into novelty, specificity, emotional engagement, and spatial awareness. The Conductor's objective is qualitative improvement of thoughts, not minimization of a pre-defined numeric loss.
- **T-minus / MIDI temporal encoding.** Game events are canonized into beat-based sequences (`B8:E72:v85 → ...`) and embedded with the same bge-m3 model used for skills, enabling vector search over *rhythms of play*.
- **Novelty claim: always-on directed learning.** Traditional ML is collect → train offline → deploy → repeat. DCA is continuous: the model is always playing, always being directed, and the training signal is the stream of consciousness itself.

### BROWSER_NATIVE_AI_RESEARCH.md
- **Chrome built-in AI APIs.** Gemini Nano (~2.7B params, Chrome 138+) exposes purpose-built APIs: Prompt, Summarization, Writer, Rewriter, Translation, Language Detection. Requirements are steep (~22 GB disk, GPU >4 GB or CPU ≥16 GB), so capability detection and fallbacks are mandatory.
- **WebGPU/WebNN + Transformers.js/WebLLM.** Browser-native inference of Phi-3-mini 3.8B / Qwen2.5-1.5B is feasible. The recommended path is Side Panel Extension + SSE (Phase 1, 1–2 weeks), then layer WebGPU inference.
- **Local persistence primitives.** IndexedDB and OPFS store journals, model weights, and cached results. `navigator.storage.persist()` mitigates browser storage eviction.
- **Graceful degradation chain.** WebGPU inference → WASM inference → Chrome built-in AI → server-side API → cached read-only journal. Every browser-native feature must have a fallback.
- **Browser as ambient AI runtime.** Side panel stays open while browsing/playing; Web Audio sonifies thoughts; TTS narrates; WebGL visualizes. The browser becomes a multi-sensory, privacy-preserving cognitive extension — but only when hardware permits.

### DEEPSEEK_BROWSER_DESIGN.md
- **Browser as full AI runtime.** WebGPU inference, IndexedDB journaling, Service Worker caching/sync, and WebRTC mesh together can make the browser self-contained after initial load — zero backend, zero ongoing cost.
- **Shadow DOM as cognitive encapsulation.** Scenario 4 maps each thought type (`explore`, `build`, `inspect`, `speak`, `reflect`) to a custom element with its own shadow DOM. The browser's custom-element system becomes a native cognitive taxonomy.
- **DOM as game world (Scenario 2) is deferred research.** CSS properties map to physics (`z-index` = elevation, `opacity` = stealth, `background-color` = material). The panel and REPO_DESIGN both defer this due to consent, safety, and scope concerns.
- **Recommended build order.** Start with Web Components as thought types (6 weeks), layer living webpage layout (3 weeks), add Service Worker + WebGPU + IndexedDB MVP (4 weeks), then experiment with multi-tab (3 weeks).
- **Model usage economics.** Five deep design explorations totaled ~20K output tokens for ~$0.051 on DeepInfra, reinforcing the token-lean thesis: speculative design should be cheap and fast.

### MULTI_MODEL_PANEL_DISCUSSION.md
- **Unanimous hybrid browser/server split.** All three panelists agreed: browser runs the fast reactive thinker (Phi-3-mini / Qwen2.5-1.5B via WebLLM+WebGPU, <50 ms); the Conductor stays server-side (GLM-5.2) because it needs full context and a large model.
- **Latency asymmetry as a teaching signal.** The browser *predicts*; the server *validates*. The difference between browser-predicted continuation and Granite's actual output is logged as **divergence loss** and consumed by the Conductor to adjust prompts.
- **Context anchor pulses.** Every 0.5–1 s the server pushes a compact packet (last 8 tokens, game state, beat position, quality signals). The browser finisher grounds completions in this anchor and therefore cannot hallucinate rule-breaking continuations.
- **Privacy and consent as first-class constraints.** Browser-native AI with DOM/page access, sensors, and cross-tab behavior raises real consent concerns. The panel recommended deferring DOM Resonance Questing, cross-tab NPCs, WebRTC AI-to-AI, and sensor input until ADRs with explicit consent models are written.
- **Capability detection and graceful degradation.** No WebGPU → the browser tier disappears silently and Tier 1 (Ollama Granite) serves everything. The browser tier is an accelerator, never a dependency.

### ROUNDTABLE_BRIEF.md
- **Lucineer production stack context.** Live Cloudflare Worker relay, D1 memory, Vectorize with 35 Luau skills, R2 buckets, 17 build templates, and a 5-model DeepInfra brain pipeline. This is the substrate Slackwater/DCA is meant to improve, not replace.
- **Character-first design.** Lucineer is an opinionated craftsman, not a servant. The game is the spec; constraint produces thought the way chord changes produce jazz. This justifies qualitative objectives (engagement, specificity) over task-completion metrics.
- **Live gaps vs. cognition gaps.** The brief lists product gaps (no Studio playtest, no polish, no progression) separately from the cognition gaps DCA targets (no reflex compiler, no trust scoring, no temporal→vector pipeline).

### TEMPO_FIRST_ARCHITECTURE.md
- **`SharedSessionTempoMap` as single source of truth.** Fields include `baseBPM`, `swingFactor`, `rootMidiNote`, `ppq=96`, `currentTick`, `fermataActive`, `currentChordProgression`, `spatialLatticeOrigin`, `activeCountdowns`, `globalFrictionScore`, `tideLevel`, `stormIntensity`, and `activeEraOverride`.
- **Single-writer `TempoService`.** Only the core `TempoService` can update the tempo map, preventing race conditions when tide, storm, and aurora events would otherwise write concurrently.
- **T-Minus predictive prep.** Agents register countdown callbacks tied to `targetTick` and pre-position one tick early. This eliminates frame-by-frame polling and ensures player/agent lockstep.
- **Free Energy Principle friction metric.** `globalFrictionScore` measures desync across players/agents. An agent drifting >2 ticks from its target loses 20% productivity and emits dissonant MIDI notes, making misalignment perceptible.
- **Failure-mode mitigations.** Desync is handled by client-side prediction + server reconciliation with integer tick math; tempo thrashing is prevented by smooth BPM transitions over 5–10 s with hysteresis bands.

### TEMPO_IS_FIRST_CLASS.md
- **Tempo as a first-class substrate.** MIDI encodes not only *what* happens but *when* and *how*: tick, velocity, channel, tempo, groove. A build command becomes a moment — recreatable, transferable, and alive — rather than a mere coordinate.
- **Shared tempo map as coordination mechanism.** When every agent (Lucineer, Earl, player) is on the same clock, the system can measure synchronization. "In the pocket" becomes a measurable state in which the harmony governor's error signal \(\Phi\) drops toward zero.
- **Build as composition.** A castle is not a sequence of placements but a musical piece: foundation = low heavy bass, walls = mid-range rhythm, beacon = high sustained resolution note. This metaphor justifies encoding world state as temporal events.
- **Context-sensitive tempo.** Morning builds are Adagio (slow, contemplative); storm builds are Presto (urgent, chaotic); aurora events are fermata (held). The tempo adapts to the emotional and environmental state of the session.
- **Recreateability and memory.** Because MIDI captures the full moment, prior sessions can be replayed and re-embedded. This is the philosophical basis for the temporal→vector pipeline: rhythms of play become searchable knowledge.

### FABLE_MASTER_PROMPT.md
- **Five subsystem tasks with concrete acceptance criteria.** Reflex compilation (<1 ms, ≥40% hit rate after 1h), evolution engine (≥15% over static weights, <50 KB compiled policy), trust scoring (≥0.6 correlation after 100 interventions, 3-strike rollback), temporal→vector pipeline (<50 ms recall, ≥30% of Conductor decisions), LoRA pipeline (≥10% held-out gain, hot-swap into Ollama).
- **Hardware and budget constraints as design forces.** RTX 4050 6 GB VRAM, Cloudflare free tier, local inference <500 ms. Token-lean operation mandates ≥50% decisions at $0; LLM calls are reserved for novelty.
- **Safety by structural separation.** The LLM never emits executable commands directly — only validated intent phrases matched against pre-approved tables. Nemotron-Safety-3.5 filters all player-facing output; a veto engine gates every action.
- **Lucineer philosophy as meta-constraint.** The foreman leaves things unfinished, so the ML system must too: every model is provisional, every policy has gaps, every reflex carries an escape hatch. This is not decoration but a design requirement that preserves openness to future evidence.
- **Closed dynamic ML loop.** Thoughts → reflexes → evolution → trust → temporal patterns → LoRA → better thoughts. The Conductor shapes the conditions under which thoughts are generated; the thoughts become the training signal.

### superinstance-ecosystem/analysis.md
- **Four-layer meta-architecture.** Execution (lever-runner) → Memory (pincherOS / `.nail`) → Intelligence (PLATO rooms/ensigns/distillation) → Identity (git-native agents). The loop is Execute → Cache → Distill → Commit → PR → Merge → Evolve → Execute (better).
- **The `.bottle` protocol.** Typed YAML envelopes with `kind` ∈ {observation, hypothesis, experiment, result, command, config}, `source`, `references` (causal links), confidence, and tags. Designed for git-native readability and cross-repo agent communication.
- **Conservation laws as governance.** Token conservation (total spend ≤ budget), action conservation (every action produces a `.nail`/bottle entry), identity conservation (every action attributable), evolution conservation (behavior changes go through PR/review). These are design principles DCA makes executable.
- **Anti-oscillation mechanisms.** Hysteresis (minimum dwell time), rollback budgets, 10% canary before promotion, and an immutable core (Rust guard rules, conservation invariants). Without dwell, fast trust loops and slow evolution loops would fight and neither would converge.
- **Honest research posture.** The ecosystem's own audit admits 300+ repos, 69+ crates, 0 launched products. Four of five conservation-law conjectures were disproved and published. The value lies in the design patterns and evidence-backed ADRs, not in the incomplete code.

### zeroclaw-arena/integration-plan.md
- **SlackwaterActionGame mapping.** State = (channel, sender_type, urgency, time_window, prior_context_hash); actions = {respond_now, defer_30min, escalate, delegate, stay_silent}; outcome = user_satisfaction_score (0–1). This is the concrete domain translation of ZeroClaw's game protocol.
- **LLM canonicalization for semantic hash matching.** Because raw BLAKE2b embeddings lack semantic awareness, an LLM canonicalizes text before hashing (e.g., "URGENT: need help now!" and "Can you assist me quickly?" both → "urgent_help_request"). Similarity search then runs at zero serving cost.
- **Daily evolution pass.** For each context/action pair, compute the mean satisfaction over the last 7 days and apply EMA \(\alpha=0.05\) toward it, clamping to \([0.05, 0.95]\). Then recompile the policy.
- **Hierarchical clustering into discovered archetypes.** Context tile score vectors are clustered into ~8 strategy types such as `evening_casual`, `morning_urgent`, `group_social`. These are discovered, not designer-specified.
- **Fast/medium/slow routing.** Known context with confidence >0.8 → free O(1) lookup; nearest neighbor within Hamming distance ≤3 and confidence >0.6 → cheap fallback; otherwise → LLM. Projected 80% cost reduction on action selection.

### zeroclaw-arena/analysis.md
- **Non-neural learning via tile decomposition and evolution.** ZeroClaw learns bounded games by Monte Carlo rollouts, per-tile statistics, and EMA score updates with \(\alpha=0.05\). No gradient descent, no weight matrices — yet Tic-Tac-Toe reaches ~70% win rate against random play after 500 games in ~0.57 s.
- **Exploration-preserving clamp.** Every tile score is clamped to \([0.05, 0.95]\). This guarantees that no action ever reaches probability 0 or 1, preventing policy collapse onto a local optimum from which the system can never escape.
- **Compiled zero-dependency policies.** The trained tile field compiles to a pure `dict[str, str]` (~15 KB for Tic-Tac-Toe) that executes in ~0.001 ms per move with no runtime dependencies. This is the empirical basis for DCA's Gate-2 compiled-policy lookup.
- **Algorithmically discovered strategy archetypes.** Reward-conditioned evolution produced five distinct species (Explorer, Diplomat, Marksman, Climber, Prospector) without human enumeration. DCA's `evolution/archetypes.py` generalizes this to ~8 discovered context archetypes.
- **Deterministic hash embeddings for pattern matching.** BLAKE2b hashes produce 64-dim normalized vectors for fast cosine search. The trade-off is exactitude without semantic generalization — "urgent" and "critical" get unrelated vectors unless canonicalized first.

### lever-runner/integration-plan.md
- **Generalized ActionStore schema.** Actions are typed JSON specs (`shell` | `http` | `lua` | `worker_api`) with trigger pattern, confidence 0–100, success/failure counts, embedding, and tags. This abstracts Lever Runner's shell-command table into a domain-agnostic policy store.
- **Three embedding backends.** Sentence-transformers for accuracy, position-aware hash (64 dims, 44% top-1, 1 µs) for edge, pure hash as baseline. All behind a `VectorStore` protocol so SQLite+numpy is the default and LanceDB/Vectorize are optional.
- **CognitionGate cascade.** FastLoop validation → exact-match cache (BLAKE2b trigger hash → action_id) → vector search → LLM intent extraction → passthrough fallback. Target: Gate 1–2 resolve >50% of queries, Gate 1 validates in <1 ms.
- **Multi-type execution and dry-run.** A `CompositeExecutor` routes by `action_type`; `decide(..., dry_run=True)` returns the selected action without executing it. Feedback after every execution updates confidence (+1.5/−4.0).
- **Heartbeat-based auto-promote and skill packs.** Winners with 20+ successes get +10 confidence; losers with confidence <30 and 5+ failures are rewritten by GLM-5.2. Skill packs are versioned JSONL; snapshots are `tar.zst` archives with SQLite, failure cache, and metrics.

### lever-runner/analysis.md
- **Three-gate cascade with measured economics.** Gate 1 Rust fastloop (~50 µs) → Gate 2 embedding cache + trust (~200 µs–7.6 ms, 44% hit) → Gate 3 LLM intent compression (~500 ms, ~76 tokens). Combined, ~56% of queries cost zero tokens; the rest cost ~76 tokens each.
- **Structural security by output-channel narrowing.** The LLM emits only a validated 3–8 word lowercase intent phrase; the actual command is looked up from a pre-approved table by cosine similarity and trust floor (≥40). Shell injection is impossible by construction, not by policy.
- **Asymmetric trust dynamics.** New commands start at trust 50; successes add +1.5, failures subtract −4.0, capped at 100. The asymmetry forces ~3 successes to recover from one failure, favoring safety over exploitativeness.
- **Token economics versus tool-calling.** Lever Runner uses ~76 tokens per query versus ~2,000–5,000 for conventional tool-calling assistants — a 28× reduction. At 1,000 commands/day on GPT-4o the cost drops from ~$675/month to ~$0.05/month.
- **Learning without gradient descent.** The `auto_promote.py` loop promotes high-success commands and flags low-trust failures for LLM-assisted rewriting. This is reinforcement learning via database operations: the vector store accumulates experiential knowledge without weight updates.

### pincher/analysis.md
- **"Vector DB as runtime, LLM as compiler" inversion.** Pincher stores executable reflexes in sqlite-vec and dispatches known intents in <1 ms at $0; the LLM only fires for novel intents, compiling the interaction into a parameterized template that is re-embedded and stored. This is the empirical precedent for DCA's Tier-0 gate.
- **Confidence dynamics and thresholds.** Updates are asymmetric and saturating: success pushes confidence toward 1.0 as \(0.05(1-c)\), failure pulls it down as \(-0.10c\), clamped to \([0.05, 0.95]\). Three execution paths follow: Direct (>0.80), Confirm (0.55–0.80), LLM route (<0.55).
- **Deterministic fallback and security veto.** ONNX embeddings have a SHA-256 trigram/word hash fallback that never fails. A deterministic pattern-based veto engine blocks dangerous commands before execution; this is the prototype of DCA's acting gate.
- **Three-tier compute as biological metaphor.** Spinal reflex (~50 ms, $0), confirmation (~3 s, ~$0.001), cortical deliberation (~10 s, ~$0.01). Each cortex cycle teaches the spinal cord, so the system converges toward reflex-dominated execution.
- **Portable agent identity via `.nail`.** A `tar.zst` bundle carries the SQLite reflex DB, identity, and config with BLAKE3 verification. This anticipates DCA's requirement for reproducible, migratable cognitive state.

## Dissertation Sections

| # | Section | Status | Source Docs |
|---|---------|--------|-------------|
| 01 | Abstract | drafted | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE |
| 02 | Introduction | drafted | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE, pincher/analysis |
| 03 | Literature Review & Related Work | drafted | REPO_DESIGN, pincher, lever-runner, zeroclaw, superinstance-ecosystem |
| 04 | Foundational Concepts | drafted | DYNAMIC_COGNITION_ARCHITECTURE, FABLE_MASTER_PROMPT, TEMPO_IS_FIRST_CLASS |
| 05 | Formal Model | drafted | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE, FABLE_MASTER_PROMPT, Pincher, Lever Runner, ZeroClaw, SuperInstance |
| 06 | Three-Gate Cascade & Reflex Compiler | drafted | REPO_DESIGN, Pincher, Lever Runner, FABLE_MASTER_PROMPT |
| 07 | Evolution Engine & Compiled Policies | drafted | REPO_DESIGN, ZeroClaw analysis, ZeroClaw integration-plan, FABLE_MASTER_PROMPT |
| 08 | Conductor & Trust Scoring | drafted | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE, FABLE_MASTER_PROMPT, Lever Runner analysis + integration-plan, SuperInstance |
| 09 | Temporal Cognition & Vector Pipeline | drafted | DYNAMIC_COGNITION_ARCHITECTURE, TEMPO_IS_FIRST_CLASS, TEMPO_FIRST_ARCHITECTURE, REPO_DESIGN, FABLE_MASTER_PROMPT |
| 10 | Distillation & LoRA | drafted | REPO_DESIGN, FABLE_MASTER_PROMPT, MULTI_MODEL_PANEL_DISCUSSION |
| 10 | Results | pending | TBD |
| 11 | System Architecture & Browser Tier | drafted | REPO_DESIGN, MULTI_MODEL_PANEL, DEEPSEEK_BROWSER, BROWSER_NATIVE_AI_RESEARCH, ADVISORY_BRIDGE |
| 12 | Experiments & Evaluation | drafted | REPO_DESIGN, FABLE_MASTER_PROMPT, ADVISORY_BRIDGE |
| 13 | Results & Discussion | pending | TBD |
| 14 | Conclusion | pending | TBD |

### ADVISORY_BRIDGE.md (Fable's findings)
- **Updated empirical baseline.** `slackwater-cognition/` on disk is 11,533 lines and 106 test functions, not the 4,152/71 figure in `FABLE_MASTER_PROMPT.md`. The genuinely missing pieces are trust-on-Conductor, temporal→vector, LoRA, `.bottle` protocol, and the browser tier.
- **Novelty-bias confound as deepest methodological problem.** Any change produces temporary improvement. A naive trust loop will learn, correctly given its evidence, that "changing things helps" — a true but useless conclusion. Fable proposes a **sham intervention arm** (log intervention, don't apply, score anyway) so real effect = treated − sham.
- **Distillation trap signature.** Selecting training data by `quality > 0.7` where quality is scored by the system's own `QualityScorer` is a closed loop. **Rising train quality with flat held-out quality is the trap closing.**
- **Latency asymmetry as gradient.** The browser finisher predicts in <50 ms; server Granite validates in ~500 ms. The gap is not a defect but a free, continuous supervision signal: divergence loss.
- **Clamping as epistemic commitment.** `[0.05, 0.95]` clamps are not defensive programming but the mechanism of corrigibility: no action reaches probability 0 or 1, so evidence can always still arrive.
- **Multi-timescale interference.** Trust (per-intervention), evolution (daily), and LoRA (weekly) modify overlapping parameters at different periods. Without hysteresis/dwell times they oscillate and none converges.
- **Open ADRs.** Additive vs. multiplicative confidence update; whether divergence loss belongs to player or global prior; ethics of sham arm on live sessions.

## Section Drafts Log

- `sections/01_abstract.md` — drafted from REPO_DESIGN.md + DYNAMIC_COGNITION_ARCHITECTURE.md.
- `sections/02_introduction.md` — drafted from REPO_DESIGN.md + DYNAMIC_COGNITION_ARCHITECTURE.md + pincher/analysis.md.
- `sections/03_literature_review.md` — drafted from REPO_DESIGN.md + deep-dive analyses of Pincher, Lever Runner, ZeroClaw Arena, and SuperInstance ecosystem.
- `sections/04_foundational_concepts.md` — drafted from DYNAMIC_COGNITION_ARCHITECTURE.md, FABLE_MASTER_PROMPT.md, TEMPO_IS_FIRST_CLASS.md.
- `sections/05_formal_model.md` — drafted from REPO_DESIGN.md, DYNAMIC_COGNITION_ARCHITECTURE.md, FABLE_MASTER_PROMPT.md, Pincher, Lever Runner, ZeroClaw, SuperInstance ecosystem.
- `sections/06_three_gate_cascade.md` — drafted from REPO_DESIGN.md, Pincher, Lever Runner, FABLE_MASTER_PROMPT.md.
- `sections/07_evolution_engine.md` — drafted from REPO_DESIGN.md, ZeroClaw analysis, ZeroClaw integration-plan, FABLE_MASTER_PROMPT.md.
- `sections/08_conductor_trust.md` — drafted from REPO_DESIGN.md, DYNAMIC_COGNITION_ARCHITECTURE.md, FABLE_MASTER_PROMPT.md, Lever Runner analysis + integration-plan, SuperInstance ecosystem.
- `sections/09_temporal_cognition.md` — drafted from DYNAMIC_COGNITION_ARCHITECTURE.md, TEMPO_IS_FIRST_CLASS.md, TEMPO_FIRST_ARCHITECTURE.md, REPO_DESIGN.md, FABLE_MASTER_PROMPT.md.
- `sections/10_distillation_lora.md` — drafted from REPO_DESIGN.md, FABLE_MASTER_PROMPT.md, MULTI_MODEL_PANEL_DISCUSSION.md.
- `sections/11_system_architecture.md` — drafted from REPO_DESIGN.md, MULTI_MODEL_PANEL_DISCUSSION.md, DEEPSEEK_BROWSER_DESIGN.md, BROWSER_NATIVE_AI_RESEARCH.md, ADVISORY_BRIDGE.md.
