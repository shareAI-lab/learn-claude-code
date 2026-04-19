"""校验所有内置工具的 input_schema 合法 (DESIGN.md §10)。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.tools.builtin import register_builtins
from mycode.tools.registry import ToolRegistry


def _valid_json_schema_object(obj: dict) -> bool:
    return (
        isinstance(obj, dict)
        and obj.get("type") == "object"
        and isinstance(obj.get("properties", {}), dict)
        and isinstance(obj.get("required", []), list)
    )


def _make_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test-model", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    return reg


def test_all_tools_have_schema(tmp_path, monkeypatch):
    reg = _make_registry(tmp_path, monkeypatch)
    names = reg.names()
    assert set(names) >= {"Bash", "Read", "Write", "Edit", "Glob", "Grep"}
    for name in names:
        tool = reg.get(name)
        assert tool is not None
        assert _valid_json_schema_object(tool.input_schema), f"{name} schema invalid"


def test_openai_specs_shape(tmp_path, monkeypatch):
    reg = _make_registry(tmp_path, monkeypatch)
    specs = reg.openai_specs()
    assert specs, "expected at least one tool spec"
    for s in specs:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]
