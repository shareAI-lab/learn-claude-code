from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence, cast

from dependency_injector import providers
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import PrivateAttr

from coding_deepgent import app
from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks import HookPayload, HookResult, LocalHookRegistry
from coding_deepgent.memory import MemoryContextMiddleware
from coding_deepgent.middleware import PlanContextMiddleware
from coding_deepgent.compact import RuntimePressureMiddleware
from coding_deepgent.runtime import (
    InMemoryEventSink,
    RuntimeContext,
    RuntimeInvocation,
    RuntimeState,
)
from coding_deepgent.sessions import SessionContext
from coding_deepgent.settings import Settings
from coding_deepgent.tool_system import ToolGuardMiddleware

EXPECTED_TOOL_NAMES = [
    "bash",
    "read_file",
    "write_file",
    "edit_file",
    "TodoWrite",
    "save_memory",
    "load_skill",
    "task_create",
    "task_get",
    "task_list",
    "task_update",
    "plan_save",
    "plan_get",
    "run_subagent",
]


class RecordingFakeModel(FakeMessagesListChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tool_choice, kwargs
        self._bound_tool_names = [
            getattr(tool, "name", type(tool).__name__) for tool in tools
        ]
        return self


class FakeAgent:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        return {
            "messages": [
                *payload["messages"],
                {"role": "assistant", "content": "planned"},
            ],
            "todos": [
                {
                    "content": "Ship it",
                    "status": "in_progress",
                    "activeForm": "Shipping",
                }
            ],
            "rounds_since_update": 0,
        }


def test_build_agent_binds_todowrite_product_tools(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(app, "build_openai_model", lambda: object())
    monkeypatch.setattr(app, "create_agent", fake_create_agent)

    agent = app.build_agent()

    assert agent is not None
    assert captured["state_schema"] is RuntimeState
    middleware = cast(Sequence[object], captured["middleware"])
    assert len(middleware) == 4
    assert isinstance(middleware[0], PlanContextMiddleware)
    assert isinstance(middleware[1], MemoryContextMiddleware)
    assert isinstance(middleware[2], RuntimePressureMiddleware)
    assert isinstance(middleware[3], ToolGuardMiddleware)
    tool_names = [
        getattr(tool, "name", getattr(tool, "__name__", ""))
        for tool in cast(Iterable[object], captured["tools"])
    ]
    assert tool_names == EXPECTED_TOOL_NAMES
    system_prompt = str(captured["system_prompt"])
    assert "explicit progress tracking helps on multi-step work" in system_prompt
    assert "activeForm for every todo" in system_prompt
    assert "write_plan" not in system_prompt


def test_build_agent_wires_runtime_pressure_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(app, "build_openai_model", lambda: object())
    monkeypatch.setattr(app, "create_agent", fake_create_agent)
    container = AppContainer(
        settings=providers.Object(
            Settings(
                auto_compact_threshold_tokens=1234,
                auto_compact_max_failures=2,
                auto_compact_ptl_retry_limit=3,
                snip_threshold_tokens=2345,
                collapse_threshold_tokens=3456,
                model_context_window_tokens=20000,
                collapse_trigger_ratio=0.75,
                subagent_spawn_guard_ratio=0.95,
                keep_recent_tool_results=5,
                microcompact_time_gap_minutes=60,
                microcompact_min_saved_tokens=100,
                microcompact_protect_recent_tokens=40000,
                microcompact_min_prune_saved_tokens=20000,
                keep_recent_messages_after_snip=7,
                keep_recent_messages_after_collapse=8,
                keep_recent_messages_after_compact=6,
                agent_name="custom-agent",
                entrypoint="custom-entrypoint",
            )
        ),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(fake_create_agent),
    )

    agent = app.build_agent(container=container)

    assert agent is not None
    middleware = cast(Sequence[object], captured["middleware"])
    runtime_pressure = cast(RuntimePressureMiddleware, middleware[2])
    assert runtime_pressure.auto_compact_threshold_tokens == 1234
    assert runtime_pressure.auto_compact_max_failures == 2
    assert runtime_pressure.auto_compact_ptl_retry_limit == 3
    assert runtime_pressure.snip_threshold_tokens == 2345
    assert runtime_pressure.collapse_threshold_tokens == 3456
    assert runtime_pressure.model_context_window_tokens == 20000
    assert runtime_pressure.collapse_trigger_ratio == 0.75
    assert runtime_pressure.keep_recent_tool_results == 5
    assert runtime_pressure.microcompact_time_gap_minutes == 60
    assert runtime_pressure.microcompact_min_saved_tokens == 100
    assert runtime_pressure.microcompact_protect_recent_tokens == 40000
    assert runtime_pressure.microcompact_min_prune_saved_tokens == 20000
    assert runtime_pressure.main_agent_name == "custom-agent"
    assert runtime_pressure.main_entrypoint == "custom-entrypoint"
    assert runtime_pressure.keep_recent_messages_after_snip == 7
    assert runtime_pressure.keep_recent_messages_after_collapse == 8
    assert runtime_pressure.keep_recent_messages == 6


def test_agent_loop_roundtrips_todo_state(monkeypatch) -> None:
    fake = FakeAgent()
    monkeypatch.setattr(app, "build_agent", lambda: fake)
    session_state = {
        "todos": [
            {
                "content": "Inspect",
                "status": "completed",
                "activeForm": "Inspecting",
            }
        ],
        "rounds_since_update": 2,
    }

    history = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "continue"},
    ]

    assert app.agent_loop(history, session_state=session_state) == "planned"
    assert fake.payloads[0]["messages"] == [
        {"role": "user", "content": "hello\n\ncontinue"}
    ]
    assert fake.payloads[0]["rounds_since_update"] == 2
    assert fake.payloads[0]["todos"] == [
        {"content": "Inspect", "status": "completed", "activeForm": "Inspecting"}
    ]
    assert history[-1] == {"role": "assistant", "content": "planned"}
    assert session_state["todos"] == [
        {"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}
    ]


def test_build_runtime_invocation_carries_session_context(tmp_path: Path) -> None:
    session_context = SessionContext(
        session_id="session-1",
        workdir=tmp_path,
        store_dir=tmp_path / "sessions",
        transcript_path=tmp_path / "sessions" / "session-1.jsonl",
        entrypoint="test",
    )
    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    invocation = app.build_runtime_invocation(
        container=container,
        session_id="session-1",
        session_context=session_context,
    )

    assert invocation.context.session_context is session_context
    assert invocation.thread_id == "session-1"


def test_agent_loop_threads_session_context_to_runtime_invocation(monkeypatch) -> None:
    session_context = SessionContext(
        session_id="session-1",
        workdir=Path.cwd(),
        store_dir=Path.cwd() / "sessions",
        transcript_path=Path.cwd() / "sessions" / "session-1.jsonl",
        entrypoint="test",
    )
    captured: dict[str, object] = {}
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=session_context,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )

    def build_runtime_invocation(**kwargs):
        captured.update(kwargs)
        return invocation

    monkeypatch.setattr(app, "build_runtime_invocation", build_runtime_invocation)
    monkeypatch.setattr(app, "build_agent", lambda **_: FakeAgent())

    history = [{"role": "user", "content": "hello"}]
    assert (
        app.agent_loop(
            history,
            session_state={"todos": [], "rounds_since_update": 0},
            session_id="session-1",
            session_context=session_context,
        )
        == "planned"
    )

    assert captured["session_context"] is session_context


