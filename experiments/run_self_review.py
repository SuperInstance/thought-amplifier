#!/usr/bin/env python3
"""
Devil's Advocate Self-Review: 20 thought cycles with Granite 3.1
Uses subprocess+curl for reliability with Ollama.
"""
import json, time, subprocess, sys, os, tempfile
from datetime import datetime
from pathlib import Path

OUTPUT_JSONL = Path("/home/eileen/projects/thought-amplifier/experiments/SELF_REVIEW_THOUGHTS.jsonl")
OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "granite3.1-dense:2b"

THOUGHTS = [
    {
        "id": 1,
        "section": "Abstract - New Subfield Claim",
        "context": "DCA is proposed as a new subfield of ML where a small fast process thinks continuously while a larger slower process modifies the conditions under which the fast process thinks. It formalizes this as a dual-time-scale system with a quality vector instead of scalar loss.",
        "question": "Is this genuinely a NEW subfield, or is it just a reinvention of existing ideas (meta-learning, RLHF, continual learning) with new vocabulary? What specific property has NOT been studied before?"
    },
    {
        "id": 2,
        "section": "Section 3.3 - Quality Vector",
        "context": "The quality vector has 4 axes: novelty (cosine distance from recent thoughts), specificity (concrete noun density), engagement (emotional salience), and spatial awareness (position references). These replace scalar loss as the training signal.",
        "question": "Are these 4 axes validated? What happens if specificity and novelty are correlated? Is the decomposition orthogonal?"
    },
    {
        "id": 3,
        "section": "Section 3.6/7.3 - Sham Interventions",
        "context": "DCA uses sham interventions (logging an intervention but not applying it) as a control arm. The real effect is measured as (q_after - q_before) minus (q_sham - q_before).",
        "question": "Can a sham arm isolate causal effects when the system state is non-stationary and previous interventions already changed the distribution?"
    },
    {
        "id": 4,
        "section": "Section 5 - Three-Gate Cascade",
        "context": "The three-gate cascade promises >=50% of decisions at zero cost after 1 hour. Gate 1 is reflex dispatch, Gate 2 is compiled policy lookup, Gate 3 is LLM inference.",
        "question": "What happens in a genuinely open-ended creative environment where novelty is the norm? Does the cascade fail to amortize cost?"
    },
    {
        "id": 5,
        "section": "Section 5.3 - Confidence Dynamics",
        "context": "Reflex confidence updates: +0.05(1-c) on success, -0.10c on failure, clamped to [0.05, 0.95]. This is chosen over Pincher's multiplicative form.",
        "question": "Is this update rule theoretically justified? What are its convergence properties? Is it purely heuristic?"
    },
    {
        "id": 6,
        "section": "Section 6.4 - Evolution Score Update",
        "context": "The evolution engine uses EMA with alpha=0.05 and clamps to [0.05, 0.95]. The dissertation claims this works across Tic-Tac-Toe, Connect 4, Go 9x9, and Hold'em.",
        "question": "Does a single EMA update rule generalize across games with radically different complexity?"
    },
    {
        "id": 7,
        "section": "Section 7.4 - Trust Asymmetry",
        "context": "Trust scoring uses +0.5 for success and -2.0 for failure, requiring ~4 successes per failure. Updates wait for 10 observations minimum.",
        "question": "Is the 4:1 penalty-to-reward ratio justified? Could this make the system overly conservative?"
    },
    {
        "id": 8,
        "section": "Section 4 - Formal Model",
        "context": "The formal model defines S = (T, C, W, M, Q, B, L) with thought generation, conductor interventions, quality scoring, and conservation laws.",
        "question": "Is this formal model rigorous enough? Does it make falsifiable predictions that POMDPs or meta-RL cannot?"
    },
    {
        "id": 9,
        "section": "Section 9 - LoRA Distillation",
        "context": "DCA proposes training LoRA adapters on the system's own high-quality thoughts. A 10% held-out gain is required for promotion.",
        "question": "Is held-out evaluation sufficient when the held-out set comes from the same non-stationary distribution?"
    },
    {
        "id": 10,
        "section": "Section 4.8 - Conservation Laws",
        "context": "Four conservation laws (token, action, identity, evolution) are executable runtime invariants checked by property tests over 1000 cycles.",
        "question": "What is the runtime overhead? Are 1000-cycle property tests sufficient to catch rare violations?"
    },
    {
        "id": 11,
        "section": "Section 8 - Tempo/MIDI Encoding",
        "context": "Game events are encoded as MIDI-like messages with BPM, beat positions, velocity, and chord tones. Sessions are canonized into strings and embedded.",
        "question": "Is the MIDI encoding adding real value or is it unnecessary complexity? What would be lost with simple timestamps?"
    },
    {
        "id": 12,
        "section": "Section 10.1 - Core/Adapter Split",
        "context": "The system claims substrate independence via port contracts. The core speaks only Observation/Thought/Action/Outcome.",
        "question": "Is true substrate independence achievable? Will domain-specific concerns always leak through?"
    },
    {
        "id": 13,
        "section": "Section 12.1 - Projected Results",
        "context": "DCA projects 50% zero-cost decisions, 40% reflex hit rate, 0.6 trust-quality correlation, 15% policy improvement from predecessor systems.",
        "question": "Are projections from different systems transferable to DCA? What if the precedents are cherry-picked?"
    },
    {
        "id": 14,
        "section": "Section 11 - Missing Baselines",
        "context": "The evaluation protocol includes null adapters and sham arms, but no direct comparison to RLHF or continual learning.",
        "question": "How can you claim a new subfield without comparing against existing approaches on the same task?"
    },
    {
        "id": 15,
        "section": "Section 10.7 - Browser Tier",
        "context": "A browser finisher model runs via WebLLM+WebGPU, generating divergence loss as a teaching signal.",
        "question": "WebGPU adoption is limited. Is building an entire tier on browser ML premature?"
    },
    {
        "id": 16,
        "section": "Section 10.3 - Bottle Ledger Determinism",
        "context": "The .bottle ledger is append-only. Under the null adapter, the system claims byte-for-byte replay determinism.",
        "question": "Can true byte-for-byte determinism be achieved given floating-point non-determinism and OS-level differences?"
    },
    {
        "id": 17,
        "section": "Section 3.3/12.3 - Quality Scorer Circularity",
        "context": "The quality vector is heuristic. The system learns what the quality scorer likes, which may diverge from what humans like.",
        "question": "How do you break this circular dependency? If the scorer is wrong, the entire system optimizes wrongly."
    },
    {
        "id": 18,
        "section": "Section 12.4 - Quality Axes Sensitivity",
        "context": "The four quality axes are described as plausible but not validated. Factor analysis is future work.",
        "question": "Could the wrong choice of quality axes doom the entire system before validation?"
    },
    {
        "id": 19,
        "section": "Section 13.2 - Rejection of Scalar Objectives",
        "context": "DCA argues scalar objectives are wrong or gameable for open-ended companion systems. Multi-objective targets are better.",
        "question": "Could a well-designed scalar reward capture everything the quality vector captures? Is the rejection justified?"
    },
    {
        "id": 20,
        "section": "Overall - Dissertation Assessment",
        "context": "This dissertation proposes DCA as a new subfield with a formal model, architecture, and evaluation protocol. It has NO empirical results, only projections.",
        "question": "What is the single most critical weakness? If you had to reject it, what would be your primary argument?"
    },
]

