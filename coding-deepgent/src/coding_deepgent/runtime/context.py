from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from coding_deepgent.hooks.registry import LocalHookRegistry
from coding_deepgent.runtime.events import RuntimeEventSink

if TYPE_CHECKING:
    from coding_deepgent.memory.service import MemoryService
    from coding_deepgent.sessions.records import SessionContext, TranscriptProjection
    from coding_deepgent.tool_system import ToolPoolProjection, ToolPolicy


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
    transcript_projection: TranscriptProjection | None = None
    model_context_window_tokens: int | None = None
    subagent_spawn_guard_ratio: float | None = None
    rendered_system_prompt: str | None = None
    visible_tool_projection: ToolPoolProjection | None = None
    tool_policy: ToolPolicy | None = None
    memory_service: MemoryService | None = None
