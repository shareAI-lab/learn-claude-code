from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from coding_deepgent.runtime.events import RuntimeEventSink


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    session_id: str
    workdir: Path
    entrypoint: str
    agent_name: str
    event_sink: RuntimeEventSink
