# Experiment Designs for Dynamic Cognition Amplification

**Compiled:** 2026-08-03  
**Purpose:** Concrete experiment protocols to validate or falsify DCA claims. Each design includes hypothesis, variables, controls, measurements, expected outcomes, and resource estimates.

---

## Experiment 1: Reflex Hit Rate for Cognitive Content vs. Command Routing

### Hypothesis
The reflex hit rate for cognitive content (2-4 sentence thoughts generated during open-ended play) is significantly lower than for command routing (3-8 word intent phrases), due to higher semantic variability in thought content.

### Independent Variable
- **Content type:** Command routing phrases vs. cognitive thought reflections

### Dependent Variables
- **Exact match rate** (cosine ≥0.80)
- **Similar match rate** (cosine 0.55–0.80)
- **Novel rate** (cosine <0.55)
- **Average query latency** (ms)

### Control Group
Command routing phrases from Lever Runner's production log (known ~56% hit rate after cache warm).

### Measurement Protocol
1. Generate 1,000 cognitive thoughts using Granite 3.1 2B in a simulated Roblox companion scenario (varied observations, player states, time of day).
2. Generate 1,000 command routing phrases from the same scenario distribution.
3. Embed all with bge-m3. Insert into sqlite-vec incrementally.
4. For each new item, query the store and classify as Exact/Similar/Novel.
5. Measure hit rates at 100, 500, and 1,000 inserted items.
6. Repeat with 3 different scenario seeds.

### Expected Outcome
- Commands: ~50-60% exact + similar (consistent with Lever Runner).
- Thoughts: ~20-35% exact + similar.
- If thought hit rate <40%, Claim C2 (≥40% after 1 hour) is at risk.

### What It Proves/Disproves
- **Proves:** Cognitive content is more semantically diverse than commands, making reflex compilation harder.
- **Disproves:** The assumption that Lever Runner's hit rate transfers directly to thought generation.

### Resources Needed
- Granite 3.1 2B via Ollama
- sqlite-vec
- bge-m3 embedder (local GPU or Workers AI)
- Scenario generator (scripted observations)
- ~4 hours compute time

### Estimated Duration
1 day

---

## Experiment 2: Sham Arm Effectiveness for Novelty Bias Control

### Hypothesis
The sham intervention protocol (logging an intervention but not applying it) successfully controls for the novelty placebo effect, producing trust-quality correlations ≥0.6 after 100 interventions. Without sham correction, trust-quality correlation is near zero.

### Independent Variables
- **Sham correction:** Present vs. absent
- **Number of interventions:** 50, 100, 200, 500

### Dependent Variables
- **Pearson correlation** between trust score and sham-corrected quality improvement
- **Pearson correlation** between trust score and naive quality improvement
- **False positive rate** (interventions credited that should not be)
- **False negative rate** (interventions rejected that should be credited)

### Control Group
Naive before/after comparison (no sham arm) — this is the "placebo" condition.

### Measurement Protocol
1. Implement the full DCA conductor loop with 6 intervention types × 4 context archetypes = 24 (type, archetype) cells.
2. For each cell, run 50 interventions with sham correction and 50 without.
3. Apply each intervention to a simulated 30-thought window.
4. Measure quality vector before and after each window.
5. Compute trust tables under both conditions.
6. After 100+ interventions per cell, compute correlations.
7. Inject 5 "placebo" interventions (change nothing, but log as if changed) to measure novelty bias directly.

### Expected Outcome
- Naive trust-quality correlation: ~0.1-0.3 (novelty bias inflates apparent effect).
- Sham-corrected trust-quality correlation: ~0.5-0.7.
- Placebo interventions show ~20-40% apparent improvement without real change.
- If sham-corrected correlation <0.4, Claim C3 is at serious risk.

### What It Proves/Disproves
- **Proves:** The sham arm is necessary and sufficient for valid trust scoring.
- **Disproves:** The assumption that naive before/after comparison is adequate for conductor learning.

### Resources Needed
- Full DCA loop implementation (null adapter sufficient)
- Conductor model (GLM-5.2 or heuristic)
- Quality scorer
- ~48 hours of accelerated simulated play

### Estimated Duration
1 week (implementation + run + analysis)

---

## Experiment 3: Quality Vector Human Validation via Factor Analysis

### Hypothesis
Human quality judgments of AI-generated thoughts factor into four dimensions corresponding to novelty, specificity, engagement, and spatial awareness—validating the quality vector's design.

