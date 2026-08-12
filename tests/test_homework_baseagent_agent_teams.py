import builtins
import importlib.util
import json
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from homework.agent_app.features.teams.bus import MessageBus
from homework.agent_app.features.teams.protocol import (
    ProtocolState,
    ProtocolStore,
    match_response,
    process_permission_request,
)
from homework.agent_app.features.teams.teammates import TeamState
from homework.agent_app.features.teams import teammates as teammate_runtime
from homework.agent_app.tools.hooks import HookRegistry


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


class BaseAgentModule:
    def __init__(self, module):
        object.__setattr__(self, "module", module)

    def __getitem__(self, name):
        return getattr(self.module, name)

    def __getattr__(self, name):
        return getattr(self.module, name)

    def __contains__(self, name):
        return hasattr(self.module, name)

    def __iter__(self):
        return iter(vars(self.module))

    def __setattr__(self, name, value):
        setattr(self.module, name, value)

    def __delattr__(self, name):
        delattr(self.module, name)


def load_baseagent_module():
    spec = importlib.util.spec_from_file_location("_baseagent_teams", BASE_AGENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return BaseAgentModule(module)


@pytest.fixture
def bus(tmp_path):
    root = tmp_path / ".mailboxes"
    root.mkdir()
    return MessageBus(root=root)


def test_bus_consumes_each_message_once(bus):
    bus.send("lead", "worker", "hello")

    assert [message["content"] for message in bus.read_inbox("worker")] == [
        "hello"
    ]
    assert bus.read_inbox("worker") == []


def test_protocol_stores_do_not_share_requests():
    first = ProtocolStore()
    second = ProtocolStore()
    first.pending["req_1"] = ProtocolState(
        request_id="req_1",
        type="shutdown",
        sender="lead",
        target="worker",
        status="pending",
        payload="",
    )

    assert second.pending == {}


def test_team_states_are_isolated():
    first = TeamState()
    second = TeamState()

    first.active["worker"] = {"status": "running"}

    assert second.active == {}


def test_teammate_runtime_triggers_injected_post_hook_once_for_guarded_success(bus):
    events = []
    hooks = HookRegistry()
    hooks.register("PostToolUse", lambda block, output: events.append((block, output)))
    block = types.SimpleNamespace(
        type="tool_use",
        id="guarded-1",
        name="bash",
        input={"command": "echo guarded"},
    )
    responses = iter([
        types.SimpleNamespace(stop_reason="tool_use", content=[block]),
        text_response("done"),
    ])

    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    teammate_runtime.spawn_teammate_thread(
        TeamState(),
        bus,
        lambda **_kwargs: next(responses),
        name="worker",
        role="reviewer",
        prompt="inspect",
        workdir=Path.cwd(),
        handlers={"bash": lambda command, cwd=None: "guarded output"},
        hooks=hooks,
        validate_name=lambda name, **_kwargs: name,
        guarded_tools={"bash"},
        guarded_tool=lambda _agent, used_block, _inbox, handler, _cwd: (
            handler(**used_block.input),
            False,
        ),
        idle=lambda *_args: "timeout",
        max_tokens=100,
        thread_factory=ImmediateThread,
    )

    assert events == [(block, "guarded output")]


def test_protocol_matches_only_the_expected_response_type():
    store = ProtocolStore()
    store.pending["req_shutdown"] = ProtocolState(
        request_id="req_shutdown",
        type="shutdown",
        sender="lead",
        target="worker",
        status="pending",
        payload="",
    )

    assert not match_response(store, "plan_approval_response", "req_shutdown", True)
    assert match_response(store, "shutdown_response", "req_shutdown", True)
    assert store.pending["req_shutdown"].status == "approved"


def test_permission_processing_replies_to_the_matching_request(bus, tmp_path):
    process_permission_request(
        bus,
        ProtocolStore(),
        {
            "from": "worker",
            "content": {
                "request_id": "req_permission",
                "tool_use_id": "tool_permission",
                "tool_name": "bash",
                "tool_input": {"command": "echo safe"},
                "cwd": str(tmp_path),
            },
        },
        hook=lambda event, block: None,
        cwd_resolver=Path,
        guarded_tools={"bash"},
        clock=lambda: 0.0,
        sleep=lambda _seconds: None,
    )

    reply = bus.read_inbox("worker")[0]
    assert reply["type"] == "permission_response"
    assert reply["content"] == {
        "request_id": "req_permission",
        "approved": True,
        "reason": "",
    }


@pytest.fixture
def baseagent(monkeypatch, tmp_path):
    """Load BaseAgent with isolated mailboxes and no live API client."""
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(
                create=None,
                stream=None,
            )

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)

    baseagent = load_baseagent_module()

    original_mailbox_dir = baseagent["MAILBOX_DIR"]
    mailbox_dir = tmp_path / ".mailboxes"
    mailbox_dir.mkdir()
    monkeypatch.setattr(baseagent, "_ACCEPTANCE_ORIGINAL_MAILBOX_DIR", original_mailbox_dir, raising=False)
    monkeypatch.setattr(baseagent, "MAILBOX_DIR", mailbox_dir)
    monkeypatch.setattr(baseagent, "BUS", MessageBus(root=mailbox_dir))
    monkeypatch.setattr(baseagent, "PROTOCOL_STORE", ProtocolStore())
    team_state = TeamState()
    monkeypatch.setattr(baseagent, "TEAM_STATE", team_state)
    monkeypatch.setattr(baseagent, "team_lock", team_state.lock)
    monkeypatch.setattr(baseagent, "active_teammates", team_state.active)
    monkeypatch.setattr(baseagent, "IDLE_POLL_INTERVAL", 1)
    monkeypatch.setattr(baseagent, "IDLE_TIMEOUT", 0)
    monkeypatch.setattr(baseagent, "PERMISSION_POLL_INTERVAL", 0)
    monkeypatch.setattr(baseagent, "PERMISSION_TIMEOUT", 0)

    return baseagent


