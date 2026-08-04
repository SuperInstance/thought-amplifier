# Distillation Loop — The Self-Improvement Engine

## What This Is

The distillation loop is the core of the thought-amplifier system. It implements
the **Pincher pattern at scale**: a large cloud model (GLM via Z.ai, unlimited
tokens) teaches a small local model (Granite 3.1 2B via Ollama, free) how to be
better at real tasks. Over time, the local model needs the cloud less and less.

## The Five Stages

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. TEACHER │ ──> │  2. STUDENT │ ──> │  3. EVAL    │ ──> │  4. DISTILL │ ──> │  5. UPDATE  │
│  GLM-5.2    │     │  Granite 2B │     │  Score Δ    │     │  .nail file │     │  Prompt v   │
│  Z.ai API   │     │  Ollama     │     │  vs base    │     │  Reflex     │     │  Versioned  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **TEACHER** — GLM generates a focused lesson about a domain topic
2. **STUDENT** — Granite applies the lesson to a real task from the codebase
3. **EVALUATE** — Score Granite's output vs its baseline (no teaching) on 4 dimensions
4. **DISTILL** — If teaching helped (positive delta), compile into a `.nail` reflex
5. **UPDATE** — If teaching consistently helps (N consecutive wins), promote to system prompt

## Usage

```bash
# Basic usage
python3 run_distillation.py --domain cognition --iterations 20

# All domains
python3 run_distillation.py --domain all --iterations 10

# Custom promotion threshold
python3 run_distillation.py --domain roblox --iterations 50 --promote-threshold 5

# Dry run (no API calls)
python3 run_distillation.py --domain maritime --iterations 5 --dry-run
```

## Domains

| Domain | Topics | Real Tasks |
|--------|--------|------------|
| `roblox` | Luau optimization, Roblox API patterns, performance | Review actual modules from lucineer-roblox |
| `digital-twin` | Durable Objects, WebSocket, schema versioning | Analyze lucineer-worker source |
| `maritime` | Fish populations, tension physics, economy design | Review FishingSystem/EconomySystem |
| `cognition` | Embeddings, cascade routing, reflex systems | Review batten-spline, NailCompiler, Conductor |

## Key Insight

GLM subagents are on Z.ai Max (unlimited tokens). They can teach forever.
Granite is local (free). Every iteration makes Granite smarter.
Over time, the local model needs the cloud less and less.

**This is the Pincher pattern at scale.**

## Output Structure

```
distillation-output/
├── teacher/          # GLM lesson artifacts (JSON per iteration)
├── student/          # Granite responses (baseline + taught, per iteration)
├── eval/             # Quality scores and deltas
├── reflexes/         # Compiled .nail reflexes
├── prompts/          # Version history of promoted system prompt directives
└── logs/             # Full run logs (JSONL)
```

## API Key Resolution

The runner looks for the Z.ai API key in this order:
1. `GLM_API_KEY` environment variable
2. `ZAI_API_KEY` environment variable
3. OpenClaw's auth store (SQLite)

## Quality Scoring

Responses are scored on 4 dimensions (matching QualityScorer weights):

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Novelty | 30% | Unique bigrams / total bigrams |
| Specificity | 25% | Numbers, technical terms, proper nouns |
| Engagement | 20% | Questions, action verbs, sentence variety |
| Spatial | 25% | Structural references, system relationships |

Positive delta = teaching helped. Only positive-delta lessons get distilled into reflexes.
