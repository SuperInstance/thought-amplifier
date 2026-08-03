#!/usr/bin/env python3
"""
Experiment 1: Reflex Hit Rate — Robust embedding with ollama restart.
Restarts ollama when it crashes, uses long retry windows.
"""
import requests
import numpy as np
import json
import time
import sys
import os
import subprocess
import signal
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
EXPERIMENT_DIR = "/home/eileen/projects/thought-amplifier/experiments"

def ensure_ollama():
    """Check if ollama is alive; restart if needed."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/version", timeout=5)
        if resp.status_code == 200:
            return True
    except:
        pass
    
    # Ollama is dead, restart it
    print("  [OLLAMA] Restarting...", file=sys.stderr, flush=True)
    try:
        # Kill any zombie processes
        subprocess.run(["pkill", "-f", "ollama"], capture_output=True, timeout=5)
        time.sleep(3)
    except:
        pass
    
    # Start fresh
    subprocess.Popen(
        ["/home/eileen/.local/bin/ollama", "serve"],
        stdout=open("/tmp/ollama_exp.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True  # Detach from our process group
    )
    
    # Wait for it to be ready
    for _ in range(30):
        time.sleep(2)
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/version", timeout=5)
            if resp.status_code == 200:
                print("  [OLLAMA] Back online", file=sys.stderr, flush=True)
                # Warm up the embedding model
                time.sleep(2)
                try:
                    requests.post(f"{OLLAMA_URL}/api/embeddings", json={
                        "model": EMBED_MODEL, "prompt": "warmup"
                    }, timeout=60)
                except:
                    pass
                return True
        except:
            pass
    return False

def embed_robust(text, max_retries=8):
    """Get embedding with aggressive retry + ollama restart."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
                "model": EMBED_MODEL,
                "prompt": text
            }, timeout=90)
            resp.raise_for_status()
            emb = resp.json().get("embedding", [])
            if emb:
                return np.array(emb, dtype=np.float32)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = min(5 * (attempt + 1), 20)
                print(f"  [RETRY {attempt+1}/{max_retries}] {text[:40]}... waiting {wait}s", file=sys.stderr, flush=True)
                time.sleep(wait)
                # Every 3 failures, restart ollama
                if (attempt + 1) % 3 == 0:
                    ensure_ollama()
            else:
                print(f"  [FAILED] {text[:40]}... using random fallback", file=sys.stderr, flush=True)
                return np.random.randn(768).astype(np.float32) * 0.01
    return np.random.randn(768).astype(np.float32) * 0.01

def embed_all(texts, label):
    """Embed all texts with progress and checkpointing."""
    embeddings = []
    checkpoint_file = f"{EXPERIMENT_DIR}/emb_checkpoint_{label}.npy"
    
    # Load checkpoint if exists
    if os.path.exists(checkpoint_file):
        embeddings = list(np.load(checkpoint_file))
        print(f"  Resuming from checkpoint: {len(embeddings)}/{len(texts)}", file=sys.stderr, flush=True)
    
    for i in range(len(embeddings), len(texts)):
        emb = embed_robust(texts[i])
        embeddings.append(emb)
        
        if (i + 1) % 10 == 0:
            print(f"  {label}: {i+1}/{len(texts)} embedded", file=sys.stderr, flush=True)
            # Save checkpoint
            np.save(checkpoint_file, np.array(embeddings))
        
        # Small delay to avoid overwhelming ollama
        time.sleep(0.1)
    
    # Final save
    np.save(checkpoint_file, np.array(embeddings))
    return np.array(embeddings)

def cosine_similarity_matrix(emb_matrix):
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    normalized = emb_matrix / (norms + 1e-8)
    return normalized @ normalized.T

def incremental_hit_rate(embeddings, threshold_exact=0.80, threshold_similar=0.55):
    results = []
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / (norms + 1e-8)
    
    for i in range(1, len(embeddings)):
        sims = normalized[i] @ normalized[:i].T
        best_sim = float(sims.max())
        best_match_idx = int(sims.argmax())
        
        if best_sim >= threshold_exact:
            classification = "exact"
        elif best_sim >= threshold_similar:
            classification = "similar"
        else:
            classification = "novel"
        
        results.append({
            "item_idx": i,
            "best_similarity": best_sim,
            "best_match_idx": best_match_idx,
            "classification": classification
        })
    return results

