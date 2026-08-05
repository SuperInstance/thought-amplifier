"""
Tests for the Cognitive Router.

Covers:
  1. Router correctly identifies KNOWN-KNOWNs (reflex hits)
  2. Router correctly identifies KNOWN-UNKNOWNs (local model sufficient)
  3. Router correctly identifies UNKNOWN-UNKNOWNs (cascade to cloud)
  4. Boundary shifts over time as reflexes accumulate
  5. Cost tracking accurate
  6. Model selection optimal for given constraints
  7. Confidence assessment signals work correctly
  8. Reflex write-back (Pincher pattern)
  9. Escape hatch prevents reflex blindness
  10. Calibration tracking
"""

import sys
import os
import time
import math

# Add the router package's parent to path so 'router' resolves as a package
_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARENT_OF_PARENT = os.path.dirname(_PARENT)
sys.path.insert(0, _PARENT_OF_PARENT)

from router.router import (
    CognitiveRouter,
    RouteDecision,
    EpistemicState,
    RouteTarget,
    ReflexCache,
    ReflexEntry,
)
from router.confidence import (
    ConfidenceAssessor,
    analyze_complexity,
    best_model_for_task,
    SuccessHistory,
    NoveltyDetector,
    MODEL_CAPABILITY,
)
from router.model_selector import (
    LocalModelSelector,
    GRANITE,
    QWEN,
    ModelProfile,
)
from router.cloud_cascade import (
    CloudCascade,
    CloudBudget,
    estimate_cloud_cost,
    DEEPSEEK_V3,
    QWEN_CODER_480B,
    HERMES_405B,
    CF_LLAMA_8B,
)
from router.boundary_tracker import BoundaryTracker


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0


def test(name: str):
    """Decorator for test functions."""
    test.__test__ = False  # tell pytest not to collect this decorator
    def decorator(fn):
        def wrapper():
            global PASS, FAIL
            try:
                fn()
                PASS += 1
                print(f"  ✓ {name}")
            except AssertionError as e:
                FAIL += 1
                print(f"  ✗ {name}: {e}")
            except Exception as e:
                FAIL += 1
                print(f"  ✗ {name}: {type(e).__name__}: {e}")
        wrapper._is_test = True
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# 1. Reflex Cache (KNOWN-KNOWN)
# ---------------------------------------------------------------------------

@test("reflex cache stores and retrieves")
def test_reflex_store_retrieve():
    cache = ReflexCache(confidence_threshold=0.85)
    cache.store("What is 2+2?", "4", confidence=0.90)
    hit = cache.check("What is 2+2?")
    assert hit is not None, "Expected reflex hit"
    assert hit.text == "4"
    assert hit.confidence >= 0.85


@test("reflex cache misses on unknown prompts")
def test_reflex_miss():
    cache = ReflexCache()
    hit = cache.check("What is the meaning of life?")
    assert hit is None, "Should not have a reflex for unknown prompt"


@test("reflex cache respects confidence threshold")
def test_reflex_low_confidence():
    cache = ReflexCache(confidence_threshold=0.85)
    cache.store("test prompt", "test answer", confidence=0.50)
    hit = cache.check("test prompt")
    assert hit is None, "Low-confidence reflex should not hit"


@test("reflex confidence updates on success (asymmetric)")
def test_reflex_confidence_success():
    cache = ReflexCache()
    cache.store("prompt1", "answer1", confidence=0.50)
    # Record success: +0.05 * (1 - 0.50) = +0.025
    cache.update_confidence("prompt1", success=True)
    entry = cache._cache[cache._hash("prompt1")]
    assert abs(entry.confidence - 0.525) < 0.001, f"Expected 0.525, got {entry.confidence}"


@test("reflex confidence updates on failure (asymmetric)")
def test_reflex_confidence_failure():
    cache = ReflexCache()
    cache.store("prompt2", "answer2", confidence=0.80)
    # Record failure: -0.10 * 0.80 = -0.08
    cache.update_confidence("prompt2", success=False)
    entry = cache._cache[cache._hash("prompt2")]
    assert abs(entry.confidence - 0.72) < 0.001, f"Expected 0.72, got {entry.confidence}"


