#!/usr/bin/env python3
"""Benchmark Granite 3.1 2B vs Qwen 2.5 0.5B on RTX 4050 Laptop (CPU fallback mode)."""

import json
import os
import time
import glob
import subprocess

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"
MODELS = ["granite3.1-dense:2b", "qwen2.5:0.5b"]

def call_ollama(model, prompt, num_predict=150, timeout=600):
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
            capture_output=True, text=True, timeout=timeout + 15
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)
    except Exception as e:
        print(f"    ERROR: {e}", flush=True)
        return None

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"Found {len(prompt_files)} prompts", flush=True)
    results = []

    for model in MODELS:
        print(f"\n=== {model} ===", flush=True)

        # Warmup
        print("  Warmup...", end=" ", flush=True)
        d = call_ollama(model, "Say hello.", num_predict=10, timeout=120)
        if d and "message" in d:
            ed = d.get("eval_duration", 1) / 1e9
            tps = d.get("eval_count", 0) / ed if ed > 0 else 0
            print(f"{d.get('eval_count',0)} tok in {ed:.1f}s = {tps:.2f} tok/s", flush=True)
        else:
            print("FAILED", flush=True)
        time.sleep(1)

        for pf in prompt_files:
            pid = os.path.basename(pf).replace(".txt", "")
            prompt = open(pf).read().strip()
            print(f"  {pid}...", end=" ", flush=True)
            t0 = time.time()

            d = call_ollama(model, prompt, num_predict=150, timeout=600)
            elapsed = time.time() - t0

            if d is None or "message" not in d:
                print(f"FAILED ({elapsed:.0f}s)", flush=True)
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
            print(f"{ec}t {ed//1_000_000}ms {tps:.1f}t/s (wall {elapsed:.0f}s)", flush=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results to {OUTPUT_FILE}", flush=True)

    # Summary
    for model in MODELS:
        mr = [r for r in results if r["model"] == model and r["eval_count"] > 0]
        if not mr:
            print(f"{model}: ALL FAILED")
            continue
        avg_tps = sum(r["tokens_per_sec"] for r in mr) / len(mr)
        avg_tok = sum(r["eval_count"] for r in mr) / len(mr)
        avg_eval_ms = sum(r["eval_duration_ms"] for r in mr) / len(mr)
        avg_lat = sum(r["latency_ms"] for r in mr) / len(mr)
        print(f"\n{model}:")
        print(f"  Avg tokens/sec:    {avg_tps:.2f}")
        print(f"  Avg output tokens: {avg_tok:.1f}")
        print(f"  Avg eval time:     {avg_eval_ms:.0f}ms")
        print(f"  Avg total latency: {avg_lat:.0f}ms")
        print(f"  Success: {len(mr)}/{len(prompt_files)}")

if __name__ == "__main__":
    main()
