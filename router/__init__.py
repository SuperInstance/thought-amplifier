"""
Cognitive Router — Epistemic State Detection and Request Routing

The router decides HOW to handle each inference request by detecting
which of three epistemic states the request falls into:

  KNOWN-KNOWN    — reflex hit, <1ms, $0
  KNOWN-UNKNOWN  — local model sufficient, 1-3s, $0
  UNKNOWN-UNKNOWN — cascade to cloud, 10-30s, paid

Over time, cloud solutions compile into reflexes and the boundary evolves.

The router only produces routing decisions and tracks metrics; it does
not execute inference or persist state across restarts.

Modules:
  router.py          — core routing decision
  confidence.py      — local confidence assessment
  model_selector.py  — pick the right local model
  cloud_cascade.py   — cloud escalation path
  boundary_tracker.py — track the evolving knowledge frontier
"""

from .router import CognitiveRouter, RouteDecision, EpistemicState
from .confidence import ConfidenceAssessor
from .model_selector import LocalModelSelector
from .cloud_cascade import CloudCascade
from .boundary_tracker import BoundaryTracker

__all__ = [
    "CognitiveRouter",
    "RouteDecision",
    "EpistemicState",
    "ConfidenceAssessor",
    "LocalModelSelector",
    "CloudCascade",
    "BoundaryTracker",
]
