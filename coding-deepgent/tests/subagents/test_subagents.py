from __future__ import annotations

import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, cast
from types import SimpleNamespace

import pytest
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.memory.archive import InMemoryArchiveStore
from coding_deepgent.memory.backend import SqlAlchemyMemoryRepository, create_memory_engine, migrate_memory_schema
from coding_deepgent.memory.queue import InMemoryQueue
from coding_deepgent.memory.service import MemoryService
import coding_deepgent.runtime.agent_factory as runtime_agent_factory
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.sessions import JsonlSessionStore, build_recovery_brief, render_recovery_brief
from coding_deepgent.sessions.records import message_id_for_index
from coding_deepgent.subagents import tools as subagent_tools
from coding_deepgent.subagents import (
    BackgroundSubagentRun,
    BUILTIN_AGENT_DEFINITIONS,
    DEFAULT_CHILD_TOOLS,
    FORK_PLACEHOLDER_LAYOUT_VERSION,
    FORK_RECURSION_GUARD_MARKER,
    FORBIDDEN_CHILD_TOOLS,
    ForkResultEnvelope,
    EXPLORE_CHILD_TOOLS,
    PLAN_CHILD_TOOLS,
    ResumeForkInput,
    ResumeSubagentInput,
    RunForkInput,
    RunSubagentInput,
    SubagentResultEnvelope,
    VerifierSubagentResult,
    agent_definition,
    child_capability_registry,
    child_tool_allowlist,
    resume_fork,
    resolve_agent_definition,
    resume_fork_task,
    resume_subagent,
    resume_subagent_task,
    run_subagent_background,
    run_fork,
    run_fork_task,
    run_subagent,
    run_subagent_task,
    subagent_list,
    subagent_send_input,
    subagent_stop,
    subagent_status,
)
from coding_deepgent.tasks import create_plan, create_task
from coding_deepgent.tool_system import ToolPolicy, build_default_registry


def runtime_with_store(store: InMemoryStore) -> SimpleNamespace:
    return SimpleNamespace(store=store)


def runtime_with_context_and_store(store: InMemoryStore) -> SimpleNamespace:
    return SimpleNamespace(
        store=store,
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )


def _memory_service(tmp_path: Path) -> MemoryService:
    engine = create_memory_engine(f"sqlite+pysqlite:///{tmp_path / 'memory.db'}")
    migrate_memory_schema(engine)
    return MemoryService(
        repository=SqlAlchemyMemoryRepository(engine),
        queue=InMemoryQueue(),
        archive_store=InMemoryArchiveStore(),
    )


def patch_runtime_agent_factory(monkeypatch: pytest.MonkeyPatch, factory) -> None:
    def fake_create_runtime_agent(request, *, create_agent_factory=None):
        del create_agent_factory
        return factory(
            model=request.model,
            tools=list(request.tools),
            system_prompt=request.system_prompt,
            middleware=list(request.middleware),
            context_schema=request.context_schema,
            state_schema=request.state_schema,
            checkpointer=request.checkpointer,
            store=request.store,
            name=request.name,
            role=request.role,
        )

    monkeypatch.setattr(
        runtime_agent_factory,
        "create_runtime_agent",
        fake_create_runtime_agent,
    )


def write_local_subagents(
    workdir: Path, payload: dict[str, object]
) -> Path:
    root = workdir / ".coding-deepgent"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "SUBAGENTS.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_plugin(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    plugin_dir = tmp_path / "plugins" / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    path = plugin_dir / "plugin.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_plugin_agents(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    plugin_dir = tmp_path / "plugins" / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    path = plugin_dir / "subagents.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def runtime_with_fork_context_and_store(store: InMemoryStore) -> SimpleNamespace:
    registry = build_default_registry()
    projection = registry.project("main")
    return SimpleNamespace(
        store=store,
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            rendered_system_prompt="Main system prompt",
            visible_tool_projection=projection,
            tool_policy=ToolPolicy(registry=registry),
        ),
        config={"configurable": {"thread_id": "session-1"}},
        state={"messages": [HumanMessage(content="Parent context")]},
    )


def runtime_with_recorded_session(
    store: InMemoryStore,
    *,
    session_store: JsonlSessionStore,
    workdir: Path,
) -> SimpleNamespace:
    session_context = session_store.create_session(
        workdir=workdir,
        session_id="session-1",
        entrypoint="test",
    )
    session_store.append_message(session_context, role="user", content="start")
    return SimpleNamespace(
        store=store,
        context=RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=session_context,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )


def test_subagent_allowlists_are_exact_and_exclude_mutating_tools() -> None:
    assert child_tool_allowlist("general") == DEFAULT_CHILD_TOOLS
    assert child_tool_allowlist("verifier") == DEFAULT_CHILD_TOOLS
    assert child_tool_allowlist("explore") == EXPLORE_CHILD_TOOLS
    assert child_tool_allowlist("plan") == PLAN_CHILD_TOOLS
    assert set(FORBIDDEN_CHILD_TOOLS).isdisjoint(child_tool_allowlist("verifier"))
    assert agent_definition("general").max_turns == 25
    assert agent_definition("verifier").max_turns == 5
    assert set(BUILTIN_AGENT_DEFINITIONS) == {
        "general",
        "verifier",
        "explore",
        "plan",
    }
    child_registry = child_capability_registry()
    assert child_registry.child_names() == list(DEFAULT_CHILD_TOOLS)
    assert child_registry.tools_for_names(child_tool_allowlist("general")) == [
        child_registry.require(name).tool for name in DEFAULT_CHILD_TOOLS
    ]


