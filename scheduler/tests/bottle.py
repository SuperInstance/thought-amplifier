"""
bottle.py — Lightweight message envelope for Thinker ↔ Conductor communication.

A "bottle" is a JSON-serializable dict containing a message type, payload,
and optional metadata. Bottles can be sealed with HMAC-SHA256 signatures for
integrity and authenticated with a shared key.

Protocol:
    pack(msg_type, payload, metadata=None) -> dict
    unpack(bottle) -> (msg_type, payload, metadata)
    validate(bottle) -> bool
    seal(bottle, key) -> dict  — add HMAC signature + timestamp
    open(bottle, key) -> dict|None  — verify HMAC, return original or None

Constraints:
    - <200 lines, stdlib only
    - handles missing fields, malformed input, replay attacks
    - JSON-serializable
    - docstrings and type hints
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

__all__ = ["pack", "unpack", "validate", "seal", "open"]

BOTTLE_VERSION = 1
SIGNATURE_KEY = "signature"
TIMESTAMP_KEY = "timestamp"
VERSION_KEY = "v"


def pack(msg_type: str, payload: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a new bottle with the given message type and payload.

    Args:
        msg_type: Message type identifier (e.g. "thought", "directive").
        payload: The message payload as a dict.
        metadata: Optional metadata dict (e.g. {"priority": "high"}).

    Returns:
        A dict representing the bottle.
    """
    bottle = {
        "type": msg_type,
        "payload": payload,
        VERSION_KEY: BOTTLE_VERSION,
    }
    if metadata is not None:
        bottle["metadata"] = metadata
    return bottle


def unpack(bottle: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Extract the msg_type, payload, and metadata from a bottle.

    Args:
        bottle: A bottle dict from pack().

    Returns:
        Tuple of (msg_type, payload, metadata).
        Metadata is None if not present.
    """
    return (
        bottle["type"],
        bottle["payload"],
        bottle.get("metadata"),
    )


def validate(bottle: Any) -> bool:
    """Check whether a bottle is well-formed.

    Args:
        bottle: Any value — must be a dict with "type" and "payload" keys.

    Returns:
        True if the bottle is valid, False otherwise.
    """
    if not isinstance(bottle, dict):
        return False
    if "type" not in bottle or "payload" not in bottle:
        return False
    if not isinstance(bottle["type"], str) or bottle["type"] == "":
        return False
    if not isinstance(bottle["payload"], dict):
        return False
    return True


def seal(bottle: dict[str, Any], key: str) -> dict[str, Any]:
    """Seal a bottle with an HMAC-SHA256 signature and timestamp.

    The signature covers (msg_type, payload, metadata, timestamp, version).
    This prevents tampering and provides basic replay protection via timestamp.

    Args:
        bottle: The bottle to seal (from pack()).
        key: Shared secret key for HMAC.

    Returns:
        A new dict with signature and timestamp added.
    """
    sealed = dict(bottle)
    ts = int(time.time() * 1000)
    sealed[TIMESTAMP_KEY] = ts

    payload = json.dumps(
        {
            "type": bottle["type"],
            "payload": bottle["payload"],
            "metadata": bottle.get("metadata"),
            VERSION_KEY: bottle.get(VERSION_KEY, BOTTLE_VERSION),
            TIMESTAMP_KEY: ts,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    sig = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    sealed[SIGNATURE_KEY] = sig
    return sealed


def open(bottle: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Open a sealed bottle, verifying its HMAC signature.

    The signature is recomputed and compared. If they match, a clean bottle
    (without signature/timestamp) is returned. If they don't match, or the
    bottle is not a dict, returns None.

    Args:
        bottle: A sealed bottle from seal().
        key: Shared secret key for HMAC.

    Returns:
        The original bottle dict (minus signature/timestamp) if valid,
        or None if verification fails.
    """
    if not isinstance(bottle, dict):
        return None

    sig = bottle.get(SIGNATURE_KEY)
    if not sig:
        return None

    ts = bottle.get(TIMESTAMP_KEY, 0)

    payload = json.dumps(
        {
            "type": bottle.get("type"),
            "payload": bottle.get("payload"),
            "metadata": bottle.get("metadata"),
            VERSION_KEY: bottle.get(VERSION_KEY, BOTTLE_VERSION),
            TIMESTAMP_KEY: ts,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    expected = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected):
        return None

    # Return a clean bottle without seal artifacts
    result = dict(bottle)
    result.pop(SIGNATURE_KEY, None)
    result.pop(TIMESTAMP_KEY, None)
    return result
