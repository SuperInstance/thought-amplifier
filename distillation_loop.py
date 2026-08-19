"""
Distillation Loop — the self-improvement engine.

This is the core of the whole system: a continuous loop where a large cloud
model (GLM-5.2 via Z.ai, unlimited tokens) teaches a small local model
(Granite 3.1 2B via Ollama, free) how to be better at real tasks.

Over time, the local model needs the cloud less and less. Teaching that
helped gets compiled into .nail reflexes (Pincher's "LLM as compiler"
pattern). Consistently helpful teaching becomes permanent system prompt
directives via the PromptUpdater.

The five stages:
  1. TEACHER    — GLM generates a focused lesson about a domain topic
  2. STUDENT    — Granite applies the lesson to a real task
  3. EVALUATE   — score Granite's output vs its baseline (no teaching)
  4. DISTILL    — if teaching helped, compile it into a .nail reflex
  5. UPDATE     — if teaching consistently helps, promote to system prompt

Architecture follows REPO_DESIGN.md §5 and the Pincher pattern:
  - Cloud is the compiler, not the runtime
  - Local is the runtime, not the compiler
  - Reflexes are the bridge — compiled wisdom that avoids future cloud calls
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Paths ──────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "distillation-output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Sub-directories for artifacts
TEACHER_DIR = OUTPUT_DIR / "teacher"
STUDENT_DIR = OUTPUT_DIR / "student"
EVAL_DIR = OUTPUT_DIR / "eval"
REFLEX_DIR = OUTPUT_DIR / "reflexes"
PROMPT_DIR = OUTPUT_DIR / "prompts"
LOG_DIR = OUTPUT_DIR / "logs"

for d in [TEACHER_DIR, STUDENT_DIR, EVAL_DIR, REFLEX_DIR, PROMPT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Slackwater-cognition imports (for quality scoring, nail compilation, prompt management)
COGNITION_ROOT = Path("/home/eileen/projects/slackwater-cognition")
sys.path.insert(0, str(COGNITION_ROOT))

# ─── API Configuration ─────────────────────────────────────────

# Z.ai GLM API (teacher) — unlimited tokens on Max plan
# The Z.ai API key is a JWT-style token (project_id.secret) from Z.ai console.
# Endpoint: https://api.z.ai/api/paas/v4/chat/completions (also: open.bigmodel.cn)
GLM_API_URL = os.environ.get(
    "GLM_API_URL",
    "https://api.z.ai/api/paas/v4/chat/completions",
)
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
GLM_MODEL = os.environ.get("GLM_MODEL", "glm-4.5-flash")  # free model on Z.ai

# Ollama (student) — local, free
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite3.1-dense:2b")
OLLAMA_BIN = os.environ.get("OLLAMA_BIN", "/home/eileen/.local/bin/ollama")

# Fleet Gateway shim (Phase 3: the distillation loop is its first consumer).
# Cloud API POSTs try fleet_gw.post() first; on ANY failure — shim missing,
# gateway down, unknown URL, bad response — we fall back to the original
# curl path, so loop behavior is unchanged. Fail-open is non-negotiable.
# Kill switch: DISTILL_USE_GATEWAY=0 forces curl-only (pre-Phase-3 behavior).
FLEET_GW_CLIENT_DIR = Path("/home/eileen/projects/fleet-gateway/clients/python")
GATEWAY_ENABLED = os.environ.get("DISTILL_USE_GATEWAY", "1") != "0"

_fleet_gw_cache: list = []  # [module] once successfully imported

# ─── Domain Definitions ────────────────────────────────────────

# Real task sources — actual code from the codebase
TASK_SOURCES: dict[str, list[dict[str, str]]] = {
    "roblox": [
        {
            "task": "Review this CatchMechanics module and suggest improvements to the fishing state machine. Focus on edge cases, performance, and code clarity.",
            "code": "ServerScriptService/FishingSystem/CatchMechanics.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Analyze the Currency system's three-tier economy. Suggest improvements for material balance and transaction logging.",
            "code": "ServerScriptService/EconomySystem/Currency.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Review the FishSpawner module. How could fish density calculations be improved for better gameplay?",
            "code": "ServerScriptService/FishingSystem/FishSpawner.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Review the SaveSystem module. What are the risks and how would you improve data persistence reliability?",
            "code": "ServerScriptService/SaveSystem/init.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Analyze VesselUpgrades. How should upgrade costs scale and what validation is needed?",
            "code": "ServerScriptService/EconomySystem/VesselUpgrades.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
    ],
    "digital-twin": [
        {
            "task": "Analyze the Lucineer Worker relay architecture. How could the data flow between Roblox clients and the Cloudflare Worker be improved?",
            "code": "src/index.ts",
            "repo": "/home/eileen/projects/lucineer-worker",
        },
        {
            "task": "Review the LucineerSession Durable Object. What state management improvements would reduce latency?",
            "code": "src/do/LucineerSession.ts",
            "repo": "/home/eileen/projects/lucineer-worker",
        },
        {
            "task": "Analyze the worker types. What data contracts are missing for a real-time digital twin?",
            "code": "src/types.ts",
            "repo": "/home/eileen/projects/lucineer-worker",
        },
    ],
    "maritime": [
        {
            "task": "Review the CatchMechanics fishing loop. How could the tension and line integrity physics be more realistic?",
            "code": "ServerScriptService/FishingSystem/CatchMechanics.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Analyze FishStocks. How should fish population dynamics model spawning, migration, and depletion?",
            "code": "ServerScriptService/FishingSystem/FishStocks.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Review the GearSystem. How should different gear types affect catch probability and fish selection?",
            "code": "ServerScriptService/FishingSystem/GearSystem.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
        {
            "task": "Analyze EraGates. How should progression unlock new fishing grounds and vessel capabilities?",
            "code": "ServerScriptService/EconomySystem/EraGates.lua",
            "repo": "/home/eileen/projects/lucineer-roblox",
        },
    ],
    "cognition": [
        {
            "task": "Review the batten spline cascade router. How could routing thresholds be tuned for better local/cloud balance?",
            "code": "src/batten_spline/router.py",
            "repo": "/home/eileen/projects/batten-spline",
        },
        {
            "task": "Analyze the BattenSpline class. How could the Gaussian kernel bandwidth and decay parameters be optimized?",
            "code": "src/batten_spline/spline.py",
            "repo": "/home/eileen/projects/batten-spline",
        },
        {
            "task": "Review the NailCompiler. How could situation signatures be improved for better reflex matching?",
            "code": "conductor/../reflex/nail_compiler.py",
            "repo": COGNITION_ROOT,
        },
        {
            "task": "Review the ReflexMatcher. How could the three-tier matching thresholds be improved?",
            "code": "conductor/../reflex/reflex_matcher.py",
            "repo": COGNITION_ROOT,
        },
        {
            "task": "Analyze the Conductor's analysis loop. What quality signals would improve pattern detection?",
            "code": "conductor/conductor.py",
            "repo": COGNITION_ROOT,
        },
    ],
}

# Teaching topics per domain — rotated through iterations
TEACHING_TOPICS: dict[str, list[str]] = {
    "roblox": [
        "Luau type checking best practices and strict mode patterns",
        "RemoteEvent vs RemoteFunction: when to use each and common pitfalls",
        "Roblox DataStore patterns: caching, retry logic, and data migration",
        "Entity-component patterns in Roblox for game system architecture",
        "Luau performance: table allocation, closure overhead, and hot paths",
        "Server-client boundary: what logic belongs where and why",
        "Roblox task scheduler: understanding task.delay, task.spawn, and heartbeat",
        "Memory management in long-running Roblox servers",
        "Anti-exploit patterns for economy and fishing systems",
        "Designing progression systems: era gates and unlock curves",
    ],
    "digital-twin": [
        "Cloudflare Durable Object patterns for real-time state synchronization",
        "WebSocket vs Server-Sent Events for bidirectional game state",
        "Eventual consistency vs strong consistency in digital twin architectures",
        "Schema versioning for evolving data contracts without breaking clients",
        "Rate limiting and backpressure in relay architectures",
        "D1 database optimization for game state persistence",
        "Vectorize embeddings for semantic game state queries",
        "Worker composition patterns: routing, fan-out, and aggregation",
    ],
    "maritime": [
        "Modeling realistic fish population dynamics: logistic growth and carrying capacity",
        "Tension-based fishing mechanics: spring physics and line stress modeling",
        "Maritime economy design: inflation controls and currency sinks",
        "Weather system integration: how environmental state affects gameplay loops",
        "Vessel physics: buoyancy, drag, and propulsion modeling for boat gameplay",
        "Harbor economy simulation: supply, demand, and price discovery",
        "Migration patterns: how fish movement creates emergent gameplay",
        "Seasonal variation in fishing game economies",
    ],
    "cognition": [
        "Embedding space geometry: why cosine similarity works and when it fails",
        "Cascade routing: optimizing the local/cloud decision boundary",
        "Confidence calibration in reflex systems: avoiding overconfidence traps",
        "Prompt engineering for small models: what fits in 2B parameters",
        "Situation signature design: balancing specificity and generalization",
        "Temporal pattern mining: turning rhythm into queryable knowledge",
        "Self-improvement loops: avoiding reward hacking and confirmation bias",
        "Vector database selection: sqlite-vec vs Vectorize vs FAISS",
        "Asymmetric trust scoring: why fast learning is dangerous in noisy domains",
        "LoRA fine-tuning: selecting training data that improves without narrowing",
    ],
}


# ─── HTTP Utilities ────────────────────────────────────────────

class DistillationError(Exception):
    """Base exception for distillation loop failures."""
    pass


class TeacherUnavailable(DistillationError):
    """GLM API is unavailable after all retries."""
    pass


class StudentUnavailable(DistillationError):
    """Ollama is unavailable after all retries."""
    pass


class EmptyResponse(DistillationError):
    """API returned an empty response."""
    pass


def _fleet_gw_module():
    """Lazily import the Fleet Gateway shim. Returns the module or None.

    Import is deferred (and failures are never cached) so that importing
    distillation_loop always succeeds even if the shim is absent — fail-open
    applies to wiring, not just requests. A missing shim is retried on the
    next call so it can be picked up if it appears later.
    """
    if _fleet_gw_cache:
        return _fleet_gw_cache[0]
    if not GATEWAY_ENABLED:
        return None
    try:
        if str(FLEET_GW_CLIENT_DIR) not in sys.path:
            sys.path.insert(0, str(FLEET_GW_CLIENT_DIR))
        import fleet_gw
        _fleet_gw_cache.append(fleet_gw)
        return fleet_gw
    except Exception:
        return None


def _gateway_route(url: str) -> tuple[str, str] | None:
    """Map a direct vendor URL to (provider, gateway_path) for fleet_gw.post.

    Only OpenAI-compatible chat/completions endpoints are routed through the
    gateway. Ollama's native /api/chat is deliberately NOT routed: it has a
    different payload shape ("options") AND response shape ({"message": ...}
    vs {"choices": [...]}) — proxying it through an OpenAI-compatible gateway
    would corrupt stage_student(). It stays on curl.
    """
    u = url.lower()
    if any(h in u for h in ("api.z.ai", "bigmodel.cn", "zhipuai")):
        return "zai", "/v1/chat/completions"
    if "api.deepseek.com" in u:
        return "deepseek", "/v1/chat/completions"
    if "api.deepinfra.com" in u:
        return "deepinfra", "/v1/chat/completions"
    return None


def _curl_post_json(
    url: str,
    headers: dict[str, str],
    data: dict[str, Any],
    timeout: int = 30,
    retries: int = 3,
    backoff_base: float = 2.0,
) -> dict[str, Any]:
    """
    POST JSON with retry and exponential backoff — gateway-first.

    Phase 3 (first Fleet Gateway consumer): when the URL maps to a known
    cloud provider and the gateway is reachable, the POST goes through
    fleet_gw.post() (which itself fails open to a direct vendor call with
    its own env keys). On ANY gateway-side failure — shim missing, gateway
    down, unknown URL, exception, non-dict response — we fall through to
    the original curl subprocess path, preserving the exact return
    contract every existing caller relies on:

    Returns the parsed JSON response, or {"error": ...} if all retries fail.
    """
    gw = _fleet_gw_module()
    if gw is not None:
        route = _gateway_route(url)
        if route is not None:
            provider, gw_path = route
            try:
                resp = gw.post(provider, gw_path, data)
                if isinstance(resp, dict):
                    return resp
            except Exception:
                pass  # fail open — curl path below
    return _curl_post_json_direct(url, headers, data, timeout, retries, backoff_base)


def _curl_post_json_direct(
    url: str,
    headers: dict[str, str],
    data: dict[str, Any],
    timeout: int = 30,
    retries: int = 3,
    backoff_base: float = 2.0,
) -> dict[str, Any]:
    """
    POST JSON via curl subprocess with retry and exponential backoff.

    Retries on:
      - Network errors (curl exit code != 0)
      - HTTP 429 (rate limit) or 5xx (server error)
      - JSON parse errors
      - Timeouts

    Returns the parsed JSON response, or {"error": ...} if all retries fail.
    """
    last_error = ""

    for attempt in range(1, retries + 1):
        cmd = [
            "curl", "-s", "-X", "POST", url,
            "--connect-timeout", str(timeout),
            "--max-time", str(timeout + 10),
            "-H", "Content-Type: application/json",
            "-w", "\n%{http_code}",  # Append HTTP status code
        ]
        for key, val in headers.items():
            cmd.extend(["-H", f"{key}: {val}"])
        cmd.extend(["-d", json.dumps(data)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 20,
            )

            if result.returncode != 0:
                last_error = f"curl exit {result.returncode}: {result.stderr.strip()}"
                if attempt < retries:
                    wait = backoff_base * (2 ** (attempt - 1))
                    time.sleep(min(wait, 30))
                continue

            # Split response body and HTTP status code
            raw = result.stdout.strip()
            lines = raw.rsplit("\n", 1)
            if len(lines) == 2:
                body, http_code_str = lines
            else:
                body, http_code_str = raw, "0"

            try:
                http_code = int(http_code_str)
            except ValueError:
                http_code = 0

            # Handle rate limiting and server errors with retry
            if http_code == 429 or 500 <= http_code < 600:
                retry_after = 5
                # Parse Retry-After from headers if present (simplified)
                last_error = f"HTTP {http_code} from server"
                if attempt < retries:
                    wait = max(retry_after, backoff_base * (2 ** (attempt - 1)))
                    time.sleep(min(wait, 60))
                continue

            # HTTP 4xx errors (except 429) are not retried
            if 400 <= http_code < 500 and http_code != 429:
                return {"error": f"HTTP {http_code}: {body[:500]}", "_http_code": http_code}

            # Parse JSON response
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                last_error = f"JSON decode error: {body[:200]}"
                if attempt < retries:
                    wait = backoff_base * (2 ** (attempt - 1))
                    time.sleep(min(wait, 30))
                continue

        except subprocess.TimeoutExpired:
            last_error = f"Request timed out after {timeout + 20}s"
            if attempt < retries:
                wait = backoff_base * (2 ** (attempt - 1))
                time.sleep(min(wait, 30))
        except Exception as e:
            last_error = str(e)
            if attempt < retries:
                wait = backoff_base * (2 ** (attempt - 1))
                time.sleep(min(wait, 30))

    return {"error": f"All {retries} attempts failed: {last_error}"}


def _timestamp() -> str:
    """ISO timestamp for filenames and logs."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ─── Code Loading ──────────────────────────────────────────────

