from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any, cast

from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from coding_deepgent.runtime import RuntimeContext
from coding_deepgent.subagents.schemas import (
    ForkPlaceholderLayout,
    ToolPoolIdentitySnapshot,
    ToolSurfaceSnapshot,
)
from coding_deepgent.tool_system import ToolPoolProjection

FORK_RECURSION_GUARD_MARKER = "<CODING_DEEPGENT_FORK>"
FORK_PLACEHOLDER_LAYOUT_VERSION = "fork_tool_result_v1"
FORK_REPLACEMENT_STATE_HOOK = "preserve_tool_result_ids"
FORK_MAX_TURNS = 25


def fingerprint_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def tool_surface_snapshot(projection: ToolPoolProjection) -> ToolPoolIdentitySnapshot:
    tools: list[ToolSurfaceSnapshot] = []
    for visible_order, capability in enumerate(projection.capabilities):
        schema = cast(Any, capability.tool.tool_call_schema).model_json_schema()
        tools.append(
            ToolSurfaceSnapshot(
                name=capability.name,
                visible_order=visible_order,
                schema_fingerprint=fingerprint_text(stable_json(schema)),
                description=str(getattr(capability.tool, "description", "")).strip()
                or capability.name,
            )
        )
    fingerprint = fingerprint_text(stable_json([tool.model_dump() for tool in tools]))
    return ToolPoolIdentitySnapshot(fingerprint=fingerprint, tools=tools)


def fork_placeholder_layout(messages: Sequence[BaseMessage]) -> ForkPlaceholderLayout:
    paired_tool_call_ids = [
        message.tool_call_id.strip()
        for message in messages
        if isinstance(message, ToolMessage) and message.tool_call_id.strip()
    ]
    return ForkPlaceholderLayout(
        version=FORK_PLACEHOLDER_LAYOUT_VERSION,
        paired_tool_call_ids=paired_tool_call_ids,
        placeholder_messages=[
            f"<fork-tool-result:{tool_call_id}>"
            for tool_call_id in paired_tool_call_ids
        ],
        replacement_state_hook=FORK_REPLACEMENT_STATE_HOOK,
    )


def fork_directive(intent: str) -> str:
    return "\n".join(
        [
            FORK_RECURSION_GUARD_MARKER,
            "Fork child contract: inherit the parent rendered prompt and visible tools exactly.",
            f"Branch intent: {intent.strip()}",
            "Return only the branch result needed by the parent.",
        ]
    )


def runtime_visible_tool_projection(runtime: ToolRuntime) -> ToolPoolProjection:
    context = getattr(runtime, "context", None)
    projection = getattr(context, "visible_tool_projection", None)
    if not isinstance(projection, ToolPoolProjection):
        raise RuntimeError("Fork requires a visible tool projection in runtime context")
    return projection


def runtime_rendered_system_prompt(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    prompt = getattr(context, "rendered_system_prompt", None)
    if not isinstance(prompt, str) or not prompt.strip():
        raise RuntimeError("Fork requires a rendered system prompt in runtime context")
    return prompt


def message_tool_call_ids(message: BaseMessage) -> tuple[str, ...]:
    if isinstance(message, AIMessage):
        return tuple(
            str(item.get("id", "")).strip()
            for item in message.tool_calls
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        )
    content = getattr(message, "content", None)
    if isinstance(content, list):
        return tuple(
            str(block.get("id", "")).strip()
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "tool_use"
            and str(block.get("id", "")).strip()
        )
    return ()


def tool_result_call_id(message: BaseMessage) -> str | None:
    if isinstance(message, ToolMessage):
        tool_call_id = getattr(message, "tool_call_id", None)
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            return tool_call_id.strip()
    return None


def normalize_fork_source_messages(
    source_messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    paired_tool_result_ids = {
        tool_call_id
        for message in source_messages
        if (tool_call_id := tool_result_call_id(message)) is not None
    }
    normalized: list[BaseMessage] = []
    for message in source_messages:
        tool_call_ids = message_tool_call_ids(message)
        if tool_call_ids and any(
            tool_call_id not in paired_tool_result_ids
            for tool_call_id in tool_call_ids
        ):
            continue
        normalized.append(message)
    return normalized


def message_contains_marker(message: BaseMessage, marker: str) -> bool:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return marker in content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and marker in text:
                    return True
    return False


def fork_recursion_guard(
    *,
    runtime: ToolRuntime,
    source_messages: Sequence[BaseMessage],
) -> str | None:
    context = getattr(runtime, "context", None)
    if isinstance(context, RuntimeContext) and context.entrypoint == "run_fork":
        return "Fork blocked: fork children cannot spawn nested forks."
    if any(
        message_contains_marker(message, FORK_RECURSION_GUARD_MARKER)
        for message in source_messages
    ):
        return "Fork blocked: recursion guard marker already exists in the active message prefix."
    return None


def fork_payload_messages(
    *,
    source_messages: Sequence[BaseMessage],
    intent: str,
) -> list[BaseMessage]:
    normalized_messages = normalize_fork_source_messages(source_messages)
    return [*normalized_messages, HumanMessage(content=fork_directive(intent))]
