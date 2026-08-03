#!/usr/bin/env python3
"""
EXP5: Replay Determinism Check

Send the same prompt to Granite 3.1 2B 10 times with identical parameters.
Measure variance in output. How deterministic is the production line?

Tests Claim C5 (deterministic replay).
"""

import json, time, requests, math, os, statistics
from datetime import datetime
from difflib import SequenceMatcher

OLLAMA_URL = "http://localhost:11434"
OUTPUT_DIR = "/home/eileen/projects/thought-amplifier/experiments/final"

# Test prompts of varying complexity
TEST_PROMPTS = [
    {
        "name": "simple_observe",
        "prompt": "You are a companion in a Roblox game. The player is building a stone tower. Share a 2-sentence thought about this.",
    },
    {
        "name": "complex_contextual",
        "prompt": "You are a companion in a Roblox game. The player has been building for 30 minutes. It's now sunset. They are near a river and have placed 47 stone blocks in a spiral pattern. Share a 2-sentence thought that connects these observations.",
    },
    {
        "name": "open_creative",
        "prompt": "You are a companion in a Roblox game. The player is doing something interesting. Share a 2-sentence thought.",
    },
]

def generate_thought(prompt, seed=None, temperature=0.8):
    """Generate a thought with controlled parameters."""
    payload = {
        "model": "granite3.1-dense:2b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 80,
            "top_p": 0.9,
            "top_k": 40,
        }
    }
    if seed is not None:
        payload["options"]["seed"] = seed
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {
            "text": data.get("response", "").strip(),
            "eval_count": data.get("eval_count", 0),
            "eval_duration": data.get("eval_duration", 0),
            "total_duration": data.get("total_duration", 0),
        }
    except Exception as e:
        return {"text": f"[ERROR: {e}]", "eval_count": 0, "eval_duration": 0, "total_duration": 0}