def load_task_code(task: dict[str, str]) -> str:
    """Load the source code referenced by a task."""
    repo = Path(task.get("repo", "."))
    code_path = repo / task["code"]
    try:
        return code_path.read_text(encoding="utf-8")[:4000]  # Cap at 4k chars
    except (OSError, FileNotFoundError):
        return f"(could not load {code_path})"


# ─── Quality Scoring ───────────────────────────────────────────

def score_response(text: str) -> dict[str, float]:
    """
    Score a response on 4 dimensions (adapted from QualityScorer).

    - novelty: unique bigrams / total bigrams
    - specificity: concrete details (numbers, names, technical terms)
    - engagement: sentence variety and question/action words
    - spatial_awareness: structural references and system relationships
    """
    text_lower = text.lower()
    words = text_lower.split()
    if len(words) < 5:
        return {"novelty": 0.1, "specificity": 0.1, "engagement": 0.1, "spatial": 0.1}

    # Novelty: unique bigrams
    bigrams = list(zip(words[:-1], words[1:]))
    if bigrams:
        unique_bigrams = len(set(bigrams))
        novelty = min(1.0, unique_bigrams / len(bigrams))
    else:
        novelty = 0.1

    # Specificity: numbers, technical terms, proper nouns
    numbers = len(re.findall(r"\b\d+\.?\d*\b", text))
    tech_terms = len(re.findall(
        r"\b(?:function|table|module|server|client|remote|event|"
        r"loop|queue|cache|threshold|vector|embedding|cascade|"
        r"reflex|confidence|policy|prompt|score|weight|param|"
        r"sqlite|worker|durable|schema|api|endpoint)\b",
        text_lower,
    ))
    specificity = min(1.0, (numbers + tech_terms) / max(1, len(sentences(text))))

    # Engagement: questions, action verbs, sentence length variety
    questions = text.count("?")
    action_verbs = len(re.findall(
        r"\b(?:should|could|would|improve|optimize|add|remove|"
        r"replace|refactor|implement|design|use|avoid|consider)\b",
        text_lower,
    ))
    sents = sentences(text)
    if len(sents) > 1:
        lengths = [len(s.split()) for s in sents]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        variety = min(1.0, (variance ** 0.5) / 10)
    else:
        variety = 0.1
    engagement = min(1.0, (questions + action_verbs) / 10 + variety * 0.5)

    # Spatial awareness: structural references
    structural = len(re.findall(
        r"\b(?:between|inside|above|below|before|after|around|"
        r"through|across|within|alongside|nested|parent|child|"
        r"layer|tier|level|component|module|system|subsystem)\b",
        text_lower,
    ))
    spatial = min(1.0, structural / 8)

    return {
        "novelty": round(novelty, 3),
        "specificity": round(specificity, 3),
        "engagement": round(engagement, 3),
        "spatial": round(spatial, 3),
    }


