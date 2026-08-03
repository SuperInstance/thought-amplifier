# Thought Amplifier — Repository Architecture

**Status:** Design specification, v1.0
**Date:** 2026-08-03
**Target repo:** `/home/eileen/projects/thought-amplifier` (currently empty — greenfield)
**Predecessor:** `/home/eileen/projects/slackwater-cognition` (11,533 lines, 106 test functions, running)

---

## 0. Read This First: What Changed Since the Master Prompt

`FABLE_MASTER_PROMPT.md` describes a cognition codebase of "4,152 lines, 71 tests" and asks for five missing subsystems. That snapshot is stale. The actual state on disk:

| Subsystem (master prompt task) | Reality in `slackwater-cognition/` | Verdict |
|---|---|---|
| 1. Reflex compilation → `.nail` | `reflex/` — `NailCompiler`, `build_situation_signature()`, `store_in_vectorize()`, local nail persistence | **Largely built** |
| 2. Evolution engine | `evolution/` — `ScenarioSimulator`, `EvolutionRunner`, `CompiledPolicy`, `OutcomeJournal` | **Largely built** |
| 3. Trust scoring | `cascade/trust_tracker.py` exists, but it scores *cascade gates*, not *Conductor interventions* | **Partial — wrong subject** |
| 4. Temporal → vector pipeline | `temporal/` has `BeatClock`, `MidiEncoder`, `PatternMatcher`. Nothing vectorizes them. | **Encoder built, pipeline missing** |
| 5. LoRA fine-tuning pipeline | Nothing. | **Missing entirely** |
| `.bottle` protocol (stated as the required inter-component format) | `grep -rl bottle --include=*.py` → **zero hits** | **Missing entirely** |
| Browser-native tier | `viewer/server.py` is a stdlib HTTP + WebSocket server rendering files. No WebGPU, no extension, no Gemini Nano. | **Missing entirely** |

**So the honest job is not "design five subsystems from scratch."** It is: extract what has been proven, build the three genuinely missing pieces (trust-on-Conductor, temporal→vector, LoRA), install the spine that was specified and never built (`.bottle`), and add the tier the research points at (browser-native).

That is what this repo is for. `slackwater-cognition` was the laboratory. `thought-amplifier` is the instrument.

---

## 1. What This Repo Is

**Thought Amplifier is a substrate-independent dynamic cognition engine.**

A small model thinks continuously. A large model watches and adjusts the conditions under which the small model thinks. The adjustments are measured. What works becomes cheap (a reflex, a compiled policy, a trusted modification). What doesn't decays. The loop never stops.

The four-line version of the thesis:

- **Training signal** = the stream of consciousness (every thought is an example)
- **Loss function** = play quality (novelty, specificity, engagement, spatial awareness)
- **Gradient** = prompt and parameter adjustment, applied every 30 seconds
- **Model update** = continuous — reflexes compile, policies breed, trust accrues, LoRA bakes

### What it is *not*

