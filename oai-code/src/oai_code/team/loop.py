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
from ..tools.tasks import TaskStore
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
    task_store: TaskStore | None = None,
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
    if task_store is not None:
        sub.register(
            Tool(
                name="ClaimTask",
                description=(
                    "Claim an unclaimed, unblocked task from the shared board. "
                    "After claiming, the task belongs to you and should be driven "
                    "to completion."
                ),
                requires=["write"],
                input_schema={
                    "type": "object",
                    "properties": {"task_id": {"type": "integer"}},
                    "required": ["task_id"],
                },
                handler=lambda **kw: _claim_task(task_store, self_name, kw["task_id"]),
            )
        )
    return sub


def _claim_task(store: TaskStore, self_name: str, tid: int) -> str:
    """把 task 的 owner 设为当前队友名,并置 in_progress。"""
    import json

    try:
        task = json.loads(store.get(int(tid)))
    except Exception:
        return store.get(int(tid))  # 已经是 Error: 字符串
    if "id" not in task:
        return task  # Error 透传
    if task.get("owner") and task["owner"] != self_name:
        return f"Error: task {tid} already owned by {task['owner']}"
    if task.get("blockedBy"):
        return f"Error: task {tid} blocked by {task['blockedBy']}"
    out = store.update(int(tid), status="in_progress", owner=self_name)
    return out


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
    task_store: TaskStore | None = None,
    read_only: bool = False,
    max_work_iterations: int = 20,
    idle_poll_sec: float = 2.0,
    idle_timeout_sec: float = 60.0,
    autonomous: bool = True,
) -> threading.Thread:
    """在独立线程里跑队友 agent loop。立即返回线程对象,不阻塞。

    autonomous=True 时,IDLE 阶段会自动扫描 .oaic/tasks/ 认领未阻塞任务。
    """

    sub_reg = _build_teammate_registry(parent_registry, bus, name, read_only, task_store)
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
                # 自治: 扫任务板,认领第一个 unblocked + unclaimed 任务
                if autonomous and task_store is not None:
                    claimed = _try_autoclaim(task_store, name, state)
                    if claimed:
                        woke_up = True
                        break
            if not woke_up:
                manager.set_status(name, "shutdown")
                return
            # 身份重注入: compact 可能把 system 压没了,
            # 若 non-system 消息 ≤ 3 说明历史被截断,补一条
            _reinject_identity(state, name, role)

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


def _try_autoclaim(store: TaskStore, self_name: str, state: AgentState) -> bool:
    """扫 store,找第一个 unblocked + unclaimed 的 task,认领它并注入 user 消息。

    返回 True 表示成功认领,False 表示没活干。
    """
    import json

    for p in sorted(store.dir.glob("task_*.json")):
        try:
            task = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if task.get("owner"):
            continue
        if task.get("status") not in ("pending", None):
            continue
        if task.get("blockedBy"):
            continue
        # claim
        store.update(int(task["id"]), status="in_progress", owner=self_name)
        state.messages.append(
            {
                "role": "user",
                "content": (
                    f"<auto-claimed task_id=\"{task['id']}\">"
                    f"You autonomously claimed this task. Subject: {task.get('subject', '')}. "
                    f"Description: {task.get('description', '')}. "
                    f"Drive it to completion, then mark status=completed via TaskUpdate."
                    f"</auto-claimed>"
                ),
            }
        )
        return True
    return False


def _reinject_identity(state: AgentState, name: str, role: str) -> None:
    """messages 被 compact 截断后,补一条身份提示。"""
    non_system = [m for m in state.messages if m.get("role") != "system"]
    if len(non_system) > 3:
        return
    state.messages.append(
        {
            "role": "user",
            "content": f"<identity>You are teammate '{name}' (role: {role}). "
            f"Continue your duties.</identity>",
        }
    )


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
