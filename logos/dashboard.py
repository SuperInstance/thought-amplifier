#!/usr/bin/env python3
"""
dashboard.py — Monitoring dashboard for the Thought Amplifier system.

Displays live status of all four subsystems:
  1. Processor — inference jobs completed, success/error rates
  2. Scheduler — queue depth, priority distribution, throughput
  3. Ollama — GPU status, loaded model, VRAM utilization
  4. Tripartite Fleet — Logos (scheduler), Pathos (evolver), Ethos (fair use)

Usage:
    python3 dashboard.py              # one-shot snapshot
    python3 dashboard.py --watch 5    # refresh every 5 seconds (default)
    python3 dashboard.py --watch 2    # refresh every 2 seconds
    python3 dashboard.py --json       # output as JSON

Data sources (all local, no external deps):
    - Scheduler API  (port 8771): /health, /stats, /queue
    - Ollama API     (port 11434): /api/tags, /api/ps
    - Journal files  (journals/): thought/directive entries
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────

SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://localhost:8771")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
REPO_ROOT = Path(__file__).resolve().parent.parent

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"
HR = "─" * 60


# ─── HTTP via curl ───────────────────────────────────────────────

def _curl_get(url: str, timeout: int = 5) -> dict:
    cmd = [
        "curl", "-s", "--connect-timeout", str(timeout),
        "--max-time", str(timeout + 2), url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return {}


# ─── 1. Processor Jobs ───────────────────────────────────────────

def get_job_stats() -> dict:
    """Fetch job completion stats from the scheduler API and journal."""
    scheduler_stats = _curl_get(f"{SCHEDULER_URL}/stats", timeout=5)
    agents = scheduler_stats.get("agents", {})

    total_completed = 0
    total_errors = 0
    total_submitted = 0
    per_agent = {}

    for agent_name, agent_data in agents.items():
        completed = agent_data.get("requests_completed", 0)
        errors = agent_data.get("requests_errors", 0)
        submitted = completed + errors
        total_completed += completed
        total_errors += errors
        total_submitted += submitted
        per_agent[agent_name] = {
            "completed": completed,
            "errors": errors,
            "total_gpu_ms": round(agent_data.get("total_gpu_ms", 0), 1),
            "avg_value": round(agent_data.get("avg_value", 0), 3),
        }

    # Read journal for thought count (persistent record)
    thought_count = _count_journal_thoughts()

    return {
        "jobs_completed": total_completed,
        "jobs_errored": total_errors,
        "jobs_total": total_submitted,
        "thoughts_journaled": thought_count,
        "per_agent": per_agent,
    }


def _count_journal_thoughts() -> int:
    journal_dir = REPO_ROOT / "journals"
    if not journal_dir.exists():
        return 0
    count = 0
    for f in sorted(journal_dir.glob("session_*.jsonl")):
        try:
            # Count lines via wc for speed on large files
            result = subprocess.run(
                ["wc", "-l", str(f)],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                count += int(result.stdout.split()[0])
        except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
            pass
    return count


# ─── 2. Scheduler Queue ─────────────────────────────────────────

def get_queue_depth() -> dict:
    """Fetch queue state from the scheduler."""
    queue = _curl_get(f"{SCHEDULER_URL}/queue", timeout=5)
    health = _curl_get(f"{SCHEDULER_URL}/health", timeout=3)

    current = queue.get("current")
    queued = queue.get("queued", [])
    depth = queue.get("queue_depth", 0)

    priority_counts = {}
    for item in queued:
        pri = item.get("priority", "?")
        priority_counts[pri] = priority_counts.get(pri, 0) + 1

    running_info = None
    if current:
        running_info = {
            "id": current.get("id", "")[:8],
            "agent": current.get("agent", "?"),
            "priority": current.get("priority", "?"),
            "running_ms": round(current.get("running_ms", 0) / 1000, 1),
        }

    return {
        "depth": depth,
        "running": running_info,
        "queued_breakdown": priority_counts,
        "scheduler_uptime_s": health.get("uptime_s", 0),
        "requests_handled": health.get("requests_handled", 0),
    }


# ─── 3. Ollama Status ───────────────────────────────────────────

def get_ollama_status() -> dict:
    """Check Ollama health and get model info."""
    status = {
        "online": False,
        "model": "?",
        "vram_mb": 0,
        "gpu_layers": "?",
    }

    # Basic health check
    tags = _curl_get(f"{OLLAMA_URL}/api/tags", timeout=5)
    if not tags or "models" not in tags:
        return status

    status["online"] = True
    models = tags.get("models", [])

    # Get loaded model info
    ps = _curl_get(f"{OLLAMA_URL}/api/ps", timeout=3)
    if ps and "models" in ps:
        for m in ps["models"]:
            status["model"] = m.get("name", status["model"])
            status["vram_mb"] = m.get("size_vram", 0) // (1024 * 1024)
            details = m.get("details", {})
            status["gpu_layers"] = details.get("family", "?")

            # GPU utilization
            gpu_info = []
            for gpu in m.get("gpu", []):
                gpu_info.append({
                    "name": gpu.get("name", "?"),
                    "util": gpu.get("gpu_utilization", 0),
                })
            status["gpu"] = gpu_info

    # Fallback: get first available model from tags
    if status["model"] == "?" and models:
        status["model"] = models[0].get("name", "?")

    # Available (not loaded) models
    status["available_models"] = [m.get("name", "?") for m in models[:10]]

    return status


# ─── 4. Tripartite Fleet ────────────────────────────────────────

def get_fleet_status() -> dict:
    """Assemble tripartite fleet status from scheduler components."""
    stats = _curl_get(f"{SCHEDULER_URL}/stats", timeout=5)

    # Logos = Scheduler core
    scheduler_health = _curl_get(f"{SCHEDULER_URL}/health", timeout=3)
    logos = {
        "status": "online" if scheduler_health.get("ok") else "offline",
        "uptime_s": scheduler_health.get("uptime_s", 0),
        "requests_handled": scheduler_health.get("requests_handled", 0),
    }

    # Pathos = Priority Evolver (learning system)
    evolver = stats.get("evolver", {})
    pathos = {
        "status": "learning" if evolver.get("policy_size", 0) > 0 else "dormant",
        "total_outcomes": evolver.get("total_outcomes", 0),
        "evolution_count": evolver.get("evolution_count", 0),
        "policy_size": evolver.get("policy_size", 0),
        "last_evolution_s": evolver.get("last_evolution_ago_s", 0),
        "agent_quality": evolver.get("agent_quality", {}),
    }

    # Ethos = Fair Use + Cloud Bridge
    fair_use = stats.get("fair_use", {})
    cloud = stats.get("cloud", {})
    agent_count = len(fair_use)

    total_floor = sum(
        a.get("floor_ms", 0) for a in fair_use.values()
        if a.get("registered")
    )

    ethos = {
        "status": "enforcing" if agent_count > 0 else "idle",
        "agents_registered": agent_count,
        "total_floor_ms": round(total_floor, 0),
        "cloud_configured": cloud.get("configured", False),
        "cloud_requests": cloud.get("cloud_requests", 0),
        "cloud_successes": cloud.get("cloud_successes", 0),
        "cloud_failures": cloud.get("cloud_failures", 0),
        "neurons_remaining": cloud.get("neurons_remaining", 0),
        "neurons_daily_limit": cloud.get("neurons_daily_limit", 0),
    }

    # Aggregate fleet health
    all_online = (
        logos["status"] == "online"
        and ethos["agents_registered"] >= 0
    )
    fleet_health = "healthy" if all_online else "degraded"

    return {
        "health": fleet_health,
        "logos": logos,
        "pathos": pathos,
        "ethos": ethos,
    }


# ─── Rendering ───────────────────────────────────────────────────

def color_bool(value, true_text="yes", false_text="no"):
    if value:
        return f"{GREEN}{true_text}{RESET}"
    return f"{RED}{false_text}{RESET}"


def bar(value, max_val, width=20, fill="█"):
    if max_val <= 0:
        return " " * width
    ratio = min(1.0, value / max_val)
    filled = int(ratio * width)
    if ratio > 0.8:
        color = RED
    elif ratio > 0.5:
        color = YELLOW
    else:
        color = GREEN
    return f"{color}{fill * filled}{RESET}{DIM}{'░' * (width - filled)}{RESET}"


def fmt_s(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m {seconds % 60:.0f}s"
    return f"{seconds / 3600:.0f}h {(seconds % 3600) / 60:.0f}m"


def render(jobs: dict, queue: dict, ollama: dict, fleet: dict) -> str:
    lines = []

    # ── Header ──
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"{BOLD}╔{'═' * 58}╗{RESET}")
    lines.append(f"{BOLD}║{RESET} {BOLD}Thought Amplifier — Monitoring Dashboard{RESET}" + " " * 17 + f"{BOLD}║{RESET}")
    lines.append(f"{BOLD}║{RESET} {DIM}{now}{RESET}" + " " * 39 + f"{BOLD}║{RESET}")
    lines.append(f"{BOLD}╚{'═' * 58}╝{RESET}")
    lines.append("")

    # ── Status Row ──
    sched_ok = queue["depth"] >= 0
    olla_ok = ollama["online"]
    fleet_ok = fleet["health"] == "healthy"

    status_row = (
        f"  Scheduler: {color_bool(sched_ok, 'UP  ', 'DOWN')}   "
        f"Ollama: {color_bool(olla_ok, 'UP  ', 'DOWN')}   "
        f"Fleet: {color_bool(fleet_ok, 'OK  ', 'DEGR')}"
    )
    lines.append(status_row)
    lines.append("")

    # ── 1. Processor Jobs ──
    lines.append(f"{BOLD}{CYAN}  ▸ Processor Jobs{RESET}")
    lines.append(f"  {HR}")
    lines.append(f"    Completed: {GREEN}{jobs['jobs_completed']}{RESET}  "
                 f"Errored: {RED}{jobs['jobs_errored']}{RESET}  "
                 f"Journaled: {CYAN}{jobs['thoughts_journaled']}{RESET}")
    lines.append("")

    if jobs["per_agent"]:
        lines.append(f"    {'Agent':<16} {'Done':>5} {'Errs':>5} {'GPU ms':>9} {'Value':>7}")
        lines.append(f"    {'─' * 16} {'─' * 5} {'─' * 5} {'─' * 9} {'─' * 7}")
        for agent, data in sorted(jobs["per_agent"].items()):
            v_color = GREEN if data["avg_value"] > 0.7 else (YELLOW if data["avg_value"] > 0.4 else "")
            lines.append(
                f"    {agent:<16} {data['completed']:>5} {data['errors']:>5} "
                f"{data['total_gpu_ms']:>8.0f} "
                f"{v_color}{data['avg_value']:>7.3f}{RESET}"
            )
        lines.append("")

    # ── 2. Scheduler Queue ──
    lines.append(f"{BOLD}{MAGENTA}  ▸ Scheduler Queue{RESET}")
    lines.append(f"  {HR}")
    depth = queue["depth"]
    depth_color = RED if depth > 5 else (YELLOW if depth > 2 else GREEN)
    lines.append(f"    Queue depth: {depth_color}{depth}{RESET}  {bar(depth, 10, 15)}")
    lines.append(f"    Total handled: {queue['requests_handled']}  "
                 f"Uptime: {fmt_s(queue['scheduler_uptime_s'])}")

    if queue["running"]:
        r = queue["running"]
        lines.append(f"    Running: {CYAN}{r['id']}{RESET}  "
                     f"agent={r['agent']}  pri={r['priority']}  "
                     f"elapsed={r['running_ms']}s")

    if queue["queued_breakdown"]:
        parts = []
        for pri, count in sorted(queue["queued_breakdown"].items()):
            parts.append(f"{pri}={count}")
        lines.append(f"    Queued: {', '.join(parts)}")
    lines.append("")

    # ── 3. Ollama ──
    lines.append(f"{BOLD}{YELLOW}  ▸ Ollama{chr(10) if False else ''}{RESET}")
    lines.append(f"  {HR}")
    if ollama["online"]:
        lines.append(f"    Status: {GREEN}online{RESET}  "
                     f"Model: {CYAN}{ollama['model']}{RESET}  "
                     f"VRAM: {ollama['vram_mb']} MB  "
                     f"Family: {ollama['gpu_layers']}")

        if ollama.get("gpu"):
            for gpu in ollama["gpu"]:
                lines.append(f"    GPU {gpu['name']}: utilization {gpu['util']:.0%}")
        else:
            lines.append(f"    GPU: {DIM}not reported by Ollama{RESET}")

        if ollama.get("available_models"):
            models_str = ", ".join(ollama["available_models"][:5])
            lines.append(f"    Available: {DIM}{models_str}{RESET}")
    else:
        lines.append(f"    Status: {RED}offline{RESET} — {DIM}Ollama not responding on {OLLAMA_URL}{RESET}")
    lines.append("")

    # ── 4. Tripartite Fleet ──
    lines.append(f"{BOLD}{BLUE}  ▸ Tripartite Fleet{RESET}")
    lines.append(f"  {HR}")

    # Logos
    l = fleet["logos"]
    l_color = GREEN if l["status"] == "online" else RED
    lines.append(f"    {BOLD}Logos{RESET} (scheduler)    : {l_color}{l['status']}{RESET}  "
                 f"uptime={fmt_s(l['uptime_s'])}  handled={l['requests_handled']}")

    # Pathos
    p = fleet["pathos"]
    ev_color = GREEN if p["total_outcomes"] > 0 else DIM
    lines.append(f"    {BOLD}Pathos{RESET} (evolver)     : {ev_color}{p['status']}{RESET}  "
                 f"outcomes={p['total_outcomes']}  evolutions={p['evolution_count']}  "
                 f"policy={p['policy_size']}")
    if p["agent_quality"]:
        q_parts = [f"{a}={q:.2f}" for a, q in sorted(p["agent_quality"].items())[:4]]
        lines.append(f"      quality: {DIM}{', '.join(q_parts)}{RESET}")

    # Ethos
    e = fleet["ethos"]
    lines.append(f"    {BOLD}Ethos{RESET} (fair use)      : {GREEN}{e['status']}{RESET}  "
                 f"agents={e['agents_registered']}  floor={e['total_floor_ms']:.0f}ms")
    if e["cloud_configured"]:
        lines.append(f"      cloud: {e['cloud_requests']} reqs, "
                     f"{GREEN}{e['cloud_successes']} ok{RESET}, "
                     f"{RED}{e['cloud_failures']} fail{RESET}  "
                     f"neurons: {e['neurons_remaining']}/{e['neurons_daily_limit']}")

    lines.append("")
    lines.append(f"  {DIM}{HR}{RESET}")
    lines.append(f"  {DIM}Data sources: scheduler:{SCHEDULER_URL}  ollama:{OLLAMA_URL}{RESET}")
    lines.append("")

    return "\n".join(lines)


def render_json(jobs: dict, queue: dict, ollama: dict, fleet: dict) -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processor": jobs,
        "scheduler": queue,
        "ollama": ollama,
        "fleet": fleet,
    }, indent=2, ensure_ascii=False)


# ─── Main ────────────────────────────────────────────────────────

def collect() -> tuple[dict, dict, dict, dict]:
    """Collect all metrics. Each call is independent and safe to fail individually."""
    jobs = get_job_stats()
    queue = get_queue_depth()
    ollama = get_ollama_status()
    fleet = get_fleet_status()
    return jobs, queue, ollama, fleet


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Thought Amplifier Monitoring Dashboard")
    parser.add_argument("--watch", "-w", type=int, default=0,
                        help="Refresh interval in seconds (0 = one-shot)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of terminal UI")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system("clear" if sys.platform != "win32" else "cls")
                jobs, queue, ollama, fleet = collect()
                if args.json:
                    print(render_json(jobs, queue, ollama, fleet))
                else:
                    print(render(jobs, queue, ollama, fleet))
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print(f"\n{DIM}Dashboard stopped.{RESET}")
    else:
        jobs, queue, ollama, fleet = collect()
        if args.json:
            print(render_json(jobs, queue, ollama, fleet))
        else:
            print(render(jobs, queue, ollama, fleet))


if __name__ == "__main__":
    main()
