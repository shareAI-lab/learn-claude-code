#!/usr/bin/env python3
# Deep Agents track: context compression -- keep canonical history, shrink model-facing context.
"""
s06_context_compact.py - cc-haha-inspired context compression with LangChain concepts.

This chapter teaches a six-stage pipeline modeled on the public Claude Code /
cc-haha compression flow:

1. apply_tool_result_budget
2. snip_projection
3. microcompact_messages
4. context_collapse
5. auto_compact_if_needed
6. reactive_compact_on_overflow

The implementation is intentionally tutorial-sized. It preserves canonical
history in explicit state, produces a smaller model-facing projection, and uses
injected deterministic summarizers for tests instead of live API calls.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ConfigDict, Field

try:
    from .common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        invoke_and_append,
        read_file,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        invoke_and_append,
        read_file,
        write_file,
    )

MessageRole = Literal["system", "user", "assistant", "tool"]
Summarizer = Callable[[Sequence["ContextMessage"]], str]

PIPELINE_STAGE_ORDER = (
    "apply_tool_result_budget",
    "snip_projection",
    "microcompact_messages",
    "context_collapse",
    "auto_compact_if_needed",
    "reactive_compact_on_overflow",
)
SOURCE_BACKED_STAGES = (
    "apply_tool_result_budget",
    "microcompact_messages",
    "auto_compact_if_needed",
    "reactive_compact_on_overflow",
)
INFERRED_STAGES = (
    "snip_projection",
    "context_collapse",
)
INTENTIONAL_SIMPLIFICATIONS = (
    "Character counts stand in for exact tokenizer budgets.",
    "Persisted tool outputs are stored as plain text files instead of provider cache edits.",
    "Snip projection and context collapse are honest teaching equivalents because the public cc-haha tree does not expose those internals in full.",
    "Auto compact omits session-memory extraction, telemetry, and prompt-cache-sharing details.",
)

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Keep canonical history intact, but keep the model-facing context lean.
If tool output grows too large, remember the teaching pipeline:
persist oversized results, snip the projection, microcompact stale tool
results, collapse old rounds, compact when thresholds are exceeded, and recover
reactively if an overflow still happens.
Use the compact tool when you need a manual reset point."""

DEFAULT_TOOL_RESULT_THRESHOLD = 2_000
DEFAULT_PER_MESSAGE_TOOL_BUDGET = 3_200
DEFAULT_PREVIEW_CHARS = 240
DEFAULT_SNIP_KEEP_LAST = 6
DEFAULT_MICROCOMPACT_KEEP_RECENT = 2
DEFAULT_CONTEXT_COLLAPSE_THRESHOLD = 2_800
DEFAULT_CONTEXT_COLLAPSE_KEEP_RECENT_GROUPS = 1
DEFAULT_AUTO_COMPACT_THRESHOLD = 1_900
DEFAULT_AUTO_COMPACT_KEEP_RECENT = 4
DEFAULT_SUMMARY_BUDGET = 600
DEFAULT_REACTIVE_DRAIN_BUDGET = 220
PERSISTED_OUTPUT_DIR = WORKDIR / ".task_outputs" / "tool-results"
COMPACTABLE_TOOLS = {
    "bash",
    "read_file",
    "grep",
    "glob",
    "search",
    "write_file",
    "edit_file",
}
MICROCOMPACT_PLACEHOLDER = (
    "[microcompacted tool result; rerun the tool if you need full detail.]"
)


@dataclass
class ContextMessage:
    id: str
    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersistedOutput:
    tool_call_id: str
    path: str
    preview: str
    original_size: int


@dataclass
class CompactBoundary:
    kind: str
    reason: str
    source_message_ids: tuple[str, ...] = ()
    size_saved: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollapsePlan:
    summary_message: ContextMessage
    source_message_ids: tuple[str, ...]
    recent_message_ids: tuple[str, ...]


