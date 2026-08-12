import pytest
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


def test_owner_registrars_own_schemas_and_bind_feature_dependencies():
    dependency_names = [
        "bash", "read_file", "write_file", "edit_file", "glob", "load_skill",
        "todo_write", "create_task", "list_tasks", "get_task", "claim_task",
        "complete_task", "schedule_cron", "list_crons", "cancel_cron",
        "spawn_teammate", "send_message", "check_inbox", "request_shutdown",
        "request_plan", "review_plan", "create_worktree", "remove_worktree",
        "keep_worktree", "task",
    ]
    dependencies = {
        name: (lambda name=name, **_kwargs: name) for name in dependency_names
    }
    registry = ToolRegistry()

    builtin_tools.register_builtin_tools(registry, dependencies)
    todos_feature.register_todo_tools(registry, dependencies)
    tasks_feature.register_task_tools(registry, dependencies)
    scheduler_feature.register_scheduler_tools(registry, dependencies, object())
    teammate_runtime.register_team_tools(registry, dependencies)
    worktrees_feature.register_worktree_tools(registry, dependencies, object())
    subagent_runtime.register_subagent_tool(registry, dependencies)
    mcp_state = mcp_feature.MCPState()
    mcp_feature.register_mcp_connection_tool(registry, mcp_state)

    tools, registered_handlers = registry.snapshot()
    names = [tool["name"] for tool in tools]
    assert names == [
        "bash", "read_file", "write_file", "edit_file", "glob", "load_skill",
        "compact", "todo_write", "create_task", "list_tasks", "get_task",
        "claim_task", "complete_task", "schedule_cron", "list_crons",
        "cancel_cron", "spawn_teammate", "send_message", "check_inbox",
        "request_shutdown", "request_plan", "review_plan", "create_worktree",
        "remove_worktree", "keep_worktree", "task", "connect_mcp",
    ]
    assert "compact" not in registered_handlers
    for name in dependency_names:
        assert registered_handlers[name] is dependencies[name]
    assert registered_handlers["connect_mcp"]("missing") == (
        "Unknown server 'missing'. Available: docs, deploy"
    )
    assert all(tool["description"] for tool in tools)


def test_mcp_collision_rolls_back_connection_and_snapshots_are_independent():
    state = mcp_feature.MCPState()
    registry = ToolRegistry()
    registry.register(tool_schema("mcp__docs__search"), lambda: "builtin")

    result = mcp_feature.connect_mcp(state, "docs", registry.snapshot)

    assert result.startswith("Error connecting")
    assert state.clients == {}

    client = mcp_feature._mock_server_docs()
    client.tools[0]["inputSchema"]["properties"]["query"]["nested"] = {"value": 1}
    client.tools[0]["annotations"] = {"readOnly": True, "destructiveHint": True}
    state.clients["docs"] = client
    tools, _ = mcp_feature.snapshot_mcp_tools(state, [], {})
    schema = next(tool["input_schema"] for tool in tools if tool["name"] == "mcp__docs__search")
    client.tools[0]["inputSchema"]["properties"]["query"]["nested"]["value"] = 2

    assert schema["properties"]["query"]["nested"]["value"] == 1
    metadata = state.metadata["mcp__docs__search"]
    assert metadata["readOnly"] is True
    assert metadata["destructive"] is True
