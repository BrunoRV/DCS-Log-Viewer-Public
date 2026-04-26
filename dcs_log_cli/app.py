from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    RichLog,
)
from textual.binding import Binding

from dcs_log_core.tailer import LogTailer
from dcs_log_cli.store import LogStore
from dcs_log_cli.highlighter import DCSLogHighlighter


LEVEL_STYLES = {
    "ERROR": "bold #ff5555",
    "WARN": "bold #f1fa8c",
    "INFO": "#50fa7b",
    "DEBUG": "#8be9fd",
    "TRACE": "#6272a4",
}


class DCSLogApp(App):
    """DCS Log Viewer CLI (btop style)."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f2", "toggle_sidebar", "Filters"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_filters", "Clear Filters"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
        Binding("up", "scroll_up", "Scroll Up", show=False),
        Binding("down", "scroll_down", "Scroll Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "scroll_home", "Scroll Home", show=False),
        Binding("end", "scroll_end", "Scroll End", show=False),
        Binding("s", "toggle_autoscroll", "Auto-scroll"),
    ]

    def __init__(self, log_path: Path):
        super().__init__()
        self.log_path = log_path
        self.store = LogStore()
        self.tailer = LogTailer(log_path)
        self.highlighter = DCSLogHighlighter()
        self._show_sidebar = False
        self._show_search = False
        self.auto_scroll = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with VerticalScroll(id="sidebar"):
                yield Label("LEVELS")
                self.level_list = ListView(id="level-list")
                yield self.level_list
                
                yield Label("EMITTERS")
                self.emitter_list = ListView(id="emitter-list")
                yield self.emitter_list
            
            with Container(id="log-container"):
                self.log_view = RichLog(id="log-view", highlight=False, markup=False)
                yield self.log_view

        with Container(id="search-container"):
            yield Input(placeholder="Search... (Regex supported)", id="search-input")

        yield Footer()

    async def on_mount(self) -> None:
        from rich.theme import Theme
        self.console.push_theme(Theme({
            "log.link": "underline #bd93f9",
            "log.bracket": "#ffb86c",
            "log.brace": "#ff79c6",
            "log.member": "italic #8be9fd",
            "log.string": "#f1fa8c",
        }))
        
        self.title = f"DCS Log Viewer - {self.log_path.name}"
        self.sub_title = str(self.log_path)
        
        # Initial load
        entries = await self.tailer.initial_load()
        self.store.add(entries)
        self.refresh_sidebar()
        self.refresh_logs()
        
        # Start watching
        self.watch_logs()

    @work(exclusive=True)
    async def watch_logs(self) -> None:
        async for batch in self.tailer.watch():
            self.store.add(batch)
            self.call_from_thread(self.refresh_logs, is_append=True)
            self.call_from_thread(self.refresh_sidebar)

    def refresh_logs(self, is_append: bool = False) -> None:
        """Update the log display based on filtered entries."""
        if not is_append:
            self.log_view.clear()
            entries = self.store.get_filtered()
        else:
            # For correctness and simplicity in this mode, we refresh everything
            # In a production app with huge logs, we'd only append matching entries.
            self.log_view.clear()
            entries = self.store.get_filtered()

        for entry in entries:
            self.log_view.write(self._format_entry(entry))
        
        if self.auto_scroll:
            self.log_view.scroll_end(animate=False)

    def _format_entry(self, entry) -> Text:
        # Format: TIMESTAMP LEVEL EMITTER (THREAD): MESSAGE
        level_style = LEVEL_STYLES.get(entry.level, "")
        
        text = Text()
        text.append(f"{entry.timestamp} ", style="dim")
        text.append(f"{entry.level:<7} ", style=level_style)
        text.append(f"{entry.emitter} ", style="bold")
        if entry.thread:
            text.append(f"({entry.thread})", style="dim")
        text.append(": ")
        
        # Highlight the message content
        msg_text = Text(entry.message)
        self.highlighter.highlight(msg_text)
        text.append(msg_text)
        
        # Add continuations
        for cont in entry.continuation:
            text.append("\n    ")
            cont_text = Text(cont)
            self.highlighter.highlight(cont_text)
            cont_text.stylize("dim")
            text.append(cont_text)
            
        return text

    def action_scroll_up(self) -> None:
        self.auto_scroll = False
        self.log_view.scroll_relative(y=-1)

    def action_scroll_down(self) -> None:
        self.log_view.scroll_relative(y=1)

    def action_page_up(self) -> None:
        self.auto_scroll = False
        self.log_view.scroll_page_up()

    def action_page_down(self) -> None:
        self.log_view.scroll_page_down()

    def action_scroll_home(self) -> None:
        self.auto_scroll = False
        self.log_view.scroll_home()

    def action_scroll_end(self) -> None:
        self.log_view.scroll_end()

    def action_toggle_autoscroll(self) -> None:
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self.log_view.scroll_end(animate=False)
        self.notify(f"Auto-scroll: {'ON' if self.auto_scroll else 'OFF'}")

    def _sanitize_id(self, text: str) -> str:
        """Sanitize a string to be a valid Textual identifier."""
        import re
        # Textual IDs must contain only letters, numbers, underscores, or hyphens.
        # We replace everything else with underscores.
        return re.sub(r"[^a-zA-Z0-9_-]", "_", text)

    def refresh_sidebar(self) -> None:
        """Update the emitter list in the sidebar."""
        emitters = self.store.get_emitters()
        
        # We use a set of existing IDs for faster lookup
        existing_ids = {item.id for item in self.emitter_list.query(ListItem)}
        
        for emitter in emitters:
            sanitized_id = f"emitter-{self._sanitize_id(emitter)}"
            if sanitized_id not in existing_ids:
                item = ListItem(Label(emitter), id=sanitized_id)
                # Store original name for mapping back
                item.emitter_name = emitter
                self.emitter_list.append(item)

        # Levels are static from parser
        if not self.level_list.children:
            from dcs_log_core.parser import LEVELS, LEVEL_NORM
            unique_levels = sorted(set(LEVEL_NORM.get(l, l) for l in LEVELS))
            for level in unique_levels:
                self.level_list.append(ListItem(Label(level), id=f"lvl-{level}"))

    def action_toggle_sidebar(self) -> None:
        self._show_sidebar = not self._show_sidebar
        self.query_one("#sidebar").set_class(self._show_sidebar, "-visible")
        if self._show_sidebar:
            self.query_one("#sidebar").focus()

    def action_focus_search(self) -> None:
        self._show_search = True
        container = self.query_one("#search-container")
        container.set_class(True, "-visible")
        # Focusing after a refresh helps when containers are being made visible
        self.call_after_refresh(self.query_one("#search-input").focus)

    def action_clear_filters(self) -> None:
        self.store.set_search("")
        self.store.set_levels([])
        self.store.set_emitter("")
        
        self.query_one("#search-input").value = ""
        self._show_search = False
        self.query_one("#search-container").set_class(False, "-visible")
        
        # Reset selection in sidebar
        self.refresh_logs()

    def action_clear_log(self) -> None:
        self.store.clear()
        self.refresh_logs()

    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        self.store.set_search(event.value)
        self.refresh_logs()
        self.log_view.focus()

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        # Live search disabled for performance on large logs
        pass

    @on(ListView.Selected, "#level-list")
    def on_level_selected(self, event: ListView.Selected) -> None:
        level = event.item.id.replace("lvl-", "")
        self.store.set_levels([level])
        self.refresh_logs()

    @on(ListView.Selected, "#emitter-list")
    def on_emitter_selected(self, event: ListView.Selected) -> None:
        # Retrieve original name stored on the item
        emitter = getattr(event.item, "emitter_name", None)
        if emitter:
            self.store.set_emitter(emitter)
            self.refresh_logs()


def main():
    parser = argparse.ArgumentParser(description="DCS Log Viewer CLI")
    parser.add_argument("log_path", type=Path, help="Path to dcs.log")
    args = parser.parse_args()

    if not args.log_path.exists():
        print(f"Error: {args.log_path} does not exist.")
        sys.exit(1)

    app = DCSLogApp(args.log_path)
    app.run()


if __name__ == "__main__":
    main()
