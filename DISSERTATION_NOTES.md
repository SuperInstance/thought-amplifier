# Dynamic Cognition Amplification (DCA): Dissertation Notes

Working repository for doctoral dissertation establishing DCA as a new subfield.
Follow the read → note → write → section workflow. Never hold more than 3 documents of insight in working memory.

## Document Takeaways

### REPO_DESIGN.md
- **Substrate independence via hard core/adapter split.** `amplifier/` speaks only `Observation`, `Thought`, `Action`, `Outcome`; game-specific logic is banished to `adapters/`. This separation is the central architectural claim and the precondition for treating DCA as a general subfield rather than a single-game hack.
- **The four-line thesis of continuous cognition.** Training signal = stream of consciousness; loss = play quality (novelty, specificity, engagement, spatial awareness); gradient = prompt/parameter adjustment every 30 s; model update = reflex compilation, policy breeding, trust accrual, and LoRA baking happening in parallel loops.
- **Recurring three-gate cascade.** Every expensive operation is preceded by a free gate and a cheap gate: reflex (<1 ms) → compiled policy (O(1)) → LLM (~500 ms). The same pattern recurs at conducting and acting. A fallback ladder makes ≥50% decisions at $0 a runtime invariant, not a budget aspiration.
- **`.bottle` as the interpretability spine.** Typed envelopes with `caused_by` links turn the loop into a DAG; the append-only ledger makes a stochastic loop deterministic-for-replay. These are the mechanisms that make 100% interpretability and conservation-law enforcement possible.
- **Five subsystems and their actual gaps.** Reflex compiler, evolution engine, trust scoring (the real gap — scoring Conductor interventions, not cascade gates), temporal→vector pipeline, and LoRA distillation. Trust is highest value per line because the Conductor has been modifying prompts/parameters blindly.

### DYNAMIC_COGNITION_ARCHITECTURE.md
- **Three-layer cognitive stack.** The Local Thinker (Granite 3.1 2B, ~1–2 thoughts/s) produces a continuous stream of consciousness; the Conductor (GLM-5.2 / DeepSeek V3, every 30–60 s) performs deep meta-learning; the Game/World provides observations and outcomes. This split is the anatomical basis for DCA.
- **Algorithmic action selection from generative intent.** The LLM emits a 3–8 word "lean" (e.g., `inspect tower_top`); a lightweight, pre-approved policy table converts it to concrete action. This is the structural security property that prevents unconstrained tool execution.
- **Quality as loss function.** Play quality is decomposed into novelty, specificity, emotional engagement, and spatial awareness. The Conductor's objective is qualitative improvement of thoughts, not minimization of a pre-defined numeric loss.
- **T-minus / MIDI temporal encoding.** Game events are canonized into beat-based sequences (`B8:E72:v85 → ...`) and embedded with the same bge-m3 model used for skills, enabling vector search over *rhythms of play*.
- **Novelty claim: always-on directed learning.** Traditional ML is collect → train offline → deploy → repeat. DCA is continuous: the model is always playing, always being directed, and the training signal is the stream of consciousness itself.

### pincher/analysis.md
*Pending read.*

## Dissertation Sections

| # | Section | Status | Source Docs |
|---|---------|--------|-------------|
| 01 | Abstract | pending | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE |
| 02 | Introduction | pending | REPO_DESIGN, DYNAMIC_COGNITION_ARCHITECTURE, pincher/analysis |
| 03 | Literature Review & Related Work | pending | TBD |
| 04 | Foundational Concepts | pending | TBD |
| 05 | Theoretical Framework | pending | TBD |
| 06 | Formal Model | pending | TBD |
| 07 | System Architecture | pending | TBD |
| 08 | Implementation | pending | TBD |
| 09 | Experiments & Evaluation | pending | TBD |
| 10 | Results | pending | TBD |
| 11 | Discussion | pending | TBD |
| 12 | Limitations & Future Work | pending | TBD |
| 13 | Conclusion | pending | TBD |
| 14 | References & Appendices | pending | TBD |

## Section Drafts Log

- *No sections drafted yet.*