@test("reflex confidence clamps to [0.05, 0.95]")
def test_reflex_clamp():
    cache = ReflexCache()
    cache.store("prompt3", "answer3", confidence=0.95)
    # Success at 0.95: +0.05 * (1 - 0.95) = +0.0025 → 0.9525 → clamp 0.95
    for _ in range(100):
        cache.update_confidence("prompt3", success=True)
    entry = cache._cache[cache._hash("prompt3")]
    assert entry.confidence <= 0.95, f"Should clamp at 0.95, got {entry.confidence}"

    # Failure clamp
    cache.store("prompt4", "answer4", confidence=0.10)
    for _ in range(100):
        cache.update_confidence("prompt4", success=False)
    entry = cache._cache[cache._hash("prompt4")]
    assert entry.confidence >= 0.05, f"Should clamp at 0.05, got {entry.confidence}"


@test("reflex escape hatch triggers after max consecutive uses")
def test_reflex_escape_hatch():
    cache = ReflexCache(confidence_threshold=0.85)
    cache.store("repeated", "cached answer", confidence=0.95)
    # Set low escape hatch
    entry = cache._cache[cache._hash("repeated")]
    entry.max_consecutive_uses = 3

    # First 3 hits should work
    for i in range(3):
        hit = cache.check("repeated")
        assert hit is not None, f"Hit {i+1} should succeed"

    # 4th hit should trigger escape hatch (returns None, resets)
    hit = cache.check("repeated")
    assert hit is None, "4th hit should trigger escape hatch"

    # After reset, it should work again
    hit = cache.check("repeated")
    assert hit is not None, "Should work again after escape hatch reset"


# ---------------------------------------------------------------------------
# 2. Router routing decisions (three epistemic states)
# ---------------------------------------------------------------------------

@test("router returns KNOWN-KNOWN for cached reflex")
def test_route_known_known():
    router = CognitiveRouter()
    router.reflex_cache.store("hello", "world", confidence=0.95)
    decision = router.route("hello")
    assert decision.target == RouteTarget.REFLEX
    assert decision.epistemic_state == EpistemicState.KNOWN_KNOWN
    assert decision.reflex_text == "world"
    assert decision.cost_estimate == 0.0
    assert decision.latency_expectation_ms < 1.0


@test("router returns KNOWN-UNKNOWN for familiar analytical task")
def test_route_known_unknown():
    router = CognitiveRouter()
    # An analytical prompt with moderate complexity
    # The confidence assessor should rate this as handleable locally
    decision = router.route("Compare the advantages of two approaches.")
    assert decision.target == RouteTarget.LOCAL, \
        f"Expected LOCAL, got {decision.target} ({decision.reasoning})"
    assert decision.epistemic_state == EpistemicState.KNOWN_UNKNOWN
    assert decision.model in ("granite3.1-dense:2b", "qwen2.5:0.5b")
    assert decision.cost_estimate == 0.0


@test("router returns UNKNOWN-UNKNOWN for high-novelty complex prompts")
def test_route_unknown_unknown():
    router = CognitiveRouter()
    # A very complex, novel prompt that local models can't handle.
    # Includes multi-step reasoning, nested questions, and dense
    # domain-specific vocabulary — the kind of problem that needs
    # a larger model of understanding to even shape correctly.
    prompt = (
        "Design a complete distributed consensus algorithm. "
        "First, how would you handle byzantine faults when network "
        "partitions occur across 1000 nodes? Then, what game-theoretic "
        "incentive mechanisms ensure honesty? How do you prove safety "
        "with formal verification? Finally, what is the optimal throughput "
        "under adversarial conditions, and why does this matter?"
    )
    decision = router.route(prompt)
    # This should be complex enough to cascade to cloud
    assert decision.target == RouteTarget.CLOUD, \
        f"Expected CLOUD for very complex prompt, got {decision.target} ({decision.reasoning})"
    assert decision.epistemic_state == EpistemicState.UNKNOWN_UNKNOWN
    assert decision.should_compile_reflex is True


