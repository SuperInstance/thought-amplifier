# 6. Evolution Engine and Compiled Policies

Where the reflex compiler memorizes individual situations, the evolution engine generalizes across them. It treats action selection as a bounded-state game, learns per-context statistics through Monte Carlo simulation, and compiles the result into a zero-dependency lookup table. The engine contains no neural network; its update rule is a simple exponential moving average with a hard exploration-preserving clamp.

## 6.1 From Game Playing to Action Selection

ZeroClaw Arena learns games such as Tic-Tac-Toe and Connect 4 by decomposing board states into local tiles and accumulating win/loss statistics. The same algorithm applies to cognitive action selection if we define the "game" appropriately.

In DCA, the state of the action-selection game is a context tuple

\[
c = (\text{channel}, \text{sender_type}, \text{urgency}, \text{time_window}, \text{prior_context_hash}, \text{bond_tier}, \text{nearby_structures}),
\]

and the legal actions are the leans

\[
\mathcal{A} = \{\text{explore}, \text{approach}, \text{build}, \text{inspect}, \text{wait}, \text{speak}\}.
\]

The outcome is not win/loss but a satisfaction score derived from the quality vector:

\[
s = w_1 q_{\text{novelty}} + w_2 q_{\text{specificity}} + w_3 q_{\text{engagement}} + w_4 q_{\text{spatial}}.
\]

This mapping is the central insight of the ZeroClaw integration plan: the algorithm is domain-independent once the state, action, and outcome functions are supplied.

## 6.2 Tile Decomposition

A context is factored into **tiles**, each accumulating independent statistics. Example tile dimensions include:

- Channel (Discord, Telegram, in-game chat)
- Time window (morning, afternoon, evening, night)
- Bond tier (1–5)
- Urgency (low, medium, high)
- Proximity to structures (none, near foundation, near workshop)

For a given context, multiple tiles may activate. Each tile stores, for every action, the number of times the action was chosen and the sum of satisfaction scores. The effective score for an action in context \(c\) is the weighted combination of scores from all active tiles.

Tile decomposition prevents overfitting to exact contexts. A policy learned for "evening + bond tier 3" can partially inform "evening + bond tier 4" through shared tiles. It also makes the system interpretable: every decision traces to specific tile entries with observed counts and scores.

## 6.3 Monte Carlo Self-Play

During idle heartbeat cycles, the evolution engine runs Monte Carlo rollouts. For each candidate context, it simulates each legal action forward by sampling plausible subsequent contexts and outcomes. The simulation uses a lightweight world model that encodes simple causal rules: building near an unfinished structure tends to increase spatial awareness; speaking repeatedly without player response tends to decrease engagement; and so on.

For each action \(a\) in context \(c\), the rollout estimate is

\[
\hat{s}(c, a) = \frac{1}{N} \sum_{i=1}^{N} s_i,
\]

where \(s_i\) is the outcome of the \(i\)-th simulated trajectory. The estimate is blended with the learned tile score using a confidence weight:

\[
\text{value}(c, a) = \lambda \cdot \text{tile_score}(c, a) + (1 - \lambda) \cdot \hat{s}(c, a),
\]

where \(\lambda = \min(\text{visits}/20, 0.8)\). Early in learning, simulation dominates; later, empirical tile scores dominate.

## 6.4 Evolutionary Score Update

Every evolution cycle, tile scores move toward their empirical mean satisfaction:

\[
\text{score}(c, a) \leftarrow \text{score}(c, a) + 0.05 \left( \bar{s}(c, a) - \text{score}(c, a) \right),
\]

where \(\bar{s}(c, a)\) is the average observed satisfaction for action \(a\) in context \(c\). The update is clamped:

\[
\text{score}(c, a) \in [0.05, 0.95].
\]

The clamp guarantees that no action ever reaches probability 0 or 1. This is not a numerical convenience; it is a philosophical commitment. A policy that assigns probability 1 to an action has stopped learning. The 0.05 floor keeps exploration alive forever.

The 0.05 learning rate is deliberately slow. Cognitive outcomes are noisy; a faster rate would overfit to recent fluctuations. ZeroClaw's experiments validate this choice: the same rate produces robust policies across Tic-Tac-Toe, Connect 4, Go 9×9, and Hold'em.

## 6.5 Softmax Action Selection

During training, actions are selected by softmax over the value estimates with temperature \(T\):

\[
P(a \mid c) = \frac{\exp(\text{value}(c, a) / T)}{\sum_{a'} \exp(\text{value}(c, a') / T)}.
\]

A temperature sweep in ZeroClaw found the optimal range to be \(T \approx 0.15\)–\(0.3\). Lower temperatures exploit; higher temperatures explore. DCA uses \(T = 0.3\) during training and \(T \to 0\) when compiling the policy for deployment.

## 6.6 Policy Compilation

After training, the tile field is compiled into a pure lookup table:

\[
\text{CompiledPolicy}[\kappa(c)] = \arg\max_a \text{score}(c, a),
\]

where \(\kappa(c)\) is a deterministic hash of the context. The compiled artifact is a `dict[str, str]`, typically <50 KB, with zero runtime dependencies. Execution time is ~0.001 ms per decision.

Unknown contexts use Hamming-distance nearest-neighbor fallback: if a context hash differs from a known hash by at most 3 bits and the neighbor's score exceeds a threshold, the neighbor's action is returned. Otherwise, the request escalates to Gate 3 (LLM).

## 6.7 Hierarchical Clustering and Strategy Archetypes

Tile score vectors are clustered hierarchically into approximately 8 strategy archetypes. These archetypes are discovered, not designed. Examples that emerge from the data might include:

- `morning_builder`: high build weight, low speak weight, high specificity;
- `evening_explorer`: high explore weight, high engagement, low urgency;
- `storm_repairer`: high build/inspect weight, high tempo (Presto);
- `quiet_observer`: high wait weight, high spatial awareness.

The archetypes serve two purposes. First, they compress the policy: a hierarchical field with 8 clusters achieves ~10× compression with <5 percentage points of performance loss, matching ZeroClaw's result. Second, they feed the conductor's self-model: an intervention that helps `morning_builder` contexts may harm `evening_explorer` contexts.

## 6.8 Integration with the Three-Gate Cascade

The compiled policy is Gate 2 of the thinking cascade. Its relationship to Gate 1 (reflex) is hierarchical:

- Gate 1 matches a specific situation signature.
- Gate 2 matches a context archetype or tile hash.
- Gate 3 handles genuine novelty.

A reflex can be viewed as a highly specialized policy entry that has accumulated enough evidence to bypass the policy table entirely. Over time, successful policy entries may be promoted into reflexes, and failed reflexes may be demoted back to the policy table.

## 6.9 Acceptance Criteria

The Fable master prompt specifies:

- Policy converges within 2 weeks of training (score variance < 0.01 over 24 h).
- Evolved policy outperforms static weights by ≥15% on quality metrics.
- Compiled policy is a self-contained Python dict (<50 KB).
- Every decision is traceable to a specific tile entry (100% interpretability).
- Hierarchical clustering produces human-recognizable strategy archetypes.

The ZeroClaw integration plan adds operational targets: >70% fast-path hit rate, >80% positive satisfaction, and >50% LLM cost reduction on action selection.

## 6.10 Summary

The evolution engine is DCA's mechanism for learning *above* the weights. It uses tile decomposition, Monte Carlo simulation, EMA updates with a hard clamp, and policy compilation to produce millions of free, interpretable decisions. The guarantee of permanent exploration—the \([0.05, 0.95]\) clamp—ensures that the system never collapses onto a local optimum and never stops looking for better actions.
