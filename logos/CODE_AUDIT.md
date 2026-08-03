# CODE AUDIT — Slackwater Cognition System

**Date:** 2026-08-03  
**Auditor:** LOGOS (OpenCode DeepSeek V4)  
**Scope:** `local_thinker/thinker.py`, `conductor/conductor.py`, and all transitive imports  
**Files audited:** 6 files, ~2,236 lines

---

## EXECUTIVE SUMMARY

The cognition system is a two-process architecture: the **Thinker** runs a fast observation→thought→action loop using Ollama (local) with GLM API fallback, while the **Conductor** runs a slower meta-analysis loop that reads the thought journal and issues directives (prompt changes, parameter deltas, policy weight shifts) back to the Thinker.

The core loop works. The issues are concentrated in three areas: **(1) file I/O races between the Thinker and Conductor** since they share files without locking, **(2) unbounded data growth** across the journal, context construction, and in-memory state, and **(3) brittle error handling** that silently degrades rather than surfacing failures.

**Bug count by severity:**
- 🔴 Critical: 4 (data race on directives, memory blowup on journal reads, context window overflow, curl JSON crash)
- 🟡 Moderate: 9 (missing error paths, unbounded sets, TOCTOU races, division-by-zero)
- 🔵 Minor: 6 (inconsistent error handling, naming, missing caps, stylistic)

---

## 🔴 CRITICAL BUGS

### C-1: Race condition on `conductor_directives.json` (thinker.py / conductor.py)

**Files:** `thinker.py:72-86` (reader), `conductor.py:365-380` (writer)

The Thinker reads `conductor_directives.json` every beat via `load_directives()`. The Conductor writes it via `apply_decisions()`. There is no file locking, atomic write, or signal between them.

```python
# conductor.py — WRITER (line 379)
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(directives, f, indent=2, ensure_ascii=False)

# thinker.py — READER (line 82)
text = DIRECTIVES_PATH.read_text(encoding="utf-8")
return json.loads(text)
```

**Impact:** If the Thinker reads while the Conductor is writing, it gets a truncated or partially-written JSON file. `json.loads` raises `JSONDecodeError`, the Thinker returns `None`, and the directive is silently lost. Over many cycles, this degrades the feedback loop.

**Fix:** Write to a temp file then atomic rename (`os.rename`), or use `fcntl.flock` for advisory locking, or add a `.lock` sentinel file.

---

### C-2: `read_recent_thoughts` reads entire journal into memory every call (journal.py)

**File:** `journal.py:175-196`

Every call to `read_recent_thoughts(n)` reads the **entire** session JSONL file line-by-line into a list, then slices the last `n` entries. The file grows without bound. For a session running 24 hours at 5s/beat = 17,280 entries.

```python
def read_recent_thoughts(n: int = 30) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:              # ← reads ALL lines
            ...
            entries.append(json.loads(line))
    return entries[-n:]              # ← only needs last N
```

**Impact:** Memory usage scales O(total_entries). For a long-running process, this is a slow memory leak masquerading as a feature. At 17K entries × ~2KB each = ~34MB, then GC pressure every cycle.

**Fix:** Use `seek()` from the end or read in reverse-chunk mode, or rotate journal files by session hour. Alternatively, maintain an in-memory ring buffer and only read from disk when the process restarts.

---

### C-3: Unbounded context window in `build_context` (thinker.py)

**File:** `thinker.py:559-597`

`build_context` constructs the full LLM context each beat. The system prompt is loaded from a versioned `.md` file that grows with each Conductor directive (the `PromptUpdater` *appends* directives, never removes them). On top of that, game state, policy stats, and recent thought texts are appended.

```python
def build_context(game_state, action_policy, recent_thought_texts):
    lines.append(f"## Recent Thoughts (last {len(recent_thought_texts)})")
    for i, t in enumerate(recent_thought_texts[-5:], 1):
        short = t[:120] + ("..." if len(t) > 120 else "")
        lines.append(f"{i}. {short}")
    ...
    return "\n".join(lines)
```

**Impact:**
1. The system prompt (`system_prompt`) grows monotonically — each Conductor cycle appends a directive block. After 100 cycles, it could easily exceed the model's context window (most small models support 2K–8K tokens).
2. There is no token counting, byte limit, or truncation anywhere in the prompt→context→LLM pipeline.
3. The model silently truncates input beyond its context window. The Thinker's latest directives and important context get dropped, causing it to revert to base behavior without any indication.

**Fix:** (a) Cap the system prompt at a max token count by trimming oldest directive blocks first. (b) Add a token counter (even `len(text) / 4` as a rough estimate) and truncate context before calling the LLM. (c) Rotate prompt versions — don't append infinitely.

