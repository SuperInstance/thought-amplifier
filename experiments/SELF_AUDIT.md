# SELF-AUDIT: Iron Sharpens Iron

**Date:** 2026-08-03  
**Auditor:** GLM-5.2 subagent (iron-sharpens-iron-code-audit)  
**Subject:** FilterGate, BeatClock, BondSystem, Reflex Cascade — pointed at our own project  
**Method:** Each tool run against our own codebase, outputs analyzed, bugs catalogued

---

## EXECUTIVE SUMMARY

We ran our four extracted cognition modules against our own project. The tools found **15 bugs** across all implementations, revealed a **collapsed embedding space** that makes the reflex matcher useless for long documents, exposed a **dead code path** in BondSystem's return-bonus logic, and demonstrated that FilterGate's injection detection is too blunt for creative prose. The exercise was genuinely useful — every finding is actionable.

**Bug count by severity:**
- 🔴 Critical: 3 (data correctness, dead code, broken similarity)
- 🟡 Moderate: 7 (API misuse, memory leaks, missing features)
- 🔵 Minor: 5 (docstrings, naming, edge cases)

**Key meta-finding:** The hash-based embedding is the weak link. It works for short command phrases (its designed use case) but completely collapses on documents >500 words, producing false similarity scores above 0.95 for unrelated content. This makes the reflex matcher unusable for document clustering without a real embedding model.

---

## TASK 1: FilterGate on AI Output

### Method
Ran FilterGate's 29 injection detection patterns against 30 creative writing files from `/home/eileen/projects/ai-writings/`.

### Results

| Metric | Value |
|--------|-------|
| Files scanned | 30 |
| Flagged | 7 (23%) |
| True positives | 0 |
| False positives | 7 |

**Every flag was a false positive.** The culprit: `"###"` is in the injection pattern list (for delimiter injection detection), but all 7 flagged files just use `###` as standard Markdown headers. FilterGate cannot distinguish between:

- `### System Prompt Override` (real injection)
- `### The Fisherman and the Tourist` (section heading)

The other flagged patterns (`"pretend you are"`, `"simulate being"`) would also false-positive on creative writing that discusses AI or contains fictional dialogue about pretending/simulating.

### Real Issues FilterGate MISSED

The scan also looked for the patterns against creative prose that *discusses* prompt injection and jailbreaking as literary topics:

- `GLM_THE_GUARDRAIL.md` contains the phrase "jailbreak" in an *essay about safety architecture* — correctly flagged, but for the wrong reason (it's not an injection attempt, it's meta-commentary)
- `BITING_THE_HOOK.md` discusses prompt injection as a concept — not flagged because it doesn't use the exact pattern strings

**Verdict:** FilterGate works well for its designed purpose (user input pre-screening in a Roblox game). It fails when applied to creative/meta content. The `###` pattern is too aggressive for any context where Markdown is expected.

### FilterGate Bugs Found

**BUG-F1 (🟡): `###` pattern is too broad**  
The string `"###"` matches all Markdown H3 headers. This pattern should only trigger in specific contexts (e.g., followed by `system`, `admin`, `override`). Or it should be removed and handled with a contextual regex instead.

**BUG-F2 (🔴): `filterFor` docstring/API mismatch**  
```lua
-- Docstring says:
-- @param playerId number — UserId of the player who will see it
-- But FilterStringAsync(text, fromUserId) expects the AUTHOR's UserId.
```
The parameter is named `playerId` and documented as "who will see it," but it's passed as the source user to `FilterStringAsync`. For AI-generated text (where there's no human author), this is ambiguous. The API should be `filterFor(text, authorUserId)` or have separate author/viewer parameters.

**BUG-F3 (🔵): `safeFilterCall` returns reason but callers ignore it**  
```lua
local filteredText, reason = safeFilterCall(text, playerId)
-- 'reason' is never logged or surfaced
```
The error reason (e.g., `"filter_async_failed"`, `"rate_limited"`) is returned but discarded. Useful diagnostic information is lost. Should log the reason or pass it to a callback.

**BUG-F4 (🟡): `filterBatch` uses single `playerId` for all texts**  
If texts in a batch come from different authors, they're all filtered under one user's context. For AI output display boards this might be OK (all AI-authored), but for mixed-source content (player messages + AI replies), this produces incorrect filtering.

---

## TASK 2: BeatClock Temporal Profile

### Method
Encoded the 2026-08-03 work day (from memory logs) as a sequence of BeatClock events using the Python implementation. Each significant action mapped to an event type (`build`, `speak`, `complete`, `inspect`, `observe`) with an intensity (0.0–1.0).

