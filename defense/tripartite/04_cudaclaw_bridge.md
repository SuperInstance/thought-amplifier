# CudaClaw-Bridge — Tripartite Analysis

## Overview
The Bridge is the **contract layer between compilation and execution**. It takes compiled PTX modules from the oxide pipeline and deploys them as persistent CUDA kernels on the GPU, managing VRAM accounting, worker allocation, and live hotswap. It embodies the Logos→Ethos boundary: translating abstract compiled artifacts into running hardware processes.

## 1. How It Implements the Pathos/Logos/Ethos Split

The Bridge operates at the intersection of two agents:

### Logos→Ethos Boundary
- **Input** (Logos domain): `PtxModule` — a compiled artifact with grid/block dimensions, shared memory requirements, compute capability requirements. This is the output of the compilation pipeline — pure logic, abstract and hardware-independent.
- **Output** (Ethos domain): `DeployedKernel` — running on a specific GPU worker, consuming specific VRAM, at a specific status (Running/Draining/Stopped).

The Bridge's job is the **translation from logical to physical**: which GPU worker runs this kernel, how much VRAM does it actually consume, what happens when you need to swap it out.

### Key Ethos Patterns

1. **VRAM admission control**: Before deploying, the bridge estimates VRAM usage (`estimate_vram = ceil(ptx_bytes / 1024) + (block_size * 4 / 1024)`) and rejects kernels that would exceed the budget. This is Ethos gatekeeping: "this hardware cannot hold your idea."

2. **Worker pool management**: Fixed pool of GPU workers (`max_workers`). Each kernel claims a worker. When exhausted, deployment fails with `NoAvailableWorkers`. The hardware is a first-class constraint.

3. **Live hotswap**: Replace a running kernel's PTX without stopping the worker or freeing device memory. This is the Logos→Ethos boundary at its most elegant — the logical artifact changes, but the physical vessel persists.

### DeployStatus State Machine
```
Compiled → Uploaded → Running { worker_id } → Draining → Stopped
                                        ↓
                                  Failed(String)
```
Hotswap keeps the worker and updates the PTX — the kernel identity persists across logical changes.

## 2. Hardware-Specific Optimizations (Ethos Patterns)

- **Worker allocation**: Each kernel gets a dedicated GPU worker slot. The pool size is determined by available SM resources.
- **VRAM tracking**: Cumulative VRAM accounting with admission control. `vram_utilization()` returns percentage used.
- **Compute capability validation**: `min_compute_capability` on PTX modules checked against GPU before deployment.
- **Kernel statistics**: Runtime telemetry — invocation count, cumulative GPU time, error rates, throughput estimates, GPU utilization percentage.

## 3. Agent Communication

The Bridge doesn't implement A2A directly — it is the **bridge** between two layers:
- **Upstream**: The oxide-flux-runtime (Logos) calls `bridge.deploy()` / `bridge.hotswap()` / `bridge.stop()`
- **Downstream**: CudaClaw's persistent kernel (Ethos) receives the PTX and executes it

Communication is through Rust function calls with typed errors:
- `BridgeError::EmptyPtx` — "you gave me nothing to deploy"
- `BridgeError::NoAvailableWorkers` — "the hardware is full"
- `BridgeError::InsufficientVram { required, available }` — "your idea doesn't fit the vessel"
- `BridgeError::InvalidStatus { expected, actual }` — "you can't hotswap a stopped kernel"

The Bridge README says: *"Know your layer."* This is the Ethos attitude — respect the separation of concerns between compilation and execution.

## 4. What DCA Can Adopt

1. **VRAM admission for thoughts**: Before generating a response with a large model, check if the VRAM can hold the context. The `estimate_vram` pattern could become `estimate_cognition_cost` — will this thought fit in available memory?

2. **Hotswap for model swapping**: When switching between Ollama models (e.g., from a small fast model to a large deep model), the hotswap pattern preserves the conversation context while replacing the inference engine. No teardown needed.

3. **Worker pool for concurrent cognition**: Multiple thoughts can run concurrently on different GPU workers. The allocation pattern — "here's a slot, go run" — enables parallel cognition streams.

4. **Kernel statistics → cognition telemetry**: Track invocation counts, latency, error rates for each cognition type. Build a performance profile of which thoughts are expensive and which are cheap.

5. **DeployStatus lifecycle for thoughts**: A thought has the same lifecycle: Compiled (ready to think), Deployed (running), Draining (finishing), Stopped (done), Failed (error). This is the universal task lifecycle.

6. **"Know your layer"**: DCA should have clear boundaries between Conductor (what to think about), Thinker (how to think about it), and Hardware (where the thinking actually runs). The Bridge pattern of typed errors at each boundary prevents blame confusion.
