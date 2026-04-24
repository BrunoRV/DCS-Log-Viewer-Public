import pytest
from dcs_log_viewer.parser import LogParser, parse_lines, LogEntry

def test_basic_parsing():
    """Verify that a standard DCS log line is correctly parsed into structured fields."""
    lines = [
        "2026-04-23 23:10:52.872 INFO    VISUALIZER (17652): Stopped collection of statistic."
    ]
    entries = parse_lines(lines)
    assert len(entries) == 1
    assert entries[0].level == "INFO"
    assert entries[0].emitter == "VISUALIZER"
    assert entries[0].thread == "17652"
    assert entries[0].message == "Stopped collection of statistic."

def test_continuation_parsing():
    """Verify that indented lines following a log entry are captured as continuation lines."""
    lines = [
        "2026-04-23 23:10:52.872 INFO    VISUALIZER (17652): Start",
        "    more info line 1",
        "    more info line 2"
    ]
    entries = parse_lines(lines)
    assert len(entries) == 1
    assert entries[0].continuation == ["    more info line 1", "    more info line 2"]

def test_level_normalization():
    """Verify that non-standard levels (WARNING, ERROR_ONCE) are mapped to canonical levels."""
    lines = [
        "2026-04-23 23:10:52.872 WARNING EDCORE (Main): hypervisor is active",
        "2026-04-23 22:29:55.000 ERROR_ONCE DX11BACKEND (17652): render target not found"
    ]
    entries = parse_lines(lines)
    assert len(entries) == 2
    assert entries[0].level == "WARN"
    assert entries[1].level == "ERROR"

def test_optional_fields():
    """Verify that the parser handles missing emitter or thread fields gracefully."""
    # Test message only
    lines = ["2026-04-23 22:29:55.000 INFO     (): Message"]
    entries = parse_lines(lines)
    assert entries[0].emitter == ""
    assert entries[0].thread == ""
    assert entries[0].message == "Message"

    # Test emitter but no thread
    lines = ["2026-04-23 22:29:55.000 INFO    EDCORE (): Message"]
    entries = parse_lines(lines)
    assert entries[0].emitter == "EDCORE"
    assert entries[0].thread == ""

def test_unusual_emitter_names():
    """Verify that emitter names containing dots (e.g. Dispatcher.Main) are correctly parsed."""
    lines = ["2026-04-23 22:29:55.000 INFO    Dispatcher.Main (Main): start"]
    entries = parse_lines(lines)
    assert entries[0].emitter == "Dispatcher.Main"
    assert entries[0].thread == "Main"

def test_skips_headers_and_blank_lines():
    """Verify that 'Log opened/closed' headers and blank lines are ignored by the parser."""
    lines = [
        "=== Log opened UTC 2026-04-23 23:10:52",
        "",
        "2026-04-23 23:10:52.872 INFO    EDCORE (Main): start",
        "=== Log closed UTC 2026-04-24 02:00:00"
    ]
    entries = parse_lines(lines)
    assert len(entries) == 1
    assert entries[0].message == "start"

def test_incremental_parsing():
    """Verify that the stateful LogParser correctly emits entries as new ones arrive."""
    parser = LogParser()
    
    # First line - pending
    res1 = parser.feed_line("2026-04-23 23:10:52.872 INFO    A (1): M1")
    assert res1 is None
    
    # Second line - completes first
    res2 = parser.feed_line("2026-04-23 23:10:53.000 INFO    B (2): M2")
    assert res2 is not None
    assert res2.message == "M1"
    
    # Continuation line
    parser.feed_line("    cont")
    
    # Flush last
    res3 = parser.flush()
    assert res3.message == "M2"
    assert res3.continuation == ["    cont"]

def test_parser_reset():
    """Verify that reset() clears the parser state and ID counter."""
    parser = LogParser()
    parser.feed_line("2026-04-23 23:10:52.872 INFO    A (1): M1")
    parser.reset()
    assert parser._pending is None
    assert parser._counter == 0
    
    last = parser.flush()
    assert last is None

def test_log_entry_to_dict():
    """Verify that LogEntry serialization excludes internal 'raw' data."""
    entry = LogEntry(
        id=1,
        timestamp="2026-04-23 23:10:52.872",
        level="INFO",
        emitter="A",
        thread="1",
        message="M",
        continuation=["C"],
        raw="RAW"
    )
    d = entry.to_dict()
    assert d["id"] == 1
    assert d["timestamp"] == "2026-04-23 23:10:52.872"
    assert "raw" not in d # raw should be excluded from to_dict for frontend
