# Code Quality Competition — Iron Sharpens Iron

## The Task
Each harness implements the SAME module independently. Entries are judged blind by an independent test suite.

## The Module: bottle.py
A lightweight message envelope for Thinker ↔ Conductor communication.

### Required API:
- `pack(msg_type, payload, metadata=None) -> dict` — create a bottle
- `unpack(bottle) -> (msg_type, payload, metadata)` — extract fields
- `validate(bottle) -> bool` — check structure is well-formed
- `seal(bottle, key) -> dict` — add HMAC signature
- `open(bottle, key) -> dict|None` — verify HMAC, return original or None

### Constraints:
- <200 lines, zero external dependencies (stdlib only)
- Must handle: missing fields, malformed input, replay attacks
- Must be JSON-serializable
- Must include docstrings and type hints

## Also Fix These 3 Critical Bugs (from self-audit):
1. BondSystem: init() overwrites lastSeen before onPlayerJoin reads it
2. Hash embedding collapses on documents >500 words — need truncation or chunking
3. FilterGate: parameter documented as "player who sees it" but passed as author's userId

## Quality Criteria (judged independently, blind):
1. **Correctness** (30%) — does it pass the test suite?
2. **Elegance** (25%) — clean, minimal, readable
3. **Robustness** (25%) — error handling, edge cases, security
4. **Documentation** (10%) — docstrings, comments, examples
5. **Performance** (10%) — latency, memory footprint

## Entries:
- competition/kimi/bottle.py — KimiCode K2.7
- competition/glm/bottle.py — GLM-5.2 subagent
- competition/claude/bottle.py — Claude Opus

## Judging:
Run competition/tests/judge.py against all three entries. Blind scoring.