def test_run_subagent_task_passes_effective_max_turns_via_recursion_limit(
    monkeypatch,
) -> None:
    runtime = runtime_with_context_and_store(InMemoryStore())
    captured: dict[str, Any] = {}

    class FakeChildAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "planned"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: FakeChildAgent())
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    run_subagent_task(
        task="Plan the work",
        runtime=cast(Any, runtime),
        agent_type="plan",
        max_turns=50,
    )

    assert captured["invoke_kwargs"]["config"]["configurable"]["thread_id"] == "session-1:plan"
    assert captured["invoke_kwargs"]["config"]["recursion_limit"] == 31


def test_run_subagent_task_routes_custom_model_profile(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    write_local_subagents(
        workdir,
        {
            "agents": [
                {
                    "agent_type": "docs_review",
                    "description": "Review docs",
                    "when_to_use": "Use for repository documentation review.",
                    "instructions": "Review the docs and summarize issues.",
                    "tool_allowlist": ["read_file", "glob"],
                    "disallowed_tools": ["write_file"],
                    "max_turns": 7,
                    "model_profile": "gpt-test-profile",
                }
            ]
        },
    )
    runtime = runtime_with_context_and_store(InMemoryStore())
    runtime.context = replace(runtime.context, workdir=workdir)
    captured: dict[str, Any] = {}

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "reviewed"}]
            }
        ),
    )

    def fake_build_openai_model(**kwargs: Any) -> object:
        captured["model_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(subagent_tools, "build_openai_model", fake_build_openai_model)

    result = run_subagent_task(
        task="Review docs",
        runtime=cast(Any, runtime),
        agent_type="docs_review",
    )

    assert result.agent_type == "docs_review"
    assert captured["model_kwargs"]["model_name"] == "gpt-test-profile"


def test_resolve_agent_definition_loads_repo_local_custom_agents(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    write_local_subagents(
        workdir,
        {
            "agents": [
                {
                    "agent_type": "api_mapper",
                    "description": "Map API surfaces",
                    "when_to_use": "Use for API surface comparison.",
                    "instructions": "Map API surfaces and report the differences.",
                    "tool_allowlist": ["read_file", "glob", "grep"],
                    "disallowed_tools": ["write_file", "bash"],
                    "max_turns": 6,
                }
            ]
        },
    )
    runtime = runtime_with_context_and_store(InMemoryStore())
    runtime.context = replace(runtime.context, workdir=workdir)

    definition = resolve_agent_definition("api_mapper", runtime=cast(Any, runtime))

    assert definition.agent_type == "api_mapper"
    assert definition.instructions == "Map API surfaces and report the differences."
    assert definition.tool_allowlist == ("read_file", "glob", "grep")


def test_run_subagent_executes_repo_local_custom_agent(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    write_local_subagents(
        workdir,
        {
            "agents": [
                {
                    "agent_type": "docs_review",
                    "description": "Review docs",
                    "when_to_use": "Use for documentation review.",
                    "instructions": "Review documentation files and summarize concrete issues.",
                    "tool_allowlist": ["read_file", "glob"],
                    "disallowed_tools": ["write_file"],
                    "max_turns": 7,
                }
            ]
        },
    )
    runtime = runtime_with_context_and_store(InMemoryStore())
    runtime.context = replace(runtime.context, workdir=workdir)
    captured: dict[str, Any] = {}

    class FakeChildAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "docs reviewed"}]}

    def fake_create_agent(**kwargs: Any) -> FakeChildAgent:
        captured["agent_kwargs"] = kwargs
        return FakeChildAgent()

    patch_runtime_agent_factory(monkeypatch, fake_create_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_subagent_task(
        task="Review docs",
        runtime=cast(Any, runtime),
        agent_type="docs_review",
    )

    assert result.content == "docs reviewed"
    assert [tool.name for tool in captured["agent_kwargs"]["tools"]] == ["read_file", "glob"]
    assert "Review documentation files and summarize concrete issues." in captured["agent_kwargs"]["system_prompt"]


def test_resolve_agent_definition_loads_plugin_provided_agents(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    write_plugin(
        workdir,
        "demo",
        {
            "name": "demo",
            "description": "Demo plugin",
            "version": "1.0.0",
            "skills": [],
            "tools": [],
            "resources": [],
            "agents": ["demo:docs_review"],
        },
    )
    write_plugin_agents(
        workdir,
        "demo",
        {
            "agents": [
                {
                    "agent_type": "demo:docs_review",
                    "description": "Plugin docs review",
                    "when_to_use": "Use for plugin-provided docs review.",
                    "instructions": "Review docs from plugin agent.",
                    "tool_allowlist": ["read_file", "glob"],
                    "disallowed_tools": ["write_file"],
                    "max_turns": 6,
                }
            ]
        },
    )
    runtime = runtime_with_context_and_store(InMemoryStore())
    runtime.context = replace(
        runtime.context,
        workdir=workdir,
        plugin_dir=workdir / "plugins",
    )

    definition = resolve_agent_definition("demo:docs_review", runtime=cast(Any, runtime))

    assert definition.agent_type == "demo:docs_review"
    assert definition.tool_allowlist == ("read_file", "glob")


def test_run_subagent_background_and_status(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "background result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_subagent_background).func(
            "Inspect in background",
            runtime,
            agent_type="general",
        )
    )

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background run did not complete")

    assert current.latest_result == "background result"
    assert current.total_invocations == 1
    assert current.runtime_snapshot is not None
    assert current.runtime_snapshot.parent_thread_id == "session-1"
    assert current.runtime_snapshot.workdir == str(workdir)
    assert current.notified is True
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)
    assert loaded.evidence[-1].kind == "subagent_notification"


