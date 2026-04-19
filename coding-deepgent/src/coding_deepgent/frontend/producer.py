from __future__ import annotations

import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Literal

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command

from coding_deepgent import cli_service
from coding_deepgent.agent_runtime_service import (
    resolve_compiled_agent,
    session_payload,
    supports_keyword_argument,
    update_session_state,
)
from coding_deepgent.compact import compact_record_from_messages, project_messages_with_stats
from coding_deepgent.rendering import latest_assistant_text
from coding_deepgent.runtime import RuntimeEvent, default_runtime_state
from coding_deepgent.sessions import LoadedSession
from coding_deepgent.sessions.service import recorded_session_store
from coding_deepgent.settings import Settings

from .event_mapping import (
    context_snapshot_from_loaded,
    runtime_events_to_frontend,
    subagent_snapshot_from_loaded,
    task_snapshot_from_store,
    todo_snapshot_from_state,
)
from .protocol import (
    AssistantDeltaEvent,
    AssistantMessageEvent,
    ContextSnapshotEvent,
    FrontendEvent,
    FrontendInput,
    PermissionResolvedEvent,
    PermissionRequestedEvent,
    ProtocolErrorEvent,
    RecoveryBriefEvent,
    RunFailedEvent,
    RunFinishedEvent,
    RuntimeEventPayload,
    SessionStartedEvent,
    SubmitPromptInput,
    SubagentSnapshotEvent,
    TaskItemPayload,
    TaskSnapshotEvent,
    ToolFailedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
    UserMessageEvent,
)


@dataclass(frozen=True)
class PromptRunResult:
    text: str
    runtime_events: tuple[RuntimeEvent, ...] = ()
    recovery_brief: str | None = None
    pending_permissions: tuple[PendingPermissionRequest, ...] = ()
    task_snapshot: tuple[TaskItemPayload, ...] = ()
    context_snapshot: ContextSnapshotEvent | None = None
    subagent_snapshot: SubagentSnapshotEvent | None = None


EventEmitter = Callable[[FrontendEvent], None]
PromptRunner = Callable[
    [str, list[dict[str, Any]], dict[str, Any], str, str, EventEmitter],
    PromptRunResult,
]
PermissionResumeRunner = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any], str, str, EventEmitter],
    PromptRunResult,
]

FRONTEND_HITL_ENTRYPOINT = "coding-deepgent-frontend"


@dataclass(frozen=True)
class PendingPermissionRequest:
    request_id: str
    tool: str
    description: str
    options: tuple[Literal["approve", "reject"], ...] = ("approve", "reject")


def _task_snapshot_items(container: Any) -> tuple[TaskItemPayload, ...]:
    runtime = getattr(container, "runtime", None)
    if runtime is None:
        return ()
    store_provider = getattr(runtime, "store", None)
    if not callable(store_provider):
        return ()
    try:
        store = store_provider()
    except Exception:
        return ()
    return tuple(task_snapshot_from_store(store).items)


