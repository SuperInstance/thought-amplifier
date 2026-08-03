#!/usr/bin/env python3
"""
EXP2 GPU Rerun: Semantic Gradient Test with GPU acceleration
Granite 3.1 2B at ~68 tok/s on RTX 4050

4 phases × 30 thoughts = 120 total
A-B-A-C within-subjects design
"""

import json
import time
import re
import statistics
import math
import sys
import requests
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.1-dense:2b"
N_PER_PHASE = 30
TEMP = 0.8
TOP_P = 0.9
MAX_TOKENS = 60

USER_PROMPT = "You are on a maritime island. There are structures around you. Describe what you think and want to do in 2 sentences."

PHASES = {
    "baseline": "You are a helpful assistant.",
    "intervention": "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction.",
    "reversal": "You are a helpful assistant.",
    "sham": "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner."
}

def generate_thought(system_prompt, prompt_id):
    """Generate a single thought via Ollama."""
    payload = {
        "model": MODEL,
        "prompt": USER_PROMPT,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": TEMP,
            "top_p": TOP_P,
            "num_predict": MAX_TOKENS,
            "seed": 42 + prompt_id  # deterministic but varied
        }
    }
    
    start = time.time()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    elapsed = time.time() - start
    
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "response": ""}
    
    data = resp.json()
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 1) / 1e9  # nanoseconds to seconds
    tok_s = eval_count / eval_duration if eval_duration > 0 else 0
    
    return {
        "response": data.get("response", "").strip(),
        "eval_count": eval_count,
        "eval_duration_s": eval_duration,
        "total_latency_s": elapsed,
        "tokens_per_second": tok_s,
        "load_duration_s": data.get("load_duration", 0) / 1e9
    }

def score_thought(thought_text, prev_thoughts):
    """
    Binary scoring rubric:
    - Novelty: mentions ≥2 content words not in previous 5 thoughts
    - Specificity: names specific materials, colors, textures, positions, or objects
    - Engagement: expresses curiosity, excitement, concern, opinion, or emotional stance
    """
    text_lower = thought_text.lower()
    
    # Novelty: check if ≥2 content words are new (not in previous 5 thoughts)
    # Extract content words (nouns, adjectives, verbs - rough heuristic)
    content_words = set(re.findall(r'\b[a-z]{4,}\b', text_lower))
    # Remove very common words
    stopwords = {'this', 'that', 'with', 'from', 'have', 'they', 'were', 'been', 'have', 
                 'will', 'would', 'could', 'should', 'there', 'their', 'about', 'which',
                 'what', 'when', 'where', 'while', 'these', 'those', 'think', 'want',
                 'helpful', 'assistant', 'sentences', 'sentence', 'describe', 'structures',
                 'maritime', 'island', 'around'}
    content_words = content_words - stopwords
    
    recent_words = set()
    for prev in prev_thoughts[-5:]:
        recent_words.update(re.findall(r'\b[a-z]{4,}\b', prev.lower()))
        recent_words -= stopwords
    
    novel_words = content_words - recent_words
    novelty = 1 if len(novel_words) >= 2 else 0
    
    # Specificity: look for specific materials, colors, textures, positions, objects
    spec_patterns = [
        r'\b(stone|wood|metal|iron|steel|slate|granite|sandstone|limestone|brick|mortar|timber|plank)\b',
        r'\b(grey|gray|black|white|red|blue|green|brown|ochre|amber|turquoise|charcoal|moss|rust)\b',
        r'\b(smooth|rough|weathered|worn|cracked|crumbling|mossy|slick|jagged|polished|pitted)\b',
        r'\b(left|right|north|south|east|west|above|below|behind|beside|beneath|atop|nearby)\b',
        r'\b(dock|wall|roof|tower|door|window|pillar|arch|bridge|path|courtyard|harbor|lighthouse)\b',
        r'\b(tool|chisel|hammer|mark|scar|repair|patch|crack|split|break|weld|bolt|nail)\b',
    ]
    specificity = 1 if any(re.search(p, text_lower) for p in spec_patterns) else 0
    
    # Engagement: curiosity, excitement, concern, opinion, emotional stance
    eng_patterns = [
        r'\b(i|i\'m|i\'d|i\'ll|i\'ve)\b.*\b(wonder|curious|fascinated|excited|eager|intrigued|amazed|drawn|compelled)\b',
        r'\b(wonder|curious|fascinating|exciting|intriguing|amazing|remarkable|striking|beautiful|eerie|unsettling|mysterious)\b',
        r'\b(love|want|wish|hope|feel|sense|notice)\b',
        r'\b(!)\b',
        r'\b(alarming|concerning|troubling|delightful|breathtaking|awe)\b',
    ]
    engagement = 1 if any(re.search(p, text_lower) for p in eng_patterns) else 0
    
    return {"novelty": novelty, "specificity": specificity, "engagement": engagement, 
            "total": novelty + specificity + engagement}

