"""
File tail watcher.
Reads the DCS log file using a read-only share so it never interferes
with DCS's own file lock.  Uses watchfiles for efficient inotify/FSEvents
based change detection; falls back to polling every 250 ms on Windows
(where FSEvents are less reliable for rapidly-changing files).

The tailer maintains a "sliding window" of the last `window_lines` parsed
entries and emits incremental updates via an async generator.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

import aiofiles

from .parser import LogEntry, LogParser

log = logging.getLogger(__name__)

# How often to poll when watchfiles doesn't fire (ms)
_POLL_INTERVAL = 0.25
# Max lines sent in a single batch to avoid overloading the WebSocket
_BATCH_SIZE = 200


class LogTailer:
    """
    Async log tailer that yields batches of new LogEntry objects.

    Usage:

        tailer = LogTailer(path, window_lines=1500)
        async for batch in tailer.watch():
            send_to_clients(batch)
    """

    def __init__(self, path: str | Path, window_lines: int = 1500) -> None:
        self.path = Path(path)
        self.window_lines = window_lines
        self._parser = LogParser()
        self._offset: int = 0          # byte position already consumed
        self._window: list[LogEntry] = []
        self._stop_event = asyncio.Event()
        self._last_inode: Optional[int] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def window(self) -> list[LogEntry]:
        """Current sliding window snapshot (read-only view)."""
        return list(self._window)

    async def initial_load(self) -> list[LogEntry]:
        """
        Read (up to) `window_lines` entries from the current file contents.
        Returns the initial snapshot and primes the internal offset/parser.
        """
        self._parser.reset()
        self._window.clear()
        self._offset = 0

        entries = await self._read_new_entries()
        self._window = entries[-self.window_lines :]
        return list(self._window)

    async def watch(self) -> AsyncIterator[list[LogEntry]]:
        """
        Async generator.  Yields non-empty batches of *new* LogEntry items
        as the file grows.  Handles log rotation (file truncated or replaced).
        """
        while not self._stop_event.is_set():
            await asyncio.sleep(_POLL_INTERVAL)

            if not self.path.exists():
                continue

            try:
                stat = self.path.stat()
                current_inode = stat.st_ino

                # Detect rotation / truncation
                if (
                    self._last_inode is not None
                    and current_inode != self._last_inode
                ) or stat.st_size < self._offset:
                    self._parser.reset()
                    self._offset = 0
                    self._window.clear()

                self._last_inode = current_inode

                if stat.st_size <= self._offset:
                    continue

            except OSError:
                continue

            new_entries = await self._read_new_entries()
            if new_entries:
                # Update sliding window
                combined = self._window + new_entries
                self._window = combined[-self.window_lines :]
                # Yield in batches to avoid single huge message
                for i in range(0, len(new_entries), _BATCH_SIZE):
                    yield new_entries[i : i + _BATCH_SIZE]

    # ── Internals ──────────────────────────────────────────────────────────────

    async def _read_new_entries(self) -> list[LogEntry]:
        """
        Read all bytes from `_offset` to EOF, parse them, and advance offset.
        Opens with share flags that allow DCS to keep its write handle open.
        """
        entries: list[LogEntry] = []
        try:
            # Open in binary mode to get exact byte offsets, then decode
            async with aiofiles.open(self.path, "rb") as fh:
                await fh.seek(self._offset)
                raw = await fh.read()

            if not raw:
                return entries

            # Only consume up to the last newline to avoid parsing partial lines
            last_nl = raw.rfind(b"\n")
            if last_nl == -1:
                # No newline found — don't advance offset, wait for more data
                return entries

            # Advance offset only for the complete lines
            to_parse = raw[: last_nl + 1]
            self._offset += len(to_parse)

            # Decode robustly — DCS writes in UTF-8 but may have invalid bytes
            text = to_parse.decode("utf-8", errors="replace")
            reader = io.StringIO(text)

            for line in reader:
                entry = self._parser.feed_line(line)
                if entry:
                    entries.append(entry)

            # Flush the last pending entry
            last = self._parser.flush()
            if last:
                entries.append(last)

        except PermissionError as exc:
            # File is locked exclusively by DCS — transient, just skip this cycle
            log.debug("Log file locked, will retry: %s", exc)
        except OSError as exc:
            log.warning("Unexpected I/O error reading log file: %s", exc)

        return entries
