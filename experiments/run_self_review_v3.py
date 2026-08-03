#!/usr/bin/env python3
"""
Devil's Advocate Self-Review v3: Uses ollama run CLI with stdin pipe.
Much more reliable than the API endpoint.
"""
import json, time, subprocess, sys, os
from datetime import datetime
from pathlib import Path

OUTPUT_JSONL = Path("/home/eileen/projects/thought-amplifier/experiments/SELF_REVIEW_THOUGHTS.jsonl")
MODEL = "granite3.1-dense:2b"

THOUGHTS = [
    {"id": 7, "section": "Section 7.4 - Trust Asymmetry",
     "context": "Trust scoring uses +0.5 for success and -2.0 for failure. 10-observation minimum before updates.",
     "question": "Is the 4:1 penalty-to-reward ratio justified? Could this make the system overly conservative?"},
    {"id": 8, "section": "Section 4 - Formal Model",
     "context": "S = (T, C, W, M, Q, B, L). Gradient is structured intervention delta, not numeric weight update.",
     "question": "Is this formal model rigorous enough? Does it make falsifiable predictions POMDPs cannot?"},
    {"id": 9, "section": "Section 9 - LoRA Distillation",
     "context": "Train LoRA adapters on system's own high-quality thoughts. 10% held-out gain required.",
     "question": "Is held-out evaluation sufficient when held-out data is from the same non-stationary distribution?"},
    {"id": 10, "section": "Section 4.8 - Conservation Laws",
     "context": "Four laws as executable invariants, checked over 1000 cycles.",
     "question": "What is the runtime overhead? Are 1000 cycles enough to catch rare violations?"},
    {"id": 11, "section": "Section 8 - Tempo/MIDI Encoding",
     "context": "Game events as MIDI messages with BPM, velocity, chord tones. Canonized and embedded.",
     "question": "Is the MIDI encoding adding real value or unnecessary complexity? What about simple timestamps?"},
    {"id": 12, "section": "Section 10.1 - Core/Adapter Split",
     "context": "Substrate independence via port contracts. Core speaks only Observation/Thought/Action/Outcome.",
     "question": "Is true substrate independence achievable? Will domain concerns leak through?"},
    {"id": 13, "section": "Section 12.1 - Projected Results",
     "context": "Projects from predecessor systems: 50% zero-cost, 40% reflex, 0.6 trust, 15% improvement.",
     "question": "Are projections from different systems transferable? Could precedents be cherry-picked?"},
    {"id": 14, "section": "Section 11 - Missing Baselines",
     "context": "Evaluation has null adapters and sham arms but no RLHF or continual learning comparison.",
     "question": "How can you claim a new subfield without comparing against existing approaches?"},
    {"id": 15, "section": "Section 10.7 - Browser Tier",
     "context": "Browser finisher via WebLLM+WebGPU generates divergence loss teaching signal.",
     "question": "WebGPU adoption is limited. Is a browser ML tier premature?"},
    {"id": 16, "section": "Section 10.3 - Bottle Ledger Determinism",
     "context": "Append-only .bottle ledger claims byte-for-byte replay determinism.",
     "question": "Can byte-for-byte determinism work with floating-point and OS non-determinism?"},
    {"id": 17, "section": "Section 3.3/12.3 - Quality Scorer Circularity",
     "context": "Quality vector is heuristic. System optimizes for what scorer likes, not what humans like.",
     "question": "How do you break this circular dependency? If scorer is wrong, system optimizes wrongly."},
    {"id": 18, "section": "Section 12.4 - Quality Axes Sensitivity",
     "context": "Four quality axes are plausible but not validated. Factor analysis is future work.",
     "question": "Could the wrong axes doom the system before empirical validation?"},
    {"id": 19, "section": "Section 13.2 - Rejection of Scalar Objectives",
     "context": "DCA rejects scalar objectives as wrong or gameable for open-ended systems.",
     "question": "Could a well-designed scalar reward work? Is the rejection of scalar objectives justified?"},
    {"id": 20, "section": "Overall - Dissertation Assessment",
     "context": "Proposes DCA as new subfield with no empirical results, only projections. Implementation in migration.",
     "question": "What is the single most critical weakness? What is the primary rejection argument?"},
]

def call_granite_cli(prompt: str) -> dict:
    """Call ollama via CLI pipe."""
    start = time.time()
    try:
        result = subprocess.run(
            ["ollama", "run", MODEL],
            input=prompt,
            capture_output=True, text=True, timeout=600
        )
        elapsed = time.time() - start
        response = result.stdout.strip()
        # Rough token estimate: ~4 chars per token
        token_est = len(response) // 4
        return {
            "response": response,
            "eval_count": token_est,
            "eval_duration_ns": 0,
            "latency_s": elapsed,
            "error": None if response else "empty_response"
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {"response": f"TIMEOUT after {elapsed:.0f}s",
                "eval_count": 0, "eval_duration_ns": 0, "latency_s": elapsed, "error": "timeout"}
    except Exception as e:
        elapsed = time.time() - start
        return {"response": f"ERROR: {str(e)[:200]}",
                "eval_count": 0, "eval_duration_ns": 0, "latency_s": elapsed, "error": str(e)[:200]}

def build_prompt(thought: dict) -> str:
    return f"""You are a skeptical PhD reviewer examining a dissertation on Dynamic Cognition Amplification (DCA).

SECTION: {thought['section']}
CLAIM: {thought['context']}
QUESTION: {thought['question']}

Find the SINGLE most serious weakness. Be harsh. Reply in 2-3 sentences only."""

def main():
    # Check what's done
    existing_ids = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("eval_count", 0) > 0:
                        existing_ids.add(rec["id"])
                except:
                    pass
    
    to_run = [t for t in THOUGHTS if t["id"] not in existing_ids]
    
    print(f"=== Devil's Advocate Self-Review v3 (CLI) ===")
    print(f"=== {datetime.now().isoformat()} ===")
    print(f"=== Completed: {sorted(existing_ids)} ===")
    print(f"=== To run: {[t['id'] for t in to_run]} ===")
    print()
    sys.stdout.flush()
    
    jsonl_file = open(OUTPUT_JSONL, "a")
    
    for t in to_run:
        prompt = build_prompt(t)
        result = call_granite_cli(prompt)
        
        record = {
            "id": t["id"],
            "section": t["section"],
            "question": t["question"],
            "context": t["context"],
            "response": result["response"],
            "latency_ms": round(result["latency_s"] * 1000),
            "eval_count": result["eval_count"],
            "eval_duration_s": 0,
            "error": result["error"],
            "timestamp": datetime.now().isoformat(),
            "method": "cli"
        }
        
        jsonl_file.write(json.dumps(record) + "\n")
        jsonl_file.flush()
        
        status = "OK" if not result["error"] else "FAIL"
        print(f"[{t['id']:2d}] {result['latency_s']:.1f}s | ~{result['eval_count']} tok | {status} | {t['section'][:50]}")
        resp_preview = result['response'][:150].replace('\n', ' ')
        print(f"     {resp_preview}")
        print()
        sys.stdout.flush()
    
    jsonl_file.close()
    print(f"=== Done: {datetime.now().isoformat()} ===")

if __name__ == "__main__":
    main()
