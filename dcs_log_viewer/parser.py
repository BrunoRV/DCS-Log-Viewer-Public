"""
DCS Log Parser
Extracts structured log entries from dcs.log format:
  YYYY-MM-DD HH:MM:SS.mmm LEVEL   CATEGORY (Thread): Message
Multiline entries (stack traces / indented continuations) are grouped
into a single LogEntry with a `continuation` list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ── Regex ──────────────────────────────────────────────────────────────────────
# Matches: 2026-04-23 02:09:51.935 WARNING EDCORE (Main): hypervisor is active
# Refined to support optional Emitter and Thread, and custom levels like ERROR_ONCE.
LOG_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)"
    r"\s+(?P<level>[A-Z_]+)"
    r"\s+(?P<emitter>\S*)"
    r"\s*\((?P<thread>[^)]*)\):"
    r"\s*(?P<message>.*)$"
)

HEADER_RE = re.compile(r"^=== Log (opened|closed)")

LEVELS = ("ERROR", "WARNING", "WARN", "ERROR_ONCE", "INFO", "DEBUG", "TRACE")

# Normalise levels for consistent styling
LEVEL_NORM = {
    "WARNING": "WARN",
    "ERROR_ONCE": "ERROR",
}


@dataclass
class LogEntry:
    id: int
    timestamp: str
    level: str           # ERROR / WARN / INFO / DEBUG / TRACE
    emitter: str         # Module/System (e.g. EDCORE)
    thread: str          # Thread ID or name (e.g. Main)
    message: str
    continuation: list[str] = field(default_factory=list)
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level,
            "emitter": self.emitter,
            "thread": self.thread,
            "message": self.message,
            "continuation": self.continuation,
        }


class LogParser:
    """
    Stateful, incremental parser.
    Feed it lines one at a time; retrieve completed entries via `flush()`.
    """

    def __init__(self) -> None:
        self._counter: int = 0
        self._pending: Optional[LogEntry] = None

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def feed_line(self, line: str) -> Optional[LogEntry]:
        """
        Feed a single raw line.  Returns a completed LogEntry when a new
        structured entry displaces the previously pending one; otherwise None.
        The caller should call `flush()` after the last line.
        """
        line = line.rstrip("\r\n")

        # Skip blank lines and header/footer markers
        if not line or HEADER_RE.match(line):
            return None

        m = LOG_RE.match(line)
        if m:
            # Emit the previously pending entry
            completed = self._pending
            level_raw = m.group("level")
            self._pending = LogEntry(
                id=self._next_id(),
                timestamp=m.group("timestamp"),
                level=LEVEL_NORM.get(level_raw, level_raw),
                emitter=m.group("emitter"),
                thread=m.group("thread"),
                message=m.group("message"),
                raw=line,
            )
            return completed
        else:
            # Continuation / indented line
            if self._pending is not None:
                self._pending.continuation.append(line)
            return None

    def flush(self) -> Optional[LogEntry]:
        """Return (and clear) the last pending entry."""
        entry = self._pending
        self._pending = None
        return entry

    def reset(self) -> None:
        """Reset counter and state (used when the log file is truncated/rotated)."""
        self._counter = 0
        self._pending = None


def parse_lines(lines: list[str]) -> list[LogEntry]:
    """Convenience: parse a complete list of lines into entries."""
    parser = LogParser()
    entries: list[LogEntry] = []
    for line in lines:
        entry = parser.feed_line(line)
        if entry:
            entries.append(entry)
    last = parser.flush()
    if last:
        entries.append(last)
    return entries
