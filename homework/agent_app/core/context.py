"""Read-only dynamic context construction and message helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from ..features.memory import read_memory_index
from ..features.skills import list_skills
from ..features.todos import format_current_todos


def build_context(runtime, tools: list[dict]) -> dict:
    memories = read_memory_index(runtime.memory)
    skills = list_skills(runtime.skills) if runtime.skills.registry else ""
    tool_names = sorted(tool["name"] for tool in tools)
    serialized_tools = json.dumps(
        tools,
        ensure_ascii=False,
        sort_keys=True,
    )
    tool_fingerprint = hashlib.sha256(
        serialized_tools.encode("utf-8")
    ).hexdigest()

    with runtime.mcp.lock:
        connected_mcp = sorted(runtime.mcp.clients)
    with runtime.team.lock:
        active_names = sorted(runtime.team.active)

    return {
        "enabled_tools": tool_names,
        "workspace": str(runtime.config.workdir),
        "memories": memories,
        "skills": skills,
        "todos": format_current_todos(runtime.session),
        "active_teammates": active_names,
        "connect_mcp": connected_mcp,
        "tool_fingerprint": tool_fingerprint,
        "current_time": datetime.now().isoformat(timespec="seconds"),
    }


def append_user_text_blocks(messages: list, texts: list[str]) -> None:
    if not texts:
        return

    blocks = [{"type": "text", "text": text} for text in texts]

    if messages and messages[-1].get("role") == "user":
        content = messages[-1].get("content")
        if isinstance(content, list):
            content.extend(blocks)
        else:
            messages[-1]["content"] = [
                {"type": "text", "text": str(content)},
                *blocks,
            ]
    else:
        messages.append({"role": "user", "content": blocks})
