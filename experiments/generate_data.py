#!/usr/bin/env python3
"""
Generate 100 cognitive thoughts and 100 command phrases for Experiment 1.
Uses Granite 3.1 via Ollama where possible, with template fallback for speed.
"""
import requests
import random
import json
import time
import sys
import os

OLLAMA_URL = "http://localhost:11434"
MODEL = "granite3.1-dense:2b"

# ─── Cognitive Thought Generation ───
# Rich, varied scenario + state combinations produce semantically diverse thoughts
SCENARIOS = [
    "beach at dawn", "workshop interior", "storm on island", "dock construction",
    "lighthouse at night", "garden in rain", "stone quarry", "forest path",
    "harbor at dusk", "cliff edge", "abandoned mine", "river crossing",
    "snowy mountain pass", "desert canyon", "crystal cave", "floating platform",
    "ruined castle", "tropical jungle", "volcanic vent", "coral reef",
    "windy hilltop", "frozen lake", "bamboo grove", "hidden waterfall",
    "obsidian field", "marsh at night", "tide pools", "glowing ancient tree",
    "sandstone arch", "misty meadow",
]

OBSERVATIONS = [
    "the light filtering through creates dancing shadows",
    "materials are scattered across the ground, waiting to be gathered",
    "a strange sound echoes from somewhere nearby",
    "the air feels charged with energy",
    "colors shift and change as you move",
    "structures half-built suggest someone was here before",
    "the terrain changes abruptly ahead",
    "something glints just below the surface",
    "paths branch in multiple directions",
    "the temperature drops noticeably",
    "wildlife skitters at the edge of vision",
    "ancient markings cover the walls",
    "a clearing opens up unexpectedly",
    "water flows from an unseen source",
    "the ground vibrates subtly beneath your feet",
    "mist obscures what lies ahead",
    "fragrant blooms release their scent",
    "sharp edges warn of danger",
    "smooth stones line a pathway",
    "distant lights flicker and fade",
]

INTENTIONS = [
    "I want to explore further and see what's beyond that ridge",
    "maybe I should collect some of these materials before moving on",
    "I need to find shelter before the storm gets worse",
    "this would be a perfect spot to build something",
    "I wonder if I can reach that high point for a better view",
    "let me investigate that sound cautiously",
    "I should mark this location to return later",
    "perhaps there's a connection between these markings",
    "I want to pause here and appreciate this moment",
    "time to chart a course through this new terrain",
    "I feel drawn to investigate the glowing elements",
    "let me see if I can craft something with what I've found",
    "I should check if this area is safe before proceeding",
    "maybe I can find a shortcut through here",
    "I want to document this discovery",
    "I'm curious about what created these formations",
    "I should rest here briefly and plan my next move",
    "let me see if there's anything hidden behind these structures",
    "I want to experiment with the materials in this area",
    "perhaps the answer lies in combining what I've observed",
]

