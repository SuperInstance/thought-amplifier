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
*Pending read.*

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