def test_subagent_list_reports_active_and_terminal_background_runs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=JsonlSessionStore(tmp_path / "sessions"),
        workdir=workdir,
    )
    release = threading.Event()

    def slow_agent(**_kwargs):
        def invoke(_payload, **_invoke_kwargs):
            release.wait(timeout=2)
            return {"messages": [{"role": "assistant", "content": "background result"}]}

        return SimpleNamespace(invoke=invoke)

    patch_runtime_agent_factory(monkeypatch, slow_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_subagent_background).func(
            "Inspect in background",
            runtime,
            agent_type="general",
        )
    )

    active = json.loads(cast(Any, subagent_list).func(runtime))
    assert [run["run_id"] for run in active["runs"]] == [started.run_id]

    release.set()
    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background run did not complete")

    active_after_completion = json.loads(cast(Any, subagent_list).func(runtime))
    assert active_after_completion["runs"] == []

    all_runs = json.loads(cast(Any, subagent_list).func(runtime, include_terminal=True))
    assert [run["run_id"] for run in all_runs["runs"]] == [started.run_id]


def test_run_fork_background_and_status(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = replace(
        RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=runtime.context.session_context,
            rendered_system_prompt="Main system prompt",
            visible_tool_projection=registry.project("main"),
            tool_policy=ToolPolicy(registry=registry),
        ),
        plugin_dir=workdir / "plugins",
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "background fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_fork).func(
            "Explore another branch",
            runtime,
            background=True,
        )
    )

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background fork did not complete")

    assert current.mode == "background_fork"
    assert current.agent_type == "fork"
    assert current.latest_result == "background fork result"
    assert current.summary_text == "background fork result"
    assert current.child_thread_id.startswith("session-1:fork:")
    assert current.rendered_prompt_fingerprint is not None
    assert current.tool_pool_fingerprint is not None
    assert current.runtime_snapshot is not None
    assert current.runtime_snapshot.rendered_prompt_fingerprint is not None
    assert current.runtime_snapshot.tool_pool_fingerprint is not None
    assert current.placeholder_layout_version == FORK_PLACEHOLDER_LAYOUT_VERSION


def test_background_subagent_send_input_reactivates_finished_run(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    responses = iter(["first background result", "second background result"])

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": next(responses)}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_subagent_background).func(
            "Inspect in background",
            runtime,
            agent_type="general",
        )
    )

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background run did not complete")

    queued = BackgroundSubagentRun.model_validate_json(
        cast(Any, subagent_send_input).func(
            started.run_id,
            "Continue the background inspection",
            runtime,
        )
    )

    assert queued.run_id == started.run_id

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.total_invocations == 2 and current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background continuation did not complete")

    assert current.latest_result == "second background result"
    assert current.total_invocations == 2


def test_background_fork_send_input_reuses_same_thread_and_continuity(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = replace(
        RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=runtime.context.session_context,
            rendered_system_prompt="Main system prompt",
            visible_tool_projection=registry.project("main"),
            tool_policy=ToolPolicy(registry=registry),
        ),
        plugin_dir=workdir / "plugins",
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    responses = iter(["fork first result", "fork second result"])
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": next(responses)}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime, background=True)
    )

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background fork did not complete")

    first_thread_id = current.child_thread_id
    first_fingerprint = current.rendered_prompt_fingerprint
    first_tool_pool = current.tool_pool_fingerprint

    cast(Any, subagent_send_input).func(
        started.run_id,
        "Continue the fork",
        runtime,
    )

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.total_invocations == 2 and current.status == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background fork continuation did not complete")

    assert current.child_thread_id == first_thread_id
    assert current.rendered_prompt_fingerprint == first_fingerprint
    assert current.tool_pool_fingerprint == first_tool_pool
    assert current.latest_result == "fork second result"


