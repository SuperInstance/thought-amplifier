# 9. Distillation and the Slowest Loop

The preceding chapters described learning mechanisms that operate above the weights: reflexes, compiled policies, prompt versions, and trust tables. This chapter describes the slowest loop—low-rank adaptation (LoRA) of the local thinker itself. It is deliberately listed last, because if the faster loops do not work, weight-level fine-tuning cannot rescue them.

## 9.1 The Distillation Trap

Training a model on its own highly-rated outputs is dangerous. The system can converge on its existing biases and call it progress. Every improvement on the training distribution is suspect unless it also appears on held-out data.

DCA mitigates this trap with three rules:

1. **Hold out a fixed evaluation set** that is never used for training;
2. **Sample DPO negatives from genuinely low-quality thoughts**, not merely lower-quality ones;
3. **Gate promotion on held-out gains alone**: the adapted model must beat the base model by at least 10% on the evaluation set.

If quality rises on training data but not on held-out data, the trap is closing, and the adapter must be discarded.

## 9.2 Data Selection

Not every thought is worth learning from. The selection filter is:

\[
\text{quality} > 0.7 \;\land\; \text{conductor_commentary} = \text{positive} \;\land\; \text{action_result} = \text{success}.
\]

This selects thoughts that were good, recognized as good, and led to successful outcomes. The selected set is quality-weighted: higher-quality thoughts are sampled more frequently during training, but the weighting is sub-linear to prevent a single high-scoring thought from dominating.

## 9.3 SFT and DPO Pairs

Two kinds of training pairs are constructed:

**Supervised fine-tuning (SFT) pairs.** Input is the game state and prompt version; output is the thought text, lean, and action taken:

\[
(s, \pi) \to (\tau, \ell, a).
\]

**Direct preference optimization (DPO) pairs.** For similar states, a high-quality thought is paired with a genuinely low-quality thought. The model learns to prefer the former:

\[
(s, \pi, \tau_{\text{good}}, \tau_{\text{bad}}).
\]

The DPO negatives are sampled from thoughts with quality < 0.3 or with explicit negative conductor commentary. This targets specificity and spatial awareness rather than generic fluency.

## 9.4 Training Configuration

LoRA training runs on the RTX 4050 (6 GB VRAM). The configuration is constrained by memory:

| Hyperparameter | Value | Rationale |
|---|---|---|
| Rank \(r\) | 8–16 | Sufficient expressivity without overfitting |
| Batch size | 1–4 | Fits 6 GB VRAM |
| Sequence length | 512–1024 | Covers most thoughts with padding |
| Learning rate | 1e-4–5e-4 | Standard for LoRA on small models |
| Trigger | ~1,000 qualifying thoughts | ~weekly cadence |

Training is triggered automatically when the pool of qualifying thoughts crosses the threshold. The process runs in a background job so it does not block the inference loop.

## 9.5 Evaluation Before Promotion

Before a new adapter is promoted, it is evaluated against the base model on the held-out evaluation set. The evaluation protocol:

1. Generate thoughts from both models for each held-out state;
2. Score each thought with the same quality scorer;
3. Compare average quality vectors;
4. Promote only if the adapted model wins by ≥10% on at least one axis and does not degrade on any other.

If the adapter fails, it is discarded and the base model continues. The previous adapter is retained, so rollback is always possible.

## 9.6 Hot-Swap

The promoted adapter is loaded into the running Ollama instance without restarting the inference loop. The swap is atomic at the start of a new thought batch. If the swap fails, the system falls back to the previous adapter or the base model.

Hot-swap is essential because DCA is continuous. A requirement to restart the thinker would break the stream of consciousness and reset the session context.

## 9.7 Browser-Finisher Distillation

The same distillation pattern extends to the browser tier. The browser finisher (Phi-3-mini or Qwen2.5-1.5B) learns from the divergence between its predictions and the server Granite output. The divergence loss is logged as a `result` bottle and consumed by the Conductor.

The recommended progression is:

1. **Prompt-level learning** first: adjust the browser's priming from divergence patterns.
2. **Weight-level adaptation** only after the prompt-level loop demonstrably converges.

This caution mirrors the broader DCA philosophy: change the fastest, cheapest thing first; escalate to weight changes only when cheaper mechanisms are exhausted.

## 9.8 Summary

Distillation is the slowest and most dangerous loop in DCA. It is gated by strict selection, held-out evaluation, and promotion thresholds to avoid the self-reinforcing trap of training on the system's own preferences. When it works, it compounds the gains from reflexes, policies, and conductor interventions. When it fails, the failure is detected and the adapter is discarded, preserving the integrity of the faster loops.
