#!/usr/bin/env python3
"""
modes/common.py — Shared utilities for all modes.

Provides LLM calling and URL fetching utilities used by the specialized modes.
All HTTP is done via subprocess+curl (Cloudflare blocks Python libraries).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from core.thinker import _curl_post_json


# ─── LLM Call Helper ────────────────────────────────────────────

def llm_call(
    messages: list[dict[str, str]],
    api_key: str = "",
    api_url: str = "https://api.z.ai/api/paas/v4/chat/completions",
    model: str = "glm-4-flash",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    deepseek_api_key: str = "",
    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions",
    deepseek_model: str = "deepseek-chat",
) -> str:
    """Make an LLM API call, trying GLM first then DeepSeek.

    Returns the assistant's response text.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    # Try GLM first
    if api_key:
        try:
            result = _curl_post_json(api_url, payload,
                                    headers={"Authorization": f"Bearer {api_key}"})
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    # Fallback to DeepSeek
    if deepseek_api_key:
        payload["model"] = deepseek_model
        try:
            result = _curl_post_json(deepseek_api_url, payload,
                                    headers={"Authorization": f"Bearer {deepseek_api_key}"})
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    return "[LLM call failed — no available backend]"


# ─── URL Fetching ───────────────────────────────────────────────

def fetch_url(url: str, max_chars: int = 10000, timeout: int = 15) -> str:
    """Fetch URL content using curl. Returns extracted text.

    Uses a simple HTML-to-text extraction.
    """
    cmd = ["curl", "-s", "-L", "--max-time", str(timeout),
           "-H", "User-Agent: Mozilla/5.0 (compatible; ThoughtAmplifier/1.0)",
           url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        html = result.stdout
    except Exception as e:
        return f"[Fetch error: {e}]"

    return html_to_text(html, max_chars)


def fetch_markdown(url: str, max_chars: int = 10000, timeout: int = 15) -> str:
    """Fetch URL and convert to markdown-ish text."""
    cmd = ["curl", "-s", "-L", "--max-time", str(timeout),
           "-H", "User-Agent: Mozilla/5.0 (compatible; ThoughtAmplifier/1.0)",
           url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        text = result.stdout
    except Exception as e:
        return f"[Fetch error: {e}]"

    # If it looks like HTML, convert
    if "<html" in text.lower() or "<body" in text.lower():
        text = html_to_text(text, max_chars)
    else:
        text = text[:max_chars]

    return text


def html_to_text(html: str, max_chars: int = 10000) -> str:
    """Simple HTML to text conversion."""
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements
    html = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n## \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', html)

    # Decode entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&apos;', "'")

    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()[:max_chars]


# ─── Content Hashing ────────────────────────────────────────────

def content_hash(text: str) -> str:
    """Simple hash of text content for change detection."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
