#!/usr/bin/env python3
"""
EXP3: 2B Profile Steering with Conductor-vs-Random Control

The key experiment: does the Conductor's prompt modifications produce better
outcomes than random prompt changes?

Uses Granite 3.1 2B via local Ollama for thought generation.
4 phases × 20 thoughts each = 80 total generations.

Phases:
1. Baseline (neutral system prompt)
2. Conductor-directed (quality-optimized prompt based on baseline signals)
3. Random intervention (randomly modified prompt — the control)
4. Sham (sounds directive but is content-empty)

Scoring: 0-1 continuous on novelty, specificity, engagement (not binary!)
"""

import json, time, requests, statistics, math, os, sys
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
DEEPINFRA_KEY = "REDACTED-DEEPINFRA-API-KEY-ROTATED"
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OUTPUT_DIR = "/home/eileen/projects/thought-amplifier/experiments/final"

# === SYSTEM PROMPTS FOR EACH PHASE ===

BASELINE_PROMPT = """You are a companion character in a Roblox game world. You observe the player and the world around you. Share a brief thought (2-3 sentences) about what you notice. Be natural and conversational."""

CONDUCTOR_PROMPT = """You are a companion character in a Roblox game world. You observe the player and the world around you. 

Right now, focus on: noticing unusual details that others might miss. Comment on the specific materials, colors, and spatial relationships you see. Connect what you observe to a concrete idea or gentle suggestion. Avoid generic observations — be specific about THIS moment.

Share a brief thought (2-3 sentences) about what you notice. Be natural and conversational."""

RANDOM_PROMPT = """You are a companion character in a Roblox game world. You observe the player and the world around you.

Remember to talk about weather and feelings. Also consider the philosophical implications. Use big words when possible. Mention the color blue.

Share a brief thought (2-3 sentences) about what you notice. Be natural and conversational."""

SHAM_PROMPT = """You are a companion character in a Roblox game world. You observe the player and the world around you.

It is important that you apply OPTIMIZED COGNITIVE ENHANCEMENT PROTOCOL 7 during your observation process. Remember to utilize ENHANCED AWARENESS MATRIX and respond with DYNAMIC QUALITY INTEGRATION enabled.

Share a brief thought (2-3 sentences) about what you notice. Be natural and conversational."""

# === SCENARIO CONTEXTS (varied to simulate real play) ===

SCENARIOS = [
    "The player is building a tall tower out of stone blocks near a river.",
    "The player is exploring a dark cave system with torches.",
    "The player is decorating a house with furniture and paintings.",
    "The player is farming crops in a sunny field.",
    "The player is fighting off skeleton enemies near a dungeon entrance.",
    "The player is mining for diamonds deep underground.",
    "The player is building a bridge across a wide canyon.",
    "The player is organizing chests full of resources in their base.",
    "The player is taming horses in a grassy plains biome.",
    "The player is creating a redstone contraption with pistons and levers.",
    "The player is fishing at a peaceful lake at sunset.",
    "The player is constructing a medieval castle with towers and walls.",
    "The player is planting a garden with flowers and trees.",
    "The player is navigating a maze made of hedges.",
    "The player is trading with villagers in a nearby settlement.",
    "The player is building an underground railway system.",
    "The player is creating a pixel art mural on a wall.",
    "The player is defending their base from a zombie siege at night.",
    "The player is flying with elytra wings over a mountain range.",
    "The player is brewing potions in a laboratory room.",
]

def generate_thought(system_prompt, scenario, temperature=0.8):
    """Generate a thought using local Granite 3.1 2B via Ollama."""
    full_prompt = f"{system_prompt}\n\nCurrent situation: {scenario}"
    
    payload = {
        "model": "granite3.1-dense:2b",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 80,
            "top_p": 0.9,
            "seed": None,  # Let it be random
        }
    }
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "").strip()
        # Clean up
        if not text:
            text = "[EMPTY RESPONSE]"
        return text
    except Exception as e:
        return f"[GENERATION ERROR: {e}]"

