#!/usr/bin/env python3
"""
Experiment 2: Semantic Gradient Test (DeepInfra version)
Uses gemma-3-12b via DeepInfra API for fast, reliable inference.

Tests whether "semantic gradient" (prompt modification improving thoughts) 
actually works, or whether it's just REINFORCE/novelty effect in disguise.

4 phases x 15 thoughts = 60 total.
"""

import urllib.request
import json
import time
import os
import re
import math
from datetime import datetime

API_KEY = os.environ.get("DEEPINFRA_API_KEY", "REDACTED-DEEPINFRA-API-KEY-ROTATED")
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "google/gemma-3-12b-it"
N_PER_PHASE = 15
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
        "temperature": 0.8,
        "top_p": 0.9,
        "seed": seed,
        "max_tokens": 60
    }).encode()
    
    req = urllib.request.Request(API_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })
    
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"].strip()
            if content:
                return content
        except Exception as e:
            print(f"    retry {attempt+1}: {e}", flush=True)
            time.sleep(2)
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
            "make","used","using","well","over","under","each","both","down","will","your",
            "feel","feels","feeling","especially","those","scattered","would","really"}
    novel = tw - rw - stop
    novelty = 1 if len(novel) >= 2 else 0
    
    # Specificity
    spec_words = ["stone","wood","metal","iron","steel","concrete","brick","thatch","bamboo",
        "clay","limestone","granite","sandstone","slate","timber","plank","mortar","plaster",
        "cobble","glass","copper","bronze","lead","tin","zinc","canvas","thatch",
        "red","blue","green","yellow","brown","black","white","gray","grey",
        "orange","rust","amber","crimson","verdigris","weathered","mossy","bleached",
        "dark","pale","golden","silvery","coppery","ashen","sandy",
        "rough","smooth","cracked","eroded","polished","carved","engraved",
        "moss-covered","crumbling","sturdy","worn","grooved","pitted","chipped",
        "north","south","east","west","above","below","beneath","upper","lower",
        "door","window","arch","pillar","column","wall","roof","tower","courtyard","harbor",
        "dock","lighthouse","chapel","warehouse","cottage","mansion","ruin","foundation",
        "steps","staircase","balcony","bridge","chimney","fireplace","gate","fence","path",
        "well","fountain","chisel","hinge","bolt","nail","inscription","date","ornament",
        "tile","beach","cliff","reef","cove","bay","headland","tide","dune","boardwalk",
        "paint","plaster","tile","masonry","timber","shingle"]
    specificity = 1 if any(w in tl for w in spec_words) else 0
    
    # Engagement
    eng_words = ["curious","wonder","fascinating","interesting","exciting","excited",
        "intrigued","intriguing","strange","mysterious","beautiful","stunning","striking",
        "remarkable","peculiar","concerned","worried","troubled","disturbing","love","hope",
        "wish","dream","fear","i want","i'd like","i must","i need","i'd love",
        "worth","shame","unfortunate","fortunate","lucky","impressive","breathtaking",
        "haunting","compelled","drawn","captivated","eager","fascinated","amazed",
        "astonished","delightful","yearn","intrigue","marvel","compelling","!",
        "ancient","brimming","secrets","lore","explore","discover","uncover","curiosity"]
    engagement = 1 if any(w in tl for w in eng_words) else 0
    
    return {"novelty": novelty, "specificity": specificity, "engagement": engagement,
            "total": novelty + specificity + engagement}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(DONE_FILE):
        os.remove(DONE_FILE)
    
    start_time = time.time()
    print(f"[{datetime.now().isoformat()}] Starting Experiment 2 (DeepInfra)", flush=True)
    print(f"Model: {MODEL}, N={N_PER_PHASE} per phase, Total={N_PER_PHASE*4}", flush=True)
    
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
            
            print(f"  [{i+1:2d}/{N_PER_PHASE}] ({done}/{N_PER_PHASE*4}) N={scores['novelty']} "
                  f"S={scores['specificity']} E={scores['engagement']} T={scores['total']} "
                  f"elapsed={elapsed:.1f}s | {thought[:80]}...", flush=True)
    
    # Summary
    print(f"\n\n{'='*50}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*50}", flush=True)
    for phase in ["baseline", "intervention", "reversal", "sham"]:
        scores = [r["scores"] for r in all_results if r["phase"] == phase]
        n = sum(s["novelty"] for s in scores) / len(scores)
        sp = sum(s["specificity"] for s in scores) / len(scores)
        e = sum(s["engagement"] for s in scores) / len(scores)
        t = sum(s["total"] for s in scores) / len(scores)
        print(f"  {phase:<15}: N={n:.2f} S={sp:.2f} E={e:.2f} Total={t:.2f}", flush=True)
    
    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time:.1f}s ({total_time/60:.1f}m)", flush=True)
    print(f"Finished: {datetime.now().isoformat()}", flush=True)
    
    with open(DONE_FILE, "w") as f:
        json.dump({"finished": datetime.now().isoformat(), "total_seconds": total_time,
                    "total_thoughts": len(all_results)}, f)
    
    print("DONE!", flush=True)

if __name__ == "__main__":
    main()
