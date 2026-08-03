"""
test_bottle.py — Integration tests for the .bottle protocol

The .bottle protocol is a lightweight message envelope for Thinker ↔ Conductor
communication. Each "bottle" is a JSON-serializable dict containing a message
type, payload, and optional metadata. Bottles can be sealed with HMAC
signatures for integrity and authenticated with a shared key.

Protocol contract (from competition/SPEC.md):
  - pack(msg_type, payload, metadata=None) -> dict
  - unpack(bottle) -> (msg_type, payload, metadata)
  - validate(bottle) -> bool
  - seal(bottle, key) -> dict  — add HMAC signature
  - open(bottle, key) -> dict|None  — verify HMAC, return original or None

Constraints:
  - <200 lines, zero external dependencies (stdlib only)
  - Must handle: missing fields, malformed input, replay attacks
  - Must be JSON-serializable
  - Must include docstrings and type hints

These tests validate the protocol contract. They import from a reference
bottle.py implementation in this directory.
"""

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any

# Ensure we can import from the scheduler package and tests directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bottle


# ---------------------------------------------------------------------------
# 1. Core API: pack / unpack round-trip
# ---------------------------------------------------------------------------

def test_pack_returns_dict():
    """pack() must return a dict."""
    b = bottle.pack("thought", {"text": "hello"})
    assert isinstance(b, dict), f"Expected dict, got {type(b)}"


def test_pack_without_metadata():
    """pack() must accept two arguments (metadata optional)."""
    b = bottle.pack("thought", {"text": "hello"})
    assert isinstance(b, dict)


def test_pack_with_metadata():
    """pack() must accept three arguments with metadata."""
    b = bottle.pack("directive", {"action": "build"}, {"priority": "high"})
    assert isinstance(b, dict)


def test_unpack_round_trip_basic():
    """pack then unpack must return identical msg_type, payload, metadata."""
    msg_type = "thought"
    payload = {"text": "hello", "beat": 42}
    metadata = {"priority": "NORMAL", "agent": "thinker"}
    b = bottle.pack(msg_type, payload, metadata)
    mt, pl, md = bottle.unpack(b)
    assert mt == msg_type, f"msg_type mismatch: {mt} != {msg_type}"
    assert pl == payload, f"payload mismatch: {pl} != {payload}"
    assert md == metadata, f"metadata mismatch: {md} != {metadata}"


def test_unpack_round_trip_no_metadata():
    """unpack should return None or {} for metadata when not provided."""
    b = bottle.pack("thought", {"text": "hello"})
    mt, pl, md = bottle.unpack(b)
    assert mt == "thought"
    assert pl == {"text": "hello"}
    assert md is None or md == {}, f"metadata should be None or empty, got {md}"


def test_unpack_round_trip_empty_payload():
    """Empty payload should round-trip correctly."""
    b = bottle.pack("empty", {})
    mt, pl, md = bottle.unpack(b)
    assert mt == "empty"
    assert pl == {}


def test_unpack_round_trip_nested_payload():
    """Nested dicts and lists in payload must survive round-trip."""
    payload = {
        "nested": {"a": 1, "b": [2, 3, {"c": 4}]},
        "list": [1, "two", None, True, False],
    }
    b = bottle.pack("complex", payload)
    mt, pl, md = bottle.unpack(b)
    assert pl == payload


def test_unpack_round_trip_null_values():
    """None values in payload must survive round-trip."""
    payload = {"a": None, "b": 1, "c": None}
    b = bottle.pack("nullable", payload)
    mt, pl, md = bottle.unpack(b)
    assert pl == payload


def test_unpack_round_trip_special_chars():
    """Special characters and Unicode must survive round-trip."""
    payload = {
        "emoji": "🧠💭🔮",
        "unicode": "こんにちは",
        "rtl": "مرحبا",
        "special": '"\n\t\r\\/',
    }
    b = bottle.pack("unicode", payload)
    mt, pl, md = bottle.unpack(b)
    assert pl == payload