def text_response(text="done"):
    return types.SimpleNamespace(
        stop_reason="end_turn",
        content=[types.SimpleNamespace(type="text", text=text)],
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


class CapturedThread:
    def __init__(self, *args, target=None, daemon=None, **kwargs):
        self.target = target
        self.daemon = daemon
        self.started = False
        self.name = kwargs.get("name")

    def start(self):
        self.started = True

    def run(self):
        if self.target is None:
            raise AssertionError("teammate thread has no target")
        return self.target()


def capture_threads(baseagent, monkeypatch):
    created = []

    def factory(*args, **kwargs):
        thread = CapturedThread(*args, **kwargs)
        created.append(thread)
        return thread

    monkeypatch.setattr(baseagent["threading"], "Thread", factory)
    return created


def require_captured_thread(created):
    assert created, "spawn_teammate_thread did not create a worker thread"
    assert created[0].started, "teammate worker thread was not started"
    return created[0]


def teammate_retry_with_current_policy(baseagent):
    expected_kwargs = {
        "max_transient_retries": baseagent["MAX_TRANSIENT_RETRIES"],
        "max_consecutive_529": baseagent["MAX_CONSECUTIVE_529"],
        "base_delay_ms": baseagent["BASE_DELAY_MS"],
    }

    def retry(fn, state, **kwargs):
        assert kwargs == expected_kwargs
        return fn()

    return retry


def test_required_team_api_and_tools_are_registered(baseagent):
    required_names = {
        "MessageBus",
        "BUS",
        "active_teammates",
        "team_lock",
        "spawn_teammate_thread",
        "collect_lead_inbox",
        "run_spawn_teammate",
        "run_send_message",
        "run_check_inbox",
    }
    missing = sorted(required_names.difference(baseagent))
    assert missing == []

    schemas = {tool["name"]: tool for tool in baseagent["BUILTIN_TOOLS"]}
    for tool_name in ("spawn_teammate", "send_message", "check_inbox"):
        assert tool_name in schemas
        assert tool_name in baseagent["BUILTIN_HANDLERS"]


def test_mailbox_directory_uses_required_plural_name(baseagent):
    assert baseagent["_ACCEPTANCE_ORIGINAL_MAILBOX_DIR"].name == ".mailboxes"


def test_loading_baseagent_does_not_initialize_mailbox_storage(monkeypatch):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None, stream=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)

    mailbox_dir = (BASE_AGENT.parents[1] / ".mailboxes").resolve()
    mkdir_calls = []
    original_mkdir = Path.mkdir

    def track_mkdir(path, *args, **kwargs):
        if path.resolve() == mailbox_dir:
            mkdir_calls.append(path)
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", track_mkdir)
    load_baseagent_module()

    assert mkdir_calls == []


