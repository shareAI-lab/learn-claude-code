#!/usr/bin/env python3
# Deep Agents track: planning -- keep session plan state outside the model's head.
"""
s03_todo_write.py - Session Planning with Deep Agents tools

This is the first chapter where custom state becomes natural. The session plan
belongs in explicit runtime state, not in the model's hidden chain-of-thought.
Middleware renders that state back into the prompt, and the todo tool updates it
through LangChain state updates.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Literal, Protocol

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain.tools import InjectedToolCallId, tool
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import NotRequired, TypedDict

try:
    from .common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        extract_text,
        latest_assistant_text,
        read_file,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        extract_text,
        latest_assistant_text,
        read_file,
        write_file,
    )

PLAN_REMINDER_INTERVAL = 3
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use the todo tool for complex multi-step work when explicit progress tracking is helpful.
Skip the todo tool for simple, trivial, or purely conversational requests that can be completed directly.
When a task genuinely needs a plan, call todo before other tools and write the full current plan.
Each todo item must include non-empty content; use pending, in_progress, or completed status.
Keep exactly one step in_progress while unfinished work remains.
Mark steps completed as soon as they are actually done; if blocked, leave the current step in_progress or rewrite the plan.
Revise the todo list as new information appears, remove stale steps, and add newly discovered necessary steps.
Never call todo multiple times in parallel within the same response.
Refresh the plan as work advances. Prefer tools over prose."""

# 项目约束（给维护者读）：
# - todo 是 LangChain tool calling 的结构化工具入参，不是最终回答 JSON。
# - 工具入参必须通过 Pydantic args_schema 暴露 required / enum / extra-forbid
#   约束；不要退回 list[dict[str, Any]] 让模型自由填对象。
# - 不在 Python 侧兜底猜 task/step/done/doing 等别名；错 JSON 应由 schema 暴露。
# - 如果以后新增 todo JSON 字段，先改 TodoPlanItemInput / TodoInput 和测试。
# - with_structured_output()/response_format 只用于最终结构化回答，不用于这种
#   需要写入 LangGraph state 的工具参数。
# - 当前 todo 工具只需要 `items` 和 `tool_call_id`，不读取 runtime.state/context/store。
# - 按 LangChain 官方 todo middleware 风格，用 InjectedToolCallId 注入当前调用 id。
# - 为了同时保留显式 args_schema 和隐藏注入字段，TodoInput 内部包含
#   `tool_call_id: Annotated[str | None, InjectedToolCallId] = None`；
#   它不会出现在模型可见的 tool_call_schema 中，但工具执行时会被注入。


class PlanItemState(TypedDict):
    """运行时保存的单条计划状态。

    这是 agent state 里的内部格式，渲染器和 middleware 都读取这个结构。
    它和 TodoPlanItemInput 字段保持一致，但它是普通 dict，方便写入
    LangGraph state。
    """

    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: NotRequired[str]


class PlanningState(AgentState):
    """s03 给 LangChain agent 增加的自定义短期状态。

    AgentState 已经包含 messages；这里额外保存：
    - items: 当前会话计划。
    - rounds_since_update: 计划多久没被 todo 工具刷新，用于触发提醒。
    """

    items: NotRequired[list[PlanItemState]]
    rounds_since_update: NotRequired[int]


# 注意：
# TodoPlanItemInput / TodoInput 是 args_schema 的一部分，Pydantic class docstring
# 可能进入模型可见的 JSON schema description。
# 所以这里不给这两个 schema class 写面向维护者的长 docstring；人类说明放在
# 上方注释里，模型说明放在 Field(description=...) 和 tool(description=...)。
class TodoPlanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        description="Non-empty description of this plan step.",
    )
    status: Literal["pending", "in_progress", "completed"] = Field(
        ...,
        description="Current step status. Exactly one item should be in_progress.",
    )
    activeForm: str | None = Field(
        default=None,
        description="Short gerund phrase shown only for the in_progress step.",
    )

    @field_validator("content")
    @classmethod
    def _content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content required")
        return value

    @field_validator("activeForm")
    @classmethod
    def _active_form_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TodoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TodoPlanItemInput] = Field(
        ...,
        min_length=1,
        max_length=12,
        description=(
            "Complete current plan. Every item must have content and status; "
            "use pending, in_progress, or completed."
        ),
    )
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None


