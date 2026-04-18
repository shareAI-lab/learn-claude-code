from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain.messages import ToolMessage
from langchain.tools import tool
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from coding_deepgent.hooks import HookPayload, HookResult, LocalHookRegistry
from coding_deepgent.memory import MemoryRecord, save_memory, save_memory_record
from coding_deepgent.permissions import PermissionManager
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.sessions import JsonlSessionStore, build_recovery_brief, render_recovery_brief
from coding_deepgent.skills import load_skill
from coding_deepgent.subagents import run_subagent
from coding_deepgent.tasks import (
    plan_get,
    plan_save,
    task_create,
    task_get,
    task_list,
    task_update,
)
from coding_deepgent.tool_system import (
    ToolCapability,
    ToolGuardMiddleware,
    ToolPolicy,
    build_builtin_capabilities,
    build_capability_registry,
)
from coding_deepgent.filesystem import bash, edit_file, glob_search, grep_search, read_file, write_file
from coding_deepgent.todo.tools import todo_write


@tool("mcp__docs__write", description="Write docs through MCP.")
def mcp_docs_write(path: str, content: str) -> str:
    return f"wrote {path}: {content}"


def canonical_registry():
    return build_capability_registry(
        builtin_capabilities=build_builtin_capabilities(
            filesystem_tools=(bash, read_file, write_file, edit_file),
            discovery_tools=(glob_search, grep_search),
            todo_tools=(todo_write,),
            memory_tools=(save_memory,),
            skill_tools=(load_skill,),
            task_tools=(
                task_create,
                task_get,
                task_list,
                task_update,
                plan_save,
                plan_get,
            ),
            subagent_tools=(run_subagent,),
        ),
        extension_capabilities=(),
    )


def request(
    name: str,
    args: dict[str, object],
    sink: InMemoryEventSink | None = None,
    *,
    store: object | None = None,
):
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
        ),
        store=store,
    )
    return SimpleNamespace(
        tool_call={"name": name, "args": args, "id": "call-1"}, runtime=runtime
    )


def request_with_session_context(
    name: str,
    args: dict[str, object],
    *,
    session_store: JsonlSessionStore,
    workdir: Path,
    sink: InMemoryEventSink | None = None,
):
    session_context = session_store.create_session(
        workdir=workdir, session_id="session-1"
    )
    session_store.append_message(session_context, role="user", content="start")
    hook_registry = LocalHookRegistry()
    runtime = SimpleNamespace(
        context=RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=workdir / "skills",
            event_sink=sink or InMemoryEventSink(),
            hook_registry=hook_registry,
            session_context=session_context,
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


def test_tool_guard_persists_large_tool_output_for_eligible_tools(tmp_path: Path) -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=ToolPolicy(
            registry=registry,
            permission_manager=PermissionManager(mode="default", workdir=tmp_path),
        ),
        event_sink=sink,
    )
    req = request("read_file", {"path": "README.md"}, sink)
    req.runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=tmp_path,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="test-agent",
        skill_dir=tmp_path / "skills",
        event_sink=sink,
        hook_registry=LocalHookRegistry(),
    )

    result = middleware.wrap_tool_call(
        req,
        lambda _request: ToolMessage(content="x" * 5000, tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert ".coding-deepgent/tool-results/session-1/call-1.txt" in str(result.content)
    stored = tmp_path / ".coding-deepgent" / "tool-results" / "session-1" / "call-1.txt"
    assert stored.exists()
    assert stored.read_text(encoding="utf-8") == "x" * 5000


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


def test_tool_guard_blocks_git_commit_when_feedback_requires_lint_first() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        request("bash", {"command": "git commit -m 'x'"}, sink, store=store),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "Run lint first" in str(result.content)
    events = sink.snapshot()
    assert [event.kind for event in events] == ["feedback_blocked"]
    assert events[0].metadata["policy_code"] == "permission_denied"


def test_tool_guard_blocks_dependency_file_edits_when_feedback_requires_confirmation() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Confirm before dependency changes",
            why="Dependency edits can trigger version conflicts",
            how_to_apply="Stop and confirm before changing package.json or install dependencies",
        ),
    )
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        request(
            "write_file",
            {"path": "package.json", "content": "{}"},
            sink,
            store=store,
        ),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "confirmation before dependency changes" in str(result.content)
    assert [event.kind for event in sink.snapshot()] == ["feedback_blocked"]


def test_tool_guard_blocks_generated_path_edits_when_feedback_forbids_it() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Do not modify generated files",
            why="They are regenerated by tooling",
            how_to_apply="Avoid editing generated paths directly",
        ),
    )
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        request(
            "edit_file",
            {"path": "src/generated/client.py", "old_text": "a", "new_text": "b"},
            sink,
            store=store,
        ),
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "generated files" in str(result.content)
    assert [event.kind for event in sink.snapshot()] == ["feedback_blocked"]


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
    assert result.tool_call_id == "call-1"
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


def test_tool_guard_permission_denied_appends_session_evidence(tmp_path: Path) -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    workdir = tmp_path / "repo"
    workdir.mkdir()
    req = request_with_session_context(
        "write_file",
        {"path": "README.md", "content": "x"},
        session_store=session_store,
        workdir=workdir,
        sink=sink,
    )
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=ToolPolicy(
            registry=registry,
            permission_manager=PermissionManager(mode="dontAsk", workdir=workdir),
        ),
        event_sink=sink,
    )

    result = middleware.wrap_tool_call(
        req,
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].status == "denied"
    assert loaded.evidence[0].metadata == {
        "event_kind": "permission_denied",
        "source": "tool_guard",
        "phase": "permission_denied",
        "tool": "write_file",
        "policy_code": "permission_denied",
        "permission_behavior": "deny",
    }
    assert "[denied] runtime_event: Tool write_file denied by permission_denied." in rendered


def test_tool_guard_blocks_untrusted_extension_destructive_tools() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    extension_capability = ToolCapability(
        name="mcp__docs__write",
        tool=mcp_docs_write,
        domain="mcp",
        read_only=False,
        destructive=True,
        concurrency_safe=False,
        source="mcp:docs",
        trusted=False,
        family="mcp",
        mutation="workspace_write",
        execution="plain_tool",
        exposure="extension",
        rendering_result="tool_message",
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


def test_tool_guard_converts_tool_exception_to_protocol_error_message() -> None:
    registry = canonical_registry()
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(registry=registry, event_sink=sink)

    result = middleware.wrap_tool_call(
        request("TodoWrite", {}, sink),
        lambda _request: (_ for _ in ()).throw(RuntimeError("backend exploded")),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert result.tool_call_id == "call-1"
    assert str(result.content) == "Error: RuntimeError: backend exploded"
    events = sink.snapshot()
    assert [event.kind for event in events] == ["allowed", "failed"]
    assert events[1].metadata["tool_call_id"] == "call-1"
    assert events[1].metadata["result_type"] == "ToolMessage"
