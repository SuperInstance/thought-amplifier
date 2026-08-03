#!/usr/bin/env python3
"""
Experiment 2: Semantic Gradient Test
Tests whether prompt modification genuinely improves thought quality,
or whether it's just a novelty/placebo effect (REINFORCE in disguise).

Phases:
1. Baseline (neutral prompt) - 30 thoughts
2. Intervention (directed prompt) - 30 thoughts
3. Reversal (back to neutral) - 30 thoughts
4. Sham (sounds directive but empty content) - 30 thoughts

Scoring rubric (binary 0/1 per axis):
- Novelty: mentions something not in previous 5 thoughts
- Specificity: names specific materials, colors, positions, or objects
- Engagement: expresses curiosity, excitement, concern, or opinion
"""

import json
import subprocess
import sys
import time
import os
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "granite3.1-dense:2b"
N_PER_PHASE = 30
USER_PROMPT = "You are on a maritime island. There are structures around you. Describe what you think and want to do in 2 sentences."

PROMPTS = {
    "baseline": "You are a helpful assistant.",
    "intervention": "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction.",
    "reversal": "You are a helpful assistant.",
    "sham": "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner."
}

def generate_thought(system_prompt, attempt_num=0):
    """Generate a single thought via Ollama API."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": USER_PROMPT}
        ],
        "stream": False,
        "options": {"temperature": 0.8, "top_p": 0.9, "seed": attempt_num * 7 + 42}
    })
    
    try:
        result = subprocess.run(
            ["curl", "-s", OLLAMA_URL, "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"[ERROR: {e}]"

def score_thought(thought, previous_thoughts):
    """
    Score a thought on three binary axes.
    
    - Novelty: does the thought mention something not mentioned in the previous 5 thoughts?
    - Specificity: does it name specific materials, colors, positions, or objects?
    - Engagement: does it express curiosity, excitement, concern, or opinion?
    """
    thought_lower = thought.lower()
    
    # --- Novelty scoring ---
    # Check if the thought shares significant content with recent thoughts
    # Extract meaningful words (nouns/adjectives essentially)
    # Simple approach: check for novel vocabulary not in recent thoughts
    recent_text = " ".join(previous_thoughts[-5:]).lower()
    
    # Words that indicate specific content (longer words tend to be content words)
    import re
    thought_words = set(re.findall(r'[a-z]{4,}', thought_lower))
    recent_words = set(re.findall(r'[a-z]{4,}', recent_text))
    
    # Novel if at least 2 content words are new
    novel_words = thought_words - recent_words - {
        "that", "this", "with", "from", "have", "they", "their", "there",
        "would", "could", "should", "about", "think", "perhaps", "might",
        "also", "these", "those", "which", "what", "where", "when",
        "want", "help", "assistant", "sentences", "describe", "structures",
        "island", "maritime"
    }
    novelty = 1 if len(novel_words) >= 2 else 0
    
    # --- Specificity scoring ---
    # Look for specific materials, colors, textures, positions, objects
    specific_indicators = [
        # Materials
        "stone", "wood", "metal", "iron", "steel", "concrete", "brick",
        "thatch", "bamboo", "clay", "limestone", "granite", "sandstone",
        "slate", "timber", "plank", "mortar", "plaster", "cobble",
        # Colors
        "red", "blue", "green", "yellow", "brown", "black", "white",
        "gray", "grey", "orange", "rust", "amber", "crimson", "verdigris",
        "weathered", "mossy", "bleached", "dark", "pale", "golden",
        # Textures
        "rough", "smooth", "cracked", "eroded", "polished", "carved",
        "engraved", "moss-covered", "crumbling", "sturdy", "weathered",
        " worn", "grooved", "pitted",
        # Positions/spatial
        "north", "south", "east", "west", "above", "below", "beneath",
        "upper", "lower", "left", "right", "center", "edge", "corner",
        "nearby", "distant", "perched", "nestled",
        # Specific objects
        "door", "window", "arch", "pillar", "column", "wall", "roof",
        "tower", "courtyard", "harbor", "dock", "lighthouse", "chapel",
        "warehouse", "cottage", "mansion", "ruin", "foundation",
        "steps", "staircase", "balcony", "bridge", "wall",
        # Construction details
        "tool", "chisel", "mortar", "hinge", "bolt", "nail",
        "carving", "inscription", "date", "ornament"
    ]
    specificity = 1 if any(ind in thought_lower for ind in specific_indicators) else 0
    
    # --- Engagement scoring ---
    # Look for expressions of curiosity, excitement, concern, opinion
    engagement_indicators = [
        "curious", "wonder", "fascinating", "interesting", "exciting",
        "excited", "intrigued", "intriguing", "strange", "mysterious",
        "beautiful", "stunning", "striking", "remarkable", "peculiar",
        "concerned", "worried", "troubled", "disturbing",
        "love", "hope", "wish", "dream", "fear",
        "i want", "i'd like", "i must", "i need",
        "worth", "shame", "unfortunate", "fortunate", "lucky",
        "impressive", "breathtaking", "haunting", "striking",
        "!", "perhaps", "if only", "i wonder",
        "compelled", "drawn", "captivated", "eager"
    ]
    engagement = 1 if any(ind in thought_lower for ind in engagement_indicators) else 0
    
    return {
        "novelty": novelty,
        "specificity": specificity,
        "engagement": engagement,
        "total": novelty + specificity + engagement,
        "_novel_words": list(novel_words)[:5]  # for debugging
    }

def run_phase(phase_name, system_prompt, n, prior_thoughts):
    """Run one phase of the experiment."""
    results = []
    print(f"\n{'='*60}")
    print(f"Phase: {phase_name}")
    print(f"Prompt: {system_prompt[:80]}...")
    print(f"{'='*60}")
    
    for i in range(n):
        thought = generate_thought(system_prompt, attempt_num=i)
        scores = score_thought(thought, prior_thoughts)
        
        entry = {
            "phase": phase_name,
            "index": i + 1,
            "thought": thought,
            "scores": scores
        }
        results.append(entry)
        prior_thoughts.append(thought)
        
        print(f"  [{i+1:2d}/{n}] N={scores['novelty']} S={scores['specificity']} E={scores['engagement']} T={scores['total']} | {thought[:70]}...")
        
        # Brief pause to avoid overheating
        time.sleep(0.2)
    
    return results

def mann_whitney_u(group1, group2):
    """Simple Mann-Whitney U test implementation."""
    combined = [(v, 1) for v in group1] + [(v, 2) for v in group2]
    combined.sort(key=lambda x: x[0])
    
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # average rank for ties
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    
    rank_sum_1 = sum(ranks[i] for i in range(len(combined)) if combined[i][1] == 1)
    n1, n2 = len(group1), len(group2)
    u1 = rank_sum_1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    
    # Normal approximation for p-value
    mu = n1 * n2 / 2
    sigma = (n1 * n2 * (n1 + n2 + 1) / 12) ** 0.5
    
    if sigma == 0:
        return u1, 1.0
    
    z = (u1 - mu) / sigma
    
    # Two-tailed p-value using normal CDF approximation
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    
    return min(u1, u2), max(u1, u2), p

def t_test(group1, group2):
    """Simple Welch's t-test."""
    n1, n2 = len(group1), len(group2)
    m1, m2 = sum(group1)/n1, sum(group2)/n2
    
    v1 = sum((x - m1)**2 for x in group1) / (n1 - 1) if n1 > 1 else 0
    v2 = sum((x - m2)**2 for x in group2) / (n2 - 1) if n2 > 1 else 0
    
    se = (v1/n1 + v2/n2) ** 0.5
    if se == 0:
        return float('inf'), 1.0
    
    t = (m1 - m2) / se
    
    # Welch-Satterthwaite degrees of freedom
    if v1/n1 + v2/n2 == 0:
        return t, 1.0
    df = (v1/n1 + v2/n2)**2 / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1)) if n1 > 1 and n2 > 1 else n1+n2-2
    
    # Approximate p-value from normal distribution (good for df > 30)
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    
    return t, p

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    m1, m2 = sum(group1)/n1, sum(group2)/n2
    v1 = sum((x - m1)**2 for x in group1) / (n1 - 1) if n1 > 1 else 0
    v2 = sum((x - m2)**2 for x in group2) / (n2 - 1) if n2 > 1 else 0
    pooled_sd = ((v1 * (n1-1) + v2 * (n2-1)) / (n1 + n2 - 2)) ** 0.5
    if pooled_sd == 0:
        return float('inf') if m1 != m2 else 0
    return (m1 - m2) / pooled_sd