def call_granite(prompt: str) -> dict:
    """Call Ollama using subprocess+curl with a temp file."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 120}
    })
    
    # Write payload to temp file to avoid shell quoting issues
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(payload)
        payload_file = f.name
    
    start = time.time()
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "600", OLLAMA_URL, "-d", f"@{payload_file}"],
            capture_output=True, text=True, timeout=620
        )
        elapsed = time.time() - start
        
        if result.returncode != 0:
            return {"response": f"CURL_ERROR (rc={result.returncode}): {result.stderr[:200]}", 
                    "eval_count": 0, "eval_duration_ns": 0, "latency_s": elapsed, "error": result.stderr[:200]}
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {"response": f"JSON_ERROR: {str(e)[:100]} RAW: {result.stdout[:200]}", 
                    "eval_count": 0, "eval_duration_ns": 0, "latency_s": elapsed, "error": str(e)}
        
        msg = data.get("message", {})
        return {
            "response": msg.get("content", "NO_CONTENT"),
            "eval_count": data.get("eval_count", 0),
            "eval_duration_ns": data.get("eval_duration", 0),
            "latency_s": elapsed,
            "error": None
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {"response": f"TIMEOUT after {elapsed:.0f}s", 
                "eval_count": 0, "eval_duration_ns": 0, "latency_s": elapsed, "error": "timeout"}
    finally:
        os.unlink(payload_file)

def build_prompt(thought: dict) -> str:
    return f"""You are a skeptical PhD reviewer examining a dissertation on Dynamic Cognition Amplification (DCA). Find the WEAKEST point in the following claim. Be specific and harsh.

