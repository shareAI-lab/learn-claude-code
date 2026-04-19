from __future__ import annotations

import json
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TodoItemPayload(StrictModel):
    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: str | None = None


class TaskItemPayload(StrictModel):
    id: str
    content: str
    status: str
    owner: str | None = None


class SessionStartedEvent(StrictModel):
    type: Literal["session_started"] = "session_started"
    session_id: str
    workdir: str


class UserMessageEvent(StrictModel):
    type: Literal["user_message"] = "user_message"
    id: str
    text: str


class AssistantDeltaEvent(StrictModel):
    type: Literal["assistant_delta"] = "assistant_delta"
    message_id: str
    text: str


class AssistantMessageEvent(StrictModel):
    type: Literal["assistant_message"] = "assistant_message"
    message_id: str
    text: str


class ToolStartedEvent(StrictModel):
    type: Literal["tool_started"] = "tool_started"
    tool_call_id: str
    name: str
    summary: str = ""


class ToolFinishedEvent(StrictModel):
    type: Literal["tool_finished"] = "tool_finished"
    tool_call_id: str
    name: str
    status: Literal["success"] = "success"
    preview: str = ""


class ToolFailedEvent(StrictModel):
    type: Literal["tool_failed"] = "tool_failed"
    tool_call_id: str
    name: str
    error: str


class PermissionRequestedEvent(StrictModel):
    type: Literal["permission_requested"] = "permission_requested"
    request_id: str
    tool: str
    description: str
    options: list[Literal["approve", "reject"]] = Field(
        default_factory=lambda: _default_permission_options()
    )


class PermissionResolvedEvent(StrictModel):
    type: Literal["permission_resolved"] = "permission_resolved"
    request_id: str
    decision: Literal["approve", "reject"]
    message: str | None = None


class TodoSnapshotEvent(StrictModel):
    type: Literal["todo_snapshot"] = "todo_snapshot"
    items: list[TodoItemPayload]


class TaskSnapshotEvent(StrictModel):
    type: Literal["task_snapshot"] = "task_snapshot"
    items: list[TaskItemPayload]


class ContextSnapshotEvent(StrictModel):
    type: Literal["context_snapshot"] = "context_snapshot"
    projection_mode: Literal["raw", "compact", "collapse"]
    history_messages: int = Field(..., ge=0)
    model_messages: int = Field(..., ge=0)
    visible_messages: int = Field(..., ge=0)
    hidden_messages: int = Field(..., ge=0)
    compact_count: int = Field(..., ge=0)
    collapse_count: int = Field(..., ge=0)
    session_memory_status: Literal["missing", "current", "stale"]
    latest_event: str | None = None


class SubagentItemPayload(StrictModel):
    created_at: str
    agent_type: str
    role: str
    content: str
    subagent_thread_id: str


class SubagentSnapshotEvent(StrictModel):
    type: Literal["subagent_snapshot"] = "subagent_snapshot"
    total: int = Field(..., ge=0)
    items: list[SubagentItemPayload]