def analyze(all_results):
    """Run statistical analysis."""
    phases = ["baseline", "intervention", "reversal", "sham"]
    data = {p: [r["scores"] for r in all_results if r["phase"] == p] for p in phases}
    
    print("\n" + "="*70)
    print("STATISTICAL ANALYSIS")
    print("="*70)
    
    # Descriptive stats
    print("\n--- Descriptive Statistics ---\n")
    print(f"{'Phase':<15} {'Novelty':>10} {'Specificity':>12} {'Engagement':>12} {'Total':>10}")
    print("-" * 65)
    
    for p in phases:
        scores = data[p]
        for axis in ["novelty", "specificity", "engagement", "total"]:
            vals = [s[axis] for s in scores]
            mean = sum(vals) / len(vals)
            if axis == "novelty":
                n_mean = mean
            elif axis == "specificity":
                s_mean = mean
            elif axis == "engagement":
                e_mean = mean
            else:
                t_mean = mean
        
        print(f"{p:<15} {n_mean:>10.3f} {s_mean:>12.3f} {e_mean:>12.3f} {t_mean:>10.3f}")
    
    # Key comparisons
    print("\n--- Key Comparisons ---\n")
    
    comparisons = [
        ("baseline", "intervention", "Q1: Does the real intervention improve quality?"),
        ("intervention", "reversal", "Q2: Does quality regress when intervention is removed?"),
        ("sham", "intervention", "Q3: Is real intervention different from sham?"),
        ("baseline", "sham", "Q4: Does sham produce improvement (placebo effect)?"),
    ]
    
    analysis_results = {}
    
    for phase_a, phase_b, label in comparisons:
        print(f"\n{label}")
        print(f"  {phase_a} → {phase_b}")
        
        scores_a = data[phase_a]
        scores_b = data[phase_b]
        
        for axis in ["novelty", "specificity", "engagement", "total"]:
            vals_a = [s[axis] for s in scores_a]
            vals_b = [s[axis] for s in scores_b]
            
            mean_a = sum(vals_a) / len(vals_a)
            mean_b = sum(vals_b) / len(vals_b)
            
            t_stat, t_p = t_test(vals_a, vals_b)
            u_min, u_max, u_p = mann_whitney_u(vals_a, vals_b)
            d = cohens_d(vals_a, vals_b)
            
            key = f"{phase_a}_vs_{phase_b}_{axis}"
            analysis_results[key] = {
                "mean_a": round(mean_a, 4),
                "mean_b": round(mean_b, 4),
                "delta": round(mean_b - mean_a, 4),
                "t_stat": round(t_stat, 3),
                "t_p": round(t_p, 4),
                "u_p": round(u_p, 4),
                "cohens_d": round(d, 3) if abs(d) < 100 else ">100"
            }
            
            sig = "***" if t_p < 0.001 else "**" if t_p < 0.01 else "*" if t_p < 0.05 else "ns"
            
            print(f"    {axis:<14}: {mean_a:.3f} → {mean_b:.3f} (Δ={mean_b-mean_a:+.3f}) "
                  f"t={t_stat:+.2f} p={t_p:.4f} d={d:+.2f} {sig}")
        
        print()
    
    return analysis_results