def generate_via_ollama(prompt, timeout=30):
    """Try to generate via ollama, return None on failure."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 60}
        }, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except:
        return None

def generate_cognitive_thoughts(n=100):
    """Generate n varied cognitive thoughts."""
    thoughts = []
    attempts = 0
    
    while len(thoughts) < n and attempts < n * 3:
        scenario = random.choice(SCENARIOS)
        obs = random.choice(OBSERVATIONS)
        intent = random.choice(INTENTIONS)
        
        # Try ollama first
        prompt = f"You are in {scenario}. You notice {obs}. {intent}. Express this as a personal 2-sentence thought."
        result = generate_via_ollama(prompt, timeout=45)
        
        if result and len(result) > 20:
            thoughts.append(result)
            sys.stderr.write(f".")
        else:
            # Fallback: template-based thought with high semantic variety
            templates = [
                f"The {scenario} is striking — {obs}. {intent.capitalize()}.",
                f"Standing here at the {scenario}, I notice {obs}. {intent.capitalize()}.",
                f"Looking around the {scenario}, {obs}. {intent.capitalize()}.",
                f"I pause at this {scenario} where {obs}. {intent.capitalize()}.",
                f"What catches my eye at the {scenario}: {obs}. {intent.capitalize()}.",
            ]
            thought = random.choice(templates)
            thoughts.append(thought)
            sys.stderr.write("t")
        
        attempts += 1
        if (len(thoughts)) % 10 == 0:
            sys.stderr.write(f" [{len(thoughts)}/{n}]\n")
    
    # If we still need more, use pure templates
    while len(thoughts) < n:
        scenario = random.choice(SCENARIOS)
        obs = random.choice(OBSERVATIONS)
        intent = random.choice(INTENTIONS)
        templates = [
            f"The {scenario} is striking — {obs}. {intent.capitalize()}.",
            f"Standing here at the {scenario}, I notice {obs}. {intent.capitalize()}.",
            f"Looking around the {scenario}, {obs}. {intent.capitalize()}.",
            f"I pause at this {scenario} where {obs}. {intent.capitalize()}.",
            f"What catches my eye at the {scenario}: {obs}. {intent.capitalize()}.",
        ]
        thoughts.append(random.choice(templates))
    
    return thoughts[:n]

def generate_command_phrases(n=100):
    """Generate n short command/intent phrases."""
    verbs = ["build", "explore", "inspect", "gather", "craft", "move", "search", "examine",
             "construct", "collect", "navigate", "investigate", "harvest", "place", "remove",
             "dig", "climb", "cross", "follow", "check", "scan", "map", "mark", "repair",
             "clear", "open", "close", "activate", "deactivate", "connect"]
    
    objects = ["tower", "wall", "bridge", "shelter", "path", "dock", "lighthouse",
               "platform", "staircase", "tunnel", "gate", "floor", "roof", "fence",
               "lever", "mechanism", "chest", "door", "window", "sign",
               "garden", "farm", "well", "statue", "torch", "beacon", "anchor",
               "rope", "ladder", "cart"]
    
    directions = ["north", "south", "east", "west", "up", "down", "left", "right",
                  "forward", "back", "around", "across", "through", "over", "under", "past"]
    
    locations = ["beach", "forest", "cave", "mountain", "river", "cliff", "harbor",
                 "ruins", "quarry", "garden", "marsh", "reef", "jungle", "canyon",
                 "grove", "meadow", "ridge", "valley", "plateau", "pass"]
    
    modifiers = ["the broken", "a new", "the ancient", "a small", "the large",
                 "a hidden", "the nearby", "a distant", "the old", "a strange",
                 "the glowing", "a dark", "the bright", "a cold", "the warm"]
    
    commands = []
    patterns = [
        lambda: f"{random.choice(verbs)} {random.choice(objects)}",
        lambda: f"{random.choice(verbs)} {random.choice(modifiers)} {random.choice(objects)}",
        lambda: f"{random.choice(verbs)} {random.choice(directions)}",
        lambda: f"go {random.choice(directions)}",
        lambda: f"{random.choice(verbs)} to {random.choice(locations)}",
        lambda: f"{random.choice(verbs)} {random.choice(objects)} at {random.choice(locations)}",
        lambda: f"check {random.choice(objects)}",
        lambda: f"find {random.choice(modifiers)} {random.choice(objects)}",
        lambda: f"{random.choice(verbs)} {random.choice(locations)} {random.choice(directions)}",
        lambda: f"use {random.choice(objects)} on {random.choice(objects)}",
    ]
    
    seen = set()
    while len(commands) < n:
        cmd = random.choice(patterns)()
        if cmd not in seen:
            seen.add(cmd)
            commands.append(cmd)
    
    return commands

def main():
    os.makedirs("/home/eileen/projects/thought-amplifier/experiments", exist_ok=True)
    
    print("Generating cognitive thoughts...", file=sys.stderr)
    thoughts = generate_cognitive_thoughts(100)
    with open("/home/eileen/projects/thought-amplifier/experiments/thoughts_cognitive.txt", "w") as f:
        for t in thoughts:
            f.write(t + "\n")
    
    print(f"\nGenerating command phrases...", file=sys.stderr)
    commands = generate_command_phrases(100)
    with open("/home/eileen/projects/thought-amplifier/experiments/thoughts_commands.txt", "w") as f:
        for c in commands:
            f.write(c + "\n")
    
    print(f"\nDone: {len(thoughts)} thoughts, {len(commands)} commands")
    
    # Print stats
    thought_lens = [len(t.split()) for t in thoughts]
    cmd_lens = [len(c.split()) for c in commands]
    print(f"Thought word counts: mean={sum(thought_lens)/len(thought_lens):.1f}, min={min(thought_lens)}, max={max(thought_lens)}")
    print(f"Command word counts: mean={sum(cmd_lens)/len(cmd_lens):.1f}, min={min(cmd_lens)}, max={max(cmd_lens)}")

if __name__ == "__main__":
    main()
