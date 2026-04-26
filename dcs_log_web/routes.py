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

from dcs_log_core.config import save_config
from dcs_log_core.parser import LEVELS
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
    from dcs_log_core.parser import LEVEL_NORM
    normalised = list(dict.fromkeys(          # preserve order, deduplicate
        LEVEL_NORM.get(lvl, lvl) for lvl in LEVELS
    ))
    return {"levels": normalised}


# ── File browser ──────────────────────────────────────────────────────────────

@router.get("/api/browse")
async def browse_file():
    """Open a native file-picker dialog and return the selected path.

    Uses platform-specific subprocesses to avoid blocking the event loop or
    violating GUI thread constraints (especially on macOS).
    """
    import sys
    import platform
    from pathlib import Path

    initial_dir = Path.home() / "Saved Games" / "DCS" / "Logs"
    if not initial_dir.exists():
        initial_dir = Path.home()

    system = platform.system()

    try:
        if system == "Darwin":
            path = await _browse_macos(initial_dir)
        elif system == "Windows":
            path = await _browse_windows(initial_dir)
        else:  # Linux / Others
            path = await _browse_linux(initial_dir)
    except Exception as e:
        log.error(f"Failed to open file browser: {e}")
        path = ""

    return {"path": path}


async def _browse_macos(initial_dir: Path) -> str:
    """Use AppleScript for a native macOS dialog (safe from any thread)."""
    # Escaping for AppleScript: we use POSIX file for the default location.
    script = f'''
        try
            set defaultPath to POSIX file "{initial_dir}"
            set theFile to choose file with prompt "Select dcs.log" of type {{"log", "txt"}} default location defaultPath
            return POSIX path of theFile
        on error
            return ""
        end try
    '''
    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def _browse_windows(initial_dir: Path) -> str:
    """Use an isolated Python subprocess to run Tkinter (safe and clean)."""
    import sys
    # We use repr() to ensure the path is correctly escaped for a Python string literal.
    safe_path_repr = repr(str(initial_dir))
    snippet = (
        "import tkinter as tk; "
        "from tkinter import filedialog; "
        "root = tk.Tk(); "
        "root.withdraw(); "
        "root.attributes('-topmost', True); "
        f"path = filedialog.askopenfilename(title='Select dcs.log', initialdir={safe_path_repr}, "
        "filetypes=[('Log files', '*.log'), ('All files', '*.*')]); "
        "print(path, end=''); "
        "root.destroy()"
    )
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", snippet,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def _browse_linux(initial_dir: Path) -> str:
    """Try zenity or kdialog, falling back to a Tkinter subprocess."""
    # 1. Zenity (GNOME/Common)
    try:
        proc = await asyncio.create_subprocess_exec(
            "zenity", "--file-selection", "--title=Select dcs.log",
            f"--filename={initial_dir}/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception:
        pass

    # 2. kdialog (KDE)
    try:
        proc = await asyncio.create_subprocess_exec(
            "kdialog", "--getopenfilename", str(initial_dir), "*.log|Log files",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception:
        pass

    # 3. Fallback to Tkinter subprocess (reuse Windows logic)
    return await _browse_windows(initial_dir)