def test_subagent_stop_cancels_running_background_run(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    gate = __import__("threading").Event()

    class BlockingAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            gate.wait(timeout=1.0)
            return {"messages": [{"role": "assistant", "content": "after stop"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: BlockingAgent())
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_subagent_background).func(
            "Inspect in background",
            runtime,
            agent_type="general",
        )
    )
    time.sleep(0.05)

    stopped = BackgroundSubagentRun.model_validate_json(
        cast(Any, subagent_stop).func(started.run_id, runtime)
    )
    assert stopped.stop_requested is True
    gate.set()

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "cancelled":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background run did not cancel")

    assert current.notified is True
    assert current.status == "cancelled"


def test_subagent_stop_cancels_running_background_fork(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = replace(
        RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=runtime.context.session_context,
            rendered_system_prompt="Main system prompt",
            visible_tool_projection=registry.project("main"),
            tool_policy=ToolPolicy(registry=registry),
        ),
        plugin_dir=workdir / "plugins",
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    gate = __import__("threading").Event()

    class BlockingForkAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            gate.wait(timeout=1.0)
            return {"messages": [{"role": "assistant", "content": "after stop"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: BlockingForkAgent())
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    started = BackgroundSubagentRun.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime, background=True)
    )
    time.sleep(0.05)

    stopped = BackgroundSubagentRun.model_validate_json(
        cast(Any, subagent_stop).func(started.run_id, runtime)
    )
    assert stopped.stop_requested is True
    gate.set()

    for _ in range(20):
        current = BackgroundSubagentRun.model_validate_json(
            cast(Any, subagent_status).func(started.run_id, runtime)
        )
        if current.status == "cancelled":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background fork did not cancel")

    assert current.mode == "background_fork"
    assert current.status == "cancelled"


def test_run_fork_filters_incomplete_tool_calls_and_exposes_placeholder_messages(
    monkeypatch,
) -> None:
    runtime = runtime_with_fork_context_and_store(InMemoryStore())
    captured: dict[str, Any] = {}
    runtime.state = {
        "messages": [
            HumanMessage(content="Parent context"),
            AIMessage(
                content=[{"type": "tool_use", "id": "call-1", "name": "read_file"}],
                tool_calls=[{"id": "call-1", "name": "read_file", "args": {}}],
            ),
            AIMessage(
                content=[{"type": "tool_use", "id": "call-2", "name": "glob"}],
                tool_calls=[{"id": "call-2", "name": "glob", "args": {}}],
            ),
            ToolMessage(content="glob result", tool_call_id="call-2"),
        ]
    }

    class FakeForkAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            return {"messages": [{"role": "assistant", "content": "fork result"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: FakeForkAgent())
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_fork_task(
        intent="Explore another branch",
        runtime=cast(Any, runtime),
        max_turns=99,
    )

    payload_messages = captured["payload"]["messages"]
    assert len(payload_messages) == 4
    assert result.placeholder_layout.placeholder_messages == ["<fork-tool-result:call-2>"]
    assert result.total_tokens == result.input_tokens + result.output_tokens
    assert result.child_thread_id.startswith("session-1:fork:")
    assert result.placeholder_layout.version == FORK_PLACEHOLDER_LAYOUT_VERSION
    assert result.parent_thread_id == "session-1"
    assert result.rendered_prompt_fingerprint
    assert result.tool_pool_identity.fingerprint
    assert result.total_tool_use_count == 0
    assert result.total_duration_ms >= 0
    assert result.fork_run_id
    assert result.child_thread_id != result.parent_thread_id
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.placeholder_layout.paired_tool_call_ids == ["call-2"]
    assert result.placeholder_layout.placeholder_messages == ["<fork-tool-result:call-2>"]
    assert result.placeholder_layout.replacement_state_hook
    assert result.parent_thread_id == "session-1"
    assert result.child_thread_id.startswith("session-1:fork:")
    assert result.tool_pool_identity.fingerprint
    assert payload_messages[1].tool_calls[0]["id"] == "call-2"
    assert payload_messages[2].tool_call_id == "call-2"


def test_resume_subagent_task_reuses_recorded_thread(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "first result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())
    cast(Any, run_subagent).func("Inspect the repository", runtime)

    captured: dict[str, Any] = {}

    class ResumeAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "resumed result"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: ResumeAgent())

    result = resume_subagent_task(
        subagent_thread_id="session-1:general",
        runtime=cast(Any, runtime),
        follow_up="Continue the inspection",
    )

    assert result.content == "resumed result"
    assert captured["invoke_kwargs"]["config"]["configurable"]["thread_id"] == "session-1:general"
    assert captured["payload"]["messages"][-1].content == "Continue the inspection"


def test_resume_fork_task_reuses_recorded_thread(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="coding-deepgent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=runtime.context.session_context,
        rendered_system_prompt="Main system prompt",
        visible_tool_projection=registry.project("main"),
        tool_policy=ToolPolicy(registry=registry),
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    first_result = ForkResultEnvelope.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime)
    )

    captured: dict[str, Any] = {}

    class ResumeForkAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "fork resumed"}]}

    patch_runtime_agent_factory(monkeypatch, lambda **_kwargs: ResumeForkAgent())

    result = resume_fork_task(
        child_thread_id=first_result.child_thread_id,
        runtime=cast(Any, runtime),
        follow_up="Keep exploring",
    )

    assert result.content == "fork resumed"
    assert captured["invoke_kwargs"]["config"]["configurable"]["thread_id"] == first_result.child_thread_id
    assert captured["payload"]["messages"][-1].content == "Keep exploring"


def test_resume_subagent_tool_returns_structured_result(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "first result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())
    cast(Any, run_subagent).func("Inspect the repository", runtime)

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "resumed result"}]
            }
        ),
    )

    output = cast(Any, resume_subagent).func(
        "session-1:general",
        runtime,
        "Continue the inspection",
    )
    result = SubagentResultEnvelope.model_validate_json(output)

    assert result.agent_type == "general"
    assert result.content == "resumed result"


def test_resume_fork_tool_returns_structured_result(monkeypatch, tmp_path: Path) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="coding-deepgent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=runtime.context.session_context,
        rendered_system_prompt="Main system prompt",
        visible_tool_projection=registry.project("main"),
        tool_policy=ToolPolicy(registry=registry),
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    first_result = ForkResultEnvelope.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime)
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork resumed"}]
            }
        ),
    )

    output = cast(Any, resume_fork).func(
        first_result.child_thread_id,
        runtime,
        "Keep exploring",
    )
    result = ForkResultEnvelope.model_validate_json(output)

    assert result.content == "fork resumed"
    assert result.child_thread_id == first_result.child_thread_id


