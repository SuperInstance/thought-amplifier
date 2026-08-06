"""
Tests for modes/reporter.py, advocate.py, mirror.py, watcher.py, connector.py, simulator.py.

All LLM and network calls are mocked. Tests verify:
  - Mode initialization
  - Method signatures and return types
  - Journal entries created with correct metadata
  - Error handling (fetch failures, LLM failures)
  - Analysis angles / strategies / styles are covered
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.journal import Journal
from core.thinker import Thinker, ThinkerConfig


class TestReporter(unittest.TestCase):
    """Reporter mode tests."""

    def _make_reporter(self):
        from modes.reporter import Reporter
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Reporter(thinker, j, api_key="test", deepseek_api_key="dstest"), j

    @patch("modes.reporter.fetch_markdown")
    @patch("modes.reporter.llm_call")
    def test_research_generates_entries(self, mock_llm, mock_fetch):
        mock_fetch.return_value = "Article content about AI."
        mock_llm.return_value = "Analysis of the article."
        reporter, j = self._make_reporter()
        entries = reporter.research("http://example.com/article", num_thoughts=3)
        self.assertGreater(len(entries), 0)
        # Should have system entry, mode outputs, and synthesis
        mode_outputs = j.read_entries(limit=50, entry_type="mode_output")
        self.assertGreater(len(mode_outputs), 0)

    @patch("modes.reporter.fetch_markdown")
    def test_research_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = "[Fetch error: connection refused]"
        reporter, j = self._make_reporter()
        entries = reporter.research("http://bad.url", num_thoughts=3)
        self.assertEqual(entries, [])

    @patch("modes.reporter.fetch_markdown")
    @patch("modes.reporter.llm_call")
    def test_research_metadata_has_url(self, mock_llm, mock_fetch):
        mock_fetch.return_value = "Content here."
        mock_llm.return_value = "Thought."
        reporter, j = self._make_reporter()
        reporter.research("http://example.com", num_thoughts=2)
        mode_outputs = j.read_entries(limit=20, entry_type="mode_output")
        for entry in mode_outputs:
            if entry["metadata"].get("mode") == "reporter":
                self.assertEqual(entry["metadata"]["url"], "http://example.com")

    @patch("modes.reporter.fetch_markdown")
    @patch("modes.reporter.llm_call")
    def test_research_num_thoughts_capped(self, mock_llm, mock_fetch):
        mock_fetch.return_value = "Content."
        mock_llm.return_value = "Analysis."
        reporter, j = self._make_reporter()
        reporter.research("http://example.com", num_thoughts=100)
        # Should be capped at len(analysis_angles)
        from modes.reporter import Reporter as RClass
        mode_entries = [e for e in j.read_entries(limit=50, entry_type="mode_output")
                       if e["metadata"].get("mode") == "reporter" and not e["metadata"].get("synthesis")]
        # analysis_angles has 6 entries
        self.assertLessEqual(len(mode_entries), 6 + 1)  # +1 for source content entry


class TestAdvocate(unittest.TestCase):
    """Advocate mode tests."""

    def _make_advocate(self):
        from modes.advocate import Advocate
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Advocate(thinker, j, api_key="test", deepseek_api_key="dstest"), j

    @patch("modes.advocate.llm_call")
    def test_argue_generates_entries(self, mock_llm):
        mock_llm.return_value = "Counter-argument text."
        advocate, j = self._make_advocate()
        entries = advocate.argue("Markets are efficient", num_arguments=3)
        self.assertGreater(len(entries), 0)
        mode_outputs = j.read_entries(limit=20, entry_type="mode_output")
        self.assertGreater(len(mode_outputs), 0)

    @patch("modes.advocate.llm_call")
    def test_argue_includes_meta_analysis(self, mock_llm):
        mock_llm.return_value = "Meta analysis."
        advocate, j = self._make_advocate()
        entries = advocate.argue("Claim", num_arguments=2)
        # Last entry should be meta-analysis
        meta_entries = [e for e in entries if e["metadata"].get("meta_analysis")]
        self.assertGreater(len(meta_entries), 0)

    @patch("modes.advocate.llm_call")
    def test_argue_strategies_capped(self, mock_llm):
        mock_llm.return_value = "Arg."
        advocate, j = self._make_advocate()
        advocate.argue("Claim", num_arguments=100)
        from modes.advocate import Advocate as AClass
        strategy_entries = [e for e in j.read_entries(limit=50, entry_type="mode_output")
                           if e["metadata"].get("mode") == "advocate" and not e["metadata"].get("meta_analysis")]
        # 6 strategies available
        self.assertLessEqual(len(strategy_entries), 6)

    @patch("modes.advocate.llm_call")
    def test_argue_journal_has_claim(self, mock_llm):
        mock_llm.return_value = "Response."
        advocate, j = self._make_advocate()
        advocate.argue("Specific claim text", num_arguments=2)
        all_entries = j.read_entries(limit=50)
        claims = [e for e in all_entries if e["metadata"].get("claim") == "Specific claim text"]
        self.assertGreater(len(claims), 0)


class TestMirror(unittest.TestCase):
    """Mirror mode tests."""

    def _make_mirror(self):
        from modes.mirror import Mirror, REFLECTION_STYLES
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Mirror(thinker, j, api_key="test", deepseek_api_key="dstest"), j, REFLECTION_STYLES

    def test_reflection_styles_count(self):
        _, _, styles = self._make_mirror()
        self.assertGreaterEqual(len(styles), 6)

    @patch("modes.mirror.llm_call")
    def test_reflect_generates_entries(self, mock_llm):
        mock_llm.return_value = "A beautiful metaphor."
        mirror, j, _ = self._make_mirror()
        entries = mirror.reflect("The ocean", num_reflections=3)
        self.assertGreater(len(entries), 0)

    @patch("modes.mirror.llm_call")
    def test_reflect_with_custom_styles(self, mock_llm):
        mock_llm.return_value = "Reflection."
        mirror, j, _ = self._make_mirror()
        entries = mirror.reflect("Rivers", num_reflections=2, styles=["metaphor", "paradox"])
        self.assertEqual(len(entries), 2 + 1)  # 2 reflections + 1 synthesis

    @patch("modes.mirror.llm_call")
    def test_reflect_includes_synthesis(self, mock_llm):
        mock_llm.return_value = "Synthesis text."
        mirror, j, _ = self._make_mirror()
        entries = mirror.reflect("Time", num_reflections=3)
        synthesis = [e for e in entries if e["metadata"].get("synthesis")]
        self.assertGreater(len(synthesis), 0)

    @patch("modes.mirror.llm_call")
    def test_reflect_metadata_has_style(self, mock_llm):
        mock_llm.return_value = "Poetic text."
        mirror, j, _ = self._make_mirror()
        mirror.reflect("Stars", num_reflections=2)
        style_entries = [e for e in j.read_entries(limit=20, entry_type="mode_output")
                        if e["metadata"].get("mode") == "mirror" and e["metadata"].get("style")]
        self.assertGreater(len(style_entries), 0)


class TestWatcher(unittest.TestCase):
    """Watcher mode tests."""

    def _make_watcher(self):
        from modes.watcher import Watcher
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Watcher(thinker, j, api_key="test", deepseek_api_key="dstest",
                      snapshot_dir=str(Path(j.dir) / "snapshots")), j

    @patch("modes.watcher.fetch_markdown")
    @patch("modes.watcher.llm_call")
    def test_watch_first_check_baseline(self, mock_llm, mock_fetch):
        mock_fetch.return_value = "Page content."
        watcher, j = self._make_watcher()
        entries = watcher.watch("http://example.com", interval=0.01, max_checks=1)
        self.assertGreater(len(entries), 0)
        baseline = [e for e in entries if e["metadata"].get("baseline")]
        self.assertGreater(len(baseline), 0)

    @patch("modes.watcher.fetch_markdown")
    @patch("modes.watcher.llm_call")
    def test_watch_detects_change(self, mock_llm, mock_fetch):
        mock_fetch.side_effect = ["Content A.", "Content B with changes."]
        mock_llm.return_value = "Change analysis."
        watcher, j = self._make_watcher()
        entries = watcher.watch("http://example.com", interval=0.01, max_checks=2)
        changed = [e for e in entries if e["metadata"].get("changed")]
        self.assertGreater(len(changed), 0)

    @patch("modes.watcher.fetch_markdown")
    def test_watch_fetch_error_logged(self, mock_fetch):
        mock_fetch.return_value = "[Fetch error: timeout]"
        watcher, j = self._make_watcher()
        watcher.watch("http://bad.url", interval=0.01, max_checks=1)
        all_entries = j.read_entries(limit=50)
        errors = [e for e in all_entries if e["metadata"].get("error")]
        self.assertGreater(len(errors), 0)

    @patch("modes.watcher.fetch_markdown")
    def test_watch_no_change(self, mock_fetch):
        mock_fetch.return_value = "Same content every time."
        watcher, j = self._make_watcher()
        entries = watcher.watch("http://example.com", interval=0.01, max_checks=2)
        no_change = [e for e in entries if e["metadata"].get("changed") is False]
        self.assertGreater(len(no_change), 0)

    def test_diff_analysis(self):
        watcher, _ = self._make_watcher()
        diff = watcher._diff_analysis("line1\nline2", "line1\nline3")
        self.assertIn("Added", diff)
        self.assertIn("Removed", diff)

    def test_diff_analysis_no_changes(self):
        watcher, _ = self._make_watcher()
        diff = watcher._diff_analysis("same\ncontent", "same\ncontent")
        self.assertIn("No textual changes", diff)

    def test_snapshot_path_safe(self):
        watcher, _ = self._make_watcher()
        path = watcher._snapshot_path("http://example.com/page?q=1", 1)
        self.assertTrue(path.name.endswith("_check_1.txt"))


class TestConnector(unittest.TestCase):
    """Connector mode tests."""

    def _make_connector(self):
        from modes.connector import Connector
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Connector(thinker, j, api_key="test", deepseek_api_key="dstest"), j

    @patch("modes.connector.llm_call")
    def test_connect_text_sources(self, mock_llm):
        mock_llm.return_value = "Connection analysis."
        connector, j = self._make_connector()
        entries = connector.connect(["Text about cats.", "Text about dogs."])
        self.assertGreater(len(entries), 0)

    @patch("modes.connector.llm_call")
    @patch("modes.connector.fetch_markdown")
    def test_connect_url_sources(self, mock_fetch, mock_llm):
        mock_fetch.return_value = "URL content."
        mock_llm.return_value = "Pattern found."
        connector, j = self._make_connector()
        entries = connector.connect(["http://a.com", "http://b.com"])
        self.assertGreater(len(entries), 0)

    @patch("modes.connector.llm_call")
    def test_connect_too_few_sources(self, mock_llm):
        mock_llm.return_value = "Analysis."
        connector, j = self._make_connector()
        entries = connector.connect(["only one source"])
        self.assertEqual(entries, [])

    @patch("modes.connector.llm_call")
    def test_connect_includes_synthesis(self, mock_llm):
        mock_llm.return_value = "Synthesis."
        connector, j = self._make_connector()
        entries = connector.connect(["Source A content.", "Source B content."])
        synthesis = [e for e in entries if e["metadata"].get("synthesis")]
        self.assertGreater(len(synthesis), 0)

    def test_get_content_url(self):
        connector, _ = self._make_connector()
        with patch("modes.connector.fetch_markdown", return_value="URL content"):
            result = connector._get_content("http://example.com")
            self.assertEqual(result, "URL content")

    def test_get_content_text(self):
        connector, _ = self._make_connector()
        result = connector._get_content("Just some text")
        self.assertEqual(result, "Just some text")

    def test_get_content_url_fetch_error_fallback(self):
        connector, _ = self._make_connector()
        with patch("modes.connector.fetch_markdown", return_value="[Fetch error: timeout]"):
            result = connector._get_content("http://bad.url")
            self.assertEqual(result, "http://bad.url")


class TestSimulator(unittest.TestCase):
    """Simulator mode tests."""

    def _make_simulator(self):
        from modes.simulator import Simulator, TRAJECTORIES
        j = Journal(journal_dir=tempfile.mkdtemp())
        config = ThinkerConfig()
        thinker = Thinker(config, j)
        return Simulator(thinker, j, api_key="test", deepseek_api_key="dstest"), j, TRAJECTORIES

    def test_trajectories_count(self):
        _, _, trajectories = self._make_simulator()
        self.assertGreaterEqual(len(trajectories), 5)

    @patch("modes.simulator.llm_call")
    def test_simulate_generates_entries(self, mock_llm):
        mock_llm.return_value = "Simulation result."
        simulator, j, _ = self._make_simulator()
        entries = simulator.simulate("What if gravity were optional?", num_trajectories=3)
        self.assertGreater(len(entries), 0)

    @patch("modes.simulator.llm_call")
    def test_simulate_includes_conclusion(self, mock_llm):
        mock_llm.return_value = "Conclusion text."
        simulator, j, _ = self._make_simulator()
        entries = simulator.simulate("Premise", num_trajectories=2)
        conclusions = [e for e in entries if e["metadata"].get("conclusion")]
        self.assertGreater(len(conclusions), 0)

    @patch("modes.simulator.llm_call")
    def test_simulate_trajectories_capped(self, mock_llm):
        mock_llm.return_value = "Result."
        simulator, j, trajectories = self._make_simulator()
        simulator.simulate("Premise", num_trajectories=100)
        traj_entries = [e for e in j.read_entries(limit=50, entry_type="mode_output")
                       if e["metadata"].get("mode") == "simulator"
                       and not e["metadata"].get("conclusion")]
        self.assertLessEqual(len(traj_entries), len(trajectories))

    @patch("modes.simulator.llm_call")
    def test_simulate_metadata_has_premise(self, mock_llm):
        mock_llm.return_value = "Result."
        simulator, j, _ = self._make_simulator()
        simulator.simulate("Test premise", num_trajectories=2)
        all_meta = [e["metadata"] for e in j.read_entries(limit=20, entry_type="mode_output")]
        premises = [m for m in all_meta if m.get("premise") == "Test premise"]
        self.assertGreater(len(premises), 0)

    def test_trajectory_names(self):
        _, _, trajectories = self._make_simulator()
        for t in trajectories:
            self.assertIn("name", t)
            self.assertIn("instruction", t)
            self.assertIsInstance(t["name"], str)
            self.assertIsInstance(t["instruction"], str)


if __name__ == "__main__":
    unittest.main()
