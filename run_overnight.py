#!/usr/bin/env python3
"""
run_overnight.py — Nightly distillation runner with domain rotation.

Runs the full distillation loop across all 4 domains:
  roblox → maritime → cognition → digital-twin

Each domain gets 5 iterations (20 total), then generates a morning briefing.

Usage:
    python3 run_overnight.py                    # Default: 5 iterations per domain
    python3 run_overnight.py --iterations 10    # 10 iterations per domain
    python3 run_overnight.py --dry-run          # Preview without API calls

Designed to run via cron or heartbeat overnight. Survives Ollama crashes,
API failures, and partial results without human intervention.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Add the repo to path
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from distillation_loop import (
    TEACHING_TOPICS,
    TASK_SOURCES,
    run_iteration,
    save_run_log,
    compute_stats,
    OUTPUT_DIR,
    LOG_DIR,
    REFLEX_DIR,
    PROMPT_DIR,
)
from watchdog import ensure_healthy, health_check_full, log_event

# ─── Configuration ─────────────────────────────────────────────

ALL_DOMAINS = ["roblox", "maritime", "cognition", "digital-twin"]
DEFAULT_ITERATIONS = 5
BRIEFING_DIR = Path("/home/eileen/.openclaw/workspace/memory/night-watch")

# ─── Morning Briefing Generator ────────────────────────────────

def generate_briefing(
    all_summaries: dict[str, list[dict]],
    start_time: str,
    end_time: str,
    watchdog_events: list[dict],
) -> str:
    """
    Generate a markdown morning briefing from the night's run.

    Includes:
      - Iterations run (per domain + total)
      - Help rate (overall + per domain)
      - Reflexes compiled
      - Prompt promotions
      - Average delta
      - Anything surprising (errors, anomalies, notable achievements)
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # Aggregate stats
    total_iterations = sum(len(v) for v in all_summaries.values())
    total_successful = sum(
        len([s for s in v if s.get("success", True)]) for v in all_summaries.values()
    )
    total_failed = total_iterations - total_successful

    all_deltas = []
    all_helped = 0
    total_reflexes = 0
    total_promotions = 0
    domain_reports = []

    for domain in ALL_DOMAINS:
        summaries = all_summaries.get(domain, [])
        if not summaries:
            domain_reports.append(f"### {domain}\nNo iterations run.\n")
            continue

        stats = compute_stats(summaries)
        successful = [s for s in summaries if s.get("success", True)]
        helped_count = stats.get("teaching_helped_count", 0)
        all_helped += helped_count
        total_reflexes += stats.get("reflexes_compiled", 0)
        total_promotions += stats.get("promotions", 0)

        if successful:
            for s in successful:
                all_deltas.append(s["delta"])

        help_rate = stats.get("help_rate", 0)
        avg_delta = stats.get("avg_delta", 0)

        report = (
            f"### {domain}\n"
            f"- Iterations: {stats.get('total_iterations', len(summaries))} "
            f"({len(successful)} successful, {stats.get('failed_iterations', 0)} failed)\n"
            f"- Help rate: {help_rate:.1%} ({helped_count}/{len(successful)})\n"
            f"- Avg delta: {avg_delta:+.3f}\n"
            f"- Reflexes compiled: {stats.get('reflexes_compiled', 0)}\n"
            f"- Promotions: {stats.get('promotions', 0)}\n"
        )

        if stats.get("errors"):
            report += f"- Errors: {stats['errors']}\n"

        # Notable iterations (highest and lowest delta)
        if successful:
            best = max(successful, key=lambda s: s["delta"])
            worst = min(successful, key=lambda s: s["delta"])
            report += (
                f"- Best: iter {best['iteration']} "
                f"(Δ={best['delta']:+.3f}, topic: {best['topic'][:50]})\n"
                f"- Worst: iter {worst['iteration']} "
                f"(Δ={worst['delta']:+.3f}, topic: {worst['topic'][:50]})\n"
            )

        domain_reports.append(report)

    # Overall stats
    overall_help_rate = all_helped / total_successful if total_successful > 0 else 0
    overall_avg_delta = sum(all_deltas) / len(all_deltas) if all_deltas else 0

    # Surprises section
    surprises = []
    if total_failed > 0:
        surprises.append(
            f"⚠️ {total_failed} iterations failed — check error logs"
        )
    if watchdog_events:
        restarts = [e for e in watchdog_events if "restart" in e.get("type", "")]
        if restarts:
            surprises.append(
                f"🔧 Ollama required {len(restarts)} watchdog interventions"
            )
    if total_promotions > 0:
        surprises.append(
            f"⭐ {total_promotions} prompt promotion(s) achieved — Wesley is learning!"
        )
    if overall_avg_delta > 0.1:
        surprises.append(
            f"📈 Strong night — average delta {overall_avg_delta:+.3f} is above 0.1"
        )
    if overall_avg_delta < 0:
        surprises.append(
            f"📉 Concerning — average delta {overall_avg_delta:+.3f} is negative. "
            f"Teaching may be hurting more than helping."
        )

    # Count total reflexes in store
    total_reflexes_in_store = len(list(REFLEX_DIR.glob("*.nail.json")))

    # Count prompt versions
    total_prompt_versions = 0
    for domain in ALL_DOMAINS:
        version_path = PROMPT_DIR / f"{domain}_versions.jsonl"
        if version_path.exists():
            total_prompt_versions += sum(
                1 for line in version_path.read_text().strip().split("\n") if line.strip()
            )

    # Build the briefing
    briefing = f"""# 🌅 Night Watch Briefing — {date_str}

**Run window:** {start_time} → {end_time}

## Summary

| Metric | Value |
|--------|-------|
| Total iterations | {total_iterations} |
| Successful | {total_successful} |
| Failed | {total_failed} |
| Help rate | {overall_help_rate:.1%} |
| Avg delta | {overall_avg_delta:+.3f} |
| Reflexes compiled (tonight) | {total_reflexes} |
| Reflexes in store (total) | {total_reflexes_in_store} |
| Prompt promotions (tonight) | {total_promotions} |
| Prompt versions (total) | {total_prompt_versions} |

## Per-Domain Breakdown

{chr(10).join(domain_reports)}

## Watchdog Events

"""
    if watchdog_events:
        for event in watchdog_events[-10:]:  # Last 10 events
            briefing += (
                f"- `{event['timestamp']}` — **{event['type']}**: "
                f"{json.dumps(event.get('details', {}))}\n"
            )
    else:
        briefing += "No watchdog events. Ollama was stable all night.\n"

    briefing += f"""
## Surprises

"""
    if surprises:
        for s in surprises:
            briefing += f"- {s}\n"
    else:
        briefing += "Nothing surprising. A quiet, productive night.\n"

    briefing += f"""
---
*Generated by run_overnight.py at {now.isoformat()}*
"""

    return briefing


