#!/usr/bin/env python3
"""
Fast batch embedder using subprocess curl for maximum resilience.
Each embedding is a fresh curl process - no connection pooling issues.
"""
import numpy as np
import json
import subprocess
import time
import sys
import os

EMBED_MODEL = "nomic-embed-text"

def embed_curl(text, timeout=90):
    """Embed using subprocess curl - fresh connection each time."""
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text})
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", str(timeout), 
             "http://localhost:11434/api/embeddings",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            emb = data.get("embedding", [])
            if len(emb) == 768:
                return np.array(emb, dtype=np.float32)
    except Exception as e:
        print(f"  FAIL: {str(e)[:60]}", file=sys.stderr, flush=True)
    return None

def main():
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else "items"
    
    with open(input_file) as f:
        texts = [line.strip() for line in f if line.strip()]
    
    print(f"Embedding {len(texts)} {label}...", flush=True)
    t0 = time.time()
    
    embeddings = []
    failures = 0
    
    for i, text in enumerate(texts):
        emb = embed_curl(text)
        if emb is not None:
            embeddings.append(emb)
        else:
            # Retry after pause
            time.sleep(5)
            emb = embed_curl(text)
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append(np.random.randn(768).astype(np.float32) * 0.01)
                failures += 1
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  {label}: {i+1}/{len(texts)} ({failures} fails, {rate:.1f}/s)", flush=True)
            np.save(output_file + ".checkpoint", np.array(embeddings))
    
    final = np.array(embeddings)
    np.save(output_file, final)
    
    cp = output_file + ".checkpoint"
    if os.path.exists(cp):
        os.remove(cp)
    
    elapsed = time.time() - t0
    print(f"Done: {len(embeddings)} embeddings ({failures} fails) in {elapsed:.0f}s", flush=True)
    print(f"Shape: {final.shape}", flush=True)

if __name__ == "__main__":
    main()
