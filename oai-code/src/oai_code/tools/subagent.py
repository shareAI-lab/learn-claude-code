"""Task 工具: 派发隔离的子 agent。

对齐 TOOLS.md §4.1:
- subagent_type 决定工具白名单
  - Explore:        Read / Grep / Glob / Bash(只读性质,但这里不做静态判断,依赖模型)
  - general-purpose: 全部内置工具
  - Plan:           Read / Grep / Glob (禁止写)
- 返回子 agent 的最终文本总结
- 隔离 AgentState,父不关心子 messages
- 子 agent 迭代上限更严格,避免失控
"""
from __future__ import annotations

from typing import Any

from ..config.models import Config
from .registry import Tool, ToolRegistry


SUBAGENT_MAX_ITERATIONS = 30

_WHITELIST = {
    "Explore": {"Read", "Grep", "Glob", "Bash"},
    "general-purpose": None,  # None = 继承父 registry 的 allowed
    "Plan": {"Read", "Grep", "Glob"},
}


def _filtered_registry(parent: ToolRegistry, subagent_type: str) -> ToolRegistry:
    """基于父 registry,按 subagent_type 过滤工具白名单。"""
    allowed = _WHITELIST.get(subagent_type)
    sub_cfg = parent.cfg
    sub_reg = ToolRegistry(sub_cfg)
    for name in parent.names():
        if allowed is not None and name not in allowed:
            continue
        tool = parent.get(name)
        if tool:
            sub_reg.register(tool)
    return sub_reg


def _run_subagent(
    *,
    cfg: Config,
    llm,  # LLMClient, 父对象
    parent_registry: ToolRegistry,
    description: str,
    prompt: str,
    subagent_type: str,
) -> str:
    # 延迟 import 避免循环依赖
    from ..agent.loop import AgentState, LoopCallbacks, run_turn

    if subagent_type not in _WHITELIST:
        return f"Error: unknown subagent_type '{subagent_type}'"

    sub_registry = _filtered_registry(parent_registry, subagent_type)

    sub_system_prefix = (
        f"You are a subagent of oai-code running task: {description or 'task'}.\n"
        f"Subagent type: {subagent_type}. "
        f"Do the work and return a concise text summary — your reply will be handed "
        f"back to the main agent verbatim. Do not ask clarifying questions; make "
        f"reasonable assumptions and report them."
    )
    state = AgentState()

    # 不流式渲染子 agent 到 UI;父调度处会把结果作为 tool_result 展示
    try:
        run_turn(
            state,
            prompt,
            cfg=cfg,
            llm=llm,
            registry=sub_registry,
            callbacks=LoopCallbacks(),
            stream=False,
            _system_override=sub_system_prefix,
            _max_iterations=SUBAGENT_MAX_ITERATIONS,
        )
    except Exception as e:
        return f"Error: subagent crashed: {type(e).__name__}: {e}"

    # 取最后一个 assistant message 的 content 作为总结
    for msg in reversed(state.messages):
        if msg.get("role") == "assistant":
            content = msg.get("content") or ""
            if content.strip():
                return content
    return "(subagent returned no text)"


def register_task_tool(
    registry: ToolRegistry,
    *,
    cfg: Config,
    llm,
) -> None:
    registry.register(
        Tool(
            name="Task",
            description=(
                "Spawn an isolated subagent to handle a focused sub-task. "
                "Use for exploration, planning, or delegating work in isolation "
                "so it doesn't pollute the main conversation. "
                "The subagent runs to completion and returns a text summary."
            ),
            requires=["delegate"],
            input_schema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "3-5 word label shown in the UI",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Full instructions for the subagent",
                    },
                    "subagent_type": {
                        "type": "string",
                        "enum": ["Explore", "general-purpose", "Plan"],
                    },
                },
                "required": ["description", "prompt", "subagent_type"],
            },
            handler=lambda **kw: _run_subagent(
                cfg=cfg,
                llm=llm,
                parent_registry=registry,
                description=kw["description"],
                prompt=kw["prompt"],
                subagent_type=kw.get("subagent_type", "Explore"),
            ),
        )
    )
