#!/usr/bin/env python3
"""
Devil's Advocate Self-Review: 20 thought cycles with Granite 3.1
Uses the /api/chat endpoint with long timeouts.
"""
import json, time, subprocess, sys, os, urllib.request, urllib.error
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
        "question": "Are these 4 axes validated? What happens if specificity and novelty are correlated, or if engagement is subjective? Is the decomposition orthogonal?"
    },
    {
        "id": 3,
        "section": "Section 3.6/7.3 - Sham Interventions",
        "context": "DCA uses sham interventions (logging an intervention but not applying it) as a control arm. The real effect is measured as (q_after - q_before) minus (q_sham - q_before).",
        "question": "Can a sham arm actually isolate causal effects when the system's state is non-stationary and the conductor's previous interventions have already changed the distribution?"
    },
    {
        "id": 4,
        "section": "Section 5 - Three-Gate Cascade",
        "context": "The three-gate cascade promises >=50% of decisions at zero cost after 1 hour. Gate 1 is reflex dispatch (<1ms), Gate 2 is compiled policy lookup (O(1)), Gate 3 is LLM inference (~500ms).",
        "question": "What happens in a genuinely open-ended creative environment where novelty is the norm? Does the cascade fail to amortize cost?"
    },
    {
        "id": 5,
        "section": "Section 5.3 - Confidence Dynamics",
        "context": "Reflex confidence updates: +0.05(1-c) on success, -0.10c on failure, clamped to [0.05, 0.95]. This is chosen over Pincher's multiplicative form.",
        "question": "Is this update rule theoretically justified? What are its convergence properties? Has anyone proven it converges, or is it purely heuristic?"
    },
    {
        "id": 6,
        "section": "Section 6.4 - Evolution Score Update",
        "context": "The evolution engine uses EMA with alpha=0.05 and clamps to [0.05, 0.95]. The dissertation claims this works across Tic-Tac-Toe, Connect 4, Go 9x9, and Hold'em.",
        "question": "Does a single EMA update rule generalize across games with radically different complexity? Is alpha=0.05 appropriate for both Tic-Tac-Toe (trivial) and Go (astronomical state space)?"
    },
    {
        "id": 7,
        "section": "Section 7.4 - Trust Asymmetry",
        "context": "Trust scoring uses +0.5 for success and -2.0 for failure, requiring ~4 successes per failure. Updates wait for 10 observations minimum.",
        "question": "Is the 4:1 penalty-to-reward ratio justified? Could this make the system overly conservative, never trusting genuinely good interventions because of one noisy negative result?"
    },
    {
        "id": 8,
        "section": "Section 4 - Formal Model",
        "context": "The formal model defines S = (T, C, W, M, Q, B, L) with thought generation, conductor interventions, quality scoring, and conservation laws. The gradient is a structured intervention delta.",
        "question": "Is this formal model rigorous enough for a PhD dissertation? Does it make specific falsifiable predictions that existing frameworks (POMDPs, meta-RL) cannot?"
    },
    {
        "id": 9,
        "section": "Section 9 - LoRA Distillation",
        "context": "DCA proposes training LoRA adapters on the system's own high-quality thoughts. A 10% held-out gain is required for promotion. The distillation trap is acknowledged.",
        "question": "Is held-out evaluation sufficient when the held-out set comes from the same non-stationary distribution the system was trained on? Could the system learn to game the held-out set too?"
    },
    {
        "id": 10,
        "section": "Section 4.8 - Conservation Laws",
        "context": "Four conservation laws (token, action, identity, evolution) are executable runtime invariants checked by property tests over 1000 cycles.",
        "question": "What is the runtime overhead of checking these laws every cycle? Are property tests over 1000 cycles sufficient to catch rare violations?"
    },
    {
        "id": 11,
        "section": "Section 8 - Tempo/MIDI Encoding",
        "context": "Game events are encoded as MIDI-like messages with BPM, beat positions, velocity, and chord tones. Sessions are canonized into strings like B8:E72:v85 and embedded with bge-m3.",
        "question": "Is the MIDI/tempo encoding adding real cognitive value, or is it an unnecessary analogy that adds complexity without measurable benefit? What would be lost with simple timestamps?"
    },
    {
        "id": 12,
        "section": "Section 10.1 - Core/Adapter Split",
        "context": "The system claims substrate independence via port contracts (WorldPort, ThinkerPort, ConductorPort, etc.). The core speaks only Observation/Thought/Action/Outcome.",
        "question": "Is true substrate independence achievable? Will domain-specific concerns always leak through the abstraction? Can you name one port that would be hard to implement for a non-game domain?"
    },
    {
        "id": 13,
        "section": "Section 12.1 - Projected Results",
        "context": "DCA projects 50% zero-cost decisions, 40% reflex hit rate, 0.6 trust-quality correlation, 15% policy improvement. These are derived from predecessor systems Pincher, Lever Runner, ZeroClaw.",
        "question": "Are projections from different systems (with different tasks, different environments) transferable to DCA? What if the precedents are cherry-picked successes?"
    },
    {
        "id": 14,
        "section": "Section 11 - Missing Baselines",
        "context": "The evaluation protocol includes null adapters, sham arms, and property tests, but no direct comparison to RLHF, continual learning, or agent frameworks.",
        "question": "How can you claim a new subfield exists without comparing against existing approaches on the same task? What would RLHF look like on this problem, and why would it fail?"
    },
    {
        "id": 15,
        "section": "Section 10.7 - Browser Tier",
        "context": "A browser finisher model (Phi-3-mini/Qwen2.5-1.5B) runs via WebLLM+WebGPU, generating divergence loss as a teaching signal. Context anchors pulse every 0.5-1s.",
        "question": "WebGPU adoption is limited and inconsistent. Is building an entire tier on browser ML premature? What fraction of real users would benefit?"
    },
    {
        "id": 16,
        "section": "Section 10.3 - Bottle Ledger Determinism",
        "context": "The .bottle ledger is append-only. Under the null adapter, the system claims byte-for-byte replay determinism with identical seeds.",
        "question": "Can true byte-for-byte determinism be achieved in practice? What about floating-point non-determinism, JSON key ordering, or OS-level timing differences?"
    },
    {
        "id": 17,
        "section": "Section 3.3/12.3 - Quality Scorer Circularity",
        "context": "The quality vector is heuristic. The system learns what the quality scorer likes. The dissertation admits this may diverge from what humans like.",
        "question": "How do you break this circular dependency? If the scorer is wrong, the entire system optimizes for the wrong thing. Is there a correction mechanism?"
    },
    {
        "id": 18,
        "section": "Section 12.4 - Open Questions",
        "context": "The four quality axes are described as plausible but not validated. Factor analysis of human judgments is listed as future work.",
        "question": "Could the wrong choice of quality axes doom the entire system before empirical validation even begins? How sensitive is DCA to this choice?"
    },
    {
        "id": 19,
        "section": "Section 13.2 - Rejection of Scalar Objectives",
        "context": "DCA argues scalar objectives are wrong or gameable for open-ended companion systems. Multi-objective qualitative targets are presented as better.",
        "question": "Are qualitative objectives inherently better, or just harder to evaluate? Could a well-designed scalar reward capture everything the quality vector captures?"
    },
    {
        "id": 20,
        "section": "Overall - Dissertation Assessment",
        "context": "This dissertation proposes DCA as a new subfield with a formal model, architecture, and evaluation protocol. It has NO empirical results - only projections from predecessor systems. The reference implementation is still in migration.",
        "question": "What is the single most critical weakness of this dissertation? If you had to reject it, what would be your primary argument?"
    },
]

