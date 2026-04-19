"""Frontend bridge contracts for external CLI/Web renderers."""

from .protocol import (
    AssistantMessageEvent,
    FrontendEvent,
    FrontendInput,
    ProtocolErrorEvent,
    RunFinishedEvent,
    RunFailedEvent,
    SessionStartedEvent,
    SubmitPromptInput,
    TodoSnapshotEvent,
    UserMessageEvent,
    parse_frontend_event,
    parse_frontend_input,
    serialize_frontend_event,
    dump_frontend_event,
)
from .client import FrontendClient
from .runs import FrontendRunManager, FrontendRunService, RunRecord, RunStatus
from .stream_bridge import END_SENTINEL, HEARTBEAT_SENTINEL, MemoryStreamBridge, StreamEntry

__all__ = [
    "AssistantMessageEvent",
    "FrontendEvent",
    "FrontendInput",
    "FrontendClient",
    "FrontendRunManager",
    "FrontendRunService",
    "RunRecord",
    "RunStatus",
    "StreamEntry",
    "MemoryStreamBridge",
    "HEARTBEAT_SENTINEL",
    "END_SENTINEL",
    "dump_frontend_event",
    "ProtocolErrorEvent",
    "RunFailedEvent",
    "RunFinishedEvent",
    "SessionStartedEvent",
    "SubmitPromptInput",
    "TodoSnapshotEvent",
    "UserMessageEvent",
    "parse_frontend_event",
    "parse_frontend_input",
    "serialize_frontend_event",
]
