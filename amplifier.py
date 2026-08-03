#!/usr/bin/env python3
"""
amplifier.py — Thought Amplifier Main Entry Point

A small model thinks continuously. A supervisor agent watches and adjusts
the conditions under which the small model thinks. Six specialized modes
extend the stream into research, debate, creativity, monitoring, synthesis,
and experimentation.

Usage:
    # Basic: just think
    python amplifier.py

    # With context and custom interval
    python amplifier.py --context "You are thinking about AI consciousness" --interval 10

    # Reporter mode: research a URL
    python amplifier.py --mode reporter --url https://example.com/article

    # Advocate mode: devil's advocate
    python amplifier.py --mode advocate --claim "Free trade always benefits both countries"

    # Mirror mode: creative reflection
    python amplifier.py --mode mirror --theme "The way rivers reshape landscapes"

    # Watcher mode: monitor a URL
    python amplifier.py --mode watcher --url https://news.site.com --interval 60 --max-checks 10

    # Connector mode: find patterns across sources
    python amplifier.py --mode connector --sources url1 url2 "some text"

    # Simulator mode: thought experiment
    python amplifier.py --mode simulator --premise "What if humans could photosynthesize?"

    # With viewer running
    python amplifier.py --viewer

    # Supervisor only (adjust existing thought stream)
    python amplifier.py --supervise

From REPO_DESIGN.md:
    Training signal = the stream of consciousness (every thought is an example)
    Loss function = play quality (novelty, specificity, engagement)
    Gradient = prompt and parameter adjustment, applied every 30 seconds
    Model update = continuous — the prompt evolves, the temperature shifts
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time

# Ensure local imports work regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.journal import Journal
from core.thinker import Thinker, ThinkerConfig, resolve_api_keys
from core.supervisor import Supervisor


# ─── Mode Imports ───────────────────────────────────────────────

def get_mode_instance(mode: str, thinker: Thinker, journal: Journal,
                      api_keys: dict[str, str], args) -> object | None:
    """Instantiate a mode by name."""
    glm_key = api_keys.get("glm", "")
    ds_key = api_keys.get("deepseek", "")
    glm_model = args.glm_model
    ds_model = args.deepseek_model

    if mode == "reporter":
        from modes.reporter import Reporter
        return Reporter(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                       glm_model=glm_model, deepseek_model=ds_model)
    elif mode == "advocate":
        from modes.advocate import Advocate
        return Advocate(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                       glm_model=glm_model, deepseek_model=ds_model)
    elif mode == "mirror":
        from modes.mirror import Mirror
        return Mirror(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                     glm_model=glm_model, deepseek_model=ds_model)
    elif mode == "watcher":
        from modes.watcher import Watcher
        return Watcher(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                      glm_model=glm_model, deepseek_model=ds_model)
    elif mode == "connector":
        from modes.connector import Connector
        return Connector(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                        glm_model=glm_model, deepseek_model=ds_model)
    elif mode == "simulator":
        from modes.simulator import Simulator
        return Simulator(thinker, journal, api_key=glm_key, deepseek_api_key=ds_key,
                        glm_model=glm_model, deepseek_model=ds_model)
    return None


# ─── Main ───────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Thought Amplifier — continuous thought generation with supervisor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    parser.add_argument("--mode", "-m",
                        choices=["think", "reporter", "advocate", "mirror",
                                "watcher", "connector", "simulator"],
                        default="think",
                        help="Operating mode (default: think)")

    # Common options
    parser.add_argument("--context", "-c", default="",
                        help="Context to inject into thoughts")
    parser.add_argument("--interval", "-i", type=float, default=5.0,
                        help="Seconds between thoughts (default: 5)")
    parser.add_argument("--port", "-p", type=int, default=8770,
                        help="Viewer port (default: 8770)")
    parser.add_argument("--viewer", action="store_true",
                        help="Start the WebSocket viewer server")
    parser.add_argument("--supervise", action="store_true",
                        help="Run the supervisor alongside the thinker")
    parser.add_argument("--supervisor-interval", type=float, default=30.0,
                        help="Supervisor review interval in seconds (default: 30)")
    parser.add_argument("--journal-dir", default="journals",
                        help="Directory for journal files (default: journals)")

    # Model configuration
    parser.add_argument("--ollama-model", default="granite3.1-dense:2b",
                        help="Ollama model name (default: granite3.1-dense:2b)")
    parser.add_argument("--temperature", type=float, default=0.9,
                        help="LLM temperature (default: 0.9)")
    parser.add_argument("--glm-model", default="glm-4-flash",
                        help="GLM model for API fallback (default: glm-4-flash)")
    parser.add_argument("--deepseek-model", default="deepseek-chat",
                        help="DeepSeek model (default: deepseek-chat)")

    # Mode-specific arguments
    parser.add_argument("--url", help="URL for reporter/watcher modes")
    parser.add_argument("--claim", help="Claim for advocate mode")
    parser.add_argument("--theme", help="Theme for mirror mode")
    parser.add_argument("--premise", help="Premise for simulator mode")
    parser.add_argument("--sources", nargs="+", help="Sources for connector mode")
    parser.add_argument("--max-checks", type=int, default=5,
                        help="Max checks for watcher mode (default: 5)")
    parser.add_argument("--num-thoughts", type=int, default=5,
                        help="Number of thoughts/arguments/reflections for modes")

    args = parser.parse_args()

    # ─── Initialize ─────────────────────────────────────────────

    # Resolve API keys
    api_keys = resolve_api_keys()

    # Create journal
    journal = Journal(journal_dir=args.journal_dir)

    # Create thinker config
    config = ThinkerConfig(
        ollama_model=args.ollama_model,
        system_prompt=args.context if args.context else ThinkerConfig().system_prompt,
        context=args.context,
        temperature=args.temperature,
        interval=args.interval,
        glm_api_key=api_keys.get("glm", ""),
        deepseek_api_key=api_keys.get("deepseek", ""),
        glm_model=args.glm_model,
        deepseek_model=args.deepseek_model,
    )

    # Create thinker
    thinker = Thinker(config, journal)

    # Journal startup
    journal.write("system", "Thought Amplifier starting up", {
        "mode": args.mode,
        "args": vars(args),
        "api_keys_available": list(api_keys.keys()),
    })

    # Print banner
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║        Thought Amplifier v1.0                 ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Mode:     {args.mode}")
    print(f"  Journal:  {journal.jsonl_path}")
    print(f"  Interval: {args.interval}s")
    if args.context:
        print(f"  Context:  {args.context[:60]}...")
    print()

    # ─── Start viewer if requested ──────────────────────────────

    if args.viewer:
        import subprocess
        viewer_proc = subprocess.Popen(
            [sys.executable, "viewer/server.py"],
            env={**os.environ, "VIEWER_PORT": str(args.port)},
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        print(f"  Viewer:   http://localhost:{args.port}")
        print()

        def kill_viewer(signum, frame):
            viewer_proc.terminate()
            sys.exit(0)
        signal.signal(signal.SIGINT, kill_viewer)

    # ─── Handle Ctrl+C ──────────────────────────────────────────

    def signal_handler(signum, frame):
        print("\n\nShutting down...")
        thinker.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    # ─── Mode Dispatch ──────────────────────────────────────────

    if args.mode == "think":
        # ── Plain thought loop (with optional supervisor) ──

        if args.supervise:
            # Run supervisor in a thread
            supervisor = Supervisor(
                thinker, journal,
                review_interval=args.supervisor_interval,
                api_key=api_keys.get("glm", ""),
                deepseek_api_key=api_keys.get("deepseek", ""),
                glm_model=args.glm_model,
                deepseek_model=args.deepseek_model,
            )
            sup_thread = threading.Thread(target=supervisor.run, daemon=True)
            sup_thread.start()
            print(f"  Supervisor: active (interval={args.supervisor_interval}s)")
            print()

        thinker.run()

    else:
        # ── Specialized mode ──

        mode_instance = get_mode_instance(args.mode, thinker, journal, api_keys, args)
        if mode_instance is None:
            print(f"Unknown mode: {args.mode}")
            sys.exit(1)

        print(f"  Running {args.mode} mode...")
        print()

        if args.mode == "reporter":
            if not args.url:
                print("Error: --url required for reporter mode")
                sys.exit(1)
            entries = mode_instance.research(args.url, num_thoughts=args.num_thoughts)

        elif args.mode == "advocate":
            claim = args.claim or (sys.stdin.read() if not sys.stdin.isatty() else None)
            if not claim:
                print("Error: --claim required for advocate mode (or pipe input)")
                sys.exit(1)
            entries = mode_instance.argue(claim, num_arguments=args.num_thoughts)

        elif args.mode == "mirror":
            if not args.theme:
                print("Error: --theme required for mirror mode")
                sys.exit(1)
            entries = mode_instance.reflect(args.theme, num_reflections=args.num_thoughts)

        elif args.mode == "watcher":
            if not args.url:
                print("Error: --url required for watcher mode")
                sys.exit(1)
            entries = mode_instance.watch(args.url, interval=args.interval,
                                          max_checks=args.max_checks)

        elif args.mode == "connector":
            if not args.sources or len(args.sources) < 2:
                print("Error: --sources (at least 2) required for connector mode")
                sys.exit(1)
            entries = mode_instance.connect(args.sources)

        elif args.mode == "simulator":
            if not args.premise:
                print("Error: --premise required for simulator mode")
                sys.exit(1)
            entries = mode_instance.simulate(args.premise, num_trajectories=args.num_thoughts)

        # Print results
        print(f"\n{'='*50}")
        print(f"Mode complete. {len(entries)} entries written.")
        print(f"Journal: {journal.jsonl_path}")
        print(f"Markdown: {journal.md_path}")
        print(f"{'='*50}\n")

    # ─── Cleanup ────────────────────────────────────────────────

    if args.viewer:
        viewer_proc.terminate()
        viewer_proc.wait()


if __name__ == "__main__":
    main()
