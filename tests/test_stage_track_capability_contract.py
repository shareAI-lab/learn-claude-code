from __future__ import annotations

import importlib


CAPABILITY_MATRIX = {
    "s01_agent_loop": {"bash"},
    "s02_tool_use": {"bash", "read_file", "write_file", "edit_file"},
    "s03_todo_write": {"bash", "read_file", "write_file", "edit_file", "todo"},
    "s04_subagent": {"bash", "read_file", "write_file", "edit_file", "task"},
    "s05_skill_loading": {
        "bash",
        "read_file",
        "write_file",
        "edit_file",
        "load_skill",
    },
    "s06_context_compact": {
        "bash",
        "read_file",
        "write_file",
        "edit_file",
        "compact",
    },
}

FUTURE_STAGE_CAPABILITIES = {"todo", "task", "load_skill", "compact"}


def module_tool_names(module_name: str) -> set[str]:
    module = importlib.import_module(f"agents_langchain.{module_name}")
    tools = getattr(module, "PARENT_TOOLS", None)
    if tools is None:
        tools = getattr(module, "TOOLS")
    return {tool.__name__ for tool in tools}


def test_stage_track_exposes_only_expected_capabilities() -> None:
    for module_name, expected in CAPABILITY_MATRIX.items():
        assert module_tool_names(module_name) == expected


def test_future_stage_capabilities_stay_hidden_until_their_chapter() -> None:
    for module_name, expected in CAPABILITY_MATRIX.items():
        available_future_caps = module_tool_names(module_name) & FUTURE_STAGE_CAPABILITIES
        assert available_future_caps == (expected & FUTURE_STAGE_CAPABILITIES)
