"""M4-3: AskUserQuestion 工具测试。"""
from __future__ import annotations

import json

from oai_code.config import load_config
from oai_code.tools.ask_user import (
    InteractiveUnavailable,
    _validate_and_normalize,
    non_interactive_ask,
    register_ask_user,
)
from oai_code.tools.registry import ToolRegistry


def _reg(tmp_path, monkeypatch, ask_fn):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_ask_user(reg, ask_fn=ask_fn)
    return reg


# ---------- schema 校验 ----------

def test_validate_accepts_minimal():
    out = _validate_and_normalize(
        [{"question": "which?", "options": [{"label": "A", "description": ""}, {"label": "B", "description": ""}]}]
    )
    assert isinstance(out, list)
    assert out[0]["question"] == "which?"


def test_validate_rejects_non_list():
    assert isinstance(_validate_and_normalize("hi"), str)


def test_validate_rejects_empty_questions():
    assert isinstance(_validate_and_normalize([]), str)


def test_validate_rejects_too_many_questions():
    qs = [{"question": "?", "options": [{"label": "a", "description": ""}, {"label": "b", "description": ""}]}] * 5
    assert isinstance(_validate_and_normalize(qs), str)


def test_validate_rejects_single_option():
    assert isinstance(
        _validate_and_normalize(
            [{"question": "?", "options": [{"label": "only", "description": ""}]}]
        ),
        str,
    )


def test_validate_rejects_empty_label():
    assert isinstance(
        _validate_and_normalize(
            [
                {
                    "question": "?",
                    "options": [{"label": "", "description": ""}, {"label": "b", "description": ""}],
                }
            ]
        ),
        str,
    )


def test_header_truncated_to_32_chars():
    out = _validate_and_normalize(
        [
            {
                "question": "?",
                "header": "x" * 100,
                "options": [{"label": "a", "description": ""}, {"label": "b", "description": ""}],
            }
        ]
    )
    assert len(out[0]["header"]) <= 32


# ---------- handler 行为 ----------

def test_handler_passes_to_ask_fn(tmp_path, monkeypatch):
    captured = []

    def fake_ask(questions):
        captured.append(questions)
        return [{"question": "which?", "label": "A", "description": ""}]

    reg = _reg(tmp_path, monkeypatch, fake_ask)
    out = reg.get("AskUserQuestion").handler(
        questions=[
            {
                "question": "which?",
                "options": [{"label": "A", "description": ""}, {"label": "B", "description": ""}],
            }
        ]
    )
    data = json.loads(out)
    assert data[0]["label"] == "A"
    assert captured  # ask_fn 被调用


def test_handler_non_interactive_returns_error(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch, non_interactive_ask)
    out = reg.get("AskUserQuestion").handler(
        questions=[
            {
                "question": "?",
                "options": [{"label": "a", "description": ""}, {"label": "b", "description": ""}],
            }
        ]
    )
    assert out.startswith("Error:") and "interactive" in out


def test_handler_catches_keyboard_interrupt(tmp_path, monkeypatch):
    def cancelling(_):
        raise KeyboardInterrupt()

    reg = _reg(tmp_path, monkeypatch, cancelling)
    out = reg.get("AskUserQuestion").handler(
        questions=[
            {
                "question": "?",
                "options": [{"label": "a", "description": ""}, {"label": "b", "description": ""}],
            }
        ]
    )
    assert out.startswith("Error: user aborted")


def test_invalid_schema_does_not_call_ask_fn(tmp_path, monkeypatch):
    called = {"n": 0}

    def ask(_):
        called["n"] += 1
        return []

    reg = _reg(tmp_path, monkeypatch, ask)
    out = reg.get("AskUserQuestion").handler(questions="not a list")
    assert out.startswith("Error:")
    assert called["n"] == 0