---

### C-4: `parse_llm_output` `raw.index` can crash on partial markdown (thinker.py)

**File:** `thinker.py:496-498`

```python
if "```json" in raw:
    start = raw.index("```json") + 7
    end = raw.index("```", start) if "```" in raw[start:] else len(raw)
    raw = raw[start:end].strip()
elif "```" in raw:                                # line 499
    start = raw.index("```") + 3
    end = raw.index("```", start) if "```" in raw[start:] else len(raw)
    raw = raw[start:end].strip()
```

On line 499, `raw.index("```")` is guarded by `"```" in raw`. But on line 501, `raw.index("```" , start)` searches from `start` in the original `raw`. These two `raw.index` calls could fail:
- If the LLM outputs nested or unmatched backticks (e.g., ````json\n{...}\n\`\`\`some text` ``), the second `raw.index("```", start)` finds a different closing delimiter than expected.
- If `raw.index("```", start)` raises `ValueError`, the `if "```" in raw[start:]` guard handles it — but the pattern is fragile.

**Impact:** When the model outputs unusual markdown, `parse_llm_output` raises an uncaught `ValueError`. This propagates through `run_think_loop` and crashes the entire thinker process at beat 754-756 (KeyboardInterrupt only). Since `parse_llm_output` is called inside the main `while True:` loop (line 706), an uncaught exception would kill the thinker.

**Fix:** Wrap the index operations in try/except, or use `str.find()` which returns -1 on failure instead of raising.

---

## 🟡 MODERATE BUGS

### M-1: `_visited_areas` set grows without bound (action_policy.py)

**File:** `action_policy.py:51`

```python
self._visited_areas: set[tuple[int, int]] = set()
```

A new cell is added every time the Thinker enters an unexplored grid cell. In a long-running exploration session over a large world, this set grows to tens of thousands of entries. No eviction policy.

**Fix:** Cap at ~10,000 entries with FIFO or LRU eviction, or use a bloom filter for "has this area been visited recently?"

---

### M-2: Journal files grow without rotation (journal.py)

**Files:** `journal.py:156-158`, `journal.py:169-170`

Both `session_*.jsonl` and `thoughts.md` grow without bound. A long-running process fills disk and makes the markdown file unreadably large.

**Fix:** Rotate JSONL by session hour. Truncate markdown to last N entries or rotate daily.

---

### M-3: `execute_action` polling loop blocks with no timeout guard (thinker.py)

**File:** `thinker.py:332-362`

```python
for _ in range(10):  # Poll up to 10 times
    time.sleep(1)
    job = get_job(job_id)
```

Each `get_job` call makes a curl subprocess with a 10s timeout. If the network is slow, each call takes 10s. 10 loops × 10s = 100s of blocking. During this time, the thinker can't process new game state or directives.

**Fix:** Add a cumulative timeout (e.g., `deadline = time.time() + 30`), or use non-blocking polling.

---

### M-4: `_session_file` TOCTOU race (journal.py)

**File:** `journal.py:31-39`

```python
def _session_file():
    sessions = sorted(JOURNAL_DIR.glob("session_*.jsonl"))
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    expected = JOURNAL_DIR / f"session_{today}.jsonl"
    if not sessions or sessions[-1].stem != f"session_{today}":
        return expected
    return sessions[-1]
```

Between the `glob()` call and the `open()` in `write_thought`, another process (or the Conductor) could create the file. The writer then opens it without issue, but the `sessions[-1]` result could be stale.

**Fix:** Use `open(expected, "a")` directly — if the file doesn't exist, it'll be created. Remove the glob-based session detection.

---

### M-5: Division by zero in `detect_pattern` (conductor.py)

**File:** `conductor.py:242-244`

```python
half = len(novelty_scores) // 2
first_half = sum(novelty_scores[:half]) / half        # half could be 0
second_half = sum(novelty_scores[half:]) / (len(novelty_scores) - half)
```

If `half == 0` (which happens when `len(novelty_scores) < 2`), this is a `ZeroDivisionError`. The `if len(novelty_scores) >= 6:` guard on line 241 prevents the most common case, but if scores list is mutated between lines 241 and 242 (though unlikely), or if the scores list is empty after filtering...

**Impact:** Low probability in current code (guarded by `>= 6`), but fragile. Any refactor that changes the guard could hit this.

**Fix:** Add explicit `if half == 0: return "balanced"` guard, or use `max(half, 1)`.

---

### M-6: `execute_action` doesn't handle `jobId` being a dict or unexpected type (thinker.py)

**File:** `thinker.py:335`

```python
if "jobId" in result and result["jobId"]:
```