@dataclass
class ContextCompressionState:
    messages: list[ContextMessage]
    model_messages: list[ContextMessage] | None = None
    persisted_outputs: dict[str, PersistedOutput] = field(default_factory=dict)
    replacement_decisions: dict[str, str] = field(default_factory=dict)
    compact_boundaries: list[CompactBoundary] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    staged_collapse: CollapsePlan | None = None

    def __post_init__(self) -> None:
        if self.model_messages is None:
            self.model_messages = deepcopy(self.messages)


class PromptTooLongError(RuntimeError):
    """Synthetic overflow sentinel for deterministic tests and demos."""


class CompactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus: str | None = Field(
        default=None,
        description=(
            "Optional short note about what the next compact summary must keep"
        ),
    )


def clone_state(state: ContextCompressionState) -> ContextCompressionState:
    return deepcopy(state)


def estimate_context_size(messages: Sequence[ContextMessage]) -> int:
    return sum(len(message.role) + len(message.content) for message in messages)


def tool_name(message: ContextMessage) -> str:
    if message.name:
        return message.name
    metadata_name = str(message.metadata.get("tool_name") or "").strip()
    return metadata_name or "tool"


def is_tool_result_message(message: ContextMessage) -> bool:
    return message.role == "tool" and bool(message.tool_call_id or message.name)


def is_persisted_marker(content: str) -> bool:
    return content.startswith("<persisted-output>")


def trim_text(text: str, limit: int) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: max(0, limit - 17)].rstrip() + "... [truncated]"


def relative_display_path(path: Path) -> str:
    try:
        return str(path.relative_to(WORKDIR))
    except ValueError:
        return str(path)


def persisted_output_marker(persisted: PersistedOutput) -> str:
    return (
        "<persisted-output>\n"
        f"tool_call_id: {persisted.tool_call_id}\n"
        f"path: {persisted.path}\n"
        "preview:\n"
        f"{persisted.preview}\n"
        "</persisted-output>"
    )


def deterministic_summarizer(messages: Sequence[ContextMessage]) -> str:
    if not messages:
        return "No earlier context to preserve."

    lines: list[str] = []
    for message in messages[:6]:
        label = message.role
        if is_tool_result_message(message):
            label = f"tool:{tool_name(message)}"
        preview = trim_text(message.content.replace("\n", " "), 80)
        lines.append(f"- {label}: {preview}")

    if len(messages) > 6:
        lines.append(f"- ... {len(messages) - 6} more messages elided")
    return "Compressed carry-forward summary:\n" + "\n".join(lines)


def normalize_history(messages: Sequence[dict[str, Any] | ContextMessage]) -> list[ContextMessage]:
    normalized: list[ContextMessage] = []
    for index, raw in enumerate(messages, start=1):
        if isinstance(raw, ContextMessage):
            normalized.append(deepcopy(raw))
            continue

        content = raw.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                str(block.get("text") or block.get("content") or "")
                for block in content
                if isinstance(block, dict)
            ).strip()
        normalized.append(
            ContextMessage(
                id=str(raw.get("id") or f"m{index}"),
                role=raw.get("role", "user"),
                content=str(content),
                name=raw.get("name"),
                tool_call_id=raw.get("tool_call_id"),
                metadata={
                    key: value
                    for key, value in raw.items()
                    if key
                    not in {"id", "role", "content", "name", "tool_call_id"}
                },
            )
        )
    return normalized


def state_from_history(
    messages: Sequence[dict[str, Any] | ContextMessage],
) -> ContextCompressionState:
    return ContextCompressionState(messages=normalize_history(messages))