def save_briefing(briefing: str, date_str: str | None = None) -> Path:
    """Save the briefing to the night-watch directory."""
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = BRIEFING_DIR / f"{date_str}-night.md"
    path.write_text(briefing, encoding="utf-8")
    return path


# ─── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Overnight Distillation Runner — Domain Rotation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Iterations per domain (default: {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between iterations (default: 2.0)",
    )
    parser.add_argument(
        "--domains",
        type=str,
        nargs="+",
        default=ALL_DOMAINS,
        help=f"Domains to run (default: {ALL_DOMAINS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without making API calls",
    )
    parser.add_argument(
        "--skip-briefing",
        action="store_true",
        help="Skip morning briefing generation",
    )
    args = parser.parse_args()

    start_time = datetime.now(timezone.utc).isoformat()
    print(f"🌙 Overnight Distillation Run")
    print(f"   Start: {start_time}")
    print(f"   Domains: {args.domains}")
    print(f"   Iterations per domain: {args.iterations}")
    print(f"   Total iterations: {len(args.domains) * args.iterations}")
    print()

    if args.dry_run:
        print("   [DRY RUN] Plan:")
        for domain in args.domains:
            topics = TEACHING_TOPICS.get(domain, [])
            tasks = TASK_SOURCES.get(domain, [])
            print(f"\n   {domain}:")
            for i in range(1, args.iterations + 1):
                topic = topics[(i - 1) % len(topics)] if topics else "(none)"
                task = tasks[(i - 1) % len(tasks)]["task"][:60] if tasks else "(none)"
                print(f"     iter {i}: {topic[:50]}")
                print(f"              task: {task}")
        return

    # Pre-flight: ensure Ollama is healthy
    print("🔧 Pre-flight health check...")
    if not ensure_healthy(max_attempts=3):
        print("❌ Ollama is not healthy and could not be recovered. Aborting.")
        log_event("overnight_abort", {"reason": "preflight_health_check_failed"})
        sys.exit(1)

    health = health_check_full()
    print(f"   Ollama: {'✓' if health['ollama_alive'] else '✗'}")
    print(f"   Model ({os.environ.get('OLLAMA_MODEL', 'granite3.1-dense:2b')}): "
          f"{'✓' if health['model_available'] else '✗'}")
    print(f"   GPU: {'✓' if health['gpu_available'] else '⚠ (CPU mode)'}")
    print(f"   Test inference: {'✓' if health['test_inference'] else '✗'}")
    print()

    # Track all summaries per domain
    all_summaries: dict[str, list[dict]] = {}
    total_iterations_run = 0
    total_errors = 0

    for domain in args.domains:
        print(f"\n{'═' * 60}")
        print(f"  Domain: {domain}")
        print(f"  Topics: {len(TEACHING_TOPICS.get(domain, []))}")
        print(f"  Tasks:  {len(TASK_SOURCES.get(domain, []))}")
        print(f"{'═' * 60}\n")

        summaries: list[dict] = []
        domain_errors = 0

        for i in range(1, args.iterations + 1):
            t0 = time.time()

            try:
                result = run_iteration(domain, i)
                summaries.append(result)

                if result.get("success", True):
                    delta = result["delta"]
                    delta_str = f"+{delta:.3f} ✓" if delta > 0 else f"{delta:.3f}"
                    print(
                        f"  [{domain:>12}] iter {i:3d}/{args.iterations} │ "
                        f"Δ={delta_str:<12} │ "
                        f"reflex={'YES' if result['reflex_compiled'] else 'no':<3}"
                    )
                else:
                    domain_errors += 1
                    total_errors += 1
                    print(
                        f"  [{domain:>12}] iter {i:3d}/{args.iterations} │ "
                        f"ERROR: {result.get('error', 'unknown')}"
                    )

            except Exception as e:
                domain_errors += 1
                total_errors += 1
                print(f"  [{domain}] iter {i} EXCEPTION: {e}")
                traceback.print_exc()
                # Record the error as a summary
                summaries.append({
                    "domain": domain,
                    "iteration": i,
                    "topic": "(error)",
                    "task": "",
                    "baseline_score": 0.0,
                    "taught_score": 0.0,
                    "delta": 0.0,
                    "teaching_helped": False,
                    "reflex_compiled": False,
                    "reflex_id": "",
                    "prompt_updated": False,
                    "prompt_version": "",
                    "consecutive_positives": 0,
                    "error": str(e),
                    "success": False,
                })

            total_iterations_run += 1
            elapsed = time.time() - t0
            if i < args.iterations and args.delay > 0:
                time.sleep(args.delay)

        all_summaries[domain] = summaries

        # Save per-domain run log
        if summaries:
            log_path = save_run_log(summaries, domain)
            print(f"\n  Run log: {log_path}")

            stats = compute_stats(summaries)
            successful = stats.get("successful_iterations", len(summaries))
            helped = stats.get("teaching_helped_count", 0)
            print(
                f"  Stats: {successful} ok, {helped} helped, "
                f"Δ={stats.get('avg_delta', 0):+.3f} avg, "
                f"{stats.get('reflexes_compiled', 0)} reflexes"
            )
            if domain_errors:
                print(f"  ⚠ {domain_errors} errors")

        # Brief health check between domains
        if domain != args.domains[-1]:
            print("\n  Health check between domains...")
            if not ensure_healthy(max_attempts=2):
                print("  ⚠ Ollama unhealthy after domain, but continuing...")

    end_time = datetime.now(timezone.utc).isoformat()
    print(f"\n\n{'═' * 60}")
    print(f"  Run complete: {total_iterations_run} iterations")
    print(f"  Errors: {total_errors}")
    print(f"  Window: {start_time} → {end_time}")
    print(f"{'═' * 60}\n")

    # Load watchdog events for the briefing
    watchdog_log = LOG_DIR / "watchdog.jsonl"
    watchdog_events = []
    if watchdog_log.exists():
        try:
            lines = watchdog_log.read_text().strip().split("\n")
            # Only events from this run (last N events)
            for line in lines:
                if line.strip():
                    event = json.loads(line)
                    if event.get("timestamp", "") >= start_time:
                        watchdog_events.append(event)
        except (json.JSONDecodeError, OSError):
            pass

    # Generate morning briefing
    if not args.skip_briefing:
        print("📝 Generating morning briefing...")
        briefing = generate_briefing(all_summaries, start_time, end_time, watchdog_events)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        briefing_path = save_briefing(briefing, date_str)
        print(f"   Briefing saved: {briefing_path}")
        print("\n" + "=" * 60)
        print(briefing)
        print("=" * 60)


if __name__ == "__main__":
    main()
