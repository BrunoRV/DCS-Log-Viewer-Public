import unittest
from dcs_log_viewer.parser import LogParser, parse_lines

class TestLogParser(unittest.TestCase):
    def test_basic_parsing(self):
        lines = [
            "2026-04-23 23:10:52.872 INFO    VISUALIZER (17652): Stopped collection of statistic."
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].level, "INFO")
        self.assertEqual(entries[0].emitter, "VISUALIZER")
        self.assertEqual(entries[0].thread, "17652")
        self.assertEqual(entries[0].message, "Stopped collection of statistic.")

    def test_continuation_parsing(self):
        lines = [
            "2026-04-23 23:10:52.872 INFO    VISUALIZER (17652): Start",
            "    more info line 1",
            "    more info line 2"
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].continuation, ["    more info line 1", "    more info line 2"])

    def test_error_once_issue(self):
        """
        This test reproduces the issue where ERROR_ONCE was not recognized.
        Now it should be recognized and mapped to ERROR level internally for styling,
        but the raw level might still be available or normalized.
        Wait, in parser.py I normalized it to ERROR.
        """
        lines = [
            "2026-04-23 23:10:52.872 INFO    VISUALIZER (17652): Stopped collection of statistic.",
            "2026-04-23 22:29:55.000 ERROR_ONCE  (): ",
            "2026-04-23 23:10:52.945 ERROR_ONCE DX11BACKEND (17652): render target 'uiTargetColor' not found",
            "2026-04-23 23:10:52.945 ERROR_ONCE DX11BACKEND (17652): render target 'uiTargetDepth' not found"
        ]
        entries = parse_lines(lines)
        
        self.assertEqual(len(entries), 4, f"Expected 4 entries, got {len(entries)}")
        self.assertEqual(entries[1].level, "ERROR") # Normalized
        self.assertEqual(entries[2].emitter, "DX11BACKEND")
        self.assertEqual(entries[2].thread, "17652")
        self.assertEqual(entries[3].message, "render target 'uiTargetDepth' not found")

    def test_optional_fields(self):
        lines = [
            "2026-04-23 22:29:55.000 ERROR_ONCE  (): Message"
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].emitter, "")
        self.assertEqual(entries[0].thread, "")
        self.assertEqual(entries[0].message, "Message")

    def test_no_thread_id(self):
        # 2026-04-23 22:29:55.000 INFO    EDCORE (): something
        lines = [
            "2026-04-23 22:29:55.000 INFO    EDCORE (): something"
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].emitter, "EDCORE")
        self.assertEqual(entries[0].thread, "")
        self.assertEqual(entries[0].message, "something")

    def test_no_emitter_or_thread(self):
        # 2026-04-23 22:29:55.000 INFO     (): something
        lines = [
            "2026-04-23 22:29:55.000 INFO     (): something"
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].emitter, "")
        self.assertEqual(entries[0].thread, "")
        self.assertEqual(entries[0].message, "something")

    def test_unusual_emitter_names(self):
        lines = [
            "2026-04-23 22:29:55.000 INFO    Dispatcher.Main (Main): start"
        ]
        entries = parse_lines(lines)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].emitter, "Dispatcher.Main")
        self.assertEqual(entries[0].thread, "Main")

if __name__ == "__main__":
    unittest.main()
