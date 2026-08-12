import runpy
import sys
import types
from pathlib import Path

import pytest


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


@pytest.fixture
def baseagent(monkeypatch):
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

    namespace = runpy.run_path(
        str(BASE_AGENT),
        run_name="not_main",
    )
    return namespace["agent_loop"].__globals__


def response(content, stop_reason="tool_use"):
    return types.SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
    )


def test_compact_schema_is_registered_without_normal_handler(baseagent):
    compact_tools = [
        tool
        for tool in baseagent["BUILTIN_TOOLS"]
        if tool["name"] == "compact"
    ]

    assert len(compact_tools) == 1
    schema = compact_tools[0]["input_schema"]
    assert schema["properties"]["focus"]["type"] == "string"
    assert schema["required"] == []
    assert "compact" not in baseagent["BUILTIN_HANDLERS"]


def test_explicit_compact_replaces_history_and_starts_next_round(
    baseagent,
    monkeypatch,
):
    compact_block = types.SimpleNamespace(
        type="tool_use",
        id="tool-compact",
        name="compact",
        input={"focus": "remaining work"},
    )
    later_block = types.SimpleNamespace(
        type="tool_use",
        id="tool-later",
        name="bash",
        input={"command": "must-not-run"},
    )
    final_block = types.SimpleNamespace(
        type="text",
        text="continued",
    )
    responses = iter([
        response([compact_block, later_block]),
        response([final_block], stop_reason="end_turn"),
    ])
    llm_requests = []
    executed = []
    compact_inputs = []

    monkeypatch.setitem(
        baseagent,
        "collect_background_results",
        lambda: [],
    )
    monkeypatch.setitem(
        baseagent,
        "collect_lead_inbox",
        lambda: [],
    )
    monkeypatch.setitem(
        baseagent,
        "consume_cron_queue",
        lambda: [],
    )
    monkeypatch.setitem(
        baseagent,
        "tool_result_budget",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "snip_compact",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "micro_compact",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "estimate_size",
        lambda messages: 0,
    )
    def fake_update_context(context, messages, tools=None):
        return context

    monkeypatch.setitem(
        baseagent,
        "update_context",
        fake_update_context,
    )
    monkeypatch.setitem(
        baseagent,
        "get_system_prompt",
        lambda context: "test-system",
    )
    monkeypatch.setitem(
        baseagent,
        "build_request_messages_with_memories",
        lambda messages: list(messages),
    )
    monkeypatch.setitem(
        baseagent,
        "trigger_hook",
        lambda *args: None,
    )
    monkeypatch.setitem(
        baseagent,
        "wait_for_team_activity",
        lambda messages: False,
    )
    monkeypatch.setitem(
        baseagent,
        "extract_memories",
        lambda messages: None,
    )
    monkeypatch.setitem(
        baseagent,
        "consolidate_memories",
        lambda: None,
    )
    monkeypatch.setitem(baseagent, "rounds_since_todo", 0)

    def fake_compact(config, summarize, messages):
        compact_inputs.append(list(messages))
        assert config is baseagent["APP_CONFIG"]
        assert summarize is baseagent["summarize"]
        return [{
            "role": "user",
            "content": "[Compacted]\n\nsummary",
        }]

    def fake_streaming(**kwargs):
        llm_requests.append(kwargs["request_messages"])
        return next(responses)

    monkeypatch.setitem(
        baseagent,
        "compaction_compact_history",
        fake_compact,
    )
    monkeypatch.setitem(
        baseagent,
        "create_message_streaming",
        fake_streaming,
    )
    monkeypatch.setitem(
        baseagent,
        "execute_tool",
        lambda block, handlers=None: (
            executed.append(block.name) or "executed"
        ),
    )

    messages = [{"role": "user", "content": "compact now"}]
    baseagent["agent_loop"](messages, {})

    assert len(compact_inputs) == 1
    assert executed == []
    assert len(llm_requests) == 2
    assert llm_requests[1] == [
        {"role": "user", "content": "[Compacted]\n\nsummary"},
        {
            "role": "user",
            "content": (
                "[Compacted. Continue with summarized context.]"
            ),
        },
    ]
