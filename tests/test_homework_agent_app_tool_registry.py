import pytest
from pathlib import Path

from homework.agent_app.tools.registry import ToolRegistry
from homework.agent_app.tools import builtin as builtin_tools
from homework.agent_app.features import mcp as mcp_feature
from homework.agent_app.features import scheduler as scheduler_feature
from homework.agent_app.features import subagents as subagent_runtime
from homework.agent_app.features import tasks as tasks_feature
from homework.agent_app.features import todos as todos_feature
from homework.agent_app.features import worktrees as worktrees_feature
from homework.agent_app.features.teams import teammates as teammate_runtime


def tool_schema(name):
    return {"name": name, "input_schema": {"type": "object"}}


def test_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register(tool_schema("bash"), lambda: "one")

    with pytest.raises(ValueError, match="duplicate"):
        registry.register(tool_schema("bash"), lambda: "two")


def test_snapshots_do_not_change_after_later_registration():
    registry = ToolRegistry()
    registry.register(tool_schema("bash"), lambda: "ok")
    tools, handlers = registry.snapshot()
    registry.register(tool_schema("read_file"), lambda: "ok")

    assert [item["name"] for item in tools] == ["bash"]
    assert set(handlers) == {"bash"}


def test_compact_schema_omits_handler_from_snapshot():
    registry = ToolRegistry()
    registry.register(tool_schema("compact"), None)

    tools, handlers = registry.snapshot()

    assert [item["name"] for item in tools] == ["compact"]
    assert handlers == {}


def test_baseagent_has_no_append_time_tool_registration():
    source = (Path(__file__).parents[1] / "homework" / "BaseAgent.py").read_text()

    assert "BUILTIN_TOOLS.append(" not in source
    assert "BUILTIN_HANDLERS[\"task\"] =" not in source


def test_owner_registrars_build_the_builtin_registry():
    names = [
        "bash", "read_file", "write_file", "edit_file", "glob", "load_skill",
        "compact", "todo_write", "create_task", "list_tasks", "get_task",
        "claim_task", "complete_task", "schedule_cron", "list_crons",
        "cancel_cron", "spawn_teammate", "send_message", "check_inbox",
        "request_shutdown", "request_plan", "review_plan", "create_worktree",
        "remove_worktree", "keep_worktree", "task", "connect_mcp",
    ]
    schemas = {name: tool_schema(name) for name in names}
    handlers = {name: (lambda name=name: name) for name in names if name != "compact"}
    registry = ToolRegistry()

    builtin_tools.register_builtin_tools(registry, schemas, handlers)
    todos_feature.register_todo_tools(registry, schemas, handlers)
    tasks_feature.register_task_tools(registry, schemas, handlers)
    scheduler_feature.register_scheduler_tools(registry, schemas, handlers)
    teammate_runtime.register_team_tools(registry, schemas, handlers)
    worktrees_feature.register_worktree_tools(registry, schemas, handlers)
    subagent_runtime.register_subagent_tool(registry, schemas, handlers)
    mcp_feature.register_mcp_connection_tool(registry, schemas, handlers)

    tools, registered_handlers = registry.snapshot()
    assert [tool["name"] for tool in tools] == names
    assert "compact" not in registered_handlers


def test_baseagent_wires_owner_registrars_without_static_task_extension():
    source = (Path(__file__).parents[1] / "homework" / "BaseAgent.py").read_text()

    for call in (
        "builtin_tools.register_builtin_tools(",
        "todos_feature.register_todo_tools(",
        "tasks_feature.register_task_tools(",
        "scheduler_feature.register_scheduler_tools(",
        "teammate_runtime.register_team_tools(",
        "worktrees_feature.register_worktree_tools(",
        "subagent_runtime.register_subagent_tool(",
        "mcp_feature.register_mcp_connection_tool(",
    ):
        assert call in source
    assert "[*BUILTIN_TOOLS" not in source
