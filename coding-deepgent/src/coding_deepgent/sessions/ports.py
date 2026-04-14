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
        message_index: int | None = None,
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
        original_message_count: int,
        summarized_message_count: int,
        kept_message_count: int,
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
