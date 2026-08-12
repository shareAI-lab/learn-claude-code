import pytest

from homework.agent_app.tools.registry import ToolRegistry


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