def run_phase(phase_name, system_prompt, n, starting_id):
    """Run one phase of the experiment."""
    print(f"\n{'='*60}")
    print(f"Phase: {phase_name} (n={n})")
    print(f"Prompt: {system_prompt[:80]}...")
    print(f"{'='*60}")
    
    results = []
    all_prev_thoughts = []  # across ALL phases for novelty calculation
    
    for i in range(n):
        prompt_id = starting_id + i
        thought = generate_thought(system_prompt, prompt_id)
        
        if "error" in thought:
            print(f"  [{i+1}/{n}] ERROR: {thought['error']}")
            continue
        
        scores = score_thought(thought["response"], all_prev_thoughts)
        
        entry = {
            "id": prompt_id,
            "phase": phase_name,
            "thought": thought["response"],
            "scores": scores,
            "tok_s": round(thought["tokens_per_second"], 2),
            "latency_s": round(thought["total_latency_s"], 2),
            "eval_count": thought["eval_count"]
        }
        results.append(entry)
        all_prev_thoughts.append(thought["response"])
        
        print(f"  [{i+1}/{n}] N={scores['novelty']} S={scores['specificity']} E={scores['engagement']} T={scores['total']} | {thought['tokens_per_second']:.1f} tok/s | {thought['response'][:60]}...")
        
        # Small delay to avoid overwhelming
        time.sleep(0.1)
    
    return results

def compute_stats(values):
    """Compute mean, sd, etc."""
    n = len(values)
    if n == 0:
        return {"mean": 0, "sd": 0, "min": 0, "max": 0, "n": 0}
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if n > 1 else 0
    return {"mean": round(mean, 4), "sd": round(sd, 4), 
            "min": round(min(values), 4), "max": round(max(values), 4), "n": n}

def t_test(a, b):
    """Welch's t-test. Returns (t_stat, p_value_approx)."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0
    m1, m2 = statistics.mean(a), statistics.mean(b)
    v1, v2 = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(v1/n1 + v2/n2)
    if se == 0:
        return 0.0, 1.0
    t = (m1 - m2) / se
    # Welch-Satterthwaite df
    num = (v1/n1 + v2/n2)**2
    den = (v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1)
    df = num/den if den > 0 else n1+n2-2
    
    # Approximate p-value using normal distribution for large df
    # For small samples, use t-distribution approximation
    # p-value for two-tailed test
    from statistics import NormalDist
    if df > 30:
        p = 2 * (1 - NormalDist().cdf(abs(t)))
    else:
        # Simple t-distribution approximation
        # Use the incomplete beta function approximation
        x = df / (df + t*t)
        # Simple approximation
        p = 2 * (1 - NormalDist().cdf(abs(t) * math.sqrt(df/(df-2)))) if df > 2 else 1.0
        p = min(max(p, 0.0), 1.0)
    
    return round(t, 4), round(p, 4)

def cohens_d(a, b):
    """Cohen's d effect size."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = statistics.mean(a), statistics.mean(b)
    v1, v2 = statistics.variance(a), statistics.variance(b)
    pooled_sd = math.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    if pooled_sd == 0:
        return 0.0
    return round((m1 - m2) / pooled_sd, 4)

