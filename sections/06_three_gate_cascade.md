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
