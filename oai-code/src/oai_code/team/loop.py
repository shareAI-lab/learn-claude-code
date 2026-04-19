"""Teammate 独立 agent loop,在线程里跑。

与主 agent loop 的核心差异:
- 每轮开头 drain inbox,把消息转成 user message 注入
- 工具集 = 父可用工具(仅只读派) + team 工具(SendMessage/Idle)
- 支持 Idle 工具: 标记空闲并短暂等待新消息
- shutdown_request 消息 → 优雅终止
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable

from ..agent.loop import AgentState, LoopCallbacks, run_turn
from ..config.models import Config
from ..llm.client import LLMClient
from ..tools.registry import Tool, ToolRegistry
from .bus import MessageBus
from .manager import TeammateManager


TEAMMATE_WHITELIST_READ = {"Read", "Grep", "Glob", "Bash"}
TEAMMATE_WHITELIST_FULL = {"Read", "Grep", "Glob", "Bash", "Write", "Edit"}


def _teammate_system_prompt(name: str, role: str, team_name: str, wd) -> str:
    return (
        f"You are '{name}', a teammate in team '{team_name}', role: {role}.\n"
        f"Workspace: {wd}.\n"
        "Communication:\n"
        "- Messages from others arrive as <inbox> user messages each turn.\n"
        "- Use SendMessage to reply; use Idle when you have no work.\n"
        "- If you receive shutdown_request, finish your current step and stop.\n"
        "Keep replies concise; prefer tool calls over narration."
    )


def _build_teammate_registry(
    parent: ToolRegistry,
    bus: MessageBus,
    self_name: str,
    read_only: bool = True,
) -> ToolRegistry:
    """队友的工具集: 白名单过父 registry + 加 team 专用工具。"""
    wl = TEAMMATE_WHITELIST_READ if read_only else TEAMMATE_WHITELIST_FULL
    sub = ToolRegistry(parent.cfg)
    for n in parent.names():
        if n in wl:
            t = parent.get(n)
            if t:
                sub.register(t)

    # team 专用工具
    sub.register(
        Tool(
            name="SendMessage",
            description="Send a message to another teammate.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "content": {"type": "string"},
                    "msg_type": {"type": "string"},
                },
                "required": ["to", "content"],
            },
            handler=lambda **kw: bus.send(
                self_name, kw["to"], kw["content"], kw.get("msg_type", "message")
            ),
        )
    )
    sub.register(
        Tool(
            name="Idle",
            description="Mark self as idle and wait for new messages.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda **_: "Idle requested",
        )
    )
    return sub


def start_teammate_loop(
    *,
    name: str,
    role: str,
    prompt: str,
    cfg: Config,
    llm: LLMClient,
    parent_registry: ToolRegistry,
    bus: MessageBus,
    manager: TeammateManager,
    read_only: bool = False,
    max_work_iterations: int = 20,
    idle_poll_sec: float = 2.0,
    idle_timeout_sec: float = 60.0,
) -> threading.Thread:
    """在独立线程里跑队友 agent loop。立即返回线程对象,不阻塞。"""

    sub_reg = _build_teammate_registry(parent_registry, bus, name, read_only)
    system = _teammate_system_prompt(name, role, "default", cfg.workspace_root())

    def _loop() -> None:
        state = AgentState()
        state.system = system
        state.messages.append({"role": "system", "content": system})
        state.messages.append({"role": "user", "content": prompt})

        while True:
            manager.set_status(name, "working")
            # work phase: 最多跑 N 轮直到模型停止或调用 Idle
            for _ in range(max_work_iterations):
                inbox = bus.read_inbox(name)
                terminated = _inject_inbox(state, inbox)
                if terminated:
                    manager.set_status(name, "shutdown")
                    return
                try:
                    run_turn(
                        state,
                        "",
                        cfg=cfg,
                        llm=llm,
                        registry=sub_reg,
                        callbacks=LoopCallbacks(),
                        stream=False,
                        _system_override=system,
                        _max_iterations=3,
                    )
                except Exception as e:
                    print(f"[team:{name}] loop error: {type(e).__name__}: {e}")
                    manager.set_status(name, "shutdown")
                    return

                # 检查是否调用了 Idle / 是否无 tool_calls 继续
                if _last_assistant_called_idle(state):
                    break
                if _finished_without_tools(state):
                    break

            # idle phase
            manager.set_status(name, "idle")
            deadline = time.time() + idle_timeout_sec
            woke_up = False
            while time.time() < deadline:
                time.sleep(idle_poll_sec)
                inbox = bus.read_inbox(name)
                if inbox:
                    terminated = _inject_inbox(state, inbox)
                    if terminated:
                        manager.set_status(name, "shutdown")
                        return
                    woke_up = True
                    break
            if not woke_up:
                manager.set_status(name, "shutdown")
                return

    t = threading.Thread(target=_loop, daemon=True, name=f"teammate-{name}")
    t.start()
    return t


# ---------- helpers ----------


def _inject_inbox(state: AgentState, inbox: list[dict[str, Any]]) -> bool:
    """把 inbox 消息注入 messages。返回 True 表示收到 shutdown_request 需终止。"""
    terminate = False
    for msg in inbox:
        if msg.get("type") == "shutdown_request":
            terminate = True
            state.messages.append(
                {
                    "role": "user",
                    "content": f"<shutdown-request from=\"{msg.get('from')}\">"
                    f"{msg.get('content', '')}</shutdown-request>",
                }
            )
        else:
            state.messages.append(
                {
                    "role": "user",
                    "content": f"<inbox from=\"{msg.get('from')}\" "
                    f"type=\"{msg.get('type', 'message')}\">"
                    f"{msg.get('content', '')}</inbox>",
                }
            )
    return terminate


def _last_assistant_called_idle(state: AgentState) -> bool:
    for m in reversed(state.messages):
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                if tc.get("function", {}).get("name") == "Idle":
                    return True
            return False
    return False


def _finished_without_tools(state: AgentState) -> bool:
    """最后一条 assistant 没有 tool_calls → 本轮自然结束。"""
    for m in reversed(state.messages):
        if m.get("role") == "assistant":
            return not m.get("tool_calls")
    return False