@test("forced routing overrides work correctly")
def test_force_route():
    router = CognitiveRouter()
    d1 = router.route("test", force_target=RouteTarget.LOCAL)
    assert d1.target == RouteTarget.LOCAL

    d2 = router.route("test", force_target=RouteTarget.CLOUD)
    assert d2.target == RouteTarget.CLOUD

    d3 = router.route("test", force_target=RouteTarget.REFLEX)
    assert d3.target == RouteTarget.REFLEX


# ---------------------------------------------------------------------------
# 3. Confidence Assessment
# ---------------------------------------------------------------------------

@test("complexity analyzer classifies task types")
def test_complexity_classification():
    c1 = analyze_complexity("Compare option A with option B")
    assert c1.task_type == "analytical", f"Got {c1.task_type}"

    c2 = analyze_complexity("Write a poem about the ocean")
    assert c2.task_type == "creative", f"Got {c2.task_type}"

    c3 = analyze_complexity("How do I fix this error in my code?")
    assert c3.task_type in ("problem_solving", "code"), f"Got {c3.task_type}"


@test("complexity analyzer measures word count and depth")
def test_complexity_metrics():
    simple = analyze_complexity("Hello")
    complex_prompt = analyze_complexity(
        "First, analyze the root causes. Then, design a solution. "
        "Finally, implement it step by step. What are the tradeoffs?"
    )
    assert simple.word_count < complex_prompt.word_count
    assert simple.complexity < complex_prompt.complexity
    assert complex_prompt.has_multi_step


@test("confidence assessor returns signals")
def test_confidence_signals():
    assessor = ConfidenceAssessor()
    result = assessor.assess("Explain how photosynthesis works")
    assert "confidence" in result
    assert "signals" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert "task_type" in result
    assert "capability" in result["signals"]
    assert "novelty" in result["signals"]


@test("confidence higher for familiar tasks, lower for novel")
def test_confidence_novelty_effect():
    assessor = ConfidenceAssessor()
    # Observe the same type many times
    for _ in range(20):
        assessor.assess("Compare A and B analytically", task_type_override(None) if False else "analytical")

    # Now assess a similar prompt — novelty should be low, confidence higher
    result_familiar = assessor.assess("Compare X and Y analytically")

    # Fresh assessor — everything is novel
    fresh = ConfidenceAssessor()
    result_novel = fresh.assess("Compare X and Y analytically")

    # The familiar one should have higher novelty signal (lower novelty_raw)
    assert result_familiar["signals"]["novelty_raw"] <= result_novel["signals"]["novelty_raw"], \
        "Familiar prompt should have lower novelty"


@test("success history tracks EMA per task type")
def test_success_history():
    hist = SuccessHistory()
    # Below min observations → returns None
    assert hist.success_rate("analytical") is None
    for _ in range(10):
        hist.record("analytical", success=True, quality=0.8)
    rate = hist.success_rate("analytical")
    assert rate is not None
    assert rate > 0.5, f"Expected high success rate, got {rate}"


@test("best model for task returns correct model")
def test_best_model():
    # Granite should be best for analytical
    model, score = best_model_for_task("analytical")
    assert model == "granite3.1-dense:2b", f"Expected Granite, got {model}"
    assert score > 0.7

    # Qwen should be best for creative
    model, score = best_model_for_task("creative")
    assert model == "qwen2.5:0.5b", f"Expected Qwen, got {model}"
    assert score > 0.6


# ---------------------------------------------------------------------------
# 4. Model Selection
# ---------------------------------------------------------------------------