def test_resume_fork_task_requires_matching_prompt_fingerprint(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="coding-deepgent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=runtime.context.session_context,
        rendered_system_prompt="Main system prompt",
        visible_tool_projection=registry.project("main"),
        tool_policy=ToolPolicy(registry=registry),
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    first_result = ForkResultEnvelope.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime)
    )
    runtime.context = replace(runtime.context, rendered_system_prompt="Changed prompt")

    with pytest.raises(RuntimeError, match="rendered system prompt fingerprint"):
        resume_fork_task(
            child_thread_id=first_result.child_thread_id,
            runtime=cast(Any, runtime),
        )


def test_resume_subagent_task_requires_matching_workdir(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    other_workdir = tmp_path / "other"
    other_workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "first result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())
    cast(Any, run_subagent).func("Inspect the repository", runtime)
    runtime.context = replace(runtime.context, workdir=other_workdir)

    with pytest.raises(RuntimeError, match="same recorded workdir"):
        resume_subagent_task(
            subagent_thread_id="session-1:general",
            runtime=cast(Any, runtime),
        )


def test_resume_fork_task_requires_matching_workdir(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    other_workdir = tmp_path / "other"
    other_workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="coding-deepgent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=runtime.context.session_context,
        rendered_system_prompt="Main system prompt",
        visible_tool_projection=registry.project("main"),
        tool_policy=ToolPolicy(registry=registry),
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    first_result = ForkResultEnvelope.model_validate_json(
        cast(Any, run_fork).func("Explore another branch", runtime)
    )
    runtime.context = replace(runtime.context, workdir=other_workdir)

    with pytest.raises(RuntimeError, match="same recorded workdir"):
        resume_fork_task(
            child_thread_id=first_result.child_thread_id,
            runtime=cast(Any, runtime),
        )


def test_run_subagent_task_uses_fake_factory_synchronously() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Inspect the feature output.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def factory(agent_type, tools):
        def child(task: str) -> str:
            calls.append((agent_type, tuple(tools), task))
            return f"done:{task}"

        return child

    expected_task = "\n".join(
        [
            "Verifier task:",
            "inspect",
            "",
            f"Plan ID: {plan.id}",
            "Plan title: Verification plan",
            "Verification criteria: Run pytest tests/test_subagents.py",
            f"Referenced task IDs: {task.id}",
            "",
            "Plan content:",
            "Inspect the feature output.",
        ]
    )

    result = run_subagent_task(
        task="inspect",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
        child_agent_factory=factory,
    )

    assert result.content == f"done:{expected_task}"
    assert calls == [
        (
            "verifier",
            ("read_file", "glob", "grep", "task_get", "task_list", "plan_get"),
            expected_task,
        )
    ]


def test_run_subagent_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    schema = cast(Any, run_subagent.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"task", "agent_type", "plan_id", "max_turns"}
    assert {
        "mailbox",
        "message",
        "team",
        "worker",
        "coordinator",
        "scratchpad",
        "send_message",
    }.isdisjoint(schema["properties"])

    with pytest.raises(ValidationError):
        RunSubagentInput.model_validate(
            {"task": "x", "background": True, "runtime": runtime}
        )


def test_resume_subagent_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    schema = cast(Any, resume_subagent.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"subagent_thread_id", "follow_up"}

    with pytest.raises(ValidationError):
        ResumeSubagentInput.model_validate(
            {"subagent_thread_id": "session-1:general", "runtime": runtime, "extra": True}
        )


def test_run_subagent_task_general_executes_real_read_only_child_agent(
    monkeypatch,
) -> None:
    runtime = runtime_with_context_and_store(InMemoryStore())
    captured: dict[str, Any] = {}

    class FakeChildAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "general result"}]}

    def fake_create_agent(**kwargs: Any) -> FakeChildAgent:
        captured["agent_kwargs"] = kwargs
        return FakeChildAgent()

    patch_runtime_agent_factory(monkeypatch, fake_create_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_subagent_task(
        task="Inspect the repository",
        runtime=cast(Any, runtime),
        agent_type="general",
    )

    assert result.content == "general result"
    assert result.agent_type == "general"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.total_tokens == result.input_tokens + result.output_tokens
    assert [tool.name for tool in captured["agent_kwargs"]["tools"]] == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert set(FORBIDDEN_CHILD_TOOLS).isdisjoint(
        tool.name for tool in captured["agent_kwargs"]["tools"]
    )
    assert "read-only general-purpose" in captured["agent_kwargs"]["system_prompt"]
    assert captured["agent_kwargs"]["name"] == "coding-deepgent-general"
    assert captured["payload"] == {
        "messages": [{"role": "user", "content": "Inspect the repository"}]
    }
    assert captured["invoke_kwargs"]["context"].entrypoint == "run_subagent:general"
    assert (
        captured["invoke_kwargs"]["config"]["configurable"]["thread_id"]
        == "session-1:general"
    )


def test_run_subagent_task_general_enqueues_agent_private_memory(tmp_path: Path, monkeypatch) -> None:
    runtime = runtime_with_context_and_store(InMemoryStore())
    service = _memory_service(tmp_path)
    runtime.context = replace(runtime.context, memory_service=service)
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "general result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    run_subagent_task(
        task="Inspect the repository",
        runtime=cast(Any, runtime),
        agent_type="general",
    )

    jobs = service.list_jobs(
        project_scope=str(Path.cwd()),
        agent_scope="coding-deepgent-general",
    )
    assert jobs
    assert jobs[0].job_type == "extract_long_term_memory"