- **Not an agent framework.** No tool-calling loop, no planner, no ReAct. The LLM never emits an executable command — it emits a 3-8 word intent phrase matched against a pre-approved table (Lever Runner's structural security property).
- **Not a RAG system.** The vector store is not retrieval-for-context. It is the **runtime**: known situations dispatch from it in <1ms at $0 (Pincher's inversion).
- **Not a fine-tuned model.** LoRA is the *fifth* and slowest loop, not the mechanism. Most improvement happens above the weights.
- **Not Slackwater-specific.** Slackwater is adapter #1.

### The core/adapter split (the single most important structural decision)

`slackwater-cognition` fused the engine with the game. Every module knows about Roblox positions, bond tiers, and build commands. That fusion is why it cannot be reused, tested in isolation, or reasoned about.

Thought Amplifier separates them at a hard boundary:

```
amplifier/          ← knows nothing about any game, ever
  ports/            ← protocol definitions the world must satisfy
adapters/
  slackwater/       ← Roblox/Lucineer implementation of those ports
  null/             ← in-memory fake, drives the whole loop in tests
```

The engine speaks only `Observation`, `Thought`, `Action`, `Outcome`. If a module in `amplifier/` imports anything that mentions a stud, a bond tier, or a Luau command, the build fails (enforced — see §9).

---

## 2. Inherited Evidence

Every architectural decision below traces to a deep-dive result, not invention. This is the master prompt's stated bar ("references evidence from the deep dives, not invented from scratch").

| Source | Extracted law | Where it lands here |
|---|---|---|
| **Pincher** (`study-pincher/`) | Vector DB is the runtime; the LLM is a *compiler* that turns interactions into reusable reflexes. Confidence: ×1.005 success, ×0.95 failure, clamped [0.05, 0.95]. | `amplifier/reflex/` — Tier 0 dispatch |
| **ZeroClaw Arena** (`study-zeroclaw-arena/`) | No neural nets for action selection. Tile-decomposed state, independent per-tile statistics, EMA α=0.05, compile to O(1) hash lookup. | `amplifier/evolution/` — policy breeding |
| **Lever Runner** (`study-lever-runner/`) | Three-gate cascade: guard (~50µs) → embedding cache (~7.6ms, 44% hit) → LLM (~500ms). 56% never reach the LLM. Asymmetric trust: +1.5 / −4.0. | `amplifier/cascade/` — and the *pattern* recurs everywhere |
| **SuperInstance** (`study-flagship/`) | `.bottle` typed envelopes for all inter-component messages. Conservation laws as hard constraints. 10% canary → human review → merge. Anti-oscillation via hysteresis + rollback budgets. | `amplifier/bottle/` — the spine |
| **Craftmind** | Write results back to the vector index after every execution; the library of refined plans grows itself. | `amplifier/memory/writeback.py` |

**The generalized three-gate pattern.** Lever Runner's cascade is not one component — it is the repo's recurring shape. Every expensive operation is preceded by two cheap checks:

| Level | Gate 1 (free) | Gate 2 (cheap) | Gate 3 (expensive) |
|---|---|---|---|
| Thinking | reflex hit (<1ms) | compiled policy lookup (O(1)) | LLM inference (~500ms) |
| Conducting | trust check on modification type | temporal pattern precedent | Conductor LLM (~10s) |
| Acting | veto engine | cooldown/novelty filter | game-side execution |

If a subsystem does not have this shape, it is wrong.

---

## 3. Repository Layout

```
thought-amplifier/
├── amplifier/                      # THE ENGINE — substrate-independent
│   ├── bottle/                     # ── the spine ──
│   │   ├── envelope.py             # Bottle[T]: typed message wrapper
│   │   ├── kinds.py                # observation|hypothesis|experiment|result|command|config
│   │   ├── bus.py                  # in-proc pub/sub; pluggable transport
│   │   └── ledger.py               # append-only JSONL of every bottle (audit + replay)
│   │
│   ├── ports/                      # ── what the world must provide ──
│   │   ├── world.py                # WorldPort: observe() -> Observation, act(Action) -> Outcome
│   │   ├── thinker.py              # ThinkerPort: think(Context) -> Thought
│   │   ├── conductor.py            # ConductorPort: analyze(list[Thought]) -> list[Modification]
│   │   ├── embedder.py             # EmbedderPort: embed(str) -> vector
│   │   └── vectors.py              # VectorPort: upsert/query/delete
│   │
│   ├── core/                       # ── domain types, zero dependencies ──
│   │   ├── types.py                # Observation, Thought, Lean, Action, Outcome, Quality
│   │   ├── clock.py                # BeatClock (ported from temporal/beat_clock.py)
│   │   └── laws.py                 # conservation invariants, runtime-enforced
│   │
│   ├── reflex/                     # ── Tier 0: <1ms, $0 ── [PORT from slackwater]
│   │   ├── signature.py            # build_situation_signature()
│   │   ├── nail.py                 # .nail record + (de)serialization
│   │   ├── compiler.py             # NailCompiler — LLM-as-compiler
│   │   ├── store.py                # SQLite + sqlite-vec; hash fallback
│   │   └── confidence.py           # +0.05×(1−c) success, −0.10×c failure, clamp[0.05,0.95]
│   │
│   ├── cascade/                    # ── three-gate dispatch ── [PORT]
│   │   ├── cascade.py              # Decision, Cascade
│   │   ├── gate_reflex.py          # Gate 1
│   │   ├── gate_policy.py          # Gate 2 (compiled policy, was gate_cache)
│   │   └── gate_llm.py             # Gate 3
│   │
│   ├── evolution/                  # ── policy breeding ── [PORT]
│   │   ├── tiles.py                # state factorization
│   │   ├── simulator.py            # Monte Carlo rollouts during idle
│   │   ├── runner.py               # evolve(): EMA α=0.05, clamp [0.05,0.95]
│   │   ├── compiler.py             # tiles -> dict[str, str], <50KB, zero-dep
│   │   └── archetypes.py           # hierarchical clustering -> 8 strategies  [NEW]
│   │
│   ├── trust/                      # ── does the Conductor help? ──  [NEW]
│   │   ├── intervention.py         # Intervention record (before/after state)
│   │   ├── scorer.py               # asymmetric +0.5/−2.0, min 10 obs
│   │   ├── canary.py               # 10% A/B, 50-thought promotion gate
│   │   ├── rollback.py             # 3-strike auto-revert, hysteresis dwell
│   │   └── self_model.py           # "which mods work in which contexts"
│   │
│   ├── temporal/                   # ── rhythm as knowledge ──
│   │   ├── midi.py                 # MidiEncoder [PORT]
│   │   ├── matcher.py              # PatternMatcher [PORT]
│   │   ├── canon.py                # MIDI -> "B8:E72:v85 → B16:I67:v60"  [NEW]
│   │   └── pipeline.py             # session -> canon -> embed -> vectors  [NEW]
│   │
│   ├── distill/                    # ── the slowest loop ──  [NEW]
│   │   ├── select.py               # quality>0.7 ∧ positive ∧ success
│   │   ├── pairs.py                # SFT pairs + DPO preference pairs
│   │   ├── train.py                # LoRA r=8-16, bs 1-4, seq 512-1024 (6GB)
│   │   ├── evaluate.py             # base vs tuned on held-out states
│   │   └── swap.py                 # hot-swap adapter into Ollama
│   │
│   ├── memory/
│   │   ├── writeback.py            # Craftmind loop — every outcome re-indexed
│   │   └── decay.py                # reflex/pattern pruning
│   │
│   └── loop.py                     # the orchestrator; wires ports, runs the cycle
│
├── adapters/
│   ├── slackwater/                 # Roblox/Lucineer: WorldPort impl, relay client
│   ├── ollama/                     # ThinkerPort via local Granite 3.1 2B
│   ├── deepinfra/                  # ConductorPort via GLM-5.2 / DeepSeek V3
│   ├── cloudflare/                 # VectorPort (Vectorize), EmbedderPort (bge-m3)
│   ├── local/                      # sqlite-vec VectorPort, hash EmbedderPort (offline)
│   └── null/                       # deterministic fakes — full loop, no network
│
├── browser/                        # ── the new tier ──  [NEW]
│   ├── viewer/                     # thought stream UI (CodeMirror 6 + SSE)
│   ├── finisher/                   # WebGPU Tier-0 thinker (WebLLM, Phi-3-mini)
│   ├── extension/                  # MV3: content script + service worker
│   └── protocol/                   # anchor-pulse packet schema (shared w/ server)
│
├── ops/
│   ├── bench/                      # latency gates enforced in CI
│   ├── replay/                     # rerun a bottle ledger deterministically
│   └── migrate/                    # slackwater-cognition -> thought-amplifier
│
├── tests/
│   ├── unit/                       # per-module
│   ├── contract/                   # every adapter must pass the port's contract suite
│   ├── loop/                       # full cycle on null adapter, deterministic
│   └── laws/                       # conservation invariants
│
└── docs/
    ├── REPO_DESIGN.md              # this file
    ├── DECISIONS/                  # ADRs, numbered, append-only
    └── PORTING.md                  # what came from where, and what changed
```

---

## 4. The Spine: `.bottle`

The master prompt requires `.bottle` for all inter-component communication. It was never built. It is the first thing to build, because everything else hangs off it.

A bottle is a typed envelope with provenance. Six kinds, from SuperInstance:

```python
Kind = Literal["observation", "hypothesis", "experiment", "result", "command", "config"]

@dataclass(frozen=True)
class Bottle(Generic[T]):
    kind: Kind
    payload: T
    id: str                     # uuid7 — sortable by time
    caused_by: str | None       # id of the bottle that produced this one
    source: str                 # "thinker.granite" | "conductor.glm" | "trust.canary"
    ts: float
    schema: str                 # "thought/v1" — payload contract version
    meta: dict[str, str]        # session_id, beat, prompt_version, trace_id
```

Three properties earn its keep:

1. **`caused_by` makes the loop a DAG, not a mystery.** Every thought points at the observation that triggered it; every modification points at the analysis that proposed it; every outcome points at the action. Ask "why did the system do that?" and walk the chain. This is what makes 100% interpretability (Task 2's acceptance criterion) achievable across *all* subsystems rather than just the policy.

2. **The ledger is the replay tape.** `bottle/ledger.py` appends every bottle to JSONL. `ops/replay/` reruns a session against a null adapter and asserts identical outputs. Regression testing a stochastic system is otherwise impossible — this is how you tell "the Conductor got better" from "the dice rolled differently."

3. **`schema` version makes the boundary honest.** Payload contracts change. A version string on the envelope means a v2 consumer can reject or upgrade a v1 payload instead of silently misreading it. (The stale `worker-configuration.d.ts` in `lucineer-worker` is exactly the failure this prevents.)

The bus is in-process pub/sub by default. The transport is pluggable so the browser tier can join over SSE without any component knowing it did.

---

## 5. The Five Subsystems

### 5.1 Reflex Compiler — Tier 0 *(port + harden)*

`slackwater-cognition/reflex/` already implements situation signatures, LLM compilation, and Vectorize storage. Port it behind `ports/vectors.py` so it stops importing Cloudflare directly, and add what's missing:

- **Confidence model.** The prompt specifies `+0.05×(1−c)` / `−0.10×c`, clamp [0.05, 0.95] — asymmetric, and *saturating* (gains shrink as confidence rises, losses shrink as it falls). Pincher's multiplicative ×1.005/×0.95 is the alternate form; use the additive one specified, and record which in an ADR.
- **Hash fallback.** No ONNX → deterministic feature hash over the situation signature. Degrades precision, never availability. This is a hard acceptance criterion and it is the difference between a demo and an instrument.
- **Escape hatch.** Every reflex carries `max_consecutive_uses`. After N identical dispatches, force one Gate-3 call even on a confident hit. Without this, a high-confidence wrong reflex is a permanent blind spot — the system stops sampling the very evidence that would correct it.

### 5.2 Evolution Engine *(port + finish)*

`evolution/` has the simulator, runner, and compiler. Missing: **`archetypes.py`** — hierarchical clustering of context tiles into ~8 strategy archetypes ("morning_builder", "evening_explorer"), *discovered not designed*.

Keep ZeroClaw's `evolve()` exactly: empirical rate → EMA α=0.05 → clamp [0.05, 0.95]. The clamp is not cosmetic; it guarantees every action retains ≥5% probability, which keeps exploration alive and prevents the policy from collapsing onto a local optimum it can never escape.

Compiled policy is a plain `dict[str, str]`, <50KB, zero imports, hot-swapped at heartbeat.

### 5.3 Trust Scoring — *the real gap*

`cascade/trust_tracker.py` scores cascade gates. Nothing scores **Conductor interventions**. The Conductor has been modifying prompts and parameters every 30 seconds with no feedback on whether any of it helped. It is operating blind, exactly as the master prompt says.

```python
@dataclass(frozen=True)
class Intervention:
    kind: Literal["prompt", "parameter", "policy"]
    target: str                     # "system_prompt" | "temperature" | "curiosity_weight"
    before: Any
    after: Any
    context_key: str                # tile-hash of the situation it was applied in
    applied_at: float
    quality_before: Quality         # trailing window mean
    quality_after: Quality | None   # filled in after the measurement window
```

Four mechanisms, all from the deep dives:

- **Asymmetric trust**, tuned slower than Lever Runner's (+0.5 / −2.0, minimum 10 observations before trust moves at all). Cognitive modifications are noisier than command routing; learning fast here means learning noise.
- **Novelty-bias control.** *Any* change produces temporary improvement — the placebo. Measure against a **sham intervention arm**: periodically log an intervention, don't apply it, and score the window anyway. Real effect = treated − sham, not treated − before. Without this the Conductor will confidently learn that changing things helps, which is the single most likely way this whole system fools itself.
- **Canary.** 10% of thoughts, 50-thought promotion gate.
- **Rollback + hysteresis.** 3 consecutive quality decreases → auto-revert to the previous prompt version. Minimum dwell time before any target can be modified again — the SuperInstance anti-oscillation pattern. Without dwell, trust scoring and evolution will fight each other at their respective periods and neither will converge.

The **self-model** is a table keyed by `(modification_kind, context_archetype)` — this is where the archetypes from §5.2 pay for themselves twice.

### 5.4 Temporal → Vector *(encoder exists, pipeline missing)*

`MidiEncoder` produces beat patterns that are never stored. The pipeline:

```
session ──MidiEncoder──> events ──canon──> "B8:E72:v85 → B16:I67:v60 → B4:W:v30"
                                              │
                                    EmbedderPort (bge-m3)
                                              │
                                    VectorPort.upsert(meta={session,player,quality,bond_tier})
```

Canonicalization must be **deterministic and lossy in a stable way** — same session always yields the same string, therefore the same vector (an explicit acceptance criterion). Quantize velocity to buckets and beats to a fixed grid *before* stringifying; do not embed floats.

Recall path: the Conductor queries "has this rhythm worked before?" during its 30s cycle, and the answer becomes a Gate-2 check before it spends a Gate-3 LLM call. Target: temporal precedent informs ≥30% of modification decisions.

### 5.5 Distillation (LoRA) — *entirely missing*

The slowest loop and the least important — listed last deliberately. If the first four work, this is a compounding bonus; if they don't, this cannot rescue them.

- **Select:** `quality > 0.7 ∧ conductor_commentary positive ∧ action succeeded`.
- **Pairs:** SFT `(game_state, prompt_version) → (thought, lean, action)`. DPO preference pairs from matched high/low quality thoughts in *similar states* — this is what targets specificity and spatial_awareness rather than generic fluency.
- **Train:** LoRA r=8–16, batch 1–4, seq 512–1024. Fits 6GB. Trigger every ~1000 qualifying thoughts (≈weekly).
- **Evaluate before promote:** base vs. tuned on held-out states, scored by the same `QualityScorer`. **Promotion requires beating base by ≥10%** — otherwise discard the adapter. A fine-tune that isn't measured is a regression waiting to ship.
- **Hot-swap** into Ollama without dropping the inference loop.

**The distillation trap.** Training on thoughts the system already rates highly is a self-reinforcing loop that will converge on the system's existing biases and call it progress. Mitigations, all required: hold out a fixed evaluation set *never* used for training; keep the DPO negatives sampled from genuinely low-quality thoughts rather than merely-lower-quality ones; and gate promotion on the held-out set alone. If quality rises on training data and not on held-out, that is the trap closing, and the adapter must be discarded.

---

## 6. The Browser Tier

From `MULTI_MODEL_PANEL_DISCUSSION.md`, where Seed-2.0-mini, Qwen3-Max, and Hermes-3-405B independently converged on the same architecture. Three convergence points are load-bearing:

1. **Hybrid split is correct** — browser for fast reactive thought, server for deep strategy.
2. **The Conductor stays server-side** — all three agreed; it needs full context and a large model.
3. **Latency asymmetry is an asset.** The browser *predicts*; the server *validates*. The gap between them is not a defect to minimize — it is the teaching signal.

That last point is the genuinely novel one, and it defines the tier:

```
Tier B (browser, <50ms)   Phi-3-mini / Qwen2.5-1.5B via WebLLM+WebGPU
Tier 0 (reflex,  <1ms)    .nail dispatch
Tier 1 (local,  ~500ms)   Granite 3.1 2B via Ollama          ← ground truth
Tier 2 (cloud,     ~30s)  GLM-5.2 Conductor
```

**Divergence loss** = difference between the browser's predicted continuation and Tier 1's actual output. It is logged as a `result` bottle and consumed by the Conductor. Start at prompt-level learning (adjust the browser's priming from divergence patterns); escalate to weight-level only after the prompt-level loop demonstrably converges. All three panelists wanted in-browser SGD; the philosophical panelist's caution is the right default.

**Context anchor pulses** (ranked #1 by novelty × feasibility in the panel): every 0.5–1s the server pushes a compact packet — last 8 tokens, game state, beat position, quality signals. The browser finisher grounds completions in it and therefore cannot hallucinate rule-breaking continuations. Schema lives in `browser/protocol/`, shared by both sides, versioned via the bottle `schema` field.

**Capability detection is mandatory.** No WebGPU → the browser tier disappears silently and Tier 1 serves everything. The tier is an accelerator, never a dependency.

**Deliberately deferred:** DOM Resonance Questing, cross-tab NPCs, WebRTC AI-to-AI, sensor input. All three panelists flagged consent and privacy concerns on exactly these, and the philosophical panelist's framing is correct — an AI with page access and mic permission is a different product with a different risk surface. They are not in v1. When they are proposed, they arrive as ADRs with a consent model attached, or they don't arrive.

---

## 7. Conservation Laws

SuperInstance treats these as hard constraints. Here they are executable — `amplifier/core/laws.py`, asserted in the loop and tested in `tests/laws/`.

| Law | Statement | Enforcement |
|---|---|---|
| **Token** | Every LLM call is debited from a session budget. Exhausted budget → cascade degrades to Gate 1/2 only, never blocks. | `TokenLedger.spend()` raises `BudgetExceeded`; loop catches and downshifts |
| **Action** | No action reaches the world without a corresponding logged bottle. | `WorldPort.act()` requires a `Bottle[Command]`; null adapter asserts 1:1 |
| **Identity** | Every artifact (thought, reflex, policy, adapter) carries the prompt/policy/model version that produced it. | `meta` fields required by schema validation |
| **Evolution** | No parameter changes without a recorded before-state and a measurement window. | `trust.intervention` is the only path that may mutate config |

The token law is the one with teeth. The master prompt's budget constraint — ≥50% of decisions at $0 — is not an aspiration to check at the end of the month. It is a runtime invariant with a counter, surfaced in `ops/bench/`, and CI fails if the null-adapter loop drops below the threshold.

---

## 8. Degradation Ladder

The master prompt: *"the system degrades gracefully at every level."* Explicitly:

| Component | Preferred | Fallback 1 | Fallback 2 | Never |
|---|---|---|---|---|
| Embeddings | bge-m3 (Workers AI) | local sentence-transformers | deterministic feature hash | fail the request |
| Vectors | Vectorize | sqlite-vec local | in-memory linear scan | fail the request |
| Tier-0 think | WebGPU finisher | — | skip to Tier 1 | fail |
| Tier-1 think | Ollama Granite | DeepInfra small model | compiled policy only (no thought text) | fail |
| Conductor | GLM-5.2 | DeepSeek V3 | `heuristic_analysis()` (already exists) | fail |
| Reflex store | sqlite-vec | hash bucket | disabled, all traffic to Gate 3 | fail |

Every row's fallback is exercised in CI by adapter substitution. A fallback that is never tested is not a fallback.

---

## 9. Testing Strategy

Four layers. The middle two are what make this repo different from its predecessor.

1. **Unit** — per module, pure functions preferred. `signature.py`, `confidence.py`, `canon.py` are all deterministic and trivially testable.

2. **Contract** — one suite per port; **every adapter must pass it**. `tests/contract/test_vector_port.py` runs identically against Vectorize, sqlite-vec, and in-memory. This is what makes the degradation ladder real rather than documented.

3. **Loop** — the full cycle against `adapters/null/` with a seeded RNG. Deterministic: same seed, same bottle ledger, byte-for-byte. This is the regression test for a stochastic system, and it is only possible because of the bottle ledger.

4. **Laws** — conservation invariants as property tests. Run the loop 1000 cycles; assert no action without a command bottle, no config mutation outside an intervention, token spend ≤ budget.

**Boundary enforcement:** an import-linter rule fails the build if `amplifier/**` imports from `adapters/**` or matches game vocabulary. The core/adapter split is the repo's central claim; a claim not enforced by CI is a comment.

**Latency gates in CI** (`ops/bench/`), from the master prompt's stated targets:

| Gate | Budget |
|---|---|
| Reflex check, 10k reflexes | <1 ms |
| Vector similarity search | <50 ms |
| Tier-1 inference | <500 ms |
| Reflex hit rate after 1h simulated play | ≥40% |
| Decisions served at $0 | ≥50% |

---

## 10. Migration Path

Not a rewrite. Five ordered steps, each independently shippable:

1. **Bottle + ports + null adapter + loop skeleton.** No behavior, full spine. Prove the loop runs on fakes.
2. **Port `reflex/`, `cascade/`, `evolution/`, `temporal/`** behind ports. Mechanical; their logic is sound. Contract tests come with them.
3. **Build `trust/`.** The Conductor stops flying blind. Highest value per line in the repo.
4. **Build `temporal/pipeline.py`.** Rhythm becomes queryable; feeds Gate 2 of the conducting cascade.
5. **Build `distill/`.** Last, because it is slowest and most dangerous.

The browser tier proceeds in parallel after step 1 — it only needs the bottle schema and SSE transport.

`slackwater-cognition` stays running throughout. It is the source of the journals that make step 3 measurable. Retire it only when the null-adapter loop and the Slackwater adapter both pass contract tests.

---

## 11. Acceptance Criteria

The repo is **done enough to be real** when:

- [ ] `pytest` green; loop tests deterministic across 3 consecutive seeded runs
- [ ] Every port has ≥2 adapters passing the same contract suite
- [ ] Import-linter proves `amplifier/` has zero game-specific imports
- [ ] Full loop runs offline: hash embedder + sqlite-vec + Ollama, no network
- [ ] Bottle ledger replays a recorded session to identical output
- [ ] All five latency gates pass in CI
- [ ] Conservation law property tests pass over 1000 cycles

The repo is **excellent** when:

- [ ] Trust scores correlate ≥0.6 with real quality improvement after 100 interventions — *measured against the sham arm*
- [ ] Evolved policy beats hand-tuned weights by ≥15%
- [ ] ≥40% of thoughts served by reflexes after 1h
- [ ] Archetype clustering produces human-recognizable strategies
- [ ] A LoRA adapter is promoted on held-out gains, or correctly rejected

---

## 12. What Is Deliberately Unfinished

The master prompt's quality bar: *"the character of Lucineer is preserved throughout — even the ML system follows this philosophy: every model is unfinished, every policy has gaps, every reflex has an escape hatch."*

Taken literally, as design constraints:

- **Every reflex has `max_consecutive_uses`.** Confidence never becomes certainty. The system is forced to re-check its own most-trusted conclusions.
- **Every policy clamps at [0.05, 0.95].** No action ever reaches probability 0 or 1. There is always a gap.
- **Every LoRA adapter is provisional** — evaluated against held-out data, discarded on failure to beat base. No adapter is ever final.
- **Every Conductor modification is revertible** within 3 strikes, and the previous version is retained.
- **The archetypes are discovered, not enumerated.** The repo ships with zero hardcoded strategies.

This is not decoration. A system that cannot revise its own conclusions is a system that has stopped learning, and every one of these gaps is a place where evidence can still get in.

The foreman leaves the cleats off so you have a reason to pick up the hammer. The engine leaves 5% probability on every action so it has a reason to keep looking.

---

## Appendix A: Open Questions for the First ADRs

1. Additive (`+0.05×(1−c)`) vs. multiplicative (`×1.005`) confidence — the master prompt and Pincher disagree. Pick one, measure, record.
2. Is the sham-intervention arm ethical to run against a live player session, or must it be confined to replay? (It withholds a possibly-beneficial adjustment.)
3. Does the browser finisher's divergence loss belong to the *player* (personalization) or the *system* (global prior)? The panel split on this; it is a privacy decision before it is a technical one.
4. Bottle ledger retention — the persistence layer's guano decay model (`PERSISTENCE_LAYER_DESIGN.md`) applies directly. Reuse those tiers rather than inventing new ones.
5. What is the minimum viable Slackwater adapter? Possibly narrower than the current game surface.

---

*Design synthesized from: `FABLE_MASTER_PROMPT.md`, `DYNAMIC_COGNITION_ARCHITECTURE.md`, `BROWSER_NATIVE_AI_RESEARCH.md`, `DEEPSEEK_BROWSER_DESIGN.md`, `MULTI_MODEL_PANEL_DISCUSSION.md`, deep-dive repos `study-pincher`, `study-zeroclaw-arena`, `study-lever-runner`, `study-flagship`, and direct inspection of `slackwater-cognition/` (11,533 lines, 106 tests) on 2026-08-03.*