def _persist_tool_result(
    state: ContextCompressionState,
    message: ContextMessage,
    *,
    storage_dir: Path,
    preview_chars: int,
) -> tuple[PersistedOutput, int]:
    tool_call_id = message.tool_call_id or message.id
    persisted = state.persisted_outputs.get(tool_call_id)
    if persisted is None:
        storage_dir.mkdir(parents=True, exist_ok=True)
        output_path = storage_dir / f"{tool_call_id}.txt"
        if not output_path.exists():
            output_path.write_text(message.content, encoding="utf-8")
        persisted = PersistedOutput(
            tool_call_id=tool_call_id,
            path=relative_display_path(output_path),
            preview=trim_text(message.content, preview_chars),
            original_size=len(message.content),
        )
        state.persisted_outputs[tool_call_id] = persisted

    replacement = persisted_output_marker(persisted)
    size_saved = max(0, len(message.content) - len(replacement))
    message.content = replacement
    state.replacement_decisions[tool_call_id] = persisted.path
    return persisted, size_saved


def _tool_message_groups(
    messages: Sequence[ContextMessage],
) -> dict[str, list[ContextMessage]]:
    groups: dict[str, list[ContextMessage]] = {}
    for index, message in enumerate(messages):
        if not is_tool_result_message(message):
            continue
        group_id = (
            str(message.metadata.get("group_id") or "").strip()
            or str(message.metadata.get("round_id") or "").strip()
            or f"tool-group-{index}"
        )
        groups.setdefault(group_id, []).append(message)
    return groups


def _record_boundary(
    state: ContextCompressionState,
    *,
    kind: str,
    reason: str,
    source_messages: Sequence[ContextMessage],
    size_saved: int,
    details: dict[str, Any] | None = None,
) -> None:
    state.compact_boundaries.append(
        CompactBoundary(
            kind=kind,
            reason=reason,
            source_message_ids=tuple(message.id for message in source_messages),
            size_saved=size_saved,
            details=details or {},
        )
    )


