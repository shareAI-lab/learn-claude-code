from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason=(
        "Real-LLM test requires OPENAI_API_KEY in the environment. "
        "Example: set -a; source coding-deepgent/.env; set +a"
    ),
)


PROMPT = (
    "请创建一个三步 write_plan 计划："
    "1) 检查当前目录有哪些 README 文件；"
    "2) 读取 agents_deepagents/README.md 的前20行；"
    "3) 总结 s03 write_plan 功能是否在终端可见。"
    "要求恰好三项，第一项必须是 in_progress 并给出 activeForm。"
)


def test_s03_terminal_plan_is_visible_after_real_llm_generates_todo_args() -> None:
    """真实 LLM 集成测试：验证 s03 的终端计划显示链路是通的。

    这里不用自由代理循环，而是：
    1. 用真实 OpenAI 模型绑定真实 `write_plan_tool` schema；
    2. 强制 `tool_choice='required'`，确保模型必须产出 write_plan 参数；
    3. 用这些真实参数调用 `s03.write_plan(...)`；
    4. 把返回的 items 写入 SESSION_STATE，再检查 `current_plan_text()`。

    这样测试的是真实 LLM + 真实 tool schema + 真实终端渲染路径，
    同时避免“模型这次恰好没调用工具”导致测试不稳定。
    """

    from agents_deepagents import s03_todo_write as s03

    model = s03.build_openai_model().bind_tools(
        [s03.write_plan_tool],
        tool_choice="required",
    )
    response = model.invoke(PROMPT)

    assert response.tool_calls, "real model did not emit any tool call"
    write_plan_call = response.tool_calls[0]
    assert write_plan_call["name"] == "write_plan"

    command = s03._write_plan_command(
        write_plan_call["args"]["items"],
        tool_call_id=write_plan_call["id"],
    )

    previous_state = dict(s03.SESSION_STATE)
    try:
        s03.SESSION_STATE["items"] = command.update["items"]
        s03.SESSION_STATE["rounds_since_update"] = 0
        terminal_text = s03.current_plan_text()
    finally:
        s03.SESSION_STATE.clear()
        s03.SESSION_STATE.update(previous_state)

    assert terminal_text is not None
    assert "检查当前目录有哪些 README 文件" in terminal_text
    assert "读取 agents_deepagents/README.md 的前20行" in terminal_text
    assert "总结 s03 write_plan 功能是否在终端可见" in terminal_text
    assert any(marker in terminal_text for marker in ("[ ]", "[>]", "[x]"))
