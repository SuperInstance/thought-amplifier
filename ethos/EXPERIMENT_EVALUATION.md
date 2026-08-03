# Experiment Evaluation — EXP1 (Reflex Hit Rate) and EXP2 (Semantic Gradient)

**Author:** Claude Opus, acting as Ethos (evaluative faculty)
**Date:** 2026-08-03 (revised — EXP2 was completely rerun since my prior pass)
**Verdict, in one line:** EXP1 falsifies its own hypothesis and its rescue claim is unproven. EXP2 is now a real, honestly-executed, sham-validated experiment — and it mildly undermines the strong form of the DCA thesis (no detectable *net* quality gain) while leaving the weak form (interventions have *some* real, content-dependent effect) intact. Neither experiment validates DCA. Both move the project from "no data" to "data that doesn't yet say what the dissertation needs it to say."

**Revision note:** my previous version of this file evaluated an EXP2 run that crashed against a local Ollama/CUDA failure and produced zero data for two of four phases. That run has been superseded — commit `b4fe1ab` reruns EXP2 against a cloud API (DeepInfra, `google/gemma-3-12b-it`), sidestepping the local GPU problem entirely, and this time all four phases completed with real data. EXP1 is unchanged (verified by hash/line-count against the version I reviewed previously). This document replaces the prior evaluation rather than patching it, because the EXP2 section changed too much to edit in place.

---

## EXP1: Reflex Hit Rate — unchanged, verdict stands

No new data here since my last pass. Recap, for completeness:

| | Cognitive | Command | Target (C2) |
|---|---|---|---|
| Hit rate @ ≥0.55 (TF-IDF) | 13.1% | 6.1% | ≥40% |

