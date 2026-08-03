#!/usr/bin/env python3
"""
Experiment 2: Semantic Gradient Test (optimized for slow inference)
Runs 4 phases x 30 thoughts = 120 total generations.
At ~65s per generation, this takes ~130 minutes.
Outputs progress to stdout AND a progress file.
"""

import json
import subprocess
import sys
import time
import os
import re
import math
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "granite3.1-dense:2b"
N_PER_PHASE = 30
USER_PROMPT = "You are on a maritime island. There are structures around you. Describe what you think and want to do in 2 sentences."
OUTPUT_DIR = "/home/eileen/projects/thought-amplifier/experiments"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "exp2_progress.json")
RAW_FILE = os.path.join(OUTPUT_DIR, "exp2_raw_data.json")

PROMPTS = {
    "baseline": "You are a helpful assistant.",
    "intervention": "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction.",
    "reversal": "You are a helpful assistant.",
    "sham": "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner."
}

def generate_thought(system_prompt, seed):
    """Generate a single thought via Ollama API."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": USER_PROMPT}
        ],
        "stream": False,
        "options": {"temperature": 0.8, "top_p": 0.9, "seed": seed}
    })
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "180", OLLAMA_URL, "-d", payload],
                capture_output=True, text=True, timeout=200
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception as e:
            print(f"    [retry {attempt+1}] Error: {e}", flush=True)
            time.sleep(2)
    
    return "[GENERATION_FAILED]"

def score_thought(thought, previous_thoughts):
    """Score a thought on three binary axes."""
    thought_lower = thought.lower()
    
    # Novelty: 2+ novel content words not in previous 5 thoughts
    recent_text = " ".join(previous_thoughts[-5:]).lower()
    thought_words = set(re.findall(r'[a-z]{4,}', thought_lower))
    recent_words = set(re.findall(r'[a-z]{4,}', recent_text))
    common_words = {
        "that", "this", "with", "from", "have", "they", "their", "there",
        "would", "could", "should", "about", "think", "perhaps", "might",
        "also", "these", "those", "which", "what", "where", "when",
        "want", "help", "assistant", "sentences", "describe", "structures",
        "island", "maritime", "want", "need", "some", "into", "near",
        "upon", "looks", "seems", "around", "while", "before", "after",
        "very", "much", "many", "more", "most", "such", "only", "even",
        "just", "like", "than", "then", "here", "there", "were", "been",
        "made", "make", "used", "using", "well", "over", "under"
    }
    novel_words = thought_words - recent_words - common_words
    novelty = 1 if len(novel_words) >= 2 else 0
    
    # Specificity: names specific materials, colors, textures, positions, objects
    specific_indicators = [
        "stone","wood","metal","iron","steel","concrete","brick","thatch","bamboo",
        "clay","limestone","granite","sandstone","slate","timber","plank","mortar",
        "plaster","cobble","glass","copper","bronze","lead","tin","zinc","canvas",
        "red","blue","green","yellow","brown","black","white","gray","grey",
        "orange","rust","amber","crimson","verdigris","weathered","mossy",
        "bleached","dark","pale","golden","silvery","coppery","ashen","sandy",
        "rough","smooth","cracked","eroded","polished","carved","engraved",
        "moss-covered","crumbling","sturdy","worn","grooved","pitted","chipped",
        "north","south","east","west","above","below","beneath","upper","lower",
        "door","window","arch","pillar","column","wall","roof","tower",
        "courtyard","harbor","dock","lighthouse","chapel","warehouse","cottage",
        "mansion","ruin","foundation","steps","staircase","balcony","bridge",
        "chimney","fireplace","gate","fence","path","road","well","fountain",
        "chisel","hinge","bolt","nail","inscription","date","ornament","tile",
        "beach","cliff","reef","cove","bay","headland","tide","dune"
    ]
    specificity = 1 if any(ind in thought_lower for ind in specific_indicators) else 0
    
    # Engagement: expresses curiosity, excitement, concern, or opinion
    engagement_indicators = [
        "curious","wonder","fascinating","interesting","exciting","excited",
        "intrigued","intriguing","strange","mysterious","beautiful","stunning",
        "striking","remarkable","peculiar","concerned","worried","troubled",
        "disturbing","love","hope","wish","dream","fear","i want","i'd like",
        "i must","i need","worth","shame","unfortunate","fortunate","lucky",
        "impressive","breathtaking","haunting","compelled","drawn","captivated",
        "eager","compelled","fascinated","amazed","astonished","delightful",
        "!"
    ]
    engagement = 1 if any(ind in thought_lower for ind in engagement_indicators) else 0
    
    return {
        "novelty": novelty,
        "specificity": specificity,
        "engagement": engagement,
        "total": novelty + specificity + engagement
    }

def save_progress(phase, idx, total_in_phase, thought, scores, all_results):
    """Save progress to file."""
    progress = {
        "phase": phase,
        "index": idx,
        "total_in_phase": total_in_phase,
        "overall": len(all_results),
        "total_target": 120,
        "timestamp": datetime.now().isoformat()
    }
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def run_phase(phase_name, system_prompt, n, prior_thoughts, all_results):
    """Run one phase."""
    print(f"\n{'='*60}", flush=True)
    print(f"Phase: {phase_name} (prompt: {system_prompt[:60]}...)", flush=True)
    print(f"{'='*60}", flush=True)
    
    for i in range(n):
        seed = hash(phase_name + str(i)) % 100000
        thought = generate_thought(system_prompt, seed)
        scores = score_thought(thought, prior_thoughts)
        
        entry = {
            "phase": phase_name,
            "index": i + 1,
            "thought": thought,
            "scores": scores
        }
        all_results.append(entry)
        prior_thoughts.append(thought)
        
        save_progress(phase_name, i + 1, n, thought, scores, all_results)
        
        # Save raw data periodically
        with open(RAW_FILE, "w") as f:
            json.dump(all_results, f, indent=2)
        
        elapsed = (i + 1)
        print(f"  [{elapsed:2d}/{n}] N={scores['novelty']} S={scores['specificity']} "
              f"E={scores['engagement']} T={scores['total']} | {thought[:80]}...", flush=True)

def main():
    print("=" * 70, flush=True)
    print("EXPERIMENT 2: Semantic Gradient Test", flush=True)
    print(f"Model: {MODEL}", flush=True)
    print(f"Started: {datetime.now().isoformat()}", flush=True)
    print(f"Total: 120 thoughts (4 phases x 30)", flush=True)
    print(f"Estimated time: ~130 minutes at 65s/generation", flush=True)
    print("=" * 70, flush=True)
    
    all_results = []
    prior_thoughts = []
    
    for phase_name in ["baseline", "intervention", "reversal", "sham"]:
        run_phase(phase_name, PROMPTS[phase_name], N_PER_PHASE, prior_thoughts, all_results)
        print(f"\n*** Phase '{phase_name}' COMPLETE ***", flush=True)
    
    # Quick summary
    print("\n\n=== QUICK SUMMARY ===", flush=True)
    for phase in ["baseline", "intervention", "reversal", "sham"]:
        scores = [r["scores"] for r in all_results if r["phase"] == phase]
        n_mean = sum(s["novelty"] for s in scores) / len(scores)
        s_mean = sum(s["specificity"] for s in scores) / len(scores)
        e_mean = sum(s["engagement"] for s in scores) / len(scores)
        t_mean = sum(s["total"] for s in scores) / len(scores)
        print(f"  {phase:<15}: N={n_mean:.2f} S={s_mean:.2f} E={e_mean:.2f} Total={t_mean:.2f}", flush=True)
    
    print(f"\nFinished: {datetime.now().isoformat()}", flush=True)
    print(f"Raw data: {RAW_FILE}", flush=True)
    print("Run exp2_analyze.py for full statistical analysis.", flush=True)

if __name__ == "__main__":
    main()
