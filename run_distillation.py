#!/usr/bin/env python3
"""
run_distillation.py — CLI runner for the self-improvement loop.

Usage:
    python3 run_distillation.py --domain roblox --iterations 20
    python3 run_distillation.py --domain cognition --iterations 50
    python3 run_distillation.py --domain all --iterations 10

Runs the full 5-stage distillation loop continuously:
  1. TEACHER  — GLM-5.2 generates a lesson about a domain topic
  2. STUDENT  — Granite 3.1 2B applies it to a real task
  3. EVALUATE — score vs baseline, calculate delta
  4. DISTILL  — compile helpful teaching into a .nail reflex
  5. UPDATE   — promote consistently helpful teaching to system prompt

After each iteration, prints:
  teacher topic → quality delta → reflex compiled (yes/no) → prompt updated (yes/no)

All artifacts saved to distillation-output/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add the repo to path
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# Import after path setup
from distillation_loop import (
    TASK_SOURCES,
    TEACHING_TOPICS,
    run_iteration,
    save_run_log,
    compute_stats,
    OUTPUT_DIR,
    REFLEX_DIR,
    PROMPT_DIR,
)

# ─── API Key Resolution ────────────────────────────────────────

def resolve_glm_api_key() -> str:
    """
    Resolve the GLM/Z.ai API key from multiple sources.

    Priority:
      1. GLM_API_KEY env var
      2. ZAI_API_KEY env var
      3. OpenClaw's auth store (SQLite)
    """
    # Check env vars first
    key = os.environ.get("GLM_API_KEY") or os.environ.get("ZAI_API_KEY")
    if key:
        return key

    # Try reading from OpenClaw's auth store
    try:
        import sqlite3

        for db_path in [
            Path.home() / ".openclaw" / "agents" / "main" / "agent" / "openclaw-agent.sqlite",
            Path.home() / ".openclaw" / "state" / "openclaw.sqlite",
        ]:
            if not db_path.exists():
                continue
            db = sqlite3.connect(str(db_path))
            cursor = db.cursor()

            # Check auth_profile_store
            try:
                cursor.execute("SELECT store_json FROM auth_profile_store WHERE store_key = 'primary'")
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    key = (
                        data.get("profiles", {})
                        .get("zai:default", {})
                        .get("key", "")
                    )
                    if key:
                        db.close()
                        return key
            except Exception:
                pass
            db.close()
    except Exception:
        pass

    return ""


# ─── CLI ────────────────────────────────────────────────────────

AVAILABLE_DOMAINS = ["roblox", "digital-twin", "maritime", "cognition", "all"]

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   THOUGHT AMPLIFIER — Distillation Loop                      ║
║   "The Pincher pattern at scale: cloud teaches, local        ║
║    learns, reflexes compile, the cloud fades."               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_banner(args):
    print(BANNER)
    print(f"  Domain:     {args.domain}")
    print(f"  Iterations: {args.iterations}")
    print(f"  Delay:      {args.delay}s between iterations")
    print(f"  Output:     {OUTPUT_DIR}/")
    print(f"  Promote at: {args.promote_threshold} consecutive wins")
    print()


def print_iteration_summary(s: dict[str, any]) -> None:
    """Print one iteration's results."""
    domain = s["domain"]
    iteration = s["iteration"]
    topic = s["topic"][:50]
    delta = s["delta"]
    baseline = s["baseline_score"]
    taught = s["taught_score"]

    # Format the delta with color indicator
    if delta > 0:
        delta_str = f"+{delta:.3f} ✓"
        indicator = "HELPED"
    elif delta == 0:
        delta_str = f" {delta:.3f} ="
        indicator = "NEUTRAL"
    else:
        delta_str = f"{delta:.3f} ✗"
        indicator = "NO HELP"

    reflex = "YES" if s["reflex_compiled"] else "no"
    promoted = "YES" if s["prompt_updated"] else "no"
    consec = s.get("consecutive_positives", 0)

    print(
        f"  [{domain:>12}] iter {iteration:3d} │ "
        f"Δ={delta_str:<12} │ "
        f"base={baseline:.3f} → taught={taught:.3f} │ "
        f"reflex={reflex:<3} │ prompt={promoted:<3}"
    )
    print(f"    topic: {topic}")
    if s["prompt_updated"]:
        print(f"    ★ PROMOTED to v{s.get('prompt_version', '?')}")
    print()