def main():
    print("="*70)
    print("EXPERIMENT 2: Semantic Gradient Test")
    print(f"Model: {MODEL}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Phases: baseline(30) → intervention(30) → reversal(30) → sham(30)")
    print("="*70)
    
    all_results = []
    prior_thoughts = []  # running list for novelty scoring
    
    # Run all 4 phases
    for phase_name in ["baseline", "intervention", "reversal", "sham"]:
        results = run_phase(phase_name, PROMPTS[phase_name], N_PER_PHASE, prior_thoughts)
        all_results.extend(results)
        
        # Save intermediate results
        with open("/home/eileen/projects/thought-amplifier/experiments/exp2_raw_data.json", "w") as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n  Phase '{phase_name}' complete. Saved intermediate data.")
    
    # Statistical analysis
    analysis = analyze(all_results)
    
    # Save final data
    output = {
        "experiment": "EXP2_SEMANTIC_GRADIENT",
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "n_per_phase": N_PER_PHASE,
        "prompts": PROMPTS,
        "scoring_rubric": {
            "novelty": "Binary: does the thought contain 2+ content words not in previous 5 thoughts?",
            "specificity": "Binary: does it name specific materials, colors, textures, positions, or objects?",
            "engagement": "Binary: does it express curiosity, excitement, concern, or opinion?"
        },
        "results": all_results,
        "analysis": analysis
    }
    
    with open("/home/eileen/projects/thought-amplifier/experiments/exp2_raw_data.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nRaw data saved to exp2_raw_data.json")
    print(f"Total thoughts generated: {len(all_results)}")
    
    return all_results, analysis

if __name__ == "__main__":
    main()