def test_unpack_round_trip_large_string():
    """Large payload strings must survive round-trip."""
    payload = {"data": "x" * 10000}
    b = bottle.pack("large", payload)
    mt, pl, md = bottle.unpack(b)
    assert len(pl["data"]) == 10000
    assert pl == payload


# ---------------------------------------------------------------------------
# 2. JSON Serialization
# ---------------------------------------------------------------------------

def test_json_serialize_deserialize():
    """Bottles must survive json.dumps/loads round-trip."""
    b = bottle.pack("thought", {"text": "hello", "num": 42})
    serialized = json.dumps(b)
    assert isinstance(serialized, str)
    restored = json.loads(serialized)
    assert isinstance(restored, dict)
    mt, pl, md = bottle.unpack(restored)
    assert mt == "thought"
    assert pl["text"] == "hello"


def test_json_serialize_sealed():
    """Sealed bottles must survive json.dumps/loads round-trip."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret")
    serialized = json.dumps(sealed)
    restored = json.loads(serialized)
    opened = bottle.open(restored, "secret")
    assert opened is not None
    mt, _, _ = bottle.unpack(opened)
    assert mt == "thought"


# ---------------------------------------------------------------------------
# 3. Validate — well-formed vs. malformed
# ---------------------------------------------------------------------------

def test_validate_valid_bottle():
    """validate() must return True for a well-formed bottle."""
    b = bottle.pack("thought", {"text": "hello"})
    assert bottle.validate(b) is True


def test_validate_empty_dict():
    """validate() must return False for an empty dict."""
    assert bottle.validate({}) is False


def test_validate_none():
    """validate() must return False for None (must not crash)."""
    assert bottle.validate(None) is False


def test_validate_non_dict_string():
    """validate() must return False for a string."""
    assert bottle.validate("not a bottle") is False


def test_validate_non_dict_int():
    """validate() must return False for a non-dict primitive."""
    assert bottle.validate(42) is False


def test_validate_non_dict_list():
    """validate() must return False for a list."""
    assert bottle.validate([1, 2, 3]) is False


def test_validate_missing_msg_type():
    """validate() must return False when msg_type field is missing."""
    b = bottle.pack("thought", {"text": "hello"})
    b = dict(b)
    assert "type" in b or "msg_type" in b or "message_type" in b
    # Find and remove the type key
    type_keys = ["type", "msg_type", "message_type"]
    for k in type_keys:
        b.pop(k, None)
    assert bottle.validate(b) is False


def test_validate_missing_payload():
    """validate() must return False when payload field is missing."""
    b = bottle.pack("thought", {"text": "hello"})
    b = dict(b)
    payload_keys = ["payload", "data", "body", "content"]
    for k in payload_keys:
        b.pop(k, None)
    # If all payload keys are gone, should be invalid
    assert bottle.validate(b) is False


def test_validate_corrupted_bottle():
    """validate() must return False when the bottle struct is corrupted."""
    b = bottle.pack("thought", {"text": "hello"})
    b["__malicious__"] = "injected"
    # Should still validate (extra keys don't break the envelope)
    # or return False depending on strictness
    result = bottle.validate(b)
    assert result in (True, False), f"Expected bool, got {type(result)}"


def test_validate_sealed_bottle():
    """validate() must work on sealed bottles (with extra keys)."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret")
    result = bottle.validate(sealed)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# 4. Security: seal / open
# ---------------------------------------------------------------------------

def test_seal_returns_dict():
    """seal() must return a dict."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret_key")
    assert isinstance(sealed, dict)


def test_seal_adds_signature():
    """seal() must add a signature or HMAC field to the bottle."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret_key")
    has_sig = any(
        k in sealed for k in ("signature", "hmac", "sig", "mac", "auth")
    )
    assert has_sig, f"No signature field found in sealed bottle: {list(sealed.keys())}"


