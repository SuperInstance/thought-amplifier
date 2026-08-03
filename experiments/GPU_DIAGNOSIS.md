# GPU Diagnosis Report: RTX 4050 Laptop GPU in WSL2

**Date:** 2026-08-03  
**Hardware:** AMD Ryzen AI 9 HX 370, 24GB RAM, NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM)  
**OS:** WSL2 (Ubuntu), kernel `6.18.33.2-microsoft-standard-WSL2`  
**Driver:** NVIDIA 595.79 (Windows), CUDA 13.2  
**Ollama:** v0.9.6  

---

## TL;DR — ROOT CAUSE & FIX

**Root Cause:** The installed Ollama binary (32MB) was a **CPU-only build** missing the ggml CUDA backend library (`libggml-cuda.so`). Ollama could *detect* the GPU via the CUDA driver API (querying VRAM, compute capability) and allocated VRAM for model weights, but had no CUDA compute backend to actually execute operations on the GPU. All computation silently fell back to CPU.

**Fix:** Downloaded the official Ollama Linux package (1.25GB `ollama-linux-amd64.tgz`) from GitHub releases, extracted the bundled CUDA libraries (`libggml-cuda.so`, `libcudart.so.12`, `libcublas.so.12`), and placed them in `/home/eileen/.local/lib/ollama/`. Set `OLLAMA_LIBRARY_PATH` and `LD_LIBRARY_PATH` to include this directory.

**Result:** Granite 3.1 2B inference went from **1.49 tok/s (CPU) → 76.6 tok/s (GPU)** — a **51.4× speedup**.

---

## What Was Checked

### 1. WSL2 GPU Passthrough — ✅ Working
```
/dev/dxg exists (WSL2 DirectX passthrough device)
/usr/lib/wsl/lib/libcuda.so → present (CUDA driver shim)
/usr/lib/wsl/lib/nvidia-smi → works, shows RTX 4050
```
The GPU is properly passed through from Windows to WSL2. `nvidia-smi` shows the RTX 4050 with 6141MiB VRAM, driver 595.79, CUDA 13.2.

### 2. CUDA Driver Detection — ✅ Working
Ollama's debug log (`OLLAMA_DEBUG=1`) showed:
```
initializing /usr/lib/wsl/lib/libcuda.so
CUDA driver version: 13.2
detected GPUs count=1
CUDA totalMem 6140mb, freeMem 5072mb
Compute Capability 8.9
```
The CUDA **driver API** works fine. Ollama can query device count, memory, compute capability.

### 3. CUDA Compute Backend — ❌ Was Missing
```
ggml backend load all from path: /home/eileen/.local/bin
backend_ptrs.size() = 1  ← Only CPU!
```
The ggml library (which llama.cpp/Ollama uses for tensor operations) only loaded the **CPU backend**. The critical `libggml-cuda.so` library was absent from the library search path.

Despite Ollama reporting `runner.inference=cuda` and `runner.vram="3.0 GiB"`:
```
llama_kv_cache_unified: layer 0-39: dev = CPU  ← ALL layers on CPU!
CUDA0 KV buffer size = 0  ← No GPU KV cache
CPU compute buffer size = 544.01 MiB  ← CPU doing the math
graph splits = 1  ← Only 1 backend active
```

### 4. KV Cache Location — The Smoking Gun
All 40 transformer layers' KV cache was allocated on CPU:
```
llama_kv_cache_unified: layer 0: dev = CPU
llama_kv_cache_unified: layer 1: dev = CPU
...
llama_kv_cache_unified: layer 39: dev = CPU
```
Model weights were copied to VRAM (showing 3.0 GiB allocated), but no actual computation happened on GPU.

### 5. dmesg Kernel Log
Previous experiments reported `dxgkrnl` kernel crashes. Current dmesg shows:
```
dxgk: dxgvmb_send_sync_msg: wait_for_completion failed: fffffe00
dxgk: dxgkio_query_adapter_info: Ioctl failed: -22
dxgk: dxgkio_reserve_gpu_va: Ioctl failed: -75
```
These errors were from **earlier failed attempts** (timestamps from hours ago). After the fix, no new kernel errors appeared during inference. The earlier crashes were likely caused by the broken CUDA library setup, not a fundamental WSL2 kernel bug.

