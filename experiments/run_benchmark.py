#!/usr/bin/env python3
"""Benchmark Granite 3.1 2B vs Qwen 2.5 0.5B - resilient version."""

import json
import os
import time
import glob
import subprocess

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"
MODELS = ["granite3.1-dense:2b", "qwen2.5:0.5b"]

def call_ollama(model, prompt, num_predict=256, timeout=300):
    """Call ollama API and return parsed response or None."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.7, "top_p": 0.9, "seed": 42,
            "num_ctx": 2048, "num_predict": num_predict,
        }
    })
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "http://localhost:11434/api/chat", "-d", payload],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)
    except Exception:
        return None

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"Found {len(prompt_files)} prompts\n", flush=True)
    results = []

    for model in MODELS:
        print(f"=== {model} ===", flush=True)

        # Warmup with small generation
        print("  Warmup...", flush=True)
        d = call_ollama(model, "Say hello.", num_predict=20, timeout=120)
        if d:
            ed = d.get("eval_duration", 1) / 1e9
            tps = d.get("eval_count", 0) / ed if ed > 0 else 0
            print(f"  Warm: {d.get('eval_count',0)} tok in {ed:.1f}s = {tps:.1f} tok/s", flush=True)
        else:
            print("  Warmup failed, continuing anyway...", flush=True)
        time.sleep(2)

        for pf in prompt_files:
            pid = os.path.basename(pf).replace(".txt", "")
            prompt = open(pf).read().strip()
            print(f"  {pid}...", end=" ", flush=True)

            d = call_ollama(model, prompt, num_predict=256, timeout=300)
            if d is None or "message" not in d:
                print("FAILED", flush=True)
                results.append({
                    "model": model, "prompt_id": pid, "prompt": prompt,
                    "response": "[FAILED]", "eval_count": 0, "latency_ms": 0,
                    "tokens_per_sec": 0, "eval_duration_ms": 0, "load_duration_ms": 0,
                    "prompt_eval_count": 0, "prompt_eval_duration_ms": 0,
                })
                continue

            ed = d.get("eval_duration", 0)
            ec = d.get("eval_count", 0)
            tps = (ec / (ed / 1e9)) if ed > 0 else 0

            results.append({
                "model": model, "prompt_id": pid, "prompt": prompt,
                "response": d["message"]["content"],
                "eval_count": ec,
                "prompt_eval_count": d.get("prompt_eval_count", 0),
                "latency_ms": d.get("total_duration", 0) // 1_000_000,
                "load_duration_ms": d.get("load_duration", 0) // 1_000_000,
                "prompt_eval_duration_ms": d.get("prompt_eval_duration", 0) // 1_000_000,
                "eval_duration_ms": ed // 1_000_000,
                "tokens_per_sec": round(tps, 2),
            })
            print(f"{ec}t {ed//1_000_000}ms {tps:.1f}t/s", flush=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results to {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    main()
