# SIGNAL CHAIN + JAZZ METAPHOR: The Complete Framework

**From:** Casey DiGennaro, referencing SuperInstance/signal-chain
**Date:** 2026-08-03

---

## THE DIAL

Every room in the vessel has a dial. The dial goes from **pure code** (left) to **full model** (right). The signal-chain determines where on that spectrum each component sits.

```
← CODE                                              MODEL →
  |────|────|────|────|────|────|────|────|
  0   12.5  25   37.5  50   62.5  75   87.5  100%
  
  Dead    Autopilot   Hermit-Crab    Power-Armor    Full
  Artifact  (hardcode   (loose         (tight          Agent
  (no         + human     harness,       harness,       (model
  model)      controls)   seeded)        variable)      in loop)
```

### The 5 Positions on the Dial

1. **Dead Artifact (0%)** — Pure code. No model. Hard-coded logic. Like a guitar pedal: always does exactly the same thing. Predictable, fast, zero latency, zero surprise.

2. **Autopilot (25%)** — Hard-code with human controls. The artifact runs on its own but the captain can grab the wheel. An agent CAN port in through the NMEA 0183, but that doesn't make the autopilot an agent — it's equipment the agent welds.

3. **Hermit-Crab (50%)** — Loose harness, seeded. The agent lives inside a shell it found. It has some model in the loop but the shell constrains it. Seeded with initial conditions that shape behavior. Like a jazz musician who knows the head arrangement but improvises the solo.

4. **Power-Armor (75%)** — Tight harness, variable. The agent is fully in the loop but wearing a structured suit. The harness provides capabilities the agent couldn't have alone. Variable parameters let the agent tune its own constraints.

5. **Full Agent (100%)** — Model fully in the loop. No harness constraints. Pure improvisation. Like a free jazz soloist — can go anywhere, but risks losing the thread.

## THE JAZZ METAPHOR

### Levels of Musicianship

A jazz musician climbs levels:

1. **Learn the rules** — scales, chords, rhythm. Pure code. Dead artifact. The head arrangement.

2. **Understand how to bend them** — which notes outside the scale work, where to push the time, how to create tension. Autopilot mode — following the rules but with human feel.

3. **Spring from to the proper landing** — after bending, you must LAND. In time. In pitch. In timbre. The return to the head arrangement after the solo. This is the reflex compilation — the cached pattern that brings you home.

4. **Make the moment appear out of nowhere** — the solo that surprises everyone, including the soloist. This is the DCA loop at full power: the Conductor shapes the conditions, the Thinker produces something neither expected, but it's *fully simulated to perfection by the other members of the group.*

### The Rhythm Section (the group)

The other members of the group:
- "only enough to remain in time and harmony" — the Ethos agent maintains the beat (hardware constraints, timing, thermal limits)
- "but be pleasantly surprised themselves" — the Pathos agent and Logos agent hear the soloist's creative line and are genuinely surprised
- "by the edge of the creative line being surfed by the soloist" — the Local Thinker is surfing the edge between pattern and novelty, between the known and the unknown

This is EXACTLY what the DCA loop does:
- The Local Thinker is the soloist, surfing the edge
- The Conductor is the rhythm section, maintaining time and harmony
- The thought stream is the improvised solo
- The reflex cascade is the head arrangement (cached patterns to return to)
- The quality scoring is the audience response (did that solo work?)

## HARNESS CHOICES

### Loose vs Tight
- **Loose harness:** the agent has freedom to explore. High temperature, wide action space, long context. Like a jazz soloist in the first chorus — establishing, exploring, taking risks.
- **Tight harness:** the agent is constrained. Low temperature, narrow action space, short context. Like the rhythm section — must maintain the beat, must stay in the changes.

### Seeded vs Variable
- **Seeded:** initial conditions are set and don't change. The soloist starts from a known head arrangement. The rhythm section plays from a chart. Predictable entry point.
- **Variable:** conditions evolve. The solo modulates. The tempo shifts. The key changes. The Conductor is turning the dial in real-time.

## THE COMPLETE PICTURE

```
                    SIGNAL CHAIN DIAL
                 ← CODE                    MODEL →
                 ┌─────┬─────┬─────┬─────┬─────┐
   VESSEL        │Dead │Auto │Crab│Armor│Full │
   COMPONENT     │Art  │Pilot│     │     │Agent│
                 └─────┴─────┴─────┴─────┴─────┘
                                    
   PATHOS         │     │  ●  │     │     │  ●  │  (designs the dial)
   (Conductor)    │     │     │     │     │     │
                                    
   LOGOS          │  ●  │     │  ●  │     │     │  (builds the nodes)
   (Thinker)      │     │     │     │     │     │
                                    
   ETHOS          │  ●  │  ●  │     │  ●  │     │  (optimizes the chain)
   (Hardware)     │     │     │     │     │     │
```

Each agent operates at different positions on the dial for different tasks. Ethos lives more toward code (it optimizes hardware). Pathos lives more toward model (it shapes attention). Logos spans the middle (it builds both code and models).

The Conductor turns the dial for the Thinker in real-time — loosening when creativity is needed, tightening when precision matters, seeding when stability is required, making variable when novelty is the goal.

## CONNECTION TO SIGNAL-CHAIN REPO

The Rust signal-chain library implements the literal processing pipeline:
- `SignalNode` trait = each stage in the chain
- `SignalChain` = the composition of stages
- `process(sample)` = one tick of the loop

In DCA terms:
- Each SignalNode is a transformation applied to the thought stream
- The chain is the full cognition pipeline (perception → thought → action → feedback)
- The dial determines which nodes are hard-coded (filters, gains) vs model-driven (generative, adaptive)
- The Conductor reconfigures the chain in real-time, like a producer at a mixing board

## THE JAZZ PRINCIPLE FOR DCA

The deepest insight: **the soloist doesn't play alone.** Even in a solo, the rhythm section is there — maintaining time, providing harmony, responding. The soloist SURFS the edge of what the rhythm section provides.

In DCA:
- The Thinker is the soloist — it improvises thoughts
- The reflex cascade is the head arrangement — cached patterns to spring from and return to
- The Conductor is the producer — shaping the mix, turning dials
- The Ethos agent is the rhythm section — maintaining the beat (timing), the changes (hardware constraints), the groove (thermal state)
- The audience response (quality scoring) tells the whole band whether the solo worked

"Make the moment appear out of nowhere but fully simulated to perfection by the other members of the group only enough to remain in time and harmony but be pleasantly surprised themselves by the edge of the creative line being surfed by the soloist."

That's the DCA loop. That's what we're building.
