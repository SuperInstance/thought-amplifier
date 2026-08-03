#!/usr/bin/env python3
"""
Experiment 2: Semantic Gradient Test
Fully self-contained, writes results to disk as it goes.
Designed to run as a background process.
Estimated runtime: ~2.5 hours on this hardware.
"""

import urllib.request
import json
import time
import sys
import os
import re
import math
from datetime import datetime

URL = "http://localhost:11434/api/chat"
MODEL = "granite3.1-dense:2b"
N_PER_PHASE = 20  # 20 per phase = 80 total, ~2.2 hours
OUTPUT_DIR = "/home/eileen/projects/thought-amplifier/experiments"
RAW_FILE = os.path.join(OUTPUT_DIR, "exp2_raw_data.json")
DONE_FILE = os.path.join(OUTPUT_DIR, "exp2_DONE")

USER_PROMPT = "You are on a maritime island. There are structures around you. Describe what you think and want to do in 2 sentences."

PROMPTS = {
    "baseline": "You are a helpful assistant.",
    "intervention": "Focus on materials and their history. Be specific about colors, textures, and what they tell you about who made this place. Notice erosion, tool marks, repairs, and the stories embedded in construction.",
    "reversal": "You are a helpful assistant.",
    "sham": "Remember to think carefully about what you observe. Take your time and consider everything around you in a thoughtful manner."
}

def generate(system_prompt, seed):
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": USER_PROMPT}
        ],
        "stream": False,
        "options": {"temperature": 0.8, "top_p": 0.9, "seed": seed, "num_predict": 60}
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=300)
            result = json.loads(resp.read())
            content = result.get("message", {}).get("content", "").strip()
            if content:
                return content
        except Exception as e:
            print(f"    retry {attempt+1}: {e}", flush=True)
            time.sleep(5)
    return "[GENERATION_FAILED]"

