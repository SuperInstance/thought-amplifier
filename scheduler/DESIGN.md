# Inference Scheduler — The Production Line

**Status:** Built and tested
**Date:** 2026-08-03
**Location:** `/home/eileen/projects/thought-amplifier/scheduler/`
**Port:** 8771

---

## The Thesis

> *"This turns a person's hardware into a production line that gets better at producing value."*

An RTX 4050 with 6GB VRAM can run one model at a time. Left to itself, that's a liability — every agent that calls Ollama simultaneously crashes the GPU, and the hardware sits idle 90% of the time while agents wait for each other.

The Inference Scheduler transforms that liability into an asset. It serializes requests (so the GPU never crashes), prioritizes them (so urgent work goes first), guarantees fair access (so no agent starves), overflows to cloud when overloaded (so throughput scales), and — critically — *learns which scheduling decisions produce better outcomes over time* (so the hardware literally gets better at producing value).

This is the Logos faculty of the tripartite: the rational principle that governs how scarce compute is allocated.

---

## The Tripartite

The scheduler is three faculties working in concert:

### Logos — The Scheduler (`scheduler.py`)
The rational principle. The priority queue. The rule of law.

Logos says: requests are served in priority order, one at a time, no exceptions. The GPU is a single-lane bridge, and Logos is the toll collector who decides who crosses next. It is perfectly fair and perfectly rigid — it follows the rules without exception, because the alternative (two models on the GPU at once) is a crash.

Priority bands:
- **URGENT** — user-facing, blocking, real-time. The player is waiting.
- **HIGH** — conductor analysis, trust scoring. The system is reflecting.
- **NORMAL** — agent thinking loop. The system is thinking.
- **LOW** — batch embedding, indexing. The system is filing.
- **IDLE** — evolution rollouts, background training. The system is dreaming.

### Pathos — The Quality Signals (`priority_evolver.py`)
The emotional principle. The feedback loop. The capacity to feel whether an outcome was *good*.

Pathos says: not all NORMAL-priority requests produce equal value. Some agents, in some contexts, at some times of day, consistently produce better results. Pathos is the faculty that *feels* this difference and *responds* — nudging the priority of agents whose outcomes are better, gently, slowly (EMA α=0.05), never making extreme changes.

The policy evolves through observed outcomes. Quality × timeliness × efficiency = reward. The reward signal feeds back into priority adjustments. The adjustments change which requests get served first. The new ordering produces new outcomes. The loop never stops.

This is the dynamic ML — not a neural network in sight, just exponential moving averages and a policy table that's smaller than this README. The sophistication is in the feedback loop, not the math.

### Ethos — Fair Use (`fair_use.py`)
The ethical principle. The character of the system. The guarantee.

Ethos says: every agent gets a floor. No agent starves. The pie is divided so that even the LOWEST priority agent gets its minimum share of GPU time over any sliding window. This is not negotiable.

Above the floor, excess capacity is redistributed by value-weight — agents that produce more value per GPU-millisecond get more time. This is the university supercomputer model: every lab gets a guaranteed allocation. Labs that use their allocation productively get more. Nobody is ever fully cut off.

The sliding window (5 minutes by default) means the system forgives past greed and rewards current productivity. An agent that was wasteful 10 minutes ago starts fresh.

---

## The University Supercomputer Metaphor

A university supercomputer serves hundreds of labs with different needs:
- The physics department needs massive parallel jobs (URGENT, lots of GPU)
- The biology lab needs steady moderate jobs (NORMAL, consistent)
- The humanities lab needs small occasional jobs (LOW, but must not starve)
- The CS department trains models overnight (IDLE, opportunistic)

The supercomputer's scheduler guarantees each lab a minimum allocation, lets productive labs borrow excess capacity, and never lets any lab be fully starved. This is not charity — it's the recognition that you don't know in advance which lab will produce the breakthrough.

Our scheduler treats each agent the same way. The thinker, the conductor, the embedder, the evolution engine — they're all labs sharing one machine. The fair-use policy ensures the system as a whole is more productive than any single agent could be alone.

---

## The Jazz Rhythm

Scheduled turns are the beat. Urgent preemptions are syncopation.

