# Product Roadmap: The Overnight Forge

**Mission:** Turn a person's hardware into a production line that gets better at producing value.

## Phase 1: Foundation (BUILT ✅)
- Inference Scheduler (port 8771, 70 tests) ✅
- Cognitive Router (37 tests) ✅  
- Conductor (validated p=0.001) ✅
- RTX 4050 running 4 models ✅
- 4 websites live ✅
- Game processor wired through scheduler (69ms local, $0) ✅

## Phase 2: The Morning Meeting (BUILD NEXT)
The system works overnight. Morning brings a personalized briefing.

**Podcast Engine:**
- Rotate models on GPU: Granite 2B for thoughts, Qwen for summaries, nomic-embed for search
- Generate TTS audio segments (via Cloudflare Workers AI or DeepInfra Qwen-TTS)
- Stitch into a podcast episode personalized per listener
- The listener's role determines what they hear
- Boss lays out priorities, system generates role-specific briefings

**Presentation Builder:**
- GPU generates slides overnight (FLUX for images, Granite for narrative)
- Different "feels": boardroom, creative pitch, technical review, teaching
- Morning: finished presentation waiting

## Phase 3: The DM World-Engine (BUILD AFTER)
Procedural world-building through play.

- Run many parallel game sessions overnight
- DM watches summaries, selects what's canon
- Variations explored automatically
- The forge generates, the DM curates

## Phase 4: Async Team Tool (BUILD AFTER)
Sidebar conversations without wasted meeting time.

- Each person gets a customized version of the briefing
- Role-specific depth (engineer gets technical details, PM gets priorities, designer gets visuals)
- Interactive: ask follow-ups to the generated voices
- Budget per person per day

## Phase 5: Integration with Murmur + Air + Spreader-Tool
- **Murmur:** communication layer between agents and humans
- **Air:** ambient interface (audio/visual presence)
- **Spreader-tool:** distribution and fan-out across team members

## Budget Model
Person gives their forge a token budget per hour or per job.
Hardware is treated like a forge — you might as well utilize it.
"Automation is as easy as specs."
