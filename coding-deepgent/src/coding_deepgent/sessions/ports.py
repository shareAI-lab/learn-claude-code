from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from .records import LoadedSession, SessionContext, SessionSummary


class SessionStore(Protocol):
    def create_session(
        self,
        *,
        workdir: Path,
        session_id: str | None = None,
        entrypoint: str | None = None,
    ) -> SessionContext: ...

    def append_message(
        self,
        context: SessionContext,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path: ...

    def append_state_snapshot(
        self,
        context: SessionContext,
        *,
        state: dict[str, Any],
    ) -> Path: ...

    def append_compact(
        self,
        context: SessionContext,
        *,
        trigger: str,
        summary: str,
        start_message_id: str,
        end_message_id: str,
        covered_message_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path: ...

    def append_collapse(
        self,
        context: SessionContext,
        *,
        trigger: str,
        summary: str,
        start_message_id: str,
        end_message_id: str,
        covered_message_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path: ...

    def load_session(
        self,
        *,
        session_id: str,
        workdir: Path,
        default_state_factory: Callable[[], dict[str, Any]] | None = None,
    ) -> LoadedSession: ...

    def list_sessions(self, *, workdir: Path) -> list[SessionSummary]: ...
