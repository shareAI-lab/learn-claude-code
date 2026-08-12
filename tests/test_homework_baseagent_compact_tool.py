from homework.agent_app.tools import builtin
from homework.agent_app.tools.registry import ToolRegistry


def test_compact_schema_is_registered_without_normal_handler():
    handlers = {
        name: (lambda **_kwargs: "unused")
        for name in (
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "load_skill",
        )
    }
    registry = ToolRegistry()
    builtin.register_builtin_tools(registry, handlers)
    tools, registered_handlers = registry.snapshot()

    compact_tools = [tool for tool in tools if tool["name"] == "compact"]

    assert len(compact_tools) == 1
    schema = compact_tools[0]["input_schema"]
    assert schema["properties"]["focus"]["type"] == "string"
    assert schema["required"] == []
    assert "compact" not in registered_handlers