def test_run_subagent_tool_returns_structured_general_result(monkeypatch) -> None:
    runtime = runtime_with_context_and_store(InMemoryStore())
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "general result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_subagent).func("Inspect the repository", runtime)
    result = SubagentResultEnvelope.model_validate_json(output)

    assert result.agent_type == "general"
    assert result.content == "general result"
    assert result.tool_allowlist == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert result.total_tokens == result.input_tokens + result.output_tokens


def test_run_subagent_records_sidechain_messages_in_parent_session(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "general result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_subagent).func("Inspect the repository", runtime)
    result = SubagentResultEnvelope.model_validate_json(output)
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)

    assert result.content == "general result"
    assert [
        (item.message_id, item.role, item.content) for item in loaded.history
    ] == [(message_id_for_index(0), "user", "start")]
    assert [(item.role, item.content) for item in loaded.sidechain_messages] == [
        ("user", "Inspect the repository"),
        ("assistant", "general result"),
    ]
    assert loaded.sidechain_messages[0].parent_message_id == message_id_for_index(0)
    assert loaded.sidechain_messages[0].parent_thread_id == "session-1"
    assert loaded.sidechain_messages[0].subagent_thread_id == "session-1:general"


def test_subagent_result_falls_back_to_last_text_when_final_message_is_tool_only(
    monkeypatch,
) -> None:
    runtime = runtime_with_context_and_store(InMemoryStore())
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [
                    {"role": "assistant", "content": "fallback text"},
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "call-1",
                                "name": "read_file",
                            }
                        ],
                    },
                ]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_subagent_task(
        task="Inspect the repository",
        runtime=cast(Any, runtime),
        agent_type="general",
    )

    assert result.content == "fallback text"


def test_run_fork_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    schema = cast(Any, run_fork.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"intent", "background", "max_turns"}
    assert {
        "mailbox",
        "message",
        "team",
        "worker",
        "coordinator",
        "scratchpad",
        "send_message",
    }.isdisjoint(schema["properties"])

    with pytest.raises(ValidationError):
        RunForkInput.model_validate(
            {"intent": "branch", "runtime": runtime, "agent_type": "general"}
        )


def test_background_tools_do_not_claim_mailbox_or_team_runtime_schema() -> None:
    forbidden = {
        "mailbox",
        "team",
        "worker",
        "coordinator",
        "scratchpad",
        "send_message",
    }
    background_schemas = [
        cast(Any, run_subagent_background.tool_call_schema).model_json_schema(),
        cast(Any, subagent_status.tool_call_schema).model_json_schema(),
        cast(Any, subagent_send_input.tool_call_schema).model_json_schema(),
        cast(Any, subagent_stop.tool_call_schema).model_json_schema(),
    ]
    for schema in background_schemas:
        assert forbidden.isdisjoint(schema["properties"])


def test_resume_fork_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    schema = cast(Any, resume_fork.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"child_thread_id", "follow_up"}

    with pytest.raises(ValidationError):
        ResumeForkInput.model_validate(
            {"child_thread_id": "session-1:fork:run", "runtime": runtime, "extra": True}
        )


def test_run_fork_task_executes_same_config_sibling_branch(monkeypatch) -> None:
    runtime = runtime_with_fork_context_and_store(InMemoryStore())
    captured: dict[str, Any] = {}

    class FakeForkAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "fork result"}]}

    def fake_create_agent(**kwargs: Any) -> FakeForkAgent:
        captured["agent_kwargs"] = kwargs
        return FakeForkAgent()

    patch_runtime_agent_factory(monkeypatch, fake_create_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_fork_task(
        intent="Check an alternate implementation path",
        runtime=cast(Any, runtime),
    )

    assert result.content == "fork result"
    assert result.parent_thread_id == "session-1"
    assert result.child_thread_id.startswith("session-1:fork:")
    assert result.fork_run_id
    assert result.rendered_prompt_fingerprint
    assert result.tool_pool_identity.tools[0].name == "bash"
    assert result.placeholder_layout.version == FORK_PLACEHOLDER_LAYOUT_VERSION
    assert captured["agent_kwargs"]["system_prompt"] == "Main system prompt"
    assert [tool.name for tool in captured["agent_kwargs"]["tools"]] == [
        tool.name for tool in runtime.context.visible_tool_projection.tools()
    ]
    payload_messages = captured["payload"]["messages"]
    assert isinstance(payload_messages[0], HumanMessage)
    assert payload_messages[0].content == "Parent context"
    assert isinstance(payload_messages[-1], HumanMessage)
    assert FORK_RECURSION_GUARD_MARKER in payload_messages[-1].content
    assert "Branch intent: Check an alternate implementation path" in payload_messages[-1].content
    assert captured["invoke_kwargs"]["context"].entrypoint == "run_fork"
    assert captured["invoke_kwargs"]["config"]["configurable"]["thread_id"].startswith(
        "session-1:fork:"
    )


def test_run_fork_tool_returns_structured_result(monkeypatch) -> None:
    runtime = runtime_with_fork_context_and_store(InMemoryStore())
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_fork).func("Explore another branch", runtime)
    result = ForkResultEnvelope.model_validate_json(output)

    assert result.mode == "fork"
    assert result.content == "fork result"
    assert result.parent_thread_id == "session-1"
    assert result.child_thread_id.startswith("session-1:fork:")
    assert result.tool_pool_identity.fingerprint
    assert result.placeholder_layout.version == FORK_PLACEHOLDER_LAYOUT_VERSION
    assert result.total_tokens == result.input_tokens + result.output_tokens


