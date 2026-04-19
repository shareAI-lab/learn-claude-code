"""给 lead(主 agent) 用的团队工具:
SpawnTeammate / SendMessage / Broadcast / ReadInbox / ListTeammates。
"""
from __future__ import annotations

from ..config.models import Config
from ..llm.client import LLMClient
from ..tools.registry import Tool, ToolRegistry
from .bus import MessageBus
from .manager import TeammateManager
from .loop import start_teammate_loop


LEAD_NAME = "lead"


def register_team_tools(
    registry: ToolRegistry,
    *,
    cfg: Config,
    llm: LLMClient,
    bus: MessageBus,
    manager: TeammateManager,
    parent_registry: ToolRegistry,
) -> None:
    def _spawn(**kw) -> str:
        name = kw["name"]
        role = kw["role"]
        prompt = kw["prompt"]
        read_only = kw.get("read_only", False)
        if manager.find(name):
            return f"Error: teammate '{name}' already exists"
        manager.register(name, role)
        t = start_teammate_loop(
            name=name,
            role=role,
            prompt=prompt,
            cfg=cfg,
            llm=llm,
            parent_registry=parent_registry,
            bus=bus,
            manager=manager,
            read_only=read_only,
        )
        manager.register_thread(name, t)
        return f"Spawned teammate '{name}' (role={role}, read_only={read_only})"

    registry.register(
        Tool(
            name="SpawnTeammate",
            description=(
                "Create a persistent teammate that runs in its own thread with "
                "its own agent loop. The teammate reads its inbox each turn and "
                "can be sent messages via SendMessage. Returns immediately."
            ),
            requires=["delegate"],
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "prompt": {"type": "string"},
                    "read_only": {"type": "boolean", "default": False},
                },
                "required": ["name", "role", "prompt"],
            },
            handler=_spawn,
        )
    )

    registry.register(
        Tool(
            name="SendMessage",
            description="Send a message to a teammate by name.",
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
                LEAD_NAME,
                kw["to"],
                kw["content"],
                kw.get("msg_type", "message"),
            ),
        )
    )

    registry.register(
        Tool(
            name="Broadcast",
            description="Send a message to all teammates at once.",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
            handler=lambda **kw: bus.broadcast(
                LEAD_NAME, kw["content"], manager.names()
            ),
        )
    )

    registry.register(
        Tool(
            name="ReadInbox",
            description="Read and drain the lead's inbox (messages from teammates).",
            input_schema={"type": "object", "properties": {}},
            handler=lambda **_: _fmt_inbox(bus.read_inbox(LEAD_NAME)),
        )
    )

    registry.register(
        Tool(
            name="ListTeammates",
            description="List all teammates with their current status.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda **_: manager.render(),
        )
    )


def _fmt_inbox(msgs: list[dict]) -> str:
    if not msgs:
        return "(inbox empty)"
    lines = []
    for m in msgs:
        lines.append(
            f"[{m.get('type', 'message')}] from={m.get('from', '?')}: "
            f"{m.get('content', '')[:500]}"
        )
    return "\n".join(lines)