def apply_tool_result_budget(
    state: ContextCompressionState,
    *,
    storage_dir: Path = PERSISTED_OUTPUT_DIR,
    per_tool_threshold: int = DEFAULT_TOOL_RESULT_THRESHOLD,
    per_message_budget: int = DEFAULT_PER_MESSAGE_TOOL_BUDGET,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> ContextCompressionState:
    next_state = clone_state(state)
    next_state.transitions.append("apply_tool_result_budget")

    replaced_messages: list[ContextMessage] = []
    total_saved = 0

    for message in next_state.model_messages:
        if not is_tool_result_message(message):
            continue
        tool_call_id = message.tool_call_id or message.id
        if tool_call_id in next_state.replacement_decisions:
            _, saved = _persist_tool_result(
                next_state,
                message,
                storage_dir=storage_dir,
                preview_chars=preview_chars,
            )
            replaced_messages.append(message)
            total_saved += saved
            continue
        if len(message.content) > per_tool_threshold:
            _, saved = _persist_tool_result(
                next_state,
                message,
                storage_dir=storage_dir,
                preview_chars=preview_chars,
            )
            replaced_messages.append(message)
            total_saved += saved

    for group_id, tool_messages in _tool_message_groups(next_state.model_messages).items():
        remaining_budget = sum(len(message.content) for message in tool_messages)
        fresh_messages = [
            message
            for message in tool_messages
            if (message.tool_call_id or message.id)
            not in next_state.replacement_decisions
        ]
        while remaining_budget > per_message_budget and fresh_messages:
            candidate = max(fresh_messages, key=lambda message: len(message.content))
            _, saved = _persist_tool_result(
                next_state,
                candidate,
                storage_dir=storage_dir,
                preview_chars=preview_chars,
            )
            replaced_messages.append(candidate)
            total_saved += saved
            remaining_budget = sum(len(message.content) for message in tool_messages)
            fresh_messages = [
                message
                for message in tool_messages
                if (message.tool_call_id or message.id)
                not in next_state.replacement_decisions
            ]
        if group_id and tool_messages:
            tool_messages[-1].metadata["budget_group"] = group_id

    if replaced_messages:
        _record_boundary(
            next_state,
            kind="tool_result_budget",
            reason=(
                "Persist oversized tool outputs and freeze replacement decisions "
                "by tool_call_id."
            ),
            source_messages=replaced_messages,
            size_saved=total_saved,
            details={
                "replacement_decisions": dict(next_state.replacement_decisions),
            },
        )
    return next_state


def snip_projection(
    state: ContextCompressionState,
    *,
    keep_last: int = DEFAULT_SNIP_KEEP_LAST,
) -> ContextCompressionState:
    next_state = clone_state(state)
    next_state.transitions.append("snip_projection")

    if len(next_state.model_messages) <= keep_last:
        return next_state

    omitted = next_state.model_messages[:-keep_last]
    kept = next_state.model_messages[-keep_last:]
    snip_message = ContextMessage(
        id=f"snip-{len(next_state.compact_boundaries) + 1}",
        role="system",
        content=(
            f"[snip] {len(omitted)} older messages hidden from the active "
            "projection; canonical history still lives in state.messages."
        ),
        metadata={"stage": "snip"},
    )
    next_state.model_messages = [snip_message, *kept]
    _record_boundary(
        next_state,
        kind="snip",
        reason="Projection-only trim of older context.",
        source_messages=omitted,
        size_saved=max(0, estimate_context_size(omitted) - len(snip_message.content)),
        details={"kept_recent": keep_last},
    )
    return next_state


def microcompact_messages(
    state: ContextCompressionState,
    *,
    keep_recent: int = DEFAULT_MICROCOMPACT_KEEP_RECENT,
    compactable_tools: set[str] | None = None,
) -> ContextCompressionState:
    next_state = clone_state(state)
    next_state.transitions.append("microcompact_messages")

    compactable_tools = compactable_tools or COMPACTABLE_TOOLS
    compactable = [
        message
        for message in next_state.model_messages
        if is_tool_result_message(message) and tool_name(message) in compactable_tools
    ]
    if len(compactable) <= keep_recent:
        return next_state

    cleared_messages = compactable[:-keep_recent]
    size_saved = 0
    cleared_ids: list[str] = []
    for message in cleared_messages:
        if is_persisted_marker(message.content) or message.content == MICROCOMPACT_PLACEHOLDER:
            continue
        size_saved += max(0, len(message.content) - len(MICROCOMPACT_PLACEHOLDER))
        message.content = MICROCOMPACT_PLACEHOLDER
        cleared_ids.append(message.tool_call_id or message.id)

    if cleared_ids:
        _record_boundary(
            next_state,
            kind="microcompact",
            reason="Clear older compactable tool results while keeping recent ones intact.",
            source_messages=cleared_messages,
            size_saved=size_saved,
            details={"cleared_tool_call_ids": cleared_ids, "kept_recent": keep_recent},
        )
    return next_state


def group_api_rounds(
    messages: Sequence[ContextMessage],
) -> list[list[ContextMessage]]:
    groups: list[list[ContextMessage]] = []
    current_group: list[ContextMessage] = []
    for message in messages:
        if message.role == "user" and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append(message)
    if current_group:
        groups.append(current_group)
    return groups


def context_collapse(
    state: ContextCompressionState,
    summarizer: Summarizer = deterministic_summarizer,
    *,
    collapse_threshold: int = DEFAULT_CONTEXT_COLLAPSE_THRESHOLD,
    keep_recent_groups: int = DEFAULT_CONTEXT_COLLAPSE_KEEP_RECENT_GROUPS,
) -> ContextCompressionState:
    next_state = clone_state(state)
    next_state.transitions.append("context_collapse")

    if estimate_context_size(next_state.model_messages) <= collapse_threshold:
        return next_state

    groups = group_api_rounds(next_state.model_messages)
    if len(groups) <= keep_recent_groups:
        return next_state

    collapsed_groups = groups[:-keep_recent_groups]
    recent_groups = groups[-keep_recent_groups:]
    collapsed_messages = [message for group in collapsed_groups for message in group]
    recent_messages = [message for group in recent_groups for message in group]
    summary = summarizer(collapsed_messages).strip() or "Earlier context summarized."
    summary_message = ContextMessage(
        id=f"context-collapse-{len(next_state.summaries) + 1}",
        role="system",
        content=f"[context-collapse]\n{summary}",
        metadata={"stage": "context_collapse", "inferred": True},
    )
    next_state.model_messages = [summary_message, *recent_messages]
    next_state.summaries.append(summary)
    next_state.staged_collapse = CollapsePlan(
        summary_message=deepcopy(summary_message),
        source_message_ids=tuple(message.id for message in collapsed_messages),
        recent_message_ids=tuple(message.id for message in recent_messages),
    )
    _record_boundary(
        next_state,
        kind="context_collapse",
        reason="Summarize older API-round groups while keeping recent groups verbatim.",
        source_messages=collapsed_messages,
        size_saved=max(
            0,
            estimate_context_size(collapsed_messages) - len(summary_message.content),
        ),
        details={"keep_recent_groups": keep_recent_groups},
    )
    return next_state


def _build_summary_message(
    *,
    stage: str,
    summary: str,
    index: int,
) -> ContextMessage:
    return ContextMessage(
        id=f"{stage}-{index}",
        role="system",
        content=f"[{stage}]\n{summary}",
        metadata={"stage": stage},
    )


def auto_compact_if_needed(
    state: ContextCompressionState,
    summarizer: Summarizer = deterministic_summarizer,
    *,
    threshold: int = DEFAULT_AUTO_COMPACT_THRESHOLD,
    keep_recent: int = DEFAULT_AUTO_COMPACT_KEEP_RECENT,
    summary_budget: int = DEFAULT_SUMMARY_BUDGET,
    focus: str | None = None,
    force: bool = False,
    boundary_kind: str = "auto_compact",
    transition_name: str | None = "auto_compact",
) -> ContextCompressionState:
    next_state = clone_state(state)
    if transition_name:
        next_state.transitions.append(transition_name)

    if not force and estimate_context_size(next_state.model_messages) <= threshold:
        return next_state

    if keep_recent and len(next_state.model_messages) > keep_recent:
        summary_source = next_state.model_messages[:-keep_recent]
        recent_messages = next_state.model_messages[-keep_recent:]
    else:
        summary_source = list(next_state.model_messages)
        recent_messages = []

    summary = summarizer(summary_source).strip() or "Conversation compacted."
    if focus:
        summary = f"{summary}\nFocus next: {focus.strip()}"
    summary = trim_text(summary, summary_budget)
    summary_message = _build_summary_message(
        stage=boundary_kind.replace("_", "-"),
        summary=summary,
        index=len(next_state.summaries) + 1,
    )
    next_state.model_messages = [summary_message, *recent_messages]
    next_state.summaries.append(summary)
    next_state.staged_collapse = None
    _record_boundary(
        next_state,
        kind=boundary_kind,
        reason="Reset active context to a summary plus recent messages.",
        source_messages=summary_source,
        size_saved=max(
            0,
            estimate_context_size(summary_source) - len(summary_message.content),
        ),
        details={"keep_recent": keep_recent},
    )
    return next_state


def compact_conversation(
    state: ContextCompressionState,
    summarizer: Summarizer = deterministic_summarizer,
    *,
    focus: str | None = None,
    keep_recent: int = DEFAULT_AUTO_COMPACT_KEEP_RECENT,
) -> ContextCompressionState:
    return auto_compact_if_needed(
        state,
        summarizer,
        threshold=0,
        keep_recent=keep_recent,
        focus=focus,
        force=True,
    )


manual_compact = compact_conversation


def reactive_compact_on_overflow(
    state: ContextCompressionState,
    error: Exception | str | None,
    summarizer: Summarizer = deterministic_summarizer,
    *,
    threshold: int = DEFAULT_AUTO_COMPACT_THRESHOLD,
    keep_recent: int = DEFAULT_AUTO_COMPACT_KEEP_RECENT,
    drain_summary_budget: int = DEFAULT_REACTIVE_DRAIN_BUDGET,
) -> ContextCompressionState:
    next_state = clone_state(state)
    next_state.transitions.append("collapse_drain_retry")

    if next_state.staged_collapse is not None:
        drained_summary = trim_text(
            next_state.staged_collapse.summary_message.content,
            drain_summary_budget,
        )
        recent_ids = set(next_state.staged_collapse.recent_message_ids)
        recent_messages = [
            message
            for message in next_state.model_messages
            if message.id in recent_ids
        ]
        next_state.model_messages = [
            ContextMessage(
                id=f"collapse-drain-{len(next_state.summaries) + 1}",
                role="system",
                content=drained_summary,
                metadata={"stage": "collapse_drain_retry"},
            ),
            *recent_messages,
        ]

    if estimate_context_size(next_state.model_messages) <= threshold:
        return next_state

    next_state.transitions.append("reactive_compact_retry")
    focus = None
    if error:
        focus = f"Recover after overflow: {error}"
    return auto_compact_if_needed(
        next_state,
        summarizer,
        threshold=threshold,
        keep_recent=keep_recent,
        focus=focus,
        force=True,
        boundary_kind="reactive_compact",
        transition_name=None,
    )


def run_compression_pipeline(
    state: ContextCompressionState,
    summarizer: Summarizer = deterministic_summarizer,
    *,
    storage_dir: Path = PERSISTED_OUTPUT_DIR,
    per_tool_threshold: int = DEFAULT_TOOL_RESULT_THRESHOLD,
    per_message_budget: int = DEFAULT_PER_MESSAGE_TOOL_BUDGET,
    snip_keep_last: int = DEFAULT_SNIP_KEEP_LAST,
    micro_keep_recent: int = DEFAULT_MICROCOMPACT_KEEP_RECENT,
    collapse_threshold: int = DEFAULT_CONTEXT_COLLAPSE_THRESHOLD,
    collapse_keep_recent_groups: int = DEFAULT_CONTEXT_COLLAPSE_KEEP_RECENT_GROUPS,
    auto_threshold: int = DEFAULT_AUTO_COMPACT_THRESHOLD,
    auto_keep_recent: int = DEFAULT_AUTO_COMPACT_KEEP_RECENT,
) -> ContextCompressionState:
    compacted = apply_tool_result_budget(
        state,
        storage_dir=storage_dir,
        per_tool_threshold=per_tool_threshold,
        per_message_budget=per_message_budget,
    )
    compacted = snip_projection(compacted, keep_last=snip_keep_last)
    compacted = microcompact_messages(compacted, keep_recent=micro_keep_recent)
    compacted = context_collapse(
        compacted,
        summarizer,
        collapse_threshold=collapse_threshold,
        keep_recent_groups=collapse_keep_recent_groups,
    )
    return auto_compact_if_needed(
        compacted,
        summarizer,
        threshold=auto_threshold,
        keep_recent=auto_keep_recent,
    )


@tool(
    "compact",
    args_schema=CompactInput,
    description=(
        "Manual teaching wrapper for conversation compaction. Use it when the "
        "thread is bloated and you want a short carry-forward summary of goals, "
        "decisions, files, and next steps before continuing."
    ),
)
def compact(focus: str | None = None) -> str:
    """Expose the stage's manual compact capability to the model."""

    summary = (
        "Manual compaction in this chapter means carrying forward the current "
        "goal, important decisions, touched files, and next steps while "
        "dropping bulky detail from the active context."
    )
    if focus:
        return f"{summary}\nFocus next: {focus.strip()}"
    return summary


TOOLS = [bash, read_file, write_file, edit_file, compact]


def build_agent(*, model: BaseChatModel | None = None):
    """Create the s06 demo agent without requiring credentials on import."""

    return create_agent(
        model=model or build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    return invoke_and_append(build_agent(), messages)


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms06-da >> \033[0m")
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
        print(final)
        print()