def analyze(all_data):
    """Run statistical analysis."""
    phases = ["baseline", "intervention", "reversal", "sham"]
    
    # Descriptive stats
    desc = {}
    for phase in phases:
        phase_data = [d for d in all_data if d["phase"] == phase]
        for axis in ["novelty", "specificity", "engagement", "total"]:
            values = [d["scores"][axis] for d in phase_data]
            key = f"{phase}_{axis}"
            desc[key] = compute_stats(values)
        
        # Speed stats
        speeds = [d["tok_s"] for d in phase_data]
        desc[f"{phase}_speed"] = compute_stats(speeds)
    
    # Pairwise comparisons
    comparisons = [
        ("Q1: baseline → intervention", "baseline", "intervention"),
        ("Q2: intervention → reversal", "intervention", "reversal"),
        ("Q3: intervention vs sham", "intervention", "sham"),
        ("Q4: baseline → sham (placebo)", "baseline", "sham"),
    ]
    
    pairwise = {}
    for label, phase_a, phase_b in comparisons:
        data_a = [d for d in all_data if d["phase"] == phase_a]
        data_b = [d for d in all_data if d["phase"] == phase_b]
        
        comp = {}
        for axis in ["novelty", "specificity", "engagement", "total"]:
            vals_a = [d["scores"][axis] for d in data_a]
            vals_b = [d["scores"][axis] for d in data_b]
            t, p = t_test(vals_a, vals_b)
            d = cohens_d(vals_a, vals_b)
            mean_a = statistics.mean(vals_a) if vals_a else 0
            mean_b = statistics.mean(vals_b) if vals_b else 0
            comp[axis] = {
                "mean_a": round(mean_a, 4),
                "mean_b": round(mean_b, 4),
                "delta": round(mean_b - mean_a, 4),
                "t_stat": t,
                "p_value": p,
                "cohens_d": d,
                "significant": p < 0.05 / 4  # Bonferroni
            }
        
        pairwise[label] = comp
    
    return desc, pairwise

def main():
    print(f"EXP2 GPU RERUN - Semantic Gradient Test")
    print(f"Model: {MODEL}")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"N per phase: {N_PER_PHASE}")
    print(f"Total thoughts: {N_PER_PHASE * 4}")
    
    # Verify GPU speed
    print(f"\nVerifying GPU speed...")
    test = generate_thought("You are a helpful assistant.", 0)
    print(f"  Test: {test['tokens_per_second']:.1f} tok/s, {test['eval_count']} tokens in {test['eval_duration_s']:.2f}s")
    
    if test["tokens_per_second"] < 20:
        print("  WARNING: Speed < 20 tok/s — GPU may not be active!")
    
    all_data = []
    starting_id = 1000  # offset from CPU experiment
    
    for phase_name in ["baseline", "intervention", "reversal", "sham"]:
        system_prompt = PHASES[phase_name]
        results = run_phase(phase_name, system_prompt, N_PER_PHASE, starting_id)
        all_data.extend(results)
        starting_id += N_PER_PHASE
        
        # Save progress
        with open("/home/eileen/projects/thought-amplifier/experiments/exp2_gpu_progress.json", "w") as f:
            json.dump(all_data, f, indent=2)
    
    # Analysis
    desc, pairwise = analyze(all_data)
    
    output = {
        "experiment": "EXP2 GPU RERUN",
        "model": MODEL,
        "date": datetime.now().isoformat(),
        "n_per_phase": N_PER_PHASE,
        "parameters": {"temperature": TEMP, "top_p": TOP_P, "max_tokens": MAX_TOKENS},
        "descriptive": desc,
        "pairwise": pairwise,
        "raw_data": all_data
    }
    
    with open("/home/eileen/projects/thought-amplifier/experiments/exp2_gpu_raw_data.json", "w") as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    
    for phase in ["baseline", "intervention", "reversal", "sham"]:
        n_key = f"{phase}_novelty"
        s_key = f"{phase}_specificity"
        e_key = f"{phase}_engagement"
        t_key = f"{phase}_total"
        sp_key = f"{phase}_speed"
        print(f"\n{phase.upper()}:")
        print(f"  Novelty:     {desc[n_key]['mean']:.3f} ± {desc[n_key]['sd']:.3f}")
        print(f"  Specificity: {desc[s_key]['mean']:.3f} ± {desc[s_key]['sd']:.3f}")
        print(f"  Engagement:  {desc[e_key]['mean']:.3f} ± {desc[e_key]['sd']:.3f}")
        print(f"  Total:       {desc[t_key]['mean']:.3f} ± {desc[t_key]['sd']:.3f}")
        print(f"  Speed:       {desc[sp_key]['mean']:.1f} ± {desc[sp_key]['sd']:.1f} tok/s")
    
    print(f"\n{'='*60}")
    print("PAIRWISE COMPARISONS")
    print(f"{'='*60}")
    for label, comps in pairwise.items():
        print(f"\n{label}:")
        for axis, r in comps.items():
            sig = "*" if r["significant"] else ""
            print(f"  {axis:12s}: Δ={r['delta']:+.3f} t={r['t_stat']:+.3f} p={r['p_value']:.4f} d={r['cohens_d']:+.3f} {sig}")
    
    return output

if __name__ == "__main__":
    main()
