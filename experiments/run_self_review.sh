#!/bin/bash
# Devil's Advocate Self-Review: 20 thought cycles with Granite 3.1
# Each cycle feeds a dissertation claim to Granite and asks it to find the weakest point

set -e

OUTPUT_JSONL="/home/eileen/projects/thought-amplifier/experiments/SELF_REVIEW_THOUGHTS.jsonl"
> "$OUTPUT_JSONL"

run_thought() {
    local id="$1"
    local section="$2"
    local context="$3"
    local question="$4"
    
    # Build the prompt
    local prompt="You are a skeptical PhD reviewer examining a dissertation on Dynamic Cognition Amplification (DCA). Find the WEAKEST point in the following claim. Be specific and harsh.

SECTION: $section

CLAIM/CONTEXT:
$context

REVIEWER QUESTION: $question

Respond in 3-5 sentences. Identify the SINGLE most serious weakness."

    # Create JSON payload
    python3 -c "
import json, sys
payload = {
    'model': 'granite3.1-dense:2b',
    'prompt': sys.argv[1],
    'stream': False,
    'options': {'temperature': 0.7, 'top_p': 0.9}
}
print(json.dumps(payload))
" "$prompt" > /tmp/think_${id}.json
    
    # Time the request
    local start_ms=$(date +%s%3N)
    local response=$(curl -s http://localhost:11434/api/generate -d @/tmp/think_${id}.json 2>&1)
    local end_ms=$(date +%s%3N)
    local latency=$((end_ms - start_ms))
    
    # Extract the response text and eval count
    local text=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','ERROR: '+str(d)[:200]))" 2>&1)
    local eval_count=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('eval_count',0))" 2>&1)
    local eval_duration=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('eval_duration',0)/1e9)" 2>&1)
    
    # Write JSONL
    python3 -c "
import json
record = {
    'id': $id,
    'section': '''$section''',
    'question': '''$question''',
    'response': '''$(echo "$text" | sed "s/'/'\\\\''/g")''',
    'latency_ms': $latency,
    'eval_count': $eval_count,
    'eval_duration_s': $eval_duration
}
print(json.dumps(record))
" >> "$OUTPUT_JSONL"
    
    echo "[$id] ${latency}ms | ${eval_count} tokens | ${section:0:50}..."
    echo "  Response: ${text:0:120}..."
    echo ""
}

echo "=== Devil's Advocate Self-Review ==="
echo "=== $(date) ==="
echo ""

# Thought 1: Abstract - Is DCA actually new?
run_thought 1 "Abstract - New Subfield Claim" \
"DCA is proposed as a new subfield of ML where a small fast process thinks continuously while a larger slower process modifies the conditions under which the fast process thinks." \
"Is this genuinely a NEW subfield, or is it just a reinvention of existing ideas (meta-learning, RLHF, continual learning) with new vocabulary?"

# Thought 2: Quality Vector - Is it validated?
run_thought 2 "Section 3.3 - Quality Vector" \
"The quality vector has 4 axes: novelty, specificity, engagement, spatial awareness. These are used as the training signal instead of scalar loss." \
"Are these 4 axes validated? What evidence supports this particular decomposition over alternatives?"

# Thought 3: Sham Intervention - Is it ethical/valid?
run_thought 3 "Section 3.6 / 7.3 - Sham Interventions" \
"DCA uses sham interventions (logging but not applying) as a control arm. The real effect is measured relative to this sham." \
"Can a sham arm in a continuous self-modifying system actually isolate causal effects when the system's state is non-stationary?"

# Thought 4: Three-Gate Cascade - Does it scale?
run_thought 4 "Section 5 - Three-Gate Cascade" \
"The three-gate cascade promises >=50% of decisions at zero cost after 1 hour, with reflexes handling known situations." \
"What happens when the environment is genuinely novel most of the time? Does the cascade break down?"

# Thought 5: Reflex Compiler - Confidence dynamics
run_thought 5 "Section 5.3 - Confidence Dynamics" \
"Reflex confidence updates: +0.05(1-c) on success, -0.10c on failure, clamped to [0.05, 0.95]." \
"Is this update rule theoretically justified or just heuristic? What are the convergence guarantees?"

# Thought 6: Evolution Engine - EMA with clamp
run_thought 6 "Section 6.4 - Evolution Score Update" \
"The evolution engine uses EMA with alpha=0.05 and clamps scores to [0.05, 0.95]. This is claimed to work across Tic-Tac-Toe, Connect 4, Go, and Hold'em." \
"Does an EMA update rule generalize this broadly? What domains would it fail in?"

