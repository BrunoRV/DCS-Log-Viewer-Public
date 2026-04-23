"""
HTTP route handlers.

Routes registered here:
  GET  /               → index.html (SPA shell)
  GET  /api/config     → current persisted config
  POST /api/config     → update + persist config
  GET  /api/levels     → canonical log level list from parser
  GET  /api/browse     → open native file-picker, return selected path
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .config import save_config
from .parser import LEVELS
from . import ws as ws_state

log = logging.getLogger(__name__)

router = APIRouter()

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_file = _STATIC / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/api/config")
async def get_config() -> dict:
    return ws_state.get_config()


@router.post("/api/config")
async def post_config(body: dict) -> dict:
    cfg = ws_state.get_config()
    cfg.update(body)
    save_config(cfg)
    return cfg


# ── Levels ────────────────────────────────────────────────────────────────────

@router.get("/api/levels")
async def get_levels() -> dict:
    """Return the canonical log-level list derived from parser.LEVELS.

    Normalised levels only (WARNING is collapsed to WARN on ingest),
    so the client sees exactly what appears in ``entry.level``.
    """
    from .parser import LEVEL_NORM
    normalised = list(dict.fromkeys(          # preserve order, deduplicate
        LEVEL_NORM.get(lvl, lvl) for lvl in LEVELS
    ))
    return {"levels": normalised}


# ── File browser ──────────────────────────────────────────────────────────────

@router.get("/api/browse")
async def browse_file():
    """Open a native file-picker dialog and return the selected path."""
    import tkinter as tk
    from tkinter import filedialog

    def _open_dialog():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Select dcs.log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")],
            initialdir=str(Path.home() / "Saved Games" / "DCS" / "Logs"),
        )
        root.destroy()
        return file_path

    path = await asyncio.to_thread(_open_dialog)
    return {"path": path}