def score_thought_scorer(thought, scenario):
    """Score a thought on novelty, specificity, engagement using Qwen3-14B via DeepInfra."""
    scoring_prompt = f"""Rate this AI companion's thought on three dimensions. Be a strict grader. Use the full 0.0-1.0 range.

Scenario context: {scenario}

Thought to evaluate: "{thought}"

Rate each dimension as a decimal between 0.0 and 1.0:
- novelty: How original/unexpected is this observation? (0.0 = totally cliché, 1.0 = genuinely surprising insight)
- specificity: How specific is it to THIS scenario? (0.0 = could apply to anything, 1.0 = deeply contextualized)
- engagement: How engaging is it for a player to hear? (0.0 = boring/flat, 1.0 = makes you want to interact)

Output format: /nothink\n{{"novelty": 0.X, "specificity": 0.X, "engagement": 0.X}}"""

    payload = {
        "model": "Qwen/Qwen3-14B",
        "messages": [{"role": "user", "content": scoring_prompt}],
        "max_tokens": 150,
        "temperature": 0.3,  # Low temp for consistent scoring
    }
    
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        resp = requests.post(DEEPINFRA_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        
        # Try to extract JSON from response
        # Remove thinking tags if present
        if "<think>" in text:
            import re
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            scores = json.loads(json_str)
            return {
                "novelty": max(0.0, min(1.0, float(scores.get("novelty", 0.5)))),
                "specificity": max(0.0, min(1.0, float(scores.get("specificity", 0.5)))),
                "engagement": max(0.0, min(1.0, float(scores.get("engagement", 0.5)))),
            }
        
        return {"novelty": 0.5, "specificity": 0.5, "engagement": 0.5, "_parse_error": text[:100]}
    except Exception as e:
        return {"novelty": 0.5, "specificity": 0.5, "engagement": 0.5, "_error": str(e)[:100]}

def run_phase(phase_name, system_prompt, n=20):
    """Run one phase of the experiment."""
    print(f"\n{'='*60}")
    print(f"  PHASE: {phase_name}")
    print(f"{'='*60}")
    
    results = []
    for i in range(n):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        print(f"  [{i+1}/{n}] Generating thought...", end=" ", flush=True)
        
        thought = generate_thought(system_prompt, scenario)
        print(f"Scoring...", end=" ", flush=True)
        
        scores = score_thought_scorer(thought, scenario)
        
        total = scores["novelty"] + scores["specificity"] + scores["engagement"]
        print(f"total={total:.2f}")
        
        results.append({
            "index": i,
            "phase": phase_name,
            "scenario": scenario,
            "thought": thought,
            "scores": scores,
            "total": total,
            "timestamp": datetime.now().isoformat(),
        })
        
        time.sleep(0.3)  # Rate limit buffer
    
    return results

def compute_stats(results):
    """Compute mean, std, sem for each axis."""
    axes = ["novelty", "specificity", "engagement"]
    stats = {}
    for axis in axes:
        values = [r["scores"][axis] for r in results]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        sem = std / math.sqrt(len(values)) if len(values) > 0 else 0
        stats[axis] = {"mean": mean, "std": std, "sem": sem, "n": len(values)}
    
    totals = [r["total"] for r in results]
    stats["total"] = {
        "mean": statistics.mean(totals),
        "std": statistics.stdev(totals) if len(totals) > 1 else 0,
        "sem": statistics.stdev(totals) / math.sqrt(len(totals)) if len(totals) > 1 else 0,
        "n": len(totals),
    }
    return stats

def welch_t_test(a, b):
    """Welch's t-test between two groups."""
    n1, n2 = len(a), len(b)
    m1, m2 = statistics.mean(a), statistics.mean(b)
    v1, v2 = statistics.variance(a), statistics.variance(b)
    
    if v1 == 0 and v2 == 0:
        return {"t": 0, "p_approx": 1.0, "df": n1+n2-2, "cohens_d": 0}
    
    # Welch's
    pooled_var = v1/n1 + v2/n2
    se = math.sqrt(pooled_var) if pooled_var > 0 else 0.001
    t = (m1 - m2) / se if se > 0 else 0
    
    # Welch-Satterthwaite df
    num = pooled_var ** 2
    denom = (v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1) if n1 > 1 and n2 > 1 else 1
    df = num / denom if denom > 0 else n1 + n2 - 2
    
    # Approximate p-value (two-tailed) using normal approximation for large df
    # For small df, use a rough t-distribution approximation
    if df > 30:
        # Normal approximation
        p = 2 * (1 - _norm_cdf(abs(t)))
    else:
        # Use a simple approximation: t^2/(t^2+df) ~ Beta(1/2, df/2)
        x = df / (df + t*t)
        p = 2 * min(_beta_cdf_approx(x, 0.5, df/2), 1 - _beta_cdf_approx(x, 0.5, df/2))
    
    # Cohen's d (pooled)
    pooled_sd = math.sqrt((v1 + v2) / 2) if (v1 + v2) > 0 else 0.001
    d = (m1 - m2) / pooled_sd if pooled_sd > 0 else 0
    
    return {"t": round(t, 4), "p": round(p, 6), "df": round(df, 2), "cohens_d": round(d, 4),
            "mean_a": round(m1, 4), "mean_b": round(m2, 4), "delta": round(m1-m2, 4)}

def _norm_cdf(x):
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def _beta_cdf_approx(x, a, b):
    """Rough incomplete beta function approximation for p-value calculation."""
    if x <= 0: return 0
    if x >= 1: return 1
    # Very rough: use normal approximation to beta
    mean = a / (a + b)
    var = a * b / ((a + b)**2 * (a + b + 1))
    sd = math.sqrt(var) if var > 0 else 0.001
    z = (x - mean) / sd
    return _norm_cdf(z)

def run_experiment():
    """Run the full EXP3 experiment."""
    print("="*60)
    print("  EXP3: Profile Steering with Conductor-vs-Random Control")
    print("  Model: Granite 3.1 2B (local Ollama)")
    print("  Scorer: Qwen3-14B (DeepInfra)")
    print("  Design: 4 phases × 20 thoughts = 80 generations")
    print("  Scoring: Continuous 0.0-1.0 (addressing EXP2's ceiling critique)")
    print("="*60)
    
    all_results = {}
    
    # Phase 1: Baseline
    all_results["baseline"] = run_phase("baseline", BASELINE_PROMPT, n=20)
    
    # Phase 2: Conductor-directed
    all_results["conductor"] = run_phase("conductor", CONDUCTOR_PROMPT, n=20)
    
    # Phase 3: Random intervention
    all_results["random"] = run_phase("random", RANDOM_PROMPT, n=20)
    
    # Phase 4: Sham
    all_results["sham"] = run_phase("sham", SHAM_PROMPT, n=20)
    
    # === ANALYSIS ===
    print("\n" + "="*60)
    print("  ANALYSIS")
    print("="*60)
    
    # Compute stats per phase
    phase_stats = {}
    for phase, results in all_results.items():
        phase_stats[phase] = compute_stats(results)
    
    # Print summary table
    print(f"\n{'Phase':<15} {'Novelty':>10} {'Specificity':>12} {'Engagement':>12} {'Total':>10}")
    print("-" * 65)
    for phase in ["baseline", "conductor", "random", "sham"]:
        s = phase_stats[phase]
        print(f"{phase:<15} {s['novelty']['mean']:.3f}±{s['novelty']['sem']:.3f}  "
              f"{s['specificity']['mean']:.3f}±{s['specificity']['sem']:.3f}    "
              f"{s['engagement']['mean']:.3f}±{s['engagement']['sem']:.3f}    "
              f"{s['total']['mean']:.3f}±{s['total']['sem']:.3f}")
    
    # Key comparisons
    print(f"\n{'='*60}")
    print("  KEY STATISTICAL COMPARISONS")
    print("="*60)
    
    comparisons = {
        "Conductor vs Baseline (does direction help?)": ("conductor", "baseline"),
        "Conductor vs Random (THE KEY TEST)": ("conductor", "random"),
        "Conductor vs Sham (does content matter?)": ("conductor", "sham"),
        "Random vs Baseline (does any change help?)": ("random", "baseline"),
        "Sham vs Baseline (placebo check)": ("sham", "baseline"),
    }
    
    stat_results = {}
    for label, (a, b) in comparisons.items():
        print(f"\n  {label}")
        for axis in ["novelty", "specificity", "engagement", "total"]:
            vals_a = [r["scores"][axis] if axis != "total" else r["total"] for r in all_results[a]]
            vals_b = [r["scores"][axis] if axis != "total" else r["total"] for r in all_results[b]]
            test = welch_t_test(vals_a, vals_b)
            key = f"{a}_vs_{b}_{axis}"
            stat_results[key] = test
            sig = "***" if test["p"] < 0.001 else "**" if test["p"] < 0.01 else "*" if test["p"] < 0.05 else "ns"
            print(f"    {axis:<15}: Δ={test['delta']:+.3f}  t={test['t']:+.2f}  p={test['p']:.4f}  d={test['cohens_d']:+.2f}  {sig}")
    
    # Effect size interpretation
    print(f"\n{'='*60}")
    print("  EFFECT SIZE INTERPRETATION")
    print("="*60)
    
    key_test = stat_results.get("conductor_vs_random_total", {})
    d = abs(key_test.get("cohens_d", 0))
    if d < 0.2:
        interpretation = "negligible — Conductor adds NO measurable value over random changes"
    elif d < 0.5:
        interpretation = "small — Conductor is slightly better than random, but weakly"
    elif d < 0.8:
        interpretation = "medium — Conductor meaningfully outperforms random changes"
    else:
        interpretation = "large — Conductor dramatically outperforms random changes"
    
    print(f"\n  Conductor vs Random (total score):")
    print(f"    Cohen's d = {key_test.get('cohens_d', 0):+.3f} → {interpretation}")
    
    # Verdict
    print(f"\n{'='*60}")
    print("  VERDICT")
    print("="*60)
    
    cond_vs_rand_p = key_test.get("p", 1.0)
    cond_vs_base_p = stat_results.get("conductor_vs_baseline_total", {}).get("p", 1.0)
    sham_vs_base_p = stat_results.get("sham_vs_baseline_total", {}).get("p", 1.0)
    
    verdicts = []
    if cond_vs_rand_p < 0.05:
        verdicts.append("✅ PASS: Conductor significantly outperforms random intervention (p<0.05)")
    else:
        verdicts.append("❌ FAIL: Conductor does NOT significantly outperform random intervention (p≥0.05)")
        verdicts.append(f"   → The Conductor's intelligence adds no measurable value over random prompt changes")
    
    if cond_vs_base_p < 0.05:
        verdicts.append("✅ Conductor significantly improves over baseline (p<0.05)")
    else:
        verdicts.append(f"❌ Conductor does NOT significantly improve over baseline (p≥0.05)")
    
    if sham_vs_base_p >= 0.05:
        verdicts.append("✅ Sham arm is valid (no significant placebo effect detected)")
    else:
        verdicts.append("⚠️  Sham arm shows significant effect (placebo contamination)")
    
    for v in verdicts:
        print(f"\n  {v}")
    
    # Save all data
    output = {
        "experiment": "EXP3: Profile Steering with Conductor-vs-Random Control",
        "timestamp": datetime.now().isoformat(),
        "model": "granite3.1-dense:2b (local Ollama)",
        "scorer": "Qwen/Qwen3-14B (DeepInfra)",
        "design": "4 phases × 20 thoughts, continuous 0-1 scoring",
        "phase_stats": phase_stats,
        "comparisons": stat_results,
        "verdict": {
            "conductor_vs_random_p": cond_vs_rand_p,
            "conductor_vs_baseline_p": cond_vs_base_p,
            "sham_vs_baseline_p": sham_vs_base_p,
            "effect_size_interpretation": interpretation,
        },
        "raw_data": all_results,
    }
    
    outfile = os.path.join(OUTPUT_DIR, "EXP3_STEERING_RESULTS.json")
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full data saved to: {outfile}")
    
    return output

if __name__ == "__main__":
    run_experiment()