SECTION: {thought['section']}

CLAIM/CONTEXT:
{thought['context']}

REVIEWER QUESTION: {thought['question']}

Respond in 3-5 sentences. Identify the SINGLE most serious weakness."""

def main():
    # Clear previous output
    with open(OUTPUT_JSONL, "w") as f:
        pass
    
    print(f"=== Devil's Advocate Self-Review ===")
    print(f"=== {datetime.now().isoformat()} ===")
    print(f"=== Model: {MODEL} ===")
    print(f"=== Using subprocess+curl ===")
    print()
    sys.stdout.flush()
    
    records = []
    
    for t in THOUGHTS:
        prompt = build_prompt(t)
        
        # Write prompt to a visible file for debugging
        with open(f"/tmp/thought_{t['id']:02d}_prompt.txt", "w") as f:
            f.write(prompt)
        
        result = call_granite(prompt)
        
        record = {
            "id": t["id"],
            "section": t["section"],
            "question": t["question"],
            "context": t["context"],
            "response": result["response"],
            "latency_ms": round(result["latency_s"] * 1000),
            "eval_count": result["eval_count"],
            "eval_duration_s": round(result["eval_duration_ns"] / 1e9, 3),
            "error": result["error"],
            "timestamp": datetime.now().isoformat()
        }
        records.append(record)
        
        # Append to JSONL
        with open(OUTPUT_JSONL, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        print(f"[{t['id']:2d}] {result['latency_s']:.1f}s | {result['eval_count']} tok | {t['section'][:55]}")
        resp_preview = result['response'][:150].replace('\n', ' ')
        print(f"     {resp_preview}")
        print()
        sys.stdout.flush()
    
    print(f"=== All 20 thoughts complete ===")
    print(f"=== {datetime.now().isoformat()} ===")
    
    # Summary stats
    latencies = [r["latency_ms"] for r in records]
    tokens = [r["eval_count"] for r in records]
    errors = sum(1 for r in records if r["error"])
    successes = [r for r in records if not r["error"]]
    
    print(f"\n--- Summary ---")
    print(f"Total thoughts: {len(records)}")
    print(f"Errors: {errors}")
    print(f"Successful: {len(successes)}")
    if successes:
        s_lat = [r["latency_ms"] for r in successes]
        s_tok = [r["eval_count"] for r in successes]
        print(f"Latency: min={min(s_lat)}ms max={max(s_lat)}ms avg={sum(s_lat)//len(s_lat)}ms")
        print(f"Tokens:  min={min(s_tok)} max={max(s_tok)} avg={sum(s_tok)//len(s_tok)}")
        print(f"Total generation time: {sum(r['eval_duration_s'] for r in successes):.1f}s")

if __name__ == "__main__":
    main()