In jazz, the rhythm section plays a steady pulse — bass on every beat, drums keeping time. Against that pulse, the soloist plays *around* the beat —提前, behind, syncopating. The tension between the steady pulse and the rhythmic displacement is what makes the music swing.

The scheduler works the same way:
- The **fair-use window** is the measure (5 minutes = one chorus)
- The **priority queue** is the beat (requests served in order)
- **Urgent preemptions** are syncopation (displacing the expected order)
- **Priority evolution** is the groove developing over time (the rhythm section locks in)

A system that only had the beat (static priority, no evolution) would be a metronome — technically correct, musically dead. A system that only had syncopation (purely dynamic, no guarantees) would be chaos — exciting for one bar, exhausting for ten. The scheduler has both: the steady pulse of fair-use guarantees, and the syncopation of learned priority adjustments.

The idle capacity — the spaces between the notes — is where the evolution engine does its work. Rollouts, simulation, background learning. The silence is not empty; it's where the next phrase is being composed.

---

## How Fair Use Evolves to Fit the Application

The system starts with equal floors: every agent gets 2,000ms per 5-minute window. That's the neutral starting position.

Over the first hours of operation:

1. **Quality signals arrive.** Each completed request gets a quality score (did the agent use the result? was the output good?). These feed into the value EMA per agent.