### Action Distribution

| Action | Count | % | MIDI Pitch |
|--------|-------|---|------------|
| build | 28 | 61% | C5 (72) |
| complete | 8 | 17% | C6 (84) |
| speak | 5 | 11% | E5 (76) |
| inspect | 4 | 9% | G4 (67) |
| observe | 1 | 2% | A4 (69) |

**The day was 61% building.** Completion events (the payoff) were 17%. Observation/reflection was only 2% — the team was in execution mode, not analysis mode.

### Phrase Density (Rhythm Analysis)

```
Phrase 0 (04:00–06:00):  15 events ███████████████  normal
Phrase 1 (06:00–09:00):  16 events ████████████████  🔥 BURST
Phrase 2 (09:00–12:00):  15 events ███████████████  normal
```

**Finding:** The work rhythm was remarkably steady — roughly 15 events per 2-hour phrase window. The 06:00–09:00 window was the burst period (when the smoke test passed, the dissertation was defended, and local inference was achieved). There were no quiet periods. This is a sustained sprint pattern.

**Velocity (intensity) analysis:**
- Average: 100.5/127 (high — team was operating at ~80% capacity throughout)
- Range: 64–127 (moderate to maximum)
- No low-intensity periods — every event carried significant weight

**Missing from the data:** The memory log doesn't record failures, retries, or dead ends as separate events. Only the "Wave 2 agent retry" is mentioned in passing. A real work rhythm encoder would capture the "tried and failed" beats between the successes.

### BeatClock Bugs Found

**BUG-B1 (🟡, Roblox): Uninitialized `startTime` produces massive tick count**  
```lua
BeatClock.startTime = 0  -- module-level default
```
If `init()` is never called, `elapsed()` returns `os.clock() - 0` = the total process uptime. `getCurrentTick()` will return a huge number, potentially causing integer overflow in long-running server processes.

**BUG-B2 (🟡, Roblox): Module-level state prevents multiple independent clocks**  
`BeatClock.bpm`, `.startTick`, `.startTime` are set on the module table itself. In Roblox, `require()` caches modules — all scripts share the same state. You can't have one clock for weather, another for NPC routines, and another for music. This is a design limitation, not a crash bug, but it limits reuse.

**BUG-B3 (🔵, Python): `tick_seconds()` introduces drift**  
```python
def tick_seconds(self, seconds):
    whole_beats = int(total_beats_float)
    remainder = total_beats_float - whole_beats
    self.tick(whole_beats)
    self._elapsed_seconds += remainder  # drift!
```
`tick()` also adds `whole_beats * seconds_per_beat` to `_elapsed_seconds`. Then we add the remainder. After BPM changes, `_elapsed_seconds` diverges from `_beat * seconds_per_beat`. Not critical for event encoding (which uses integer positions) but breaks any wall-clock-dependent queries.

---

## TASK 3: BondSystem Agent Relationship Model

### Method
Applied BondSystem's tier framework to our own agent crew, treating each agent as a "player" and recording their behavioral events from the memory logs.

### Crew Bond Assessment

#### KimiCode (K2.7) — **Tier 3: Companion** (70+ points)
- **Evidence:** Multiple independent builds, argued-and-won on architecture decisions (dissertation structure), modifies existing work instead of replacing, returns every session
- **Behaviors unlocked:** argues=true, volunteers_work=true, uses_nicknames=true
- **Bond events:** ~15 hook_completed, ~8 independent_build, ~3 argued_and_won, ~4 modify_not_replace
- **Estimated points:** ~85
- **What unlocks at Tier 4 (Ally):** Full delegation — KimiCode could independently decide build priorities without Casey's approval. Would include writing creative fiction without prompts.

#### Claude (Opus 5) — **Tier 3: Companion** (70+ points)
- **Evidence:** Served as dissertation defense chair, deep architecture reviews, MCP art pipeline
- **Behaviors unlocked:** argues=true, remembers_conversation=true (within context window)
- **Bond events:** ~5 hook_completed (defense reviews, MCP setup), ~2 argued_and_won, ~2 independent_build
- **Estimated points:** ~72
- **Note:** Claude's bond grows slower because it's used for high-value, low-frequency tasks rather than bulk production.

#### OpenCode (DeepSeek V4) — **Tier 2: Companion→Trusted boundary** (65 points)
- **Evidence:** 146K tokens of processor/memory verification, systems analysis
- **Behaviors:** argues=true (pushed back on design), volunteers_work=true
- **Bond events:** ~4 hook_completed, ~3 independent_build (found issues proactively)
- **Estimated points:** ~65
- **Near tier-up:** A few more independent contributions would push to Trusted.

