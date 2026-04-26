from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from dcs_log_viewer.parser import LogEntry


class LogStore:
    """
    Manages log entries and filtering logic.
    Mirroring the functionality of filters.js in Python.
    """

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []
        self._search: str = ""
        self._use_regex: bool = False
        self._levels: set[str] = set()  # empty means "all"
        self._emitter: str = ""
        self._regex_cache: re.Pattern | None = None

    def add(self, entries: Iterable[LogEntry]) -> None:
        """Append new entries to the store."""
        self._entries.extend(entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def set_search(self, text: str, use_regex: bool = False) -> None:
        self._search = text
        self._use_regex = use_regex
        self._regex_cache = None
        if use_regex and text:
            try:
                self._regex_cache = re.compile(text, re.IGNORECASE)
            except re.error:
                self._regex_cache = None

    def set_levels(self, levels: Iterable[str]) -> None:
        self._levels = set(levels)

    def set_emitter(self, emitter: str) -> None:
        self._emitter = emitter

    def get_emitters(self) -> list[str]:
        """Return unique sorted list of emitters."""
        return sorted({e.emitter for e in self._entries if e.emitter})

    def get_filtered(self) -> list[LogEntry]:
        """Return entries that match current filters."""
        return [e for e in self._entries if self._matches(e)]

    def _matches(self, entry: LogEntry) -> bool:
        # Level filter
        if self._levels and entry.level not in self._levels:
            return False

        # Emitter filter
        if self._emitter and entry.emitter != self._emitter:
            return False

        # Search filter
        if self._search:
            # We search in timestamp, level, emitter, thread, message, and continuations
            haystack = (
                f"{entry.timestamp} {entry.level} {entry.emitter} "
                f"{entry.thread} {entry.message} {' '.join(entry.continuation)}"
            )

            if self._use_regex and self._regex_cache:
                if not self._regex_cache.search(haystack):
                    return False
            else:
                if self._search.lower() not in haystack.lower():
                    return False

        return True