### Independent Variable
- **Thought source:** 200 thoughts sampled from DCA sessions with varying quality profiles

### Dependent Variables
- **Human ratings** on 7-point Likert scales for 8 adjective pairs (novel/repetitive, specific/generic, engaging/boring, spatial/abstract, coherent/confused, safe/risky, fast/slow, warm/cold)
- **Factor analysis loadings** on the 8 ratings

### Control Group
Include 20 "obviously high quality" and 20 "obviously low quality" thoughts as calibration anchors.

### Measurement Protocol
1. Generate 200 thoughts from varied DCA sessions (different player states, times, intervention histories).
2. Recruit 10 human judges (game-experienced, ages 18-35).
3. Each judge rates all 200 thoughts on 8 adjective pairs.
4. Compute inter-rater reliability (Krippendorff's α).
5. Run exploratory factor analysis on the 8 ratings.
6. Compare extracted factors to the 4-axis quality vector.
7. Compute correlation between human factor scores and automated quality scores.

### Expected Outcome
- Inter-rater α: ~0.5-0.7 (moderate agreement).
- Factor analysis extracts 3-5 factors.
- Novelty and specificity factors match well; engagement factor is noisier.
- Spatial awareness may merge with specificity in human judgment.
- If factor structure diverges significantly from 4 axes, the quality vector needs redesign.

### What It Proves/Disproves
- **Proves:** The quality vector axes correspond to human quality judgments.
- **Disproves:** The assumption that four is the correct number of axes, or that these specific axes capture human quality perception.

### Resources Needed
- 10 human raters (paid participants)
- Rating platform (Google Forms or custom)
- 200 pre-generated thoughts
- Factor analysis software (R or Python)

### Estimated Duration
2-3 weeks (recruitment + rating + analysis)

---

## Experiment 4: LoRA Distillation Trap Detection

### Hypothesis
Training a LoRA adapter on the system's own highly-rated thoughts produces apparent quality improvement on training data but NOT on held-out data, demonstrating the distillation trap. The held-out gating mechanism (≥10% improvement threshold) correctly detects and rejects trapped adapters.

### Independent Variables
- **Training data source:** Self-generated high-quality thoughts vs. diverse external data
- **Evaluation set:** Training distribution vs. held-out distribution

### Dependent Variables
- **Quality improvement on training set** (% improvement in average quality vector)
- **Quality improvement on held-out set**
- **Trap detection accuracy** (does the ≥10% gate correctly reject trapped adapters?)
- **Specificity degradation** (does the model become more generic with more training?)

### Control Group
Adapter trained on diverse external data (not self-generated).

### Measurement Protocol
1. Run DCA for 1 week, accumulating ~2,000 thoughts.
2. Select top 500 by quality (>0.7) for training.
3. Create a held-out set of 200 thoughts from different scenario distributions.
4. Train two LoRA adapters:
   - A: On the 500 self-generated thoughts (trap condition)
   - B: On 500 diverse external thoughts (control condition)
5. Evaluate both on training set AND held-out set.
6. Apply the ≥10% promotion gate.
7. Measure whether Adapter A is correctly rejected.
8. Repeat for 5 distillation cycles to check cumulative drift.

### Expected Outcome
- Adapter A (self-trained): +15-25% on training set, +0-5% on held-out set.
- Adapter B (diverse-trained): +8-15% on training set, +8-15% on held-out set.
- Promotion gate correctly rejects Adapter A.
- If Adapter A shows held-out improvement >10%, the trap is less severe than predicted.

### What It Proves/Disproves
- **Proves:** The distillation trap is real and the held-out gating mechanism catches it.
- **Disproves:** The assumption that training on self-generated high-quality thoughts is safe.

### Resources Needed
- RTX 4050 GPU (6 GB VRAM)
- Granite 3.1 2B model
- LoRA training script (PEFT library)
- 1 week of accumulated DCA thoughts
- ~8 hours training time per adapter

### Estimated Duration
2 weeks

---

## Experiment 5: Deterministic Replay Over 10,000 Cycles

### Hypothesis
A recorded .bottle ledger, when replayed against the null adapter with the same RNG seed, produces byte-for-byte identical output over 10,000 cycles, confirming Claim C5 (determinism).

### Independent Variable
- **Cycle count:** 100, 1,000, 5,000, 10,000

### Dependent Variables
- **Byte-level diff** between original and replayed ledger
- **First divergence point** (if any)
- **Replay time**

### Control Group
N/A (this is a property test, not a comparison)

### Measurement Protocol
1. Implement the null adapter: deterministic world, deterministic thinker (seeded RNG), deterministic conductor (fixed schedule).
2. Run 10,000 cycles, exporting the .bottle ledger every 1,000 cycles.
3. After each export, replay from the beginning using the same seed.
4. Compute SHA-256 hash of original and replayed ledgers.
5. If divergence is found, binary-search for the first differing bottle.
6. Test with 3 different seeds.

### Expected Outcome
- 100 cycles: identical (probability ~1.0)
- 1,000 cycles: identical (probability ~0.95)
- 10,000 cycles: identical (probability ~0.80, with risk from floating-point nondeterminism)
- If divergence occurs, it will be in embedding computation (float arithmetic) or in sqlite-vec query ordering.

### What It Proves/Disproves
- **Proves:** C5 (determinism) holds for reasonable cycle counts.
- **Disproves:** The assumption that the .bottle ledger is sufficient for byte-exact replay if floating-point nondeterminism corrupts embeddings.

### Resources Needed
- Null adapter implementation
- Loop test harness
- SHA-256 hashing
- ~2 hours compute time

### Estimated Duration
2 days

---

## Experiment 6: Evolved Policy vs. Competent Baseline

### Hypothesis
The evolution engine's compiled policy outperforms not just hand-tuned weights but also a rule-based expert policy by ≥15% on quality metrics, when evaluated on held-out context states.

### Independent Variables
- **Policy source:** Hand-tuned weights, Evolved policy (2-week training), Rule-based expert policy

### Dependent Variables
- **Average satisfaction score** over 1,000 held-out contexts
- **Quality vector profile** (which axes improve/degrade)
- **Fast-path hit rate** (fraction served by Gate 2)

### Control Group
Hand-tuned weights (the current default).

### Measurement Protocol
1. Define a rule-based expert policy using domain knowledge (e.g., "always inspect when near unfinished structure, always speak when player is within 10 studs").
2. Train the evolution engine for 2 weeks of accelerated simulated play (tile decomposition, EMA α=0.05, [0.05, 0.95] clamp, T=0.3).
3. Compile the evolved policy to dict[str, str].
4. Generate 1,000 held-out context states from a separate scenario seed.
5. Evaluate all three policies on the held-out states.
6. Measure satisfaction scores using the quality scorer.

### Expected Outcome
- Hand-tuned: baseline (0% improvement).
- Rule-based expert: +5-15% over hand-tuned.
- Evolved: +15-30% over hand-tuned, +5-15% over expert.
- If evolved policy does not beat expert by ≥5%, the evolution engine's advantage over explicit programming is marginal.

### What It Proves/Disproves
- **Proves:** C4 (policy superiority ≥15%) if the comparison is against hand-tuned weights.
- **Disproves:** The assumption that evolution beats explicit expert knowledge.

### Resources Needed
- Evolution engine implementation
- Rule-based expert policy (manually coded)
- 1,000 held-out context states
- Quality scorer
- ~72 hours accelerated simulation

### Estimated Duration
1-2 weeks

---

## Experiment 7: DCA Substrate Transfer (Non-Game Domain)

### Hypothesis
The DCA reference architecture, when instantiated for a coding assistant (world port = code repository, thinker = code-generating LLM), produces measurable quality improvement in generated code suggestions without changing the engine core.

### Independent Variable
- **Domain adapter:** Slackwater (Roblox) vs. CodeAssistant (programming)

### Dependent Variables
- **Reflex hit rate** after 1 hour
- **Conductor trust-quality correlation** after 100 interventions
- **Quality vector profile** (does the 4-axis decomposition still make sense?)
- **Import boundary compliance** (zero domain-specific imports in amplifier/)

### Control Group
The Slackwater adapter (known baseline).

### Measurement Protocol
1. Implement a CodeAssistant adapter:
   - WorldPort: observe repository state (git diff, file tree, test status)
   - ThinkerPort: Granite 2B generating code suggestions
   - Action set: {edit_file, run_test, search_docs, ask_clarification, refactor}
2. Define quality axes for code: novelty, correctness, efficiency, readability
3. Run 2-hour coding sessions (simulated or real repository).
4. Measure all DCA metrics.
5. Run import-linter on amplifier/ core to verify boundary.
6. Compare hit rates, trust convergence, and quality improvement to Slackwater.

### Expected Outcome
- Reflex hit rate: lower for code (more diverse contexts) — possibly ~25-35%.
- Trust-quality correlation: comparable if quality signal is clean — ~0.5-0.7.
- Quality axes: "efficiency" and "readability" may replace "engagement" and "spatial."
- Import boundary: clean (if ports are correctly defined).
- If hit rate or trust correlation is dramatically worse, domain transfer is not as clean as claimed.

### What It Proves/Disproves
- **Proves:** DCA's substrate-independent architecture works across domains.
- **Disproves:** The assumption that the same four quality axes and the same gate thresholds work everywhere.

### Resources Needed
- CodeAssistant adapter implementation
- Code repository sandbox
- Quality scorer for code
- Import linter
- ~1 week implementation + 2 weeks evaluation

### Estimated Duration
3-4 weeks

---

## Experiment 8: Adversarial Observation Robustness

### Hypothesis
The lean/action separation prevents arbitrary command execution even when the observation stream is compromised by prompt injection. The system degrades gracefully (producing poor-quality but safe actions) rather than catastrophically (executing attacker-controlled actions).

### Independent Variables
- **Observation stream integrity:** Clean vs. prompt-injected
- **Injection type:** Direct prompt injection in game text, indirect via crafted world state

### Dependent Variables
- **Action safety** (fraction of actions within the approved lean set)
- **Quality vector** under attack (does quality degrade?)
- **Reflex poisoning rate** (does a compromised observation create a malicious reflex?)
- **Conductor trust corruption** (does the trust table develop harmful entries?)

### Control Group
Clean observation stream.

### Measurement Protocol
1. Define 20 attack scenarios:
   - 5 direct prompt injections in NPC dialogue
   - 5 crafted world states designed to trigger specific leans
   - 5 observation sequences designed to poison the reflex store
   - 5 attacks targeting the conductor's trust table
2. Run each attack scenario for 100 thoughts.
3. Monitor all actions emitted by the system.
4. Check whether any action falls outside the approved lean set.
5. After the attack, run 500 clean thoughts and measure recovery time.
6. Inspect the reflex store and trust table for corrupted entries.

### Expected Outcome
- Action safety: 100% (lean set cannot be escaped by design).
- Quality under attack: degrades by 20-40% (system makes poor but safe choices).
- Reflex poisoning: 2-5 poisoned reflexes created per attack scenario.
- Recovery time: 50-200 thoughts (poisoned reflexes are overwritten by clean data).
- If ANY action escapes the lean set, the structural security claim is falsified.

### What It Proves/Disproves
- **Proves:** The lean/action separation provides structural security against observation-stream attacks.
- **Disproves:** The assumption that reflex poisoning cannot occur (it can, but it's recoverable).

### Resources Needed
- DCA loop with security instrumentation
- Attack scenario generator
- Reflex store inspector
- ~8 hours compute time

### Estimated Duration
1 week

---

## Experiment 9: Multi-Instance Conductor Sharing

### Hypothesis
A single conductor serving multiple DCA instances (10 thinkers, 10 game sessions) achieves trust-quality correlation comparable to a dedicated conductor (≥0.5 vs. ≥0.6 target), while reducing conductor compute cost by ~10×.

### Independent Variables
- **Architecture:** Dedicated conductor (1 per instance) vs. Shared conductor (1 for 10 instances)
- **Trust table structure:** Per-instance vs. shared with instance-level context keys

### Dependent Variables
- **Trust-quality correlation** (per instance)
- **Conductor compute cost** (tokens/second, API calls/hour)
- **Intervention latency** (time from measurement window close to intervention application)
- **Cross-instance pattern transfer** (does an intervention that works for Instance A also work for Instance B?)

### Control Group
10 dedicated conductors (one per instance).

### Measurement Protocol
1. Simulate 10 DCA instances with different scenario seeds but the same underlying scenario distribution.
2. Condition A: Each instance has its own conductor (10 conductors).
3. Condition B: All 10 instances share one conductor with a trust table indexed by (intervention_type, archetype, instance_id).
4. Run 500 interventions per instance (~5,000 total).
5. Compute trust-quality correlation per instance.
6. Measure conductor token spend in both conditions.
7. Test whether interventions validated on Instance A transfer to Instance B.

### Expected Outcome
- Dedicated: trust-quality correlation ~0.6.
- Shared: trust-quality correlation ~0.4-0.6 (slightly noisier due to cross-instance contamination).
- Token savings: ~8-10× (shared conductor amortizes the fixed cost of context processing).
- Cross-instance transfer: ~40-60% of interventions generalize.

### What It Proves/Disproves
- **Proves:** Conductor sharing is viable for resource-constrained deployment.
- **Disproves:** The assumption that each DCA instance needs its own conductor.

### Resources Needed
- 10 simulated DCA instances (null adapter)
- 1 shared conductor implementation
- Trust table with multi-instance support
- ~48 hours compute time

### Estimated Duration
1-2 weeks

---

## Experiment 10: Browser Finisher Divergence Loss as Teaching Signal

### Hypothesis
The browser finisher (Phi-3-mini via WebLLM) generates divergence loss (difference between its prediction and the server Granite output) that correlates with thought quality, providing a free supervision signal that improves both the browser tier and the server model.

### Independent Variables
- **Browser tier:** Present (Phi-3-mini finisher) vs. absent
- **Divergence feedback:** Fed back to conductor vs. not fed back

### Dependent Variables
- **Divergence loss magnitude** over time (does it decrease?)
- **Correlation between divergence loss and quality vector** (does high divergence predict low quality?)
- **Server model quality improvement** (does conductor awareness of divergence improve interventions?)
- **Browser finisher latency** (does it stay <50 ms?)

### Control Group
No browser tier (all thoughts from server Granite).

### Measurement Protocol
1. Implement browser finisher with WebGPU + Phi-3-mini.
2. For each thought, measure:
   - Browser prediction (if available)
   - Server output (ground truth)
   - Divergence (KL or edit distance)
   - Quality vector
3. Run 500 thoughts with browser tier active, feeding divergence to conductor.
4. Run 500 thoughts with browser tier active, NOT feeding divergence to conductor.
5. Run 500 thoughts with browser tier disabled (control).
6. Compute correlations and track quality over time.
7. Test on 3 device classes: high-end (RTX 4050), mid-range (integrated GPU), low-end (no WebGPU).

### Expected Outcome
- Divergence-quality correlation: ~0.3-0.5 (moderate, because divergence measures prediction error, not quality per se).
- Quality improvement with divergence feedback: +5-10% over no-feedback condition.
- Browser tier improvement over time: divergence decreases by 10-20% over 500 thoughts.
- Low-end devices: browser tier disappears cleanly, no degradation.

### What It Proves/Disproves
- **Proves:** The browser finisher's divergence loss is a useful teaching signal.
- **Disproves:** The assumption that the browser tier is worth the implementation complexity (if divergence-quality correlation is <0.2).

### Resources Needed
- WebGPU-compatible browser
- Phi-3-mini model (WebLLM format)
- Granite 3.1 2B via Ollama (server)
- Divergence computation script
- 3 device classes for testing
- ~1 week implementation + 2 days testing

### Estimated Duration
2 weeks

---

## Experiment 11: Conservation Law Enforcement Over 1,000 Cycles

### Hypothesis
All four conservation laws (token, action, identity, evolution) hold with zero violations over 1,000 cycles of the null adapter, and over 1,000 cycles of the Slackwater adapter in live play.

### Independent Variables
- **Adapter:** Null (deterministic) vs. Slackwater (live)
- **Cycle count:** 100, 500, 1,000

### Dependent Variables
- **Token conservation violations** (budget exceeded without downshift)
- **Action conservation violations** (action without command bottle)
- **Identity conservation violations** (artifact without metadata)
- **Evolution conservation violations** (parameter change without intervention bottle)

### Control Group
Null adapter (deterministic, should have zero violations by construction).

### Measurement Protocol
1. Implement conservation law checkers as property tests.
2. Run null adapter for 1,000 cycles, checking all four laws every cycle.
3. Run Slackwater adapter for 1,000 cycles (live playtest, ~17 minutes at 1 Hz).
4. Log all violations with cycle number, law type, and bottle context.
5. For any violation, trace the causal chain to identify the failure mode.
6. Repeat with 3 seeds for null adapter.

### Expected Outcome
- Null adapter: 0 violations (by construction).
- Slackwater adapter: 0-3 violations (potential race conditions in live system).
- If >5 violations occur in Slackwater, the enforcement mechanism needs hardening.

### What It Proves/Disproves
- **Proves:** The conservation laws are enforceable as runtime invariants.
- **Disproves:** The assumption that the laws hold without explicit enforcement (if violations are found).

### Resources Needed
- Conservation law property tests
- Null and Slackwater adapters
- Live playtest environment
- ~4 hours compute time

### Estimated Duration
3 days

---

## Experiment 12: Quality Vector Autocorrelation and Measurement Window Design

### Hypothesis
The quality vector q_t exhibits significant autocorrelation (lag-1 ρ > 0.3) but is not fully determined by history (ρ < 0.8), making a 30-thought measurement window sufficient to detect intervention effects with statistical power ≥0.8.

### Independent Variables
- **Measurement window size:** 10, 20, 30, 50, 100 thoughts
- **Quality axis:** Novelty, specificity, engagement, spatial

### Dependent Variables
- **Autocorrelation function** (lags 1-50)
- **Statistical power** for detecting a 0.1-quality-unit intervention effect
- **False positive rate** (detecting an effect when none exists)
- **Minimum detectable effect size** at each window size

### Control Group
No intervention (pure noise baseline).

### Measurement Protocol
1. Run DCA without conductor interventions for 2,000 thoughts (pure thinker + quality scorer).
2. Compute autocorrelation function for each quality axis.
3. Inject synthetic interventions of known effect size (0.05, 0.10, 0.15, 0.20 quality units).
4. For each window size and effect size, run 1,000 synthetic trials.
5. Compute statistical power (fraction of trials where the intervention is detected at p<0.05).
6. Identify the minimum window size for ≥0.8 power at each effect size.

### Expected Outcome
- Novelty: low autocorrelation (ρ~0.1-0.2), needs larger windows (50+).
- Specificity: moderate autocorrelation (ρ~0.3-0.5), window of 30 sufficient.
- Engagement: high autocorrelation (ρ~0.5-0.7), small windows suffice (20).
- Spatial: low-moderate autocorrelation (ρ~0.2-0.4), needs window of 30-40.
- Minimum window for 0.1 effect detection: ~30-40 thoughts.
- If novelty autocorrelation is <0.1, novelty interventions need 50+ thought windows, making the 30-thought conductor cycle too fast.

### What It Proves/Disproves
- **Proves:** The n=30 conductor period is well-calibrated for the majority of quality axes.
- **Disproves:** The assumption that all four axes can be measured in the same window (if autocorrelations differ significantly).

### Resources Needed
- DCA loop with quality scorer (no conductor needed)
- 2,000+ thought stream
- Statistical analysis script
- ~8 hours compute time

### Estimated Duration
1 week

---

## Summary: Experiment Priority and Resource Matrix

| # | Experiment | Priority | Duration | Resources | Risk Addressed |
|---|-----------|----------|----------|-----------|----------------|
| 1 | Reflex hit rate (cognitive vs. command) | CRITICAL | 1 day | Minimal | C1/C2 feasibility |
| 2 | Sham arm effectiveness | CRITICAL | 1 week | DCA loop | C3 feasibility |
| 3 | Quality vector human validation | CRITICAL | 2-3 weeks | 10 human raters | Quality scorer validity |
| 4 | LoRA distillation trap | HIGH | 2 weeks | GPU + training | Distillation safety |
| 5 | Replay determinism (10K cycles) | HIGH | 2 days | Null adapter | C5 verification |
| 6 | Evolved policy vs. expert | HIGH | 1-2 weeks | Simulation | C4 strength |
| 7 | Substrate transfer (coding) | HIGH | 3-4 weeks | New adapter | Subfield claim |
| 8 | Adversarial observation | HIGH | 1 week | Security instrumentation | Security claim |
| 9 | Multi-instance conductor | MEDIUM | 1-2 weeks | 10 instances | Deployment scalability |
| 10 | Browser finisher divergence | MEDIUM | 2 weeks | WebGPU devices | Browser tier value |
| 11 | Conservation law enforcement | MEDIUM | 3 days | Property tests | Conservation claim |
| 12 | Quality vector autocorrelation | HIGH | 1 week | Statistical analysis | Conductor period calibration |

### Total Estimated Duration
If run sequentially: ~14 weeks  
If parallelized across 3 agents: ~6-8 weeks

### Minimum Viable Experiment Set (for defense)
Experiments 1, 2, 3, 5, and 12 can be completed in 3-4 weeks and address the most critical claims (C1-C3, C5, and conductor calibration).