def sentences(text: str) -> list[str]:
    """Split text into sentences."""
    parts = re.split(r"[.!?]+", text)
    return [s.strip() for s in parts if s.strip()]


def composite_score(scores: dict[str, float]) -> float:
    """Weighted composite (matches QualityScorer weights)."""
    return (
        scores.get("novelty", 0) * 0.30
        + scores.get("specificity", 0) * 0.25
        + scores.get("engagement", 0) * 0.20
        + scores.get("spatial", 0) * 0.25
    )


# ─── Hash Embedding (from slackwater-cognition) ────────────────

def embed_hash(text: str, dim: int = 384) -> list[float]:
    """Lightweight hash embedding for reflex storage (no external deps)."""
    import math

    text = text.lower().strip()
    words = text.split()
    vec = [0.0] * dim

    # Trigram features
    padded = f"^{text}$"
    for i in range(len(padded) - 2):
        trigram = padded[i : i + 3]
        h = hashlib.sha256(trigram.encode()).digest()
        idx = int.from_bytes(h[:4], "big") % (dim * 2 // 3)
        weight = 0.5 + (int.from_bytes(h[4:8], "big") / 0xFFFFFFFF) * 0.5
        vec[idx] += weight

    # Word features (filtered)
    stopwords = frozenset({"the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "for", "it", "that", "with"})
    for word in words:
        w = word.strip(".,!?;:\"'()[]{}-").lower()
        if not w or w in stopwords:
            continue
        h = hashlib.sha256(w.encode()).digest()
        idx = (int.from_bytes(h[:4], "big") % (dim // 3)) + (dim * 2 // 3)
        vec[idx] += 1.0

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


# ─── STAGE 1: TEACHER ──────────────────────────────────────────

TEACHER_SYSTEM_PROMPT = """You are an expert teacher. The student is a small local model (2B params).

Produce a concise, actionable lesson about the given topic. Focus on practical wisdom the student doesn't know yet — patterns, gotchas, best practices.

Rules:
- Be specific. Name actual patterns, actual numbers, actual tradeoffs.
- No filler. Every sentence should teach something.
- 200-400 words. Short enough for the student to ingest in one go.
- Use code snippets when they clarify (but keep them tiny).
- Structure: 3-5 numbered insights, each with a one-line summary and a paragraph of explanation.
- End with a "Key takeaway" line that distills the most important point.
"""


def stage_teacher(
    domain: str,
    topic: str,
    iteration: int,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    STAGE 1: Call GLM to generate a teaching prompt about the topic.

    Returns dict with:
      - topic, lesson, raw_response, timestamp, iteration
      - error (optional): present if the teacher failed permanently

    Raises TeacherUnavailable if all retries are exhausted and no fallback works.
    """
    user_msg = (
        f"Domain: {domain}\n"
        f"Topic: {topic}\n\n"
        f"Teach this topic as if the student will immediately apply it to "
        f"reviewing and improving real code. Focus on what a 2B parameter "
        f"model would likely get wrong without this knowledge."
    )

    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": TEACHER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }
    api_key = GLM_API_KEY or os.environ.get("GLM_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"}

    result = _curl_post_json(GLM_API_URL, headers, payload, timeout=45, retries=max_retries)

    if "error" in result:
        # All retries exhausted. Record the error but don't crash.
        error_msg = result["error"]
        artifact = {
            "topic": topic,
            "domain": domain,
            "lesson": "",
            "iteration": iteration,
            "timestamp": _timestamp(),
            "model": GLM_MODEL,
            "token_usage": {},
            "error": error_msg,
            "success": False,
        }
        fname = f"{domain}_iter{iteration:04d}_teacher.json"
        (TEACHER_DIR / fname).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return artifact

    choices = result.get("choices", [])
    lesson = choices[0].get("message", {}).get("content", "") if choices else ""

    # Check for empty response
    if not lesson or not lesson.strip():
        artifact = {
            "topic": topic,
            "domain": domain,
            "lesson": "",
            "iteration": iteration,
            "timestamp": _timestamp(),
            "model": GLM_MODEL,
            "token_usage": result.get("usage", {}),
            "error": "Empty response from teacher",
            "success": False,
        }
        fname = f"{domain}_iter{iteration:04d}_teacher.json"
        (TEACHER_DIR / fname).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return artifact

    artifact = {
        "topic": topic,
        "domain": domain,
        "lesson": lesson,
        "iteration": iteration,
        "timestamp": _timestamp(),
        "model": GLM_MODEL,
        "token_usage": result.get("usage", {}),
        "success": True,
    }

    # Save artifact
    fname = f"{domain}_iter{iteration:04d}_teacher.json"
    (TEACHER_DIR / fname).write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    return artifact


# ─── STAGE 2: STUDENT ──────────────────────────────────────────

def stage_student(
    teacher_artifact: dict[str, Any],
    task: dict[str, str],
    code: str,
    use_teaching: bool,
    iteration: int,
    domain: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    STAGE 2: Feed the teaching to Granite (or run baseline without it).

    If use_teaching is True, the prompt includes the teacher's lesson.
    If False, it's a baseline response without the teaching.

    Includes watchdog integration: if Ollama is down, attempt recovery
    before giving up.
    """
    if use_teaching:
        lesson_text = teacher_artifact.get('lesson', '(no lesson)')
        prompt = (
            f"A teacher explains:\n\n{lesson_text}\n\n"
            f"---\n\n"
            f"Now apply this to the following real task.\n\n"
            f"Task: {task['task']}\n\n"
            f"Code to review:\n```\n{code[:2000]}\n```\n\n"
            f"Show your work. Apply the lesson's insights specifically."
        )
    else:
        prompt = (
            f"Task: {task['task']}\n\n"
            f"Code to review:\n```\n{code[:2000]}\n```\n\n"
            f"Provide your analysis and suggestions."
        )

    # Call Ollama with retries
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.5, "top_p": 0.9},
    }

    result = _curl_post_json(
        "http://localhost:11434/api/chat", {}, payload,
        timeout=90, retries=max_retries,
    )

    if "error" in result:
        # Ollama is likely down. Try watchdog recovery.
        try:
            from watchdog import ensure_healthy
            if ensure_healthy(max_attempts=3):
                # Retry after recovery
                result = _curl_post_json(
                    "http://localhost:11434/api/chat", {}, payload,
                    timeout=90, retries=2,
                )
        except ImportError:
            pass  # Watchdog not available, continue with error

        if "error" in result:
            response = f"(Student error after recovery attempt: {result['error']})"
            success = False
        else:
            msg = result.get("message", {})
            response = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            success = True
    else:
        msg = result.get("message", {})
        response = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        success = bool(response and response.strip())
        if not success:
            response = "(Empty response from student model)"

    label = "taught" if use_teaching else "baseline"

    artifact = {
        "response": response,
        "label": label,
        "domain": domain,
        "iteration": iteration,
        "task": task["task"],
        "code_file": task["code"],
        "timestamp": _timestamp(),
        "eval_count": result.get("eval_count", 0),
        "eval_duration": result.get("eval_duration", 0),
        "success": success,
    }

    fname = f"{domain}_iter{iteration:04d}_{label}.json"
    (STUDENT_DIR / fname).write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    return artifact


# ─── STAGE 3: EVALUATE ─────────────────────────────────────────

def stage_evaluate(
    baseline_artifact: dict[str, Any],
    taught_artifact: dict[str, Any],
    domain: str,
    iteration: int,
) -> dict[str, Any]:
    """
    STAGE 3: Score both responses and compute the delta.

    Positive delta = teaching helped. Negative = it didn't.
    """
    baseline_scores = score_response(baseline_artifact["response"])
    taught_scores = score_response(taught_artifact["response"])

    baseline_composite = composite_score(baseline_scores)
    taught_composite = composite_score(taught_scores)
    delta = taught_composite - baseline_composite

    # Per-dimension deltas
    dim_deltas = {}
    for dim in ["novelty", "specificity", "engagement", "spatial"]:
        dim_deltas[dim] = round(taught_scores[dim] - baseline_scores[dim], 3)

    artifact = {
        "domain": domain,
        "iteration": iteration,
        "baseline_scores": baseline_scores,
        "taught_scores": taught_scores,
        "baseline_composite": round(baseline_composite, 3),
        "taught_composite": round(taught_composite, 3),
        "delta": round(delta, 3),
        "dimension_deltas": dim_deltas,
        "teaching_helped": delta > 0,
        "timestamp": _timestamp(),
    }

    fname = f"{domain}_iter{iteration:04d}_eval.json"
    (EVAL_DIR / fname).write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    return artifact


# ─── STAGE 4: DISTILL ──────────────────────────────────────────

def stage_distill(
    teacher_artifact: dict[str, Any],
    eval_artifact: dict[str, Any],
    domain: str,
    iteration: int,
) -> dict[str, Any]:
    """
    STAGE 4: If teaching helped (positive delta), compile into a .nail reflex.

    The reflex allows Granite to reproduce the good behavior WITHOUT the teacher.
    """
    if not eval_artifact["teaching_helped"]:
        return {
            "compiled": False,
            "reason": f"Delta was negative ({eval_artifact['delta']:.3f}), skipping distillation",
            "domain": domain,
            "iteration": iteration,
        }

    # Build the reflex
    lesson = teacher_artifact["lesson"]
    topic = teacher_artifact["topic"]

    # Extract key insights from the lesson (first 500 chars for the reflex)
    lesson_excerpt = lesson[:500]

    # Create a situation signature for matching
    situation = f"domain={domain} topic={topic[:60]}"

    # Embed the situation
    embedding = embed_hash(situation)

    # Generate reflex ID
    raw = f"{domain}|{topic}|{iteration}|{teacher_artifact['timestamp']}"
    nail_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    # Confidence: based on how much the teaching helped
    # Map delta (typically 0.0 - 0.3) to confidence (0.4 - 0.8)
    delta = eval_artifact["delta"]
    confidence = min(0.85, 0.40 + delta * 2.0)

    nail = {
        "id": nail_id,
        "domain": domain,
        "match_key": situation,
        "situation": situation,
        "topic": topic,
        "lesson_excerpt": lesson_excerpt,
        "full_lesson_file": f"teacher/{domain}_iter{iteration:04d}_teacher.json",
        "action": f"apply_{domain}_wisdom",
        "outcome": "good",
        "outcome_quality": round(eval_artifact["taught_composite"], 3),
        "delta": round(delta, 3),
        "confidence": round(confidence, 3),
        "embedding": embedding,
        "metadata": {
            "iteration": iteration,
            "timestamp": teacher_artifact["timestamp"],
            "source": "distillation_loop",
            "domain": domain,
            "model": OLLAMA_MODEL,
            "scores": eval_artifact["taught_scores"],
        },
    }

    # Save locally
    nail_path = REFLEX_DIR / f"{nail_id}.nail.json"
    nail_path.write_text(json.dumps(nail, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also maintain a domain-specific reflex index
    index_path = REFLEX_DIR / f"{domain}_index.json"
    index: list[dict[str, Any]] = []
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    index.append({
        "id": nail_id,
        "topic": topic,
        "delta": round(delta, 3),
        "confidence": round(confidence, 3),
        "iteration": iteration,
    })
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "compiled": True,
        "nail_id": nail_id,
        "confidence": round(confidence, 3),
        "delta": round(delta, 3),
        "path": str(nail_path),
        "domain": domain,
        "iteration": iteration,
    }


# ─── STAGE 5: UPDATE PROMPT ────────────────────────────────────

# Track consistency per domain for promotion gating
_domain_history: dict[str, list[bool]] = {}


def stage_update_prompt(
    teacher_artifact: dict[str, Any],
    eval_artifact: dict[str, Any],
    domain: str,
    iteration: int,
    promote_threshold: int = 3,
) -> dict[str, Any]:
    """
    STAGE 5: If teaching consistently helps across multiple trials,
    promote it to a permanent system prompt directive.

    Promotes when: N consecutive positive deltas (default 3).
    """
    helped = eval_artifact["teaching_helped"]

    # Track history
    if domain not in _domain_history:
        _domain_history[domain] = []
    _domain_history[domain].append(helped)

    # Keep last 10
    if len(_domain_history[domain]) > 10:
        _domain_history[domain] = _domain_history[domain][-10:]

    # Check for promotion (N consecutive positives)
    recent = _domain_history[domain][-promote_threshold:]
    consecutive_positives = sum(recent)

    if len(recent) >= promote_threshold and consecutive_positives == promote_threshold:
        # Promote!
        directive = (
            f"[{domain.upper()}] Apply this wisdom consistently: "
            f"{teacher_artifact['topic']}. "
            f"Key insight: {teacher_artifact['lesson'][:200].strip()}"
        )

        # Version the prompt
        version_path = PROMPT_DIR / f"{domain}_versions.jsonl"
        versions: list[dict[str, Any]] = []
        if version_path.exists():
            try:
                versions = [json.loads(line) for line in version_path.read_text().strip().split("\n") if line.strip()]
            except (json.JSONDecodeError, OSError):
                pass

        version_num = len(versions) + 1
        version_entry = {
            "version": f"v{version_num}",
            "domain": domain,
            "directive": directive,
            "topic": teacher_artifact["topic"],
            "iteration": iteration,
            "delta": eval_artifact["delta"],
            "timestamp": _timestamp(),
            "consecutive_positives": consecutive_positives,
        }
        versions.append(version_entry)

        with open(version_path, "w", encoding="utf-8") as f:
            for v in versions:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")

        # Record in VERSION_HISTORY.jsonl
        history_path = PROMPT_DIR / "VERSION_HISTORY.jsonl"
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(version_entry, ensure_ascii=False) + "\n")

        # Reset the streak to avoid re-promoting the same thing
        _domain_history[domain] = []

        return {
            "updated": True,
            "version": f"v{version_num}",
            "directive": directive[:100] + "...",
            "domain": domain,
            "iteration": iteration,
        }

    return {
        "updated": False,
        "domain": domain,
        "consecutive_positives": consecutive_positives,
        "needed": promote_threshold,
        "iteration": iteration,
    }


# ─── The Full Loop ─────────────────────────────────────────────

def run_iteration(domain: str, iteration: int) -> dict[str, Any]:
    """
    Run all 5 stages of the distillation loop for one iteration.

    Returns a summary dict for the CLI to print.
    Handles partial failures gracefully — if the teacher fails,
    the iteration is skipped with a recorded error but the loop continues.
    """
    topics = TEACHING_TOPICS.get(domain, TEACHING_TOPICS["cognition"])
    tasks = TASK_SOURCES.get(domain, TASK_SOURCES["cognition"])

    topic = topics[iteration % len(topics)]
    task = tasks[iteration % len(tasks)]
    code = load_task_code(task)

    # STAGE 1: Teacher generates lesson
    teacher = stage_teacher(domain, topic, iteration)

    # If teacher failed entirely, skip this iteration but don't crash
    if not teacher.get("success", False):
        return {
            "domain": domain,
            "iteration": iteration,
            "topic": topic,
            "task": task["task"][:80],
            "baseline_score": 0.0,
            "taught_score": 0.0,
            "delta": 0.0,
            "teaching_helped": False,
            "reflex_compiled": False,
            "reflex_id": "",
            "prompt_updated": False,
            "prompt_version": "",
            "consecutive_positives": 0,
            "error": teacher.get("error", "teacher_failed"),
            "success": False,
        }

    # STAGE 2a: Student baseline (no teaching)
    baseline = stage_student(teacher, task, code, use_teaching=False, iteration=iteration, domain=domain)

    # STAGE 2b: Student with teaching
    taught = stage_student(teacher, task, code, use_teaching=True, iteration=iteration, domain=domain)

    # If student failed, record but continue with empty scores
    if not baseline.get("success", False) or not taught.get("success", False):
        return {
            "domain": domain,
            "iteration": iteration,
            "topic": topic,
            "task": task["task"][:80],
            "baseline_score": 0.0,
            "taught_score": 0.0,
            "delta": 0.0,
            "teaching_helped": False,
            "reflex_compiled": False,
            "reflex_id": "",
            "prompt_updated": False,
            "prompt_version": "",
            "consecutive_positives": 0,
            "error": "student_model_unavailable",
            "success": False,
        }

    # STAGE 3: Evaluate the delta
    evaluation = stage_evaluate(baseline, taught, domain, iteration)

    # STAGE 4: Distill into reflex if teaching helped
    distillation = stage_distill(teacher, evaluation, domain, iteration)

    # STAGE 5: Update prompt if consistently helpful
    prompt_update = stage_update_prompt(teacher, evaluation, domain, iteration)

    return {
        "domain": domain,
        "iteration": iteration,
        "topic": topic,
        "task": task["task"][:80],
        "baseline_score": evaluation["baseline_composite"],
        "taught_score": evaluation["taught_composite"],
        "delta": evaluation["delta"],
        "teaching_helped": evaluation["teaching_helped"],
        "reflex_compiled": distillation["compiled"],
        "reflex_id": distillation.get("nail_id", ""),
        "prompt_updated": prompt_update["updated"],
        "prompt_version": prompt_update.get("version", ""),
        "consecutive_positives": prompt_update.get("consecutive_positives", 0),
        "success": True,
    }


def save_run_log(summaries: list[dict[str, Any]], domain: str) -> Path:
    """Save the full run log."""
    log_path = LOG_DIR / f"{domain}_run_{_timestamp()}.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for s in summaries:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return log_path


# ─── Stats ─────────────────────────────────────────────────────

def compute_stats(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics for a run."""
    if not summaries:
        return {}

    # Separate successful iterations from failed ones
    successful = [s for s in summaries if s.get("success", True)]
    failed = [s for s in summaries if not s.get("success", True)]

    if not successful:
        return {
            "total_iterations": len(summaries),
            "successful_iterations": 0,
            "failed_iterations": len(failed),
            "errors": [s.get("error", "unknown") for s in failed],
        }

    deltas = [s["delta"] for s in successful]
    helped = [s for s in successful if s["teaching_helped"]]
    compiled = [s for s in successful if s["reflex_compiled"]]
    promoted = [s for s in successful if s["prompt_updated"]]

    return {
        "total_iterations": len(summaries),
        "successful_iterations": len(successful),
        "failed_iterations": len(failed),
        "teaching_helped_count": len(helped),
        "help_rate": round(len(helped) / len(successful), 3),
        "reflexes_compiled": len(compiled),
        "promotions": len(promoted),
        "avg_delta": round(sum(deltas) / len(deltas), 3),
        "max_delta": round(max(deltas), 3),
        "min_delta": round(min(deltas), 3),
        "positive_iterations": [s["iteration"] for s in helped],
        "errors": [s.get("error", "unknown") for s in failed],
    }