def normalize_plan_items(
    items: list[TodoPlanItemInput | dict[str, Any]],
) -> list[PlanItemState]:
    """把 todo 工具入参转换成 LangGraph state 可保存的普通 dict。

    这一步做三件事：
    1. `TodoInput(items=items)` 触发 Pydantic 校验，确保 JSON 结构符合
       LangChain tool schema。
    2. 将 Pydantic 对象转成 PlanItemState 普通 dict，方便写入 state 和渲染。
    3. 额外检查最多只能有一个 in_progress，避免模型同时标记多个当前步骤。
    """

    validated = TodoInput(items=items)

    normalized: list[PlanItemState] = []
    in_progress_count = 0
    for item_input in validated.items:
        if item_input.status == "in_progress":
            in_progress_count += 1

        item: PlanItemState = {
            "content": item_input.content,
            "status": item_input.status,
        }
        if item_input.activeForm:
            item["activeForm"] = item_input.activeForm
        normalized.append(item)

    if in_progress_count > 1:
        raise ValueError("Only one plan item can be in_progress")

    return normalized


class PlanRenderer(Protocol):
    """计划渲染器接口。

    s03 当前只渲染到终端，但先把“如何显示计划”和“如何保存计划”分开。
    后续如果要做 Web / API / 事件流展示，可以实现同样接口而不改 todo 工具。
    """

    def render_plan_items(self, items: list[PlanItemState]) -> str:
        """Return display text for the current session plan."""
        ...

    def reminder_text(
        self,
        items: list[PlanItemState],
        rounds_since_update: int,
    ) -> str | None:
        """Return reminder text when the current plan is stale."""
        ...


class TerminalPlanRenderer:
    """终端版计划渲染器。

    把 state 里的 items 变成用户能直接看到的文本：
    [ ] pending, [>] in_progress, [x] completed。
    """

    def render_plan_items(self, items: list[PlanItemState]) -> str:
        """生成当前计划的终端文本。"""

        if not items:
            return "No session plan yet."

        lines: list[str] = []
        for item in items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[
                item["status"]
            ]
            line = f"{marker} {item['content']}"
            active_form = item.get("activeForm", "")
            if item["status"] == "in_progress" and active_form:
                line += f" ({active_form})"
            lines.append(line)

        completed = sum(1 for item in items if item["status"] == "completed")
        lines.append(f"\n({completed}/{len(items)} completed)")
        return "\n".join(lines)

    def reminder_text(
        self,
        items: list[PlanItemState],
        rounds_since_update: int,
    ) -> str | None:
        """当计划连续多轮未更新时，生成注入给模型的提醒文本。"""

        if not items:
            return None
        if rounds_since_update < PLAN_REMINDER_INTERVAL:
            return None
        return "<reminder>Refresh your current plan before continuing.</reminder>"


DEFAULT_PLAN_RENDERER = TerminalPlanRenderer()


def render_plan_items(
    items: list[PlanItemState],
    renderer: PlanRenderer = DEFAULT_PLAN_RENDERER,
) -> str:
    """使用默认渲染器展示计划。

    包一层函数是为了让教程代码好读，也方便测试时替换 renderer。
    """

    return renderer.render_plan_items(items)


def reminder_text(
    items: list[PlanItemState],
    rounds_since_update: int,
    renderer: PlanRenderer = DEFAULT_PLAN_RENDERER,
) -> str | None:
    """使用默认渲染器判断是否需要提醒模型刷新计划。"""

    return renderer.reminder_text(items, rounds_since_update)


