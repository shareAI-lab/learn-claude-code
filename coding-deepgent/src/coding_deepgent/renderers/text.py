from __future__ import annotations

from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

_RENDER_WIDTH = 140


def _render_table(table: Table) -> str:
    stream = StringIO()
    console = Console(
        file=stream,
        color_system=None,
        force_terminal=False,
        record=True,
        width=_RENDER_WIDTH,
    )
    console.print(table)
    return console.export_text(styles=False).rstrip()


def render_config_table(rows: Sequence[tuple[str, str]]) -> str:
    table = Table(title="Configuration", box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for key, value in rows:
        table.add_row(key, value)
    return _render_table(table)


def render_session_table(sessions: Sequence[Mapping[str, Any]]) -> str:
    if not sessions:
        return "No sessions recorded yet."

    table = Table(title="Sessions", box=box.SIMPLE_HEAVY)
    table.add_column("Session", style="cyan", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Messages", justify="right", no_wrap=True)
    table.add_column("Workdir")
    for session in sessions:
        table.add_row(
            str(session.get("session_id", "unknown")),
            str(session.get("updated_at", "-")),
            str(session.get("message_count", 0)),
            str(session.get("workdir", "-")),
        )
    return _render_table(table)


def render_doctor_table(checks: Sequence[Mapping[str, Any]]) -> str:
    table = Table(title="Doctor", box=box.SIMPLE_HEAVY)
    table.add_column("Check", style="cyan", no_wrap=True, overflow="fold")
    table.add_column("Status", no_wrap=True, overflow="fold")
    table.add_column("Detail", overflow="fold")
    for check in checks:
        table.add_row(
            str(check.get("name", "unknown")),
            str(check.get("status", "unknown")),
            str(check.get("detail", "")),
        )
    return _render_table(table)
