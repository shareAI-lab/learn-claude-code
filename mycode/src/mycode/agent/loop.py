"""Agent 主循环 (M0 版).

职责:
- 调 LLM (可流式可非流式)
- 解析 tool_calls → dispatch → 回灌 tool_result
- 处理 Ctrl-C 中断语义: 为未完成 tool_call_id 补 [interrupted]
- 迭代直到 finish_reason != "tool_calls"
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..config.models import Config
from ..llm.client import LLMClient
from ..tools.registry import ToolRegistry
from .dispatcher import ToolCall, ToolResult, dispatch
from .system_prompt import build_system_prompt


MAX_ITERATIONS = 50


class Interrupted(Exception):
    """Ctrl-C 一次: 单轮打断,不退出进程。"""


@dataclass
class LoopCallbacks:
    """UI 层可注入这些钩子,接管渲染。"""

    on_text_delta: Callable[[str], None] | None = None
    on_tool_call: Callable[[ToolCall], None] | None = None
    on_tool_result: Callable[[ToolCall, ToolResult], None] | None = None
    on_iteration: Callable[[int], None] | None = None
    # M6-4: 每次 LLM 调用结束后回传 usage(含 cached_tokens)
    on_usage: Callable[[dict[str, Any]], None] | None = None


@dataclass
class AgentState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    system: str = ""


def _parse_tool_calls(raw: list[dict[str, Any]]) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for raw_call in raw:
        try:
            args = json.loads(raw_call.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append(ToolCall(id=raw_call["id"], name=raw_call["name"], arguments=args))
    return calls


def _assistant_message_from_response(
    content: str, tool_calls: list[ToolCall]
) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
    if tool_calls:
        msg["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": json.dumps(c.arguments, ensure_ascii=False),
                },
            }
            for c in tool_calls
        ]
    return msg


def run_turn(
    state: AgentState,
    user_input: str,
    *,
    cfg: Config,
    llm: LLMClient,
    registry: ToolRegistry,
    callbacks: LoopCallbacks | None = None,
    stream: bool = True,
    summarize_llm: LLMClient | None = None,
    background_manager=None,
    plan_state=None,
    _system_override: str | None = None,
    _max_iterations: int | None = None,
) -> None:
    """追加一轮用户输入,跑到本轮结束(finish_reason != tool_calls)。"""
    if not state.system:
        state.system = _system_override or build_system_prompt(cfg)
        state.messages.insert(0, {"role": "system", "content": state.system})

    state.messages.append({"role": "user", "content": user_input})

    cb = callbacks or LoopCallbacks()
    max_iter = _max_iterations or MAX_ITERATIONS

    # 延迟 import 避免循环依赖
    from ..context import auto_compact, microcompact, should_auto_compact

    for i in range(max_iter):
        # 压缩: 先 microcompact,再按阈值决定 auto-compact
        microcompact(state.messages, cfg)
        if summarize_llm is not None and should_auto_compact(state.messages, cfg):
            if cb.on_text_delta:
                cb.on_text_delta("\n[auto-compact triggered]\n")
            state.messages = auto_compact(state.messages, cfg, summarize_llm)

        # 回流后台任务结果
        if background_manager is not None:
            done = background_manager.drain()
            if done:
                lines = []
                for t in done:
                    lines.append(
                        f"[bg:{t.id}] {t.status}: {t.description}\n{t.result[:500]}"
                    )
                state.messages.append(
                    {
                        "role": "user",
                        "content": "<background-results>\n"
                        + "\n---\n".join(lines)
                        + "\n</background-results>",
                    }
                )
        if cb.on_iteration:
            cb.on_iteration(i)

        tool_specs = registry.openai_specs()
        try:
            content_text, tool_calls, finish = _call_llm(
                llm, state.messages, tool_specs, stream=stream, cb=cb
            )
        except KeyboardInterrupt:
            # 模型生成中被中断: 无 assistant 消息产生,追加 user 侧提示
            state.messages.append(
                {"role": "user", "content": "<interrupted/>"}
            )
            raise Interrupted()

        # 追加 assistant 消息(含 tool_calls 结构)
        state.messages.append(
            _assistant_message_from_response(content_text, tool_calls)
        )

        if finish != "tool_calls" or not tool_calls:
            return

        # 执行工具
        try:
            results = dispatch(tool_calls, registry, cfg, plan_state=plan_state)
        except KeyboardInterrupt:
            # 工具执行中断: 为每个未完成 id 补 [interrupted] tool_result,
            # 保持 messages 合法
            for c in tool_calls:
                state.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": c.id,
                        "content": "[interrupted by user]",
                    }
                )
            state.messages.append({"role": "user", "content": "<interrupted/>"})
            raise Interrupted()

        for c, r in zip(tool_calls, results):
            if cb.on_tool_result:
                cb.on_tool_result(c, r)
            state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": r.tool_call_id,
                    "content": r.content,
                }
            )
    # 超过最大迭代:
    state.messages.append(
        {
            "role": "user",
            "content": f"<system-note>stopped after {max_iter} iterations</system-note>",
        }
    )


def _call_llm(
    llm: LLMClient,
    messages: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
    *,
    stream: bool,
    cb: LoopCallbacks,
) -> tuple[str, list[ToolCall], str]:
    """调 LLM,返回 (文本, tool_calls, finish_reason)。"""
    if not stream:
        resp = llm.call(messages, tool_specs)
        calls = _parse_tool_calls(resp.tool_calls)
        if cb.on_text_delta and resp.content:
            cb.on_text_delta(resp.content)
        for c in calls:
            if cb.on_tool_call:
                cb.on_tool_call(c)
        if cb.on_usage:
            raw_usage = {}
            try:
                raw_usage = resp.raw.usage.model_dump() if resp.raw.usage else {}
            except Exception:
                raw_usage = {}
            cb.on_usage(
                {"cached_tokens": resp.cached_tokens, "usage": raw_usage}
            )
        return resp.content, calls, resp.finish_reason

    text_buf: list[str] = []
    tool_accum: dict[int, dict[str, Any]] = {}
    finish: str = "stop"
    last_usage: dict[str, Any] | None = None
    for ev in llm.stream(messages, tool_specs):
        t = ev["type"]
        if t == "text":
            text_buf.append(ev["delta"])
            if cb.on_text_delta:
                cb.on_text_delta(ev["delta"])
        elif t == "tool_call_start":
            tool_accum[ev["index"]] = {
                "id": ev["id"],
                "name": ev["name"],
                "arguments": "",
            }
        elif t == "tool_call_args":
            idx = ev["index"]
            if idx in tool_accum:
                tool_accum[idx]["arguments"] += ev["delta"]
        elif t == "finish":
            finish = ev["reason"]
        elif t == "usage":
            last_usage = {
                "cached_tokens": ev.get("cached_tokens", 0),
                "usage": ev.get("usage", {}),
            }
    if cb.on_usage and last_usage is not None:
        cb.on_usage(last_usage)
    raw_calls = [tool_accum[k] for k in sorted(tool_accum)]
    calls = _parse_tool_calls(raw_calls)
    for c in calls:
        if cb.on_tool_call:
            cb.on_tool_call(c)
    return "".join(text_buf), calls, finish