def test_run_fork_records_sidechain_messages_with_contract_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    registry = build_default_registry()
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    runtime.context = RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="coding-deepgent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=runtime.context.session_context,
        rendered_system_prompt="Main system prompt",
        visible_tool_projection=registry.project("main"),
        tool_policy=ToolPolicy(registry=registry),
    )
    runtime.state = {"messages": [HumanMessage(content="Parent context")]}
    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "fork result"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_fork).func("Explore another branch", runtime)
    result = ForkResultEnvelope.model_validate_json(output)
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)

    assert [(item.role, item.content) for item in loaded.sidechain_messages[-2:]] == [
        ("user", payload_messages := loaded.sidechain_messages[-2].content),
        ("assistant", "fork result"),
    ]
    assert FORK_RECURSION_GUARD_MARKER in payload_messages
    assert loaded.sidechain_messages[-2].agent_type == "fork"
    assert loaded.sidechain_messages[-2].metadata is not None
    assert loaded.sidechain_messages[-2].metadata["fork_run_id"] == result.fork_run_id
    assert (
        loaded.sidechain_messages[-2].metadata["placeholder_layout_version"]
        == FORK_PLACEHOLDER_LAYOUT_VERSION
    )
    assert (
        loaded.sidechain_messages[-2].metadata["tool_pool_fingerprint"]
        == result.tool_pool_identity.fingerprint
    )


def test_run_fork_rejects_recursive_fork_marker(monkeypatch) -> None:
    runtime = runtime_with_fork_context_and_store(InMemoryStore())
    runtime.state = {
        "messages": [HumanMessage(content=f"Parent\n{FORK_RECURSION_GUARD_MARKER}")]
    }
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    with pytest.raises(RuntimeError, match="recursion guard marker"):
        run_fork_task(intent="nested fork", runtime=cast(Any, runtime))


def test_run_subagent_pressure_guard_blocks_high_pressure() -> None:
    runtime = SimpleNamespace(
        store=InMemoryStore(),
        state={"messages": [HumanMessage(content="x" * 5000)]},
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            model_context_window_tokens=1000,
            subagent_spawn_guard_ratio=0.5,
        ),
    )

    result = run_subagent_task(
        task="inspect",
        runtime=cast(Any, runtime),
    )

    assert result.content.startswith("Subagent spawn blocked")
    assert runtime.context.event_sink.snapshot()[0].kind == "subagent_spawn_guard"


def test_run_subagent_pressure_guard_records_evidence(tmp_path: Path) -> None:
    session_store = JsonlSessionStore(tmp_path / "sessions-store")
    runtime = runtime_with_recorded_session(
        InMemoryStore(),
        session_store=session_store,
        workdir=tmp_path,
    )
    runtime.state = {"messages": [HumanMessage(content="x" * 5000)]}
    runtime.context = RuntimeContext(
        session_id=runtime.context.session_id,
        workdir=runtime.context.workdir,
        trusted_workdirs=runtime.context.trusted_workdirs,
        entrypoint=runtime.context.entrypoint,
        agent_name=runtime.context.agent_name,
        skill_dir=runtime.context.skill_dir,
        event_sink=runtime.context.event_sink,
        hook_registry=runtime.context.hook_registry,
        session_context=runtime.context.session_context,
        model_context_window_tokens=1000,
        subagent_spawn_guard_ratio=0.5,
    )

    output = cast(Any, run_subagent).func("inspect", runtime)
    result = SubagentResultEnvelope.model_validate_json(output)
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)

    assert result.content.startswith("Subagent spawn blocked")
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].metadata is not None
    assert loaded.evidence[0].metadata["event_kind"] == "subagent_spawn_guard"


def test_verifier_subagent_requires_plan_id() -> None:
    runtime = runtime_with_store(InMemoryStore())

    with pytest.raises(ValueError, match="plan_id"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
        )


def test_verifier_subagent_requires_task_store() -> None:
    runtime = SimpleNamespace(store=None)

    with pytest.raises(RuntimeError, match="task store"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
            plan_id="plan-123",
        )


def test_verifier_subagent_rejects_unknown_plan() -> None:
    runtime = runtime_with_store(InMemoryStore())

    with pytest.raises(KeyError, match="Unknown plan"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
            plan_id="plan-missing",
        )


