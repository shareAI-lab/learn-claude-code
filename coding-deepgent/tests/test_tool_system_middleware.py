from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain.messages import ToolMessage
from langgraph.types import Command

from coding_deepgent.hooks import HookPayload, HookResult, LocalHookRegistry
from coding_deepgent.memory import save_memory
from coding_deepgent.permissions import PermissionManager
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.skills import load_skill
from coding_deepgent.subagents import run_subagent
from coding_deepgent.tasks import task_create, task_get, task_list, task_update
from coding_deepgent.tool_system import (
    ToolCapability,
    ToolGuardMiddleware,
    ToolPolicy,
    build_builtin_capabilities,
    build_capability_registry,
)
from coding_deepgent.filesystem import bash, edit_file, glob_search, grep_search, read_file, write_file
from coding_deepgent.todo.tools import todo_write


def canonical_registry():
    return build_capability_registry(
        builtin_capabilities=build_builtin_capabilities(
            filesystem_tools=(bash, read_file, write_file, edit_file),
            discovery_tools=(glob_search, grep_search),
            todo_tools=(todo_write,),
            memory_tools=(save_memory,),
            skill_tools=(load_skill,),
            task_tools=(task_create, task_get, task_list, task_update),
            subagent_tools=(run_subagent,),
        ),
        extension_capabilities=(),
    )


def request(name: str, args: dict[str, object], sink: InMemoryEventSink | None = None):
    hook_registry = LocalHookRegistry()
    runtime = SimpleNamespace(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink or InMemoryEventSink(),
            hook_registry=hook_registry,
        )
    )
    return SimpleNamespace(
        tool_call={"name": name, "args": args, "id": "call-1"}, runtime=runtime
    )


def test_tool_guard_preserves_allowed_handler_return_values_and_events() -> None:
    registry = canonical_registry()
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
    registry = canonical_registry()
    policy = ToolPolicy(
        registry=registry,
        permission_manager=PermissionManager(mode="default", workdir=Path.cwd()),
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
    registry = canonical_registry()
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
    registry = canonical_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=ToolPolicy(
            registry=registry,
            permission_manager=PermissionManager(mode="dontAsk", workdir=Path.cwd()),
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


def test_tool_guard_blocks_untrusted_extension_destructive_tools() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    extension_capability = ToolCapability(
        name="mcp__docs__write",
        tool=registry.require("write_file").tool,
        domain="mcp",
        read_only=False,
        destructive=True,
        concurrency_safe=False,
        source="mcp:docs",
        trusted=False,
    )
    extended_registry = type(registry)(
        [*registry.metadata().values(), extension_capability]
    )
    policy = ToolPolicy(
        registry=extended_registry,
        permission_manager=PermissionManager(mode="acceptEdits", workdir=Path.cwd()),
    )
    middleware = ToolGuardMiddleware(
        registry=extended_registry,
        policy=policy,
        event_sink=sink,
    )

    result = middleware.wrap_tool_call(
        request("mcp__docs__write", {"path": "README.md", "content": "x"}, sink),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "untrusted extension" in str(result.content)
    assert sink.snapshot()[0].metadata["policy_code"] == "permission_required"


def test_tool_guard_pre_tool_hook_can_block_handler_and_emits_hook_events() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    req = request("write_file", {"path": "README.md", "content": "x"}, sink)
    req.runtime.context.hook_registry.register(
        "PreToolUse",
        lambda payload: HookResult.model_validate(
            {
                "continue": False,
                "decision": "block",
                "reason": f"blocked:{payload.data['tool']}",
            }
        ),
    )
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=ToolPolicy(
            registry=registry,
            permission_manager=PermissionManager(mode="acceptEdits", workdir=Path.cwd()),
        ),
        event_sink=sink,
    )

    result = middleware.wrap_tool_call(
        req,
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert "blocked:write_file" in str(result.content)
    assert [event.kind for event in sink.snapshot()] == ["hook_start", "hook_blocked"]


def test_tool_guard_post_tool_and_permission_denied_hooks_run() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    req = request("TodoWrite", {}, sink)
    seen: list[str] = []

    def on_post_tool_use(payload: HookPayload) -> HookResult:
        seen.append(f"post:{payload.data['tool']}")
        return HookResult()

    req.runtime.context.hook_registry.register("PostToolUse", on_post_tool_use)
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        req,
        lambda _request: Command(update={"todos": []}),
    )

    assert isinstance(result, Command)
    assert seen == ["post:TodoWrite"]
    assert [event.kind for event in sink.snapshot()] == [
        "allowed",
        "completed",
        "hook_start",
        "hook_complete",
    ]

    deny_req = request("write_file", {"path": "README.md", "content": "x"}, sink)
    deny_seen: list[str] = []

    def on_permission_denied(payload: HookPayload) -> HookResult:
        deny_seen.append(str(payload.data["tool"]))
        return HookResult()

    deny_req.runtime.context.hook_registry.register(
        "PermissionDenied", on_permission_denied
    )
    deny_middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    deny_result = deny_middleware.wrap_tool_call(
        deny_req,
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(deny_result, ToolMessage)
    assert deny_seen == ["write_file"]
