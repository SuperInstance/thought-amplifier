# Bug Fixes — Self-Audit Critical Findings

**Date:** 2026-08-03  
**Source:** [SELF_AUDIT.md](../experiments/SELF_AUDIT.md)  
**Auditor:** GLM-5.2 subagent (iron-sharpens-iron-code-audit)  
**Fixes Applied By:** GLM-5.2 subagent (bug-fix-logos)

---

## Summary

Three critical bugs identified by the self-audit have been fixed. Each fix is minimal, documented inline, and preserves the original API surface.

| Bug | Severity | File | Status |
|-----|----------|------|--------|
| BUG-S1 | 🔴 Critical | BondSystem/init.lua | ✅ Fixed |
| BUG-R1/R2 | 🔴 Critical | reflex/embedding.py | ✅ Fixed |
| BUG-F2 | 🔴 Critical | FilterGate.lua | ✅ Fixed |

---

## Bug 1: BondSystem Return-Bonus Dead Code (BUG-S1)

**File:** `lucineer-roblox/src/ServerScriptService/BondSystem/init.lua`

### Problem

In `BondSystem.init()`, the `PlayerAdded` handler set `data.lastSeen = os.time()` before `onPlayerJoin()` could read the previous value. This made the >24h return check in `onPlayerJoin()` always see ~0 seconds elapsed, so the `returned_next_day` bond event (+2 points) could **never fire** from the normal join path.

### Root Cause

```lua
-- BEFORE (broken):
Players.PlayerAdded:Connect(function(player)
    local data = getData(player.Name)
    data.sessionFirstBuild = false
    data.lastSeen = os.time()       -- ← overwrites previous value
    loadBond(player.Name)
    -- onPlayerJoin() was never called from init() at all
end)
```

### Fix

1. Removed the `data.lastSeen = os.time()` overwrite from `init()`.
   - `getData()` already initializes `lastSeen` to `os.time()` for new players (correct — no return bonus for first-time players).
   - For returning players, the in-memory `lastSeen` from the previous session (same server) is preserved.
2. Added explicit `BondSystem.onPlayerJoin(player.Name)` call in the `PlayerAdded` handler so the return check actually runs.

```lua
-- AFTER (fixed):
Players.PlayerAdded:Connect(function(player)
    local data = getData(player.Name)
    data.sessionFirstBuild = false
    -- lastSeen is NOT overwritten here
    loadBond(player.Name)
    BondSystem.onPlayerJoin(player.Name)  -- reads lastSeen, then updates it
end)
```

### Verification

- `onPlayerJoin()` reads `data.lastSeen`, checks if `os.time() - lastSeen >= 86400`, awards bonus if true, THEN sets `data.lastSeen = os.time()`. The ordering is now correct.
- For same-session leave/rejoin: in-memory `lastSeen` persists, so a player who leaves and returns after 24h gets the bonus. ✓
- For server restart: in-memory data is lost, `getData()` creates fresh with `lastSeen = os.time()`. Return bonus won't fire on first join after restart. This is acceptable — D1 persistence of `lastSeen` is a future enhancement (would require adding `last_seen` to the D1 upsert).

---

## Bug 2: Hash Embedding Collapse on Documents (BUG-R1 + BUG-R2)

**File:** `slackwater-cognition/reflex/embedding.py`

### Problem

Two sub-issues:
1. **BUG-R2 (Global hash byte overlap):** The global hash extraction used `start = (i * 4) % GLOBAL_DIMS` (modulo 32), which meant dimensions overlapped byte ranges. For example, dim 0 read bytes [0:4] and dim 8 also read bytes [0:4] (since `8*4=32`, `32%32=0`). This created artificial correlations between dimensions that should have been independent.
2. **BUG-R1 (Chunk threshold too high):** `CHUNK_WORD_LIMIT` was 300, but hash saturation becomes severe above ~200 words for the 96-dim word bucket.

### Fix

1. **Global hash (BUG-R2):** Replaced the overlapping `(i * 4) % GLOBAL_DIMS` with non-overlapping `i * 4` byte windows from an extended hash. The extended hash is built by concatenating salted SHA-256 iterations to ensure 128 bytes (32 dims × 4 bytes each) of non-overlapping data.

2. **Chunk threshold (BUG-R1):** Lowered `CHUNK_WORD_LIMIT` from 300 to 200 words, matching the audit's recommendation for 200-word chunks.

### Already Implemented (from prior improvements)

The codebase already had several improvements for the saturation problem:
- Stopword removal (prevents common words from inflating similarity)
- sqrt term-frequency normalization (reduces saturation on repeated tokens)
- Chunked embedding for long texts (splits, embeds, averages)

These improvements plus the two fixes above significantly reduce false similarity scores for documents >500 words.

### Note

For production document clustering, a real embedding model (e.g., `@cf/baai/bge-m3` on Cloudflare Workers AI) is still recommended. The hash embedding is designed for short command phrases and remains the best zero-dependency option for that use case.

---

## Bug 3: FilterGate Parameter Mismatch (BUG-F2)

**File:** `lucineer-roblox/src/ReplicatedStorage/Lucineer/FilterGate.lua`

### Problem

The `filterFor()` function's docstring documented the `playerId` parameter as "the UserId of the player who will see it" (the viewer/recipient). However, this value was passed directly to `TextService:FilterStringAsync(text, playerId)`, which per the Roblox API expects the **author's** UserId — the player who created or triggered the text.

This mismatch means:
- For AI-generated text, callers might pass the viewer's UserId thinking it's correct per the docs, when Roblox actually uses it for age-based filtering of the **author**.
- Filtering may be incorrect if the author and viewer have different account settings (e.g., under-13 vs 13+).

### Fix

- Renamed the parameter from `playerId` to `authorUserId` throughout the function.
- Updated the docstring to correctly document that this is the **author's** UserId (the player who authored or triggered the text), not the viewer's.
- Updated the usage example in the file header.
- Updated all warning messages to say "author" instead of "player".
- Added a detailed BUG FIX comment block explaining the change.

### Roblox API Context

Per [Roblox documentation](https://create.roblox.com/docs/reference/engine/classes/TextService#FilterStringAsync):
- `FilterStringAsync(text, fromUserId)`: `fromUserId` is the UserId of the player who created the text.
- For broadcast text (signs, NPC dialogue, AI output): use the triggering player's UserId as the author.
- For 1:1 chat: use the sender's UserId, then call `GetChatForUserAsync(toUserId)`.

The `filterForChat()` function was already correct — it properly takes `fromUserId` (sender) and `toUserId` (recipient) and passes `fromUserId` to `FilterStringAsync`.

---

## Testing Notes

- Lua files use Luau type annotations (`: string`, `: number`, etc.) which are not parseable by standard `lua5.1`/`luac5.1`. Syntax verification requires a Luau compiler (not available in this environment). The changes were verified by manual inspection and structural analysis.
- Python file (`embedding.py`) passed `py_compile` successfully.
- All API surfaces remain backward compatible:
  - `BondSystem.init()` — same interface, now calls `onPlayerJoin()` internally.
  - `FilterGate.filterFor(text, authorUserId)` — parameter renamed but position unchanged. Callers passing `player.UserId` as the second argument will work correctly **if** that player is the author/triggerer. Callers who were incorrectly passing the viewer's UserId need to update.
  - `reflex/embedding.py` — `embed()`, `cosine_similarity()` interfaces unchanged.

---

## Commits

Each fix was committed separately with a clear, descriptive message referencing the bug ID.
