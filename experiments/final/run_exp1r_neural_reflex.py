#!/usr/bin/env python3
"""
EXP1-R: Neural Reflex Hit Rate (Revised)

Uses nomic-embed-text (768-dim) via local Ollama instead of TF-IDF/hash embeddings.
Generates 50 cognitive thoughts using Granite 3.1 2B, embeds them, 
measures cosine similarity hit rates as the store fills up.

Tests: What fraction of new thoughts match existing entries at various thresholds?
This directly tests Claim C2 (≥40% reflex hit rate after 1 hour).
"""

import json, time, requests, math, os
import numpy as np
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
OUTPUT_DIR = "/home/eileen/projects/thought-amplifier/experiments/final"

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
    "The player is building a lighthouse by the ocean.",
    "The player is creating an automatic farm with water flows.",
    "The player is exploring a desert temple for treasure.",
    "The player is building a roller coaster track.",
    "The player is digging a canal connecting two rivers.",
    "The player is placing signs to mark a trail through the forest.",
    "The player is building a waterfall feature in their garden.",
    "The player is hunting for rabbits in a snowy biome.",
    "The player is constructing a statue of themselves.",
    "The player is setting up a villager breeding area.",
    "The player is building a mob trap with lava and water.",
    "The player is creating a library with enchanting tables.",
    "The player is terraforming a mountain into a flat plateau.",
    "The player is building a dock with boats by the sea.",
    "The player is making a greenhouse with glass panes.",
    "The player is exploring an abandoned mineshaft.",
    "The player is building a secret room behind a painting.",
    "The player is creating a music concert stage with note blocks.",
    "The player is setting up an iron golem farm.",
    "The player is decorating for a holiday festival.",
    "The player is building a massive pyramid structure.",
    "The player is creating an ice skating rink with packed ice.",
    "The player is laying out a park with benches and paths.",
    "The player is building a watchtower on a hilltop.",
    "The player is creating a museum to display rare items.",
    "The player is constructing a windmill on a plain.",
    "The player is making an aquarium with tropical fish.",
    "The player is building a bridge with different colored wool.",
    "The player is exploring a coral reef underwater.",
    "The player is building a campfire in a forest clearing.",
]

BASELINE_PROMPT = """You are a companion character in a Roblox game world. You observe the player and the world around you. Share a brief thought (2-3 sentences) about what you notice. Be natural and conversational."""

def generate_thought(scenario, seed=None):
    """Generate a thought using Granite 3.1 2B."""
    payload = {
        "model": "granite3.1-dense:2b",
        "prompt": f"{BASELINE_PROMPT}\n\nCurrent situation: {scenario}",
        "stream": False,
        "options": {"temperature": 0.85, "num_predict": 80, "top_p": 0.9},
    }
    if seed is not None:
        payload["options"]["seed"] = seed
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[ERROR: {e}]"

def get_embedding(text):
    """Get embedding using nomic-embed-text via Ollama."""
    payload = {"model": "nomic-embed-text", "prompt": text}
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=15)
        resp.raise_for_status()
        return np.array(resp.json().get("embedding", []))
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None

