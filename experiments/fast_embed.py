#!/usr/bin/env python3
"""
Fast batch embedder: reads a text file, embeds all lines, saves as numpy array.
Does NOT restart ollama - just skips failed items with random fallback.
Designed to be resilient and fast.
"""
import requests
import numpy as np
import json
import time
import sys
import os
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

def embed_one(text, timeout=90):
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": EMBED_MODEL,
            "prompt": text
        }, timeout=timeout)
        resp.raise_for_status()
        emb = resp.json().get("embedding", [])
        if len(emb) == 768:
            return np.array(emb, dtype=np.float32)
    except Exception as e:
        print(f"  FAIL: {str(e)[:80]}", file=sys.stderr, flush=True)
    return None

def main():
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else "items"
    
    with open(input_file) as f:
        texts = [line.strip() for line in f if line.strip()]
    
    print(f"Embedding {len(texts)} {label}...", flush=True)
    
    embeddings = []
    failures = 0
    
    for i, text in enumerate(texts):
        emb = embed_one(text)
        if emb is not None:
            embeddings.append(emb)
        else:
            # Retry once after a pause
            time.sleep(3)
            emb = embed_one(text)
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append(np.random.randn(768).astype(np.float32) * 0.01)
                failures += 1
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0 if i > 0 else 0
            rate = (i + 1) / max(elapsed, 1) if elapsed > 0 else 0
            print(f"  {label}: {i+1}/{len(texts)} ({failures} failures)", flush=True)
            # Save checkpoint
            np.save(output_file + ".checkpoint", np.array(embeddings))
    
    t0 = time.time()
    final = np.array(embeddings)
    np.save(output_file, final)
    
    # Remove checkpoint
    cp = output_file + ".checkpoint"
    if os.path.exists(cp):
        os.remove(cp)
    
    elapsed = time.time() - t0
    print(f"Done: {len(embeddings)} embeddings, {failures} failures, saved to {output_file}", flush=True)
    print(f"Shape: {final.shape}", flush=True)

if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"Total time: {time.time()-t0:.0f}s", flush=True)
