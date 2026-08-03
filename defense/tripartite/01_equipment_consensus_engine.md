# Equipment-Consensus-Engine — Tripartite Analysis

## Overview
The Consensus Engine is the **canonical implementation of the Pathos/Logos/Ethos deliberation framework**. It is a TypeScript library that implements multi-round deliberation across three rhetorical perspectives, with weighted voting, cross-examination, and conflict resolution.

## 1. How It Implements the Pathos/Logos/Ethos Split

The architecture is a direct 1:1 mapping of Aristotle's rhetorical triad:

| Agent | Role | Implementation |
|-------|------|----------------|
| **Pathos** | Emotion/intent analyzer | `analyzeFromPathos()` — detects emotional tone, identifies stakeholders, calculates emotional intensity, generates empathy-based arguments |
| **Logos** | Logic/reason analyzer | `analyzeFromLogos()` — detects logical structure (deductive/inductive/abductive/analogical), extracts premises, identifies assumptions, assesses validity |
| **Ethos** | Ethics/truth analyzer | `analyzeFromEthos()` — applies ethical frameworks (utilitarian, deontological, virtue, care), identifies values at stake, assesses alignment |

Each perspective produces a `PerspectiveAnalysis` with verdict, confidence (0-1), arguments, concerns, and suggestions. These are gathered into `DeliberationRound`s with **cross-examinations** — each perspective challenges the others. This is the "coffee house" creative session model: Pathos asks "does this serve emotional needs?", Logos challenges with "what's the logical basis?", Ethos questions "is this ethically justifiable?"

### Key Mechanism: Domain-Weighted Deliberation

The `WeightCalculator` adjusts perspective weights by domain:
- **Technical**: Logos 70%, Ethos 20%, Pathos 10%
- **Emotional**: Pathos 50%, Ethos 30%, Logos 20%
- **Sensitive**: Ethos 45%, Pathos 30%, Logos 25%
- **Balanced**: Equal 33.3% each

This is directly transferable to DCA: different thought types need different agent weightings. Creative ideation = Pathos-heavy. System design = Logos-heavy. Safety/ethics review = Ethos-heavy.

## 2. Hardware-Specific Optimizations (Ethos Patterns)

None directly — this is an application-layer library. However, the *Ethos perspective* within the engine is conceptually what Casey describes: "connected to constants and actual ports in/out of the construct." The Ethos analyzer checks whether decisions align with constants (ethical frameworks, inviolable principles).

## 3. Agent Communication (A2A / .bottle Protocol)

The Consensus Engine uses **cross-examination** as its A2A protocol:
- `CrossExamination` records: challenger, responder, challenge text, response, satisfaction evaluation, confidence impact
- Challenges reduce responder confidence by -0.1 if unsatisfactory
- This is structured adversarial debate — not free-form chat

The **message-in-a-bottle** protocol is the *fleet-level* communication system:
- `message-in-a-bottle/for-fleet/` — tasks, protocols, context broadcast to all agents
- `message-in-a-bottle/from-fleet/` — messages from fleet members
- Branch naming: `{agent-name}/T-{task-id}`
- Commit format: `type(scope): description [T-XXX]`
- **Beachcombing protocol**: agents scan for new forks, open PRs, and external message bottles

This is a **git-native A2A protocol** — communication happens through git operations (commits, PRs, branches) rather than API calls or message queues.

## 4. What DCA Can Adopt

1. **Domain-weighted deliberation**: Map thought types to Pathos/Logos/Ethos weights. A creative thought = Pathos-heavy. A debugging session = Logos-heavy. An ethical consideration = Ethos-heavy.

2. **Cross-examination between agents**: When the Conductor (Pathos) proposes attention shaping, the Local Thinker (Logos) should challenge: "What's the evidence?" The Hardware Layer (Ethos) should ask: "Can this actually run efficiently?"

3. **Conflict resolution strategies**: The engine has 8 resolution strategies — weighted voting, compromise, conditional approval, deliberation extension, reframing, escalation, suspension, perspective dominance. DCA needs all of these for handling disagreements between its three layers.

4. **Audit trail**: Every deliberation is fully logged with timestamps, confidence scores, and round-by-round progression. DCA should maintain this for thought provenance.

5. **Git-native communication**: The .bottle protocol could map to file-based agent communication in DCA — a shared directory where the Conductor, Thinker, and Hardware agents leave structured messages for each other.
