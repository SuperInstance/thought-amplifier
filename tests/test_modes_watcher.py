#!/usr/bin/env python3
"""
Tests for modes/watcher.py — URL monitoring helpers and change detection logic.
Focuses on the pure helper methods that don't require API calls.
"""

import pytest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from modes.watcher import Watcher


@pytest.fixture
def watcher(tmp_path):
    """Create a Watcher with mocked dependencies."""
    thinker = MagicMock()
    journal = MagicMock()
    return Watcher(
        thinker=thinker,
        journal=journal,
        snapshot_dir=str(tmp_path / "snapshots"),
    )


class TestSnapshotPath:
    def test_returns_path_object(self, watcher):
        path = watcher._snapshot_path("https://example.com", 1)
        assert isinstance(path, Path)

    def test_includes_check_number(self, watcher):
        path = watcher._snapshot_path("https://example.com", 5)
        assert "check_5" in path.name

    def test_includes_url_hash(self, watcher):
        url = "https://example.com"
        expected_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        path = watcher._snapshot_path(url, 1)
        assert expected_hash in path.name

    def test_different_urls_different_paths(self, watcher):
        path1 = watcher._snapshot_path("https://a.com", 1)
        path2 = watcher._snapshot_path("https://b.com", 1)
        assert path1 != path2

    def test_same_url_different_checks(self, watcher):
        path1 = watcher._snapshot_path("https://example.com", 1)
        path2 = watcher._snapshot_path("https://example.com", 2)
        assert path1 != path2


class TestLoadSnapshot:
    def test_returns_none_for_missing_file(self, watcher, tmp_path):
        path = tmp_path / "nonexistent.txt"
        assert watcher._load_snapshot(path) is None

    def test_returns_content_for_existing_file(self, watcher, tmp_path):
        path = tmp_path / "snap.txt"
        path.write_text("snapshot content")
        assert watcher._load_snapshot(path) == "snapshot content"

    def test_returns_empty_string_for_empty_file(self, watcher, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        assert watcher._load_snapshot(path) == ""

    def test_returns_unicode_content(self, watcher, tmp_path):
        path = tmp_path / "unicode.txt"
        path.write_text("héllo 🌊", encoding="utf-8")
        assert watcher._load_snapshot(path) == "héllo 🌊"


class TestSaveSnapshot:
    def test_creates_file(self, watcher, tmp_path):
        path = tmp_path / "snap.txt"
        watcher._save_snapshot(path, "new content")
        assert path.exists()
        assert path.read_text() == "new content"

    def test_overwrites_existing(self, watcher, tmp_path):
        path = tmp_path / "snap.txt"
        path.write_text("old")
        watcher._save_snapshot(path, "new")
        assert path.read_text() == "new"


class TestDiffAnalysis:
    def test_no_change_returns_empty(self, watcher):
        result = watcher._diff_analysis("same content", "same content")
        # No additions or removals
        assert "Added" not in result
        assert "Removed" not in result

    def test_change_returns_diff_info(self, watcher):
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        result = watcher._diff_analysis(old, new)
        assert "Added" in result or "Removed" in result

    def test_added_content_detected(self, watcher):
        old = "line1\nline2"
        new = "line1\nline2\nline3"
        result = watcher._diff_analysis(old, new)
        assert "Added" in result
        assert "line3" in result

    def test_removed_content_detected(self, watcher):
        old = "line1\nline2\nline3"
        new = "line1\nline3"
        result = watcher._diff_analysis(old, new)
        assert "Removed" in result
        assert "line2" in result


class TestWatcherInit:
    def test_creates_snapshot_dir(self, tmp_path):
        snapshot_path = str(tmp_path / "deep" / "nested" / "snapshots")
        thinker = MagicMock()
        journal = MagicMock()
        w = Watcher(thinker, journal, snapshot_dir=snapshot_path)
        assert Path(snapshot_path).exists()
        assert Path(snapshot_path).is_dir()

    def test_stores_api_keys(self, watcher):
        assert hasattr(watcher, 'api_key')
        assert hasattr(watcher, 'deepseek_api_key')

    def test_stores_model_names(self, watcher):
        assert hasattr(watcher, 'glm_model')
        assert hasattr(watcher, 'deepseek_model')
