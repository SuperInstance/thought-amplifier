import requests
import random
import json
import time
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.1-dense:2b"

# Varied scenarios for cognitive diversity
SCENARIOS = [
    "beach at dawn with seagulls",
    "workshop interior with tools scattered",
    "storm on a tropical island",
    "dock construction by the harbor",
    "lighthouse at night with rotating beam",
    "garden in gentle rain",
    "stone quarry with fresh cuts",
    "forest path with dappled sunlight",
    "harbor at dusk with fishing boats",
    "cliff edge overlooking ocean",
    "abandoned mine entrance",
    "river crossing with stepping stones",
    "snowy mountain pass",
    "desert canyon with red walls",
    "underground crystal cave",
    "floating platform above clouds",
    "ruined castle courtyard",
    "tropical jungle with vines",
    "volcanic vent with steam",
    "coral reef underwater",
    "windy hilltop with wildflowers",
    "frozen lake in moonlight",
    "bamboo grove swaying",
    "waterfall in a hidden glen",
    "obsidian shard field",
    "marsh with fireflies at night",
    "rocky tide pool ecosystem",
    "ancient tree with glowing bark",
    "sandstone arch formation",
    "misty meadow at twilight",
]

# Varied player states for diversity
PLAYER_STATES = [
    "you feel energetic and curious",
    "you're tired from a long journey",
    "you just built something and feel proud",
    "you're searching for rare materials",
    "you're lost and trying to find your way",
    "you're planning a big construction project",
    "you just had a surprising encounter",
    "you're relaxing and enjoying the view",
    "you're hungry and looking for food",
    "you're excited about a new discovery",
    "you feel cautious after hearing strange noises",
    "you're collaborating with another player",
    "you're reflecting on your progress so far",
    "you're preparing for an upcoming challenge",
    "you're exploring somewhere nobody has been",
    "you're remembering something from earlier",
    "you feel creative and want to build",
    "you're trying to solve a puzzle",
    "you're gathering resources methodically",
    "you're anxious about a looming threat",
]

thoughts = []
errors = 0

for i in range(100):
    scenario = random.choice(SCENARIOS)
    state = random.choice(PLAYER_STATES)
    
    prompt = f"You are a thoughtful companion exploring a game world. Current setting: {scenario}. {state}. Write a brief 2-sentence inner thought about what you notice and what you want to do next. Be specific and personal."
    
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7 + random.random() * 0.2}
        }, timeout=30)
        resp.raise_for_status()
        thought = resp.json()["response"].strip()
        if thought:
            thoughts.append(thought)
            sys.stderr.write(f".")
        else:
            errors += 1
            sys.stderr.write("x")
    except Exception as e:
        errors += 1
        sys.stderr.write(f"x({e})")
    
    if (i + 1) % 10 == 0:
        sys.stderr.write(f" [{i+1}/100]\n")

with open("/home/eileen/projects/thought-amplifier/experiments/thoughts_cognitive.txt", "w") as f:
    for t in thoughts:
        f.write(t + "\n")

print(f"\nGenerated {len(thoughts)} cognitive thoughts ({errors} errors)")
print(f"Average length: {sum(len(t) for t in thoughts)/len(thoughts):.0f} chars")
