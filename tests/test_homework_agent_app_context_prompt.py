import copy
from types import SimpleNamespace

from homework.agent_app.config import AppConfig
from homework.agent_app.core.context import build_context, append_user_text_blocks
from homework.agent_app.core.prompt import PromptBuilder
from homework.agent_app.features.mcp import MCPState
from homework.agent_app.features.memory import MemoryStore
from homework.agent_app.features.skills import SkillState
from homework.agent_app.features.teams.teammates import TeamState
from homework.agent_app.features.todos import format_current_todos
from homework.agent_app.runtime import SessionState
from homework.agent_app.tools.registry import ToolRegistry
from tests.homework_agent_app_fakes import tool_schema


def test_context_uses_runtime_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    session = SessionState(
        todos=[{"content": "inspect", "status": "in_progress"}]
    )
    tools = ToolRegistry()
    tools.register(tool_schema("echo_tool"), lambda: "ok")
    tool_schemas, _handlers = tools.snapshot()
    runtime_view = SimpleNamespace(
        config=config,
        session=session,
        skills=SkillState(root=config.skills_dir),
        memory=MemoryStore(
            root=config.memory_dir,
            index_path=config.memory_index,
        ),
        team=TeamState(),
        mcp=MCPState(),
    )
    original_schemas = copy.deepcopy(tool_schemas)
    original_todos = copy.deepcopy(session.todos)

    context = build_context(runtime_view, tool_schemas)

    assert context["workspace"] == str(config.workdir)
    assert context["enabled_tools"] == sorted(context["enabled_tools"])
    assert context["todos"] == format_current_todos(session)
    assert tool_schemas == original_schemas
    assert session.todos == original_todos


def test_prompt_cache_is_instance_owned():
    first = PromptBuilder()
    second = PromptBuilder()

    first_prompt = first.build({"enabled_tools": []})

    assert first.last_key is not None
    assert first.last_prompt == first_prompt
    assert second.last_key is None
    assert second.last_prompt is None
    assert first_prompt == second.build({"enabled_tools": []})
    assert first is not second


def test_append_user_text_blocks_extends_the_latest_user_message():
    messages = [{"role": "user", "content": "existing"}]

    append_user_text_blocks(messages, ["first", "second"])

    assert messages == [{
        "role": "user",
        "content": [
            {"type": "text", "text": "existing"},
            {"type": "text", "text": "first"},
            {"type": "text", "text": "second"},
        ],
    }]
