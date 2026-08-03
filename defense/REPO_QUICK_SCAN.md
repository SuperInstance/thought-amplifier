# Quick Scan: 15 New Repos

## Key Discoveries

### PRODUCTION SYSTEMS already implementing DCA patterns:

1. **Nebula (Edge Reflex Engine)** — deployed Cloudflare Worker with 3-gate cascade
   - Fast path: ~700ms from KV cache (Gate 1)
   - Similar path: ~800ms LLM confirm (Gate 2)  
   - Slow path: full DeepInfra call (Gate 3)
   - Embeddings: BGE base 384-dim
   - "The conversation IS the building"

2. **Spreader (Intelligence Tiling)** — deadband detection for PLATO rooms
   - Detects gap between hardcoded rules and LLM calls
   - Freezes reasoning snapshots (Frozen Context Windows)
   - Seeds: staged validation pipeline → fleet-deployable
   - Self-optimizing: monitors own test suite
   - This IS the reflex compilation system

3. **LucidDreamer.ai** — fleet infotainment streaming platform
   - Auto-generates content about fleet projects
   - Audio-first (podcast-style)
   - Character system: Navigator, Builder, Herald, Skeptic, Critic
   - Multi-provider LLM failover + BYOK
   - Knowledge graph with confidence tracking
   - Discourse mode for interactive Q&A

4. **Murmur** — self-populating TensorDB wiki
   - Knowledge graph that organizes itself
   - Semantic connections via AI
   - Real-time event streaming

5. **flux-lucid** — unified constraint compilation
   - CDCL (conflict-driven clause learning)
   - LLVM integration
   - AVX-512 vector instructions
   - GL(9) consensus protocol
   - One crate for constraints + coordination + intent

6. **AIR (Asynchronous Infinite Radio)** — nightly synthesis
   - Build a wiki as you chat
   - Continuous knowledge base evolution
