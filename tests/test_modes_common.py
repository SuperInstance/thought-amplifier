"""
Tests for modes/common.py — shared utilities for all modes.

Covers:
  - html_to_text() HTML stripping and conversion
  - content_hash() consistency
  - llm_call() with mocked backends
  - fetch_url / fetch_markdown with mocked curl
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modes.common import html_to_text, content_hash, llm_call, fetch_url, fetch_markdown


class TestHtmlToText(unittest.TestCase):

    def test_strips_script_tags(self):
        html = "<script>alert('xss')</script><p>Hello</p>"
        text = html_to_text(html)
        self.assertNotIn("alert", text)
        self.assertIn("Hello", text)

    def test_strips_style_tags(self):
        html = "<style>body { color: red; }</style><p>Content</p>"
        text = html_to_text(html)
        self.assertNotIn("color", text)
        self.assertIn("Content", text)

    def test_strips_nav_and_footer(self):
        html = "<nav>Menu</nav><p>Main</p><footer>Copyright</footer>"
        text = html_to_text(html)
        self.assertNotIn("Menu", text)
        self.assertNotIn("Copyright", text)
        self.assertIn("Main", text)

    def test_converts_headings(self):
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        text = html_to_text(html)
        self.assertIn("## Title", text)
        self.assertIn("## Subtitle", text)

    def test_converts_paragraphs(self):
        html = "<p>Para one.</p><p>Para two.</p>"
        text = html_to_text(html)
        self.assertIn("Para one.", text)
        self.assertIn("Para two.", text)

    def test_converts_line_breaks(self):
        html = "Line 1<br>Line 2<br/>Line 3"
        text = html_to_text(html)
        self.assertIn("\n", text)

    def test_converts_list_items(self):
        html = "<ul><li>One</li><li>Two</li></ul>"
        text = html_to_text(html)
        self.assertIn("• One", text)
        self.assertIn("• Two", text)

    def test_converts_links(self):
        html = '<a href="http://example.com">Click here</a>'
        text = html_to_text(html)
        self.assertIn("Click here", text)
        self.assertIn("http://example.com", text)

    def test_strips_remaining_tags(self):
        html = "<div><span>Text</span></div>"
        text = html_to_text(html)
        self.assertNotIn("<", text)
        self.assertIn("Text", text)

    def test_decodes_entities(self):
        html = "Hello &amp; goodbye &lt;tag&gt; &quot;quoted&quot;"
        text = html_to_text(html)
        self.assertIn("&", text)
        self.assertIn("<tag>", text)
        self.assertIn('"quoted"', text)

    def test_decodes_nbsp(self):
        html = "a&nbsp;b"
        text = html_to_text(html)
        self.assertIn("a b", text)

    def test_cleans_whitespace(self):
        html = "<p>Text</p>\n\n\n\n<p>More</p>"
        text = html_to_text(html)
        self.assertNotIn("\n\n\n", text)

    def test_max_chars_limit(self):
        html = "<p>" + "x" * 5000 + "</p>"
        text = html_to_text(html, max_chars=100)
        self.assertLessEqual(len(text), 100)

    def test_empty_html(self):
        text = html_to_text("")
        self.assertEqual(text, "")

    def test_plain_text_passes_through(self):
        text = html_to_text("Just plain text")
        self.assertIn("Just plain text", text)


class TestContentHash(unittest.TestCase):

    def test_consistent_hash(self):
        h1 = content_hash("test content")
        h2 = content_hash("test content")
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        h1 = content_hash("content a")
        h2 = content_hash("content b")
        self.assertNotEqual(h1, h2)

    def test_hash_length(self):
        h = content_hash("test")
        self.assertEqual(len(h), 16)

    def test_unicode_content(self):
        h = content_hash("Hello 世界 🐟")
        self.assertEqual(len(h), 16)

    def test_empty_string(self):
        h = content_hash("")
        self.assertEqual(len(h), 16)


class TestLlmCall(unittest.TestCase):

    def test_glm_success(self):
        with patch("modes.common._curl_post_json") as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": "LLM response"}}]}
            result = llm_call(
                [{"role": "user", "content": "hi"}],
                api_key="test-key",
            )
            self.assertEqual(result, "LLM response")

    def test_glm_failure_fallback_to_deepseek(self):
        with patch("modes.common._curl_post_json") as mock_post:
            mock_post.side_effect = [
                RuntimeError("GLM down"),
                {"choices": [{"message": {"content": "DS response"}}]},
            ]
            result = llm_call(
                [{"role": "user", "content": "hi"}],
                api_key="glm-key",
                deepseek_api_key="ds-key",
            )
            self.assertEqual(result, "DS response")

    def test_no_keys_returns_failure_message(self):
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="",
            deepseek_api_key="",
        )
        self.assertIn("failed", result.lower())

    def test_deepseek_only(self):
        with patch("modes.common._curl_post_json") as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": "DS only"}}]}
            result = llm_call(
                [{"role": "user", "content": "hi"}],
                api_key="",
                deepseek_api_key="ds-key",
            )
            self.assertEqual(result, "DS only")

    def test_both_fail_returns_failure(self):
        with patch("modes.common._curl_post_json") as mock_post:
            mock_post.side_effect = RuntimeError("all down")
            result = llm_call(
                [{"role": "user", "content": "hi"}],
                api_key="k1",
                deepseek_api_key="k2",
            )
            self.assertIn("failed", result.lower())


class TestFetchUrl(unittest.TestCase):

    @patch("subprocess.run")
    def test_fetch_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="<p>Hello world</p>", stderr="")
        result = fetch_url("http://example.com")
        self.assertIn("Hello world", result)

    @patch("subprocess.run")
    def test_fetch_error(self, mock_run):
        mock_run.side_effect = RuntimeError("network error")
        result = fetch_url("http://example.com")
        self.assertIn("Fetch error", result)

    @patch("subprocess.run")
    def test_fetch_max_chars(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="<p>" + "x" * 5000 + "</p>", stderr="")
        result = fetch_url("http://example.com", max_chars=100)
        self.assertLessEqual(len(result), 100)

    @patch("subprocess.run")
    def test_fetch_markdown_html(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="<html><body><p>Markdown test</p></body></html>",
            stderr="")
        result = fetch_markdown("http://example.com")
        self.assertIn("Markdown test", result)

    @patch("subprocess.run")
    def test_fetch_markdown_plain_text(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Just plain text", stderr="")
        result = fetch_markdown("http://example.com")
        self.assertIn("Just plain text", result)


if __name__ == "__main__":
    unittest.main()