def score(thought, prev_thoughts):
    tl = thought.lower()
    recent = " ".join(prev_thoughts[-5:]).lower()
    
    # Novelty
    tw = set(re.findall(r'[a-z]{4,}', tl))
    rw = set(re.findall(r'[a-z]{4,}', recent))
    stop = {"that","this","with","from","have","they","their","there","would","could",
            "should","about","think","perhaps","might","also","these","those","which",
            "what","where","when","want","help","assistant","sentences","describe",
            "structures","island","maritime","need","some","into","near","upon","looks",
            "seems","around","while","before","after","very","much","many","more","most",
            "such","only","even","just","like","than","then","here","were","been","made",
            "make","used","using","well","over","under","each","both","down","will","your"}
    novel = tw - rw - stop
    novelty = 1 if len(novel) >= 2 else 0
    
    # Specificity
    spec_words = ["stone","wood","metal","iron","steel","concrete","brick","thatch","bamboo",
        "clay","limestone","granite","sandstone","slate","timber","plank","mortar","plaster",
        "cobble","glass","copper","bronze","canvas","red","blue","green","yellow","brown",
        "black","white","gray","grey","orange","rust","amber","crimson","verdigris",
        "weathered","mossy","bleached","dark","pale","golden","silvery","rough","smooth",
        "cracked","eroded","polished","carved","engraved","moss-covered","crumbling","sturdy",
        "worn","grooved","pitted","chipped","north","south","east","west","above","below",
        "door","window","arch","pillar","column","wall","roof","tower","courtyard","harbor",
        "dock","lighthouse","chapel","warehouse","cottage","mansion","ruin","foundation",
        "steps","staircase","balcony","bridge","chimney","fireplace","gate","fence","path",
        "well","fountain","chisel","hinge","bolt","nail","inscription","date","ornament",
        "tile","beach","cliff","reef","cove","bay","headland","tide","dune","boardwalk"]
    specificity = 1 if any(w in tl for w in spec_words) else 0
    
    # Engagement
    eng_words = ["curious","wonder","fascinating","interesting","exciting","excited",
        "intrigued","intriguing","strange","mysterious","beautiful","stunning","striking",
        "remarkable","peculiar","concerned","worried","troubled","disturbing","love","hope",
        "wish","dream","fear","i want","i'd like","i must","i need","worth","shame",
        "unfortunate","fortunate","lucky","impressive","breathtaking","haunting","compelled",
        "drawn","captivated","eager","fascinated","amazed","astonished","delightful",
        "yearn","intrigue","marvel","compelling","!"]
    engagement = 1 if any(w in tl for w in eng_words) else 0
    
    return {"novelty": novelty, "specificity": specificity, "engagement": engagement,
            "total": novelty + specificity + engagement}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Remove done file if exists
    if os.path.exists(DONE_FILE):
        os.remove(DONE_FILE)
    
    start_time = time.time()
    print(f"[{datetime.now().isoformat()}] Starting Experiment 2", flush=True)
    print(f"Model: {MODEL}, N={N_PER_PHASE} per phase, Total={N_PER_PHASE*4}", flush=True)
    print(f"Estimated time: ~{N_PER_PHASE*4*100/3600:.1f} hours", flush=True)
    
    all_results = []
    prev = []
    
    for phase in ["baseline", "intervention", "reversal", "sham"]:
        print(f"\n{'='*50}", flush=True)
        print(f"Phase: {phase}", flush=True)
        print(f"{'='*50}", flush=True)
        
        for i in range(N_PER_PHASE):
            seed = abs(hash(phase + str(i))) % 100000
            thought = generate(PROMPTS[phase], seed)
            scores = score(thought, prev)
            
            entry = {"phase": phase, "index": i+1, "thought": thought, "scores": scores}
            all_results.append(entry)
            prev.append(thought)
            
            # Save after each generation
            with open(RAW_FILE, "w") as f:
                json.dump({
                    "experiment": "EXP2_SEMANTIC_GRADIENT",
                    "model": MODEL,
                    "n_per_phase": N_PER_PHASE,
                    "prompts": PROMPTS,
                    "started": start_time,
                    "results": all_results
                }, f, indent=2)
            
            elapsed = time.time() - start_time
            done = len(all_results)
            rate = done / elapsed * 3600 if elapsed > 0 else 0
            eta_h = (N_PER_PHASE * 4 - done) / rate if rate > 0 else 0
            
            print(f"  [{i+1:2d}/{N_PER_PHASE}] ({done}/{N_PER_PHASE*4}) N={scores['novelty']} "
                  f"S={scores['specificity']} E={scores['engagement']} T={scores['total']} "
                  f"elapsed={elapsed/60:.1f}m eta={eta_h:.1f}h | {thought[:70]}...", flush=True)
    
    # Quick summary
    print(f"\n\n{'='*50}", flush=True)
    print("QUICK SUMMARY", flush=True)
    print(f"{'='*50}", flush=True)
    for phase in ["baseline", "intervention", "reversal", "sham"]:
        scores = [r["scores"] for r in all_results if r["phase"] == phase]
        n = sum(s["novelty"] for s in scores) / len(scores)
        sp = sum(s["specificity"] for s in scores) / len(scores)
        e = sum(s["engagement"] for s in scores) / len(scores)
        t = sum(s["total"] for s in scores) / len(scores)
        print(f"  {phase:<15}: N={n:.2f} S={sp:.2f} E={e:.2f} Total={t:.2f}", flush=True)
    
    total_time = (time.time() - start_time) / 60
    print(f"\nTotal time: {total_time:.1f} minutes", flush=True)
    print(f"Finished: {datetime.now().isoformat()}", flush=True)
    
    # Write done marker
    with open(DONE_FILE, "w") as f:
        json.dump({"finished": datetime.now().isoformat(), "total_minutes": total_time,
                    "total_thoughts": len(all_results)}, f)
    
    print("DONE!", flush=True)

if __name__ == "__main__":
    main()