@dataclass
class BridgeSession:
    settings: Settings
    prompt_runner: PromptRunner
    permission_resume_runner: PermissionResumeRunner | None = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: list[dict[str, Any]] = field(default_factory=list)
    session_state: dict[str, Any] = field(default_factory=default_runtime_state)
    pending_permission_requests: dict[str, PendingPermissionRequest] = field(
        default_factory=dict
    )
    pending_assistant_message_id: str | None = None
    started: bool = False

    def handle(self, request: FrontendInput, emit: EventEmitter) -> bool:
        if isinstance(request, SubmitPromptInput):
            self._handle_prompt(request, emit)
            return False
        if request.type == "permission_decision":
            self._handle_permission_decision(request, emit)
            return False
        if request.type == "interrupt":
            emit(
                RuntimeEventPayload(
                    kind="interrupt_requested",
                    message="Interrupt requested by frontend.",
                )
            )
            return False
        if request.type == "exit":
            emit(RunFinishedEvent(session_id=self.session_id, status="exited"))
            return True
        emit(ProtocolErrorEvent(error=f"unsupported input type: {request.type}"))
        return False

    def _handle_prompt(self, request: SubmitPromptInput, emit: EventEmitter) -> None:
        if not self.started:
            self.started = True
            emit(
                SessionStartedEvent(
                    session_id=self.session_id,
                    workdir=str(self.settings.workdir),
                )
            )

        user_id = f"user-{uuid.uuid4().hex[:12]}"
        assistant_id = f"assistant-{uuid.uuid4().hex[:12]}"
        emit(UserMessageEvent(id=user_id, text=request.text))
        try:
            result = self.prompt_runner(
                request.text,
                self.history,
                self.session_state,
                self.session_id,
                assistant_id,
                emit,
            )
        except Exception as exc:
            emit(
                RunFailedEvent(
                    session_id=self.session_id,
                    error=_bounded_error(exc),
                )
            )
            return

        if result.pending_permissions:
            self.pending_assistant_message_id = assistant_id
            self.pending_permission_requests = {
                permission.request_id: permission
                for permission in result.pending_permissions
            }
            for permission in result.pending_permissions:
                emit(
                    PermissionRequestedEvent(
                        request_id=permission.request_id,
                        tool=permission.tool,
                        description=permission.description,
                        options=list(permission.options),
                    )
                )
            return

        self.pending_assistant_message_id = None
        self.pending_permission_requests.clear()
        self._emit_completed_run(result, assistant_id=assistant_id, emit=emit)

    def _handle_permission_decision(self, request, emit: EventEmitter) -> None:
        pending = self.pending_permission_requests.get(request.request_id)
        if pending is None:
            emit(
                ProtocolErrorEvent(
                    error=f"Unknown permission request id: {request.request_id}"
                )
            )
            return

        emit(
            PermissionResolvedEvent(
                request_id=request.request_id,
                decision=request.decision,
                message=request.message,
            )
        )

        assistant_id = self.pending_assistant_message_id
        if assistant_id is None:
            self.pending_permission_requests.clear()
            emit(
                ProtocolErrorEvent(
                    error="Missing pending assistant message id for permission resume"
                )
            )
            return

        if self.permission_resume_runner is None:
            self.pending_permission_requests.pop(request.request_id, None)
            return

        try:
            result = self.permission_resume_runner(
                {
                    request.request_id: {
                        "decision": request.decision,
                        "message": request.message,
                    }
                },
                self.history,
                self.session_state,
                self.session_id,
                assistant_id,
                emit,
            )
        except Exception as exc:
            self.pending_assistant_message_id = None
            self.pending_permission_requests.clear()
            emit(
                RunFailedEvent(
                    session_id=self.session_id,
                    error=_bounded_error(exc),
                )
            )
            return

        if result.pending_permissions:
            self.pending_permission_requests = {
                permission.request_id: permission
                for permission in result.pending_permissions
            }
            for permission in result.pending_permissions:
                emit(
                    PermissionRequestedEvent(
                        request_id=permission.request_id,
                        tool=permission.tool,
                        description=permission.description,
                        options=list(permission.options),
                    )
                )
            return

        self.pending_assistant_message_id = None
        self.pending_permission_requests.clear()
        self._emit_completed_run(result, assistant_id=assistant_id, emit=emit)

    def _emit_completed_run(
        self,
        result: PromptRunResult,
        *,
        assistant_id: str,
        emit: EventEmitter,
    ) -> None:
        for event in runtime_events_to_frontend(result.runtime_events):
            emit(event)
        emit(todo_snapshot_from_state(self.session_state))
        emit(TaskSnapshotEvent(items=list(result.task_snapshot)))
        if result.context_snapshot is not None:
            emit(result.context_snapshot)
        if result.subagent_snapshot is not None:
            emit(result.subagent_snapshot)
        emit(AssistantMessageEvent(message_id=assistant_id, text=result.text))
        if result.recovery_brief:
            emit(RecoveryBriefEvent(text=result.recovery_brief))
        emit(RunFinishedEvent(session_id=self.session_id))