def call_granite(prompt: str) -> dict:
    """Call Ollama /api/chat endpoint."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 150}
    }).encode("utf-8")
    
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - start
        msg = data.get("message", {})
        return {
            "response": msg.get("content", "NO_CONTENT"),
            "eval_count": data.get("eval_count", 0),
            "eval_duration_ns": data.get("eval_duration", 0),
            "latency_s": elapsed,
            "error": None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "response": f"ERROR: {str(e)[:200]}",
            "eval_count": 0,
            "eval_duration_ns": 0,
            "latency_s": elapsed,
            "error": str(e)[:200]
        }

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
    print(f"=== Model: {MODEL} (CPU only, no GPU) ===")
    print(f"=== Expecting ~60-120s per thought ===")
    print()
    sys.stdout.flush()
    
    records = []
    
    for t in THOUGHTS:
        prompt = build_prompt(t)
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
            "error": result["error"]
        }
        records.append(record)
        
        # Append to JSONL
        with open(OUTPUT_JSONL, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        print(f"[{t['id']:2d}] {result['latency_s']:.1f}s | {result['eval_count']} tok | {t['section'][:55]}")
        resp_preview = result['response'][:120].replace('\n', ' ')
        print(f"     {resp_preview}...")
        print()
        sys.stdout.flush()
    
    print(f"=== All 20 thoughts complete ===")
    print(f"=== {datetime.now().isoformat()} ===")
    
    # Summary stats
    latencies = [r["latency_ms"] for r in records]
    tokens = [r["eval_count"] for r in records]
    errors = sum(1 for r in records if r["error"])
    print(f"\nLatency: min={min(latencies)}ms max={max(latencies)}ms avg={sum(latencies)//len(latencies)}ms")
    print(f"Tokens:  min={min(tokens)} max={max(tokens)} avg={sum(tokens)//len(tokens)}")
    print(f"Errors:  {errors}/20")

if __name__ == "__main__":
    main()