2. **Value-weighted redistribution activates.** Agents with higher value EMAs get a larger share of the excess capacity (the GPU time left over after everyone's floor is met). An agent producing 0.9 quality gets more time than one producing 0.3.

3. **Priority evolution kicks in.** After 10 observations per context bucket, the evolver starts adjusting effective priorities. An agent that consistently produces better results when expedited gets a permanent negative adjustment. One that wastes GPU time gets delayed.

4. **Context buckets emerge.** The system discovers that agent X is more productive in the morning, or when the queue is deep, or under heavy load. These aren't hardcoded patterns — they emerge from the data.

5. **The policy stabilizes.** The EMA smoothing (α=0.05) means the policy changes slowly. After a few days, it reflects the actual usage patterns of *this specific user's specific application on this specific hardware*.

The result: the same hardware serves the same agents more productively in week 2 than week 1. Not because anything was upgraded, but because the scheduler learned how to allocate scarce compute to maximize value.

*That* is a production line that gets better at producing value.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │          API (port 8771)         │
                    │  POST /infer  GET /status/:id    │
                    │  GET /queue   POST /priority/:id │
                    │  GET /stats   POST /quality/:id  │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │       Inference Scheduler        │
                    │       (Priority Queue +          │
                    │        GPU Serialization)        │
                    └──┬────────────┬─────────────┬───┘
                       │            │             │
              ┌────────▼───┐  ┌─────▼─────┐  ┌────▼────────┐
              │  Fair Use  │  │  Cloud    │  │  Priority   │
              │  Tracker   │  │  Bridge   │  │  Evolver    │
              │ (Ethos)    │  │ (Overflow)│  │ (Pathos)    │
              └────────────┘  └───────────┘  └─────────────┘
                     │              │              │
                     │      ┌───────▼───────┐      │
                     │      │  Cloudflare   │      │
                     │      │  Workers AI   │      │
                     │      │  (10K/day)    │      │
                     │      └───────────────┘      │
                     │                              │
                     └──────────┬───────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     Ollama (Local)    │
                    │     RTX 4050 6GB      │
                    │     ONE AT A TIME     │
                    └───────────────────────┘
```

### Data Flow

1. Agent calls `POST /infer` with prompt + priority
2. API applies learned priority adjustment (from evolver)
3. Request enters the priority queue
4. Scheduler worker pops highest-priority request
5. Fair-use check: is this agent over its share?
   - Yes → defer, pick next
   - No → proceed
6. Cloud overflow check: is queue too deep?
   - Yes → route to Cloudflare Workers AI
   - No → call Ollama locally
7. Inference completes → result stored
8. Agent polls `GET /status/:id` or receives callback
9. Agent submits quality feedback via `POST /quality/:id`
10. Evolver records outcome → policy adjusts over time

### Files

| File | Purpose | Lines |
|------|---------|-------|
| `scheduler.py` | Priority queue, GPU serialization, Ollama calls | ~350 |
| `fair_use.py` | Fair-use tracking, value-weighted redistribution | ~250 |
| `cloud_bridge.py` | Cloudflare Workers AI overflow routing | ~200 |
| `priority_evolver.py` | Learning system, policy evolution | ~280 |
| `api.py` | HTTP API server (stdlib only) | ~300 |
| `tests/test_scheduler.py` | 20 tests covering all components | ~450 |

### Dependencies

**Zero external Python packages.** Stdlib only (json, heapq, threading, subprocess, http.server) + curl for HTTP calls.

---

## API Reference

### POST /infer
Submit an inference request.
```json
{
  "prompt": "What is the nature of consciousness?",
  "agent": "thinker",
  "priority": "NORMAL",        // URGENT|HIGH|NORMAL|LOW|IDLE
  "model": "llama3.2:3b",
  "options": {"temperature": 0.7, "num_predict": 256}
}
```
Returns:
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "queued",
  "priority": "NORMAL",
  "base_priority": "NORMAL",
  "position": 3
}
```

### GET /status/:id
Check request status. Returns full result when done.

### GET /queue
Current queue state (running request + queued requests + depth).

### POST /priority/:id
Update priority of a queued request.
```json
{"priority": "URGENT"}
```

### POST /cancel/:id
Cancel a queued request.

### GET /stats
Full system stats: per-agent GPU usage, fair-use shares, cloud neuron consumption, evolver state.

### POST /quality/:id
Submit quality feedback for a completed request. This is the signal that drives policy evolution.
```json
{"quality": 0.85, "timeliness": 0.92}
```

### GET /policy
Export the current evolved scheduling policy.

### GET /health
Health check with uptime and request count.

---

## Operational Notes

### Starting the Scheduler
```bash
cd /home/eileen/projects/thought-amplifier/scheduler
python3 api.py --port 8771 --ollama http://localhost:11434
```

### Agent Integration
Agents currently calling Ollama directly should switch to:
```bash
# Instead of: curl http://localhost:11434/api/generate -d '{"model": "...", "prompt": "..."}'
# Use:
curl http://localhost:8771/infer -d '{"prompt": "...", "agent": "my_agent", "priority": "NORMAL"}'
```

### Cloudflare Workers AI Setup
Set environment variables or pass at construction:
```bash
export CF_ACCOUNT_ID="your_account_id"
export CF_API_TOKEN="your_api_token"
```

The bridge activates automatically when queue depth ≥ 3. It falls back to local when quota is exhausted or cloud errors occur. Cloud is an accelerator, never a dependency.

### What the Scheduler Does NOT Do
- **No streaming.** Requests complete atomically. Streaming would require holding the GPU lock longer, increasing contention.
- **No model hot-swapping.** The scheduler assumes the model is already loaded. Model management is a separate concern.
- **No authentication.** This is a localhost-only service. Don't expose port 8771 to the network.

---

## What's Deliberately Unfinished

Following the Thought Amplifier philosophy ("every model is unfinished, every policy has gaps, every reflex has an escape hatch"):

1. **The evolver starts blind.** No prior knowledge of which agents need which priorities. It learns from zero. This is intentional — hardcoded priors would bias the system toward the designer's assumptions, not the user's actual workload.

2. **Quality scoring is manual (for now).** Agents must POST /quality/:id with their score. Eventually this should be automatic (measuring whether the result was used, how long the agent spent on it, downstream effect). But starting manual means we know exactly what signal we're feeding the evolver.

3. **No model routing yet.** All requests go to the same model (llama3.2:3b by default). The natural next step is routing different request types to different models (embedding vs generation vs chat).

4. **The cloud bridge is conservative.** Overflow threshold of 3 is high — it means three requests must be queued before cloud activates. This prioritizes local GPU usage (free) over cloud (quota-limited). The threshold should be tuned per workload.

5. **No persistence.** If the scheduler restarts, the queue and stats are lost. The evolved policy can be exported/imported via GET /policy and POST /policy, but this must be done manually. Automatic checkpointing is a natural next step.

The gaps are where the growth happens. The scheduler is designed to get better — not to be perfect out of the box.

---

*Built 2026-08-03. The Logos faculty of the tripartite mind. The production line thesis, made executable.*
