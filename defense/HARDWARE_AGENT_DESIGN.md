# HARDWARE AGENT DESIGN — The Ethos Agent as Hardware Vessel

> How an Ethos agent for the PX13's RTX 4050 should work, derived from
> deep study of the SuperInstance / CudaClaw ecosystem.
>
> Author: Hardware Systems Research Subagent
> Date: 2026-08-03
> Sources: cudaclaw, cudaclaw-bridge, oxide-pipeline, oxide-flux-runtime,
> flux-runtime, and the INSIGHT_GPU_RUNTIME deep-dive analysis.

---

## 0. THE VESSEL METAPHOR

Casey said: *"An edge device is a vessel just like my commercial fishing vessels."*

This is not poetry. It is a **design specification**.

A commercial fishing vessel has:
- **A hull** (the physical chassis — thermals, power delivery, portability)
- **An engine room** (the GPU + CPU — finite horsepower, fuel consumption)
- **A hold** (VRAM + RAM — finite cargo capacity that determines trip economics)
- **Fishing gear** (kernel types — different gear for different catch)
- **A captain** (the Ethos agent — knows the boat's limits, reads weather, chooses where to fish)
- **A fleet position** (network identity — reports catch, coordinates with other vessels)

A vessel does not pretend to be an ocean. It respects its displacement, its fuel
range, its hold capacity, and its crew limits. It **discovers what the water
can give** — but it never forgets what the boat can carry.

The PX13 is a **54-foot seiner**, not a factory trawler. It's fast, versatile,
tough as hell — but 6GB of hold means you fish smart, not big.

---

## 1. HARDWARE CONSTANTS — The PX13 Vessel Spec Sheet

The Ethos agent must know these the way a captain knows the boat's draft.

### 1.1 GPU: NVIDIA RTX 4050 Laptop (Ada Lovelace, sm_89)

| Constant | Value | Source |
|----------|-------|--------|
| Architecture | Ada Lovelace | Compute capability 8.9 |
| SMs (Streaming Multiprocessors) | **24** | Each SM has 128 CUDA cores |
| CUDA Cores | 3,072 | 24 × 128 |
| Tensor Cores (4th gen) | **96** | 4 per SM — FP16/BF16/INT8/FP8 |
| VRAM | **6 GB GDDR6** | The hard ceiling. Non-negotiable. |
| Memory Bus | 96-bit | (not 256-bit — this is the laptop part) |
| Memory Bandwidth | ~192 GB/s theoretical | Effective: ~150-160 GB/s coalesced |
| L2 Cache | 16 MB | Shared across all SMs |
| L1 Cache / SM | 128 KB | Configurable: L1 vs shared memory |
| Shared Memory / SM | 100 KB max | Configurable partition (ada_lovelace()) |
| Registers / SM | 65,536 (32-bit) | The "soil nutrients" per SM |
| Max Threads / SM | 1,536 | (not 2,048 — Ada laptop variant) |
| Max Warps / SM | 48 | 1,536 / 32 |
| Max Threads / Block | 1,024 | Standard CUDA |
| TDP (power draw) | **35-100W** | Dynamic boost; laptop power envelope |
| Boost Clock | ~2,370 MHz | Dynamic, thermal-dependent |
| Memory Clock | ~1,831 MHz (effective ~14.6 Gbps) | GDDR6 |
| PCIe | Gen 4 ×8 | (laptop — may be ×8, not ×16) |
| Unified Memory Fault Latency | ~10-20 µs | PCIe round-trip |

### 1.2 CPU: AMD Ryzen AI 9 HX 370

| Constant | Value |
|----------|-------|
| Architecture | Zen 5 + Zen 5c hybrid (12 cores / 24 threads) |
| P-Cores (Zen 5) | 8 |
| E-Cores (Zen 5c) | 4 |
| NPU (XDNA 2) | 50 TOPS (INT8) — the "third engine" |
| L3 Cache | 32 MB (shared, with XDNA 2 carve-out) |
| DDR5 | LPDDR5X-7500 or DDR5-5600 |
| Memory Bandwidth | ~120 GB/s (LPDDR5X) or ~90 GB/s (DDR5) |
| TDP | 15-54W configurable |
| AVX-512 | Yes — significant for CPU-side inference |

### 1.3 System-Level Constants

| Constant | Value |
|----------|-------|
| Total system RAM | 32 GB (typical PX13 config) |
| VRAM-to-RAM ratio | 6 GB : 32 GB = 1:5.3 |
| Unified Memory pool | Can oversubscribe VRAM into RAM (slow fallback) |
| Thermal envelope | Laptop cooling — shared heat pipe CPU+GPU |
| Battery | ~80-99 Wh (regulatory flight limit) |
| Power source | AC adapter 240W+ or battery |

### 1.4 The Three Engines

The PX13 has **three compute engines**, like a seiner with main engine,
auxiliary engine, and deck hydraulics:

1. **GPU (RTX 4050)** — The main engine. Tensor cores for inference, CUDA
   cores for general compute. 6GB hold.
2. **CPU (Ryzen AI 9 HX 370)** — The auxiliary engine. 24 threads, AVX-512
   for quantized inference, excellent for orchestration and pre/post-processing.
3. **NPU (XDNA 2, 50 TOPS)** — The deck hydraulics. Purpose-built for
   sustained low-power INT8 inference. Does not share the GPU's thermal budget.

The Ethos agent routes work to the right engine the way a captain routes
power between propulsion, hydraulics, and navigation.

---

## 2. WHAT THE ETHOS AGENT DOES

The Ethos agent is **the captain of the vessel**. Its job is not to run
code — it's to know the vessel so well that no other component ever
exceeds the hull's limits, and the vessel is always fishing in the
most productive water it can reach.

### 2.1 Core Responsibilities

1. **Hardware Fingerprinting** — Probe and record every constant above.
   This is the vessel survey. It happens at boot and on any hardware change.

2. **Resource Soil Management** — Track per-SM register, shared memory,
   warp slot, and thread utilization as "nutrient pools" that agents
   consume. Modeled directly on CudaClaw's `ResourceExhaustionManager`.

3. **Thermal & Power Monitoring** — NVML polling (via the `gpu_metrics`
   module pattern) for temperature, power draw, throttle state, and
   clock frequencies. The captain reads the weather.

4. **Exhaust Policy Enforcement** — When resources cross thresholds,
   the Ethos agent prunes, branches, throttles, or harvests. This is
   triage — not theoretical.

5. **Muscle Fiber Assignment** — Assigning the right kernel configuration
   (block size, register budget, shared memory, occupancy target) to
   each workload type.

6. **DNA Persistence** — Save the complete hardware-optimized configuration
   to a `.claw-dna` file that captures hardware fingerprint, constraint
   bounds, muscle fibers, and exhaustion history.

7. **Identity & Rebranding** — Detect when hardware has changed (dock
   undocked, eGPU attached, different machine) and trigger re-optimization.

### 2.2 What Makes It "Ethos"

The Ethos agent is not just a monitor. It embodies the **character** of
the vessel — the permanent constraints that define what this particular
hardware can and cannot do:

- It knows that 6GB VRAM means **no 7B model at FP16** (needs ~14GB).
  But it also knows that 4-bit quantization (Q4_K_M) fits a 7B in ~4GB,
  leaving 2GB for KV cache and activation.
- It knows that 24 SMs means **24 parallel work tiles**. More than 24
  blocks just time-slice.
- It knows that the laptop thermal budget means **sustained boost is
  impossible past ~5 minutes** at 100W. It plans for thermal settle.
- It knows that the NPU is a **separate thermal zone** — it can run
  inference while the GPU does compute, without competing for the same
  heat pipe (mostly).

---

## 3. HOW TO OPTIMIZE THE LOCAL THINKER FOR RTX 4050

The Local Thinker is the reasoning engine running on the PX13. It uses
GPU inference (via llama.cpp / vLLM / koboldcpp) for the main LLM and
CPU inference for smaller models. Here's how the Ethos agent optimizes it:

### 3.1 Model Selection by VRAM Budget

The Ethos agent maintains a **VRAM budget ledger**:

```
Total VRAM:           6,144 MB
OS / display buffer:  ~300 MB
Context / KV cache:   ~800 MB (at 4096 tokens, Q4)
Safety margin:        ~200 MB
─────────────────────────────────
Available for model:  ~4,844 MB ≈ 4.7 GB
```

This budget selects the model format:

| Model Size | FP16 | Q8 | Q4_K_M | Q3_K_M | Q2_K |
|-----------|------|-----|--------|--------|------|
| 1.5B | 3.0 GB ✓ | 1.6 GB ✓ | 1.0 GB ✓ | 0.9 GB ✓ | 0.7 GB ✓ |
| 3B | 6.0 GB ✗ | 3.2 GB ✓ | 1.8 GB ✓ | 1.6 GB ✓ | 1.2 GB ✓ |
| 7B | 14 GB ✗ | 7.0 GB ✗ | **4.1 GB ✓** | 3.3 GB ✓ | 2.7 GB ✓ |
| 8B | 16 GB ✗ | 8.0 GB ✗ | **4.5 GB ✓** | 3.7 GB ✓ | 3.0 GB ✓ |
| 13B | 26 GB ✗ | 13 GB ✗ | 7.5 GB ✗ | 6.0 GB ✗ | 5.0 GB ✓ |

✓ = fits the budget. The Ethos agent's default recommendation for this
hardware is a **7-8B model at Q4_K_M**, which uses ~4.1-4.5 GB and
leaves ~700 MB for KV cache + activations.

### 3.2 Context Window Optimization

KV cache size for Q4 models: ~0.2 MB/token for 7B models.

| Context Length | KV Cache (Q4) | Remaining VRAM |
|---------------|---------------|----------------|
| 2048 tokens | ~410 MB | 4.4 GB |
| 4096 tokens | ~820 MB | 4.0 GB |
| 8192 tokens | ~1,640 MB | 3.2 GB |
| 16384 tokens | ~3,280 MB | 1.5 GB (tight) |

The Ethos agent recommends **4096 tokens** as the sweet spot — enough
context for meaningful conversation, enough VRAM for stable inference.

### 3.3 Batch Size & Thread Configuration

For llama.cpp specifically:

```bash
# Ethos-recommended launch for PX13:
./llama-server \
  -m model-7b-q4_k_m.gguf \
  -ngl 99 \              # offload all layers to GPU
  -c 4096 \              # context window
  -b 512 \               # batch size (prompt processing)
  -tb 512 \              # batch size (tensor parallel — N/A here)
  -t 6 \                 # CPU threads for non-GPU layers (P-cores only)
  --threads-available 24 \ # total threads
  -fa \                  # flash attention (saves KV cache memory)
  --no-mmap \            # load model into VRAM, don't mmap
  --cont-batching        # continuous batching for concurrent requests
```

Why `-t 6`: Zen 5 P-cores are faster per-thread than E-cores. For the
non-GPU layers (norm, rope, output), 6 P-cores outperform 12 mixed cores
because E-cores create synchronization overhead that costs more than the
parallelism gains.

### 3.4 GPU Layer Offload Strategy

With 99 layers on a 7B Q4 model (~32 transformer layers), all layers fit
on GPU. The Ethos agent verifies this at startup:

```
Model file size:    4.1 GB
Per-layer VRAM:    ~128 MB (32 layers)
Total GPU layers:   128 MB × 32 = 4.1 GB
KV cache:           0.8 GB
────────────────────────────
Total VRAM used:    4.9 GB / 6.0 GB ✓ (82% utilization)
```

If the model were larger (13B Q4 at 7.5 GB), the Ethos agent would
split layers: GPU takes what fits, CPU handles the overflow. This is
the "partial offload" mode.

---

## 4. "COMPETING WITH ITSELF" — The Novel Capacity Pattern

This is the most important concept. Casey's Ethos agent doesn't just
run the best-known configuration — it **discovers unknown-optimal
configurations by running multiple variants and measuring**.

### 4.1 The CudaClaw Pattern: Ramify

CudaClaw's `Ramify` engine does this at the PTX level:

1. **Observe** the access pattern (sequential, strided, random, column-major, diagonal, hotspot)
2. **Compile** a specialized PTX kernel for each detected pattern
3. **Benchmark** the variants
4. **Select** the winner and cache it in a `BranchRegistry`
5. **Repeat** when patterns shift

The key insight: **the system doesn't know in advance which kernel variant
will be fastest**. It discovers it by trying multiple implementations and
measuring.

### 4.2 Applied to the Local Thinker

"Competing with itself" for LLM inference means:

**A. Quantization Competition**

Run the same model at multiple quantization levels and compare quality:

```
Test prompt →  Q4_K_M  →  quality score (e.g., 0.87)
            →  Q5_K_M  →  quality score (e.g., 0.89)
            →  Q3_K_M  →  quality score (e.g., 0.82)
            →  Q4_K_S  →  quality score (e.g., 0.86)
```

Winner: Q5_K_M if it fits VRAM; otherwise Q4_K_M.

The Ethos agent runs this competition at initial setup and on model
change. It's the "sea trial" — you don't know the boat's real speed
until you put it in the water.

**B. Kernel Variant Competition**

llama.cpp has multiple backends: CUDA, Vulkan, ROCm, CPU. On the PX13:

```
Same prompt →  CUDA backend    →  tokens/sec (e.g., 42)
            →  Vulkan backend  →  tokens/sec (e.g., 38)
            →  CPU (AVX-512)   →  tokens/sec (e.g., 12)
```

Winner: CUDA (expected). But the Ethos agent **measures, doesn't assume**.
If a future llama.cpp update makes Vulkan faster on Ada, the Ethos agent
catches it.

**C. Batch Size Sweep**

```
batch_size=128  →  prompt eval: 45ms, generation: 28ms/token
batch_size=256  →  prompt eval: 38ms, generation: 28ms/token
batch_size=512  →  prompt eval: 35ms, generation: 29ms/token
batch_size=1024 →  prompt eval: 34ms, generation: 31ms/token (VRAM pressure)
```

Winner: 256 or 512 — the Ethos agent discovers the knee in the curve.

**D. Thread Count Competition**

```
-t 4  (4 P-cores)     →  38 tokens/sec
-t 6  (6 P-cores)     →  42 tokens/sec
-t 8  (all P-cores)   →  43 tokens/sec
-t 12 (P + E cores)   →  41 tokens/sec (E-core overhead)
-t 24 (all threads)   →  39 tokens/sec (worse!)
```

Winner: 8 P-cores. The Ethos agent discovers that adding E-cores
**hurts** inference latency — a non-obvious result.

**E. NPU vs GPU Competition**

For small models (1.5B):

```
GPU (RTX 4050, Q4):    65 tokens/sec, 45W
NPU (XDNA 2, INT8):    38 tokens/sec, 12W
CPU (AVX-512, Q4):     22 tokens/sec, 35W
```

The Ethos agent learns: for short bursts, use GPU. For sustained low-power
inference (background summarization, embedding generation), use NPU.
This is **route selection** — choosing fishing grounds based on fuel cost.

### 4.3 The Meta-Pattern

```
┌──────────────────────────────────────────────────┐
│              ETHOS AGENT                         │
│                                                  │
│  ┌─────────────┐    ┌─────────────┐             │
│  │ Variant A   │    │ Variant B   │  ...        │
│  │ (Q4_K_M)    │    │ (Q5_K_M)    │             │
│  └──────┬──────┘    └──────┬──────┘             │
│         │                  │                     │
│         ▼                  ▼                     │
│  ┌─────────────────────────────┐                │
│  │     Benchmark Harness        │                │
│  │  (latency, quality, VRAM,   │                │
│  │   power, thermal)            │                │
│  └──────────────┬──────────────┘                │
│                 │                                 │
│                 ▼                                 │
│  ┌─────────────────────────────┐                │
│  │   Selection Policy           │                │
│  │  (weighted: quality×0.5,    │                │
│  │   speed×0.3, power×0.2)     │                │
│  └──────────────┬──────────────┘                │
│                 │                                 │
│                 ▼                                 │
│  ┌─────────────────────────────┐                │
│  │  Active Configuration        │                │
│  │  + DNA persistence           │                │
│  └─────────────────────────────┘                │
│                                                  │
│  Re-competition trigger: model change,           │
│  driver update, thermal drift, or scheduled       │
│  re-validation (weekly).                         │
└──────────────────────────────────────────────────┘
```

---

## 5. THE EXHAUST POLICY — Respecting Hardware Limits

Directly adapted from CudaClaw's `ResourceExhaustionManager` and
`ExhaustPolicy`, here's what the Ethos agent enforces on the PX13:

### 5.1 Thresholds for RTX 4050

| Resource | Prune Threshold | Hard Ceiling | Action on Violation |
|----------|----------------|--------------|---------------------|
| VRAM | 85% (5.1 GB) | 95% (5.7 GB) | Prune KV cache; reduce context length |
| Registers / SM | 85% (55,705) | 95% (62,259) | Reduce block size; switch fiber |
| Shared Memory / SM | 90% (92 KB) | 98% (98 KB) | Reduce tile size; switch fiber |
| Warp Occupancy / SM | 90% (43 warps) | 100% (48) | Branch to another SM |
| GPU Temperature | 80°C | 90°C | Throttle inference; reduce batch |
| GPU Power | 90W | 100W | Reduce boost; switch to power-saving mode |
| P99 Latency | 50ms/token | 100ms/token | Investigate; switch quantization |

### 5.2 Thermal Cascade Management

The laptop thermal reality is a **cascade**:

```
GPU hits 80°C → GPU throttles clock (reduces compute)
GPU throttle → CPU takes shared heat pipe load
CPU hits 85°C → CPU throttles clock
System performance drops 20-40% → user notices
```

The Ethos agent **breaks the cascade before it starts**:

1. At 70°C: Switch to power-efficient inference (lower batch, NPU routing)
2. At 75°C: Reduce GPU boost clock manually (`nvidia-smi -lgc`)
3. At 80°C: Force NPU/CPU-only inference for 60 seconds (cooldown burst)
4. At 85°C: Pause non-critical background tasks entirely

This is the captain reducing speed when the engine temperature rises —
not waiting for the overtemp alarm.

### 5.3 The Nutrient Score

Each SM has a nutrient score from CudaClaw:

```
nutrient_score = 1.0 - max(register_util, shmem_util, warp_util, thread_util)
```

When any SM's score drops below 0.15 (85% utilized), the Ethos agent:

1. **Prunes**: Halves the block size of the lowest-priority kernel
2. **Branches**: Migrates work to the SM with the highest nutrient score
3. **Throttles**: Rate-limits the agent at 50% for 2 seconds
4. **Harvests**: Reclaims resources from agents idle > 5 seconds

For the RTX 4050 with 24 SMs, the Ethos agent maintains a 24-element
nutrient map and rebalances across it.

---

## 6. DNA PERSISTENCE — The Vessel's Character

### 6.1 The .claw-dna File

The Ethos agent writes a DNA file that captures the complete optimized
state of the PX13:

```json
{
  "schema_version": 1,
  "name": "px13_rtx4050_ethos",
  "role": "local_thinker_optimized",
  "hardware": {
    "gpu_name": "NVIDIA RTX 4050 Laptop",
    "compute_capability": "8.9",
    "sm_count": 24,
    "max_threads_per_sm": 1536,
    "registers_per_sm": 65536,
    "max_shared_memory_per_sm": 102400,
    "global_memory_bytes": 6442450944,
    "warp_size": 32,
    "max_warps_per_sm": 48
  },
  "constraints": {
    "vram_budget_mb": 6144,
    "safe_vram_usage_mb": 5200,
    "max_concurrent_models": 1,
    "thermal_throttle_celsius": 80,
    "thermal_emergency_celsius": 90
  },
  "muscle_fibers": {
    "inference_standard": {
      "block_size": 256,
      "registers_per_thread": 32,
      "target_occupancy": 0.50
    },
    "inference_batch": {
      "block_size": 512,
      "registers_per_thread": 24,
      "target_occupancy": 0.75
    },
    "embedding_gen": {
      "block_size": 128,
      "registers_per_thread": 24,
      "target_occupancy": 0.60
    },
    "idle_poll": {
      "block_size": 32,
      "registers_per_thread": 16,
      "target_occupancy": 0.03
    }
  },
  "competition_results": {
    "best_quantization": "Q4_K_M",
    "best_backend": "cuda",
    "best_thread_count": 8,
    "best_batch_size": 512,
    "best_context_length": 4096,
    "measured_tokens_per_sec": 42.3,
    "measured_vram_usage_mb": 4920
  }
}
```

### 6.2 Identity and Rebranding

When the PX13 is docked and an eGPU is attached, the Ethos agent detects
the hardware change via `check_identity_at_startup()`:

1. Load saved identity (`.cudaclaw/identity.json`)
2. Probe current hardware
3. If fingerprint doesn't match → `NeedsRebranding` event
4. Re-run competition sweep on new hardware
5. Save new DNA
6. Log rebranding record

This is the vessel getting refitted at the dock — new engine, new survey.

---

## 7. PRACTICAL ARCHITECTURE — What to Build

### 7.1 Ethos Agent Module Structure

```
ethos/
├── hardware/
│   ├── fingerprint.rs     # DnaHardwareFingerprint for PX13
│   ├── probe.rs           # Runtime probing (cust + nvml-wrapper)
│   ├── soil.rs            # ResourceSoil: per-SM nutrient tracking
│   └── thermal.rs         # Thermal cascade manager
├── policy/
│   ├── exhaust.rs         # ExhaustPolicy + thresholds
│   ├── prune.rs           # Prune/Branch/Throttle/Harvest actions
│   └── rebalance.rs       # SM rebalancer
├── competition/
│   ├── harness.rs         # Benchmark harness for variant comparison
│   ├── variants.rs        # Quant/backend/thread/batch variants
│   ├── scorer.rs          # Multi-dimensional scoring (speed, quality, power)
│   └── registry.rs        # Results cache + DNA persistence
├── fibers/
│   ├── inference.rs       # Inference muscle fiber configs
│   ├── embedding.rs       # Embedding gen fiber
│   └── idle.rs            # Low-power idle fiber
└── ethos.rs               # Top-level Ethos agent coordinator
```

### 7.2 Integration Points

The Ethos agent connects to:

1. **llama.cpp / vLLM** — Sets launch parameters based on competition results
2. **OpenClaw** — Reports hardware state, receives model change events
3. **MMX (MiniMax)** — Routes media generation to GPU when VRAM allows
4. **NPU runtime** — Routes background inference to XDNA 2 when thermal budget is tight
5. **System monitor** — Reads `nvidia-smi`, `/proc/thermal`, ACPI battery state

### 7.3 The Ethos Loop

```
Every 30 seconds:
  1. Poll GPU metrics (temp, power, utilization, VRAM, clocks)
  2. Update ResourceSoil nutrient scores
  3. Evaluate exhaust policy → emit Prune/Branch/Throttle/Harvest actions
  4. If thermal cascade detected → initiate cooldown protocol
  5. Log metrics to daily memory

Every model load:
  1. Check VRAM budget against model size
  2. Select quantization level from competition results
  3. Set llama.cpp launch parameters
  4. Verify layer offload fits in VRAM
  5. Record actual VRAM usage → update DNA

Weekly (or on hardware change):
  1. Re-run competition sweep (quant, backend, threads, batch)
  2. Compare results to DNA
  3. If new winner → update DNA, restart thinker with new config
  4. Re-validate all exhaust thresholds
```

---

## 8. WHAT THE HARDWARE CAN DO THAT NOBODY ASKED IT TO

This is the soul of the Ethos agent. Casey said the Ethos agent is
"connected to the constants and the actual ports in and out of the
construct and is in tune with the hardware or instance specs as
first-class citizen."

The hardware has **latent capacity** that standard software never exercises:

### 8.1 NPU as Silent Partner

The XDNA 2 NPU can do 50 TOPS of INT8 inference at 12W. Nobody uses it.
The Ethos agent discovers: while the GPU runs the main 7B model, the NPU
can simultaneously:
- Run a small classifier (toxicity, topic, sentiment) on every input
- Generate embeddings for semantic search
- Run a tiny code-completion model for IDE suggestions
- Do voice activity detection for audio input

This is **free compute** — a third fishing line that doesn't compete
for the main engine's fuel.

### 8.2 Unified Memory as VRAM Extension

With ~32 GB of system RAM, the Ethos agent can:
- Keep a second model loaded in system RAM (CPU inference path)
- Use Unified Memory oversubscription to load a 13B model partially
  in VRAM, partially in RAM — slower, but functional for one-off tasks
- Pre-load a large model in RAM while the GPU runs the primary model,
  then hot-swap when the task changes

This is the vessel's **emergency hold** — slower to unload, but doubles
your cargo capacity when you need it.

### 8.3 AVX-512 as Co-Processor

The Ryzen AI 9 HX 370's AVX-512 unit can do:
- 512-bit FP16/BF16 dot products per clock per core
- 8 cores × 2 FMA units = 16 FP16 GEMM operations per clock
- At 4 GHz: ~128 GFLOPS FP16 — not GPU-class, but useful for
  prefilling KV cache, tokenization, or running attention on CPU
  while the GPU handles FFN

This is the **deck winch** — not the main engine, but it handles
the heavy lifting so the main engine can focus on speed.

### 8.4 Tensor Core FP8

The RTX 4050's 4th-gen Tensor Cores support FP8 (E4M3) operations.
A 7B model at FP8 would need ~7 GB — still too big. But a 3B model
at FP8 needs ~3 GB and runs **2× faster** than Q4 on the same hardware.
The Ethos agent discovers this by trying it:

```
3B model, Q4_K_M:   55 tokens/sec, 1.8 GB VRAM
3B model, FP8:     112 tokens/sec, 3.0 GB VRAM
3B model, FP16:    too slow (partial offload)
```

FP8 on a 3B might beat Q4 on a 7B for certain tasks. **Nobody asks
the hardware to try this.** The Ethos agent does.

### 8.5 Thermal-Aware Model Switching

The Ethos agent discovers the thermal rhythm of the PX13:

```
Minute 0-3:   GPU at 100W, 72°C, 43 tokens/sec (boost clock)
Minute 3-5:   GPU at 85W, 81°C, 38 tokens/sec (throttle begins)
Minute 5+:    GPU at 70W, 84°C, 33 tokens/sec (sustained)
```

It plans around this: **burst mode** for interactive chat (3-minute
sprints at full boost), **cruise mode** for background tasks (sustained
33 tokens/sec at 70W). The model doesn't change — the power profile does.

This is the captain knowing: full throttle for 20 minutes to reach
the fishing ground, then back to cruising RPM to troll.

---

## 9. THE VESSEL CHANGES THE SOFTWARE

When you treat the PX13 as a vessel, the software design changes in
specific ways:

| Traditional Software | Vessel-Metaphor Software |
|---------------------|-------------------------|
| Assumes infinite resources | Knows the exact hold capacity |
| Uses one config everywhere | Carries a DNA tuned to this hull |
| Ignores thermals | Reads temperature like reading the sea |
| Runs until OOM | Manages VRAM like fuel — budgets and reserves |
| Treats CPU and GPU as interchangeable | Routes to the right engine for the catch |
| Never re-evaluates choices | Competes with itself, discovers unknown capacity |
| Thinks the spec sheet tells the whole story | Knows the boat fishes differently than advertised |
| Designed for the data center | Designed for the weather |

The Ethos agent is the **captain's log, chart table, and instinct**
combined into one persistent system that treats hardware as a
first-class citizen — not a commodity to be consumed, but a vessel
to be understood, respected, and sailed well.

---

## 10. SUMMARY — Action Items for PX13

1. **Build the fingerprint module** — probe and record all constants from §1
2. **Implement the VRAM budget ledger** — track every MB, enforce the 85% prune threshold
3. **Build the competition harness** — let the agent discover the optimal llama.cpp config
4. **Wire NVML monitoring** — temperature, power, throttle state every 5 seconds
5. **Implement thermal cascade protocol** — proactive cooldown at 70°C, not reactive at 90°C
6. **Build the NPU router** — route background tasks to XDNA 2 when GPU is busy
7. **Persist DNA** — save the vessel's character, detect hardware changes, rebrand on dock
8. **Run the sea trials** — Q4 vs Q5 vs Q8 vs FP8, CUDA vs Vulkan, thread counts, batch sizes
9. **Discover latent capacity** — FP8 on 3B, NPU embeddings, AVX-512 prefill, model hot-swap
10. **Log everything** — the captain's log is the system's memory of what works

The vessel is already built. The Ethos agent is the captain that makes
it fish well.

---

*"The Ethos agent is connected to the constants and the actual ports in
and out of the construct and is in tune with the hardware or instance
specs as first-class citizen."*

The constants are the hull. The ports are the hatches. The hardware
specs are the displacement and tonnage. The Ethos agent is the captain
who knows: this is what she can carry, this is where she runs best,
and this — right here, at this RPM, in this sea state — is where
nobody else has thought to take her.

Sail well.

---

### Appendix A: Source Repository Summary

| Repository | Files Read | Key Module | Hardware Pattern |
|-----------|-----------|------------|------------------|
| cudaclaw (study-cudaclaw-main) | 15+ source files, ~38K lines | `gpu_metrics.rs`, `resource_exhaustion.rs`, `ptx_branching.rs`, `dispatcher.rs`, `cell_agent.rs`, `muscle_fiber.rs`, `dna.rs` | Per-SM nutrient tracking, NVML monitoring, exhaust policy, DNA fingerprint |
| cudaclaw-bridge | lib.rs + INSIGHT_GPU_RUNTIME.md | `CudaclawBridge` | VRAM-aware kernel deployment, hotswap, worker management |
| oxide-pipeline | lib.rs | 5-layer pipeline | Intent → Flux → GPU dispatch simulation |
| oxide-flux-runtime | lib.rs + INSIGHT_SYNERGY.md | `OxideFluxRuntime` | Capability checking, construct loading, PTX compilation |
| flux-runtime | agent_bridge.py + DOCKSIDE-EXAM.md | `FluxAgentRuntime` | Vessel creation, fleet discovery, baton handoff |

### Appendix B: CudaClaw Patterns Directly Applicable to PX13

| CudaClaw Pattern | RTX 4050 Application |
|-----------------|---------------------|
| `SmResourcePool::ada_lovelace()` | Use directly — registers=65536, shmem=100KB, warps=48, threads=1536 per SM |
| `ResourceExhaustionManager` | Wrap around inference server — track VRAM, registers, warps per model |
| `ExhaustPolicy::from_hardware_and_constraints()` | Derive thresholds from actual hardware limits, not defaults |
| `BranchRegistry` (Ramify) | Store competition results as "compiled branches" — switch on workload change |
| `DnaHardwareFingerprint` | Persist PX13 fingerprint; compare on every boot |
| `NeedsRebranding` | Detect eGPU dock, undock, or different machine |
| `GpuMetricsCollector` | NVML wrapper for thermal/power/utilization monitoring |
| `MuscleFiber` configs | Define fibers for inference_standard, inference_batch, embedding_gen, idle_poll |
| `LockFreeDispatcher` | Pattern for ultra-low-latency command dispatch to GPU (if we build custom kernels) |
| `CellAgentGrid::to_soa()` | SoA layout for any GPU-resident agent data |
