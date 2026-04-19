from __future__ import annotations

import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

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
from coding_deepgent.sessions.service import recorded_session_store
from coding_deepgent.settings import Settings

from .event_mapping import runtime_events_to_frontend, todo_snapshot_from_state
from .protocol import (
    AssistantDeltaEvent,
    AssistantMessageEvent,
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


EventEmitter = Callable[[FrontendEvent], None]
PromptRunner = Callable[
    [str, list[dict[str, Any]], dict[str, Any], str, str, EventEmitter],
    PromptRunResult,
]


@dataclass
class BridgeSession:
    settings: Settings
    prompt_runner: PromptRunner
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: list[dict[str, Any]] = field(default_factory=list)
    session_state: dict[str, Any] = field(default_factory=default_runtime_state)
    started: bool = False

    def handle(self, request: FrontendInput, emit: EventEmitter) -> bool:
        if isinstance(request, SubmitPromptInput):
            self._handle_prompt(request, emit)
            return False
        if request.type == "permission_decision":
            emit(
                PermissionResolvedEvent(
                    request_id=request.request_id,
                    decision=request.decision,
                    message=request.message,
                )
            )
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

        for event in runtime_events_to_frontend(result.runtime_events):
            emit(event)
        emit(todo_snapshot_from_state(self.session_state))
        emit(AssistantMessageEvent(message_id=assistant_id, text=result.text))
        if result.recovery_brief:
            emit(RecoveryBriefEvent(text=result.recovery_brief))
        emit(RunFinishedEvent(session_id=self.session_id))


def build_default_prompt_runner(settings: Settings) -> PromptRunner:
    from coding_deepgent.app import agent_loop, build_agent, build_container, build_runtime_invocation

    container = build_container()
    event_sink = container.runtime.event_sink()
    emitted_events = 0

    def run_prompt(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        nonlocal emitted_events
        if not _force_nonstreaming():
            try:
                return _run_streaming_prompt(
                    settings=settings,
                    prompt=prompt,
                    history=history,
                    session_state=session_state,
                    session_id=session_id,
                    assistant_message_id=assistant_message_id,
                    emit=emit,
                    container=container,
                    event_sink=event_sink,
                    emitted_events=lambda: emitted_events,
                    set_emitted_events=lambda value: _set_emitted_events(value),
                    build_agent=build_agent,
                    build_runtime_invocation=build_runtime_invocation,
                )
            except (AttributeError, TypeError, NotImplementedError):
                pass

        result = cli_service.run_once(
            settings=settings,
            prompt=prompt,
            run_agent=partial(agent_loop, container=container),
            history=history,
            session_state=session_state,
            session_id=session_id,
        )
        snapshot = _event_sink_snapshot(event_sink)
        new_events = snapshot[emitted_events:]
        emitted_events = len(snapshot)
        return PromptRunResult(
            text=result,
            runtime_events=tuple(new_events),
            recovery_brief=_recovery_brief(settings, session_id),
        )

    def _set_emitted_events(value: int) -> None:
        nonlocal emitted_events
        emitted_events = value

    return run_prompt


def build_fake_prompt_runner() -> PromptRunner:
    def run_prompt(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit: EventEmitter,
    ) -> PromptRunResult:
        del session_id
        history.append({"role": "user", "content": prompt})
        emit(
            ToolStartedEvent(
                tool_call_id=f"fake-tool-{uuid.uuid4().hex[:8]}",
                name="fake_tool",
                summary="Preparing fake response.",
            )
        )
        if "permission" in prompt.lower():
            emit(
                PermissionRequestedEvent(
                    request_id=f"fake-permission-{uuid.uuid4().hex[:8]}",
                    tool="fake_write",
                    description="Fake permission request; no destructive action ran.",
                )
            )
        prefix = "Fake response: "
        for chunk in (prefix, prompt):
            emit(AssistantDeltaEvent(message_id=assistant_message_id, text=chunk))
        if "fail" in prompt.lower():
            raise RuntimeError("Fake streaming failure after partial output.")
        response = f"Fake response: {prompt}"
        history.append({"role": "assistant", "content": response})
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
        )

    return run_prompt



def _run_streaming_prompt(    *,
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
    context = _recording_context(settings, session_id, history)
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
    payload = {"messages": normalized, **session_payload(session_state)}
    compiled_agent = resolve_compiled_agent(container, build_agent)

    final_state: dict[str, Any] | None = None
    delta_text: list[str] = []
    for part in _stream_agent_parts(compiled_agent, payload, invocation):
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
    return PromptRunResult(
        text=final_text,
        recovery_brief=_recovery_brief(settings, session_id),
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
    payload: dict[str, Any],
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
    if part_type == "values" and isinstance(data, dict):
        return data
    return None


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
    try:
        loaded = cli_service.load_session(settings, session_id)
    except Exception:
        return None
    return cli_service.recovery_brief_text(loaded)


def _bounded_error(error: Exception) -> str:
    detail = " ".join(str(error).split()).strip()
    if not detail:
        detail = type(error).__name__
    return detail[:500]