# Thought 7: Conductor Trust - Asymmetric scoring
run_thought 7 "Section 7.4 / 4.6 - Trust Dynamics" \
"Trust scoring: +0.5 for success, -2.0 for failure, with 10-observation minimum before updates." \
"Is the 4:1 ratio of penalty to reward justified? Could this make the system overly conservative?"

# Thought 8: Formal Model - Is it actually formal?
run_thought 8 "Section 4 - Formal Model" \
"The formal model defines S = (T, C, W, M, Q, B, L) with discrete time steps and specific update rules." \
"Is this model formal enough? Does it make falsifiable predictions that existing frameworks cannot?"

# Thought 9: LoRA Distillation - Self-training risk
run_thought 9 "Section 9 - Distillation Trap" \
"DCA proposes training LoRA adapters on the system's own high-quality thoughts, with held-out evaluation to prevent the self-reinforcing trap." \
"Is held-out evaluation sufficient when the held-out set comes from the same non-stationary distribution?"

# Thought 10: Conservation Laws - Are they enforceable?
run_thought 10 "Section 4.8 / 9 - Conservation Laws" \
"Four conservation laws (token, action, identity, evolution) are claimed to be executable runtime invariants." \
"Can these laws actually be enforced without crippling performance? What are the overhead costs?"

# Thought 11: Tempo/MIDI - Is this overengineered?
run_thought 11 "Section 8 / 3.5 - Tempo as Substrate" \
"DCA encodes game events as MIDI-like messages with BPM, beat positions, velocity, and chord tones. Sessions are canonized into strings and embedded." \
"Is the MIDI/tempo encoding adding real value or is it unnecessary complexity?"

# Thought 12: Substrate Independence - Real or aspirational?
run_thought 12 "Section 10.1 - Core/Adapter Split" \
"The system claims substrate independence via port contracts. The core speaks only Observation/Thought/Action/Outcome." \
"Is true substrate independence achievable, or will domain-specific concerns always leak into the core?"

# Thought 13: Projected Results - Are they credible?
run_thought 13 "Section 12.1 - Projected Results" \
"DCA projects 50% zero-cost decisions by 1 hour, 40% reflex hit rate, 0.6 trust-quality correlation, 15% policy improvement." \
"Are these projections credible given they're derived from predecessor systems rather than the actual DCA implementation?"

# Thought 14: Missing Baselines
run_thought 14 "Section 11 - Evaluation Protocol" \
"The evaluation uses null adapters, sham arms, and conservation-law property tests but no comparison to existing systems." \
"What baselines are missing? How can you claim a new subfield without comparing against RLHF or continual learning?"

# Thought 15: Browser Tier - Practical feasibility
run_thought 15 "Section 10.7 - Browser Tier" \
"A browser finisher model (Phi-3-mini or Qwen2.5-1.5B) runs via WebLLM+WebGPU and generates divergence loss as a teaching signal." \
"Is WebGPU reliable enough for this? What fraction of users actually have the hardware?"

# Thought 16: .bottle Ledger - Replay determinism
run_thought 16 "Section 10.3 / 4.8 - Bottle Ledger" \
"The .bottle ledger is append-only and claims byte-for-byte replay determinism under the null adapter." \
"Can true byte-for-byte determinism be achieved in practice given floating-point, timing, and OS-level non-determinism?"

# Thought 17: Quality Scorer - Circular dependency
run_thought 17 "Section 3.3 / 12.3 - Quality Scorer" \
"The quality vector is a heuristic. The system learns what the quality scorer likes, which may diverge from what humans like." \
"How do you break the circular dependency where the system optimizes for a heuristic scorer that is itself never validated?"

# Thought 18: Open Questions - Quality vector design
run_thought 18 "Section 12.4 - Quality Vector Design" \
"The four quality axes (novelty, specificity, engagement, spatial) are described as plausible but not validated." \
"Could the wrong choice of axes doom the entire system? How sensitive is DCA to this choice?"

# Thought 19: The Core Philosophical Argument
run_thought 19 "Section 13.2 / 12.5 - Core Argument" \
"DCA argues that scalar objectives are wrong or gameable for open-ended companion systems, and that qualitative multi-objective targets are better." \
"Is the rejection of scalar objectives actually justified? Are qualitative objectives inherently better or just harder to game?"

# Thought 20: Overall Dissertation Quality
run_thought 20 "Overall - Dissertation Assessment" \
"This dissertation proposes DCA as a new subfield, presents a formal model, architecture, and evaluation protocol. It has no empirical results yet - only projections from predecessor systems." \
"What is the single most critical weakness of this dissertation as a piece of scholarly work?"

echo "=== All 20 thoughts complete ==="
echo "=== $(date) ==="