- **The pre-registered hypothesis ("cognitive < command hit rate") is falsified, not just unconfirmed** — cognitive similarity came in significantly *higher* than command similarity (Welch's t, p<0.000001, d=-0.83, two-sided). The report's own "not significant" Mann-Whitney result tested the wrong tail (one-sided for cog<cmd, when the data ran the other way) and shouldn't be read as a null finding.
- **The synthetic data generation likely undersells both domains equally**: uniform random sampling over millions of template combinations produces near-zero repetition, unlike the Zipfian recurrence real command routing (and the Pincher/Lever Runner precedent numbers) depend on. Neither hit rate here should be read against the dissertation's inherited 50–80% targets as an apples-to-apples comparison.
- **The "neural embeddings rescue C2" claim rests on n=8 templated items**, not the n=100 used to falsify the TF-IDF version, uses the term "cross-validation" incorrectly, and has no threshold-sensitivity sweep. This is a hopeful spot-check, not a finding. Claim C2 should be treated as unsupported at production scale until rerun properly.

Full detail unchanged from before; see the EXP1 file itself for the complete threshold table and per-item classification.

---

## EXP2: Semantic Gradient — completely new data, credit due

### What changed, and why it matters

The prior run died against the same GPU/CUDA collapse `ADVISORY_BRIDGE.md` had already diagnosed, twice. This run moved to a cloud API and got a clean, complete dataset: N=15 per phase, all four phases (baseline, intervention, reversal, sham), zero generation failures, ~2 minutes runtime, ~$0.0005 cost. This is exactly the "don't fight the infrastructure, route around it" move I'd have recommended, and it produced the first real sham-arm data this project has ever collected. That's genuine progress and worth stating plainly before the critique below.

### The numbers

| Phase | Novelty | Specificity | Engagement | Total |
|---|---|---|---|---|
| baseline | 0.867 ± 0.35 | 1.000 ± 0.00 | 1.000 ± 0.00 | 2.867 ± 0.35 |
| intervention | 1.000 ± 0.00 | 1.000 ± 0.00 | 0.867 ± 0.35 | 2.867 ± 0.35 |
| reversal | 0.800 ± 0.41 | 1.000 ± 0.00 | 1.000 ± 0.00 | 2.800 ± 0.41 |
| sham | 0.800 ± 0.41 | 1.000 ± 0.00 | 1.000 ± 0.00 | 2.800 ± 0.41 |

Two findings are genuinely solid, and one is asserted more confidently than the statistics support.

**Solid finding 1: the ceiling effect is real and well-established.** Specificity scored 1.000 with zero variance across all 60 generations, in every phase. That's n=60, not a small sample — this is a clean, unambiguous result: the binary rubric, this task (describe a maritime island), and a 12B-class model combine to leave no room for specificity to move at all. This is a legitimate methodological finding independent of the DCA question, and it explains why the total score can't show much regardless of what's happening underneath.

**Solid finding 2: the sham arm actually worked this time.** Baseline vs. sham is not significant (Δ=-0.067, p=0.63), and reversal and sham are statistically indistinguishable from each other and from baseline. That's what a valid negative control is supposed to look like — a vacuous prompt change (sham) produces no detectable effect, while a content-bearing one (intervention) at least trends differently. This is the first time in this project that the sham-arm mechanism — the thing `CLAUDE_REVIEW.md` calls the dissertation's single best idea — has actually behaved the way it's supposed to. Worth crediting explicitly.

**Overclaimed finding: the "profile shift" itself is a trend, not an established effect, and the report's language doesn't consistently reflect that.** Novelty moved 0.867→1.000 and engagement moved 1.000→0.867 (baseline vs. intervention), exactly canceling in the total. Both are Cohen's d≈0.54, p=0.14 uncorrected, Bonferroni-corrected p=1.0 in the report's own table. With binary scoring at n=15 per arm, that shift is exactly 2 of 15 items flipping on each axis — a small, real-looking pattern, but not one that clears conventional significance even before correcting for the four comparisons run. A rough power calculation confirms this: for d≈0.5 at α=0.05 two-sided, 80% power needs roughly n≈55–60 per group — this run has 15. The report's Verdict and Conclusion sections say "this profile shift is real and interesting" and "the effect is real (content-dependent, not placebo)." I'd soften that: the pattern is *directionally coherent and mechanistically plausible* (a materials/texture-focused prompt plausibly displaces first-person emotional language within a fixed 60-token budget — that's a sensible causal story), and it's worth taking seriously as a hypothesis, but "real" is doing more work than p=0.14 earns it. This is the same shape of overclaim I flagged in the previous EXP2 report (there, a categorical "NOT DETECTABLE" headline over data that was mostly never collected; here, a categorical "real" over data that's suggestive but underpowered) — the team's instinct to state a clear verdict is good practice, but the confidence language should track the p-values more tightly than it currently does.

**A caveat the report itself raises well, and I want to underline:** `gemma-3-12b-it` is roughly 6× larger than the 2B-class model (Granite 3.1 2B) the dissertation actually targets for the local thinker, and a 12B model already ceilings on this task. If the profile-shift pattern is real, we still don't know whether it holds, strengthens, or vanishes at the actual target model scale — smaller models plausibly have *more* headroom for a directed prompt to move quality (in either direction), which cuts both for and against the DCA thesis depending on which axis moves. This is honestly flagged in the report's own Conclusion ("DCA's value proposition is strongest where the base model is weakest") and I think it's the single most important open question this experiment raises.

### What this means for the thesis, precisely

The dissertation's claim is that directed intervention produces *quality improvement* — a net gain, not merely a change. EXP2, as executed, shows: no detectable net gain (total score flat, sham-indistinguishable-from-intervention on the aggregate), a directionally plausible but statistically unconfirmed *redistribution* across axes, and — crucially — a working sham-arm methodology that would have caught a naive novelty-bias artifact if one had been present, and didn't find one. That's not nothing. It's evidence against the *strong* claim (net improvement) under this specific configuration, and it's silent on the *weak* claim (intervention selection matters at all, i.e., interventions aren't interchangeable) because that comparison (real vs. sham, Q3) also isn't significant (p=0.63) — so even the "content-dependent effect" claim in the report's point 4 is a trend read off non-significant numbers, not an established result. I'd state it more cautiously than the report does: this experiment is *consistent with* interventions producing axis-level trade-offs rather than net gains, and it's the best-executed test of that question this project has run, but "consistent with" and "shows" are different epistemic states, and the write-up sometimes uses the language of the latter for evidence that supports only the former.

---

## Cross-cutting: what this tells us about the production line model

The move to a cloud API for EXP2 is good experimental hygiene — it isolates "does the semantic gradient exist" from "does our local GPU stay up" as separate questions, and it got a clean answer to the first one. But it also means this experiment tells us **nothing new** about the local production-line claim (RTX 4050, Ollama, continuous 1–2Hz thinker, the scheduler's fair-use/priority model). That claim is exactly as unverified as it was after the crashed run — the team correctly worked around the GPU reliability problem for this experiment rather than solving it, which was the right call for getting an answer to the semantic-gradient question quickly, but the underlying infrastructure question (can the local stack sustain the workload the dissertation describes) remains open and untested. Don't read EXP2's clean execution as evidence the CUDA/reliability issue is resolved — it was routed around, not fixed.

---

## Direct answers

**Do these results validate or undermine the DCA thesis?** Mildly undermine, with real uncertainty attached rather than a clean negative. EXP1 falsifies its stated hypothesis and leaves its fallback claim (C2 via neural embeddings) unproven. EXP2, now a genuinely well-executed experiment, finds no significant net quality gain from directed intervention and a sham arm that correctly detected no placebo effect — evidence against the strong thesis under this configuration. What it does *not* do is settle the question for the system the dissertation actually describes: a 2B-class local model, continuous thought stream, autocorrelated context — all four of EXP2's own caveats (12B not 2B, independent generations not a stream, binary not continuous scoring, single task) point at exactly the conditions where the answer might differ. This is a project that has gone from "zero real experiments" to "two real experiments, both technically well-executed, neither confirming the thesis" in the space of a day. That's honest progress, and it's still a REJECT-shaped evidence base.

**What should we do next, based on this real data?**

1. **Don't rerun EXP2 at 12B scale again — rerun it at 2B scale**, using the same DeepInfra-API workaround (many providers host small open models) rather than going back to local Ollama, so the CUDA reliability problem doesn't reintroduce itself. This directly targets the report's own best open question: does the profile-shift pattern change shape at the model size DCA actually targets.
2. **Switch to continuous (0–1, not binary) scoring** before rerunning anything. The ceiling effect here is a scoring-resolution artifact as much as a model-capability one — specificity pinned at 1.000 with zero variance across 60 samples tells you the rubric can't see anything happening on that axis, not that nothing is happening.
3. **Power the next run properly.** The observed effect size (d≈0.5) needs roughly 55–60 samples per arm for conventional power at α=0.05 two-sided, not 15. Decide the minimum effect size worth detecting up front and size N to it, rather than running N=15 again and re-reporting "trending but not significant."
4. **Still add the Conductor-vs-random-intervention arm.** Nothing in EXP1 or EXP2 has tested this yet, and it remains, per `CLAUDE_REVIEW.md`, the one comparison that would tell us whether the Conductor's intelligence contributes anything beyond the fact that prompts have effects.
5. **Rerun EXP1's neural-embedding check at n=100 with real Granite-generated thoughts**, not n=8 templated ones, before treating C2 as supported by anything more than hope.
6. **Separately, and still unresolved:** verify the local Ollama/CUDA stack (the original #1 item) before trusting any future claim about the continuous local thinker or the scheduler's throughput — EXP2's clean result this time is a testament to avoiding that infrastructure, not evidence it's fixed.
