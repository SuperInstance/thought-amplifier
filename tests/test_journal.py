"""
Tests for core/journal.py — JSONL + Markdown Journal Writer

Covers:
  - Entry writing (all types: thought, directive, mode_output, system, intervention, summary)
  - JSONL format correctness
  - Markdown format correctness
  - Reading entries (filtering, limiting, ordering)
  - Session management
  - read_all_sessions across multiple sessions
  - get_latest_session
  - Edge cases: empty journal, corrupted lines, missing directory
  - Metadata propagation
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.journal import Journal, ENTRY_TYPES


class TestJournalInit(unittest.TestCase):
    """Journal initialization and directory management."""

    def test_creates_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            jdir = Path(tmp) / "deep" / "nested" / "journal"
            j = Journal(journal_dir=jdir)
            self.assertTrue(jdir.exists())

    def test_session_id_is_timestamp_format(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        # YYYYMMDD_HHMMSS
        self.assertEqual(len(j.session_id), 15)
        self.assertEqual(j.session_id[8], "_")

    def test_jsonl_and_md_paths_set(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        self.assertTrue(str(j.jsonl_path).endswith(".jsonl"))
        self.assertTrue(str(j.md_path).endswith(".md"))


class TestJournalWrite(unittest.TestCase):
    """Writing entries in all types."""

    def setUp(self):
        self.j = Journal(journal_dir=tempfile.mkdtemp())

    def test_write_thought_creates_jsonl(self):
        entry = self.j.write("thought", "The ocean remembers every wave.")
        self.assertTrue(self.j.jsonl_path.exists())
        self.assertEqual(entry["type"], "thought")
        self.assertEqual(entry["content"], "The ocean remembers every wave.")

    def test_write_directive(self):
        entry = self.j.write("directive", "Increase temperature.", {"reason": "stagnation"})
        self.assertEqual(entry["type"], "directive")
        self.assertEqual(entry["metadata"]["reason"], "stagnation")

    def test_write_mode_output(self):
        entry = self.j.write("mode_output", "Report content.", {"mode": "reporter"})
        self.assertEqual(entry["metadata"]["mode"], "reporter")

    def test_write_system(self):
        entry = self.j.write("system", "Startup complete.")
        self.assertEqual(entry["type"], "system")

    def test_write_intervention(self):
        entry = self.j.write("intervention", "User redirected topic.")
        self.assertEqual(entry["type"], "intervention")

    def test_write_summary(self):
        entry = self.j.write("summary", "10 thoughts generated, avg quality 0.7.")
        self.assertEqual(entry["type"], "summary")

    def test_write_with_dict_content(self):
        """Dict content is JSON-serialized."""
        entry = self.j.write("thought", {"nested": "value", "num": 42})
        parsed = json.loads(entry["content"])
        self.assertEqual(parsed["nested"], "value")
        self.assertEqual(parsed["num"], 42)

    def test_write_with_no_metadata_defaults_to_empty(self):
        entry = self.j.write("thought", "test")
        self.assertEqual(entry["metadata"], {})

    def test_entry_has_id(self):
        entry = self.j.write("thought", "test")
        self.assertTrue(len(entry["id"]) > 0)

    def test_entry_has_timestamp(self):
        entry = self.j.write("thought", "test")
        self.assertIn("timestamp", entry)
        self.assertIn("T", entry["timestamp"])  # ISO format

    def test_entry_has_session(self):
        entry = self.j.write("thought", "test")
        self.assertEqual(entry["session"], self.j.session_id)

    def test_multiple_writes_append_to_jsonl(self):
        for i in range(5):
            self.j.write("thought", f"Thought {i}")
        lines = self.j.jsonl_path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 5)

    def test_jsonl_entries_are_valid_json(self):
        self.j.write("thought", "test content")
        self.j.write("directive", "do something")
        lines = self.j.jsonl_path.read_text().strip().split("\n")
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("type", parsed)
            self.assertIn("content", parsed)


class TestMarkdownOutput(unittest.TestCase):
    """Markdown formatting for each entry type."""

    def setUp(self):
        self.j = Journal(journal_dir=tempfile.mkdtemp())

    def test_md_header_written_on_first_entry(self):
        self.j.write("thought", "first thought")
        content = self.j.md_path.read_text()
        self.assertIn("# Thought Stream", content)
        self.assertIn("**Started:**", content)

    def test_md_header_written_only_once(self):
        self.j.write("thought", "first")
        self.j.write("thought", "second")
        content = self.j.md_path.read_text()
        self.assertEqual(content.count("# Thought Stream"), 1)

    def test_thought_format_has_quality_when_present(self):
        self.j.write("thought", "good thought", {"quality": 0.85})
        content = self.j.md_path.read_text()
        self.assertIn("q=0.85", content)

    def test_thought_format_no_quality_when_absent(self):
        self.j.write("thought", "plain thought")
        content = self.j.md_path.read_text()
        self.assertNotIn("q=", content)

    def test_directive_format_has_arrow(self):
        self.j.write("directive", "Change the prompt.")
        content = self.j.md_path.read_text()
        self.assertIn("> Change the prompt.", content)

    def test_directive_metadata_in_md(self):
        self.j.write("directive", "Adjust.", {"temp": 1.2, "reason": "stagnation"})
        content = self.j.md_path.read_text()
        self.assertIn("**temp**", content)
        self.assertIn("1.2", content)

    def test_mode_output_has_mode_label(self):
        self.j.write("mode_output", "Report body.", {"mode": "reporter"})
        content = self.j.md_path.read_text()
        self.assertIn("Reporter Output", content)

    def test_system_format(self):
        self.j.write("system", "Engine started.")
        content = self.j.md_path.read_text()
        self.assertIn("⚙️", content)

    def test_intervention_format(self):
        self.j.write("intervention", "Manual override.")
        content = self.j.md_path.read_text()
        self.assertIn("👤", content)

    def test_summary_format(self):
        self.j.write("summary", "Period summary.")
        content = self.j.md_path.read_text()
        self.assertIn("📊", content)


class TestReadEntries(unittest.TestCase):
    """Reading entries from the journal."""

    def setUp(self):
        self.j = Journal(journal_dir=tempfile.mkdtemp())
        for i in range(10):
            self.j.write("thought", f"Thought {i}")
        self.j.write("directive", "Adjust temperature.")
        self.j.write("system", "Mode changed.")

    def test_read_all_entries(self):
        entries = self.j.read_entries(limit=100)
        self.assertEqual(len(entries), 12)

    def test_read_entries_most_recent_first(self):
        entries = self.j.read_entries(limit=5)
        self.assertEqual(len(entries), 5)
        # Most recent first: last written was system event
        self.assertEqual(entries[0]["type"], "system")

    def test_limit_respected(self):
        entries = self.j.read_entries(limit=3)
        self.assertEqual(len(entries), 3)

    def test_filter_by_type(self):
        thoughts = self.j.read_entries(limit=100, entry_type="thought")
        self.assertEqual(len(thoughts), 10)
        for e in thoughts:
            self.assertEqual(e["type"], "thought")

    def test_read_thoughts_shortcut(self):
        thoughts = self.j.read_thoughts(limit=100)
        self.assertEqual(len(thoughts), 10)

    def test_read_directives_shortcut(self):
        directives = self.j.read_directives(limit=100)
        self.assertEqual(len(directives), 1)

    def test_empty_journal_returns_empty_list(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        self.assertEqual(j.read_entries(), [])

    def test_handles_corrupted_jsonl_lines(self):
        """Corrupted lines in JSONL are skipped, not crashed."""
        with open(self.j.jsonl_path, "a") as f:
            f.write("THIS IS NOT JSON\n")
            f.write('{"valid": "but no required fields"}\n')
        entries = self.j.read_entries(limit=100)
        # Should not crash; corrupted lines are skipped
        self.assertGreater(len(entries), 0)


class TestMultipleSessions(unittest.TestCase):
    """Reading across multiple session files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_read_all_sessions_combines_files(self):
        j1 = Journal(journal_dir=self.tmpdir)
        j1.write("thought", "from session 1")

        j2 = Journal(journal_dir=self.tmpdir)
        j2.write("thought", "from session 2")

        entries = Journal.read_all_sessions(self.tmpdir, limit=100)
        self.assertGreaterEqual(len(entries), 2)

    def test_read_all_sessions_limit_respected(self):
        for i in range(5):
            j = Journal(journal_dir=self.tmpdir)
            j.write("thought", f"session {i}")

        entries = Journal.read_all_sessions(self.tmpdir, limit=3)
        self.assertEqual(len(entries), 3)

    def test_read_all_sessions_empty_dir(self):
        entries = Journal.read_all_sessions("/nonexistent/path", limit=10)
        self.assertEqual(entries, [])

    def test_get_latest_session_returns_path(self):
        j1 = Journal(journal_dir=self.tmpdir)
        j1.write("thought", "first")

        j2 = Journal(journal_dir=self.tmpdir)
        j2.write("thought", "second")

        latest = Journal.get_latest_session(self.tmpdir)
        self.assertIsNotNone(latest)
        self.assertTrue(latest.exists())

    def test_get_latest_session_empty_dir(self):
        result = Journal.get_latest_session("/nonexistent/path")
        self.assertIsNone(result)