@pytest.mark.parametrize(
    "valid_name",
    ["a", "Researcher_1", "worker-name", "x" * 32],
)
def test_mailbox_accepts_safe_boundary_names(baseagent, valid_name):
    baseagent["BUS"].send("lead", valid_name, "safe")
    inbox_path = baseagent["MAILBOX_DIR"] / f"{valid_name}.jsonl"

    assert inbox_path.resolve().is_relative_to(baseagent["MAILBOX_DIR"].resolve())
    assert baseagent["BUS"].read_inbox(valid_name)[0]["content"] == "safe"


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "../evil",
        "a/b",
        "a\\b",
        "1worker",
        "has space",
        "x" * 33,
    ],
)
def test_mailbox_rejects_unsafe_agent_names(baseagent, invalid_name):
    with pytest.raises((ValueError, TypeError)):
        baseagent["BUS"].send(
            "lead",
            invalid_name,
            "unsafe",
        )

    mailbox_root = baseagent["MAILBOX_DIR"].resolve()
    assert all(
        path.resolve().is_relative_to(mailbox_root)
        for path in mailbox_root.rglob("*")
    )


def test_reserved_duplicate_and_empty_teammates_are_rejected(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)

    for name, role, prompt in (
        ("lead", "researcher", "inspect"),
        ("", "researcher", "inspect"),
        ("worker", "", "inspect"),
        ("worker", "researcher", ""),
    ):
        result = baseagent["spawn_teammate_thread"](name, role, prompt)
        assert isinstance(result, str)
        assert any(word in result.lower() for word in ("invalid", "reserved", "required"))

    first = baseagent["spawn_teammate_thread"](
        "researcher",
        "Repository investigator",
        "Inspect tests",
    )
    assert "researcher" in baseagent["active_teammates"]
    assert "spawn" in first.lower() or "created" in first.lower()

    duplicate = baseagent["spawn_teammate_thread"](
        "researcher",
        "Second role",
        "Do other work",
    )
    assert "already" in duplicate.lower() or "duplicate" in duplicate.lower()
    assert len(created) == 1


def test_synchronous_task_and_teammate_tools_coexist(baseagent):
    tool_names = {tool["name"] for tool in baseagent["BUILTIN_TOOLS"]}
    assert "task" in tool_names
    assert "spawn_teammate" in tool_names
    assert callable(baseagent["BUILTIN_HANDLERS"]["task"])
    assert callable(baseagent["BUILTIN_HANDLERS"]["spawn_teammate"])


def test_mailbox_send_read_consumes_each_message_once(baseagent):
    bus = baseagent["BUS"]
    bus.send("researcher", "lead", "first", "message")
    bus.send("reviewer", "lead", "second", "result")

    messages = bus.read_inbox("lead")
    assert [(item["from"], item["content"], item["type"]) for item in messages] == [
        ("researcher", "first", "message"),
        ("reviewer", "second", "result"),
    ]
    assert bus.read_inbox("lead") == []


