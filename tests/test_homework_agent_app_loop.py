import types
from dataclasses import replace

import pytest

from homework.agent_app.config import AppConfig
from homework.agent_app.core.loop import run_agent_loop
from homework.agent_app.core.prompt import PromptBuilder
from homework.agent_app.core.recovery import PartialStreamError
from homework.agent_app.features.background import BackgroundState
from homework.agent_app.features.mcp import MCPState
from homework.agent_app.features.memory import MemoryStore
from homework.agent_app.features.scheduler import CronJob, SchedulerState
from homework.agent_app.features.skills import SkillState
from homework.agent_app.features.tasks import TaskStore
from homework.agent_app.features.teams.bus import MessageBus
from homework.agent_app.features.teams.protocol import ProtocolStore
from homework.agent_app.features.teams.teammates import TeamState
from homework.agent_app.features.worktrees import WorktreeState
from homework.agent_app.runtime import RuntimeContext, SessionState
from homework.agent_app.tools.hooks import HookRegistry
from homework.agent_app.tools.registry import ToolRegistry


def text_block(text):
    return types.SimpleNamespace(type="text", text=text)


def text_response(text="done"):
    return types.SimpleNamespace(
        stop_reason="end_turn",
        content=[text_block(text)],
    )


def tool_response(tool_id, name, tool_input):
    return types.SimpleNamespace(
        stop_reason="tool_use",
        content=[
            types.SimpleNamespace(
                type="tool_use",
                id=tool_id,
                name=name,
                input=tool_input,
            )
        ],
    )


def tool_schema(name):
    return {
        "name": name,
        "description": f"Run {name}",
        "input_schema": {"type": "object", "properties": {}},
    }


class FakeAdapter:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def create_streaming(self, **kwargs):
        self.requests.append(kwargs)
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response()
        return response

    def create(self, **kwargs):
        return types.SimpleNamespace(content=[text_block("[]")])


class FakeAPIError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


@pytest.fixture
def runtime_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)
    config = AppConfig.from_env(tmp_path)
    config.task_dir.mkdir()
    config.mailbox_dir.mkdir()
    config.worktrees_dir.mkdir()

    def make_runtime(responses):
        return RuntimeContext(
            config=config,
            llm=FakeAdapter(responses),
            session=SessionState(),
            prompt_builder=PromptBuilder(),
            tools=ToolRegistry(),
            hooks=HookRegistry(),
            scheduler=SchedulerState(),
            background=BackgroundState(),
            tasks=TaskStore(root=config.task_dir),
            worktrees=WorktreeState(
                workdir=config.workdir,
                root=config.worktrees_dir,
                run_git=lambda _args: (True, "ok"),
            ),
            skills=SkillState(root=config.skills_dir),
            memory=MemoryStore(
                root=config.memory_dir,
                index_path=config.memory_index,
            ),
            bus=MessageBus(root=config.mailbox_dir),
            protocols=ProtocolStore(),
            team=TeamState(),
            mcp=MCPState(),
        )

    return make_runtime


def tool_results(runtime):
    return [
        block
        for message in runtime.session.history
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]


def assistant_texts(runtime):
    return [
        block.get("text", "")
        if isinstance(block, dict)
        else getattr(block, "text", "")
        for message in runtime.session.history
        if message.get("role") == "assistant"
        for block in (
            message.get("content", [])
            if isinstance(message.get("content"), list)
            else []
        )
        if (
            block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        ) == "text"
    ]


def test_runtime_context_is_a_slotted_data_holder(runtime_factory):
    runtime = runtime_factory([text_response()])

    assert not hasattr(runtime, "__dict__")
    assert runtime.session.history == []
    assert runtime.session.context == {}
    assert runtime.session.todos == []
    assert runtime.session.rounds_since_todo == 0


