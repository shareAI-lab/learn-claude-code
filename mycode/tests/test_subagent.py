"""M1-4: Subagent Task 工具测试 (不打真实 LLM,用 stub)。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.tools.builtin import register_builtins, reset_session_state
from mycode.tools.registry import ToolRegistry
from mycode.tools.subagent import _filtered_registry, register_task_tool


def _make_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session_state()
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    return cfg, reg


def test_explore_filter_whitelist(tmp_path, monkeypatch):
    _, parent = _make_registry(tmp_path, monkeypatch)
    sub = _filtered_registry(parent, "Explore")
    names = set(sub.names())
    assert "Read" in names
    assert "Grep" in names
    assert "Glob" in names
    assert "Bash" in names
    assert "Write" not in names
    assert "Edit" not in names


def test_plan_filter_excludes_write(tmp_path, monkeypatch):
    _, parent = _make_registry(tmp_path, monkeypatch)
    sub = _filtered_registry(parent, "Plan")
    names = set(sub.names())
    assert names <= {"Read", "Grep", "Glob"}
    assert "Write" not in names
    assert "Bash" not in names
    assert "Edit" not in names


def test_general_purpose_inherits_all(tmp_path, monkeypatch):
    _, parent = _make_registry(tmp_path, monkeypatch)
    sub = _filtered_registry(parent, "general-purpose")
    assert set(sub.names()) == set(parent.names())


def test_register_adds_task_tool(tmp_path, monkeypatch):
    cfg, parent = _make_registry(tmp_path, monkeypatch)
    register_task_tool(parent, cfg=cfg, llm=None)
    assert parent.get("Task") is not None
    schema = parent.get("Task").input_schema
    assert "prompt" in schema["properties"]
    assert "subagent_type" in schema["properties"]
    enum = schema["properties"]["subagent_type"]["enum"]
    assert set(enum) == {"Explore", "general-purpose", "Plan"}


def test_unknown_subagent_type(tmp_path, monkeypatch):
    from mycode.tools.subagent import _run_subagent

    cfg, parent = _make_registry(tmp_path, monkeypatch)
    out = _run_subagent(
        cfg=cfg,
        llm=None,
        parent_registry=parent,
        description="x",
        prompt="x",
        subagent_type="bogus",
    )
    assert out.startswith("Error: unknown subagent_type")