def test_concurrent_mailbox_sends_keep_complete_json_lines(baseagent):
    bus = baseagent["BUS"]
    lock_present = (
        "mailbox_lock" in baseagent
        or hasattr(bus, "lock")
        or hasattr(bus, "_lock")
    )
    assert lock_present, "MessageBus has no thread-safety lock"

    def send(index):
        bus.send(
            f"worker-{index}",
            "lead",
            f"message-{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(send, range(40)))

    inbox_path = baseagent["MAILBOX_DIR"] / "lead.jsonl"
    raw_lines = inbox_path.read_text().splitlines()
    assert len(raw_lines) == 40
    assert all(isinstance(json.loads(line), dict) for line in raw_lines)

    received = bus.read_inbox("lead")
    assert {item["content"] for item in received} == {
        f"message-{index}" for index in range(40)
    }


def test_corrupt_mailbox_line_does_not_hide_valid_messages(baseagent, capsys):
    inbox_path = baseagent["MAILBOX_DIR"] / "lead.jsonl"
    valid_one = {
        "from": "one",
        "to": "lead",
        "content": "valid one",
        "type": "message",
        "ts": 1.0,
    }
    valid_two = {
        "from": "two",
        "to": "lead",
        "content": "valid two",
        "type": "result",
        "ts": 2.0,
    }
    inbox_path.write_text(
        json.dumps(valid_one) + "\n"
        + "{not-json}\n"
        + json.dumps(valid_two) + "\n"
    )

    messages = baseagent["BUS"].read_inbox("lead")
    assert messages == [valid_one, valid_two]
    output = capsys.readouterr().out.lower()
    assert "warning" in output or "corrupt" in output or "invalid" in output
    assert baseagent["BUS"].read_inbox("lead") == []


def test_check_inbox_and_auto_injection_share_consumption(baseagent):
    assert "collect_lead_inbox" in baseagent

    baseagent["BUS"].send("researcher", "lead", "first")
    checked = baseagent["run_check_inbox"]()
    assert "first" in checked
    assert not baseagent["collect_lead_inbox"]()

    baseagent["BUS"].send("researcher", "lead", "second")
    collected = baseagent["collect_lead_inbox"]()
    assert "second" in str(collected)
    assert "empty" in baseagent["run_check_inbox"]().lower()


def test_spawn_returns_immediately_and_worker_is_daemon(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    result = baseagent["spawn_teammate_thread"](
        "researcher",
        "Repository investigator",
        "Inspect the repository",
    )

    thread = require_captured_thread(created)
    assert thread.daemon is True
    assert "researcher" in baseagent["active_teammates"]
    assert isinstance(result, str)
    assert "researcher" in result


def test_teammate_history_is_independent_and_tools_are_nonrecursive(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    captured_calls = []
    lead_history = [{"role": "user", "content": "lead-only-marker"}]

    def fake_create(**kwargs):
        captured_calls.append(kwargs)
        return text_response("investigation complete")

    baseagent["client"].messages.create = fake_create
    monkeypatch.setattr(baseagent, "with_retry", teammate_retry_with_current_policy(baseagent))

    baseagent["spawn_teammate_thread"](
        "researcher",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    assert lead_history == [{"role": "user", "content": "lead-only-marker"}]
    assert captured_calls
    assert captured_calls[0]["messages"] == [
        {
            "role": "user",
            "content": (
                "<identity>You are 'researcher', role: "
                "Repository investigator. Continue your work.</identity>"
            ),
        },
        {"role": "user", "content": "Inspect tests"},
    ]
    assert "lead-only-marker" not in str(captured_calls[0]["messages"])

    teammate_system = captured_calls[0]["system"].lower()
    assert "researcher" in teammate_system
    assert "repository investigator" in teammate_system
    assert str(baseagent["WORKDIR"]).lower() in teammate_system
    assert "send_message" in teammate_system
    assert "lead" in teammate_system
    assert "subagent" in teammate_system and (
        "do not" in teammate_system or "must not" in teammate_system
    )

    teammate_tools = {tool["name"] for tool in captured_calls[0]["tools"]}
    assert {"bash", "read_file", "write_file", "send_message"}.issubset(teammate_tools)
    assert teammate_tools.isdisjoint({"task", "spawn_teammate", "schedule_cron"})


def test_teammate_collects_its_inbox_before_each_request(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    captured_calls = []
    baseagent["BUS"].send(
        "lead",
        "researcher",
        "Focus on parser tests",
    )

    def fake_create(**kwargs):
        captured_calls.append(kwargs)
        return text_response("done")

    baseagent["client"].messages.create = fake_create
    monkeypatch.setattr(baseagent, "with_retry", teammate_retry_with_current_policy(baseagent))
    baseagent["spawn_teammate_thread"](
        "researcher",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    request_text = json.dumps(captured_calls[0]["messages"], default=str)
    assert "Focus on parser tests" in request_text
    assert baseagent["BUS"].read_inbox("researcher") == []


def test_teammate_worker_uses_noninteractive_write_policy(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    replies = iter([
        tool_response(
            "write-1",
            "write_file",
            {"path": "unsafe.py", "content": "changed"},
        ),
        text_response("done"),
    ])
    wrote = []
    input_calls = []
    captured_calls = []

    def fake_create(**kwargs):
        captured_calls.append(kwargs)
        return next(replies)

    def forbidden_write(*args, **kwargs):
        wrote.append((args, kwargs))
        return "wrote file"

    def forbidden_input(*args, **kwargs):
        input_calls.append((args, kwargs))
        raise AssertionError("teammate worker called input()")

    baseagent["client"].messages.create = fake_create
    monkeypatch.setattr(baseagent, "with_retry", teammate_retry_with_current_policy(baseagent))
    monkeypatch.setattr(baseagent, "run_write", forbidden_write)
    monkeypatch.setattr(builtins, "input", forbidden_input)

    baseagent["spawn_teammate_thread"](
        "writer",
        "Repository investigator",
        "Inspect and request changes",
    )
    require_captured_thread(created).run()

    assert input_calls == []
    assert wrote == []
    assert len(captured_calls) >= 2
    tool_results = captured_calls[1]["messages"][-1]["content"]
    assert "permission" in str(tool_results).lower() or "denied" in str(tool_results).lower()


def test_teammate_reuses_transient_retry_helper(baseagent, monkeypatch):
    created = capture_threads(baseagent, monkeypatch)
    retry_calls = []

    baseagent["client"].messages.create = lambda **kwargs: text_response("done")

    def recording_retry(fn, state, **kwargs):
        assert kwargs == {
            "max_transient_retries": baseagent["MAX_TRANSIENT_RETRIES"],
            "max_consecutive_529": baseagent["MAX_CONSECUTIVE_529"],
            "base_delay_ms": baseagent["BASE_DELAY_MS"],
        }
        retry_calls.append(state)
        return fn()

    monkeypatch.setattr(baseagent, "with_retry", recording_retry)
    baseagent["spawn_teammate_thread"](
        "retryer",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    assert len(retry_calls) == 1
    assert isinstance(retry_calls[0], baseagent["RecoveryState"])


def test_teammate_normal_completion_sends_result_and_cleans_registry(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    baseagent["client"].messages.create = lambda **kwargs: text_response("final summary")
    monkeypatch.setattr(baseagent, "with_retry", teammate_retry_with_current_policy(baseagent))

    baseagent["spawn_teammate_thread"](
        "normal",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    messages = baseagent["BUS"].read_inbox("lead")
    assert any(
        item["from"] == "normal"
        and item["type"] == "result"
        and "final summary" in item["content"]
        for item in messages
    )
    assert "normal" not in baseagent["active_teammates"]


def test_teammate_exception_sends_error_and_cleans_registry(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)

    def fail_request(**kwargs):
        raise RuntimeError("teammate boom")

    baseagent["client"].messages.create = fail_request

    def fail_retry(fn, state, **kwargs):
        assert kwargs == {
            "max_transient_retries": baseagent["MAX_TRANSIENT_RETRIES"],
            "max_consecutive_529": baseagent["MAX_CONSECUTIVE_529"],
            "base_delay_ms": baseagent["BASE_DELAY_MS"],
        }
        return fn()

    monkeypatch.setattr(baseagent, "with_retry", fail_retry)
    baseagent["spawn_teammate_thread"](
        "failing",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    messages = baseagent["BUS"].read_inbox("lead")
    assert any(
        item["from"] == "failing"
        and item["type"] == "result"
        and "teammate boom" in item["content"]
        for item in messages
    )
    assert "failing" not in baseagent["active_teammates"]


def test_teammate_round_limit_sends_result_and_cleans_registry(
    baseagent,
    monkeypatch,
):
    created = capture_threads(baseagent, monkeypatch)
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return tool_response(
            f"read-{len(calls)}",
            "read_file",
            {"path": "README.md"},
        )

    baseagent["client"].messages.create = fake_create
    monkeypatch.setattr(baseagent, "with_retry", teammate_retry_with_current_policy(baseagent))
    monkeypatch.setattr(
        baseagent,
        "run_read",
        lambda path, offset=0, limit=None, cwd=None: "read",
    )

    baseagent["spawn_teammate_thread"](
        "bounded",
        "Repository investigator",
        "Inspect tests",
    )
    require_captured_thread(created).run()

    assert len(calls) == 10
    messages = baseagent["BUS"].read_inbox("lead")
    assert any(
        item["from"] == "bounded" and item["type"] == "result"
        for item in messages
    )
    assert "bounded" not in baseagent["active_teammates"]


def test_team_guidance_and_active_names_are_in_prompt_context(baseagent):
    baseagent["active_teammates"].update({
        "reviewer": {"status": "running"},
        "researcher": {"status": "running"},
    })
    context = baseagent["update_context"]({}, [])

    assert context["active_teammates"] == ["researcher", "reviewer"]
    prompt = baseagent["assemble_system_prompt"](context).lower()
    assert "task" in prompt
    assert "synchronous" in prompt
    assert "spawn_teammate" in prompt
    assert "asynchronous" in prompt
    assert "mailbox" not in json.dumps(context, default=str).lower()