def test_loop_executes_registered_tool_and_returns(runtime_factory):
    runtime = runtime_factory([
        tool_response("tool-1", "echo_tool", {"value": "hello"}),
        text_response("done"),
    ])
    runtime.tools.register(
        tool_schema("echo_tool"),
        lambda value: f"echo:{value}",
    )
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert tool_results(runtime)[-1]["content"] == "echo:hello"
    assert runtime.session.context["enabled_tools"] == ["echo_tool"]


def test_compact_is_control_flow_and_skips_later_tools(runtime_factory, monkeypatch):
    compact = types.SimpleNamespace(
        type="tool_use", id="compact-1", name="compact", input={"focus": "next"}
    )
    later = types.SimpleNamespace(
        type="tool_use", id="later-1", name="later", input={}
    )
    runtime = runtime_factory([
        types.SimpleNamespace(stop_reason="tool_use", content=[compact, later]),
        text_response(),
    ])
    runtime.tools.register(tool_schema("compact"), None)
    calls = []
    runtime.tools.register(tool_schema("later"), lambda: calls.append("later"))
    runtime.session.history.append({"role": "user", "content": "compact"})
    monkeypatch.setattr(
        "homework.agent_app.core.loop.compact_history",
        lambda _config, _summarize, _messages: [
            {"role": "user", "content": "[Compacted]\n\nsummary"}
        ],
    )

    run_agent_loop(runtime)

    assert calls == []
    assert runtime.llm.requests[1]["messages"][:2] == [
        {"role": "user", "content": "[Compacted]\n\nsummary"},
        {
            "role": "user",
            "content": "[Compacted. Continue with summarized context.]",
        },
    ]


def test_notifications_are_drained_before_the_request(runtime_factory):
    runtime = runtime_factory([text_response()])
    runtime.scheduler.queue.append(
        CronJob("cron-1", "* * * * *", "scheduled", False, False)
    )
    runtime.background.tasks["bg_0001"] = {
        "id": "bg_0001",
        "tool_use_id": "tool-bg",
        "tool_name": "bash",
        "command": "pytest",
        "status": "completed",
        "error": None,
    }
    runtime.background.results["bg_0001"] = "passed"
    runtime.bus.send("worker", "lead", "team result", "result")
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    request_text = str(runtime.llm.requests[0]["messages"])
    assert "[Scheduled: cron-1] scheduled" in request_text
    assert "<task_notification>" in request_text
    assert "team result" in request_text
    assert runtime.scheduler.queue == []
    assert runtime.bus.read_inbox("lead") == []


def test_permission_denial_does_not_dispatch_handler(runtime_factory):
    runtime = runtime_factory([
        tool_response("deny-1", "danger", {}),
        text_response(),
    ])
    calls = []
    runtime.tools.register(tool_schema("danger"), lambda: calls.append("executed"))
    runtime.hooks.register("PreToolUse", lambda _block: "Permission denied")
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert calls == []
    assert tool_results(runtime)[-1]["content"] == "Permission denied"


def test_max_tokens_pairs_tool_use_then_continues(runtime_factory):
    truncated = tool_response("truncated-1", "echo", {})
    truncated.stop_reason = "max_tokens"
    runtime = runtime_factory([truncated, text_response()])
    runtime.tools.register(tool_schema("echo"), lambda: "must not run")
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    result = tool_results(runtime)[0]
    assert result["tool_use_id"] == "truncated-1"
    assert result["is_error"] is True
    assert len(runtime.llm.requests) == 2
    assert runtime.llm.requests[1]["max_tokens"] == 64_000


def test_max_tokens_at_limit_still_pairs_truncated_tool_use(runtime_factory):
    truncated = tool_response("truncated-limit", "echo", {})
    truncated.stop_reason = "max_tokens"
    runtime = runtime_factory([truncated])
    runtime.config = replace(runtime.config, max_continuations=0)
    runtime.tools.register(tool_schema("echo"), lambda: "must not run")
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert len(runtime.llm.requests) == 1
    assert tool_results(runtime) == [
        {
            "type": "tool_result",
            "tool_use_id": "truncated-limit",
            "content": (
                "Tool call was not executed because the response hit the "
                "output token limit."
            ),
            "is_error": True,
        }
    ]


