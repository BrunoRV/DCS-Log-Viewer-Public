"""
WebSocket endpoint + background log watcher.

State (tailer, watch task, connected clients) is scoped to this module.
The single WebSocket route is registered on the shared FastAPI `app` instance
imported from main.

WebSocket protocol (server → client):
  { "type": "init",   "entries": [...], "total": N }
  { "type": "append", "entries": [...] }
  { "type": "clear" }
  { "type": "error",  "message": "..." }
  { "type": "config", "data": {...} }

WebSocket protocol (client → server):
  { "action": "set_path",   "path": "..." }
  { "action": "set_config", ...fields... }
  { "action": "clear" }
  { "action": "reload" }
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from .config import save_config
from .tailer import LogTailer

log = logging.getLogger(__name__)

# ── Process-level singletons ──────────────────────────────────────────────────

_tailer: Optional[LogTailer] = None
_watch_task: Optional[asyncio.Task] = None
_clients: set[WebSocket] = set()

# Populated by main.py lifespan before any connection arrives
_config: dict = {}


def set_config(cfg: dict) -> None:
    """Called by main.py lifespan to inject the loaded config."""
    global _config
    _config = cfg


def get_config() -> dict:
    return _config


# ── Helpers ───────────────────────────────────────────────────────────────────

async def broadcast(msg: dict) -> None:
    """Send a JSON message to every connected client, pruning dead sockets."""
    data = json.dumps(msg)
    dead: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


async def start_watch(path: str) -> None:
    """Start (or restart) the background log-file watcher for *path*."""
    global _tailer, _watch_task

    # Stop any existing watcher
    if _watch_task and not _watch_task.done():
        if _tailer:
            _tailer.stop()
        _watch_task.cancel()
        try:
            await _watch_task
        except asyncio.CancelledError:
            pass

    p = Path(path)
    if not p.exists():
        await broadcast({"type": "error", "message": f"File not found: {path}"})
        return

    window_lines = _config.get("window_lines", 1000)
    _tailer = LogTailer(p, window_lines=window_lines)

    # Initial snapshot
    entries = await _tailer.initial_load()
    await broadcast({
        "type": "init",
        "entries": [e.to_dict() for e in entries],
        "total": len(entries),
    })

    # Background watcher task
    async def _watch_loop() -> None:
        try:
            async for batch in _tailer.watch():
                await broadcast({
                    "type": "append",
                    "entries": [e.to_dict() for e in batch],
                })
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.exception("Watcher crashed: %s", exc)
            await broadcast({"type": "error", "message": str(exc)})

    _watch_task = asyncio.create_task(_watch_loop())


# ── WebSocket endpoint ────────────────────────────────────────────────────────

async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)

    # Send current config on connect
    await ws.send_text(json.dumps({"type": "config", "data": _config}))

    # If a log path is already configured, kick off the watch immediately
    if _config.get("log_path"):
        await start_watch(_config["log_path"])

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")

            if action == "set_path":
                path = msg.get("path", "")
                _config["log_path"] = path
                save_config(_config)
                if path:
                    await start_watch(path)

            elif action == "set_config":
                updates = {k: v for k, v in msg.items() if k != "action"}
                _config.update(updates)
                save_config(_config)
                # If window size changed, restart watcher
                if "window_lines" in updates and _config.get("log_path"):
                    await start_watch(_config["log_path"])

            elif action == "reload":
                if _config.get("log_path"):
                    await start_watch(_config["log_path"])

            elif action == "clear":
                await broadcast({"type": "clear"})

    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