def test_run_subagent_task_verifier_executes_real_child_agent(monkeypatch) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    captured: dict[str, Any] = {}

    class FakeChildAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "VERDICT: PASS"}]}

    def fake_create_agent(**kwargs: Any) -> FakeChildAgent:
        captured["agent_kwargs"] = kwargs
        return FakeChildAgent()

    patch_runtime_agent_factory(monkeypatch, fake_create_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    result = run_subagent_task(
        task="Verify the implementation",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
    )

    assert result.content == "VERDICT: PASS"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.total_tokens == result.input_tokens + result.output_tokens
    assert result.total_tool_use_count == 0
    assert [tool.name for tool in captured["agent_kwargs"]["tools"]] == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert "strictly read-only" in captured["agent_kwargs"]["system_prompt"]
    assert captured["agent_kwargs"]["store"] is store
    assert captured["agent_kwargs"]["name"] == "coding-deepgent-verifier"
    assert len(captured["agent_kwargs"]["middleware"]) == 1
    assert captured["payload"] == {
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "Verifier task:",
                        "Verify the implementation",
                        "",
                        f"Plan ID: {plan.id}",
                        "Plan title: Verification plan",
                        "Verification criteria: Run pytest tests/test_subagents.py",
                        f"Referenced task IDs: {task.id}",
                        "",
                        "Plan content:",
                        "Run the targeted tests and inspect durable task state.",
                    ]
                ),
            }
        ]
    }
    assert captured["invoke_kwargs"]["context"].entrypoint == "run_subagent:verifier"
    assert (
        captured["invoke_kwargs"]["config"]["configurable"]["thread_id"]
        == f"session-1:verifier:{plan.id}"
    )


def test_run_subagent_task_verifier_uses_durable_plan_payload() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def factory(agent_type, tools):
        def child(rendered_task: str) -> str:
            calls.append((agent_type, tuple(tools), rendered_task))
            return "VERDICT: PASS"

        return child

    result = run_subagent_task(
        task="Verify the implementation",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
        child_agent_factory=factory,
    )

    assert result.content == "VERDICT: PASS"
    assert result.plan_id == plan.id
    assert result.plan_title == "Verification plan"
    assert result.verification == "Run pytest tests/test_subagents.py"
    assert result.task_ids == (task.id,)
    assert calls == [
        (
            "verifier",
            ("read_file", "glob", "grep", "task_get", "task_list", "plan_get"),
            "\n".join(
                [
                    "Verifier task:",
                    "Verify the implementation",
                    "",
                    f"Plan ID: {plan.id}",
                    "Plan title: Verification plan",
                    "Verification criteria: Run pytest tests/test_subagents.py",
                    f"Referenced task IDs: {task.id}",
                    "",
                    "Plan content:",
                    "Run the targeted tests and inspect durable task state.",
                ]
            ),
        )
    ]


def test_run_subagent_tool_returns_structured_verifier_result(monkeypatch) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "VERDICT: PASS"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)

    assert result.agent_type == "verifier"
    assert result.plan_id == plan.id
    assert result.plan_title == "Verification plan"
    assert result.verification == "Run pytest tests/test_subagents.py"
    assert result.task_ids == [task.id]
    assert result.tool_allowlist == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert result.content == "VERDICT: PASS"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.total_tokens == result.input_tokens + result.output_tokens
    assert result.total_tool_use_count == 0


def test_verifier_verdict_helpers_map_status_and_summary() -> None:
    assert subagent_tools.verifier_verdict("Checked output\nVERDICT: PASS") == "PASS"
    assert subagent_tools.verifier_verdict("VERDICT: fail") == "FAIL"
    assert subagent_tools.verifier_verdict("VERDICT: PARTIAL") == "PARTIAL"
    assert subagent_tools.verifier_verdict("looks ok") is None
    assert (
        subagent_tools.verifier_evidence_summary(
            "Checked targeted tests.\nVERDICT: PASS", verdict="PASS"
        )
        == "Checked targeted tests."
    )
    assert (
        subagent_tools.verifier_evidence_summary("VERDICT: PASS", verdict="PASS")
        == "Verifier verdict: PASS"
    )


def test_run_subagent_tool_persists_verifier_evidence_roundtrip(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    task = create_task(task_store, title="Implement feature")
    plan = create_plan(
        task_store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest coding-deepgent/tests/test_subagents.py",
        task_ids=[task.id],
    )

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Checked targeted tests.\nVERDICT: FAIL",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert result.content == "Checked targeted tests.\nVERDICT: FAIL"
    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "verification"
    assert loaded.evidence[0].status == "failed"
    assert loaded.evidence[0].summary == "Checked targeted tests."
    assert loaded.evidence[0].subject == plan.id
    assert loaded.evidence[0].metadata == {
        "plan_id": plan.id,
        "plan_title": "Verification plan",
        "verdict": "FAIL",
        "parent_session_id": "session-1",
        "parent_thread_id": "session-1",
        "child_thread_id": f"session-1:verifier:{plan.id}",
        "verifier_agent_name": "coding-deepgent-verifier",
        "task_ids": [task.id],
        "tool_allowlist": [
            "read_file",
            "glob",
            "grep",
            "task_get",
            "task_list",
            "plan_get",
        ],
    }
    assert "[failed] verification: Checked targeted tests." in rendered


def test_run_subagent_tool_skips_verifier_evidence_without_recording_context(
    monkeypatch,
) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest coding-deepgent/tests/test_subagents.py",
        task_ids=[task.id],
    )

    patch_runtime_agent_factory(
        monkeypatch,
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Checked targeted tests.\nVERDICT: PASS",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda **_kwargs: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)

    assert result.content == "Checked targeted tests.\nVERDICT: PASS"