def print_run_summary(domain: str, summaries: list[dict]) -> None:
    """Print aggregate statistics for a completed run."""
    stats = compute_stats(summaries)
    if not stats:
        return

    print(f"\n{'─' * 60}")
    print(f"  Run Summary: {domain}")
    print(f"{'─' * 60}")
    print(f"  Total iterations:    {stats['total_iterations']}")
    print(f"  Teaching helped:     {stats['teaching_helped_count']}/{stats['total_iterations']} "
          f"({stats['help_rate']:.1%})")
    print(f"  Reflexes compiled:   {stats['reflexes_compiled']}")
    print(f"  Prompt promotions:   {stats['promotions']}")
    print(f"  Avg delta:           {stats['avg_delta']:+.3f}")
    print(f"  Best delta:          {stats['max_delta']:+.3f}")
    print(f"  Worst delta:         {stats['min_delta']:+.3f}")

    # Count reflexes in store
    domain_reflexes = list(REFLEX_DIR.glob(f"*.nail.json"))
    domain_versions = list(PROMPT_DIR.glob(f"{domain}_versions.jsonl"))
    print(f"\n  Reflexes in store:   {len(domain_reflexes)} total")
    if domain_versions:
        print(f"  Prompt versions:     {domain_versions[0].name}")

    print(f"{'─' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Thought Amplifier — Distillation Loop Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 run_distillation.py --domain roblox --iterations 20\n"
            "  python3 run_distillation.py --domain cognition --iterations 50\n"
            "  python3 run_distillation.py --domain all --iterations 10\n"
        ),
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="cognition",
        choices=AVAILABLE_DOMAINS,
        help="Domain to teach (default: cognition)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="Number of distillation iterations (default: 20)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to wait between iterations (default: 2.0)",
    )
    parser.add_argument(
        "--promote-threshold",
        type=int,
        default=3,
        help="Consecutive positive deltas required for prompt promotion (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without calling APIs",
    )
    args = parser.parse_args()

    # Resolve API key
    api_key = resolve_glm_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: Could not find GLM/Z.ai API key.")
        print("Set GLM_API_KEY or ZAI_API_KEY environment variable.")
        sys.exit(1)

    if api_key:
        os.environ["GLM_API_KEY"] = api_key

    # Patch the module to use the resolved key
    import distillation_loop
    distillation_loop.GLM_API_KEY = api_key
    distillation_loop.GLM_API_URL = os.environ.get(
        "GLM_API_URL",
        "https://api.z.ai/api/paas/v4/chat/completions",
    )

    # Patch the promote threshold
    import distillation_loop
    original_stage_update = distillation_loop.stage_update_prompt

    def patched_stage_update(teacher_artifact, eval_artifact, domain, iteration):
        return original_stage_update(
            teacher_artifact, eval_artifact, domain, iteration,
            promote_threshold=args.promote_threshold,
        )

    distillation_loop.stage_update_prompt = patched_stage_update

    print_banner(args)

    if args.dry_run:
        print("  [DRY RUN] Would teach:")
        domains_to_run = (
            ["roblox", "digital-twin", "maritime", "cognition"]
            if args.domain == "all"
            else [args.domain]
        )
        for d in domains_to_run:
            topics = TEACHING_TOPICS.get(d, [])
            tasks = TASK_SOURCES.get(d, [])
            print(f"\n  {d}:")
            for i in range(min(args.iterations, len(topics))):
                topic = topics[i % len(topics)]
                task = tasks[i % len(tasks)]["task"][:60]
                print(f"    iter {i+1}: {topic[:50]}")
                print(f"             task: {task}")
        return

    # Determine domains
    domains_to_run = (
        ["roblox", "digital-twin", "maritime", "cognition"]
        if args.domain == "all"
        else [args.domain]
    )

    # Run the loop
    for domain in domains_to_run:
        print(f"\n{'═' * 60}")
        print(f"  Domain: {domain}")
        print(f"  Topics: {len(TEACHING_TOPICS.get(domain, []))}")
        print(f"  Tasks:  {len(TASK_SOURCES.get(domain, []))}")
        print(f"{'═' * 60}\n")

        summaries: list[dict] = []

        try:
            for i in range(1, args.iterations + 1):
                t0 = time.time()

                try:
                    result = run_iteration(domain, i)
                    summaries.append(result)
                    print_iteration_summary(result)
                except Exception as e:
                    print(f"  [{domain}] iter {i} ERROR: {e}")
                    import traceback
                    traceback.print_exc()

                elapsed = time.time() - t0
                if i < args.iterations and args.delay > 0:
                    time.sleep(args.delay)

        except KeyboardInterrupt:
            print(f"\n  Stopped by user after {len(summaries)} iterations.")

        # Save run log
        if summaries:
            log_path = save_run_log(summaries, domain)
            print(f"  Run log saved: {log_path}")

            # Print summary
            print_run_summary(domain, summaries)

    # Final overall stats
    print(f"\n{'═' * 60}")
    print(f"  All domains complete. Artifacts in {OUTPUT_DIR}/")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
