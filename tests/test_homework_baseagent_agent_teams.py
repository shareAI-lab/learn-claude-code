import json
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import homework.agent_app.bootstrap as bootstrap
from homework.agent_app.bootstrap import build_runtime
from homework.agent_app.config import AppConfig
from homework.agent_app.features.teams import teammates
from homework.agent_app.features.teams.bus import MessageBus
from homework.agent_app.features.teams.protocol import ProtocolState, ProtocolStore, match_response, process_permission_request
from homework.agent_app.tools.hooks import HookRegistry


class FakeSDKClient:
    def __init__(self):
        self.messages = types.SimpleNamespace(create=lambda **_kwargs: text_response())


def text_response(text="done"):
    return types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=text)])


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    config = replace(config, idle_timeout=0, permission_timeout=0)
    return build_runtime(config, FakeSDKClient())


@pytest.fixture
def bus(tmp_path):
    return MessageBus(tmp_path / ".mailboxes")


def test_bus_protocol_and_team_states_are_isolated(bus):
    bus.send("lead", "worker", "hello")
    assert [item["content"] for item in bus.read_inbox("worker")] == ["hello"]
    assert bus.read_inbox("worker") == []
    first, second = ProtocolStore(), ProtocolStore()
    first.pending["req"] = ProtocolState("req", "shutdown", "lead", "worker", "pending", "")
    assert second.pending == {}
    assert teammates.TeamState().active == {}


def test_protocol_routes_only_matching_response_and_permission(bus, tmp_path):
    store = ProtocolStore()
    store.pending["shutdown"] = ProtocolState("shutdown", "shutdown", "lead", "worker", "pending", "")
    assert not match_response(store, "plan_approval_response", "shutdown", True)
    assert match_response(store, "shutdown_response", "shutdown", True)
    process_permission_request(
        bus, ProtocolStore(), {"from": "worker", "content": {"request_id": "permit", "tool_use_id": "tool", "tool_name": "bash", "tool_input": {"command": "echo safe"}, "cwd": str(tmp_path)}},
        hook=lambda *_args: None, cwd_resolver=Path, guarded_tools={"bash"}, clock=lambda: 0, sleep=lambda _seconds: None,
    )
    assert bus.read_inbox("worker")[0]["content"] == {"request_id": "permit", "approved": True, "reason": ""}


def test_runtime_registers_team_tools_and_uses_plural_mailboxes(runtime):
    schemas, handlers = runtime.tools.snapshot()
    names = {schema["name"] for schema in schemas}
    assert {"task", "spawn_teammate", "send_message", "check_inbox"} <= names
    assert {"task", "spawn_teammate", "send_message", "check_inbox"} <= set(handlers)
    assert runtime.config.mailbox_dir.name == ".mailboxes"


@pytest.mark.parametrize("name", ["a", "Researcher_1", "worker-name", "x" * 32])
def test_mailbox_safe_names_stay_below_runtime_root(runtime, name):
    runtime.bus.send("lead", name, "safe")
    path = runtime.config.mailbox_dir / f"{name}.jsonl"
    assert path.resolve().is_relative_to(runtime.config.mailbox_dir.resolve())
    assert runtime.bus.read_inbox(name)[0]["content"] == "safe"


@pytest.mark.parametrize("name", ["", "../evil", "a/b", "a\\b", "1worker", "has space", "x" * 33])
def test_mailbox_rejects_unsafe_names(runtime, name):
    with pytest.raises((TypeError, ValueError)):
        runtime.bus.send("lead", name, "unsafe")
    assert all(path.resolve().is_relative_to(runtime.config.mailbox_dir.resolve()) for path in runtime.config.mailbox_dir.rglob("*"))


def test_concurrent_messages_and_lead_inbox_consumption(runtime):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda index: runtime.bus.send(f"worker-{index}", "lead", f"message-{index}"), range(40)))
    lines = (runtime.config.mailbox_dir / "lead.jsonl").read_text().splitlines()
    assert len(lines) == 40 and all(isinstance(json.loads(line), dict) for line in lines)
    assert {item["content"] for item in runtime.bus.read_inbox("lead")} == {f"message-{index}" for index in range(40)}


def test_corrupt_mailbox_line_does_not_hide_valid_messages(bus, capsys):
    bus.bootstrap()
    bus.mailbox_path("worker").write_text("not-json\n", encoding="utf-8")
    bus.send("lead", "worker", "valid")

    messages = bus.read_inbox("worker")

    assert [message["content"] for message in messages] == ["valid"]
    assert "ignored corrupt line" in capsys.readouterr().out


