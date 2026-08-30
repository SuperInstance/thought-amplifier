# Thought Amplifier

<img src="assets/images/gallery-thought-amplifier.jpg" alt="A machine that dreams continuously: a brass thought-stream ticker spilling endless amber paper tape in a dark engine room, an unseen supervisor's hand adjusting the tuning dial." width="720">

**A continuous thought-generation engine with a supervisor that shapes what thoughts look like.**

A small model thinks continuously. A supervisor watches the stream and adjusts the conditions — prompt, temperature, context, interval — to improve thought quality. Six specialized modes extend the stream into research, debate, creativity, monitoring, synthesis, and experimentation.

## What's Verified

- **551 tests, all passing** (`tests/`: 444 · `router/tests/`: 37 · `scheduler/tests/`: 70), run on Python 3.10–3.12 in CI.
- **Quickstart below was tested in a fresh venv with zero pip installs** — the runtime is pure Python 3.10+ stdlib (HTTP goes through `curl`); thoughts generated against local Ollama.
- No frameworks, no agent loops, no vector DB required to run the core loop.

## Why It's Novel

Most AI tools are **reactive** — you ask, they answer. Thought Amplifier is **proactive** — it thinks before you ask, and keeps thinking. The supervisor creates a feedback loop that is absent from chat interfaces:

1. **Training signal** = the stream of consciousness (every thought is an example)
2. **Loss function** = play quality (novelty, specificity, engagement, coherence)
3. **Gradient** = prompt and parameter adjustment, applied every 30 seconds
4. **Model update** = continuous — the prompt evolves, the temperature shifts

This is not an agent framework (no tool-calling loops). Not a RAG system (not retrieval-for-context). Not a fine-tuned model. It's a **thinking loop** — a substrate-independent dynamic cognition engine that measures what makes thoughts good and adjusts the conditions to produce better ones.

## Quick Start

Verified in a fresh venv with no packages installed.

```bash
# Install Ollama with a small model (preferred)
ollama pull granite3.1-dense:2b

# Or use API keys (works without Ollama)
export DEEPSEEK_API_KEY="your-key"
# export ZAI_API_KEY="your-glm-key"   # optional GLM fallback

# Sanity check
python amplifier.py --help

# Just think (Ctrl+C to stop)
python amplifier.py
```

One honest expectation: **the think loop writes to the journal, not the terminal.** After startup you'll see the banner and backend line; thoughts accumulate in `journals/session_*.jsonl` (machine) and `.md` (human). Watch them live:

```bash
# In another terminal while it thinks
tail -f journals/session_*.md

# Or run the built-in live viewer, then open http://localhost:8770
python amplifier.py --viewer

# Think with a context
python amplifier.py --context "You are exploring the nature of consciousness"

# Think with the supervisor adjusting conditions (recommended)
python amplifier.py --supervise
```

## Modes

| Mode | What It Does | Example |
|------|-------------|---------|
| **think** (default) | Continuous thought generation | `python amplifier.py` |
| **reporter** | Fetch a URL, generate research thoughts | `python amplifier.py -m reporter --url https://article.com` |
| **advocate** | Steel-man counter-arguments | `python amplifier.py -m advocate --claim "Markets are always efficient"` |
| **mirror** | Creative reflections (metaphor, poetry, paradox) | `python amplifier.py -m mirror --theme "The mathematics of forest growth"` |
| **watcher** | Monitor a URL for changes | `python amplifier.py -m watcher --url https://site.com --interval 60` |
| **connector** | Find patterns across sources | `python amplifier.py -m connector --sources url1 url2 "some text"` |
| **simulator** | Thought experiments | `python amplifier.py -m simulator --premise "What if dreams are practice runs?"` |

Modes are single-shot: one run produces a bounded batch of journal entries and returns. They are not part of the continuous loop.

## Architecture

```
thought-amplifier/
├── amplifier.py          # Main entry point (--mode, --context, --interval, --port)
├── core/
│   ├── thinker.py        # Continuous thought loop (Ollama → GLM → DeepSeek)
│   ├── supervisor.py     # Quality assessment + prompt/param adjustment
│   └── journal.py        # JSONL + Markdown dual-format journal
├── modes/
│   ├── reporter.py       # URL research
│   ├── advocate.py       # Devil's advocate
│   ├── mirror.py         # Creative reflection
│   ├── watcher.py        # URL change monitoring
│   ├── connector.py      # Multi-document synthesis
│   └── simulator.py      # Thought experiments
├── router/               # Cognitive router: known/unknown triage, confidence,
│                         #   boundary tracking, cloud escalation (own test suite)
├── scheduler/            # Fair-use cloud budgeting + priority queue (own test suite)
├── viewer/
│   ├── server.py         # WebSocket viewer (pure stdlib)
│   └── index.html        # Real-time stream UI
├── journals/             # Session logs (JSONL + Markdown, gitignored)
└── REPO_DESIGN.md        # Full architecture spec
```

## How It Works

### The Thinker

Generates thoughts at a configurable interval (default 5s) using the best available backend:
1. **Ollama** (localhost:11434) — preferred, free, local, private
2. **GLM API** (Z.AI) — fast cloud fallback
3. **DeepSeek API** — cheap cloud fallback

One sweep per tick: if every backend fails, the failure is journalled and the next tick tries again. Every thought is journaled with metadata: backend, model, temperature, prompt version.

### The Supervisor

Every 30 seconds (configurable), the supervisor:
1. Reads the last 10 thoughts (needs at least 3 before it acts)
2. Scores them on novelty, specificity, coherence, engagement
3. Decides if conditions should change (prompt style, temperature, context)
4. Applies the directive and journals it

Trust model, as implemented (asymmetric — a bad change costs more than a good change earns):
- Trust starts at 0.5, bounded [0.05, 0.95]
- +0.05 per quality improvement, −0.20 per quality decline
- 3 consecutive declines → automatic rollback to the previous prompt

### The Modes

Each mode is a specialized thought pattern that uses the LLM in a different way. They're on-demand tools, not part of the continuous loop. See each module's docstring for exactly which angles/layers/trajectories it runs.

## Requirements

- Python 3.10+
- `curl` (for HTTP — Cloudflare blocks Python HTTP libraries)
- Ollama (optional but recommended) OR an API key

No Python packages required — the runtime is stdlib-only (verified). `pip install -e ".[dev]"` gives you pytest if you want to run the suite.

## Depth

- **[REPO_DESIGN.md](REPO_DESIGN.md)** — the full architecture spec
- **[DISSERTATION.md](DISSERTATION.md)** / **[DISSERTATION_NOTES.md](DISSERTATION_NOTES.md)** — the research grounding
- **[ADVISORY_BRIDGE.md](ADVISORY_BRIDGE.md)** — theory-to-practice mapping
- **[HOW_TO_USE.md](HOW_TO_USE.md)** — command cookbook for every mode
- **[DISTILLATION.md](DISTILLATION.md)** — the distillation loop (first gateway consumer)

## Design Heritage

Derived from `slackwater-cognition` (11,533 lines, 106 tests) and the architecture spec in `REPO_DESIGN.md`, which synthesizes research from:
- **Pincher** — vector DB as runtime, LLM as compiler
- **ZeroClaw Arena** — empirical policy evolution, no neural nets
- **Lever Runner** — three-gate cascade (reflex → cache → LLM)
- **SuperInstance** — typed message envelopes, conservation laws

The Thought Amplifier is the practical extraction: what if the core insight (continuous thinking + measured adjustment) were a standalone tool anyone could run?

## License

MIT
