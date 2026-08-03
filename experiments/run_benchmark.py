#!/usr/bin/env python3
"""Benchmark using ollama Python library - handles connections better."""

import json
import os
import time
import glob
import ollama

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"
MODELS = ["granite3.1-dense:2b", "qwen2.5:0.5b"]

def run_one(model, prompt, num_predict=150):
    """Run a single prompt, return result dict."""
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "seed": 42,
                "num_ctx": 2048,
                "num_predict": num_predict,
            }
        )
        # Get model stats from the response
        result = {
            "response": response["message"]["content"],
            "eval_count": response.get("eval_count", 0),
            "prompt_eval_count": response.get("prompt_eval_count", 0),
            "total_duration_ns": response.get("total_duration", 0),
            "load_duration_ns": response.get("load_duration", 0),
            "prompt_eval_duration_ns": response.get("prompt_eval_duration", 0),
            "eval_duration_ns": response.get("eval_duration", 0),
            "error": None,
        }
        ed = result["eval_duration_ns"] / 1e9
        ec = result["eval_count"]
        result["tokens_per_sec"] = round(ec / ed, 2) if ed > 0 else 0
        result["latency_ms"] = result["total_duration_ns"] // 1_000_000
        result["eval_duration_ms"] = result["eval_duration_ns"] // 1_000_000
        result["load_duration_ms"] = result["load_duration_ns"] // 1_000_000
        result["prompt_eval_duration_ms"] = result["prompt_eval_duration_ns"] // 1_000_000
        return result
    except Exception as e:
        return {
            "response": f"[ERROR: {e}]",
            "eval_count": 0, "prompt_eval_count": 0,
            "total_duration_ns": 0, "load_duration_ns": 0,
            "prompt_eval_duration_ns": 0, "eval_duration_ns": 0,
            "tokens_per_sec": 0, "latency_ms": 0,
            "eval_duration_ms": 0, "load_duration_ms": 0,
            "prompt_eval_duration_ms": 0,
            "error": str(e),
        }

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"Found {len(prompt_files)} prompts\n", flush=True)
    results = []

    for model in MODELS:
        print(f"=== {model} ===", flush=True)

        # Warmup
        print("  Warmup...", end=" ", flush=True)
        w = run_one(model, "Say hello.", num_predict=10)
        if w["error"] is None:
            print(f"{w['eval_count']}t {w['eval_duration_ms']}ms {w['tokens_per_sec']:.1f}t/s", flush=True)
        else:
            print(f"FAILED: {w['error']}", flush=True)
        time.sleep(2)

        for pf in prompt_files:
            pid = os.path.basename(pf).replace(".txt", "")
            prompt = open(pf).read().strip()
            print(f"  {pid}...", end=" ", flush=True)

            r = run_one(model, prompt, num_predict=150)

            r.update({
                "model": model,
                "prompt_id": pid,
                "prompt": prompt,
            })
            results.append(r)

            if r["error"]:
                print(f"ERROR: {r['error'][:80]}", flush=True)
            else:
                print(f"{r['eval_count']}t {r['eval_duration_ms']}ms {r['tokens_per_sec']:.1f}t/s", flush=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results", flush=True)

    # Summary
    for model in MODELS:
        mr = [r for r in results if r["model"] == model and r.get("eval_count", 0) > 0]
        if not mr:
            print(f"\n{model}: ALL FAILED")
            continue
        avg_tps = sum(r["tokens_per_sec"] for r in mr) / len(mr)
        avg_tok = sum(r["eval_count"] for r in mr) / len(mr)
        avg_eval = sum(r["eval_duration_ms"] for r in mr) / len(mr)
        avg_lat = sum(r["latency_ms"] for r in mr) / len(mr)
        print(f"\n{model}:")
        print(f"  Avg tokens/sec:    {avg_tps:.2f}")
        print(f"  Avg output tokens: {avg_tok:.1f}")
        print(f"  Avg eval time:     {avg_eval:.0f}ms ({avg_eval/1000:.1f}s)")
        print(f"  Avg total latency: {avg_lat:.0f}ms ({avg_lat/1000:.1f}s)")
        print(f"  Success: {len(mr)}/{len(prompt_files)}")

if __name__ == "__main__":
    main()
