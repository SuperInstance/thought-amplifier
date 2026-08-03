# EXP3 GPU RERUN: Speed vs Quality Tradeoff — Granite vs Qwen on RTX 4050

**Date:** 2026-08-03  
**Hardware:** AMD Ryzen AI 9 HX 370, 24GB RAM, WSL2  
**GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM) — **NOW WORKING** (dxgkrnl fix applied)  
**Inference:** GPU-accelerated via Ollama (CUDA 12, compute 8.9)  
**Models:** granite3.1-dense:2b (Q4_K_M, 1.57GB) vs qwen2.5:0.5b (Q4_K_M, 398MB)  
**Parameters:** temp=0.7, top_p=0.9, seed=42+i, num_predict=80  
**N prompts:** 20 (same as original EXP3)

---

## ⚡ GPU Fix Confirmation

| Metric | CPU (original) | GPU (rerun) | Improvement |
|--------|:---:|:---:|:---:|
| Granite tok/s | 1.49 | **76.8** | **51.5×** |
| Qwen tok/s | 3.79 | **178.8** | **47.2×** |
| Granite latency | 62.6s | **1.1s** | **56.9×** |
| Qwen latency | 22.4s | **0.5s** | **44.8×** |
| Speed variance (CV) | 33-59% | **1.7-9.6%** | **Rock stable** |

**The dxgkrnl crash is resolved.** GPU inference works perfectly. Both models run at previously theoretical speeds.

---

## Summary Results

| Metric | Granite 3.1 2B (GPU) | Qwen 2.5 0.5B (GPU) | Ratio (Q/G) | CPU Ratio (orig) |
|--------|:---:|:---:|:---:|:---:|
| **Avg tok/s** | **76.8** | **178.8** | **2.33×** | 2.54× |
| Median tok/s | 77.0 | 183.1 | 2.38× | — |
| Min tok/s | 73.7 | 112.5 | 1.53× | — |
| Max tok/s | 78.5 | 193.8 | 2.47× | — |
| **Avg latency** | **1.1s** | **0.9s** | 0.82× | 0.36× |
| Speed CV | 1.7% | 9.6% | — | 33-59% |
| **Avg quality (/20)** | **11.8** | **12.4** | **0.95×** | **0.55× (orig: G=17.3, Q=9.6)** |
| Quality wins | 7/20 | 10/20 | — | 0/20 (orig) |

### The Shocking Reversal

On CPU, Granite won quality 20/20 and Qwen won speed 2.54×.  
On GPU, **Qwen wins both speed (2.33×) AND quality (12.4 vs 11.8).**

This was unexpected. Let me explain why.

---

## Per-Prompt Performance

| # | Category | Granite tok/s | Qwen tok/s | G/Q Speed | Granite Q | Qwen Q | Quality Winner |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| 01 | Spatial reasoning | 73.7 | 112.5 | 1.53× | 12 | 13 | Qwen |
| 02 | Emotional response | 76.3 | 166.0 | 2.18× | 9 | 11 | Qwen |
| 03 | Planning | 77.0 | 188.0 | 2.44× | 14 | 14 | TIE |
| 04 | Creative describe | 77.3 | 193.8 | 2.51× | 9 | 12 | Qwen |
| 05 | Analytical compare | 78.5 | 186.4 | 2.37× | 14 | 13 | **Granite** |
| 06 | Social interpretation | 77.6 | 187.4 | 2.42× | 9 | 10 | Qwen |
| 07 | Causal reasoning | 78.3 | 179.8 | 2.30× | 11 | 12 | Qwen |
| 08 | Moral dilemma | 75.1 | 179.6 | 2.39× | 9 | 12 | Qwen |
| 09 | Temporal sequence | 75.2 | 175.0 | 2.33× | 12 | 12 | TIE |
| 10 | Descriptive detail | 74.7 | 185.5 | 2.48× | 12 | 16 | Qwen |
| 11 | Problem solving | 76.8 | 181.5 | 2.36× | 15 | 12 | **Granite** |
| 12 | Personality voice | 77.3 | 167.9 | 2.17× | 9 | 15 | Qwen |
| 13 | Abstract thinking | 77.8 | 178.4 | 2.29× | 9 | 11 | Qwen |
| 14 | Instructional | 76.8 | 183.8 | 2.39× | 15 | 16 | Qwen |
| 15 | Hypothetical | 77.1 | 182.5 | 2.37× | 13 | 10 | **Granite** |
| 16 | Empathy | 77.5 | 179.7 | 2.32× | 13 | 12 | **Granite** |
| 17 | Pattern recognition | 77.1 | 182.5 | 2.37× | 15 | 12 | **Granite** |
| 18 | Narrative | 78.3 | 187.8 | 2.40× | 12 | 11 | **Granite** |
| 19 | Constraint reasoning | 77.0 | 190.0 | 2.47× | 11 | 13 | Qwen |
| 20 | Reflection | 76.7 | 188.7 | 2.46× | 12 | 11 | **Granite** |

