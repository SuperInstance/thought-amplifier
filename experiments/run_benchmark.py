#!/usr/bin/env python3
"""
EXP3 Benchmark: Granite 3.1 2B vs Qwen 2.5 0.5B
Using llama-cpp-python directly (bypasses Ollama/dxgkrnl crash).
Pure CPU inference on AMD Ryzen AI 9 HX 370.
"""

import json
import os
import time
import glob
from llama_cpp import Llama

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"

# Model paths (Ollama GGUF blobs)
MODELS = {
    "granite3.1-dense:2b": {
        "path": os.path.expanduser("~/.ollama/models/blobs/sha256-5c56bb0256a2c402e95282a29bb5cb747bb805eda0e14a84b1f6c594a297ec1a"),
        "n_ctx": 1024,
        "n_threads": 8,
    },
    "qwen2.5:0.5b": {
        "path": os.path.expanduser("~/.ollama/models/blobs/sha256-970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6"),
        "n_ctx": 1024,
        "n_threads": 8,
    },
}

NUM_PREDICT = 80  # Max tokens per response

def load_model(name, config):
    """Load a model with llama-cpp-python."""
    print(f"  Loading {name}...", flush=True)
    t0 = time.time()
    llm = Llama(
        model_path=config["path"],
        n_ctx=config["n_ctx"],
        n_threads=config["n_threads"],
        n_gpu_layers=0,  # Force CPU only
        verbose=False,
        use_mmap=True,
        use_mlock=False,
    )
    load_time = time.time() - t0
    print(f"  Loaded in {load_time:.1f}s", flush=True)
    return llm, load_time

def run_inference(llm, prompt, num_predict=100):
    """Run inference and return metrics."""
    t0 = time.perf_counter()
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=num_predict,
        temperature=0.7,
        top_p=0.9,
        seed=42,
    )
    elapsed = time.perf_counter() - t0

    text = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})
    eval_count = usage.get("completion_tokens", 0)
    prompt_tokens = usage.get("prompt_tokens", 0)

    tps = eval_count / elapsed if elapsed > 0 else 0

    return {
        "response": text,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_tokens,
        "latency_ms": int(elapsed * 1000),
        "load_duration_ms": 0,  # Tracked separately
        "prompt_eval_duration_ms": 0,
        "eval_duration_ms": int(elapsed * 1000),
        "tokens_per_sec": round(tps, 2),
        "error": None,
    }

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))
    print(f"=== EXP3: Speed vs Quality Tradeoff ===", flush=True)
    print(f"Found {len(prompt_files)} prompts\n", flush=True)

    results = []

    for model_name, config in MODELS.items():
        print(f"\n=== {model_name} ===", flush=True)

        # Load model
        llm, load_time = load_model(model_name, config)

        # Warmup
        print("  Warmup...", end=" ", flush=True)
        w = run_inference(llm, "Say hello.", num_predict=5)
        print(f"{w['eval_count']}t {w['latency_ms']}ms {w['tokens_per_sec']:.2f}t/s", flush=True)

        for i, pf in enumerate(prompt_files):
            pid = os.path.basename(pf).replace(".txt", "")
            prompt = open(pf).read().strip()
            print(f"  [{i+1}/20] {pid}...", end=" ", flush=True)

            r = run_inference(llm, prompt, num_predict=NUM_PREDICT)
            r["model"] = model_name
            r["prompt_id"] = pid
            r["prompt"] = prompt
            r["load_duration_ms"] = int(load_time * 1000)
            results.append(r)
            print(f"{r['eval_count']}t {r['latency_ms']}ms {r['tokens_per_sec']:.1f}t/s", flush=True)

            # Save after each prompt
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, indent=2)

        # Unload model to free memory
        del llm
        print(f"  Unloaded {model_name}", flush=True)

    print(f"\nSaved {len(results)} results to {OUTPUT_FILE}", flush=True)

    # Summary
    for model_name in MODELS:
        mr = [r for r in results if r["model"] == model_name and r.get("eval_count", 0) > 0]
        if not mr:
            print(f"\n{model_name}: ALL FAILED")
            continue
        avg_tps = sum(r["tokens_per_sec"] for r in mr) / len(mr)
        avg_tok = sum(r["eval_count"] for r in mr) / len(mr)
        avg_lat = sum(r["latency_ms"] for r in mr) / len(mr)
        min_tps = min(r["tokens_per_sec"] for r in mr)
        max_tps = max(r["tokens_per_sec"] for r in mr)
        print(f"\n{model_name}:")
        print(f"  Avg tokens/sec:    {avg_tps:.2f}")
        print(f"  Min tokens/sec:    {min_tps:.2f}")
        print(f"  Max tokens/sec:    {max_tps:.2f}")
        print(f"  Avg output tokens: {avg_tok:.1f}")
        print(f"  Avg latency:       {avg_lat:.0f}ms ({avg_lat/1000:.1f}s)")
        print(f"  Success: {len(mr)}/{len(prompt_files)}")

if __name__ == "__main__":
    main()
