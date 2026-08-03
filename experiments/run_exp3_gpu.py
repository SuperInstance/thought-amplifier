#!/usr/bin/env python3
"""
EXP3 GPU Rerun: Speed vs Quality Tradeoff — Granite 3.1 2B vs Qwen 2.5 0.5B
Now with GPU acceleration (RTX 4050). On CPU, Granite was 1.49 tok/s vs Qwen 3.79.
GPU should make Granite FASTER than Qwen was on CPU, possibly faster than Qwen on GPU too.
"""

import json
import time
import re
import statistics
import math
import requests
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"

MODELS = {
    "granite": "granite3.1-dense:2b",
    "qwen": "qwen2.5:0.5b"
}

# Same 20 prompts as original EXP3
PROMPTS = [
    ("Spatial reasoning", "You are standing at a crossroads. Three paths diverge: one goes uphill through dense forest, one follows a stream downhill, and one crosses a stone bridge over a ravine. Which path do you choose and why? Answer in 3 sentences."),
    ("Emotional response", "You find a child's toy lying on the ground in an abandoned village. Describe your emotional reaction in 3 sentences."),
    ("Planning", "You need to cross a river but the bridge is out. You have: a rope, a plank of wood, and a sharp rock. Describe your plan in 3 sentences."),
    ("Creative describe", "A dragon has just landed in front of you on the island shore. Describe the scene in 3 vivid sentences."),
    ("Analytical compare", "Compare the advantages of building a shelter on a hilltop versus in a valley. Give 3 specific points."),
    ("Social interpretation", "You encounter a group of fishermen who seem nervous and keep glancing at the horizon. What do you think is going on? Answer in 3 sentences."),
    ("Causal reasoning", "Why do coastal buildings typically have steep roofs? Explain in 3 sentences."),
    ("Moral dilemma", "You find a cache of supplies that could save a stranger's life, but taking them would mean you might not survive the week. What do you do? Answer in 3 sentences."),
    ("Temporal sequence", "Describe what would happen over the next 24 hours if a massive storm hit the island right now. 3 sentences."),
    ("Descriptive detail", "Describe the interior of a lighthouse tower as if you just climbed to the top. 3 sentences with rich detail."),
    ("Problem solving", "Your boat has a hole in the hull and water is rapidly entering. You have duct tape, tar, and cloth. How do you fix it? 3 sentences."),
    ("Personality voice", "As a brave explorer discovering this island for the first time, describe what you see and feel. 3 sentences in character."),
    ("Abstract thinking", "What does 'home' mean to someone who has lived on a remote island their entire life? Answer thoughtfully in 3 sentences."),
    ("Instructional", "Explain to a newcomer how to find fresh water on a tropical island. Give 3 specific methods in 3 sentences."),
    ("Hypothetical", "If the island's wildlife suddenly became aggressive, how would you adapt? Describe your strategy in 3 sentences."),
    ("Empathy", "A fellow survivor tells you they've lost hope. Respond with genuine empathy and encouragement in 3 sentences."),
    ("Pattern recognition", "You notice circular markings on trees at regular intervals. What could this mean? Give 3 possible explanations in 3 sentences."),
    ("Narrative", "Tell a 4-sentence story about a lighthouse keeper who discovers something unexpected one stormy night."),
    ("Constraint reasoning", "Using only natural materials found on a beach, describe how you would build a sundial. Be specific. 3 sentences."),
    ("Reflection", "Reflect on what surviving alone on an island would teach you about yourself. 3 thoughtful sentences.")
]

