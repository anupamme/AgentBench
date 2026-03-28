"""Interactive trace viewer for deep-diving into agent runs.

Provides multiple views of a trace:
- Timeline: chronological event list with color coding and relative timestamps
- Filtered: events filtered by type, turn, or file path
- Turn detail: expanded view of a single turn with full content
- File tree: all files the agent touched, organized as a directory tree
- Token breakdown: per-turn token usage as a horizontal bar chart
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree

from agentbench.trace.events import EventType

if TYPE_CHECKING:
    from datetime import datetime

    from agentbench.trace.collector import TraceCollector
    from agentbench.trace.events import TraceEvent


# --- Event display config ---

EVENT_STYLES: dict[EventType, tuple[str, str]] = {
    EventType.AGENT_THINKING: ("💭", "dim"),
    EventType.AGENT_MESSAGE: ("💬", "bold"),
    EventType.TOOL_CALL: ("🔧", "cyan"),
    EventType.TOOL_RESULT: ("📋", "cyan dim"),
    EventType.FILE_READ: ("📖", "blue"),
    EventType.FILE_WRITE: ("✏️ ", "yellow"),
    EventType.FILE_CREATE: ("📄", "green"),
    EventType.FILE_DELETE: ("🗑️ ", "red"),
    EventType.COMMAND_EXEC: ("⚡", "cyan bold"),
    EventType.COMMAND_OUTPUT: ("📤", "dim"),
    EventType.TEST_RUN: ("🧪", "magenta"),
    EventType.TEST_RESULT: ("📊", ""),
    EventType.AGENT_START: ("🚀", "bold green"),
    EventType.AGENT_DONE: ("🏁", ""),
    EventType.CONSTRAINT_HIT: ("⛔", "bold red"),
    EventType.ERROR: ("❌", "bold red"),
    EventType.SEARCH: ("🔍", "blue"),
    EventType.DIRECTORY_LIST: ("📁", "blue dim"),
}


class TraceViewer:
    """Rich terminal display for agent execution traces."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def show_timeline(self, trace: TraceCollector) -> None:
        """Display a chronological timeline of all events grouped by turn."""
        events = trace.events
        if not events:
            self.console.print("[dim]No events in trace.[/dim]")
            return

        base_ts = events[0].timestamp

        # Group events by turn_number
        turns: dict[int, list[Any]] = {}
        for event in events:
            turns.setdefault(event.turn_number, []).append(event)

        for turn_num in sorted(turns.keys()):
            turn_events = turns[turn_num]
            lines = Text()
            for event in turn_events:
                line = self._format_event_line(event, base_ts)
                lines.append_text(line)
                lines.append("\n")
            self.console.print(Panel(lines, title=f"Turn {turn_num}", expand=False))

        # Summary
        total_tokens = sum(e.token_usage.total_tokens for e in events if e.token_usage)
        duration = (events[-1].timestamp - base_ts).total_seconds()
        self.console.print(
            f"Total: {len(turns)} turns, {len(events)} events, "
            f"{total_tokens:,} tokens, {duration:.1f}s"
        )

    def show_events(
        self,
        trace: TraceCollector,
        event_types: list[EventType] | None = None,
        file_path: str | None = None,
    ) -> None:
        """Show events filtered by type and/or file path."""
        all_events = trace.events
        filtered = list(all_events)

        if event_types is not None:
            filtered = [e for e in filtered if e.event_type in event_types]
        if file_path is not None:
            filtered = [e for e in filtered if e.data.get("path") == file_path]

        self.console.print(
            f"Showing {len(filtered)} events (filtered from {len(all_events)} total)"
        )

        if not all_events:
            return
        base_ts = all_events[0].timestamp
        for event in filtered:
            line = self._format_event_line(event, base_ts)
            self.console.print(line)

    def show_turn(self, trace: TraceCollector, turn_number: int) -> None:
        """Show all events for a specific turn in expanded detail."""
        all_events = trace.events
        turn_events = [e for e in all_events if e.turn_number == turn_number]

        if not turn_events:
            self.console.print(f"[dim]No events found for turn {turn_number}.[/dim]")
            return

        total_tokens = 0
        total_duration = 0

        for event in turn_events:
            et = event.event_type
            d = event.data

            if event.token_usage:
                total_tokens += event.token_usage.total_tokens
            total_duration += event.duration_ms

            if et == EventType.AGENT_THINKING:
                content = d.get("content", "")
                self.console.print(Panel(content, title="💭 Agent Thinking", style="dim"))

            elif et == EventType.FILE_READ:
                path = d.get("path", "")
                content = d.get("content", "")
                if content:
                    lexer = self._detect_lexer(path)
                    self.console.print(
                        Panel(
                            Syntax(content, lexer, theme="monokai", line_numbers=True),
                            title=f"📖 FILE READ: {path}",
                        )
                    )
                else:
                    lines_read = d.get("lines_read", d.get("size_bytes", 0))
                    self.console.print(
                        Panel(
                            f"[blue]{path}[/blue] ({lines_read} lines)",
                            title="📖 File Read",
                        )
                    )

            elif et == EventType.FILE_WRITE:
                path = d.get("path", "")
                diff_text = d.get("diff", "")
                if diff_text:
                    self.console.print(
                        Panel(
                            Syntax(diff_text, "diff"),
                            title=f"✏️  FILE WRITE: {path}",
                        )
                    )
                else:
                    lines_changed = d.get("lines_changed", d.get("size_bytes", 0))
                    self.console.print(
                        Panel(
                            f"[yellow]{path}[/yellow] ({lines_changed} lines changed)",
                            title="✏️  File Write",
                        )
                    )

            elif et == EventType.COMMAND_EXEC:
                cmd = d.get("command", "")
                self.console.print(Panel(f"[bold]$ {cmd}[/bold]", title="⚡ Command"))

            elif et == EventType.COMMAND_OUTPUT:
                stdout = d.get("stdout", "")
                stderr = d.get("stderr", "")
                if stdout:
                    self.console.print(Panel(stdout, title="stdout"))
                if stderr:
                    self.console.print(
                        Panel(f"[red]{stderr}[/red]", title="stderr", border_style="red")
                    )

            elif et == EventType.TEST_RESULT:
                passed = d.get("tests_passed", d.get("passed", 0))
                failed = d.get("tests_failed", d.get("failed", 0))
                skipped = d.get("tests_skipped", d.get("skipped", 0))
                output = d.get("output", "")
                failures = d.get("failures", [])

                summary_style = "green" if failed == 0 else "red"
                summary = (
                    f"[{summary_style}]{passed} passed[/{summary_style}],"
                    f" {failed} failed, {skipped} skipped"
                )
                content = summary
                if output:
                    content += f"\n\n{output}"
                self.console.print(Panel(content, title="📊 Test Result"))

                for failure_msg in failures:
                    self.console.print(
                        Panel(str(failure_msg), title="[red]Failure[/red]", border_style="red")
                    )

            elif et == EventType.TOOL_CALL:
                tool = d.get("tool", "")
                input_data = d.get("input", {})
                input_json = json.dumps(input_data, indent=2)
                self.console.print(
                    Panel(
                        Syntax(input_json, "json"),
                        title=f"🔧 Tool Call: {tool}",
                    )
                )

            else:
                # Generic fallback for other event types
                icon, style = EVENT_STYLES.get(et, ("•", ""))
                label = et.value.upper()
                self.console.print(f"  {icon} [bold]{label}[/bold]: {d}")

        self.console.print(
            f"\nTurn {turn_number}: {len(turn_events)} events, "
            f"{total_tokens:,} tokens, {total_duration}ms"
        )

    def show_files_touched(self, trace: TraceCollector) -> None:
        """Show a tree view of all files the agent interacted with."""
        file_ops: dict[str, dict[str, int]] = {}

        op_map = {
            EventType.FILE_READ: "reads",
            EventType.FILE_WRITE: "writes",
            EventType.FILE_CREATE: "creates",
            EventType.FILE_DELETE: "deletes",
        }

        for event in trace.events:
            if event.event_type in op_map:
                path = event.data.get("path", "")
                if path:
                    if path not in file_ops:
                        file_ops[path] = {"reads": 0, "writes": 0, "creates": 0, "deletes": 0}
                    file_ops[path][op_map[event.event_type]] += 1

        if not file_ops:
            self.console.print("[dim]No files touched.[/dim]")
            return

        # Build directory tree
        tree = Tree("workspace/")
        dir_nodes: dict[str, Any] = {"": tree}

        for file_path in sorted(file_ops.keys()):
            parts = Path(file_path).parts
            current_dir = ""
            for part in parts[:-1]:
                parent_dir = current_dir
                current_dir = str(Path(current_dir) / part) if current_dir else part
                if current_dir not in dir_nodes:
                    dir_nodes[current_dir] = dir_nodes[parent_dir].add(f"[bold]{part}/[/bold]")
            # Add file leaf
            ops = file_ops[file_path]
            op_parts = []
            if ops["reads"]:
                op_parts.append(f"[blue]READ ×{ops['reads']}[/blue]")
            if ops["writes"]:
                op_parts.append(f"[yellow]WRITE ×{ops['writes']}[/yellow]")
            if ops["creates"]:
                op_parts.append("[green]CREATED[/green]")
            if ops["deletes"]:
                op_parts.append("[red]DELETED[/red]")
            op_label = ", ".join(op_parts) if op_parts else ""
            filename = parts[-1] if parts else file_path
            parent_dir = str(Path(file_path).parent) if len(parts) > 1 else ""
            parent_node = dir_nodes.get(parent_dir, tree)
            parent_node.add(f"{filename}  [{op_label}]" if op_label else filename)

        self.console.print(tree)
        self.console.print(f"\nTotal unique files: {len(file_ops)}")

    def show_token_breakdown(self, trace: TraceCollector) -> None:
        """Show per-turn token usage as a horizontal bar chart."""
        events = trace.events
        if not events:
            self.console.print("[dim]No events.[/dim]")
            return

        turn_tokens: dict[int, int] = {}
        for event in events:
            if event.token_usage:
                t = event.turn_number
                turn_tokens[t] = turn_tokens.get(t, 0) + event.token_usage.total_tokens

        if not turn_tokens:
            self.console.print("[dim]No token usage recorded.[/dim]")
            return

        max_tokens = max(turn_tokens.values())
        max_bar = 40

        self.console.print("Token Usage by Turn")
        self.console.print("─" * 50)

        total = 0
        max_turn = max(turn_tokens, key=lambda t: turn_tokens[t])

        for turn_num in sorted(turn_tokens.keys()):
            count = turn_tokens[turn_num]
            total += count
            bar_width = int(count / max_tokens * max_bar) if max_tokens > 0 else 0
            bar = "█" * bar_width + "░" * (max_bar - bar_width)
            is_max = turn_num == max_turn
            suffix = " (max)" if is_max else ""
            style = "bold" if is_max else ""
            line = f"Turn {turn_num}:  {bar}  {count:,} tokens{suffix}"
            if style:
                self.console.print(f"[{style}]{line}[/{style}]")
            else:
                self.console.print(line)

        self.console.print("─" * 50)
        self.console.print(f"{'Total:':<10}{'':>{max_bar + 2}}  {total:,} tokens")

    def _format_relative_time(self, event: TraceEvent, base_ts: datetime) -> str:
        """Format an event's timestamp as MM:SS.mmm relative to base_ts."""
        delta = (event.timestamp - base_ts).total_seconds()
        minutes = int(delta // 60)
        seconds = delta % 60
        return f"{minutes:02d}:{seconds:06.3f}"

    def _format_event_line(self, event: TraceEvent, base_ts: datetime) -> Text:
        """Format a single event as a Rich Text line for timeline display."""
        icon, base_style = EVENT_STYLES.get(event.event_type, ("•", ""))

        # Dynamic styles for certain events
        style = base_style
        et = event.event_type
        d = event.data
        if et == EventType.TEST_RESULT:
            failed = d.get("tests_failed", d.get("failed", 0))
            style = "green" if failed == 0 else "red"
        elif et == EventType.AGENT_DONE:
            reason = d.get("reason", "")
            style = "bold green" if reason == "completed" else "yellow"

        ts = self._format_relative_time(event, base_ts)
        type_label = event.event_type.value.upper()
        summary = self._summarize_event(event)

        # Append token info if present
        token_info = ""
        if event.token_usage:
            token_info = f" [dim]({event.token_usage.total_tokens:,} tokens)[/dim]"

        text = Text()
        text.append(f"[{ts}] ", style="dim")
        text.append(f"{icon} ", style="")
        text.append(f"{type_label:<18} ", style=style or "")
        text.append(summary)
        if token_info:
            text.append(f" ({event.token_usage.total_tokens:,} tokens)", style="dim")  # type: ignore[union-attr]
        return text

    def _summarize_event(self, event: TraceEvent) -> str:
        """Return a brief summary string for an event."""
        d = event.data
        et = event.event_type

        if et == EventType.AGENT_THINKING:
            content = str(d.get("content", ""))
            return content[:60] + "…" if len(content) > 60 else content
        elif et in (EventType.FILE_READ, EventType.FILE_CREATE):
            lines = d.get("lines_read", d.get("size_bytes", 0))
            return f"{d.get('path', '')} ({lines} lines)"
        elif et == EventType.FILE_WRITE:
            lines = d.get("lines_changed", d.get("size_bytes", 0))
            return f"{d.get('path', '')} ({lines} lines changed)"
        elif et == EventType.FILE_DELETE:
            return str(d.get("path", ""))
        elif et == EventType.COMMAND_EXEC:
            cmd = str(d.get("command", ""))
            return cmd[:80] + "…" if len(cmd) > 80 else cmd
        elif et == EventType.TEST_RESULT:
            passed = d.get("tests_passed", d.get("passed", 0))
            failed = d.get("tests_failed", d.get("failed", 0))
            return f"{passed} passed, {failed} failed"
        elif et == EventType.AGENT_DONE:
            return str(d.get("reason", ""))
        elif et == EventType.CONSTRAINT_HIT:
            return str(d.get("constraint", ""))
        elif et == EventType.TOOL_CALL:
            tool = str(d.get("tool", ""))
            inp = str(d.get("input", ""))
            abbrev = inp[:40] + "…" if len(inp) > 40 else inp
            return f"{tool}: {abbrev}"
        elif et == EventType.AGENT_START:
            return str(d.get("agent_name", d.get("model", "")))
        elif et == EventType.ERROR:
            return str(d.get("message", ""))[:80]
        elif et == EventType.SEARCH:
            return str(d.get("query", ""))[:60]
        elif et == EventType.DIRECTORY_LIST:
            return str(d.get("path", ""))
        else:
            return str(d)[:60]

    def _detect_lexer(self, file_path: str) -> str:
        """Detect Rich Syntax lexer from file extension."""
        ext = Path(file_path).suffix.lower()
        mapping = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".java": "java",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown",
            ".sh": "bash",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
        }
        return mapping.get(ext, "text")
