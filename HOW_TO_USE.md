# How to Use Thought Amplifier

A comprehensive guide to every mode, with real examples and output samples.

---

## Table of Contents

1. [Installation](#installation)
2. [Basic Thinking](#basic-thinking)
3. [The Supervisor](#the-supervisor)
4. [Reporter Mode](#reporter-mode)
5. [Advocate Mode](#advocate-mode)
6. [Mirror Mode](#mirror-mode)
7. [Watcher Mode](#watcher-mode)
8. [Connector Mode](#connector-mode)
9. [Simulator Mode](#simulator-mode)
10. [The Viewer](#the-viewer)
11. [Journal Files](#journal-files)
12. [Backend Configuration](#backend-configuration)
13. [Advanced Usage](#advanced-usage)

---

## Installation

### Prerequisites

- Python 3.10 or later
- `curl` (installed by default on most systems)
- An LLM backend (see below)

### Option A: Ollama (Recommended — Free, Local, Private)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a small model (2B parameters, runs on 4GB RAM)
ollama pull granite3.1-dense:2b

# Verify it's running
curl http://localhost:11434/api/tags
```

### Option B: API Keys (Cloud — No Local Setup)

```bash
# DeepSeek (extremely cheap, works well)
export DEEPSEEK_API_KEY="sk-your-key-here"

# Or Z.AI/GLM (if you have access)
export ZAI_API_KEY="your-key-here"
```

You can also put the keys in `~/.bashrc` — the amplifier will find them there.

### Verify Installation

```bash
cd thought-amplifier
python amplifier.py --help
```

---

## Basic Thinking

The simplest mode: just generate thoughts continuously.

```bash
# Default: a new thought every 5 seconds
python amplifier.py
```

**What happens:** The thinker generates one thought at a time, forever (until Ctrl+C). Each thought is 2-4 sentences, journaled to both JSONL and Markdown.

### With Context

Give the thinker a topic or perspective:

```bash
python amplifier.py --context "You are thinking about the relationship between music and mathematics"
```

The context becomes part of every thought generation. The thinker stays on topic but roams freely within it.

### Adjusting Speed

```bash
# Fast: a thought every 2 seconds
python amplifier.py --interval 2

# Slow and deep: a thought every 30 seconds
python amplifier.py --interval 30 --context "You are contemplating the hard problem of consciousness"
```

### Adjusting Temperature

```bash
# Focused and analytical (lower temperature)
python amplifier.py --temperature 0.5

# Wild and creative (higher temperature)
python amplifier.py --temperature 1.2
```

### Example Output

From `--context "You are exploring the nature of time"`:

> Time might not be a river but a landscape — we don't flow through it, we stand in it and look around. The past isn't behind us; it's the ground we're standing on, visible in every geological layer and cultural artifact. The future isn't ahead; it's the horizon — visible but unreachable, always receding.

---

## The Supervisor

The supervisor is what makes this more than a random thought generator.

```bash
# Run thinker + supervisor together
python amplifier.py --supervise

# Adjust how often the supervisor reviews (default: 30s)
python amplifier.py --supervise --supervisor-interval 15
```

**What happens:** Every 30 seconds (configurable), the supervisor:

1. Reads the last 10 thoughts
2. Scores each on four dimensions:
   - **Novelty** — how different from recent thoughts (word overlap analysis)
   - **Specificity** — how detailed vs generic
   - **Coherence** — basic sentence structure quality
   - **Engagement** — questions, connections, surprises
3. Computes the average quality
4. Decides whether to adjust:
   - Quality declining → rollback to previous prompt
   - Quality very low (<0.35) → switch to a different prompt style
   - Quality mid-range → inject context from best recent thought
   - Quality high (>0.7) → small temperature nudge for more creativity
5. Every 3rd review, uses the LLM itself for smarter analysis

### Prompt Styles

The supervisor cycles through these prompt variations:

| Style | Character |
|-------|-----------|
| analytical | Probes deep structure, finds hidden patterns |
| creative | Metaphors, what-ifs, inventions, perspective shifts |
| philosophical | Questions assumptions about existence, knowledge, value |
| scientific | Hypotheses, observations, connections between phenomena |
| playful | Joy, humor, wordplay, delightful absurdity |
| investigative | Following threads of curiosity, opening new territory |

### Trust System

The supervisor tracks whether its interventions actually help:

- **Quality goes up after a directive:** trust increases (+0.05, up to 0.95)
- **Quality goes down:** trust decreases (-0.2, down to 0.05)
- **3 consecutive decreases:** automatic rollback to previous prompt
- **Minimum 10 observations** before trust starts moving

This prevents the supervisor from thrashing — making changes that look good briefly but actually degrade the stream.

---

## Reporter Mode

Fetch a URL, then generate analytical thoughts about the content.

```bash
python amplifier.py -m reporter --url https://en.wikipedia.org/wiki/Free_energy_principle
```

**What happens:**

1. Fetches the URL content using curl
2. Extracts readable text (removes HTML, scripts, styles)
3. Generates 5 analytical thoughts (configurable with `--num-thoughts`):
   - Key claims or findings
   - Questionable assumptions
   - Connections to broader themes
   - Counterarguments
   - Practical implications
4. Synthesizes everything into one key insight

### Example

```bash
python amplifier.py -m reporter --url https://arxiv.org/abs/2306.06624 --num-thoughts 3
```

Output includes:
- Source content excerpt
- 3 analytical angles
- A synthesis: one crystalline insight from the source

### Use Cases

- **Research a topic quickly:** Point it at Wikipedia, arXiv, or a blog post
- **Summarize a long article:** The multi-angle approach captures more than a flat summary
- **Find what's missing:** The "unanswered questions" angle surfaces gaps

---

## Advocate Mode

Generate the strongest possible counter-arguments against any claim.

```bash
python amplifier.py -m advocate --claim "Free trade always benefits both countries"
```

**What happens:**

1. Generates counter-arguments from multiple angles:
   - **Empirical:** What evidence contradicts this?
   - **Logical:** What fallacies exist in the reasoning?
   - **Practical:** What are the real-world consequences?
   - **Moral:** What ethical concerns does this raise?
   - **Historical:** When has this been tried and what happened?
   - **Systemic:** What does this assume about how the world works?
2. Identifies the meta-pattern: which type of argument is the claim MOST vulnerable to

### Real Example

```bash
python amplifier.py -m advocate --claim "Social media has been net positive for humanity" --num-thoughts 2
```

**Empirical counter-argument:**

> The factual basis for "net positive" collapses under scrutiny of the causal evidence on mental health, especially among adolescents. Longitudinal studies tracking teen depression since 2012 show a stark, time-locked correlation with the rise of algorithmic feeds...

**Vulnerability Analysis:**

> The claim is most vulnerable to the empirical counter-argument, because the observable, measurable harms — teen anxiety, election interference, misinformation amplification — are concrete and repeatedly verified, whereas the "net positive" assertion relies on diffuse benefits like "global connectivity."

### Use Cases

- **Stress-test your beliefs:** Before publishing or presenting, find the weaknesses
- **Debate preparation:** Get the strongest opposing arguments
- **Critical thinking:** The steel-man approach builds the best counter, not a strawman

---

## Mirror Mode

Reflect an idea through multiple creative lenses.

```bash
python amplifier.py -m mirror --theme "The way rivers reshape landscapes over millennia"
```

**What happens:**

The theme gets reflected through 6 creative styles:

| Style | What It Produces |
|-------|-----------------|
| **Metaphor** | An unexpected comparison revealing hidden structure |
| **Story** | A 3-sentence narrative embodying the idea |
| **Poetry** | A 4-6 line poem capturing the essence |
| **Paradox** | The self-contradiction hidden inside the idea |
| **Inversion** | What if the opposite were true? |
| **Scale** | The idea at cosmic or microscopic scale |

After all reflections, a synthesis finds the hidden unity across them.

### Example

```bash
python amplifier.py -m mirror --theme "The mathematics of forest growth"
```

Possible output:

> **Metaphor:** A forest is a slow explosion — the same equations that describe a bomb describe a tree's growth, just with different timescales. The forest doesn't grow; it detonates in geological slow motion.

> **Paradox:** The forest's mathematical precision emerges from total chaos — each tree follows its own random growth pattern, yet the forest achieves near-optimal spacing. Order from disorder, computation from indifference.

### Use Cases

- **Creative writing prompts:** Generate metaphors and imagery for essays, stories
- **Finding new angles:** When you're stuck on how to think about something
- **Presentation material:** Vivid imagery makes ideas memorable

---

## Watcher Mode

Monitor a URL for changes, with automatic diff analysis.

```bash
# Check every 60 seconds, up to 10 times
python amplifier.py -m watcher --url https://news.ycombinator.com --interval 60 --max-checks 10
```

**What happens:**

1. Fetches the URL and stores a baseline snapshot
2. On each check:
   - Fetches again
   - Computes content hash (SHA-256)
   - If changed: generates an LLM analysis of what changed and why it matters
   - If unchanged: logs the check
3. Snapshots are stored in `journals/watcher_snapshots/`

### Example

```bash
python amplifier.py -m watcher --url https://github.com/microsoft/vscode/releases --interval 300 --max-checks 20
```

When a change is detected:

> **🔔 Change detected at check #4**
>
> **Diff:**
> Added (3 lines): "## September 2025 Release", "New feature:...", "Fixed:..."
>
> **Analysis:** VS Code released their September 2025 update. The key addition is multi-cursor improvements and a new TypeScript 5.5 integration. This continues their pattern of monthly releases with incremental language support improvements.

### Use Cases

- **Release monitoring:** Watch for new versions of libraries, tools, products
- **News tracking:** Monitor developing stories
- **Price changes:** Track product pages (though dynamic content may cause false positives)

---

## Connector Mode

Find patterns, contradictions, and hidden connections between multiple sources.

```bash
python amplifier.py -m connector --sources \
    "https://en.wikipedia.org/wiki/Entropy" \
    "https://en.wikipedia.org/wiki/Information_theory" \
    "Entropy and information are deeply related concepts"
```

**What happens:**

1. Fetches and processes each source
2. Performs 5 layers of analysis:
   - **Surface Patterns:** shared vocabulary, recurring themes
   - **Structural Patterns:** parallel arguments, similar reasoning
   - **Hidden Connections:** one source resolves tension in another
   - **Contradictions:** where they conflict
   - **Synthesis:** what emerges from their interaction
3. The synthesis is the key output — insights that belong to none of the sources individually

### Example

```bash
python amplifier.py -m connector --sources \
    "The medium is the message" \
    "Structure and function are inseparable in biology" \
    "The map is not the territory"
```

**Synthesis:**

> All three sources point at the same deep truth: the container shapes the content. A biological structure determines function; a communication medium shapes its message; a map's projection distorts the territory it represents. The meta-pattern is that form and content are never truly separable — every act of representation is also an act of transformation.

### Use Cases

- **Literature review:** Connect papers across different fields
- **Argument synthesis:** Find the unified position across multiple perspectives
- **Creative research:** Discover connections between unrelated domains

---

## Simulator Mode

Run thought experiments: take a premise and trace it to its conclusions.

```bash
python amplifier.py -m simulator --premise "What if humans could photosynthesize?"
```

**What happens:**

The premise gets explored through 6 trajectories:

1. **First-Order:** Immediate direct consequences
2. **Second-Order:** Systemic adaptation, new equilibria
3. **Edge Cases:** Where does it break down?
4. **Historical Parallel:** When was something similar true?
5. **Reductio:** Taken to the logical extreme
6. **Inversion:** What if the opposite were true?

Then a meta-synthesis extracts the core insight.

### Example

```bash
python amplifier.py -m simulator --premise "What if memory were perfect and complete?" --num-thoughts 3
```

**First-Order:**

> Perfect memory would eliminate forgetting as a psychological defense mechanism. Trauma would be permanent — PTSD-like symptoms would become universal rather than exceptional. The judicial system would transform: eyewitness testimony becomes infallible, contracts can be recalled verbatim by all parties. Learning would accelerate dramatically since nothing needs to be re-learned.

**Reductio:**

> If memory were perfect, experience would become a prison — every moment you've ever lived is equally accessible, equally vivid. You couldn't selectively attend to the present because the past would be just as loud. Consciousness requires forgetting; it's the mechanism by which the present feels different from the past. Perfect memory would effectively end the experience of time passing.

### Use Cases

- **Philosophical exploration:** Test ideas rigorously
- **Science fiction worldbuilding:** Develop the implications of a premise
- **Decision making:** Trace the consequences of a choice before making it

---

## The Viewer

Real-time web UI for watching the thought stream.

```bash
# Start thinking with the viewer
python amplifier.py --viewer

# Custom port
python amplifier.py --viewer --port 9000
```

Then open `http://localhost:8770` (or your custom port) in a browser.

### Features

- **Live WebSocket stream:** New thoughts appear instantly with fade-in animation
- **Color-coded entries:** Thoughts (cyan), directives (orange), system events (green), mode outputs (purple)
- **Quality indicators:** Visual dots showing novelty, specificity, coherence, engagement scores
- **Entry counts:** Running totals of thoughts and directives
- **Reconnection:** Automatically reconnects if the connection drops

### Standalone Viewer

If the amplifier is already running and writing to journals, you can start just the viewer:

```bash
python viewer/server.py
```

### API Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/thoughts` | Last 200 thoughts as JSON |
| `GET /api/directives` | Last 50 supervisor directives |
| `GET /api/system` | Last 20 system events |
| `GET /api/state` | Current system snapshot |
| `WS /stream` | Real-time WebSocket stream |

---

## Journal Files

Every session creates two files in `journals/`:

### JSONL (Machine-Readable)

```
journals/session_20260803_181651.jsonl
```

One JSON object per line. Every entry has:

```json
{
    "id": "181651123456",
    "timestamp": "2026-08-03T18:16:51.123456+00:00",
    "type": "thought",
    "content": "The thought text...",
    "metadata": {
        "backend": "deepseek",
        "model": "deepseek-chat",
        "temperature": 0.9,
        "thought_number": 42,
        "quality": 0.73,
        "quality_detail": {
            "novelty": 0.82,
            "specificity": 0.68,
            "coherence": 0.75,
            "engagement": 0.65
        }
    },
    "session": "20260803_181651"
}
```

### Markdown (Human-Readable)

```
journals/session_20260803_181651.md
```

Organized by entry type with timestamps. Easy to read, search, and reference.

### Reading Past Sessions

```python
from core.journal import Journal

# Read from a specific session
entries = Journal.read_all_sessions("journals", limit=500)

# Filter by type
thoughts = [e for e in entries if e["type"] == "thought"]
directives = [e for e in entries if e["type"] == "directive"]
```

---

## Backend Configuration

### Priority Order

The thinker tries backends in this order:

1. **Ollama** (if localhost:11434 responds)
2. **GLM API** (if `ZAI_API_KEY` / `Z_AI_API_KEY` / `ZHIPUAI_API_KEY` is set)
3. **DeepSeek API** (if `DEEPSEEK_API_KEY` is set)

### Finding API Keys

The amplifier checks:
1. Environment variables
2. `~/.bashrc`
3. `~/.profile`
4. `~/.bash_profile`

If you put your key in any of these, it will be found automatically.

### Model Selection

```bash
# Use a different Ollama model
python amplifier.py --ollama-model llama3.2:3b

# Use a different GLM model
python amplifier.py --glm-model glm-4

# Use a different DeepSeek model
python amplifier.py --deepseek-model deepseek-reasoner
```

---

## Advanced Usage

### Run Thinker + Supervisor + Viewer Together

```bash
python amplifier.py \
    --context "You are exploring the deep structure of games and play" \
    --interval 8 \
    --supervise \
    --supervisor-interval 20 \
    --viewer \
    --port 8770
```

This gives you a full system: continuous thinking with quality-adjusted prompts, visible in a web UI.

### Pipe Input

```bash
# Use piped text as the claim for advocate mode
echo "Technology has made us happier" | python amplifier.py -m advocate
```

### Custom Journal Directory

```bash
python amplifier.py --journal-dir /path/to/my/journals --supervise
```

### Running as a Service

```bash
# Simple background with nohup
nohup python amplifier.py --supervise --viewer > amplifier.log 2>&1 &

# Or use systemd
cat > ~/.config/systemd/user/thought-amplifier.service << 'EOF'
[Unit]
Description=Thought Amplifier
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /path/to/amplifier.py --supervise --viewer
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user enable thought-amplifier
systemctl --user start thought-amplifier
```

### Combining Modes

Run multiple modes by running multiple instances:

```bash
# Terminal 1: continuous thinking
python amplifier.py --supervise --viewer

# Terminal 2: research a topic
python amplifier.py -m reporter --url https://article.com

# Terminal 3: monitor a page
python amplifier.py -m watcher --url https://site.com --interval 120
```

All instances write to the same journals directory, and the viewer picks up new entries in real-time.

---

## Troubleshooting

### "No LLM backend available"

- Check if Ollama is running: `curl http://localhost:11434/api/tags`
- Check if API keys are set: `echo $DEEPSEEK_API_KEY`
- The amplifier will show which keys it found in the startup log

### "curl failed" errors

- Make sure `curl` is installed: `which curl`
- For corporate networks, set `HTTPS_PROXY` environment variable

### Viewer not loading

- Check the port isn't already in use: `lsof -i :8770`
- Try a different port: `--port 9000`

### Quality scores seem wrong

- The heuristic scorer is intentionally simple (no LLM needed)
- It measures word overlap, length, sentence structure, and keywords
- For better scoring, run with `--supervise` — the supervisor uses the LLM for quality analysis every 3rd cycle

---

*Thought Amplifier v1.0 — every thought is a training signal, every adjustment is measured, every mind is unfinished.*