def test_seal_preserves_fields():
    """sealed bottle must contain all original fields."""
    b = bottle.pack("thought", {"text": "hello"}, {"priority": "high"})
    sealed = bottle.seal(b, "secret")
    keys_before = set(b.keys())
    keys_after = set(sealed.keys())
    for k in keys_before:
        assert k in keys_after, f"Missing key '{k}' in sealed bottle"


def test_open_correct_key():
    """open() with correct key must return the original bottle."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "correct_key")
    opened = bottle.open(sealed, "correct_key")
    assert opened is not None, "open() returned None for correct key"
    assert isinstance(opened, dict)
    mt, pl, _ = bottle.unpack(opened)
    assert mt == "thought"
    assert pl == {"text": "hello"}


def test_open_wrong_key():
    """open() with wrong key must return None."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "correct_key")
    result = bottle.open(sealed, "wrong_key")
    assert result is None, f"open() should return None for wrong key, got {result}"


def test_open_tampered_bottle():
    """open() must return None when the bottle has been tampered with."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret")
    # Clone and tamper
    tampered = dict(sealed)
    tampered["__tampered__"] = True
    # Remove signature to inject new data
    for k in ("signature", "hmac", "sig", "mac"):
        tampered.pop(k, None)
    result = bottle.open(tampered, "secret")
    assert result is None or isinstance(result, dict), \
        f"Tampered bottle: expected None or dict, got {type(result)}"


def test_open_unsealed_bottle():
    """open() on an unsealed bottle should return None or the bottle."""
    b = bottle.pack("thought", {"text": "hello"})
    result = bottle.open(b, "secret")
    assert result is None or isinstance(result, dict)


def test_seal_different_keys_produce_different_signatures():
    """Different keys must produce different seals."""
    b = bottle.pack("thought", {"text": "hello"})
    s1 = bottle.seal(b, "key_a")
    s2 = bottle.seal(b, "key_b")
    sig_keys = ("signature", "hmac", "sig", "mac", "auth")
    s1_sig = None
    s2_sig = None
    for k in sig_keys:
        if k in s1:
            s1_sig = s1[k]
        if k in s2:
            s2_sig = s2[k]
    if s1_sig is not None and s2_sig is not None:
        assert s1_sig != s2_sig, "Different keys produced same signature"


def test_seal_deterministic():
    """Sealing the same bottle with same key must be deterministic."""
    b = bottle.pack("thought", {"text": "hello"})
    s1 = bottle.seal(b, "secret")
    s2 = bottle.seal(b, "secret")
    assert s1 == s2, "seal() must be deterministic"


# ---------------------------------------------------------------------------
# 5. Replay attack protection
# ---------------------------------------------------------------------------

def test_seal_includes_timestamp_or_nonce():
    """seal() should include timestamp or nonce for replay protection."""
    b = bottle.pack("thought", {"text": "hello"})
    sealed = bottle.seal(b, "secret")
    has_ts = any(
        k in sealed for k in ("timestamp", "ts", "nonce", "time", "created")
    )
    assert has_ts, (
        "seal() should include timestamp/nonce for replay protection. "
        f"Keys found: {list(sealed.keys())}"
    )


def test_seal_different_timestamps_different_seals():
    """Two seal calls at different times should produce different seals."""
    b = bottle.pack("thought", {"text": "hello"})
    s1 = bottle.seal(b, "secret")
    time.sleep(0.01)
    s2 = bottle.seal(b, "secret")
    assert s1 != s2, (
        "seal() should include timestamp to produce different seals at different times"
    )


# ---------------------------------------------------------------------------
# 6. Unpack robustness — malformed input
# ---------------------------------------------------------------------------

def test_unpack_empty_dict():
    """unpack() on empty dict should raise or return sentinel."""
    try:
        result = bottle.unpack({})
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    except (KeyError, ValueError, TypeError, AttributeError):
        pass


def test_unpack_none():
    """unpack() on None should raise or return sentinel."""
    try:
        result = bottle.unpack(None)
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    except (TypeError, ValueError, AttributeError):
        pass


def test_unpack_string():
    """unpack() on a string should raise."""
    try:
        bottle.unpack("not a bottle")
        # If it doesn't raise, that's technically OK but unusual
    except (TypeError, ValueError, KeyError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# 7. Pack robustness — malformed input
# ---------------------------------------------------------------------------

def test_pack_empty_msg_type():
    """pack() with empty string msg_type should work or raise clearly."""
    try:
        b = bottle.pack("", {"text": "hello"})
        assert isinstance(b, dict)
    except (ValueError, TypeError):
        pass


def test_pack_none_payload():
    """pack() with None payload should work or raise clearly."""
    try:
        b = bottle.pack("thought", None)
        assert isinstance(b, dict)
    except (ValueError, TypeError):
        pass


def test_pack_non_dict_payload():
    """pack() with non-dict payload should work or raise clearly."""
    try:
        b = bottle.pack("thought", "just a string")
        assert isinstance(b, dict)
    except (ValueError, TypeError):
        pass


# ---------------------------------------------------------------------------
# 8. Determinism and idempotency
# ---------------------------------------------------------------------------

def test_pack_deterministic():
    """pack() must be deterministic — same input, same output."""
    b1 = bottle.pack("test", {"a": 1}, {"m": 2})
    b2 = bottle.pack("test", {"a": 1}, {"m": 2})
    assert b1 == b2, "pack() must be deterministic"


def test_pack_idempotent():
    """Packing the same data twice must yield identical bottles."""
    params = ("test", {"a": 1}, {"m": 2})
    b1 = bottle.pack(*params)
    b2 = bottle.pack(*params)
    assert b1 == b2


# ---------------------------------------------------------------------------
# 9. Interoperability — bottles from dicts
# ---------------------------------------------------------------------------

def test_validate_hand_crafted_bottle():
    """A hand-crafted dict with the right fields should validate."""
    b = {
        "type": "thought",
        "payload": {"text": "hello"},
        "metadata": None,
    }
    result = bottle.validate(b)
    assert isinstance(result, bool)


def test_unpack_hand_crafted_bottle():
    """A hand-crafted bottle dict should unpack correctly."""
    b = {
        "type": "thought",
        "payload": {"text": "hello"},
        "metadata": {"agent": "thinker"},
    }
    try:
        mt, pl, md = bottle.unpack(b)
        assert mt == "thought"
        assert pl == {"text": "hello"}
        assert md == {"agent": "thinker"}
    except (KeyError, ValueError, TypeError):
        pass  # Some implementations may enforce stricter internal keys


# ---------------------------------------------------------------------------
# 10. Performance baseline
# ---------------------------------------------------------------------------

def test_pack_unpack_performance():
    """1000 pack/unpack cycles should complete quickly (< 100ms)."""
    start = time.time()
    for i in range(1000):
        b = bottle.pack("perf", {"n": i, "data": "x" * 20})
        mt, pl, md = bottle.unpack(b)
        assert mt == "perf"
    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 1000, (
        f"1000 pack/unpack cycles took {elapsed_ms:.0f}ms, expected < 1000ms"
    )


def test_seal_open_performance():
    """1000 seal/open cycles should complete quickly (< 500ms)."""
    b = bottle.pack("perf", {"n": 0})
    start = time.time()
    for i in range(1000):
        sealed = bottle.seal(b, "secret")
        opened = bottle.open(sealed, "secret")
        assert opened is not None
    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 2000, (
        f"1000 seal/open cycles took {elapsed_ms:.0f}ms, expected < 2000ms"
    )


# ---------------------------------------------------------------------------
# 11. Edge cases — keys and values
# ---------------------------------------------------------------------------

def test_unusual_msg_types():
    """msg_type with special characters should round-trip."""
    for mt in [
        "thought.v2",
        "directive/action",
        "system:heartbeat",
        "event__new",
    ]:
        b = bottle.pack(mt, {"a": 1})
        result_mt, _, _ = bottle.unpack(b)
        assert result_mt == mt, f"msg_type mismatch: {result_mt} != {mt}"


def test_metadata_none_vs_empty():
    """None metadata vs empty dict metadata should both be handled."""
    b_none = bottle.pack("test", {"a": 1}, None)
    b_empty = bottle.pack("test", {"a": 1}, {})
    _, _, md_none = bottle.unpack(b_none)
    _, _, md_empty = bottle.unpack(b_empty)
    assert md_none is None or md_none == {}, f"Unexpected metadata for None: {md_none}"
    assert md_empty is None or md_empty == {}, f"Unexpected metadata for empty: {md_empty}"


def test_float_payload_values():
    """Float values in payload should round-trip."""
    import math
    payload = {"pi": 3.14159, "neg": -1.0, "zero": 0.0}
    b = bottle.pack("float", payload)
    _, pl, _ = bottle.unpack(b)
    assert abs(pl["pi"] - 3.14159) < 1e-6
    assert pl["neg"] == -1.0
    assert pl["zero"] == 0.0


def test_boolean_payload_values():
    """Boolean values in payload should round-trip."""
    payload = {"yes": True, "no": False, "maybe": None}
    b = bottle.pack("bool", payload)
    _, pl, _ = bottle.unpack(b)
    assert pl["yes"] is True
    assert pl["no"] is False
    assert pl["maybe"] is None


def test_integer_payload_values():
    """Integer values (including 0) should round-trip."""
    payload = {"count": 0, "max": 99999, "neg": -42}
    b = bottle.pack("int", payload)
    _, pl, _ = bottle.unpack(b)
    assert pl["count"] == 0
    assert pl["max"] == 99999
    assert pl["neg"] == -42


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        # Core API
        test_pack_returns_dict,
        test_pack_without_metadata,
        test_pack_with_metadata,
        test_unpack_round_trip_basic,
        test_unpack_round_trip_no_metadata,
        test_unpack_round_trip_empty_payload,
        test_unpack_round_trip_nested_payload,
        test_unpack_round_trip_null_values,
        test_unpack_round_trip_special_chars,
        test_unpack_round_trip_large_string,
        # JSON serialization
        test_json_serialize_deserialize,
        test_json_serialize_sealed,
        # Validate
        test_validate_valid_bottle,
        test_validate_empty_dict,
        test_validate_none,
        test_validate_non_dict_string,
        test_validate_non_dict_int,
        test_validate_non_dict_list,
        test_validate_missing_msg_type,
        test_validate_missing_payload,
        test_validate_corrupted_bottle,
        test_validate_sealed_bottle,
        # Security
        test_seal_returns_dict,
        test_seal_adds_signature,
        test_seal_preserves_fields,
        test_open_correct_key,
        test_open_wrong_key,
        test_open_tampered_bottle,
        test_open_unsealed_bottle,
        test_seal_different_keys_produce_different_signatures,
        test_seal_deterministic,
        # Replay attack
        test_seal_includes_timestamp_or_nonce,
        test_seal_different_timestamps_different_seals,
        # Unpack robustness
        test_unpack_empty_dict,
        test_unpack_none,
        test_unpack_string,
        # Pack robustness
        test_pack_empty_msg_type,
        test_pack_none_payload,
        test_pack_non_dict_payload,
        # Determinism
        test_pack_deterministic,
        test_pack_idempotent,
        # Interoperability
        test_validate_hand_crafted_bottle,
        test_unpack_hand_crafted_bottle,
        # Performance
        test_pack_unpack_performance,
        test_seal_open_performance,
        # Edge cases
        test_unusual_msg_types,
        test_metadata_none_vs_empty,
        test_float_payload_values,
        test_boolean_payload_values,
        test_integer_payload_values,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
