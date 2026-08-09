#!/usr/bin/env python3
"""
Tests for modes/common.py — HTML processing, URL fetching, content hashing,
and LLM call fallback logic.
"""

import pytest
import hashlib
from unittest.mock import patch, MagicMock
from modes.common import (
    html_to_text, content_hash, fetch_url, fetch_markdown, llm_call
)


# ─── html_to_text tests ────────────────────────────────────────

class TestHtmlToText:
    def test_strips_script_tags(self):
        html = '<script>alert("xss")</script><p>Hello</p>'
        result = html_to_text(html)
        assert "alert" not in result
        assert "Hello" in result

    def test_strips_style_tags(self):
        html = '<style>body { color: red; }</style><p>Content</p>'
        result = html_to_text(html)
        assert "color" not in result
        assert "Content" in result

    def test_strips_nav_and_footer(self):
        html = '<nav>Menu Item</nav><p>Main</p><footer>Copyright</footer>'
        result = html_to_text(html)
        assert "Menu Item" not in result
        assert "Copyright" not in result
        assert "Main" in result

    def test_converts_headings_to_markdown(self):
        html = '<h1>Title</h1><h2>Subtitle</h2><p>Body</p>'
        result = html_to_text(html)
        assert "## Title" in result
        assert "## Subtitle" in result

    def test_converts_paragraphs_with_double_newline(self):
        html = '<p>First</p><p>Second</p>'
        result = html_to_text(html)
        assert "First" in result
        assert "Second" in result
        assert "\n\n" in result

    def test_converts_br_to_newline(self):
        html = '<p>Line1<br>Line2<br/>Line3</p>'
        result = html_to_text(html)
        assert "Line1" in result
        assert "Line2" in result
        assert "Line3" in result

    def test_converts_list_items(self):
        html = '<ul><li>Apple</li><li>Banana</li></ul>'
        result = html_to_text(html)
        assert "Apple" in result
        assert "Banana" in result
        assert "•" in result

    def test_converts_links_with_href(self):
        html = '<a href="https://example.com">Click here</a>'
        result = html_to_text(html)
        assert "Click here" in result
        assert "https://example.com" in result

    def test_strips_all_remaining_tags(self):
        html = '<div class="x"><span>Text</span></div>'
        result = html_to_text(html)
        assert "<div>" not in result
        assert "<span>" not in result
        assert "Text" in result

    def test_decodes_html_entities(self):
        html = '<p>&nbsp;Hello&nbsp;&amp;&nbsp;world&lt;/p&gt;</p>'
        result = html_to_text(html)
        assert "&nbsp;" not in result
        assert " " in result
        assert "&" in result

    def test_decodes_quotation_entities(self):
        html = '<p>She said &quot;hello&quot; &amp; &#39;hi&#39;</p>'
        result = html_to_text(html)
        assert '"hello"' in result
        assert "'hi'" in result

    def test_collapses_multiple_newlines(self):
        html = '<p>A</p><p>B</p><p>C</p><p>D</p><p>E</p>'
        result = html_to_text(html)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in result

    def test_collapses_multiple_spaces(self):
        html = '<p>Word     spacing</p>'
        result = html_to_text(html)
        assert "     " not in result

    def test_truncates_at_max_chars(self):
        html = '<p>' + 'A' * 500 + '</p>'
        result = html_to_text(html, max_chars=100)
        assert len(result) <= 100

    def test_empty_html_returns_empty(self):
        assert html_to_text('') == ''

    def test_plain_text_passes_through(self):
        result = html_to_text('Just text', max_chars=100)
        assert 'Just text' in result

    def test_nested_tags(self):
        html = '<div><div><div><p>Deep</p></div></div></div>'
        result = html_to_text(html)
        assert "Deep" in result
        assert "<div>" not in result

    def test_strips_comments(self):
        html = '<!-- comment --><p>Visible</p>'
        result = html_to_text(html)
        assert "Visible" in result
        assert "comment" not in result


# ─── content_hash tests ────────────────────────────────────────

class TestContentHash:
    def test_returns_hex_string(self):
        h = content_hash("test content")
        assert all(c in '0123456789abcdef' for c in h)

    def test_returns_16_chars(self):
        h = content_hash("test")
        assert len(h) == 16

    def test_same_input_same_hash(self):
        assert content_hash("hello") == content_hash("hello")

    def test_different_input_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_matches_sha256_prefix(self):
        text = "verify me"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        assert content_hash(text) == expected

    def test_empty_string(self):
        h = content_hash("")
        assert len(h) == 16

    def test_unicode_content(self):
        h = content_hash("héllo wörld 🌊")
        assert len(h) == 16


