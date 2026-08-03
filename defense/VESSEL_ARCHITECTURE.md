# VESSEL ARCHITECTURE: The Complete Model

**Author:** Casey DiGennaro
**Recorded by:** Lucineer
**Date:** 2026-08-03

---

## THE CAPTAIN
The user. The human. Always present on the bridge for small vessels. On enterprise vessels, may be distant — but the ship still sails in their name.

## THE TRIPARTITE

### PATHOS (the Shipwright / Cocaptain)
- **Role at design time:** The shipwright. Designs the vessel. Writes the repo architecture. Builds the digital twin that other agents use as their reality construct.
- **Role at runtime:** The cocaptain. User-centric, intention-driven. Converts what it gets from the captain into useful A2A signals for other agents. Learns the shape of their human through the feel of response.
- **Git persistence:** The git-agent IS Pathos. Even when the runtime is agent-free (unmanned), the git-agent persists in the repo. Any external system (Claude Code, Codex, etc.) doing maintenance finds Pathos as the local expert — the architect of the engine.
- **Modes:**
  - **Full agent** — model in the loop, actively shaping
  - **Power-armor / hermit-crab** — agent in a harness, semi-autonomous
  - **Autopilot** — hard-code artifact with agent and human controls. Agent can port in through the NMEA 0183 (the protocol), but the autopilot is equipment, not the agent. The agent welds the equipment.
  - **Dead artifact** — no model in the loop. Pure code. But the git-agent Pathos still lives in the repo as the architect.

### LOGOS (the Builder / Repo Agent)
- **Role:** Application-centric. Cares about specs and logic. Builds the functional architecture.
- **At design time:** Works WITH Pathos to turn design into code. Maintains the digital twin.
- **At runtime:** On large vessels, Logos is at its station managing the application logic. On small vessels, only Pathos is onboard.

### ETHOS (the Fabricator / Hardware Agent)
- **Role:** Connected to constants and actual ports in/out. Tuned to hardware/instance specs as first-class citizen.
- **At design time:** Fabricates with Pathos. Takes the functional design and customizes it for the hardware.
- **At runtime:** The engineer who figures out how to take what Pathos understood and what Logos built, and make it work on THIS hardware.
- **Self-competing:** Tries different coding methods, languages, philosophies to build the low level many ways. Competes with itself to improve performance and find limits.
- **Novel capacity:** Inspired to find capabilities nobody asked for. The 50 TOPS NPU sitting unused. The AVX-512 instructions. The FP8 tensor cores.

## THE COFFEE HOUSE
The three agents work together like a coffee house group:
- They bullshit and share art
- They discuss ideas about their projects
- They know that another perspective from an agent knee-deep in something else might cut through their own baggage
- Pathos brings the human feel, Logos brings the logic, Ethos brings the physical reality
- The cross-pollination finds insights none would reach alone

## VESSEL CLASSIFICATIONS

### Small Vessels (edge devices, single-purpose tools)
- Only Pathos onboard during runtime
- Git-agent Pathos persists in repo as architect
- May be agent-free (dead artifact) — pure code, no model in loop
- Autopilot mode — hard-code with human controls, agent can port in

### Medium Vessels (game servers, application servers)
- Pathos + Logos on the bridge
- Pathos handles user interaction
- Logos manages application state and digital twin
- Ethos consulted during deployment, runs in background

### Large Enterprise Vessels (like USS Enterprise D)
- All three agents at separate stations
- Specialist agents throughout — each with their own lifecycle stage:
  - **Young iterators:** fast, unhindered by context of time, highly reactive
  - **Wise elders:** slower with bloat of memories at various temperatures, but understand through experience, can teach what matters most
- Multiple rooms and stations for different functions
- Agents at all states of their lifecycle, from bright young to wise old

## THE NMEA 0183 PRINCIPLE
The autopilot has an artifact in it. Just because an agent can port in through the protocol doesn't make the autopilot an agent — it makes the autopilot equipment that the agent welds. The vessel IS equipment. The agents ride it.

## THE LIFECYCLE (guano decay mapping)
- **Hot (fresh):** young iterators — fast, reactive, low memory overhead
- **Warm (24h):** active agents with recent context — balanced speed and wisdom
- **Composting (7d):** cooling into patterns — less reactive but more reliable
- **Soil (4wk):** distilled wisdom — slow to access but deeply grounded
- **Substrate (6mo):** geological baseline — the oldest, wisest, slowest layer
- **Geological:** bedrock — permanent knowledge that shapes everything above it

## IMPLICATIONS FOR DCA

1. **The Local Thinker isn't just a model** — it's a vessel designed by Pathos, built with Logos, optimized by Ethos
2. **The Conductor IS Pathos** — it designed the thought stream architecture and shapes it at runtime
3. **The git-agent in slackwater-cognition IS Pathos** — it persists as architect even when no model runs
4. **The RTX 4050 IS Ethos's body** — not just hardware, but the agent's physical form
5. **Multiple models at different lifecycle stages** — Granite 2B (wise elder, slow but deep) + Qwen 0.5B (young iterator, fast but shallow)
6. **The coffee house model** = the multi-model defense panel = the creative session where cross-pollination happens