If the Worker API returns `"jobId": {"id": "abc"}` (nested object) instead of a string, this passes the truthiness check but then `get_job(job_id)` gets a dict instead of a string. The curl URL would be malformed.

**Fix:** Validate `isinstance(result["jobId"], str)` before using it as a job ID.

---

### M-7: `apply_decisions` writes to config without atomicity (conductor.py)

**File:** `conductor.py:379-380`

```python
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(directives, f, indent=2, ensure_ascii=False)
```

If the process crashes mid-write, the file is corrupted. Combined with C-1 (the Thinker reads it concurrently), this is doubly dangerous.

**Fix:** Write to temp file, then `os.replace(temp, config_path)` for atomic replacement.

---

### M-8: Module-level mutable globals (`TEMPERATURE`, `TOP_P`, `MAX_TOKENS`) (thinker.py)

**File:** `thinker.py:183-185`

```python
TEMPERATURE = 0.85
TOP_P = 0.9
MAX_TOKENS = 300
```

These are mutated by `apply_directives` via `global` (line 106). If the module is ever imported in a threaded context or if async LLM calls are added later, these become shared mutable state with no synchronization.

**Fix:** Encapsulate in a `ThinkerConfig` dataclass or a simple config dict passed explicitly.

---

### M-9: `call_conductor_llm` has no try/except (conductor.py)

**File:** `conductor.py:67-103`

If `_curl_post` raises (e.g., `subprocess.CalledProcessError` if `check=True` is later added, or `MemoryError`), the exception propagates up through `analyze_thoughts` → `run_conductor_loop` and crashes the Conductor.

**Fix:** Wrap the entire LLM call in try/except, return a structured error dict.

---

## 🔵 MINOR BUGS

### m-1: `_curl_post` error handling inconsistent between thinker and conductor

Thinker's `_curl_post` catches `subprocess.TimeoutExpired`, `json.JSONDecodeError`, and generic `Exception`. Conductor's version only catches generic `Exception` (line 61), so a timeout or bad JSON would go to the generic handler with less context.

**Fix:** Align error handling in both modules.

---

### m-2: `load_system_prompt` silently creates v1_base.md (thinker.py)

**File:** `thinker.py:538-549`

If the prompts directory is somehow empty, the thinker writes a default prompt file. This is a good fallback, but the write can fail silently if the directory is read-only (the `Path.mkdir` above handles directory creation, but `write_text` is unguarded).

---

### m-3: `quality_scorer._history` uncapped append (quality_scorer.py)

**File:** `quality_scorer.py:106-108`

```python
self._history.append(batch_summary)
if len(self._history) > self._max_history:
    self._history = self._history[-self._max_history:]
```

This creates a new list on every trim operation. For 200 entries it's negligible, but the pattern is fragile if `_max_history` is raised.

**Fix:** Use `collections.deque(maxlen=self._max_history)`.

---

### m-4: `_synthetic_state` uses `random` without seeding (thinker.py)

Each call generates different synthetic state. This makes testing non-deterministic. Not a bug per se, but makes the system harder to test.

**Fix:** Seed with a session constant in dev mode.

---

### m-5: Commentary file path hardcoded with no directory creation (conductor.py)

**File:** `conductor.py:387-390`

```python
commentary_path = REPO_ROOT / "journals" / "thoughts" / "conductor_commentary.md"
with open(commentary_path, "a", encoding="utf-8") as f:
```

The `journals/thoughts/` directory is created by the Thinker's journal writer, but if the Conductor runs before the Thinker, the directory won't exist and this will crash.

**Fix:** Add `commentary_path.parent.mkdir(parents=True, exist_ok=True)`.

---

### m-6: `apply_directives` `global` statement is fragile (thinker.py)

**File:** `thinker.py:106`

```python
def apply_directives(...):
    global TEMPERATURE, TOP_P, MAX_TOKENS
```

If the module-level constants are renamed, the global statement becomes silently wrong (it would create local variables shadowing the globals instead of mutating them).

**Fix:** Use a config object as noted in M-8.

---

## CONTEXT WINDOW OVERFLOW ANALYSIS

The context window problem is a system-level concern that spans both modules:

