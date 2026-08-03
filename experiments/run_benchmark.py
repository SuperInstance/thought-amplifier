#!/usr/bin/env python3
"""Benchmark Granite 3.1 2B vs Qwen 2.5 0.5B on RTX 4050."""

import json
import os
import time
import glob
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"

MODELS = ["granite3.1-dense:2b", "qwen2.5:0.5b"]

def run_chat(model, prompt_text):
    """Run a single chat completion and return metrics."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "seed": 42,
            "num_ctx": 2048,
        }
    }).encode("utf-8")

    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})

    start_ns = time.perf_counter_ns()
    resp = urllib.request.urlopen(req, timeout=120)
    end_ns = time.perf_counter_ns()

    data = json.loads(resp.read().decode("utf-8"))
    latency_ms = (end_ns - start_ns) // 1_000_000

    return {
        "response": data["message"]["content"],
        "eval_count": data.get("eval_count", 0),
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "total_duration_ns": data.get("total_duration", 0),
        "load_duration_ns": data.get("load_duration", 0),
        "prompt_eval_duration_ns": data.get("prompt_eval_duration", 0),
        "eval_duration_ns": data.get("eval_duration", 0),
        "latency_ms": latency_ms,
    }

def compute_tps(metrics):
    """Compute tokens per second from eval_duration."""
    eval_count = metrics["eval_count"]
    eval_dur_s = metrics["eval_duration_ns"] / 1e9
    if eval_dur_s > 0:
        return eval_count / eval_dur_s
    return 0.0

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"Found {len(prompt_files)} prompts")

    # Warm up models
    for model in MODELS:
        print(f"Warming up {model}...")
        run_chat(model, "Hello")
        print(f"  {model} ready")

    results = []

    for model in MODELS:
        for pf in prompt_files:
            prompt_id = os.path.basename(pf).replace(".txt", "")
            with open(pf) as f:
                prompt_text = f.read().strip()

            print(f"  Running {model} on {prompt_id}...", end=" ", flush=True)
            metrics = run_chat(model, prompt_text)
            tps = compute_tps(metrics)

            result = {
                "model": model,
                "prompt_id": prompt_id,
                "prompt": prompt_text,
                "response": metrics["response"],
                "eval_count": metrics["eval_count"],
                "prompt_eval_count": metrics["prompt_eval_count"],
                "latency_ms": metrics["latency_ms"],
                "load_duration_ms": metrics["load_duration_ns"] // 1_000_000,
                "prompt_eval_duration_ms": metrics["prompt_eval_duration_ns"] // 1_000_000,
                "eval_duration_ms": metrics["eval_duration_ns"] // 1_000_000,
                "tokens_per_sec": round(tps, 2),
            }
            results.append(result)
            print(f"{metrics['eval_count']} tok, {metrics['latency_ms']}ms, {tps:.1f} tok/s")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {OUTPUT_FILE}")

    # Quick summary
    for model in MODELS:
        model_results = [r for r in results if r["model"] == model]
        avg_latency = sum(r["latency_ms"] for r in model_results) / len(model_results)
        avg_tps = sum(r["tokens_per_sec"] for r in model_results) / len(model_results)
        avg_tokens = sum(r["eval_count"] for r in model_results) / len(model_results)
        print(f"\n{model}:")
        print(f"  Avg latency: {avg_latency:.0f}ms")
        print(f"  Avg tokens/sec: {avg_tps:.2f}")
        print(f"  Avg output tokens: {avg_tokens:.1f}")

if __name__ == "__main__":
    main()