@test("model selector picks Granite for analytical tasks")
def test_select_granite_analytical():
    selector = LocalModelSelector()
    assessment = {"task_type": "analytical", "confidence": 0.7}
    model = selector.select("Compare two approaches", assessment)
    assert model.name == "granite3.1-dense:2b", \
        f"Expected Granite, got {model.name}"


@test("model selector picks Qwen for creative tasks")
def test_select_qwen_creative():
    selector = LocalModelSelector()
    assessment = {"task_type": "creative", "confidence": 0.7}
    model = selector.select("Write a poem", assessment)
    assert model.name == "qwen2.5:0.5b", \
        f"Expected Qwen, got {model.name}"


@test("model selector respects character consistency requirement")
def test_select_character_consistency():
    selector = LocalModelSelector()
    assessment = {"task_type": "creative", "confidence": 0.7}
    model = selector.select(
        "Write a story",
        assessment,
        context={"requires_character": True}
    )
    assert model.name == "granite3.1-dense:2b", \
        "Character consistency should force Granite"


@test("model selector prefers Qwen for URGENT non-high-quality tasks")
def test_select_urgent():
    selector = LocalModelSelector()
    assessment = {"task_type": "general", "confidence": 0.6}
    model = selector.select(
        "Quick question",
        assessment,
        context={"urgency": "URGENT", "quality_requirement": "low"}
    )
    assert model.name == "qwen2.5:0.5b", \
        f"URGENT + low quality should prefer Qwen, got {model.name}"


@test("model selector learns from outcomes")
def test_model_learning():
    selector = LocalModelSelector()
    # Initially Granite is better for analytical
    assessment = {"task_type": "analytical", "confidence": 0.7}
    model1 = selector.select("Compare two things", assessment)
    assert model1.name == "granite3.1-dense:2b"

    # Record many Granite failures and Qwen successes on analytical
    for _ in range(50):
        selector.record_outcome("analytical", "granite3.1-dense:2b",
                                success=False, quality=0.2)
        selector.record_outcome("analytical", "qwen2.5:0.5b",
                                success=True, quality=0.7)

    # Now Qwen should be preferred (or at least competitive)
    scores = selector.get_model_scores("analytical")
    # The gap should have narrowed significantly
    g_score = scores.get("granite3.1-dense:2b", 0.5)
    q_score = scores.get("qwen2.5:0.5b", 0.5)
    assert q_score > g_score * 0.8, \
        f"Qwen should have narrowed the gap: G={g_score:.3f} Q={q_score:.3f}"


# ---------------------------------------------------------------------------
# 5. Cloud Cascade
# ---------------------------------------------------------------------------

@test("cloud cascade selects DeepSeek for reasoning")
def test_cloud_reasoning():
    cascade = CloudCascade()
    assessment = {"task_type": "analytical", "confidence": 0.3}
    sel = cascade.select_model(
        "Analyze the tradeoffs of distributed systems",
        assessment
    )
    assert sel.provider in ("deepseek", "deepinfra"), \
        f"Expected reasoning model, got {sel.provider}/{sel.name}"


@test("cloud cascade selects Qwen-Coder for code")
def test_cloud_code():
    cascade = CloudCascade()
    assessment = {"task_type": "code", "confidence": 0.3}
    sel = cascade.select_model(
        "Write a Python function to sort a binary tree",
        assessment
    )
    assert "Coder" in sel.name or "coder" in sel.name.lower(), \
        f"Expected coder model, got {sel.name}"


@test("cloud cascade selects Hermes for creative")
def test_cloud_creative():
    cascade = CloudCascade()
    assessment = {"task_type": "creative", "confidence": 0.3}
    sel = cascade.select_model(
        "Write a character backstory for a fantasy novel",
        assessment
    )
    assert "Hermes" in sel.name, \
        f"Expected Hermes for creative, got {sel.name}"


@test("cloud cost estimation is reasonable")
def test_cloud_cost():
    cost = estimate_cloud_cost(DEEPSEEK_V3, "short prompt", 500)
    assert cost > 0
    assert cost < 0.01  # should be very cheap

    long_prompt = "x " * 1000
    cost_long = estimate_cloud_cost(DEEPSEEK_V3, long_prompt, 2000)
    assert cost_long > cost  # longer should cost more