def test_teammate_owner_validates_lifecycle_and_nonrecursive_tools(bus, tmp_path):
    state = teammates.TeamState()
    created = []
    class Thread:
        def __init__(self, *, target, daemon): self.target, self.daemon = target, daemon
        def start(self): created.append(self)
    kwargs = dict(workdir=tmp_path, handlers={}, hooks=HookRegistry(), validate_name=lambda name, **_kwargs: (_ for _ in ()).throw(ValueError("reserved")) if name == "lead" else name, guarded_tools=set(), guarded_tool=lambda *_args: ("", False), idle=lambda *_args: "timeout", max_tokens=100, thread_factory=Thread)
    assert "Invalid" in teammates.spawn_teammate_thread(state, bus, lambda **_kwargs: text_response(), name="lead", role="r", prompt="p", **kwargs)
    kwargs["validate_name"] = lambda name, **_kwargs: name
    result = teammates.spawn_teammate_thread(state, bus, lambda **_kwargs: text_response(), name="worker", role="reviewer", prompt="inspect", **kwargs)
    assert "spawned" in result and created[0].daemon and "worker" in state.active
    assert {tool["name"] for tool in teammates.TEAM_TOOLS}.isdisjoint({"task", "spawn_teammate", "schedule_cron"})
    created[0].target()
    assert "worker" not in state.active
    assert bus.read_inbox("lead")[0]["content"] == "done"


def test_teammate_owner_injects_inbox_and_post_hook_once(bus, tmp_path):
    state, events, calls = teammates.TeamState(), [], []
    bus.send("lead", "worker", "Focus parser tests")
    block = types.SimpleNamespace(type="tool_use", id="guarded", name="bash", input={"command": "echo guarded"})
    responses = iter([types.SimpleNamespace(content=[block]), text_response("complete")])
    class Immediate:
        def __init__(self, *, target, daemon): self.target = target
        def start(self): self.target()
    hooks = HookRegistry(); hooks.register("PostToolUse", lambda block, output: events.append((block, output)))
    teammates.spawn_teammate_thread(state, bus, lambda **kwargs: (calls.append(kwargs), next(responses))[1], name="worker", role="reviewer", prompt="inspect", workdir=tmp_path, handlers={"bash": lambda command, cwd=None: "guarded output"}, hooks=hooks, validate_name=lambda name, **_kwargs: name, guarded_tools={"bash"}, guarded_tool=lambda _agent, used, _inbox, handler, _cwd: (handler(**used.input), False), idle=lambda *_args: "timeout", max_tokens=100, thread_factory=Immediate)
    assert "Focus parser tests" in json.dumps(calls[0]["messages"])
    assert events == [(block, "guarded output")]
    assert bus.read_inbox("lead")[0]["content"] == "complete"


def test_bootstrap_teammate_idle_adapter_drops_role_argument(
    runtime, monkeypatch
):
    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(bootstrap.threading, "Thread", ImmediateThread)
    _, handlers = runtime.tools.snapshot()

    result = handlers["spawn_teammate"]("worker", "reviewer", "inspect")
    messages = runtime.bus.read_inbox("lead")

    assert "spawned" in result
    assert messages[-1]["content"] == "done"


def test_bootstrap_teammate_uses_retry_policy(runtime, monkeypatch):
    calls = []

    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target

        def start(self):
            self.target()

    def retry(call, state, **kwargs):
        calls.append((state, kwargs))
        return call()

    monkeypatch.setattr(bootstrap.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(bootstrap, "with_retry", retry)
    _, handlers = runtime.tools.snapshot()

    handlers["spawn_teammate"]("worker", "reviewer", "inspect")

    assert len(calls) == 1
    assert calls[0][1] == {
        "max_transient_retries": runtime.config.max_transient_retries,
        "max_consecutive_529": runtime.config.max_consecutive_529,
        "base_delay_ms": runtime.config.base_delay_ms,
    }


def test_teammate_error_and_round_limit_send_result_and_cleanup(bus, tmp_path):
    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target

        def start(self):
            self.target()

    common = dict(
        role="reviewer",
        prompt="inspect",
        workdir=tmp_path,
        handlers={},
        hooks=HookRegistry(),
        validate_name=lambda name, **_kwargs: name,
        guarded_tools=set(),
        guarded_tool=lambda *_args: ("", False),
        idle=lambda *_args: "timeout",
        max_tokens=100,
        thread_factory=ImmediateThread,
    )

    error_state = teammates.TeamState()
    teammates.spawn_teammate_thread(
        error_state,
        bus,
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        name="error-worker",
        **common,
    )
    assert error_state.active == {}
    assert "Teammate error: RuntimeError: boom" in bus.read_inbox("lead")[0][
        "content"
    ]

    block = types.SimpleNamespace(
        type="tool_use", id="missing", name="missing", input={}
    )
    round_state = teammates.TeamState()
    teammates.spawn_teammate_thread(
        round_state,
        bus,
        lambda **_kwargs: types.SimpleNamespace(content=[block]),
        name="round-worker",
        **common,
    )
    assert round_state.active == {}
    assert bus.read_inbox("lead")[0]["content"] == (
        "Stopped after 10 teammate tool rounds."
    )
