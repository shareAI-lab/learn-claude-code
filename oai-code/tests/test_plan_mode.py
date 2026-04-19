"""M4-5: Plan Mode 测试。"""
from __future__ import annotations

from oai_code.agent.dispatcher import ToolCall, dispatch
from oai_code.config import load_config
from oai_code.tools.ask_user import register_ask_user
from oai_code.tools.builtin import register_builtins, reset_session_state
from oai_code.tools.plan_mode import (
    PlanModeState,
    is_tool_allowed_in_plan_mode,
    register_plan_mode,
)
from oai_code.tools.registry import ToolRegistry


def _setup(tmp_path, monkeypatch, ask_fn=None):
    monkeypatch.chdir(tmp_path)
    reset_session_state()
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    if ask_fn is None:
        ask_fn = lambda qs: [{"label": "Approve", "description": "ok"}]
    register_ask_user(reg, ask_fn=ask_fn)
    state = PlanModeState()
    register_plan_mode(reg, state=state, ask_fn=ask_fn)
    return cfg, reg, state


# ---------- 工具白名单 ----------

def test_read_allowed_in_plan():
    assert is_tool_allowed_in_plan_mode("Read", [])
    assert is_tool_allowed_in_plan_mode("Grep", [])


def test_write_blocked_in_plan():
    assert not is_tool_allowed_in_plan_mode("Write", ["write"])
    assert not is_tool_allowed_in_plan_mode("Edit", ["write"])
    assert not is_tool_allowed_in_plan_mode("Bash", ["exec"])


def test_exitplanmode_always_allowed():
    assert is_tool_allowed_in_plan_mode("ExitPlanMode", [])


def test_untagged_tool_allowed_by_default():
    """没声明 requires 的工具默认允许(保守策略只拦声明了 write/exec/delegate 的)"""
    assert is_tool_allowed_in_plan_mode("SomeCustomTool", [])


# ---------- PlanModeState 方法 ----------

def test_enter_idempotent():
    s = PlanModeState()
    out1 = s.enter()
    assert "Entered" in out1
    assert s.active
    out2 = s.enter()
    assert "Already" in out2


def test_exit_without_enter():
    s = PlanModeState()
    out = s.exit_with_approval("some plan", lambda _: [])
    assert out.startswith("Error: not in plan mode")


def test_exit_empty_plan():
    s = PlanModeState()
    s.enter()
    out = s.exit_with_approval("   ", lambda _: [{"label": "Approve"}])
    assert "plan text required" in out


def test_exit_approve_turns_flag_off():
    s = PlanModeState()
    s.enter()
    assert s.active
    out = s.exit_with_approval("do X", lambda _: [{"label": "Approve"}])
    assert "approved" in out
    assert not s.active


def test_exit_reject_keeps_flag_on():
    s = PlanModeState()
    s.enter()
    out = s.exit_with_approval(
        "do X",
        lambda _: [{"label": "Reject", "description": "not yet"}],
    )
    assert "rejected" in out
    assert s.active


def test_exit_non_interactive_returns_error():
    from oai_code.tools.ask_user import InteractiveUnavailable, non_interactive_ask

    s = PlanModeState()
    s.enter()
    out = s.exit_with_approval("do X", non_interactive_ask)
    assert out.startswith("Error") and "interactive" in out


# ---------- dispatcher 集成 ----------

def test_dispatcher_blocks_write_in_plan(tmp_path, monkeypatch):
    cfg, reg, state = _setup(tmp_path, monkeypatch)
    (tmp_path / "f.txt").write_text("x")
    state.enter()
    calls = [
        ToolCall("1", "Read", {"file_path": "f.txt"}),
        ToolCall("2", "Write", {"file_path": "f.txt", "content": "y"}),
    ]
    results = dispatch(calls, reg, cfg, plan_state=state)
    # Read 成功
    assert not results[0].content.startswith("Error")
    # Write 被拦
    assert results[1].content.startswith("Error")
    assert "blocked in plan mode" in results[1].content


def test_dispatcher_normal_after_exit(tmp_path, monkeypatch):
    cfg, reg, state = _setup(tmp_path, monkeypatch)
    (tmp_path / "f.txt").write_text("old")
    state.enter()
    # 用 ExitPlanMode 批准
    reg.get("ExitPlanMode").handler(plan="do stuff")
    assert not state.active
    # 之后 Write 必须先 Read
    calls = [
        ToolCall("1", "Read", {"file_path": "f.txt"}),
        ToolCall("2", "Write", {"file_path": "f.txt", "content": "new"}),
    ]
    results = dispatch(calls, reg, cfg, plan_state=state)
    assert not results[1].content.startswith("Error")


def test_bash_blocked_in_plan(tmp_path, monkeypatch):
    cfg, reg, state = _setup(tmp_path, monkeypatch)
    state.enter()
    calls = [ToolCall("1", "Bash", {"command": "echo hi"})]
    results = dispatch(calls, reg, cfg, plan_state=state)
    assert results[0].content.startswith("Error") and "blocked in plan" in results[0].content


def test_tools_registered(tmp_path, monkeypatch):
    _, reg, _ = _setup(tmp_path, monkeypatch)
    assert reg.get("EnterPlanMode") is not None
    assert reg.get("ExitPlanMode") is not None
