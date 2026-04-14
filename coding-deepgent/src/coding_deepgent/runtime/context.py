from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from coding_deepgent.hooks.registry import LocalHookRegistry
from coding_deepgent.runtime.events import RuntimeEventSink

if TYPE_CHECKING:
    from coding_deepgent.sessions.records import SessionContext


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    session_id: str
    workdir: Path
    trusted_workdirs: tuple[Path, ...]
    entrypoint: str
    agent_name: str
    skill_dir: Path
    event_sink: RuntimeEventSink
    hook_registry: LocalHookRegistry = field(default_factory=LocalHookRegistry)
    session_context: SessionContext | None = None