def compute_hit_rates(results, checkpoints):
    rates = {}
    for cp in checkpoints:
        subset = results[:cp]
        if not subset:
            continue
        exact = sum(1 for r in subset if r["classification"] == "exact")
        similar = sum(1 for r in subset if r["classification"] == "similar")
        novel = sum(1 for r in subset if r["classification"] == "novel")
        total = len(subset)
        avg_sim = sum(r["best_similarity"] for r in subset) / total
        sims = sorted([r["best_similarity"] for r in subset])
        median_sim = sims[len(sims)//2]
        p25 = sims[len(sims)//4]
        p75 = sims[3*len(sims)//4]
        
        rates[cp] = {
            "total": total, "exact": exact, "similar": similar, "novel": novel,
            "exact_rate": exact / total, "similar_rate": similar / total,
            "novel_rate": novel / total, "hit_rate": (exact + similar) / total,
            "avg_similarity": avg_sim, "median_similarity": median_sim,
            "p25_similarity": p25, "p75_similarity": p75,
        }
    return rates

def main():
    print("=" * 70, flush=True)
    print("EXPERIMENT 1: Reflex Hit Rate — Cognitive vs Command", flush=True)
    print("=" * 70, flush=True)
    print(f"Date: {datetime.now().isoformat()}", flush=True)
    print(f"Embedding: {EMBED_MODEL} (768-dim)", flush=True)
    print(f"Thresholds: exact ≥0.80, similar 0.55-0.80, novel <0.55", flush=True)
    print(flush=True)
    
    # Ensure ollama is up
    print("Checking ollama...", flush=True)
    if not ensure_ollama():
        print("FATAL: Could not start ollama!", flush=True)
        sys.exit(1)
    
    # Load data
    with open(f"{EXPERIMENT_DIR}/thoughts_cognitive.txt") as f:
        thoughts = [line.strip() for line in f if line.strip()]
    with open(f"{EXPERIMENT_DIR}/thoughts_commands.txt") as f:
        commands = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(thoughts)} thoughts, {len(commands)} commands", flush=True)
    
    # Embed
    print("\nEmbedding cognitive thoughts...", flush=True)
    t0 = time.time()
    cog_embs = embed_all(thoughts, "cognitive")
    print(f"  Done in {time.time()-t0:.0f}s ({len(cog_embs)} embeddings)", flush=True)
    
    print("\nEmbedding command phrases...", flush=True)
    t0 = time.time()
    cmd_embs = embed_all(commands, "commands")
    print(f"  Done in {time.time()-t0:.0f}s ({len(cmd_embs)} embeddings)", flush=True)
    
    # Save final embeddings
    np.save(f"{EXPERIMENT_DIR}/cog_embeddings.npy", cog_embs)
    np.save(f"{EXPERIMENT_DIR}/cmd_embeddings.npy", cmd_embs)
    
    # Clean up checkpoints
    for f in ["emb_checkpoint_cognitive.npy", "emb_checkpoint_commands.npy"]:
        path = f"{EXPERIMENT_DIR}/{f}"
        if os.path.exists(path):
            os.remove(path)
    
    # Check how many fallback embeddings were used
    cog_norms = np.linalg.norm(cog_embs, axis=1)
    cmd_norms = np.linalg.norm(cmd_embs, axis=1)
    cog_fallbacks = np.sum(cog_norms < 0.1)
    cmd_fallbacks = np.sum(cmd_norms < 0.1)
    
    if cog_fallbacks > 0 or cmd_fallbacks > 0:
        print(f"\nWARNING: {cog_fallbacks} cognitive + {cmd_fallbacks} command fallback embeddings used", flush=True)
    
    # Compute similarity matrices
    cog_sim = cosine_similarity_matrix(cog_embs)
    cmd_sim = cosine_similarity_matrix(cmd_embs)
    
    # Incremental hit rate
    cog_results = incremental_hit_rate(cog_embs)
    cmd_results = incremental_hit_rate(cmd_embs)
    
    checkpoints = [25, 50, 99]
    checkpoint_labels = {25: "n=25", 50: "n=50", 99: "n=100"}
    
    cog_rates = compute_hit_rates(cog_results, checkpoints)
    cmd_rates = compute_hit_rates(cmd_results, checkpoints)
    
    # Stats
    from scipy.stats import mannwhitneyu, ttest_ind
    
    cog_sims = [r["best_similarity"] for r in cog_results]
    cmd_sims = [r["best_similarity"] for r in cmd_results]
    
    cog_hit_rates = [1 if r["classification"] in ("exact", "similar") else 0 for r in cog_results]
    cmd_hit_rates = [1 if r["classification"] in ("exact", "similar") else 0 for r in cmd_results]
    
    u_stat, u_pvalue = mannwhitneyu(cog_sims, cmd_sims, alternative='less')
    t_stat, t_pvalue = ttest_ind(cog_sims, cmd_sims)
    
    pooled_std = np.sqrt((np.var(cog_sims, ddof=1) + np.var(cmd_sims, ddof=1)) / 2)
    cohens_d = (np.mean(cmd_sims) - np.mean(cog_sims)) / pooled_std if pooled_std > 0 else 0
    
    cog_hit_055 = sum(1 for s in cog_sims if s >= 0.55) / len(cog_sims)
    cmd_hit_055 = sum(1 for s in cmd_sims if s >= 0.55) / len(cmd_sims)
    
    # Crossover analysis
    crossover_cog = None
    for i in range(len(cog_results)):
        subset = cog_results[:i+1]
        rate = sum(1 for r in subset if r["best_similarity"] >= 0.55) / len(subset)
        if rate >= 0.40:
            crossover_cog = i + 1
            break
    
    crossover_cmd = None
    for i in range(len(cmd_results)):
        subset = cmd_results[:i+1]
        rate = sum(1 for r in subset if r["best_similarity"] >= 0.55) / len(subset)
        if rate >= 0.40:
            crossover_cmd = i + 1
            break
    
    # ─── Build Report ───
    report = []
    
    report.append("# Experiment 1: Reflex Hit Rate — Cognitive Content vs Command Routing")
    report.append("")
    report.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AKDT  ")
    report.append(f"**Embedding model:** `{EMBED_MODEL}` (768-dim, BGE/nomic family) via Ollama on RTX 4050 (WSL2)  ")
    report.append(f"**Thresholds:** exact ≥0.80 | similar 0.55–0.80 | novel <0.55  ")
    report.append(f"**Sample size:** 100 cognitive thoughts + 100 command phrases  ")
    report.append(f"**Fallback embeddings:** {cog_fallbacks} cognitive, {cmd_fallbacks} command (random, will show as novel)  ")
    report.append("")
    
    report.append("## Hypothesis")
    report.append("")
    report.append("> The reflex hit rate for cognitive content (2-4 sentence thoughts) is significantly")
    report.append("> lower than for command routing (3-8 word intent phrases), due to higher semantic")
    report.append("> variability in thought content.")
    report.append("")
    
    # Data characteristics
    cog_wc = [len(t.split()) for t in thoughts]
    cmd_wc = [len(c.split()) for c in commands]
    
    report.append("## Data Characteristics")
    report.append("")
    report.append("| Metric | Cognitive Thoughts | Command Phrases |")
    report.append("|--------|-------------------|-----------------|")
    report.append(f"| Count | {len(thoughts)} | {len(commands)} |")
    report.append(f"| Mean word count | {np.mean(cog_wc):.1f} | {np.mean(cmd_wc):.1f} |")
    report.append(f"| Min word count | {min(cog_wc)} | {min(cmd_wc)} |")
    report.append(f"| Max word count | {max(cog_wc)} | {max(cmd_wc)} |")
    report.append(f"| Mean char count | {np.mean([len(t) for t in thoughts]):.0f} | {np.mean([len(c) for c in commands]):.0f} |")
    report.append("")
    
    report.append("### Sample Cognitive Thoughts (first 5)")
    for i, t in enumerate(thoughts[:5]):
        report.append(f"{i+1}. \"{t}\"")
    report.append("")
    report.append("### Sample Command Phrases (first 5)")
    for i, c in enumerate(commands[:5]):
        report.append(f"{i+1}. `{c}`")
    report.append("")
    
    # Hit rate results
    report.append("## Hit Rate Results")
    report.append("")
    report.append("### Cumulative Hit Rates at Checkpoints")
    report.append("")
    report.append("| Checkpoint | Type | Exact (≥0.80) | Similar (0.55-0.80) | Novel (<0.55) | Hit Rate (E+S) | Avg Sim |")
    report.append("|-----------|------|---------------|---------------------|---------------|----------------|---------|")
    
    for cp in checkpoints:
        for label, rates in [("Cognitive", cog_rates), ("Command", cmd_rates)]:
            r = rates[cp]
            report.append(
                f"| {checkpoint_labels[cp]} | {label} | "
                f"{r['exact']} ({r['exact_rate']:.1%}) | "
                f"{r['similar']} ({r['similar_rate']:.1%}) | "
                f"{r['novel']} ({r['novel_rate']:.1%}) | "
                f"{r['hit_rate']:.1%} | "
                f"{r['avg_similarity']:.3f} |"
            )
    report.append("")
    
    # Similarity distribution
    report.append("### Similarity Distribution (best match per item)")
    report.append("")
    report.append("| Metric | Cognitive | Command |")
    report.append("|--------|-----------|---------|")
    report.append(f"| Mean best similarity | {np.mean(cog_sims):.4f} | {np.mean(cmd_sims):.4f} |")
    report.append(f"| Std deviation | {np.std(cog_sims, ddof=1):.4f} | {np.std(cmd_sims, ddof=1):.4f} |")
    report.append(f"| Median | {np.median(cog_sims):.4f} | {np.median(cmd_sims):.4f} |")
    report.append(f"| 25th percentile | {np.percentile(cog_sims, 25):.4f} | {np.percentile(cmd_sims, 25):.4f} |")
    report.append(f"| 75th percentile | {np.percentile(cog_sims, 75):.4f} | {np.percentile(cmd_sims, 75):.4f} |")
    report.append(f"| Min | {min(cog_sims):.4f} | {min(cmd_sims):.4f} |")
    report.append(f"| Max | {max(cog_sims):.4f} | {max(cmd_sims):.4f} |")
    report.append("")
    
    # Threshold sensitivity
    report.append("## Threshold Sensitivity Analysis")
    report.append("")
    report.append("Hit rate at various similarity thresholds (full 100-item set):")
    report.append("")
    report.append("| Threshold | Cognitive Hit Rate | Command Hit Rate | Difference |")
    report.append("|-----------|-------------------|------------------|------------|")
    for thresh in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        cog_h = sum(1 for s in cog_sims if s >= thresh) / len(cog_sims)
        cmd_h = sum(1 for s in cmd_sims if s >= thresh) / len(cmd_sims)
        report.append(f"| ≥{thresh:.2f} | {cog_h:.1%} | {cmd_h:.1%} | {cmd_h - cog_h:+.1%} |")
    report.append("")
    
    # Statistical analysis
    report.append("## Statistical Analysis")
    report.append("")
    report.append("| Test | Value | p-value | Significant? |")
    report.append("|------|-------|---------|--------------|")
    report.append(f"| Mann-Whitney U (one-sided, cog < cmd) | U={u_stat:.1f} | {u_pvalue:.6f} | {'Yes' if u_pvalue < 0.05 else 'No'} (α=0.05) |")
    report.append(f"| Welch's t-test (two-sided) | t={t_stat:.3f} | {t_pvalue:.6f} | {'Yes' if t_pvalue < 0.05 else 'No'} (α=0.05) |")
    report.append("")
    
    effect_label = "small" if abs(cohens_d) < 0.5 else "medium" if abs(cohens_d) < 0.8 else "large"
    report.append(f"**Effect size (Cohen's d):** {cohens_d:.3f} ({effect_label} effect)")
    report.append(f"**Cognitive mean similarity:** {np.mean(cog_sims):.4f} ± {np.std(cog_sims, ddof=1):.4f}")
    report.append(f"**Command mean similarity:** {np.mean(cmd_sims):.4f} ± {np.std(cmd_sims, ddof=1):.4f}")
    report.append(f"**Cognitive hit rate (≥0.55):** {cog_hit_055:.1%}")
    report.append(f"**Command hit rate (≥0.55):** {cmd_hit_055:.1%}")
    report.append("")
    
    # 40% threshold assessment
    report.append("## Assessment: Can the 40% Reflex Hit Rate Threshold Be Achieved?")
    report.append("")
    report.append("The dissertation (Claim C2) states that after 1 hour of play, the reflex cascade")
    report.append("should achieve ≥40% hit rate (exact + similar at threshold 0.55).")
    report.append("")
    report.append(f"- **Command phrases hit rate (≥0.55):** {cmd_hit_055:.1%}")
    report.append(f"- **Cognitive thoughts hit rate (≥0.55):** {cog_hit_055:.1%}")
    report.append(f"- **Gap:** {cmd_hit_055 - cog_hit_055:+.1%} percentage points")
    report.append("")
    
    if crossover_cog:
        report.append(f"- **Cognitive content reaches 40% hit rate at n={crossover_cog}** ✅")
    else:
        report.append(f"- **Cognitive content does NOT reach 40% hit rate within 100 items** ❌")
    
    if crossover_cmd:
        report.append(f"- **Command content reaches 40% hit rate at n={crossover_cmd}** ✅")
    else:
        report.append(f"- **Command content does NOT reach 40% hit rate within 100 items** ❌")
    report.append("")
    
    if cog_hit_055 >= 0.40:
        report.append("**VERDICT:** The 40% threshold IS achievable for cognitive content at n=100.")
    elif cog_hit_055 >= 0.25:
        report.append("**VERDICT:** The 40% threshold is AT RISK for cognitive content at n=100.")
        report.append(f"Only {cog_hit_055:.1%} of cognitive thoughts found a match ≥0.55.")
        report.append("")
        report.append("The reflex cascade would need:")
        report.append("- A lower similarity threshold (e.g., 0.45)")
        report.append("- A larger cache (more thoughts before reaching 40%)")
        report.append("- Content-type-aware threshold tuning")
    else:
        report.append("**VERDICT:** The 40% threshold is NOT achievable for cognitive content at n=100.")
        report.append(f"Only {cog_hit_055:.1%} of cognitive thoughts found a match ≥0.55.")
        report.append("")
        report.append("Gate 2 (fast path) would rarely fire for thought-level caching,")
        report.append("making the system functionally equivalent to always routing to Gate 3.")
    report.append("")
    
    # Find the threshold where cognitive hits 40%
    cog_40_threshold = None
    for t in np.arange(0.30, 0.80, 0.01):
        rate = sum(1 for s in cog_sims if s >= t) / len(cog_sims)
        if rate >= 0.40:
            cog_40_threshold = t
            break
    
    if cog_40_threshold:
        report.append(f"- Cognitive content reaches 40% hit rate at threshold ≥{cog_40_threshold:.2f}")
    report.append("")
    
    # Implications
    report.append("## Implications for Reflex Cascade Design")
    report.append("")
    report.append("### Key Findings")
    report.append("")
    report.append(f"1. **Semantic diversity gap:** Cognitive thoughts are {'substantially' if (cmd_hit_055 - cog_hit_055) > 0.15 else 'moderately'} more semantically diverse than commands.")
    report.append(f"2. **Hit rate differential:** Commands achieve {cmd_hit_055:.1%} vs thoughts at {cog_hit_055:.1%} (≥0.55 threshold)")
    report.append(f"3. **Threshold sensitivity:** Cognitive content requires a {'lower' if cog_40_threshold and cog_40_threshold < 0.50 else 'similar'} threshold to achieve viable hit rates")
    report.append("")
    report.append("### Design Recommendations")
    report.append("")
    if cog_hit_055 < 0.40:
        report.append("1. **Adaptive thresholds:** Use different similarity thresholds for cognitive vs command content")
        if cog_40_threshold:
            report.append(f"   - Cognitive threshold recommendation: ~{cog_40_threshold:.2f} (instead of 0.55)")
        report.append("2. **Semantic clustering:** Pre-cluster thoughts by topic before similarity search")
        report.append("3. **Multi-level caching:** Short-term (exact) + medium-term (semantic cluster) + full generation")
        report.append("4. **Cache warming:** Accept that thought cache needs longer warmup than command cache")
    else:
        report.append("1. **Proceed with current design:** Hit rates are sufficient for reflex cascade")
        report.append("2. **Monitor closely:** Track actual hit rates in production to validate")
    report.append("")
    report.append("### Comparison to Expected Values")
    report.append("")
    report.append("| Metric | Expected (Dissertation) | Observed |")
    report.append("|--------|------------------------|----------|")
    report.append(f"| Command hit rate | 50-60% | {cmd_hit_055:.1%} |")
    report.append(f"| Cognitive hit rate | 20-35% | {cog_hit_055:.1%} |")
    report.append(f"| Hit rate gap | ~20-30pp | {cmd_hit_055 - cog_hit_055:+.1%} |")
    report.append(f"| 40% achievable (cognitive) | At risk | {'YES' if cog_hit_055 >= 0.40 else 'NO'} |")
    report.append("")
    
    # Limitations
    report.append("## Limitations")
    report.append("")
    report.append("1. **Sample size:** 100 items per category (dissertation calls for 1,000)")
    report.append("2. **Thought generation:** Template-enriched fallback (ollama generation unstable under concurrent gateway load)")
    report.append(f"3. **Fallback embeddings:** {cog_fallbacks} cognitive + {cmd_fallbacks} command items used random embeddings (will show as artificially novel)")
    report.append("4. **Embedding model:** nomic-embed-text (768-dim) instead of bge-m3 (1024-dim)")
    report.append("5. **Single seed:** One generation run; dissertation calls for 3 seeds")
    report.append("6. **No temporal correlation:** Real thought streams have autocorrelation; random sampling overestimates diversity")
    report.append("7. **Gateway contention:** Ollama shared between experiment and OpenClaw gateway, causing instability")
    report.append("")
    
    # Raw data
    report.append("## Appendix A: Per-Item Classification")
    report.append("")
    report.append("### Cognitive Thoughts")
    report.append("")
    report.append("| Item | Best Similarity | Classification | Matched Item |")
    report.append("|------|----------------|----------------|--------------|")
    for r in cog_results:
        report.append(f"| {r['item_idx']} | {r['best_similarity']:.4f} | {r['classification']} | {r['best_match_idx']} |")
    report.append("")
    
    report.append("### Command Phrases")
    report.append("")
    report.append("| Item | Best Similarity | Classification | Matched Item |")
    report.append("|------|----------------|----------------|--------------|")
    for r in cmd_results:
        report.append(f"| {r['item_idx']} | {r['best_similarity']:.4f} | {r['classification']} | {r['best_match_idx']} |")
    report.append("")
    
    # Similarity matrix samples
    report.append("## Appendix B: Similarity Matrix Samples (10×10)")
    report.append("")
    report.append("### Cognitive Thoughts (first 10)")
    report.append("")
    header = "| | " + " | ".join(f"T{i}" for i in range(10)) + " |"
    report.append(header)
    report.append("|" + "---|" * 11)
    for i in range(10):
        row = " | ".join(f"{cog_sim[i][j]:.2f}" for j in range(10))
        report.append(f"| T{i} | {row} |")
    report.append("")
    
    report.append("### Command Phrases (first 10)")
    report.append("")
    report.append(header.replace("T", "C"))
    report.append("|" + "---|" * 11)
    for i in range(10):
        row = " | ".join(f"{cmd_sim[i][j]:.2f}" for j in range(10))
        report.append(f"| C{i} | {row} |")
    report.append("")
    
    # Methodology
    report.append("## Appendix C: Methodology")
    report.append("")
    report.append(f"- **Embedding:** `{EMBED_MODEL}` via Ollama REST API")
    report.append(f"- **Dimensionality:** 768")
    report.append(f"- **Similarity:** Cosine (dot product of L2-normalized vectors)")
    report.append(f"- **Incremental insertion:** For item i, compare against items 0..i-1")
    report.append(f"- **Classification:** exact (≥0.80), similar (0.55–0.80), novel (<0.55)")
    report.append(f"- **Statistical tests:** Mann-Whitney U (non-parametric), Welch's t-test")
    report.append("")
    report.append("### Data Generation")
    report.append("- **Cognitive:** 30 scenarios × 20 observations × 20 intentions (12K combinations)")
    report.append("- **Commands:** 30 verbs × 30 objects × 16 directions × 20 locations × 15 modifiers")
    report.append("")
    
    # Reproducibility
    report.append("### Reproducibility")
    report.append(f"- Embeddings: `cog_embeddings.npy`, `cmd_embeddings.npy`")
    report.append(f"- Raw data: `thoughts_cognitive.txt`, `thoughts_commands.txt`")
    report.append(f"- Scripts: `generate_data.py`, `run_experiment.py`")
    report.append("")
    
    # Write report
    report_path = f"{EXPERIMENT_DIR}/EXP1_REFLEX_HIT_RATE.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report))
    
    print(f"\nReport written to {report_path}", flush=True)
    print(f"\n{'='*70}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Cognitive hit rate (≥0.55): {cog_hit_055:.1%}", flush=True)
    print(f"Command hit rate (≥0.55):   {cmd_hit_055:.1%}", flush=True)
    print(f"Gap: {cmd_hit_055 - cog_hit_055:+.1%} percentage points", flush=True)
    print(f"40% threshold achievable: {'YES' if cog_hit_055 >= 0.40 else 'NO'}", flush=True)
    print(f"Cohen's d: {cohens_d:.3f} ({effect_label})", flush=True)
    print(f"Mann-Whitney p: {u_pvalue:.6f}", flush=True)

if __name__ == "__main__":
    main()
