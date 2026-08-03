#!/usr/bin/env python3
"""Run Qwen 2.5 0.5B benchmark with the CORRECT model file."""

import json
import os
import time
import glob
from llama_cpp import Llama

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"
QWEN_PATH = os.path.expanduser("~/.ollama/models/blobs/sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515")

def format_prompt(user_msg):
    return f"<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n"

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"=== Qwen 2.5 0.5B Benchmark ===", flush=True)
    print(f"Found {len(prompt_files)} prompts\n", flush=True)

    results = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing results", flush=True)

    print("Loading qwen2.5:0.5b...", flush=True)
    t0 = time.time()
    llm = Llama(
        model_path=QWEN_PATH,
        n_ctx=1024,
        n_threads=8,
        n_gpu_layers=0,
        verbose=False,
        use_mmap=True,
        use_mlock=False,
    )
    load_time = time.time() - t0
    print(f"Loaded in {load_time:.1f}s", flush=True)
    print(f"Memory: {llm._ctx.memory}", flush=True)

    # Warmup
    print("Warmup...", end=" ", flush=True)
    t0 = time.perf_counter()
    resp = llm.create_completion(
        prompt=format_prompt("Say hello."),
        max_tokens=5, temperature=0.7, top_p=0.9, seed=42,
        stop=["<|im_end|>"]
    )
    elapsed = time.perf_counter() - t0
    ec = resp["usage"]["completion_tokens"]
    print(f"{ec} tokens in {elapsed:.1f}s ({ec/elapsed:.2f} tok/s)\n", flush=True)

    for i, pf in enumerate(prompt_files):
        pid = os.path.basename(pf).replace(".txt", "")
        prompt_text = open(pf).read().strip()
        formatted = format_prompt(prompt_text)
        print(f"[{i+1}/20] {pid}...", end=" ", flush=True)

        t0 = time.perf_counter()
        resp = llm.create_completion(
            prompt=formatted,
            max_tokens=80, temperature=0.7, top_p=0.9, seed=42,
            stop=["<|im_end|>"]
        )
        elapsed = time.perf_counter() - t0

        text = resp["choices"][0]["text"]
        ec = resp["usage"]["completion_tokens"]
        pc = resp["usage"]["prompt_tokens"]
        tps = ec / elapsed if elapsed > 0 else 0

        result = {
            "model": "qwen2.5:0.5b",
            "prompt_id": pid,
            "prompt": prompt_text,
            "response": text.strip(),
            "eval_count": ec,
            "prompt_eval_count": pc,
            "latency_ms": int(elapsed * 1000),
            "load_duration_ms": int(load_time * 1000),
            "prompt_eval_duration_ms": 0,
            "eval_duration_ms": int(elapsed * 1000),
            "tokens_per_sec": round(tps, 2),
            "error": None,
        }
        results.append(result)
        print(f"{ec}t {int(elapsed*1000)}ms {tps:.1f}t/s", flush=True)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} total results", flush=True)

    mr = [r for r in results if r["model"] == "qwen2.5:0.5b" and r.get("eval_count", 0) > 0]
    avg_tps = sum(r["tokens_per_sec"] for r in mr) / len(mr)
    avg_tok = sum(r["eval_count"] for r in mr) / len(mr)
    avg_lat = sum(r["latency_ms"] for r in mr) / len(mr)
    print(f"\nqwen2.5:0.5b:")
    print(f"  Avg tokens/sec:    {avg_tps:.2f}")
    print(f"  Avg output tokens: {avg_tok:.1f}")
    print(f"  Avg latency:       {avg_lat:.0f}ms ({avg_lat/1000:.1f}s)")

if __name__ == "__main__":
    main()
