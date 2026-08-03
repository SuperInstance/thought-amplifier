# Thought Amplifier

**A continuous thought-generation engine with a supervisor that shapes what thoughts look like.**

A small model thinks continuously. A supervisor agent watches the stream and adjusts the conditions — prompt, temperature, context, interval — to improve thought quality. Six specialized modes extend the stream into research, debate, creativity, monitoring, synthesis, and experimentation.

## Why It's Novel

Most AI tools are **reactive** — you ask, they answer. Thought Amplifier is **proactive** — it thinks before you ask, and keeps thinking. The supervisor creates a feedback loop that is absent from chat interfaces:

1. **Training signal** = the stream of consciousness (every thought is an example)
2. **Loss function** = play quality (novelty, specificity, engagement, coherence)
3. **Gradient** = prompt and parameter adjustment, applied every 30 seconds
4. **Model update** = continuous — the prompt evolves, the temperature shifts

This is not an agent framework (no tool-calling loops). Not a RAG system (not retrieval-for-context). Not a fine-tuned model. It's a **thinking loop** — a substrate-independent dynamic cognition engine that measures what makes thoughts good and adjusts the conditions to produce better ones.

## Quick Start

```bash
# Install Ollama with a small model (preferred)
ollama pull granite3.1-dense:2b

# Or use API keys (works without Ollama)
export DEEPSEEK_API_KEY="your-key"
# export ZAI_API_KEY="your-glm-key"   # optional GLM fallback

# Just think
python amplifier.py

# Think with context
python amplifier.py --context "You are exploring the nature of consciousness"

# Think with supervisor (adjusts prompts based on quality)
python amplifier.py --supervise

# Think with live web viewer
python amplifier.py --viewer
# Then open http://localhost:8770
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
├── viewer/
│   ├── server.py         # WebSocket viewer (pure stdlib)
│   └── index.html        # Real-time stream UI
├── journals/             # Session logs (JSONL + Markdown)
└── REPO_DESIGN.md        # Full architecture spec
```

## How It Works

### The Thinker

Generates thoughts at a configurable interval using the best available backend:
1. **Ollama** (localhost:11434) — preferred, free, local, private
2. **GLM API** (Z.AI) — fast cloud fallback
3. **DeepSeek API** — cheap cloud fallback

Every thought is journaled with metadata: backend, model, temperature, prompt version.

### The Supervisor

Every 30 seconds, the supervisor:
1. Reads the last 10 thoughts
2. Scores them on novelty, specificity, coherence, engagement
3. Decides if conditions should change (prompt style, temperature, context)
4. Applies the directive and journals it
5. Tracks trust: does changing things actually help?

Trust model (asymmetric, from the deep dives):
- +0.5 per quality improvement (minimum 10 observations)
- -2.0 per quality decrease
- 3 consecutive decreases → automatic rollback

### The Modes

Each mode is a specialized thought pattern that uses the LLM in a different way. They're not part of the continuous loop — they're on-demand tools that produce structured multi-output analyses.

## Requirements

- Python 3.10+
- `curl` (for HTTP — Cloudflare blocks Python HTTP libraries)
- Ollama (optional but recommended) OR an API key

No Python packages required — the system runs entirely on stdlib.

## Design Heritage

Derived from `slackwater-cognition` (11,533 lines, 106 tests) and the architecture spec in `REPO_DESIGN.md`, which synthesizes research from:
- **Pincher** — vector DB as runtime, LLM as compiler
- **ZeroClaw Arena** — empirical policy evolution, no neural nets
- **Lever Runner** — three-gate cascade (reflex → cache → LLM)
- **SuperInstance** — typed message envelopes, conservation laws

The Thought Amplifier is the practical extraction: what if the core insight (continuous thinking + measured adjustment) were a standalone tool anyone could run?

## License

MIT