def test_partial_stream_is_saved_then_continued(runtime_factory):
    runtime = runtime_factory([
        PartialStreamError("partial text", RuntimeError("network")),
        text_response(),
    ])
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert runtime.session.history[1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "partial text"}],
    }
    assert runtime.llm.requests[1]["max_tokens"] == 64_000


def test_prompt_too_long_compacts_once_then_rebuilds_request(
    runtime_factory, monkeypatch
):
    runtime = runtime_factory([
        FakeAPIError(400, "prompt_is_too_long"),
        text_response(),
    ])
    runtime.session.history.append({"role": "user", "content": "run"})
    compacted = []

    def fake_compact(_config, _summarize, messages):
        compacted.append(list(messages))
        return [{"role": "user", "content": "[Reactive compact]"}]

    monkeypatch.setattr(
        "homework.agent_app.core.loop.reactive_compact", fake_compact
    )

    run_agent_loop(runtime)

    assert len(compacted) == 1
    assert len(runtime.llm.requests) == 2
    assert runtime.llm.requests[1]["messages"][0]["content"] == "[Reactive compact]"


def test_partial_stream_limit_preserves_visible_marker(runtime_factory, capsys):
    runtime = runtime_factory([
        PartialStreamError("visible-part", RuntimeError("connection lost"))
    ])
    runtime.config = replace(runtime.config, max_continuations=0)
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    marker = "[Stream interrupted: RuntimeError: connection lost]"
    assert assistant_texts(runtime) == [f"visible-part\n{marker}"]
    assert capsys.readouterr().out.count(marker) == 1


def test_continuation_budget_is_shared_by_max_tokens_and_partial_streams(
    runtime_factory
):
    first = text_response("max-part-0")
    first.stop_reason = "max_tokens"
    third = text_response("max-part-2")
    third.stop_reason = "max_tokens"
    runtime = runtime_factory([
        first,
        PartialStreamError("stream-part-1", RuntimeError("lost 1")),
        third,
        PartialStreamError("stream-part-3", RuntimeError("lost 3")),
    ])
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert [request["max_tokens"] for request in runtime.llm.requests] == [
        8_000,
        64_000,
        64_000,
        64_000,
    ]
    assert assistant_texts(runtime) == [
        "max-part-0",
        "stream-part-1",
        "max-part-2",
        "stream-part-3\n[Stream interrupted: RuntimeError: lost 3]",
    ]


def test_streamed_tool_use_keeps_adjacent_tool_result(runtime_factory):
    response = types.SimpleNamespace(
        stop_reason="tool_use",
        content=[
            text_block("Checking."),
            types.SimpleNamespace(
                type="tool_use",
                id="tool-stream-1",
                name="echo",
                input={},
            ),
        ],
    )
    runtime = runtime_factory([response, text_response("Done.")])
    runtime.tools.register(tool_schema("echo"), lambda: "/workspace")
    runtime.session.history.append({"role": "user", "content": "where?"})

    run_agent_loop(runtime)

    assert runtime.session.history[1]["role"] == "assistant"
    assert runtime.session.history[2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tool-stream-1",
                "content": "/workspace",
            }
        ],
    }


def test_background_dispatch_uses_handler_snapshot_without_real_thread(
    runtime_factory, monkeypatch
):
    runtime = runtime_factory([
        tool_response(
            "bg-tool", "bash", {"command": "pytest -q", "run_in_background": True}
        ),
        text_response(),
    ])
    runtime.tools.register(tool_schema("bash"), lambda **_kwargs: "ok")
    runtime.session.history.append({"role": "user", "content": "run"})
    captured = []

    def fake_start(state, block, handlers, **kwargs):
        captured.append((state, block, dict(handlers), kwargs))
        return "bg_test"

    monkeypatch.setattr(
        "homework.agent_app.core.loop.start_background_task", fake_start
    )

    run_agent_loop(runtime)

    assert captured[0][0] is runtime.background
    assert "bash" in captured[0][2]
    assert "[Background task bg_test started]" in tool_results(runtime)[-1]["content"]