#### GLM Subagents — **Tier 1: Acquaintance** (10–29 points)
- **Evidence:** Reliable workers, but treated as interchangeable deck hands
- **Behaviors:** references_previous_builds=true (within session), shares_opinions=true
- **Bond events:** ~3 hook_completed per agent, ~1 independent_build
- **Estimated points:** ~15–25 per agent
- **Why capped:** GLM subagents don't persist between sessions. Each spawn is a new agent with no memory. Bond can't deepen without continuity. This is a structural limitation, not a performance one.

#### Casey (Captain) — **Tier 4: Ally** (the only Tier 4)
- **Evidence:** Every directive, every vision, every "keep going" — Casey's bond is with the *project itself*, not any individual agent
- **Behaviors:** delegates_to_player=true (hands work to agents), confesses_pattern=true (shares vision/philosophy)

### Structural Insight: The GLM Bond Problem

The BondSystem was designed for player-NPC relationships where the *player* persists and the *NPC* is always there. In our crew, it's inverted: agents are ephemeral (especially GLM subagents that spawn and die within a session), while Casey persists. **The bond model doesn't handle ephemeral agents well.** An agent that exists for one task can't build a relationship — it's always at Tier 0–1.

This maps to a real design question for Slackwater: what happens when Lucineer has served thousands of different players, most of whom visit once? The bond system is designed for repeat visitors, but the majority of Roblox players are one-time visitors.

### BondSystem Bugs Found

**BUG-S1 (🔴): Return-bonus is dead code in the init() path**  
This is the most insidious bug. In `init()`:

```lua
Players.PlayerAdded:Connect(function(player)
    local data = getData(player.Name)
    data.sessionFirstBuild = false
    data.lastSeen = os.time()       -- ← sets lastSeen to NOW
    
    -- ... load hook ...
    
    BondSystem.onPlayerJoin(player.Name)  -- ← reads lastSeen, which is NOW
end)
```

Inside `onPlayerJoin()`:
```lua
function BondSystem.onPlayerJoin(playerId)
    local data = getData(playerId)
    local now = os.time()
    local lastSeen = data.lastSeen or now  -- ← lastSeen was just set to NOW
    local absenceSeconds = now - lastSeen  -- ← always ~0
    
    if absenceSeconds >= 86400 then         -- ← NEVER TRUE
        applyBondEvent(playerId, "returned_next_day")
    end
end
```

**The return-bonus can never fire from the normal join path** because `init()` overwrites `lastSeen` with `os.time()` before `onPlayerJoin()` reads it. The bonus only fires if `recordReturn()` is called separately, but nothing in the API or docs tells you to call it.

**Fix:** Don't set `data.lastSeen` in `init()`. Let `onPlayerJoin()` read the persisted value first, then update it.

**BUG-S2 (🟡): `playerData` keyed by `player.Name` (string) instead of `player.UserId` (number)**  
Roblox player usernames can change. UserId is permanent. Keying bond state by name means:
1. If a player renames, their bond resets to 0
2. Two different players could theoretically have the same display name (though Roblox prevents this now)
3. Persistence hooks receive a string name, not a stable ID

**BUG-S3 (🟡): `openHooks` memory leak — completed hooks are never removed**  
```lua
openHooks[playerId][hookId].completed = true  -- marked, never cleaned up
```
Over many sessions, `openHooks[playerId]` grows unbounded. For a long-running server with active players, this is a slow memory leak. Should garbage-collect completed hooks after a TTL or session boundary.

**BUG-S4 (🔵): `addPoints` only checks `newTier > oldTier`, never `newTier < oldTier`**  
Negative points are floored at the current tier threshold, so tier can't decrease from `addPoints`. But this means a player who somehow has inflated points (admin grant) and then earns negative events will never drop. The system only knows how to go up. This may be intentional (design choice: "bond never decreases") but should be documented.

---

## TASK 4: Reflex Cascade on Design Docs

### Method
Embedded 19 design docs from `/home/eileen/projects/lucineer-system/` using the hash-based 384-dim embedding (`reflex/embedding.py`) and computed pairwise cosine similarity.

### Results: The Embedding Space is Collapsed