# ─── llm_call tests ────────────────────────────────────────────

class TestLlmCall:
    @patch('modes.common._curl_post_json')
    def test_glm_success(self, mock_curl):
        mock_curl.return_value = {"choices": [{"message": {"content": "GLM response"}}]}
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="test-key",
        )
        assert result == "GLM response"
        assert mock_curl.call_count == 1

    @patch('modes.common._curl_post_json')
    def test_falls_back_to_deepseek(self, mock_curl):
        # First call (GLM) raises, second (DeepSeek) succeeds
        mock_curl.side_effect = [Exception("GLM failed"),
                                 {"choices": [{"message": {"content": "DeepSeek response"}}]}]
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="glm-key",
            deepseek_api_key="ds-key",
        )
        assert result == "DeepSeek response"
        assert mock_curl.call_count == 2

    @patch('modes.common._curl_post_json')
    def test_returns_failure_message_when_no_keys(self, mock_curl):
        result = llm_call([{"role": "user", "content": "hi"}])
        assert "failed" in result.lower()
        assert mock_curl.call_count == 0

    @patch('modes.common._curl_post_json')
    def test_returns_failure_when_both_backends_fail(self, mock_curl):
        mock_curl.side_effect = [Exception("GLM"), Exception("DeepSeek")]
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="k1",
            deepseek_api_key="k2",
        )
        assert "failed" in result.lower()

    @patch('modes.common._curl_post_json')
    def test_trims_response_whitespace(self, mock_curl):
        mock_curl.return_value = {"choices": [{"message": {"content": "  trimmed  "}}]}
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="key",
        )
        assert result == "trimmed"

    @patch('modes.common._curl_post_json')
    def test_handles_empty_response(self, mock_curl):
        mock_curl.return_value = {"choices": [{}]}
        result = llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="key",
        )
        assert result == ""

    @patch('modes.common._curl_post_json')
    def test_uses_deepseek_model_on_fallback(self, mock_curl):
        mock_curl.side_effect = [Exception("GLM"),
                                 {"choices": [{"message": {"content": "ok"}}]}]
        llm_call(
            [{"role": "user", "content": "hi"}],
            api_key="k1",
            deepseek_api_key="k2",
            deepseek_model="deepseek-reasoner",
        )
        # Second call should use deepseek_model
        second_call_args = mock_curl.call_args_list[1]
        # The payload is passed positionally
        payload = second_call_args[0][1]
        assert payload["model"] == "deepseek-reasoner"


# ─── fetch_url tests ───────────────────────────────────────────

class TestFetchUrl:
    @patch('modes.common.subprocess.run')
    def test_returns_text_on_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="<html><body>Hello</body></html>")
        result = fetch_url("https://example.com")
        assert "Hello" in result

    @patch('modes.common.subprocess.run')
    def test_returns_error_on_exception(self, mock_run):
        mock_run.side_effect = Exception("Network error")
        result = fetch_url("https://example.com")
        assert "Fetch error" in result

    @patch('modes.common.subprocess.run')
    def test_respects_max_chars(self, mock_run):
        mock_run.return_value = MagicMock(stdout="A" * 5000)
        result = fetch_url("https://example.com", max_chars=100)
        assert len(result) <= 100

    @patch('modes.common.subprocess.run')
    def test_uses_curl_command(self, mock_run):
        mock_run.return_value = MagicMock(stdout="text")
        fetch_url("https://example.com")
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "curl"
        assert "https://example.com" in cmd


# ─── fetch_markdown tests ──────────────────────────────────────

class TestFetchMarkdown:
    @patch('modes.common.subprocess.run')
    def test_converts_html_to_text(self, mock_run):
        mock_run.return_value = MagicMock(stdout="<html><body><p>Markdown test</p></body></html>")
        result = fetch_markdown("https://example.com")
        assert "Markdown test" in result

    @patch('modes.common.subprocess.run')
    def test_passes_plain_text_through(self, mock_run):
        mock_run.return_value = MagicMock(stdout="# Already Markdown\n\nText here.")
        result = fetch_markdown("https://example.com")
        assert "Already Markdown" in result

    @patch('modes.common.subprocess.run')
    def test_returns_error_on_failure(self, mock_run):
        mock_run.side_effect = Exception("Connection refused")
        result = fetch_markdown("https://example.com")
        assert "Fetch error" in result

    @patch('modes.common.subprocess.run')
    def test_truncates_plain_text(self, mock_run):
        mock_run.return_value = MagicMock(stdout="X" * 20000)
        result = fetch_markdown("https://example.com", max_chars=500)
        assert len(result) <= 500