def test_background_completion_after_dispatch_is_appended_as_text(
    runtime_factory, monkeypatch
):
    runtime = runtime_factory([
        tool_response(
            "bg-tool", "bash", {"command": "pytest -q", "run_in_background": True}
        ),
        text_response(),
    ])
    runtime.tools.register(tool_schema("bash"), lambda **_kwargs: "ok")
    runtime.session.history.append({"role": "user", "content": "run"})

    def complete_immediately(state, block, _handlers, **_kwargs):
        state.tasks["bg_done"] = {
            "id": "bg_done",
            "tool_use_id": block.id,
            "tool_name": block.name,
            "command": block.input["command"],
            "status": "completed",
            "error": None,
        }
        state.results["bg_done"] = "passed"
        return "bg_done"

    monkeypatch.setattr(
        "homework.agent_app.core.loop.start_background_task",
        complete_immediately,
    )

    run_agent_loop(runtime)

    result_message = runtime.session.history[2]
    assert [block["type"] for block in result_message["content"]] == [
        "tool_result",
        "text",
    ]
    assert "<task_notification>" in result_message["content"][1]["text"]
    assert "passed" in result_message["content"][1]["text"]


def test_final_teammate_message_forces_one_more_round(runtime_factory):
    runtime = runtime_factory([])

    def first_response():
        runtime.bus.send("worker", "lead", "late result", "result")
        return text_response("first")

    runtime.llm.responses = iter([first_response, text_response("second")])
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert len(runtime.llm.requests) == 2
    assert "late result" in str(runtime.llm.requests[1]["messages"])


def test_finalization_runs_stop_then_team_wait_then_memory(
    runtime_factory, monkeypatch
):
    runtime = runtime_factory([text_response()])
    runtime.session.history.append({"role": "user", "content": "run"})
    events = []
    runtime.hooks.register("Stop", lambda _messages: events.append("stop"))
    monkeypatch.setattr(
        "homework.agent_app.core.loop._wait_for_team_activity",
        lambda _runtime: events.append("team") or False,
    )
    monkeypatch.setattr(
        "homework.agent_app.core.loop.extract_memories",
        lambda *_args: events.append("extract"),
    )
    monkeypatch.setattr(
        "homework.agent_app.core.loop.consolidate_memories",
        lambda *_args: events.append("consolidate"),
    )

    run_agent_loop(runtime)

    assert events == ["stop", "team", "extract", "consolidate"]


def test_tool_registry_is_snapshotted_again_each_round(runtime_factory):
    runtime = runtime_factory([])

    def first_response():
        runtime.tools.register(tool_schema("late_tool"), lambda: "late")
        return tool_response("echo-1", "echo", {})

    runtime.llm.responses = iter([first_response, text_response()])
    runtime.tools.register(tool_schema("echo"), lambda: "ok")
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    assert [tool["name"] for tool in runtime.llm.requests[0]["tools"]] == ["echo"]
    assert [tool["name"] for tool in runtime.llm.requests[1]["tools"]] == [
        "echo",
        "late_tool",
    ]


def test_todo_reminder_round_counter_is_session_owned(runtime_factory):
    first = runtime_factory([text_response()])
    second = runtime_factory([text_response()])
    first.session.rounds_since_todo = 3
    first.session.history.append({"role": "user", "content": "first"})
    second.session.history.append({"role": "user", "content": "second"})

    run_agent_loop(first)
    run_agent_loop(second)

    assert "<reminder> Update your todos.</reminder>" in str(
        first.llm.requests[0]["messages"]
    )
    assert "<reminder>" not in str(second.llm.requests[0]["messages"])
    assert first.session.rounds_since_todo == 0
    assert second.session.rounds_since_todo == 0