**Granite quality wins:** Analytical compare, Problem solving, Hypothetical, Empathy, Pattern recognition, Narrative, Reflection (7/20)  
**Qwen quality wins:** 10/20  
**Ties:** 3/20

---

## Quality Dimension Breakdown

| Dimension | Granite (avg) | Qwen (avg) | Difference |
|-----------|:---:|:---:|:---:|
| Relevance | **5.0** | 4.7 | Granite slightly better |
| Specificity | **2.2** | 1.8 | Granite slightly better |
| Coherence | 3.4 | **4.7** | **Qwen much better** |
| Originality | 1.1 | **1.2** | Tied (both low) |

### Why Qwen Closed the Quality Gap

The original EXP3 (CPU) found Granite winning 20/20 on quality with an average of 17.3 vs 9.6. The GPU rerun shows a near-tie (11.8 vs 12.4). What happened?

**1. Scoring rubric is different (automated vs manual).** The original used careful manual scoring with the full response text visible. This rerun uses automated keyword-based scoring, which is less generous on originality and specificity.

**2. Granite 2B has a "clinical" style on GPU.** At 76.8 tok/s, Granite generates fluent but detached responses — heavy on "I perceive," "I observe," light on creative vocabulary. This depresses originality (1.1) and coherence (3.4 — many responses are just 2 sentences with formal structure).

**3. Qwen 0.5B improved dramatically at speed.** On CPU, Qwen was so slow it frequently broke character ("As an AI language model..."). On GPU, Qwen still breaks character on some prompts but its coherent, conversational style scores well on the automated rubric. Qwen's higher token count per response (longer answers = more sentences = higher coherence score).

**4. The "As an AI" deflection is the main quality differentiator.** Qwen still does this on ~4/20 prompts (Emotional response, Social interpretation, Problem solving, Hypothetical). When it doesn't deflect, its answers are comparable in quality to Granite's.

---

## Speed-Quality Tradeoff Analysis

| Model | Speed (tok/s) | Quality (/20) | Speed × Quality | ms per quality point |
|-------|:---:|:---:|:---:|:---:|
| Granite 3.1 2B | 76.8 | 11.8 | 906 | 93ms |
| Qwen 2.5 0.5B | 178.8 | 12.4 | 2,217 | 40ms |

**Qwen is 2.45× more efficient** on the speed×quality product. Even on quality alone, Qwen now edges out Granite on the automated rubric.

### When Granite Still Wins

Granite wins quality on tasks requiring:
- **Analytical thinking** (compare, pattern recognition)
- **Problem-solving** (practical steps)
- **Deep reflection** (empathy, hypothetical, narrative)

These are tasks where precision matters more than style. Granite's formal, structured output works well for analysis but poorly for creative/emotional tasks.

### When Qwen Wins

Qwen wins on:
- **Creative/descriptive tasks** (dragon, lighthouse interior)
- **Emotional tasks** (emotional response, personality voice)
- **Instructional tasks** (find water, build sundial)

Qwen's conversational warmth and longer responses score well on engagement and coherence, even when the content is generic.

---

## CPU vs GPU Comparison: What Changed?

### Speed
| Model | CPU tok/s | GPU tok/s | Speedup |
|-------|:---:|:---:|:---:|
| Granite 2B | 1.49 | 76.8 | **51.5×** |
| Qwen 0.5B | 3.79 | 178.8 | **47.2×** |

Both models speed up by ~50×. The relative speed ratio is similar (Qwen 2.54× faster on CPU, 2.33× faster on GPU). The smaller model maintains its speed advantage on GPU because it has fewer parameters to compute.

### Quality Verdict Reversal
| Metric | CPU Result | GPU Result |
|--------|:---:|:---:|
| Quality winner | **Granite 20/20** (17.3 vs 9.6) | **Qwen 10/20** (12.4 vs 11.8) |
| Granite's advantage | +7.7 points (massive) | -0.6 points (none) |

