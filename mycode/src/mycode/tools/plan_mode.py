"""Plan Mode: agent 只读探索 → 拟定方案 → 用户批准 → 写入执行。

对齐 Kode 的 EnterPlanMode / ExitPlanMode 对:
- EnterPlanMode: 设 flag, dispatcher 拒绝所有 write/exec/delegate 工具
- ExitPlanMode(plan): 提交方案,通过 AskUserQuestion 要求用户批准,
  approve 后关 flag 继续执行

flag 存在一个共享的 PlanModeState 单例里,被 dispatcher 和 CLI 读取。
"""
from __future__ import annotations

from dataclasses import dataclass

from .ask_user import InteractiveUnavailable
from .registry import Tool, ToolRegistry


# 这些工具在 plan 模式下**始终允许**(读取 + 自我管理)
_PLAN_ALLOWED = {
    "Read",
    "Grep",
    "Glob",
    "LoadSkill",
    "TodoWrite",
    "TaskList",
    "TaskGet",
    "BackgroundCheck",
    "ListTeammates",
    "ReadInbox",
    "AskUserQuestion",
    "EnterPlanMode",
    "ExitPlanMode",
}


@dataclass
class PlanModeState:
    active: bool = False

    def enter(self) -> str:
        if self.active:
            return "Already in plan mode."
        self.active = True
        return (
            "Entered plan mode. Only read-only tools are allowed until you call "
            "ExitPlanMode with a plan for user approval."
        )

    def exit_with_approval(self, plan: str, ask_fn) -> str:
        if not self.active:
            return "Error: not in plan mode"
        plan = (plan or "").strip()
        if not plan:
            return "Error: plan text required"
        questions = [
            {
                "question": "Approve this plan and exit plan mode?",
                "header": "Plan review",
                "options": [
                    {
                        "label": "Approve",
                        "description": "Exit plan mode and let the agent execute the plan",
                    },
                    {
                        "label": "Reject",
                        "description": "Stay in plan mode; the agent will revise",
                    },
                ],
            }
        ]
        try:
            answers = ask_fn(questions)
        except InteractiveUnavailable as e:
            return f"Error: {e}"
        if not answers:
            return "Error: no answer received"
        chosen = answers[0].get("label", "").lower()
        if chosen == "approve":
            self.active = False
            return f"Plan approved. Exited plan mode.\n\nPlan:\n{plan}"
        return f"Plan rejected. Still in plan mode. Feedback (if any): {answers[0].get('description', '')}"


def is_tool_allowed_in_plan_mode(tool_name: str, requires: list[str]) -> bool:
    """plan 模式下某工具是否允许执行。

    规则:
    - 在 _PLAN_ALLOWED 白名单里 → 允许
    - 声明了 write/exec/delegate → 拒绝
    - 其它(无 requires 标签)→ 允许(保守,只拦写/执行/派发)
    """
    if tool_name in _PLAN_ALLOWED:
        return True
    blocked = {"write", "exec", "delegate"}
    return not any(r in blocked for r in (requires or []))


def register_plan_mode(
    registry: ToolRegistry,
    *,
    state: PlanModeState,
    ask_fn,
) -> None:
    registry.register(
        Tool(
            name="EnterPlanMode",
            description=(
                "Enter read-only plan mode. While in plan mode, Write/Edit/Bash/"
                "Task and similar mutating tools are blocked. Use for exploration "
                "before proposing a plan."
            ),
            input_schema={"type": "object", "properties": {}},
            handler=lambda **_: state.enter(),
        )
    )
    registry.register(
        Tool(
            name="ExitPlanMode",
            description=(
                "Submit a plan for user approval and exit plan mode if approved. "
                "Pass the full plan as markdown text in 'plan'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "Markdown text describing the plan",
                    }
                },
                "required": ["plan"],
            },
            handler=lambda **kw: state.exit_with_approval(kw["plan"], ask_fn),
        )
    )