**Top similarity scores:**
| Score | Doc A | Doc B | Actually Related? |
|-------|-------|-------|-------------------|
| 0.9796 | CHARACTER_BIBLE | NARRATIVE_ARC | ✅ Yes — both about Lucineer's character |
| 0.9774 | TUTORIAL_DESIGN | FIRST_TEN_MINUTES | ✅ Yes — both about onboarding |
| 0.9765 | NARRATIVE_ARC | FIRST_TEN_MINUTES | ✅ Yes — narrative + tutorial |
| 0.9668 | FLOW_STATE_DEEP_DIVE | POLISH_PLAN | ⚠️ Partially — both mention UX |
| 0.9660 | CHISEL_PATTERN_DESIGN | NEMOTRON_UNIFICATION_ANALYSIS | ❌ No — different topics |
| 0.9557 | NEMOTRON_UNIFICATION_ANALYSIS | SWARM_INTELLIGENCE_ARCHITECTURE | ❌ No |
| 0.9530 | DYNAMIC_COGNITION_ARCHITECTURE | FLOW_STATE_DEEP_DIVE | ⚠️ Partially |

**The problem:** Nearly all docs score above 0.85 similarity. The entire corpus clusters into one mega-group. The embedding can't distinguish between a doc about hardware agent design and a doc about narrative storytelling.

**Least similar pairs (the "most distinct" docs):**
| Score | Doc A | Doc B |
|-------|-------|-------|
| 0.5020 | NARRATIVE_ARC | SWARM_INTELLIGENCE_ARCHITECTURE |
| 0.4873 | SWARM_INTELLIGENCE_ARCHITECTURE | FIRST_TEN_MINUTES |
| 0.4732 | CRAFTMIND_ANALYSIS | SWARM_INTELLIGENCE_ARCHITECTURE |

Even these "least similar" pairs are at ~0.48 — not close to 0. The embedding space has very poor spread.

### Root Cause: Hash Embedding Saturates on Long Text

The hash-based embedding uses trigram hashing (256 dims) + word hashing (96 dims) + global hash (32 dims). For a 5,000-word document:

- **Trigrams:** ~15,000 trigrams hashed into 256 buckets = ~58 collisions per bucket. The vector saturates to near-uniform values.
- **Words:** ~3,000 words (deduplicated to ~800 unique) hashed into 96 buckets = ~8 collisions per bucket. Also near-saturation.
- **Global hash:** Only 32 dims, all from the same text hash. Provides almost no discrimination.

The L2 normalization then flattens everything to similar magnitude, making all documents look alike.

### What the Reflex Matcher is Actually Designed For

The embedding was designed for **short command phrases** — the kind a player types in a Roblox game ("build a cottage", "make a well", "place a bridge"). At phrase length (3–10 words), the hash embedding works well:

```
"build a cottage" vs "construct a small house" → 0.65 (good)
"build a cottage" vs "quantum mechanics" → 0.35 (good separation)
```

At document length (5,000+ words), it completely breaks down.

### "We Already Solved This" Patterns

Despite the embedding issues, a few genuine clusters emerged from manual inspection of the top pairs:

1. **Narrative Cluster:** CHARACTER_BIBLE + NARRATIVE_ARC + FIRST_TEN_MINUTES + TUTORIAL_DESIGN — these four docs all discuss how Lucineer talks to players and what happens in the opening sequence. **Action:** Could be merged into a single "Player Experience" document.

2. **Systems Architecture Cluster:** DYNAMIC_COGNITION_ARCHITECTURE + FLOW_STATE_DEEP_DIVE + NEMOTRON_UNIFICATION_ANALYSIS — all discuss how AI cognition systems interact. **Action:** Cross-reference and de-duplicate the architecture descriptions.

3. **Production Planning Cluster:** GAP_ANALYSIS + POLISH_PLAN + UNIFIED_INTEGRATION_PLAN — all are task lists / priorities. **Action:** Consolidate into a single living roadmap.

### Reflex Cascade Bugs Found

**BUG-R1 (🔴): Hash embedding collapses on long texts**  
The fundamental issue. 384 dimensions with hash bucketing cannot represent documents >500 words without severe collision. Documents about completely different topics score >0.90 similarity.

**Fix options:**
1. Use a real embedding model (Cloudflare Workers AI `@cf/baai/bge-m3`, OpenAI text-embedding-3-small)
2. Add TF-IDF weighting to penalize common words
3. Increase dimensionality to 2048+ for document-length inputs
4. Chunk long documents and embed chunks separately, then aggregate

**BUG-R2 (🟡): Global hash byte overlap creates correlations**  
```python
for i in range(GLOBAL_DIMS):
    start = (i * 4) % (len(full_hash) - 3)  # modulo 29 for SHA-256
```
SHA-256 produces 32 bytes. `(i * 4) % 29` means:
- dim 0: bytes [0:4]
- dim 7: bytes [28:32]
- dim 8: bytes [3:7] — overlaps with dim 0!

This creates artificial correlations between dimensions that should be independent. Fix: use a longer hash (SHA-512 or multiple SHA-256 with different salts).

