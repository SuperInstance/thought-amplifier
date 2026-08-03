#!/usr/bin/env python3
"""Quick test of ollama generation timing."""
import urllib.request
import json
import time

url = "http://localhost:11434/api/chat"
data = json.dumps({
    "model": "granite3.1-dense:2b",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": False
}).encode()

print(f"Starting request at {time.strftime('%H:%M:%S')}", flush=True)
start = time.time()

req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
        elapsed = time.time() - start
        print(f"Got response in {elapsed:.1f}s", flush=True)
        print(f"Content: {result['message']['content'][:200]}", flush=True)
        print(f"Total duration: {result.get('total_duration', 0)/1e9:.1f}s", flush=True)
        print(f"Eval duration: {result.get('eval_duration', 0)/1e9:.1f}s", flush=True)
        print(f"Load duration: {result.get('load_duration', 0)/1e9:.1f}s", flush=True)
        print(f"Prompt eval: {result.get('prompt_eval_duration', 0)/1e9:.1f}s", flush=True)
except Exception as e:
    elapsed = time.time() - start
    print(f"FAILED after {elapsed:.1f}s: {e}", flush=True)