class BackgroundSubagentItemPayload(StrictModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    mode: Literal["background_subagent", "background_fork"]
    agent_type: str
    progress_summary: str
    pending_inputs: int = Field(..., ge=0)
    total_invocations: int = Field(..., ge=0)


class BackgroundSubagentSnapshotEvent(StrictModel):
    type: Literal["background_subagent_snapshot"] = "background_subagent_snapshot"
    total: int = Field(..., ge=0)
    items: list[BackgroundSubagentItemPayload]


class RuntimeEventPayload(StrictModel):
    type: Literal["runtime_event"] = "runtime_event"
    kind: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecoveryBriefEvent(StrictModel):
    type: Literal["recovery_brief"] = "recovery_brief"
    text: str


class RunFinishedEvent(StrictModel):
    type: Literal["run_finished"] = "run_finished"
    session_id: str
    status: Literal["completed", "exited"] = "completed"


class RunFailedEvent(StrictModel):
    type: Literal["run_failed"] = "run_failed"
    session_id: str
    error: str


class ProtocolErrorEvent(StrictModel):
    type: Literal["protocol_error"] = "protocol_error"
    error: str


FrontendEvent: TypeAlias = Annotated[
    SessionStartedEvent
    | UserMessageEvent
    | AssistantDeltaEvent
    | AssistantMessageEvent
    | ToolStartedEvent
    | ToolFinishedEvent
    | ToolFailedEvent
    | PermissionRequestedEvent
    | PermissionResolvedEvent
    | TodoSnapshotEvent
    | TaskSnapshotEvent
    | ContextSnapshotEvent
    | SubagentSnapshotEvent
    | BackgroundSubagentSnapshotEvent
    | RuntimeEventPayload
    | RecoveryBriefEvent
    | RunFinishedEvent
    | RunFailedEvent
    | ProtocolErrorEvent,
    Field(discriminator="type"),
]


class SubmitPromptInput(StrictModel):
    type: Literal["submit_prompt"] = "submit_prompt"
    text: str


class PermissionDecisionInput(StrictModel):
    type: Literal["permission_decision"] = "permission_decision"
    request_id: str
    decision: Literal["approve", "reject"]
    message: str | None = None


class InterruptInput(StrictModel):
    type: Literal["interrupt"] = "interrupt"


class ExitInput(StrictModel):
    type: Literal["exit"] = "exit"


class RefreshSnapshotsInput(StrictModel):
    type: Literal["refresh_snapshots"] = "refresh_snapshots"


class RunBackgroundSubagentControlInput(StrictModel):
    type: Literal["run_background_subagent"] = "run_background_subagent"
    task: str = Field(..., min_length=1)
    agent_type: str = "general"
    plan_id: str | None = Field(default=None, min_length=1)
    max_turns: int = Field(default=25, ge=1, le=25)


class SubagentSendInputControl(StrictModel):
    type: Literal["subagent_send_input"] = "subagent_send_input"
    run_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class SubagentStopInputControl(StrictModel):
    type: Literal["subagent_stop"] = "subagent_stop"
    run_id: str = Field(..., min_length=1)


FrontendInput: TypeAlias = Annotated[
    SubmitPromptInput
    | PermissionDecisionInput
    | InterruptInput
    | ExitInput
    | RefreshSnapshotsInput
    | RunBackgroundSubagentControlInput
    | SubagentSendInputControl
    | SubagentStopInputControl,
    Field(discriminator="type"),
]


_EVENT_ADAPTER: TypeAdapter[FrontendEvent] = TypeAdapter(FrontendEvent)
_INPUT_ADAPTER: TypeAdapter[FrontendInput] = TypeAdapter(FrontendInput)


def _default_permission_options() -> list[Literal["approve", "reject"]]:
    return ["approve", "reject"]


def parse_frontend_event(payload: str | bytes | dict[str, Any]) -> FrontendEvent:
    raw = _coerce_json_payload(payload)
    return _EVENT_ADAPTER.validate_python(raw)


def parse_frontend_input(payload: str | bytes | dict[str, Any]) -> FrontendInput:
    raw = _coerce_json_payload(payload)
    return _INPUT_ADAPTER.validate_python(raw)


def serialize_frontend_event(event: FrontendEvent) -> str:
    return _EVENT_ADAPTER.dump_json(event, exclude_none=True).decode("utf-8")


def dump_frontend_event(event: FrontendEvent) -> dict[str, Any]:
    payload = _EVENT_ADAPTER.dump_python(event, exclude_none=True)
    if not isinstance(payload, dict):
        raise ValueError("frontend event payload must serialize to an object")
    return payload


def _coerce_json_payload(payload: str | bytes | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON payload: {exc.msg}") from exc
    if not isinstance(decoded, dict):
        raise ValueError("frontend protocol payload must be a JSON object")
    return decoded


def protocol_error_from_exception(error: Exception) -> ProtocolErrorEvent:
    if isinstance(error, ValidationError):
        detail = error.errors()[0].get("msg", "validation error")
        return ProtocolErrorEvent(error=str(detail))
    return ProtocolErrorEvent(error=str(error) or type(error).__name__)