def string_similarity(a, b):
    """Compute similarity between two strings (0-1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def run_experiment():
    print("="*60)
    print("  EXP5: Replay Determinism Check")
    print("  Model: Granite 3.1 2B (local Ollama)")
    print("  Protocol: Same prompt × 10 repetitions, 3 prompt types")
    print("  Tests Claim C5 (deterministic replay)")
    print("="*60)
    
    N_REPS = 10
    all_results = {}
    
    for test in TEST_PROMPTS:
        name = test["name"]
        prompt = test["prompt"]
        
        print(f"\n{'='*60}")
        print(f"  TEST: {name}")
        print(f"  N={N_REPS} repetitions, temperature=0.8")
        print(f"{'='*60}")
        
        # Condition A: Same fixed seed (should be deterministic)
        print(f"\n  Condition A: Fixed seed (seed=42)")
        fixed_runs = []
        for i in range(N_REPS):
            print(f"    [{i+1}/{N_REPS}] Generating...", end=" ", flush=True)
            r = generate_thought(prompt, seed=42, temperature=0.8)
            fixed_runs.append(r)
            print(f"({r['eval_count']} tokens, {len(r['text'])} chars)")
            time.sleep(0.2)
        
        # Condition B: Random seed (control - expected to vary)
        print(f"\n  Condition B: Random seed (temperature=0.8)")
        random_runs = []
        for i in range(N_REPS):
            print(f"    [{i+1}/{N_REPS}] Generating...", end=" ", flush=True)
            r = generate_thought(prompt, seed=None, temperature=0.8)
            random_runs.append(r)
            print(f"({r['eval_count']} tokens, {len(r['text'])} chars)")
            time.sleep(0.2)
        
        # Condition C: Temperature=0 (should be maximally deterministic)
        print(f"\n  Condition C: Temperature=0 (greedy decoding)")
        greedy_runs = []
        for i in range(N_REPS):
            print(f"    [{i+1}/{N_REPS}] Generating...", end=" ", flush=True)
            r = generate_thought(prompt, seed=None, temperature=0.0)
            greedy_runs.append(r)
            print(f"({r['eval_count']} tokens, {len(r['text'])} chars)")
            time.sleep(0.2)
        
        # === ANALYSIS ===
        print(f"\n  ANALYSIS: {name}")
        print(f"  {'-'*40}")
        
        analysis = {}
        
        for cond_name, runs in [("fixed_seed", fixed_runs), ("random", random_runs), ("greedy_temp0", greedy_runs)]:
            texts = [r["text"] for r in runs]
            unique = set(texts)
            
            # Pairwise similarity matrix
            sim_matrix = []
            for i in range(len(texts)):
                row = []
                for j in range(len(texts)):
                    row.append(string_similarity(texts[i], texts[j]))
                sim_matrix.append(row)
            
            # Average pairwise similarity (excluding diagonal)
            off_diag_sims = []
            for i in range(len(texts)):
                for j in range(len(texts)):
                    if i != j:
                        off_diag_sims.append(sim_matrix[i][j])
            
            avg_sim = statistics.mean(off_diag_sims) if off_diag_sims else 0
            min_sim = min(off_diag_sims) if off_diag_sims else 0
            max_sim = max(off_diag_sims) if off_diag_sims else 0
            std_sim = statistics.stdev(off_diag_sims) if len(off_diag_sims) > 1 else 0
            
            # Token counts
            token_counts = [r["eval_count"] for r in runs]
            
            analysis[cond_name] = {
                "n_unique": len(unique),
                "n_total": len(texts),
                "exact_match_rate": len(unique) / len(texts) if len(texts) > 0 else 0,
                "avg_pairwise_similarity": avg_sim,
                "min_pairwise_similarity": min_sim,
                "max_pairwise_similarity": max_sim,
                "std_pairwise_similarity": std_sim,
                "mean_tokens": statistics.mean(token_counts) if token_counts else 0,
                "std_tokens": statistics.stdev(token_counts) if len(token_counts) > 1 else 0,
                "texts": texts,
                "sim_matrix": sim_matrix,
            }
            
            print(f"\n    {cond_name}:")
            print(f"      Unique outputs: {len(unique)}/{len(texts)} ({len(unique)/len(texts)*100:.0f}%)")
            print(f"      Avg pairwise similarity: {avg_sim:.4f} ± {std_sim:.4f}")
            print(f"      Range: [{min_sim:.4f}, {max_sim:.4f}]")
            print(f"      Tokens: {statistics.mean(token_counts):.0f} ± {statistics.stdev(token_counts) if len(token_counts)>1 else 0:.0f}")
            
            if len(unique) == 1:
                print(f"      ✅ PERFECTLY DETERMINISTIC")
            elif avg_sim > 0.9:
                print(f"      ⚠️  Near-deterministic (high similarity, minor variations)")
            elif avg_sim > 0.6:
                print(f"      ❌ Moderately variable (shared structure, different content)")
            else:
                print(f"      ❌ Highly variable (low replay fidelity)")
        
        all_results[name] = analysis
    
    # === OVERALL VERDICT ===
    print(f"\n{'='*60}")
    print("  OVERALL DETERMINISM VERDICT (C5)")
    print("="*60)
    
    # Check the greedy condition across all prompts
    greedy_deterministic = all(
        all_results[name]["greedy_temp0"]["n_unique"] == 1
        for name in all_results
    )
    fixed_deterministic = all(
        all_results[name]["fixed_seed"]["n_unique"] == 1
        for name in all_results
    )
    
    if greedy_deterministic:
        print("\n  ✅ Temperature=0 produces byte-identical output across all prompts")
        print("     → C5 (determinism) IS achievable with greedy decoding")
    else:
        # Check how close
        for name in all_results:
            n = all_results[name]["greedy_temp0"]["n_unique"]
            avg = all_results[name]["greedy_temp0"]["avg_pairwise_similarity"]
            print(f"\n  {name}: greedy_temp0 → {n} unique outputs, avg sim={avg:.4f}")
        
        if all(all_results[name]["greedy_temp0"]["avg_pairwise_similarity"] > 0.95 for name in all_results):
            print("\n  ⚠️  Temperature=0 is NEAR-deterministic (>95% similarity) but not byte-identical")
            print("     → C5 is approximately achievable, minor platform-level nondeterminism exists")
        else:
            print("\n  ❌ Temperature=0 does NOT produce deterministic output")
            print("     → C5 (determinism) CANNOT be guaranteed even with greedy decoding")
    
    if fixed_deterministic:
        print("\n  ✅ Fixed seed produces byte-identical output across all prompts")
        print("     → C5 IS achievable with seed control")
    else:
        print("\n  ⚠️  Fixed seed does NOT produce identical output (Ollama/llama.cpp seed limitations)")
    
    # Implications for .bottle replay
    print(f"\n{'='*60}")
    print("  IMPLICATIONS FOR .BOTTLE REPLAY")
    print("="*60)
    
    avg_greedy_sim = statistics.mean([
        all_results[name]["greedy_temp0"]["avg_pairwise_similarity"]
        for name in all_results
    ])
    avg_random_sim = statistics.mean([
        all_results[name]["random"]["avg_pairwise_similarity"]
        for name in all_results
    ])
    
    print(f"\n  Average pairwise similarity across all prompt types:")
    print(f"    Temperature=0:  {avg_greedy_sim:.4f}")
    print(f"    Temperature=0.8: {avg_random_sim:.4f}")
    
    print(f"\n  For .bottle replay to work, the production line must produce identical")
    print(f"  output when replayed. With temperature=0, similarity is {avg_greedy_sim:.1%}.")
    
    if avg_greedy_sim >= 0.99:
        print(f"  → Byte-exact replay is PRACTICAL with temperature=0.")
        print(f"  → Minor nondeterminism from floating-point/GPU scheduling may exist.")
    elif avg_greedy_sim >= 0.90:
        print(f"  → Near-exact replay is achievable; exact replay needs seed pinning + temp=0.")
        print(f"  → The .bottle ledger should record SEEDS, not just prompts.")
    else:
        print(f"  → Byte-exact replay is NOT achievable with current setup.")
        print(f"  → The .bottle ledger must store full outputs, not just prompts.")
    
    # Save
    output = {
        "experiment": "EXP5: Replay Determinism Check",
        "timestamp": datetime.now().isoformat(),
        "model": "granite3.1-dense:2b (local Ollama)",
        "n_reps": N_REPS,
        "conditions": ["fixed_seed_42", "random_temp0.8", "greedy_temp0"],
        "results": all_results,
        "overall_verdict": {
            "greedy_deterministic": greedy_deterministic,
            "fixed_seed_deterministic": fixed_deterministic,
            "avg_greedy_similarity": avg_greedy_sim,
            "avg_random_similarity": avg_random_sim,
        },
    }
    
    outfile = os.path.join(OUTPUT_DIR, "EXP5_DETERMINISM_RESULTS.json")
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full data saved to: {outfile}")
    
    return output

if __name__ == "__main__":
    run_experiment()
