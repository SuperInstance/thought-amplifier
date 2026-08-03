# 8. Temporal Cognition and the Vector Pipeline

Most AI systems treat time as a sequence of discrete states. DCA treats time as a substrate: events are placed on a shared tempo map, rhythms of play are canonized into strings, and those strings are embedded and stored for future recall. This chapter describes the temporal substrate, the MIDI→vector pipeline, and how temporal patterns inform the Conductor's decisions.

## 8.1 The Shared Tempo Map

Every DCA instance maintains a `SharedSessionTempoMap`:

\[
\mathcal{M} = (\text{baseBPM}, \text{swingFactor}, \text{rootMidiNote}, \text{ppq}, \text{currentTick}, \text{fermataActive}, \text{currentChordProgression}, \text{spatialLatticeOrigin}, \text{globalFrictionScore}).
\]

The map is the single source of truth for all temporal coordination. Only the `TempoService` can modify it, enforcing a single-writer pattern that prevents race conditions when tide, storm, and aurora events would otherwise update BPM simultaneously.

The tempo map serves two cognitive functions. First, it synchronizes agents and player so that "in the pocket" is a measurable state. Second, it provides the beat position \(b_t\) attached to every thought, making the thought stream a temporal signal rather than merely a sequence.

## 8.2 MIDI Encoding of Events

Game events are encoded as MIDI-like messages. A build command is not merely `place block at (x,y,z)`; it carries:

- `targetTick`: when the action should occur;
- `agentChannel`: which agent lane performs it;
- `midiVelocity`: weight or intensity (stone = 127, glass = 80);
- `midiInstrument`: sonic identity tied to agent and era;
- `durationTicks`: how long the event persists;
- `chordTone`: harmonic role tied to spatial position.

This encoding captures the *feel* of the action: the moment the hammer falls, the pause before the capstone, the resolution of a completed structure. JSON coordinates describe where; MIDI describes when and how.

## 8.3 Canonicalization

A play session produces a sequence of MIDI events. Before embedding, the sequence is canonized into a deterministic, lossy string. The canonical form is:

\[
B_8{:}E_{72}{:}v_{85} \;\to\; B_{16}{:}I_{67}{:}v_{60} \;\to\; B_4{:}W{:}v_{30},
\]

where:

- \(B\) is the beat number;
- \(E\)/\(I\)/\(W\) are action codes (explore, inspect, wait);
- the subscript after the action code is an encoded parameter (e.g., object id 72);
- \(v\) is a velocity bucket.

The quantization is intentional. Velocities are bucketed, beats are snapped to a fixed grid, and parameters are mapped to a finite vocabulary. The same session always yields the same string, therefore the same vector. This determinism is an explicit acceptance criterion: "same session always produces the same vector."

## 8.4 Embedding and Storage

The canonical string is embedded with bge-m3 via Cloudflare Workers AI or a local sentence-transformers model. The resulting vector is stored in the vector index with metadata:

```python
{
  "session_id": "...",
  "player_id": "...",
  "timestamp": "...",
  "quality_score": 0.82,
  "bond_tier": 3,
  "archetype": "methodical_builder",
  "beat_count": 1248
}
```

The vector index serves two query modes. Similarity search returns past sessions whose rhythms resemble the current session. Clustering discovers play-style archetypes such as "methodical builder," "storm repairer," or "social chatterer."

## 8.5 Temporal Pattern Recall

During its 30-second cycle, the Conductor queries the vector index:

```text
"Has this rhythm worked before?"
```

The query is the canonical string of the last \(m\) beats. The returned patterns are scored by quality and recency. A strong match becomes a Gate-2 check before the Conductor spends a Gate-3 LLM call.

The target is that temporal patterns inform ≥30% of modification decisions. For example, if the current rhythm is "explore-explore-build-pause" and past instances of that rhythm improved after a specificity prompt, the Conductor applies that prompt directly rather than reasoning from scratch.

## 8.6 Play-Style Archetypes

Clustering temporal vectors produces play-style archetypes. Unlike the strategy archetypes from the evolution engine—which classify action-selection policies—these archetypes classify *rhythms of engagement*. Example clusters that emerge from the data might include:

- `methodical_builder`: long build phrases, regular pauses, high spatial awareness;
- `storm_repairer`: bursts of build/inspect actions under Presto tempo;
- `wanderer`: long explore sequences, irregular beats, high novelty;
- `social_player`: frequent speak actions, rubato chat timing, high engagement.

These archetypes feed the Conductor's self-model and the narrative layer. A player whose rhythm matches `methodical_builder` receives more detailed material comments; a `wanderer` receives prompts that nudge toward concrete goals without breaking exploratory flow.

## 8.7 The Temporal→Vector Pipeline as a Three-Gate Cascade

The temporal pipeline itself follows the three-gate pattern:

| Gate | Operation | Latency |
|---|---|---|
| 1 | MIDI encoder produces events from session log | local, <1 ms |
| 2 | Canonizer maps events to deterministic string | local, <1 ms |
| 3 | Embedder produces vector; VectorPort stores it | ~10–50 ms |

The pipeline runs as a post-session batch job and after significant in-session milestones. It is not on the critical path of thought generation; it feeds the Conductor's Gate-2 memory.

## 8.8 Synchronization and Friction

The Free Energy Principle friction score `globalFrictionScore` measures how far players and agents drift from the shared tempo map. An agent that misses its `targetTick` by more than 2 ticks loses productivity and emits a dissonant note. This makes misalignment perceptible to the player and gives the Conductor another quality signal: a rising friction score may prompt a tempo-adaptation intervention.

Client-side prediction with server reconciliation and integer tick math prevent desync. Smooth BPM transitions over 5–10 seconds with hysteresis bands prevent tempo thrashing when storms or auroras change the map.

## 8.9 Acceptance Criteria

The Fable master prompt specifies:

- The session → MIDI → text → embedding → Vectorize pipeline runs end-to-end without manual intervention.
- Temporal similarity search returns relevant patterns in <50 ms.
- Play-style archetypes are discoverable via clustering (≥3 meaningful clusters after 20 sessions).
- The Conductor uses temporal patterns in ≥30% of its modification decisions.
- Embedding consistency: the same session always produces the same vector.

These criteria ensure that temporal cognition is not merely a visualization feature but a functional part of the learning loop.

## 8.10 Summary

Temporal cognition in DCA rests on three commitments: time is a first-class substrate, rhythms are canonized into deterministic strings, and those strings are embedded and queried. The shared tempo map synchronizes agents and player; the MIDI encoding captures feel as well as fact; the vector pipeline turns individual sessions into searchable knowledge. The result is a system that can answer not only "what happened?" but "has this rhythm worked before?"