def todo(
    items: list[TodoPlanItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """todo 工具本体：把模型给出的计划写回 LangGraph state。

    返回 Command(update=...) 是 LangGraph/LangChain 的状态更新方式：
    - items 写入当前会话计划；
    - rounds_since_update 重置为 0；
    - ToolMessage 把渲染后的计划作为工具结果返回给模型。

    这里不再依赖 ToolRuntime，因为这个工具并不读取 runtime 的其他内容；
    它只需要当前这次 tool call 的 id，用于构造 ToolMessage。
    """

    if tool_call_id is None:
        raise ValueError("tool_call_id is required for todo tool execution")

    normalized = normalize_plan_items(items)
    rendered = render_plan_items(normalized)
    return Command(
        update={
            "items": normalized,
            "rounds_since_update": 0,
            "messages": [
                ToolMessage(content=rendered, tool_call_id=tool_call_id)
            ],
        }
    )


todo_tool = tool(
    "todo",
    args_schema=TodoInput,
    description=(
        "Create or replace the visible session plan for complex multi-step work. "
        "Use it when a task needs explicit planning, progress tracking, or later "
        "revision; skip it for simple one-step or purely conversational requests. "
        "Input must be the full current plan as JSON items[]. Each item requires "
        "content and status (pending, in_progress, or completed), and exactly one "
        "item should stay in_progress while work remains."
    ),
)(todo)

TOOLS = [bash, read_file, write_file, edit_file, todo_tool]


class PlanningMiddleware(AgentMiddleware[PlanningState]):
    """把计划状态接回每一轮模型调用。

    todo 工具负责“写计划”；middleware 负责“读计划并注入 prompt”。
    这样模型下一轮会看到 Current session plan，而不是只把计划藏在 Python state。
    """

    state_schema = PlanningState

    def __init__(self) -> None:
        super().__init__()
        self._updated_this_turn = False

    def before_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        """每次 agent invocation 开始时补齐 s03 自定义 state 默认值。"""

        self._updated_this_turn = False
        return {
            key: value
            for key, value in (("items", []), ("rounds_since_update", 0))
            if key not in state
        } or None

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable):
        """包住工具调用，用来记录本轮是否调用过 todo。"""

        if request.tool_call["name"] == "todo":
            self._updated_this_turn = True
        return handler(request)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """每次模型调用前，把当前计划追加到 system message。

        request.system_message.content_blocks 是 LangChain 官方的消息块接口。
        这里追加 text block，让模型在下一次思考时看到最新计划和过期提醒。
        """

        items = request.state.get("items", [])
        rounds_since_update = request.state.get("rounds_since_update", 0)
        extra_blocks: list[dict[str, str]] = []

        if items:
            extra_blocks.append(
                {
                    "type": "text",
                    "text": "Current session plan:\n" + render_plan_items(items),
                }
            )
            reminder = reminder_text(items, rounds_since_update)
            if reminder:
                extra_blocks.append({"type": "text", "text": reminder})

        if not extra_blocks:
            return handler(request)

        return handler(
            request.override(
                system_message=SystemMessage(
                    content=[*request.system_message.content_blocks, *extra_blocks]
                )
            )
        )

    def after_model(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        """拒绝同一轮里并行多次调用 todo。

        todo 会整体替换当前计划，所以一条 AIMessage 里如果同时出现多个 todo
        tool call，会产生“哪个计划才算最终版本”的歧义。这里沿用 LangChain
        官方 todo middleware 的思路，在工具真正执行前直接返回错误 ToolMessage。
        """

        messages = state.get("messages", [])
        if not messages:
            return None

        last_ai_message = next(
            (message for message in reversed(messages) if isinstance(message, AIMessage)),
            None,
        )
        if last_ai_message is None or not last_ai_message.tool_calls:
            return None

        todo_calls = [call for call in last_ai_message.tool_calls if call["name"] == "todo"]
        if len(todo_calls) <= 1:
            return None

        return {
            "messages": [
                ToolMessage(
                    content=(
                        "Error: The `todo` tool should never be called multiple times in "
                        "parallel. Call it once per model response so the session plan has "
                        "one unambiguous replacement."
                    ),
                    tool_call_id=call["id"],
                    status="error",
                )
                for call in todo_calls
            ]
        }

    def after_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        """本轮结束后维护 stale counter。

        如果本轮调用过 todo，计划刚刷新，不增加计数；否则只要已有计划，
        rounds_since_update 就加一，后续达到阈值会触发 reminder_text。
        """

        if self._updated_this_turn:
            return None
        if state.get("items"):
            return {"rounds_since_update": state.get("rounds_since_update", 0) + 1}
        return None


SESSION_STATE: dict[str, Any] = {
    "items": [],
    "rounds_since_update": 0,
}


def build_agent():
    """创建 s03 agent，并注册带 args_schema 的 todo_tool。"""

    return create_agent(
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        middleware=[PlanningMiddleware()],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    """推进一轮对话，并把 LangGraph 返回的计划状态同步回 SESSION_STATE。"""

    result = build_agent().invoke({"messages": list(messages), **SESSION_STATE})
    SESSION_STATE.update(
        {
            "items": result.get("items", []),
            "rounds_since_update": result.get("rounds_since_update", 0),
        }
    )
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text


def current_plan_text() -> str | None:
    """给 CLI 使用：如果当前已有计划，就返回可打印的终端计划文本。"""

    items = SESSION_STATE.get("items") or []
    if not items:
        return None
    return render_plan_items(items)


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms03-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        try:
            final = agent_loop(history)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        plan_text = current_plan_text()
        if plan_text:
            print("\nCurrent session plan:")
            print(plan_text)
        print()
