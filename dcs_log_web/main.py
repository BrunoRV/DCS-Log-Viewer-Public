"""
FastAPI application factory and entry point.

Responsibilities:
  - Create the FastAPI `app` instance
  - Register the lifespan (config load + cleanup)
  - Include HTTP routes  (routes.py)
  - Register WebSocket endpoint  (ws.py)
  - Mount static files
  - Provide the `main()` CLI entry point

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

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dcs_log_core.config import load_config
from . import ws as ws_state
from .routes import router
from .ws import websocket_endpoint

log = logging.getLogger(__name__)

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    ws_state.set_config(load_config())
    yield  # server runs here


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DCS Log Viewer",
    docs_url=None,
    redoc_url=None,
    lifespan=_lifespan,
)

app.include_router(router)
app.add_api_websocket_route("/ws", websocket_endpoint)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    port = int(os.environ.get("DCS_LOG_PORT", "8420"))
    host = os.environ.get("DCS_LOG_HOST", "127.0.0.1")
    log_level = os.environ.get("DCS_LOG_LEVEL", "info")

    print(f"\n[DCS Log Viewer] http://{host}:{port}\n")

    uvicorn.run(
        "dcs_log_web.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