def test_free_agent_path_executes_todowrite_without_runtime_injection_error(
    monkeypatch,
) -> None:
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "TodoWrite",
                        "args": {
                            "todos": [
                                {
                                    "content": "Inspect repo",
                                    "status": "in_progress",
                                    "activeForm": "Inspecting",
                                },
                                {
                                    "content": "Summarize findings",
                                    "status": "pending",
                                    "activeForm": "Summarizing",
                                },
                            ]
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="planned"),
        ]
    )

    monkeypatch.setattr(app, "build_openai_model", lambda: model)
    session_state = {
        "todos": [],
        "rounds_since_update": 0,
    }

    history = [{"role": "user", "content": "plan this work"}]
    assert app.agent_loop(history, session_state=session_state) == "planned"
    assert model._bound_tool_names == EXPECTED_TOOL_NAMES
    assert session_state["todos"] == [
        {
            "content": "Inspect repo",
            "status": "in_progress",
            "activeForm": "Inspecting",
        },
        {
            "content": "Summarize findings",
            "status": "pending",
            "activeForm": "Summarizing",
        },
    ]


def test_agent_loop_user_prompt_submit_hook_can_block_before_agent(monkeypatch) -> None:
    registry = LocalHookRegistry()

    def block_user_prompt(_payload: HookPayload) -> HookResult:
        return HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "hook blocked"}
        )

    registry.register("UserPromptSubmit", block_user_prompt)
    sink = InMemoryEventSink()
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink,
            hook_registry=registry,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )
    called: list[str] = []

    monkeypatch.setattr(app, "build_runtime_invocation", lambda **_: invocation)

    def build_blocked_agent(**_kwargs):
        called.append("agent")
        return FakeAgent()

    monkeypatch.setattr(app, "build_agent", build_blocked_agent)

    history = [{"role": "user", "content": "hello"}]
    assert (
        app.agent_loop(
            history,
            session_state={"todos": [], "rounds_since_update": 0},
            session_id="session-1",
        )
        == "hook blocked"
    )
    assert called == []
    assert history[-1] == {"role": "assistant", "content": "hook blocked"}
    assert [event.kind for event in sink.snapshot()] == [
        "hook_start",
        "hook_blocked",
    ]