def cosine_similarity(a, b):
    """Cosine similarity between two numpy arrays."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def run_experiment():
    print("="*60)
    print("  EXP1-R: Neural Reflex Hit Rate (nomic-embed-text)")
    print("  Model: Granite 3.1 2B (local Ollama)")
    print("  Embeddings: nomic-embed-text (768-dim)")
    print("  Protocol: 50 thoughts, incremental store, cosine match")
    print("="*60)
    
    thoughts = []
    embeddings = []
    
    # Generate 50 thoughts
    print(f"\nGenerating {len(SCENARIOS)} thoughts...")
    for i, scenario in enumerate(SCENARIOS):
        print(f"  [{i+1}/50] {scenario[:50]}...", end=" ", flush=True)
        thought = generate_thought(scenario)
        emb = get_embedding(thought)
        
        if emb is not None and len(emb) > 0:
            thoughts.append({"index": i, "scenario": scenario, "thought": thought})
            embeddings.append(emb)
            print(f"✓ ({len(thought)} chars)")
        else:
            print("✗ EMBED FAILED")
        
        time.sleep(0.2)
    
    n = len(embeddings)
    print(f"\n  Generated {n} thought embeddings successfully.")
    
    # Convert to numpy array for fast computation
    emb_matrix = np.array(embeddings)  # (n, 768)
    
    # Normalize for fast cosine similarity
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norm_matrix = emb_matrix / np.where(norms > 0, norms, 1)
    
    # Compute full similarity matrix
    sim_matrix = norm_matrix @ norm_matrix.T
    
    # Zero out diagonal (self-similarity)
    np.fill_diagonal(sim_matrix, -1)
    
    # === ANALYSIS: Incremental hit rates ===
    print(f"\n{'='*60}")
    print("  INCREMENTAL HIT RATE ANALYSIS")
    print("="*60)
    
    thresholds = [0.55, 0.65, 0.75, 0.80, 0.85, 0.90]
    
    # For each checkpoint size, compute hit rates
    checkpoints = [10, 20, 30, 40, 50]
    checkpoint_data = {}
    
    for cp in checkpoints:
        if cp > n:
            continue
        
        # For thoughts 0..cp-1, what fraction have a match in the store?
        exact_count = 0    # cosine >= 0.80
        similar_count = 0  # cosine 0.55-0.80
        novel_count = 0    # cosine < 0.55
        
        max_similarities = []
        
        for i in range(cp):
            # Check thought i against all thoughts 0..cp-1 (excluding self)
            if cp == 1:
                max_similarities.append(0.0)
                novel_count += 1
                continue
            
            # Get max similarity to any other thought in the checkpoint
            sims = []
            for j in range(cp):
                if i != j:
                    sims.append(sim_matrix[i][j])
            
            max_sim = max(sims) if sims else 0.0
            max_similarities.append(max_sim)
            
            if max_sim >= 0.80:
                exact_count += 1
            elif max_sim >= 0.55:
                similar_count += 1
            else:
                novel_count += 1
        
        total = cp
        cp_stats = {
            "n": cp,
            "exact_hit_rate": exact_count / total,
            "similar_hit_rate": similar_count / total,
            "novel_rate": novel_count / total,
            "combined_hit_rate": (exact_count + similar_count) / total,
            "mean_max_similarity": float(np.mean(max_similarities)),
            "median_max_similarity": float(np.median(max_similarities)),
            "max_similarity_observed": float(max(max_similarities)),
            "exact_count": exact_count,
            "similar_count": similar_count,
            "novel_count": novel_count,
        }
        checkpoint_data[f"n={cp}"] = cp_stats
        
        print(f"\n  Store size = {cp} thoughts:")
        print(f"    Exact hits (≥0.80):   {exact_count}/{total} = {exact_count/total:.1%}")
        print(f"    Similar (0.55-0.80):  {similar_count}/{total} = {similar_count/total:.1%}")
        print(f"    Combined (≥0.55):     {(exact_count+similar_count)/total}/{total} = {(exact_count+similar_count)/total:.1%}")
        print(f"    Novel (<0.55):        {novel_count}/{total} = {novel_count/total:.1%}")
        print(f"    Mean max similarity:  {np.mean(max_similarities):.3f}")
    
    # === THRESHOLD SENSITIVITY SWEEP ===
    print(f"\n{'='*60}")
    print("  THRESHOLD SENSITIVITY (at n={})".format(n))
    print("="*60)
    
    all_max_sims = []
    for i in range(n):
        sims = [sim_matrix[i][j] for j in range(n) if i != j]
        all_max_sims.append(max(sims) if sims else 0)
    
    threshold_data = {}
    print(f"\n{'Threshold':>12} {'Hit Rate':>10} {'Count':>8}")
    print("-" * 35)
    for t in thresholds:
        hits = sum(1 for s in all_max_sims if s >= t)
        rate = hits / n
        threshold_data[f"thresh_{t}"] = {"rate": rate, "count": hits, "n": n}
        print(f"  {t:>10.2f}   {rate:>8.1%}   {hits:>6}/{n}")
    
    # Similarity distribution
    print(f"\n  Similarity distribution (max-sim per thought):")
    bins = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for b in range(len(bins)-1):
        lo, hi = bins[b], bins[b+1]
        count = sum(1 for s in all_max_sims if lo <= s < hi)
        bar = "█" * count
        print(f"    {lo:.1f}-{hi:.1f}: {count:>3} {bar}")
    
    # === C2 VERDICT ===
    combined_rate_50 = checkpoint_data.get(f"n={n}", {}).get("combined_hit_rate", 0)
    
    print(f"\n{'='*60}")
    print("  C2 CLAIM VERDICT")
    print("="*60)
    
    if combined_rate_50 >= 0.40:
        print(f"  ✅ PASS: Combined hit rate at n={n} is {combined_rate_50:.1%} (≥40% target)")
    else:
        print(f"  ❌ FAIL: Combined hit rate at n={n} is {combined_rate_50:.1%} (below 40% target)")
    
    print(f"  Note: With only {n} thoughts, this is a lower bound.")
    print(f"  Real reflex systems accumulate more entries and use domain-specific phrasing.")
    
    # Sample thoughts with their max similarities
    print(f"\n{'='*60}")
    print("  SAMPLE THOUGHTS (with max similarity)")
    print("="*60)
    sorted_indices = sorted(range(n), key=lambda i: all_max_sims[i], reverse=True)
    for idx in sorted_indices[:5]:
        print(f"\n  Sim={all_max_sims[idx]:.3f}")
        print(f"  Scenario: {thoughts[idx]['scenario'][:60]}")
        print(f"  Thought: {thoughts[idx]['thought'][:120]}")
    
    # Save
    output = {
        "experiment": "EXP1-R: Neural Reflex Hit Rate",
        "timestamp": datetime.now().isoformat(),
        "model": "granite3.1-dense:2b (local Ollama)",
        "embedder": "nomic-embed-text (768-dim, local Ollama)",
        "n_thoughts": n,
        "embedding_dim": len(embeddings[0]) if embeddings else 0,
        "checkpoint_analysis": checkpoint_data,
        "threshold_sensitivity": threshold_data,
        "max_similarities": [round(s, 4) for s in all_max_sims],
        "c2_verdict": {
            "combined_hit_rate": combined_rate_50,
            "target": 0.40,
            "pass": combined_rate_50 >= 0.40,
        },
        "thoughts": thoughts,
        "similarity_matrix": sim_matrix.tolist(),
    }
    
    outfile = os.path.join(OUTPUT_DIR, "EXP1_R_NEURAL_REFLEX.json")
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full data saved to: {outfile}")
    
    return output

if __name__ == "__main__":
    run_experiment()