| Component | Growth pattern | Cap? | Risk |
|-----------|---------------|------|------|
| `system_prompt` | Appends directive blocks each Conductor cycle | ❌ | Grows indefinitely; exceeds model context window within hours |
| `build_context` (game state) | Fixed fields | ✅ | Low |
| `build_context` (recent thoughts) | Last 5, each ≤120 chars | ✅ | Low |
| `recent_thought_texts(10)` | Last 10 full thought texts (no truncation) | ❌ | Each thought can be 300 chars → ~3K chars |
| `call_llm` messages | system_prompt + context | ❌ | **Combined risk: unbounded** |
| `CONDUCTOR_SYSTEM_PROMPT` | Static (1.6KB) | ✅ | Low |
| `analyze_thoughts` context | 30 thoughts × 100 chars each | ⚠️ | ~3KB, manageable but grows with THOUGHTS_PER_ANALYSIS |
| `conductor_decisions.jsonl` | Appends each cycle | ❌ | Disk only, not in context window |
| `session_*.jsonl` | Appends each beat | ❌ | Causes C-2 memory issue |
| `thoughts.md` | Appends each beat | ❌ | Disk only |
| `_action_history` | Capped at 50 | ✅ | Low |
| `_visited_areas` | Grows with exploration | ❌ | See M-1 |

**Primary risk:** The combination of unbounded `system_prompt` + unbounded `recent_thought_texts` in `call_llm` will exceed the model's context window (typically 2K–32K tokens depending on model). When this happens, the model silently drops tokens from the **beginning** of the prompt — which is where the system prompt lives. The Thinker loses its identity and instructions without any error or warning.

---

## RACE CONDITION ANALYSIS

| Shared resource | Thinker role | Conductor role | Lock? | Risk |
|----------------|-------------|---------------|-------|------|
| `conductor_directives.json` | Reads every beat | Writes every cycle | ❌ | **C-1: torn reads** |
| `config/prompts/v*.md` | Reads at startup + directive check | Writes new versions | ⚠️ | Thinker reads-only after file is written; safe if atomic write |
| `journals/thoughts/` | Writes JSONL + MD | Reads JSONL, writes MD | ❌ | Conductor reads may see partial lines |
| `TEMPERATURE/TOP_P/MAX_TOKENS` | Reads in `_try_ollama/_try_glm` | Writes via config file | ❌ | See M-8 |
| `QualityScorer._history` | — | Writes in `score_batch` | ❌ | Single-threaded currently, fragile |
| `DirectiveTracker._applied_*` | Read/write every beat | — | ✅ | Single-threaded |

**Primary risk:** C-1 (directives file). A torn read means a directive cycle is silently lost. Over time, the Conductor's feedback accumulates error — it thinks it adjusted the Thinker but the adjustment didn't apply. The next cycle compounds the error because the Conductor doesn't verify that its previous directives were applied.

---

## ERROR HANDLING GAPS

| Location | Missing handler | Consequence |
|----------|----------------|-------------|
| `thinker.py:706` — `parse_llm_output` | `ValueError` from `raw.index` on malformed markdown | **C-4: Thinker crash** |
| `thinker.py:332-362` — polling loop | No cumulative timeout parameter | Blocks up to 100s (M-3) |
| `conductor.py:60-62` — `_curl_post` | Only generic Exception, no Timeout/JSON error | Less diagnostic info (m-1) |
| `conductor.py:379` — `apply_decisions` | No try/except on file write | Conductor crash if dir read-only |
| `conductor.py:387-390` — commentary write | No `mkdir` guard | Crash if Thinker hasn't run yet (m-5) |
| `journal.py:183-194` — `read_recent_thoughts` | `json.JSONDecodeError` on corrupted lines | Silent skip (OK for corruption, but mask data loss) |
| `thinker.py:484-523` — `parse_llm_output` | No handling for `intensity` out of [0,1] range | LLM can produce values outside the expected range |

---

## RECOMMENDED FIX ORDER

| Priority | Bug | Effort | Fix |
|----------|-----|--------|-----|
| **P0** | C-3: Context window overflow | Medium | Add token counting + truncation in `call_llm`; cap system prompt |
| **P0** | C-2: Journal memory blowup | Small | Read journal in reverse or use ring buffer |
| **P0** | C-1: Directives race condition | Small | Atomic write via temp file + rename |
| **P0** | C-4: `parse_llm_output` crash | Small | Use `str.find()` instead of `str.index()` |
| P1 | M-2: Journal rotation | Medium | Rotate by session hour |
| P1 | M-1: `_visited_areas` cap | Small | Add max size with eviction |
| P1 | M-8: Module-level globals | Small | Encapsulate in config dataclass |
| P1 | M-3: Polling timeout | Small | Add cumulative deadline |
| P2 | M-4: TOCTOU in session file | Small | Remove glob, use direct open |
| P2 | M-5: Division by zero guard | Trivial | Add max(half, 1) |
| P2 | M-6: `jobId` type validation | Trivial | Add isinstance check |
| P2 | M-7: Atomic config write | Small | Temp file + rename |
| P2 | M-9: Conductor LLM try/except | Small | Wrap in try/except |
| P3 | Minor items m-1 through m-6 | Trivial | Various one-liners |

---
*Generated by the LOGOS faculty of the Thought Amplifier tripartite.*