def test_agent_loop_session_start_hook_runs_on_new_session_only(monkeypatch) -> None:
    registry = LocalHookRegistry()
    seen: list[str] = []

    def on_session_start(payload: HookPayload) -> HookResult:
        seen.append(str(payload.data["session_id"]))
        return HookResult()

    registry.register("SessionStart", on_session_start)
    sink = InMemoryEventSink()
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink,
            hook_registry=registry,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )

    monkeypatch.setattr(app, "build_runtime_invocation", lambda **_: invocation)
    monkeypatch.setattr(app, "build_agent", lambda **_: FakeAgent())

    fresh_history = [{"role": "user", "content": "hello"}]
    assert (
        app.agent_loop(
            fresh_history,
            session_state={"todos": [], "rounds_since_update": 0},
            session_id="session-1",
        )
        == "planned"
    )
    assert seen == ["session-1"]

    seen.clear()
    resumed_history = [
        {
            "role": "system",
            "content": (
                "Resumed session context. Use this brief as continuation context, "
                "not as a new user request.\n\nSession: session-1"
            ),
        },
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "planned"},
        {"role": "user", "content": "continue"},
    ]
    assert (
        app.agent_loop(
            resumed_history,
            session_state={"todos": [], "rounds_since_update": 1},
            session_id="session-1",
        )
        == "planned"
    )
    assert seen == []


def test_agent_loop_session_start_hook_is_observation_only(monkeypatch) -> None:
    registry = LocalHookRegistry()
    registry.register(
        "SessionStart",
        lambda _payload: HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "ignored"}
        ),
    )
    sink = InMemoryEventSink()
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink,
            hook_registry=registry,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )

    monkeypatch.setattr(app, "build_runtime_invocation", lambda **_: invocation)
    monkeypatch.setattr(app, "build_agent", lambda **_: FakeAgent())

    history = [{"role": "user", "content": "hello"}]
    assert (
        app.agent_loop(
            history,
            session_state={"todos": [], "rounds_since_update": 0},
            session_id="session-1",
        )
        == "planned"
    )
