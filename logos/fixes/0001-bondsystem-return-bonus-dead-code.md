# Fix 0001: BondSystem Return-Bonus Dead Code

**Bug ID:** BUG-S1 (SELF_AUDIT.md)
**Severity:** 🔴 Critical
**Source:** `/home/eileen/projects/roblox-bond-system/src/BondSystem.lua`
**Date:** 2026-08-03

---

## Root Cause

In `BondSystem.init()`, `data.lastSeen = os.time()` was called *before* `BondSystem.onPlayerJoin()`, which reads `lastSeen` to compute absence duration. Since `lastSeen` was always set to `now` just before the check, `absenceSeconds` was always ~0, making the `returned_next_day` bonus (+2 points) unconditionally dead code.

```lua
-- BEFORE (broken):
Players.PlayerAdded:Connect(function(player)
    local data = getData(player.Name)
    data.lastSeen = os.time()              -- ← overwrites persisted value
    -- ...
    BondSystem.onPlayerJoin(player.Name)  -- ← reads lastSeen = NOW → absence = 0
end)

function BondSystem.onPlayerJoin(playerId)
    local lastSeen = data.lastSeen or now
    local absenceSeconds = now - lastSeen  -- ← always 0
    if absenceSeconds >= 86400 then         -- ← NEVER TRUE
        applyBondEvent("returned_next_day")
    end
end
```

## Fix

Remove `data.lastSeen = os.time()` from `init()`. The `onPlayerJoin()` function already updates `lastSeen` after the absence check, and `getData()` initializes it for new players. For returning players, the persisted value from the previous session is retained so the absence can be computed.

## Patch

```diff
--- a/src/BondSystem.lua
+++ b/src/BondSystem.lua
@@ -387,7 +387,8 @@ function BondSystem.init()
     Players.PlayerAdded:Connect(function(player)
         local data = getData(player.Name)
         data.sessionFirstBuild = false
-        data.lastSeen = os.time()
+        -- lastSeen is NOT set here; onPlayerJoin reads the persisted value
+        -- from getData(), then updates it after the return check.
 
         -- Load persisted state if a load hook is wired
         if BondSystem.hooks.load then
@@ -404,7 +405,7 @@ function BondSystem.init()
             end)
         end
 
-        -- Check for return after >24h absence
+        -- Check for return after >24h absence BEFORE updating lastSeen.
         BondSystem.onPlayerJoin(player.Name)
     end)
```

## Verification

`onPlayerJoin` correctly handles the return check:
1. Reads `lastSeen` from `data` (persisted value for returning players, `os.time()` initial value for new)
2. Computes `absenceSeconds = now - lastSeen`
3. If ≥ 86400 → awards `returned_next_day` (+2 points)
4. Sets `data.lastSeen = now` and `data.sessionFirstBuild = false`

For new players: `lastSeen` from `getData()` ≈ `now` → absence ≈ 0 → no bonus (correct).
For returning players after 24h: `lastSeen` holds prior session's timestamp → absence ≥ 86400 → bonus awarded (correct).
