from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain.messages import ToolMessage
from langgraph.types import Command

from coding_deepgent.permissions import PermissionManager
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.tool_system import (
    ToolGuardMiddleware,
    ToolPolicy,
    build_default_registry,
)


def request(name: str, args: dict[str, object], sink: InMemoryEventSink | None = None):
    runtime = SimpleNamespace(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink or InMemoryEventSink(),
        )
    )
    return SimpleNamespace(
        tool_call={"name": name, "args": args, "id": "call-1"}, runtime=runtime
    )


def test_tool_guard_preserves_allowed_handler_return_values_and_events() -> None:
    registry = build_default_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)
    calls: list[str] = []

    def handler(_request: Any) -> Command:
        calls.append("called")
        return Command(update={"todos": []})

    result = middleware.wrap_tool_call(request("TodoWrite", {}, sink), handler)

    assert isinstance(result, Command)
    assert calls == ["called"]
    assert [event.kind for event in sink.snapshot()] == ["allowed", "completed"]


def test_tool_guard_blocks_ask_decisions_without_calling_handler() -> None:
    registry = build_default_registry()
    policy = ToolPolicy(
        registry=registry, permission_manager=PermissionManager(mode="default")
    )
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(registry=registry, policy=policy, event_sink=sink)

    result = middleware.wrap_tool_call(
        request("write_file", {"path": "README.md", "content": "x"}, sink),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "Approval required" in str(result.content)
    events = sink.snapshot()
    assert [event.kind for event in events] == ["permission_ask"]
    assert events[0].metadata["policy_code"] == "permission_required"


def test_tool_guard_denies_unknown_tools() -> None:
    registry = build_default_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        request("unknown", {}, sink),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert sink.snapshot()[0].metadata["policy_code"] == "unknown_tool"


def test_tool_guard_emits_permission_denied_for_unknown_and_dont_ask() -> None:
    registry = build_default_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=ToolPolicy(
            registry=registry, permission_manager=PermissionManager(mode="dontAsk")
        ),
        event_sink=sink,
    )

    result = middleware.wrap_tool_call(
        request("write_file", {"path": "README.md", "content": "x"}, sink),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "dontAsk mode" in str(result.content)
    assert sink.snapshot()[0].kind == "permission_denied"
