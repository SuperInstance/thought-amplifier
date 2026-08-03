# The Overnight Forge

**One sentence:** This turns a person's hardware into a production line that gets better at producing value.

## What It Is

The GPU doesn't stop when you go home. It keeps working at whatever pace the hardware supports. In the morning, there's a personalized briefing waiting — the correct length for the need-to-knows.

## The Core Architecture

```
┌─────────────────────────────────────────────────────┐
│                  THE FORGE (overnight)                │
│                                                     │
│  RTX 4050 / local GPU running continuously           │
│  Inference scheduler manages priority and fair use   │
│  Cognitive router decides: reflex → local → cloud    │
│  Conductor shapes what gets produced over time       │
│                                                     │
│  While you sleep, it:                                │
│  • Generates research summaries                      │
│  • Builds presentations in various styles            │
│  • Runs experiments and collects data                │
│  • Procedurally develops game worlds                 │
│  • Creates podcast segments from thought streams     │
│  • Iterates on whatever you spec'd before leaving    │
└──────────────┬──────────────────────────────────────┘
               │ morning arrives
               ▼
┌─────────────────────────────────────────────────────┐
│              THE MORNING MEETING                      │
│                                                     │
│  Personalized briefing — correct length, your role    │
│  Interactive: ask follow-up questions to the voices   │
│  Asynchronous: sidebar conversations without wasting  │
│  others' time                                        │
│                                                     │
│  The boss lays out everything, selects who gets       │
│  what in their version. Each team member gets a       │
│  customized briefing for their expertise.             │
└─────────────────────────────────────────────────────┘
```

## Five Products From One Engine

### 1. Morning Meeting Generator
The boss lays out the day's priorities. Each team member gets a customized audio/text briefing for their role and expertise. Sidebar conversations happen asynchronously. No wasted meeting time.

### 2. DM World-Engine
The system world-builds through procedural play overnight. The DM watches or hears summaries, selects what's canon. Many parallel games run to see variations. The DM picks the best path.

### 3. Research Podcast
The internal monologue generates a constant podcast. You nudge scene development by interacting with the voices. Leave them to continue iterating. Nudge with questions to signal your interest level.

### 4. Presentation Builder
Rotate image and sound generation on the GPU to slowly build presentations. Different "feels" for different audiences.

### 5. Async Team Tool
Side-bar conversations on topics the boss planned for one person but not worth taking others' time. Each person fully briefed for their role.

## How It Works With Our Stack

- **Murmur** — communication layer between agents and humans
- **Air** — ambient interface (audio/visual)
- **Spreader-tool** — distribution and fan-out
- **Inference Scheduler** (built, 70 tests) — fair use of the GPU
- **Cognitive Router** (built, 37 tests) — routes by epistemic state
- **Conductor** (validated, p=0.001) — shapes what gets produced
- **.bottle protocol** — message envelopes between components

## Budget Model

The person gives their constant iterator a budget per hour or per job for API tokens to different services. The hardware is a forge — you might as well utilize it because automation is as easy as specs.

## Connection To Existing Work

- activelog.ai = the product site
- The Thought Amplifier = the engine
- The Cognitive Router = the brain
- The Inference Scheduler = the fair-use governor
- The Conductor = the quality shaper
- EXP3 validated: conductor beats random at p=0.001
- Neural reflex: 100% hit rate with proper embeddings
- Replay determinism: 100% at temp=0

The science is real. The hardware is proven. The products are spec'd.