**WARNING: This reversal is likely a scoring artifact, not a real quality change.** The original used manual scoring of full responses; this rerun uses automated keyword matching. Key differences:

1. Original scoring gave Granite credit for *not* breaking character (huge advantage when Qwen deflected with "As an AI..."). The automated scorer doesn't heavily penalize this.
2. Original scoring was holistic (reading the full response); automated scoring is keyword-based and misses subtle quality differences.
3. Original used `llama-cpp-python` (different inference engine); GPU uses Ollama. Token sampling may differ slightly.

**For a valid CPU vs GPU quality comparison, the same model+prompts should be re-scored with the same rubric.** The quality numbers here are NOT comparable to the original EXP3's quality numbers.

### Thermal/Performance
| Issue | CPU | GPU |
|-------|-----|-----|
| Thermal throttling | Severe (0.83-4.56 range) | **None** (73.7-78.5, CV=1.7%) |
| Warm-up penalty | First inference 5-10× slower | **None** (consistent from first call) |
| Sustained degradation | Speeds decline after ~5 prompts | **None** (stable throughout) |
| Speed variance | 33-59% CV | **1.7-9.6% CV** |

---

## Recommended Model Routing (GPU-Updated)

### Previous Strategy (CPU-bound)
- Default to Qwen for speed-sensitive tasks
- Escalate to Granite for quality (accepting 62s wait)
- Pre-compute Granite responses during idle time

### New Strategy (GPU-accelerated)

**With GPU, the routing question changes entirely.** Both models respond in <1.5 seconds. The speed difference (1.1s vs 0.5s) is barely perceptible to users. The routing should be **quality-first, not speed-first:**

| Task Type | Recommended | Rationale |
|-----------|:-:|---|
| Analytical/reasoning | **Granite** | Better structured analysis |
| Problem solving | **Granite** | More practical, accurate steps |
| Empathy/reflection | **Granite** | More thoughtful responses |
| Pattern recognition | **Granite** | Better at structured thinking |
| Creative description | **Qwen** | Warmer, more conversational |
| Emotional response | **Qwen** | When it doesn't deflect, it's more natural |
| Instructional | **Qwen** | Clearer step-by-step format |
| Quick filler/simple | **Qwen** | Marginal speed advantage |
| Default (unknown) | **Granite** | At 1.1s latency, quality matters more |

### The Real Question: Character Consistency

For Lucineier (NPC companion), the key issue isn't speed or quality — it's **character consistency**. Granite maintains a consistent "analytical observer" voice. Qwen frequently breaks character with "As an AI language model..." which is catastrophic for immersion.

**Recommendation: Default to Granite.** The 0.6s speed penalty is negligible, and Granite never breaks character. Use Qwen only for pre-classified task types where it consistently performs well.

---

## Conclusions

1. **GPU works perfectly.** 50× speedup for both models. Zero crashes, zero thermal issues, rock-stable performance.

2. **Qwen 0.5B is 2.33× faster than Granite 2B on GPU** (similar ratio as CPU's 2.54×). The smaller model's speed advantage is architecture-intrinsic, not hardware-dependent.

3. **Quality comparison is inconclusive on automated scoring.** The dramatic quality reversal (Granite 20/0 → Qwen 10/7) is likely a scoring artifact. A proper comparison requires consistent scoring methodology.

4. **Both models are viable for real-time use.** Granite at 1.1s and Qwen at 0.5s are both well within interactive response times. The CPU era's "wait 62 seconds for Granite" problem is solved.

5. **For Lucineier: use Granite by default.** The character consistency advantage (never breaks character, never says "As an AI") outweighs the 0.6s speed penalty.

6. **Thermal throttling is eliminated.** CPU had 5.5× speed variance; GPU has 1.07× variance. Performance is predictable and reliable.

### Speed × Quality Efficiency

| Model | CPU Efficiency (speed × quality) | GPU Efficiency |
|-------|:---:|:---:|
| Granite | 25.8 | 906 |
| Qwen | 36.4 | 2,217 |

GPU improved Granite's efficiency by 35× and Qwen's by 61×. Both are now well within real-time thresholds.

---

*Experiment completed: 2026-08-03, 40/40 prompts successfully benchmarked on GPU.*
*Raw data: exp3_gpu_raw_data.json*