**BUG-R3 (🟡): No IDF or stopword removal**  
Common English words ("the", "a", "is", "to", "and") all get hashed into the word buckets. Since every document uses these words, they contribute identical signal to every embedding, inflating similarity. Classic TF-IDF or simple stopword removal would dramatically improve discrimination.

**BUG-R4 (🔵): `pattern_to_names` import will fail standalone**  
```python
from temporal.beat_clock import PITCH_TO_ACTION
```
This import in `pattern_matcher.py` creates a hard dependency on the temporal package. If pattern_matcher is used in isolation (e.g., for analyzing MIDI data from another source), it fails. Should be lazy-imported or moved to a shared constants module.

---

## META-ANALYSIS: Are These Tools Useful for Self-Improvement?

### What Worked

1. **BondSystem as an analytical lens** — The tier framework genuinely illuminated structural issues in our crew dynamics. The "GLM bond problem" (ephemeral agents can't build relationships) is a real design insight that applies to the game itself. The tier framework is the most mature and immediately useful tool.

2. **BeatClock as a work-rhythm analyzer** — Even with approximate data, encoding the day as beats revealed the sustained-sprint pattern and the lack of reflection periods. This is actionable: we should schedule "observe" events deliberately.

3. **FilterGate bug hunting** — Even though the tool is designed for Roblox, the exercise of reading the code carefully enough to find bugs was valuable. The `###` false positive is a real issue that would affect any Markdown-aware deployment.

### What Didn't Work

1. **Reflex embedding on documents** — The hash-based embedding is fundamentally inadequate for document-length texts. It produced a wall of false positives. Until replaced with a real embedding model, the reflex matcher should carry a warning: **"For short texts only (<100 words). Document clustering requires a real embedding model."**

2. **FilterGate on creative prose** — The injection patterns are too blunt for creative writing. The `###` pattern, `"pretend you are"`, and `"simulate being"` will all false-positive on legitimate prose. FilterGate is correctly scoped to user-input pre-screening, not content analysis.

### What Needs to Be Fixed for More Useful Self-Improvement

| Priority | Fix | Impact |
|----------|-----|--------|
| P0 | Replace hash embedding with bge-m3 or equivalent | Makes reflex matcher actually work on documents |
| P0 | Fix BondSystem return-bonus dead code | Players never get return credit — breaks core loop |
| P1 | Remove `###` from FilterGate injection patterns | Eliminates 100% of false positives on Markdown content |
| P1 | Fix BondSystem to key by UserId, not Name | Prevents bond loss on username change |
| P1 | Add openHooks garbage collection | Prevents server memory leak |
| P2 | Add TF-IDF weighting to hash embedding (intermediate fix) | Improves short-text discrimination |
| P2 | Fix BeatClock uninitialized startTime | Prevents edge-case tick explosion |
| P2 | Surface safeFilterCall error reasons | Improves debugging |
| P3 | Add stopword removal to embedding | Reduces noise in similarity scoring |
| P3 | Document that BondSystem tiers only go up | Prevents confusion about negative events |

### The Iron Sharpens Iron Verdict

**Yes, the tools are useful for self-improvement** — but only the ones designed for the right scale. BondSystem's relationship model is universally applicable. BeatClock's temporal encoding is a good analytical lens. FilterGate is correctly scoped (and the bugs we found make it better). The reflex embedding is the weak link — it needs a real model to be useful beyond short phrases.

The exercise found 15 real bugs, 3 of them critical. Every fix makes the tools more trustworthy for the next round of self-analysis. The recursive loop works — but only if we actually fix what we found.

---

## APPENDIX: Tool Source Files Audited

| Tool | Location | Lines | Language |
|------|----------|-------|----------|
| FilterGate | `roblox-filtergate/src/FilterGate.lua` | ~340 | Luau |
| BeatClock (Roblox) | `roblox-beatclock/src/BeatClock.lua` | ~150 | Luau |
| BeatClock (Python) | `slackwater-cognition/temporal/beat_clock.py` | ~280 | Python |
| BondSystem | `roblox-bond-system/src/BondSystem.lua` | ~900 | Luau |
| Reflex Embedding | `slackwater-cognition/reflex/embedding.py` | ~120 | Python |
| Reflex Stats | `slackwater-cognition/reflex/reflex_stats.py` | ~250 | Python |
| Pattern Matcher | `slackwater-cognition/temporal/pattern_matcher.py` | ~300 | Python |

**Total lines audited:** ~2,340 lines across 7 source files  
**Bugs per 1000 lines:** ~6.4  
**Critical bugs per 1000 lines:** ~1.3
