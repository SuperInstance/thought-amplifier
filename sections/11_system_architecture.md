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