@test("cloud budget exhaustion falls back to free model")
def test_budget_exhaustion():
    budget = CloudBudget(daily_budget_usd=0.001)
    budget.spend(0.001)  # exhaust
    assert budget.is_exhausted()

    cascade = CloudCascade(budget=budget)
    assessment = {"task_type": "analytical", "confidence": 0.3}
    sel = cascade.select_model("complex reasoning task", assessment)
    assert sel.estimated_cost == 0.0, \
        "Exhausted budget should fall back to free model"
    assert "cloudflare" in sel.provider or sel.name.startswith("@"), \
        f"Expected Cloudflare fallback, got {sel.provider}/{sel.name}"


# ---------------------------------------------------------------------------
# 6. Boundary Tracker
# ---------------------------------------------------------------------------

@test("boundary tracker records decisions")
def test_boundary_records():
    tracker = BoundaryTracker()
    router = CognitiveRouter(boundary_tracker=tracker)

    router.route("test prompt")
    assert len(tracker._records) == 1

    router.route("another prompt")
    assert len(tracker._records) == 2


@test("boundary state distribution sums to 1.0")
def test_boundary_distribution():
    tracker = BoundaryTracker()
    router = CognitiveRouter(boundary_tracker=tracker)

    # Generate some traffic
    router.reflex_cache.store("cached", "answer", confidence=0.95)
    router.route("cached")  # KNOWN-KNOWN
    router.route("Compare A and B")  # likely KNOWN-UNKNOWN
    router.route("complex novel task")  # might be either

    dist = tracker.state_distribution(window_s=60)
    total = sum(dist.values())
    assert abs(total - 1.0) < 0.01 or total == 0.0, \
        f"Distribution should sum to 1.0, got {total}"


@test("boundary shifts as reflexes accumulate")
def test_boundary_shift():
    """
    The profound test: as we accumulate reflexes, the ratio of
    KNOWN-KNOWN should increase. This is the production line
    getting better at producing value.
    """
    router = CognitiveRouter()

    # Initially, everything is UNKNOWN or local
    report_0 = router.get_boundary_report()
    kk_ratio_0 = report_0["state_distribution_1h"]["KNOWN-KNOWN"]

    # Compile a bunch of reflexes
    for i in range(20):
        prompt = f"question number {i}"
        router.reflex_cache.store(prompt, f"answer {i}", confidence=0.90)

    # Now route those same prompts — should all be KNOWN-KNOWN
    for i in range(20):
        router.route(f"question number {i}")

    report_1 = router.get_boundary_report()
    kk_ratio_1 = report_1["state_distribution_1h"]["KNOWN-KNOWN"]

    assert kk_ratio_1 > kk_ratio_0, \
        f"KNOWN-KNOWN ratio should increase ({kk_ratio_0} → {kk_ratio_1})"


@test("routing accuracy is tracked")
def test_routing_accuracy():
    tracker = BoundaryTracker()
    router = CognitiveRouter(boundary_tracker=tracker)

    # Route something and record a good outcome
    decision = router.route("Compare two options analytically")
    router.record_outcome(
        "Compare two options analytically",
        decision,
        success=True,
        quality=0.8,
    )

    accuracy = tracker.routing_accuracy(window_s=60)
    assert accuracy is not None, "Should have accuracy data"
    assert accuracy == 1.0, f"Expected 100% accuracy, got {accuracy}"


@test("cost trend tracks free ratio")
def test_cost_trend():
    router = CognitiveRouter()

    # All local/reflex → all free
    router.reflex_cache.store("free1", "ans1", confidence=0.90)
    router.route("free1")
    router.route("Compare A and B")

    report = router.get_boundary_report()
    cost = report["cost_trend_1h"]
    assert cost["free_ratio"] >= 0.5, \
        f"Expected >=50% free, got {cost['free_ratio']}"


