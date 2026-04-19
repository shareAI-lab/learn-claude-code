from __future__ import annotations

import json
from io import StringIO
from types import SimpleNamespace
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from coding_deepgent.frontend.bridge import (
    PromptRunResult,
    _run_streaming_prompt,
    run_jsonl_bridge,
)
from coding_deepgent.frontend.producer import PendingPermissionRequest
from coding_deepgent.frontend.protocol import FrontendEvent
from coding_deepgent.frontend.protocol import AssistantDeltaEvent, ToolFinishedEvent
from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        workdir=tmp_path / "workdir",
        session_dir=tmp_path / "sessions",
        model_name="gpt-test",
    )


def _events(output: StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_jsonl_bridge_runs_prompt_and_emits_ordered_events(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    def runner(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del assistant_message_id, emit
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": "done"})
        session_state["todos"] = [
            {
                "content": "Implement UI",
                "status": "in_progress",
                "activeForm": "Implementing UI",
            }
        ]
        return PromptRunResult(
            text=f"done for {session_id}",
            runtime_events=(
                RuntimeEvent(
                    kind="query_progress",
                    message="Query progressed.",
                    session_id=session_id,
                    metadata={"source": "test", "unsafe": {"nested": "ignored"}},
                ),
            ),
            recovery_brief="Recovery brief text.",
        )

    run_jsonl_bridge(
        ['{"type":"submit_prompt","text":"hello"}\n', '{"type":"exit"}\n'],
        output,
        settings=settings,
        prompt_runner=runner,
    )

    events = _events(output)
    assert [event["type"] for event in events] == [
        "session_started",
        "user_message",
        "runtime_event",
        "todo_snapshot",
        "assistant_message",
        "recovery_brief",
        "run_finished",
        "run_finished",
    ]
    assert events[2]["metadata"] == {"source": "test"}
    assert events[3]["items"] == [
        {
            "content": "Implement UI",
            "status": "in_progress",
            "activeForm": "Implementing UI",
        }
    ]
    assert events[4]["text"].startswith("done for ")


def test_jsonl_bridge_reports_protocol_errors_and_continues(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    def runner(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del history, session_state, session_id, assistant_message_id, emit
        return PromptRunResult(text=f"ok {prompt}")

    run_jsonl_bridge(
        ["not-json\n", '{"type":"submit_prompt","text":"hello"}\n'],
        output,
        settings=settings,
        prompt_runner=runner,
    )

    events = _events(output)
    assert events[0]["type"] == "protocol_error"
    assert any(event["type"] == "assistant_message" for event in events)


def test_jsonl_bridge_streams_runner_events_before_final_message(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    def runner(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del prompt, session_id
        history.append({"role": "user", "content": "stream"})
        emit(AssistantDeltaEvent(message_id=assistant_message_id, text="hel"))
        emit(AssistantDeltaEvent(message_id=assistant_message_id, text="lo"))
        emit(
            ToolFinishedEvent(
                tool_call_id="call-1",
                name="fake_tool",
                preview="finished during stream",
            )
        )
        session_state["todos"] = []
        return PromptRunResult(text="hello")

    run_jsonl_bridge(
        ['{"type":"submit_prompt","text":"stream"}\n'],
        output,
        settings=settings,
        prompt_runner=runner,
    )

    events = _events(output)
    assert [event["type"] for event in events] == [
        "session_started",
        "user_message",
        "assistant_delta",
        "assistant_delta",
        "tool_finished",
        "todo_snapshot",
        "assistant_message",
        "run_finished",
    ]
    assert events[2]["text"] == "hel"
    assert events[3]["text"] == "lo"


def test_jsonl_bridge_reports_failure_after_partial_stream(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    def runner(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del prompt, history, session_state, session_id
        emit(AssistantDeltaEvent(message_id=assistant_message_id, text="partial"))
        raise RuntimeError("boom")

    run_jsonl_bridge(
        ['{"type":"submit_prompt","text":"fail"}\n'],
        output,
        settings=settings,
        prompt_runner=runner,
    )

    events = _events(output)
    assert [event["type"] for event in events] == [
        "session_started",
        "user_message",
        "assistant_delta",
        "run_failed",
    ]
    assert events[-1]["error"] == "boom"


def test_fake_bridge_can_surface_permission_request(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    from coding_deepgent.frontend.bridge import build_fake_prompt_runner

    run_jsonl_bridge(
        ['{"type":"submit_prompt","text":"permission please"}\n'],
        output,
        settings=settings,
        prompt_runner=build_fake_prompt_runner(),
    )

    events = _events(output)
    permission = next(event for event in events if event["type"] == "permission_requested")
    assert permission["tool"] == "fake_write"
    assert permission["options"] == ["approve", "reject"]


def test_jsonl_bridge_resumes_after_permission_decision(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    output = StringIO()

    def runner(
        prompt: str,
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del prompt, history, session_state, session_id, assistant_message_id, emit
        return PromptRunResult(
            text="",
            pending_permissions=(
                PendingPermissionRequest(
                    request_id="perm-1",
                    tool="write_file",
                    description="Approval required before running `write_file`",
                ),
            ),
        )

    def resume_runner(
        decisions: dict[str, Any],
        history: list[dict[str, Any]],
        session_state: dict[str, Any],
        session_id: str,
        assistant_message_id: str,
        emit,
    ) -> PromptRunResult:
        del session_id
        assert decisions == {"perm-1": {"decision": "approve", "message": None}}
        emit(AssistantDeltaEvent(message_id=assistant_message_id, text="done"))
        history.append({"role": "assistant", "content": "done"})
        session_state["todos"] = []
        return PromptRunResult(text="done")

    run_jsonl_bridge(
        [
            '{"type":"submit_prompt","text":"ship it"}\n',
            '{"type":"permission_decision","request_id":"perm-1","decision":"approve"}\n',
        ],
        output,
        settings=settings,
        prompt_runner=runner,
        permission_resume_runner=resume_runner,
    )

    events = _events(output)
    assert [event["type"] for event in events] == [
        "session_started",
        "user_message",
        "permission_requested",
        "permission_resolved",
        "assistant_delta",
        "todo_snapshot",
        "assistant_message",
        "run_finished",
    ]
    assert events[2]["request_id"] == "perm-1"
    assert events[5]["items"] == []


def test_streaming_prompt_returns_pending_permission_requests(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    emitted: list[FrontendEvent] = []
    session_state: dict[str, Any] = {}
    history: list[dict[str, Any]] = []

    class FakeInterrupt:
        def __init__(self, *, id: str, value: dict[str, Any]) -> None:
            self.id = id
            self.value = value

    class FakeAgent:
        def stream(self, payload, **kwargs):
            del payload, kwargs
            yield {
                "type": "updates",
                "data": {
                    "__interrupt__": (
                        FakeInterrupt(
                            id="perm-1",
                            value={
                                "kind": "permission_request",
                                "tool": "write_file",
                                "description": "Approval required",
                                "options": ["approve", "reject"],
                            },
                        ),
                    )
                },
            }

    result = _run_streaming_prompt(
        settings=settings,
        prompt="hello",
        history=history,
        session_state=session_state,
        session_id="session-stream",
        assistant_message_id="assistant-1",
        emit=emitted.append,
        container=SimpleNamespace(),
        event_sink=SimpleNamespace(snapshot=lambda: ()),
        emitted_events=lambda: 0,
        set_emitted_events=lambda value: None,
        build_agent=lambda container=None: FakeAgent(),
        build_runtime_invocation=lambda **kwargs: SimpleNamespace(
            context=SimpleNamespace(session_id="session-stream"),
            config={"configurable": {"thread_id": "session-stream"}},
        ),
    )

    assert result.text == ""
    assert result.pending_permissions == (
        PendingPermissionRequest(
            request_id="perm-1",
            tool="write_file",
            description="Approval required",
        ),
    )
    assert emitted == []


def test_streaming_prompt_maps_langgraph_parts_to_frontend_events(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    emitted: list[FrontendEvent] = []
    session_state: dict[str, Any] = {}
    history: list[dict[str, Any]] = []

    class FakeAgent:
        def stream(self, payload, **kwargs):
            assert payload["messages"][-1]["content"] == "hello"
            assert kwargs["stream_mode"] == ["messages", "updates", "custom", "values"]
            yield {
                "type": "messages",
                "data": (AIMessageChunk(content="hel"), {"langgraph_node": "model"}),
            }
            yield {
                "type": "updates",
                "data": {
                    "model": {
                        "messages": [
                            AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": "read_file",
                                        "args": {"path": "README.md"},
                                        "id": "call-1",
                                    }
                                ],
                            )
                        ]
                    }
                },
            }
            yield {
                "type": "updates",
                "data": {
                    "tools": {
                        "messages": [
                            ToolMessage(content="ok", tool_call_id="call-1")
                        ]
                    }
                },
            }
            yield {
                "type": "messages",
                "data": (AIMessageChunk(content="lo"), {"langgraph_node": "model"}),
            }
            yield {
                "type": "values",
                "data": {
                    "messages": [AIMessage(content="hello")],
                    "todos": [
                        {
                            "content": "Stream response",
                            "status": "completed",
                            "activeForm": "Streaming response",
                        }
                    ],
                    "rounds_since_update": 3,
                },
            }

    result = _run_streaming_prompt(
        settings=settings,
        prompt="hello",
        history=history,
        session_state=session_state,
        session_id="session-stream",
        assistant_message_id="assistant-1",
        emit=emitted.append,
        container=SimpleNamespace(),
        event_sink=SimpleNamespace(snapshot=lambda: ()),
        emitted_events=lambda: 0,
        set_emitted_events=lambda value: None,
        build_agent=lambda container=None: FakeAgent(),
        build_runtime_invocation=lambda **kwargs: SimpleNamespace(
            context=SimpleNamespace(session_id="session-stream"),
            config={"configurable": {"thread_id": "session-stream"}},
        ),
    )

    assert result.text == "hello"
    assert [event.type for event in emitted] == [
        "assistant_delta",
        "tool_started",
        "tool_finished",
        "assistant_delta",
    ]
    assert session_state["todos"][0]["content"] == "Stream response"
    assert history[-1] == {"role": "assistant", "content": "hello"}