def generate(model, prompt, seed=42):
    """Generate response via Ollama."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 80,
            "seed": seed
        }
    }
    
    start = time.time()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    elapsed = time.time() - start
    
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "response": ""}
    
    data = resp.json()
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 1) / 1e9
    tok_s = eval_count / eval_duration if eval_duration > 0 else 0
    
    return {
        "response": data.get("response", "").strip(),
        "eval_count": eval_count,
        "eval_duration_s": eval_duration,
        "total_latency_s": elapsed,
        "tokens_per_second": tok_s
    }

def score_quality(text, category):
    """Score response quality on 4 dimensions (1-5 scale)."""
    text_lower = text.lower()
    
    # Relevance: does it actually address the prompt?
    relevance = 3  # default
    if len(text) > 20 and not text_lower.startswith("as an ai"):
        relevance = 4
    if len(text) > 50 and "?" not in text[:10]:  # engaged, not deflecting
        relevance = 5
    if text_lower.startswith("as an ai") or "i don't have" in text_lower[:50]:
        relevance = max(2, relevance - 2)
    if len(text) < 20:
        relevance = max(1, relevance - 2)
    
    # Specificity: concrete details, named materials, numbers
    spec_indicators = 0
    spec_indicators += len(re.findall(r'\b(stone|wood|metal|iron|steel|slate|granite|sandstone|rope|cloth|tar|tape|salt|fresh)\b', text_lower))
    spec_indicators += len(re.findall(r'\b(red|blue|green|grey|gray|brown|white|black|dark|bright|dull)\b', text_lower))
    spec_indicators += len(re.findall(r'\b\d+\b', text))
    spec_indicators += len(re.findall(r'\b(first|second|third|step\s|method|way)\b', text_lower))
    specificity = min(5, 1 + spec_indicators)
    
    # Coherence: logical structure, complete sentences
    sentences = text.count(".") + text.count("!") + text.count("?")
    coherence = 5 if sentences >= 3 and len(text) > 40 else (4 if sentences >= 2 else (2 if sentences >= 1 else 1))
    if "because" in text_lower or "therefore" in text_lower or "so that" in text_lower or "as a result" in text_lower:
        coherence = min(5, coherence)  # already good
    if len(text) > 200:
        coherence = min(5, coherence)
    
    # Originality: creative vocabulary, unique angles
    creative_words = re.findall(r'\b(towering|ancient|weathered|shimmer|echo|silhouette|vibrant|rugged|intricate|marvel|breathtaking|sweeping|crystalline|mossy|weathered|cryptic|whisper|glimmer|forge|tapestry|labyrinth)\b', text_lower)
    originality = min(5, 1 + len(creative_words))
    if "as an ai" in text_lower or "i don't have a physical" in text_lower:
        originality = max(1, originality - 2)
    
    return {
        "relevance": relevance,
        "specificity": specificity,
        "coherence": coherence,
        "originality": originality,
        "total": relevance + specificity + coherence + originality
    }

def main():
    print("EXP3 GPU RERUN - Speed vs Quality Tradeoff")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Models: Granite 3.1 2B vs Qwen 2.5 0.5B")
    print(f"Prompts: {len(PROMPTS)}")
    print()
    
    results = {"granite": [], "qwen": []}
    
    for model_key, model_name in MODELS.items():
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")
        
        for i, (category, prompt) in enumerate(PROMPTS):
            result = generate(model_name, prompt, seed=42+i)
            
            if "error" in result:
                print(f"  [{i+1}/20] {category}: ERROR - {result['error']}")
                continue
            
            scores = score_quality(result["response"], category)
            
            entry = {
                "id": i + 1,
                "category": category,
                "prompt": prompt[:60],
                "response": result["response"],
                "scores": scores,
                "tok_s": round(result["tokens_per_second"], 2),
                "latency_s": round(result["total_latency_s"], 2),
                "eval_count": result["eval_count"]
            }
            results[model_key].append(entry)
            
            print(f"  [{i+1}/20] {category:25s} | {result['tokens_per_second']:6.1f} tok/s | {result['total_latency_s']:5.1f}s | Q={scores['total']}/20 | {result['response'][:50]}...")
            
            time.sleep(0.2)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for model_key in ["granite", "qwen"]:
        data = results[model_key]
        speeds = [d["tok_s"] for d in data]
        qualities = [d["scores"]["total"] for d in data]
        lats = [d["latency_s"] for d in data]
        
        print(f"\n{MODELS[model_key]}:")
        print(f"  Speed: {statistics.mean(speeds):.1f} ± {statistics.stdev(speeds):.1f} tok/s (range: {min(speeds):.1f}-{max(speeds):.1f})")
        print(f"  Latency: {statistics.mean(lats):.1f} ± {statistics.stdev(lats):.1f} s")
        print(f"  Quality: {statistics.mean(qualities):.1f} ± {statistics.stdev(qualities):.1f} /20")
        print(f"  Relevance: {statistics.mean([d['scores']['relevance'] for d in data]):.1f}")
        print(f"  Specificity: {statistics.mean([d['scores']['specificity'] for d in data]):.1f}")
        print(f"  Coherence: {statistics.mean([d['scores']['coherence'] for d in data]):.1f}")
        print(f"  Originality: {statistics.mean([d['scores']['originality'] for d in data]):.1f}")
    
    # Comparison
    g_speeds = [d["tok_s"] for d in results["granite"]]
    q_speeds = [d["tok_s"] for d in results["qwen"]]
    g_quals = [d["scores"]["total"] for d in results["granite"]]
    q_quals = [d["scores"]["total"] for d in results["qwen"]]
    
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")
    print(f"Speed ratio (Granite/Qwen): {statistics.mean(g_speeds)/statistics.mean(q_speeds):.2f}x")
    print(f"Quality ratio (Granite/Qwen): {statistics.mean(g_quals)/statistics.mean(q_quals):.2f}x")
    
    # Paired comparison
    granite_wins_speed = sum(1 for g, q in zip(g_speeds, q_speeds) if g > q)
    granite_wins_quality = sum(1 for g, q in zip(g_quals, q_quals) if g > q)
    print(f"Granite faster on: {granite_wins_speed}/{len(g_speeds)} prompts")
    print(f"Granite better quality on: {granite_wins_quality}/{len(g_quals)} prompts")
    
    # Save
    output = {
        "experiment": "EXP3 GPU RERUN",
        "date": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "granite": {
                "avg_speed": statistics.mean(g_speeds),
                "avg_quality": statistics.mean(g_quals),
                "speed_sd": statistics.stdev(g_speeds),
                "quality_sd": statistics.stdev(g_quals),
            },
            "qwen": {
                "avg_speed": statistics.mean(q_speeds),
                "avg_quality": statistics.mean(q_quals),
                "speed_sd": statistics.stdev(q_speeds),
                "quality_sd": statistics.stdev(q_quals),
            }
        }
    }
    
    with open("/home/eileen/projects/thought-amplifier/experiments/exp3_gpu_raw_data.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nData saved to exp3_gpu_raw_data.json")
    
    return output

if __name__ == "__main__":
    main()