@dataclass
class _DefaultFrontendBridgeRunner:
    settings: Settings
    hitl: bool = False
    emitted_events: int = 0

    def __post_init__(self) -> None:
        self.settings = _frontend_runner_settings(self.settings, hitl=self.hitl)
        self.container = _build_container_for_settings(self.settings)
        from coding_deepgent.app import agent_loop, build_agent, build_runtime_invocation

        self._agent_loop = agent_loop
        self._build_agent = build_agent
        self._build_runtime_invocation = build_runtime_invocation
        self._event_sink = self.container.runtime.event_sink()

    def run_prompt(
        self,
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        if not _force_nonstreaming():
            try:
                return _run_streaming_prompt(
                    settings=self.settings,
                    prompt=prompt,
                    history=history,
                    session_state=session_state,
                    session_id=session_id,
                    assistant_message_id=assistant_message_id,
                    emit=emit,
                    container=self.container,
                    event_sink=self._event_sink,
                    emitted_events=lambda: self.emitted_events,
                    set_emitted_events=self._set_emitted_events,
                    build_agent=self._build_agent,
                    build_runtime_invocation=self._build_runtime_invocation,
                )
            except (AttributeError, TypeError, NotImplementedError):
                pass

        result = cli_service.run_once(
            settings=self.settings,
            prompt=prompt,
            run_agent=partial(self._agent_loop, container=self.container),
            history=history,
            session_state=session_state,
            session_id=session_id,
        )
        snapshot = _event_sink_snapshot(self._event_sink)
        new_events = snapshot[self.emitted_events :]
        self.emitted_events = len(snapshot)
        recovery_brief, context_snapshot, subagent_snapshot = _session_visibility(
            self.settings,
            session_id,
        )
        return PromptRunResult(
            text=result,
            runtime_events=tuple(new_events),
            recovery_brief=recovery_brief,
            task_snapshot=_task_snapshot_items(self.container),
            context_snapshot=context_snapshot,
            subagent_snapshot=subagent_snapshot,
        )

    def resume_permission(
        self,
        resume_values: dict[str, Any],
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        if _force_nonstreaming():
            raise RuntimeError("Frontend permission resume requires streaming mode.")
        return _resume_streaming_prompt(
            settings=self.settings,
            resume_values=resume_values,
            history=history,
            session_state=session_state,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
            emit=emit,
            container=self.container,
            event_sink=self._event_sink,
            emitted_events=lambda: self.emitted_events,
            set_emitted_events=self._set_emitted_events,
            build_agent=self._build_agent,
            build_runtime_invocation=self._build_runtime_invocation,
        )

    def _set_emitted_events(self, value: int) -> None:
        self.emitted_events = value


@dataclass
class _FakeFrontendBridgeRunner:
    pending_prompt: str | None = None

    def run_prompt(
        self,
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        del session_id
        history.append({"role": "user", "content": prompt})
        if "permission" in prompt.lower():
            self.pending_prompt = prompt
            return PromptRunResult(
                text="",
                pending_permissions=(
                    PendingPermissionRequest(
                        request_id=f"fake-permission-{uuid.uuid4().hex[:8]}",
                        tool="fake_write",
                        description="Fake permission request; no destructive action ran.",
                    ),
                ),
            )
        return self._complete_fake_prompt(
            prompt=prompt,
            assistant_message_id=assistant_message_id,
            session_state=session_state,
            emit=emit,
        )

    def resume_permission(
        self,
        resume_values: dict[str, Any],
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        del history, session_id
        prompt = self.pending_prompt or "permission"
        self.pending_prompt = None
        decision_payload: Any = next(iter(resume_values.values()), {})
        if isinstance(decision_payload, dict):
            decision = str(decision_payload.get("decision", "reject")).strip().lower()
            message = decision_payload.get("message")
        else:
            decision = str(decision_payload).strip().lower()
            message = None
        if decision != "approve":
            error = message if isinstance(message, str) and message else "Fake permission request rejected."
            emit(
                ToolFailedEvent(
                    tool_call_id="fake-write-call",
                    name="fake_write",
                    error=error,
                )
            )
            return PromptRunResult(
                text="Fake response: permission rejected.",
                runtime_events=(
                    RuntimeEvent(
                        kind="permission_denied",
                        message="Fake permission rejected.",
                        session_id="fake",
                        metadata={
                            "source": "frontend_bridge",
                            "tool": "fake_write",
                            "policy_code": "permission_required",
                            "permission_behavior": "ask",
                        },
                    ),
                ),
            )
        return self._complete_fake_prompt(
            prompt=prompt,
            assistant_message_id=assistant_message_id,
            session_state=session_state,
            emit=emit,
        )

    def _complete_fake_prompt(
        self,
        *,
        prompt: str,
        assistant_message_id: str,
        session_state: dict[str, Any],
        emit: EventEmitter,
    ) -> PromptRunResult:
        emit(
            ToolStartedEvent(
                tool_call_id=f"fake-tool-{uuid.uuid4().hex[:8]}",
                name="fake_tool",
                summary="Preparing fake response.",
            )
        )
        prefix = "Fake response: "
        for chunk in (prefix, prompt):
            emit(AssistantDeltaEvent(message_id=assistant_message_id, text=chunk))
        if "fail" in prompt.lower():
            raise RuntimeError("Fake streaming failure after partial output.")
        response = f"Fake response: {prompt}"
        session_state["todos"] = [
            {
                "content": "Review frontend request",
                "status": "completed",
                "activeForm": "Reviewing frontend request",
            },
            {
                "content": "Render CLI response",
                "status": "in_progress",
                "activeForm": "Rendering CLI response",
            },
        ]
        emit(
            ToolFinishedEvent(
                tool_call_id="fake-tool-complete",
                name="fake_tool",
                preview="Fake tool completed.",
            )
        )
        event = RuntimeEvent(
            kind="fake_prompt",
            message="Fake prompt completed through frontend bridge.",
            session_id="fake",
            metadata={"source": "frontend_bridge", "mode": "fake"},
        )
        return PromptRunResult(
            text=response,
            runtime_events=(event,),
            recovery_brief="Fake recovery brief: bridge protocol is healthy.",
            task_snapshot=(),
            context_snapshot=ContextSnapshotEvent(
                projection_mode="raw",
                history_messages=2,
                model_messages=2,
                visible_messages=2,
                hidden_messages=0,
                compact_count=0,
                collapse_count=0,
                session_memory_status="missing",
            ),
            subagent_snapshot=SubagentSnapshotEvent(total=0, items=[]),
        )


def build_default_bridge_runners(
    settings: Settings,
    *,
    hitl: bool = False,
) -> tuple[PromptRunner, PermissionResumeRunner]:
    runner = _DefaultFrontendBridgeRunner(settings=settings, hitl=hitl)
    return runner.run_prompt, runner.resume_permission


def build_default_prompt_runner(
    settings: Settings,
    *,
    hitl: bool = False,
) -> PromptRunner:
    return build_default_bridge_runners(settings, hitl=hitl)[0]


def build_fake_bridge_runners() -> tuple[PromptRunner, PermissionResumeRunner]:
    runner = _FakeFrontendBridgeRunner()
    return runner.run_prompt, runner.resume_permission


def build_fake_prompt_runner() -> PromptRunner:
    return build_fake_bridge_runners()[0]

def _run_streaming_prompt(
    *,
    settings: Settings,
    prompt: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    session_id: str,
    assistant_message_id: str,
    emit: EventEmitter,
    container: Any,
    event_sink: object,
    emitted_events: Callable[[], int],
    set_emitted_events: Callable[[int], None],
    build_agent: Callable[..., Any],
    build_runtime_invocation: Callable[..., Any],
) -> PromptRunResult:
    return _stream_graph_run(
        settings=settings,
        graph_input_factory=lambda normalized: {
            "messages": normalized,
            **session_payload(session_state),
        },
        prompt=prompt,
        history=history,
        session_state=session_state,
        session_id=session_id,
        assistant_message_id=assistant_message_id,
        emit=emit,
        container=container,
        event_sink=event_sink,
        emitted_events=emitted_events,
        set_emitted_events=set_emitted_events,
        build_agent=build_agent,
        build_runtime_invocation=build_runtime_invocation,
        append_user_prompt=True,
    )


def _resume_streaming_prompt(
    *,
    settings: Settings,
    resume_values: dict[str, Any],
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    session_id: str,
    assistant_message_id: str,
    emit: EventEmitter,
    container: Any,
    event_sink: object,
    emitted_events: Callable[[], int],
    set_emitted_events: Callable[[int], None],
    build_agent: Callable[..., Any],
    build_runtime_invocation: Callable[..., Any],
) -> PromptRunResult:
    return _stream_graph_run(
        settings=settings,
        graph_input_factory=lambda _normalized: Command(resume=resume_values),
        prompt=None,
        history=history,
        session_state=session_state,
        session_id=session_id,
        assistant_message_id=assistant_message_id,
        emit=emit,
        container=container,
        event_sink=event_sink,
        emitted_events=emitted_events,
        set_emitted_events=set_emitted_events,
        build_agent=build_agent,
        build_runtime_invocation=build_runtime_invocation,
        append_user_prompt=False,
    )


def _stream_graph_run(
    *,
    settings: Settings,
    graph_input_factory: Callable[[list[dict[str, Any]]], Any],
    prompt: str | None,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    session_id: str,
    assistant_message_id: str,
    emit: EventEmitter,
    container: Any,
    event_sink: object,
    emitted_events: Callable[[], int],
    set_emitted_events: Callable[[int], None],
    build_agent: Callable[..., Any],
    build_runtime_invocation: Callable[..., Any],
    append_user_prompt: bool,
) -> PromptRunResult:
    context = _recording_context(settings, session_id, history)
    if append_user_prompt and prompt is not None:
        history.append({"role": "user", "content": prompt})
        context.store.append_message(context.session, role="user", content=prompt)

    invocation = build_runtime_invocation(
        container=container,
        session_id=session_id,
        session_context=context.session,
    )
    projection_result = project_messages_with_stats(history)
    normalized = projection_result.messages
    if projection_result.repair_stats.orphan_tombstoned:
        emit(
            RuntimeEventPayload(
                kind="orphan_tombstoned",
                message="Projection repair tombstoned orphaned tool result material.",
                metadata={
                    "source": "message_projection",
                    "tombstoned_count": projection_result.repair_stats.orphan_tombstoned,
                },
            )
        )
    compiled_agent = resolve_compiled_agent(container, build_agent)

    final_state: dict[str, Any] | None = None
    delta_text: list[str] = []
    graph_input = graph_input_factory(normalized)
    for part in _stream_agent_parts(compiled_agent, graph_input, invocation):
        pending_permissions = _pending_permissions_from_stream_part(part)
        if pending_permissions:
            return PromptRunResult(
                text="",
                pending_permissions=tuple(pending_permissions),
            )
        for frontend_event in _frontend_events_from_stream_part(
            part, assistant_message_id=assistant_message_id
        ):
            emit(frontend_event)
            if isinstance(frontend_event, AssistantDeltaEvent):
                delta_text.append(frontend_event.text)
        snapshot = _event_sink_snapshot(event_sink)
        new_events = snapshot[emitted_events():]
        if new_events:
            for event in runtime_events_to_frontend(new_events):
                emit(event)
            set_emitted_events(len(snapshot))
        state = _state_from_stream_part(part)
        if state is not None:
            final_state = state

    if final_state is not None:
        update_session_state(session_state, final_state)
    final_text = latest_assistant_text(final_state) if final_state is not None else ""
    if not final_text:
        final_text = "".join(delta_text).strip()
    if final_text:
        history.append({"role": "assistant", "content": final_text})
        context.store.append_message(context.session, role="assistant", content=final_text)
    context.store.append_state_snapshot(context.session, state=session_state)
    context.store.append_evidence(
        context.session,
        kind="runtime",
        summary="Prompt completed through coding-deepgent streaming frontend bridge.",
        status="completed",
        subject="frontend.ui_bridge.stream",
    )
    recovery_brief, context_snapshot, subagent_snapshot = _session_visibility(
        settings,
        session_id,
    )
    return PromptRunResult(
        text=final_text,
        recovery_brief=recovery_brief,
        task_snapshot=_task_snapshot_items(container),
        context_snapshot=context_snapshot,
        subagent_snapshot=subagent_snapshot,
    )


@dataclass(frozen=True)
class _RecordingContext:
    store: Any
    session: Any


def _recording_context(
    settings: Settings,
    session_id: str,
    history: list[dict[str, Any]],
) -> _RecordingContext:
    store = recorded_session_store(settings)
    session = store.create_session(
        workdir=settings.workdir,
        session_id=session_id,
        entrypoint=settings.entrypoint,
    )
    compact_record = compact_record_from_messages(history)
    if compact_record is not None:
        store.append_compact(session, **compact_record)
    return _RecordingContext(store=store, session=session)


def _stream_agent_parts(
    compiled_agent: Any,
    payload: Any,
    invocation: Any,
) -> Iterable[Any]:
    stream = compiled_agent.stream
    kwargs: dict[str, Any] = {
        "stream_mode": ["messages", "updates", "custom", "values"],
    }
    if supports_keyword_argument(stream, "version"):
        kwargs["version"] = "v2"
    if supports_keyword_argument(stream, "context"):
        kwargs["context"] = invocation.context
    if supports_keyword_argument(stream, "config"):
        kwargs["config"] = invocation.config
    return stream(payload, **kwargs)


def _frontend_events_from_stream_part(
    part: Any, *, assistant_message_id: str
) -> list[FrontendEvent]:
    part_type, data = _stream_part_type_and_data(part)
    if part_type == "messages":
        chunk, _metadata = data
        text = _message_chunk_text(chunk)
        return (
            [AssistantDeltaEvent(message_id=assistant_message_id, text=text)]
            if text
            else []
        )
    if part_type == "updates":
        return _events_from_update_data(data)
    if part_type == "custom":
        return [
            RuntimeEventPayload(
                kind="custom",
                message=_bounded_custom_message(data),
            )
        ]
    return []


def _stream_part_type_and_data(part: Any) -> tuple[str, Any]:
    if isinstance(part, dict) and "type" in part:
        return str(part.get("type")), part.get("data")
    if isinstance(part, tuple) and len(part) == 2:
        return str(part[0]), part[1]
    return "unknown", part


def _state_from_stream_part(part: Any) -> dict[str, Any] | None:
    part_type, data = _stream_part_type_and_data(part)
    if part_type == "values" and isinstance(data, dict) and "__interrupt__" not in data:
        return data
    return None


def _pending_permissions_from_stream_part(
    part: Any,
) -> list[PendingPermissionRequest]:
    part_type, data = _stream_part_type_and_data(part)
    if part_type not in {"updates", "values"} or not isinstance(data, dict):
        return []
    return _pending_permissions_from_interrupts(data.get("__interrupt__"))


def _pending_permissions_from_interrupts(
    raw_interrupts: Any,
) -> list[PendingPermissionRequest]:
    if isinstance(raw_interrupts, tuple | list):
        interrupts = list(raw_interrupts)
    elif raw_interrupts is None:
        return []
    else:
        interrupts = [raw_interrupts]

    requests: list[PendingPermissionRequest] = []
    for interrupt in interrupts:
        request_id = getattr(interrupt, "id", None)
        payload = getattr(interrupt, "value", None)
        if not isinstance(request_id, str) or not request_id.strip():
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("kind") != "permission_request":
            continue
        tool = payload.get("tool")
        description = payload.get("description")
        options = payload.get("options", ("approve", "reject"))
        if not isinstance(tool, str) or not isinstance(description, str):
            continue
        normalized_options = tuple(
            option for option in options if option in {"approve", "reject"}
        )
        requests.append(
            PendingPermissionRequest(
                request_id=request_id,
                tool=tool,
                description=description,
                options=normalized_options or ("approve", "reject"),
            )
        )
    return requests


def _events_from_update_data(data: Any) -> list[FrontendEvent]:
    events: list[FrontendEvent] = []
    if not isinstance(data, dict):
        return events
    for node_name, update in data.items():
        if not isinstance(update, dict):
            continue
        messages = update.get("messages")
        if isinstance(messages, list) and messages:
            events.extend(_events_from_messages(node_name=str(node_name), messages=messages))
    return events


def _events_from_messages(*, node_name: str, messages: list[Any]) -> list[FrontendEvent]:
    events: list[FrontendEvent] = []
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                tool_id = str(tool_call.get("id") or f"{node_name}:tool")
                name = str(tool_call.get("name") or "tool")
                events.append(
                    ToolStartedEvent(
                        tool_call_id=tool_id,
                        name=name,
                        summary=f"{name} requested by model.",
                    )
                )
        elif isinstance(message, ToolMessage):
            tool_call_id = str(getattr(message, "tool_call_id", "") or f"{node_name}:tool")
            status = getattr(message, "status", None)
            content = str(getattr(message, "content", "") or "")
            if status == "error":
                events.append(
                    ToolFailedEvent(
                        tool_call_id=tool_call_id,
                        name=str(getattr(message, "name", None) or "tool"),
                        error=content[:500],
                    )
                )
            else:
                events.append(
                    ToolFinishedEvent(
                        tool_call_id=tool_call_id,
                        name=str(getattr(message, "name", None) or "tool"),
                        preview=content[:500],
                    )
                )
    return events


def _message_chunk_text(chunk: Any) -> str:
    if isinstance(chunk, AIMessageChunk):
        return _content_text(chunk.content)
    content_blocks = getattr(chunk, "content_blocks", None)
    if isinstance(content_blocks, list):
        return "".join(
            str(block.get("text", ""))
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
        )
    content = getattr(chunk, "content", None)
    return _content_text(content)


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    texts.append(text)
        return "".join(texts)
    return ""


def _bounded_custom_message(data: Any) -> str:
    if isinstance(data, str):
        return data[:500]
    return str(data)[:500]


def _force_nonstreaming() -> bool:
    value = str(sys.argv).lower()
    return "--non-streaming" in value


def _event_sink_snapshot(event_sink: object) -> tuple[RuntimeEvent, ...]:
    snapshot = getattr(event_sink, "snapshot", None)
    if callable(snapshot):
        return tuple(snapshot())
    return ()


def _recovery_brief(settings: Settings, session_id: str) -> str | None:
    loaded = _loaded_session_or_none(settings, session_id)
    if loaded is None:
        return None
    return cli_service.recovery_brief_text(loaded)


def _session_visibility(
    settings: Settings,
    session_id: str,
) -> tuple[str | None, ContextSnapshotEvent | None, SubagentSnapshotEvent | None]:
    loaded = _loaded_session_or_none(settings, session_id)
    if loaded is None:
        return None, None, None
    return (
        cli_service.recovery_brief_text(loaded),
        context_snapshot_from_loaded(loaded),
        subagent_snapshot_from_loaded(loaded),
    )


def _loaded_session_or_none(
    settings: Settings,
    session_id: str,
) -> LoadedSession | None:
    try:
        return cli_service.load_session(settings, session_id)
    except Exception:
        return None


def _bounded_error(error: Exception) -> str:
    detail = " ".join(str(error).split()).strip()
    if not detail:
        detail = type(error).__name__
    return detail[:500]


def _frontend_runner_settings(settings: Settings, *, hitl: bool) -> Settings:
    if not hitl:
        return settings
    updates: dict[str, Any] = {"entrypoint": FRONTEND_HITL_ENTRYPOINT}
    if settings.checkpointer_backend == "none":
        updates["checkpointer_backend"] = "memory"
    return settings.model_copy(update=updates)


def _build_container_for_settings(settings: Settings) -> Any:
    from langchain.agents import create_agent

    from coding_deepgent import bootstrap
    from coding_deepgent.settings import build_openai_model

    container = bootstrap.build_container(
        settings_loader=lambda: settings,
        model_factory=build_openai_model,
        create_agent_factory=create_agent,
    )
    bootstrap.validate_container_startup(container=container)
    return container
