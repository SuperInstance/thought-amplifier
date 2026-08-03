# Fix 0002: FilterGate `filterFor` Docstring/Parameter Mismatch

**Bug ID:** BUG-F2 (SELF_AUDIT.md)
**Severity:** 🔴 Critical
**Source:** `/home/eileen/projects/roblox-filtergate/src/FilterGate.lua`
**Date:** 2026-08-03

---

## Root Cause

The `filterFor` function's docstring described `playerId` as "UserId of the player who will see it," but the parameter is passed as the `fromUserId` (author) to Roblox's `TextService:FilterStringAsync(text, fromUserId)`. This ambiguity is particularly dangerous for AI-generated text where there's no human author — integrators might pass the viewer's ID instead of the NPC/author ID, causing incorrect filtering behavior.

The sibling function `filterForChat` correctly used `fromUserId` for the same purpose, making the naming inconsistent within the same module.

```lua
-- BEFORE (misleading):
-- @param playerId number — UserId of the player who will see it
function FilterGate.filterFor(text: string, playerId: number): string?
    -- ...
    local filteredText, reason = safeFilterCall(text, playerId)
    --                                      ^^^^^^^^ passed as AUTHOR to FilterStringAsync
end
```

## Fix

1. Rename parameter `playerId` → `fromUserId` to match `filterForChat`'s naming and Roblox API convention.
2. Update docstring to clarify that this is the text author's UserId, not the viewer.
3. Add explanation for AI-authored text: use the NPC's UserId.

## Patch

```diff
--- a/src/FilterGate.lua
+++ b/src/FilterGate.lua
@@ -14,7 +14,7 @@
 
     Usage:
         local FilterGate = require(ReplicatedStorage.FilterGate)
-        local filtered = FilterGate.filterFor(modelText, player.UserId)
+        local filtered = FilterGate.filterFor(modelText, authorUserId)
         if filtered then
             -- display filtered
         else
@@ -249,16 +249,19 @@ end
 --[[
-    Filter a string for display to a specific player (broadcast/UI).
+    Filter a string for broadcast/UI display (non-chat).
 
     Calls Roblox TextService:FilterStringAsync and retrieves the
     non-chat broadcast string. On success, returns the filtered string.
     On ANY error — HTTP failure, timeout, malformed input, rate limit —
     returns nil, meaning "display nothing."

     The contract: never return unfiltered text. If the filter breaks,
     the string doesn't show. Fail-closed.
 
+    For AI-generated text with no human author, use the NPC's UserId
+    as fromUserId. For chat messages between players, use filterForChat.
 
-    @param text string — the text to filter
-    @param playerId number — UserId of the player who will see it
+    @param text string — the text to filter
+    @param fromUserId number — UserId of the text author (passed to FilterStringAsync)
     @return string? — filtered string, or nil on any failure
 ]]
-function FilterGate.filterFor(text: string, playerId: number): string?
+function FilterGate.filterFor(text: string, fromUserId: number): string?
     -- Pre-check for injection attempts
     local injection = detectInjection(text)
     if injection then
@@ -275,7 +278,7 @@ function FilterGate.filterFor(text: string, playerId: number): string?
         return nil
     end
 
-    local filteredText, reason = safeFilterCall(text, playerId)
+    local filteredText, reason = safeFilterCall(text, fromUserId)
 
     if filteredText and config.onFiltered then
         pcall(config.onFiltered, text, "broadcast")
```

## Verification

- `filterForChat` already uses `fromUserId` — naming is now consistent.
- `safeFilterCall(text, fromUserId, toUserId?)` — the first param is always the author.
- Integrators now clearly see that this parameter identifies the text source, not the display target.
