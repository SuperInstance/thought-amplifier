#!/usr/bin/env python3
"""Independent judge for the bottle.py code competition.
Runs identical tests against all entries and scores blind."""
import json, sys, os, time, traceback, hashlib, hmac

COMPETITION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = ["kimi", "glm", "claude"]

def score_entry(entry_dir):
    """Score one entry on 5 criteria. Returns dict with scores."""
    scores = {"correctness": 0, "elegance": 0, "robustness": 0, "documentation": 0, "performance": 0}
    details = []
    
    bottle_path = os.path.join(entry_dir, "bottle.py")
    if not os.path.exists(bottle_path):
        return {**scores, "total": 0, "details": ["MISSING: bottle.py not found"]}
    
    # Read source for static analysis
    with open(bottle_path) as f:
        source = f.read()
    lines = source.strip().split("\n")
    
    # --- Documentation (10%) ---
    docstrings = source.count('"""')
    has_type_hints = "->" in source
    has_examples = "example" in source.lower() or ">>>" in source
    scores["documentation"] = min(10, docstrings * 0.5 + (5 if has_type_hints else 0) + (2 if has_examples else 0))
    
    # --- Elegance (25%) ---
    line_count = len(lines)
    import_count = sum(1 for l in lines if l.strip().startswith("import ") or l.strip().startswith("from "))
    func_count = sum(1 for l in lines if l.strip().startswith("def "))
    # Fewer lines = more elegant, but too few = probably incomplete
    if 50 <= line_count <= 200:
        scores["elegance"] += 10
    elif line_count < 50:
        scores["elegance"] += 5  # probably incomplete
    else:
        scores["elegance"] += 7
    # Minimal imports = elegant
    scores["elegance"] += min(8, (3 - import_count) * 4) if import_count <= 3 else 2
    # Clean function count
    scores["elegance"] += min(7, func_count * 1.5)
    
    # --- Try importing and running tests ---
    sys.path.insert(0, entry_dir)
    try:
        # Force reimport
        if "bottle" in sys.modules:
            del sys.modules["bottle"]
        import bottle
        
        # --- Correctness (30%) ---
        tests_passed = 0
        tests_total = 0
        
        # Test pack
        tests_total += 1
        try:
            b = bottle.pack("thought", {"text": "hello", "beat": 42})
            assert isinstance(b, dict)
            tests_passed += 1
        except: details.append("FAIL: pack basic")
        
        # Test unpack
        tests_total += 1
        try:
            mt, pl, md = bottle.unpack(b)
            assert mt == "thought"
            assert pl["text"] == "hello"
            tests_passed += 1
        except: details.append("FAIL: unpack basic")
        
        # Test validate
        tests_total += 1
        try:
            assert bottle.validate(b) == True
            assert bottle.validate({}) == False
            assert bottle.validate("not a dict") == False
            tests_passed += 1
        except: details.append("FAIL: validate")
        
        # Test seal/open
        tests_total += 1
        try:
            sealed = bottle.seal(b, "secret_key")
            assert "signature" in sealed or "hmac" in str(sealed).lower()
            result = bottle.open(sealed, "secret_key")
            assert result is not None
            tests_passed += 1
        except: details.append("FAIL: seal/open correct key")
        
        # Test wrong key fails
        tests_total += 1
        try:
            result = bottle.open(sealed, "wrong_key")
            assert result is None
            tests_passed += 1
        except: details.append("FAIL: open wrong key")
        
        # Test metadata
        tests_total += 1
        try:
            b2 = bottle.pack("directive", {"action": "explore"}, {"priority": "high"})
            mt2, pl2, md2 = bottle.unpack(b2)
            assert md2["priority"] == "high"
            tests_passed += 1
        except: details.append("FAIL: metadata")
        
        # --- Robustness (25%) ---
        robust_tests = 0
        robust_total = 0
        
        # Missing fields
        robust_total += 1
        try:
            assert bottle.validate({"type": "x"}) == False  # missing payload
            robust_tests += 1
        except: pass
        
        # None input
        robust_total += 1
        try:
            bottle.validate(None)
            robust_tests += 1  # didn't crash
        except: pass
        
        # Empty payload
        robust_total += 1
        try:
            b3 = bottle.pack("test", {})
            assert bottle.validate(b3) == True
            robust_tests += 1
        except: pass
        
        # Oversized payload
        robust_total += 1
        try:
            big = bottle.pack("test", {"data": "x" * 10000})
            mt3, pl3, md3 = bottle.unpack(big)
            assert len(pl3["data"]) == 10000
            robust_tests += 1
        except: pass
        
        # --- Performance (10%) ---
        perf_start = time.time()
        for _ in range(1000):
            b = bottle.pack("perf", {"n": _})
            bottle.unpack(b)
        perf_ms = (time.time() - perf_start) * 1000
        
        scores["correctness"] = (tests_passed / max(tests_total, 1)) * 30
        scores["robustness"] = (robust_tests / max(robust_total, 1)) * 25
        scores["performance"] = min(10, max(0, 10 - perf_ms / 100))
        
        details.append(f"Correctness: {tests_passed}/{tests_total} tests passed")
        details.append(f"Robustness: {robust_tests}/{robust_total} edge cases handled")
        details.append(f"Performance: {perf_ms:.0f}ms for 1000 pack+unpack cycles")
        details.append(f"Lines: {line_count}, Functions: {func_count}, Imports: {import_count}")
        
    except Exception as e:
        details.append(f"IMPORT ERROR: {e}")
    finally:
        sys.path.pop(0)
        if "bottle" in sys.modules:
            del sys.modules["bottle"]
    
    total = sum(scores.values())
    return {**scores, "total": total, "details": details}

# Main
print("=" * 60)
print("BOTTLE.PY CODE COMPETITION — BLIND JUDGING")
print("=" * 60)

results = {}
for entry in ENTRIES:
    entry_dir = os.path.join(COMPETITION_DIR, entry)
    result = score_entry(entry_dir)
    results[entry] = result

# Print results
print("\n--- RESULTS ---\n")
ranked = sorted(results.items(), key=lambda x: x[1]["total"], reverse=True)
for rank, (name, scores) in enumerate(ranked, 1):
    print(f"#{rank} {name}: {scores['total']:.1f}/100")
    print(f"   Correctness:  {scores['correctness']:.1f}/30")
    print(f"   Elegance:     {scores['elegance']:.1f}/25")
    print(f"   Robustness:   {scores['robustness']:.1f}/25")
    print(f"   Documentation:{scores['documentation']:.1f}/10")
    print(f"   Performance:  {scores['performance']:.1f}/10")
    for d in scores["details"]:
        print(f"   → {d}")
    print()

# Write full results
with open(os.path.join(COMPETITION_DIR, "RESULTS.md"), "w") as f:
    f.write("# Code Competition Results\n\n")
    for name, scores in ranked:
        f.write(f"## {name} — {scores['total']:.1f}/100\n")
        for k, v in scores.items():
            if k != "details":
                f.write(f"- {k}: {v:.1f}\n")
        for d in scores["details"]:
            f.write(f"  - {d}\n")
        f.write("\n")

print("Full results written to competition/RESULTS.md")
