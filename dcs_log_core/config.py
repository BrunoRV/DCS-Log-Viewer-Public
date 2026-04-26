"""
Config persistence.
Stores user preferences (log path, theme, window size, etc.) in
  %APPDATA%/dcs-log-viewer/config.json  (Windows)
  ~/.config/dcs-log-viewer/config.json  (Linux / macOS)
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any

APP_NAME = "dcs-log-viewer"

DEFAULT_CONFIG: dict[str, Any] = {
    "log_path": str(Path.home() / "Saved Games" / "DCS" / "Logs" / "dcs.log"),
    "theme": "dark",
    "window_lines": 1500,
    "auto_scroll": True,
    "level_filter": [],          # empty = show all
    "search_text": "",
}


def _config_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return _config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    p = config_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # Merge with defaults so new keys always exist
            merged = {**DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict[str, Any]) -> None:
    p = config_path()
    p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