class TestEntryTypesConstant(unittest.TestCase):
    """The ENTRY_TYPES constant."""

    def test_has_all_expected_types(self):
        expected = {"thought", "directive", "mode_output", "system", "intervention", "summary"}
        self.assertEqual(set(ENTRY_TYPES.keys()), expected)

    def test_all_values_are_strings(self):
        for v in ENTRY_TYPES.values():
            self.assertIsInstance(v, str)
            self.assertTrue(len(v) > 0)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and robustness."""

    def test_write_unicode_content(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        entry = j.write("thought", "The fish says 🐟 and 你好 and —")
        self.assertIn("🐟", entry["content"])

    def test_write_empty_string_content(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        entry = j.write("thought", "")
        self.assertEqual(entry["content"], "")

    def test_write_long_content(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        long_text = "A" * 10000
        entry = j.write("thought", long_text)
        self.assertEqual(len(entry["content"]), 10000)

    def test_write_special_chars_in_metadata(self):
        j = Journal(journal_dir=tempfile.mkdtemp())
        entry = j.write("thought", "test", {"path": "/tmp/test\nfile"})
        # Should not corrupt JSONL
        lines = j.jsonl_path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])  # Should parse without error

    def test_concurrent_journal_instances_same_dir(self):
        """Two Journal instances pointing at same dir can coexist.

        If created within the same second, they share a session_id (same filename).
        Both can still write — entries append to the same file.
        If created in different seconds, they get separate files.
        """
        d = tempfile.mkdtemp()
        j1 = Journal(journal_dir=d)
        j2 = Journal(journal_dir=d)
        # Both can write without error
        j1.write("thought", "from j1")
        j2.write("thought", "from j2")
        # At least one file must exist
        self.assertTrue(j1.jsonl_path.exists())
        # If same session, both wrote to same file
        if j1.session_id == j2.session_id:
            lines = j1.jsonl_path.read_text().strip().split("\n")
            self.assertEqual(len(lines), 2)
        else:
            # Separate files
            self.assertTrue(j2.jsonl_path.exists())
            self.assertNotEqual(j1.jsonl_path, j2.jsonl_path)


if __name__ == "__main__":
    unittest.main()
