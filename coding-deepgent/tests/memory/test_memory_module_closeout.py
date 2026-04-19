from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from dependency_injector import providers
from langchain.messages import ToolMessage
from langgraph.store.memory import InMemoryStore

from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.memory import (
    MemoryRecord,
    build_long_term_memory_snapshot,
    save_memory_record,
    write_long_term_memory_snapshot,
)
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.sessions import (
    JsonlSessionStore,
    build_recovery_brief,
    render_recovery_brief,
)
from coding_deepgent.sessions.session_memory import SESSION_MEMORY_STATE_KEY
from coding_deepgent.settings import Settings
from coding_deepgent.tool_system import ToolGuardMiddleware


def test_app_container_exposes_memory_management_tools(tmp_path: Path) -> None:
    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path, store_backend="memory")),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    tool_names = [
        getattr(tool, "name", type(tool).__name__)
        for tool in container.tool_system.tools()
    ]

    assert "save_memory" in tool_names
    assert "list_memory" in tool_names
    assert "delete_memory" in tool_names


def test_feedback_memory_blocks_commit_through_tool_guard(tmp_path: Path) -> None:
    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path, store_backend="memory")),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )
    store = container.runtime.store()
    save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    sink = InMemoryEventSink()
    middleware = ToolGuardMiddleware(
        registry=container.tool_system.capability_registry(),
        event_sink=sink,
    )
    request = SimpleNamespace(
        tool_call={"name": "bash", "args": {"command": "git commit -m 'x'"}, "id": "call-1"},
        runtime=SimpleNamespace(
            context=RuntimeContext(
                session_id="session-1",
                workdir=tmp_path,
                trusted_workdirs=(),
                entrypoint="test",
                agent_name="test-agent",
                skill_dir=tmp_path / "skills",
                event_sink=sink,
                hook_registry=LocalHookRegistry(),
            ),
            store=store,
        ),
    )

    result = middleware.wrap_tool_call(
        request,
        lambda _request: ToolMessage(content="should not run", tool_call_id="call-1"),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "Run lint first" in str(result.content)


def test_recovery_brief_separates_long_term_and_current_session_memory(
    tmp_path: Path,
) -> None:
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
    state: dict[str, Any] = {
        "messages": [],
        "todos": [],
        "rounds_since_update": 0,
        SESSION_MEMORY_STATE_KEY: {
            "content": "Current repo focus is deterministic assist.",
            "source": "manual",
            "message_count": 1,
            "updated_at": "2026-04-18T00:00:00Z",
        },
    }
    write_long_term_memory_snapshot(state, build_long_term_memory_snapshot(store))

    session_store = JsonlSessionStore(tmp_path / "sessions")
    workdir = tmp_path / "repo"
    workdir.mkdir()
    context = session_store.create_session(workdir=workdir, entrypoint="cli")
    session_store.append_message(context, role="user", content="resume")
    session_store.append_state_snapshot(context, state=state)
    loaded = session_store.load_session(session_id=context.session_id, workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert "Long-term memory:" in rendered
    assert "Run lint before commit" in rendered
    assert "Current-session memory:" in rendered
    assert "Current repo focus is deterministic assist." in rendered