### 6. Environment Variables
- `LD_LIBRARY_PATH`: Was **empty** — CUDA libs not in search path
- `OLLAMA_LIBRARY_PATH`: Was not set — Ollama searched `/home/eileen/.local/bin` for ggml backends
- `CUDA_VISIBLE_DEVICES`: Not set (fine, Ollama handles this)

---

## What Was Tried

### Attempt 1: Setting LD_LIBRARY_PATH to WSL lib — ❌ Didn't Help
```bash
LD_LIBRARY_PATH=/usr/lib/wsl/lib ollama serve
```
The WSL lib directory has `libcuda.so` (driver API) but NOT `libcudart.so` (runtime) or `libggml-cuda.so` (compute backend). GPU detection still worked but compute still fell back to CPU.

### Attempt 2: CUDA_VISIBLE_DEVICES=0 — ❌ Didn't Help
```bash
CUDA_VISIBLE_DEVICES=0 ollama serve
```
No effect — the GPU was already visible, the issue was the missing compute backend.

### Attempt 3: Downloading Official Ollama Package — ✅ FIXED IT
```bash
# Downloaded the official 1.25GB package with bundled CUDA libraries
curl -L -o /tmp/ollama.tgz "https://github.com/ollama/ollama/releases/download/v0.9.6/ollama-linux-amd64.tgz"

# Extracted and copied CUDA backend libraries
mkdir -p /home/eileen/.local/lib/ollama
cp /tmp/ollama_dl/lib/ollama/libggml-cuda.so /home/eileen/.local/lib/ollama/
cp /tmp/ollama_dl/lib/ollama/libggml-base.so /home/eileen/.local/lib/ollama/
cp /tmp/ollama_dl/lib/ollama/libcudart.so.12* /home/eileen/.local/lib/ollama/
cp /tmp/ollama_dl/lib/ollama/libcublas.so.12* /home/eileen/.local/lib/ollama/
cp /tmp/ollama_dl/lib/ollama/libcublasLt.so.12* /home/eileen/.local/lib/ollama/
cp /tmp/ollama_dl/lib/ollama/libggml-cpu-*.so /home/eileen/.local/lib/ollama/

# Set environment variables
export OLLAMA_LIBRARY_PATH=/home/eileen/.local/lib/ollama
export LD_LIBRARY_PATH=/home/eileen/.local/lib/ollama

# Added to ~/.bashrc for persistence
```

**Key files copied:**
| File | Size | Purpose |
|------|------|---------|
| `libggml-cuda.so` | 1.2 GB | CUDA compute backend (the critical one) |
| `libcudart.so.12` | 712 KB | CUDA runtime library |
| `libcublas.so.12` | 111 MB | CUDA BLAS library |
| `libcublasLt.so.12` | 717 MB | CUDA BLAS Light (optimized routines) |
| `libggml-base.so` | 582 KB | Base ggml library |
| `libggml-cpu-*.so` | ~4-7 MB each | CPU backend variants |

---

## Verification — GPU IS Working

### Debug Log (After Fix)
```
ggml backend load all from path: /home/eileen/.local/lib/ollama
backend_ptrs.size() = 2  ← CPU + CUDA!
llama_kv_cache_unified: layer 0-39: dev = CUDA0  ← ALL on GPU!
CUDA0 KV buffer size = 640.00 MiB
CUDA0 compute buffer size = 544.00 MiB
graph splits = 2  ← Using both backends
```

### nvidia-smi (After Fix)
```
GPU Memory: 2224MiB / 6141MiB used
GPU-Util: 79%
Power: 64W / 64W (max draw!)
Temp: 74°C
Process: /ollama (Type C = Compute)
```

### Performance Benchmark (Granite 3.1 2B, Q4_K_M)

| Metric | CPU (Before) | GPU (After) | Speedup |
|--------|:---:|:---:|:---:|
| **Generation speed** | **1.49 tok/s** | **76.6 tok/s** | **51.4×** |
| Prompt eval speed | 22.5 tok/s | 3,440.7 tok/s | 152.9× |
| Total latency (80 tok) | ~62.6s | ~3.7s | 16.9× |
| Load time | ~1.2s | ~9.6ms | 125× |

---

## Permanent Fix Applied

Added to `~/.bashrc`:
```bash
# Ollama CUDA GPU support - added 2026-08-03
# Required for RTX 4050 GPU inference in WSL2
export OLLAMA_LIBRARY_PATH=/home/eileen/.local/lib/ollama
export LD_LIBRARY_PATH=/home/eileen/.local/lib/ollam