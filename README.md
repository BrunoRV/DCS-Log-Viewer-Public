# DCS Log Viewer

A high-performance, real-time log visualizer for **Digital Combat Simulator**.  
Stream, search, and filter `dcs.log` in your browser while DCS is running — zero impact on the simulator.

![UI preview — dark mode log grid with level badges and real-time filtering](docs/preview.png)

---

## Features

| Feature | Details |
|---|---|
| **Real-time tail** | Polls the log file every 250 ms using a read-only share so DCS never loses its write lock |
| **Sliding window** | Keeps only the last 1 000 entries in memory by default (configurable) |
| **Smart parsing** | Regex extraction of Timestamp, Level, Category, Thread, Message |
| **Multiline grouping** | Stack traces / indented continuation lines collapse into an expandable row |
| **Virtual scroll** | Only DOM-renders the visible viewport rows — zero UI lag at any entry count |
| **Level filter** | Toggle ERROR / WARN / INFO / DEBUG / TRACE individually via pill buttons |
| **Category filter** | Drop-down populated from live log data |
| **Full-text search** | Instant client-side search across all fields |
| **Auto-scroll** | Follows the tail automatically; pauses when you scroll up |
| **Copy to Clipboard** | One-click copy for log entries (including full stack traces) |
| **Dark / Light theme** | Toggled from the UI; persisted across sessions |
| **Syntax Highlighting** | Automatic highlighting of paths, IPs, URLs, brackets, braces, and method calls |
| **Config persistence** | Log path + preferences saved to `%APPDATA%\dcs-log-viewer\config.json` |
| **Log rotation** | Detects truncation / inode change and re-reads from the beginning |

---

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) — `pip install uv` or `winget install astral-sh.uv`

---

## Quick start

```powershell
# 1. Clone / download this repository
git clone https://github.com/BrunoRV/dcs-log-viewer-public.git
cd "dcs-log-viewer-public"

# 2. Install dependencies and run (uv creates the venv automatically)
uv run python -m dcs_log_viewer.main
```

The app will print:

```
[DCS Log Viewer] http://127.0.0.1:8420
```

Open that URL in your browser.

---

## Running options

| Environment variable | Default | Description |
|---|---|---|
| `DCS_LOG_PORT` | `8420` | HTTP / WS listen port |
| `DCS_LOG_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` for LAN access) |
| `DCS_LOG_LEVEL` | `info` | Uvicorn log level |

Example:

```powershell
$env:DCS_LOG_PORT = "9000"
uv run python -m dcs_log_viewer.main
```

---

## Usage

1. **Enter the path** to your `dcs.log` in the top bar.  
   Default DCS location: `%USERPROFILE%\Saved Games\DCS\Logs\dcs.log`  
   (or `DCS.openbeta` for the beta branch)

2. Click **Load**. The viewer reads the current file and starts tailing.

3. Use the **filter toolbar** to narrow results:
   - Click level pills (ERROR, WARN …) to show only those levels — multiple can be active
   - Type in the **Search** box for instant full-text filtering
   - Pick a **Category** from the drop-down

4. Click any row with a **▸** button to expand its stack trace / continuation lines.

5. Use **Reload** to re-read the file from the beginning (e.g. after DCS restarts).

6. **Clear** removes all entries from the view without touching the file.

7. Toggle **Auto-scroll** to lock to the newest entries or freely scroll history.

8. Click **Light / Dark** to switch themes. The choice is saved automatically.

---

## Project structure

```
dcs-log-viewer/
├── dcs_log_viewer/
│   ├── __init__.py
│   ├── main.py        ← FastAPI app + WebSocket server + entry point
│   ├── parser.py      ← Regex log parser + multiline grouping
│   ├── tailer.py      ← Async file tail with sliding window
│   ├── config.py      ← JSON config persistence
│   └── static/
│       ├── index.html ← SPA shell
│       ├── css/
│       │   └── style.css   ← Dark/light themes, virtual grid styles
│       └── js/
│           ├── ws.js        ← WebSocket client + event bus
│           ├── filters.js   ← In-memory store + filter/search engine
│           ├── grid.js      ← Virtual-scroll log grid renderer
│           ├── highlighter.js ← Generic syntax highlighting engine
│           ├── highlighter_dcs.js ← DCS-specific rules and instance
│           └── app.js       ← Main orchestrator, UI wiring
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Development

```powershell
# Install with dev extras (adds uvicorn reload + testing tools)
uv sync

# Run with auto-reload on source changes
uv run uvicorn dcs_log_viewer.main:app --reload --port 8420
```

---

## Testing

### Python (pytest)
The project uses `pytest` for Python unit and integration testing.

```powershell
# Run all Python tests
uv run pytest tests/python

# With coverage
uv run pytest tests/python --cov=dcs_log_viewer
```

### Frontend (JavaScript)
We use [Vitest](https://vitest.dev/) for unit testing.
- `npm test`: Run all JS tests.
- `npm run test:coverage`: Run tests with coverage report.

Our tests follow a **minimal dependency** philosophy, using manual DOM mocks to test UI logic (like virtual scrolling) without heavy simulations like JSDOM.

```powershell
# Open coverage/index.html to see the visual report

# Run JS tests in watch mode (recommended for development)
npm run test:watch
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
