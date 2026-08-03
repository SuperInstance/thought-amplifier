#!/usr/bin/env python3
"""
Resilient benchmark: restarts Ollama between prompts if needed.
Runs one model at a time, one prompt at a time, with full health checks.
"""

import json
import os
import time
import glob
import subprocess
import signal
import sys

PROMPTS_DIR = "/home/eileen/projects/thought-amplifier/experiments/prompts"
OUTPUT_FILE = "/home/eileen/projects/thought-amplifier/experiments/exp3_results.json"

def ensure_ollama():
    """Ensure Ollama is running and responsive. Restart if needed."""
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "5", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return True
    except:
        pass

    print("    [ollama down, restarting...]", flush=True)
    # Kill all ollama
    subprocess.run(["pkill", "-9", "ollama"], capture_output=True)
    time.sleep(3)
    # Restart
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    subprocess.Popen(
        ["ollama", "serve"],
        stdin=subprocess.DEVNULL,
        stdout=open("/tmp/ollama_restart.log", "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True
    )
    # Wait for it
    for i in range(30):
        time.sleep(2)
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", "3", "http://localhost:11434/api/tags"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                print(f"    [ollama up after {i*2}s]", flush=True)
                return True
        except:
            pass
    print("    [ollama FAILED to restart]", flush=True)
    return False

def call_ollama_raw(model, prompt, num_predict=80, timeout=600):
    """Call ollama via curl, return parsed dict or None."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9, "seed": 42, "num_ctx": 2048, "num_predict": num_predict}
    })
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "http://localhost:11434/api/chat", "-d", payload],
            capture_output=True, text=True, timeout=timeout + 15
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        if "message" not in data:
            return None
        return data
    except Exception as e:
        print(f"    [call error: {e}]", flush=True)
        return None

def run_prompt(model, prompt, pid="", num_predict=80, max_attempts=3):
    """Run a single prompt with retries and Ollama restart."""
    for attempt in range(max_attempts):
        if not ensure_ollama():
            continue

        result = call_ollama_raw(model, prompt, num_predict=num_predict, timeout=600)
        if result is not None:
            ed = result.get("eval_duration", 0)
            ec = result.get("eval_count", 0)
            tps = (ec / (ed / 1e9)) if ed > 0 else 0
            return {
                "response": result["message"]["content"],
                "eval_count": ec,
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "latency_ms": result.get("total_duration", 0) // 1_000_000,
                "load_duration_ms": result.get("load_duration", 0) // 1_000_000,
                "prompt_eval_duration_ms": result.get("prompt_eval_duration", 0) // 1_000_000,
                "eval_duration_ms": ed // 1_000_000,
                "tokens_per_sec": round(tps, 2),
                "error": None,
            }
        else:
            print(f"    [attempt {attempt+1} failed, ollama may have crashed]", flush=True)
            # Force restart for next attempt
            subprocess.run(["pkill", "-9", "ollama"], capture_output=True)
            time.sleep(3)

    return {
        "response": "[ALL ATTEMPTS FAILED]", "eval_count": 0, "tokens_per_sec": 0,
        "latency_ms": 0, "eval_duration_ms": 0, "load_duration_ms": 0,
        "prompt_eval_count": 0, "prompt_eval_duration_ms": 0, "error": "all_attempts_failed",
    }

def main():
    prompt_files = sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt")))

    # Load existing results if any (for resume)
    results = []
    done = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            results = json.load(f)
            done = {(r["model"], r["prompt_id"]) for r in results if r.get("eval_count", 0) > 0}
        print(f"Loaded {len(results)} existing results, {len(done)} successful", flush=True)

    print(f"=== EXP3: Speed vs Quality Tradeoff ===", flush=True)
    print(f"Found {len(prompt_files)} prompts\n", flush=True)

    # Run Qwen first (faster, more stable)
    for model in ["qwen2.5:0.5b", "granite3.1-dense:2b"]:
        # Unload other model first
        if ensure_ollama():
            subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/generate",
                 "-d", json.dumps({"model": "granite3.1-dense:2b" if model == "qwen2.5:0.5b" else "qwen2.5:0.5b", "keep_alive": 0})],
                capture_output=True, timeout=10
            )
            time.sleep(2)

        print(f"\n=== {model} ===", flush=True)

        # Warmup
        if (model, "__warmup__") not in done:
            print("  Warmup...", end=" ", flush=True)
            w = run_prompt(model, "Say hello.", "__warmup__", num_predict=5, max_attempts=3)
            if w["error"] is None:
                print(f"{w['eval_count']}t {w['eval_duration_ms']}ms {w['tokens_per_sec']:.2f}t/s", flush=True)
            else:
                print("FAILED", flush=True)

        for i, pf in enumerate(prompt_files):
            pid = os.path.basename(pf).replace(".txt", "")
            prompt = open(pf).read().strip()

            if (model, pid) in done:
                print(f"  [{i+1}/20] {pid}... SKIP (done)", flush=True)
                continue

            print(f"  [{i+1}/20] {pid}...", end=" ", flush=True)
            t0 = time.time()
            r = run_prompt(model, prompt, num_predict=80, max_attempts=3)
            wall = time.time() - t0

            r.update({"model": model, "prompt_id": pid, "prompt": prompt})
            results.append(r)
            done.add((model, pid))

            if r["error"]:
                print(f"FAILED ({wall:.0f}s)", flush=True)
            else:
                print(f"{r['eval_count']}t {r['eval_duration_ms']}ms {r['tokens_per_sec']:.1f}t/s (wall {wall:.0f}s)", flush=True)

            # Save after each prompt (crash-safe)
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} results to {OUTPUT_FILE}", flush=True)

    # Summary
    for model in ["qwen2.5:0.5b", "granite3.1-dense:2b"]:
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