# ---------------------------------------------------------------------------
# 7. Pincher Write-Back (reflex compilation from cloud)
# ---------------------------------------------------------------------------

@test("cloud response compiles into reflex")
def test_pincher_writeback():
    router = CognitiveRouter()

    # Route a complex prompt to cloud (force to ensure it goes there)
    prompt = "Design a Byzantine fault tolerant consensus protocol"
    decision = router.route(prompt, force_target=RouteTarget.CLOUD)
    assert decision.target == RouteTarget.CLOUD

    # Simulate a successful cloud response
    router.record_outcome(
        prompt,
        decision,
        success=True,
        quality=0.85,
        response_text="Use Practical Byzantine Fault Tolerance (pBFT)...",
    )

    # Now the same prompt should be a reflex hit
    decision2 = router.route(prompt)
    assert decision2.target == RouteTarget.REFLEX, \
        f"After write-back, should be KNOWN-KNOWN, got {decision2.target}"
    assert "Byzantine" in decision2.reflex_text


@test("failed cloud response does not compile into reflex")
def test_failed_writeback():
    router = CognitiveRouter()

    prompt = "Some very complex unknown question"
    decision = router.route(prompt)

    # Check if it went to cloud; if not, force it
    if decision.target != RouteTarget.CLOUD:
        decision = router.route(prompt, force_target=RouteTarget.CLOUD)

    router.record_outcome(
        prompt,
        decision,
        success=False,
        quality=0.1,
        response_text="garbage output",
    )

    # Should NOT be a reflex
    decision2 = router.route(prompt)
    assert decision2.target != RouteTarget.REFLEX, \
        "Failed cloud response should not compile into reflex"


# ---------------------------------------------------------------------------
# 8. Full System Integration
# ---------------------------------------------------------------------------

@test("full router stats are comprehensive")
def test_router_stats():
    router = CognitiveRouter()

    # Generate some traffic
    router.reflex_cache.store("cached", "answer", confidence=0.90)
    router.route("cached")
    router.route("Explain something")
    router.route("Design a complex system with many constraints")

    stats = router.get_stats()
    assert "reflex_cache" in stats
    assert "boundary" in stats
    assert "thresholds" in stats
    assert stats["reflex_cache"]["total_reflexes"] >= 1


@test("boundary report includes task breakdown")
def test_boundary_task_breakdown():
    tracker = BoundaryTracker()
    router = CognitiveRouter(boundary_tracker=tracker)

    router.route("Compare A and B analytically")
    router.route("Write a creative story")
    router.route("How do I code this?")

    report = tracker.report()
    assert "task_breakdown_1h" in report
    assert len(report["task_breakdown_1h"]) > 0


@test("reflex growth rate tracks write-backs")
def test_reflex_growth():
    router = CognitiveRouter()

    initial_rate = router.get_boundary_report()["reflex_growth_rate_per_h"]

    # Generate some cloud responses that compile into reflexes
    for i in range(5):
        prompt = f"Complex reasoning task number {i} with novel constraints"
        decision = router.route(prompt, force_target=RouteTarget.CLOUD)
        router.record_outcome(
            prompt, decision,
            success=True, quality=0.8,
            response_text=f"Answer {i}",
        )

    final_rate = router.get_boundary_report()["reflex_growth_rate_per_h"]
    assert final_rate > initial_rate, \
        f"Reflex growth rate should increase ({initial_rate} → {final_rate})"


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

def run_all():
    global PASS, FAIL
    print("\n=== Cognitive Router Tests ===\n")

    # Find and run all test functions
    g = dict(globals())
    tests = [
        (name, fn) for name, fn in sorted(g.items())
        if callable(fn) and getattr(fn, "_is_test", False)
    ]
    for _, fn in tests:
        fn()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    if FAIL > 0:
        print("STATUS: FAILED")
        return 1
    else:
        print("STATUS: ALL PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(run_all())
