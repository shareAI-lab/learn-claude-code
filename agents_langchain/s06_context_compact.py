#!/usr/bin/env python3
# LangChain track: compression -- keep the active context small enough to work.
"""
s06_context_compact.py - Context Compact with LangChain

LangChain can provide middleware for memory and summarization, but this chapter
keeps compaction visible as harness code around the agent invocation: persist
large tool outputs, micro-compact old results, and replace long history with a
summary when needed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from . import common
    from .common import (
        WORKDIR,
        build_openai_model,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        latest_assistant_text,
        read_file as common_read_file,
        write_file,
    )
except ImportError:
    import common
    from common import (
        WORKDIR,
        build_openai_model,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        latest_assistant_text,
        read_file as common_read_file,
        write_file,
    )

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Keep working step by step, and use compact if the conversation gets too long."
)
CONTEXT_LIMIT = 50_000
KEEP_RECENT_TOOL_RESULTS = 3
PERSIST_THRESHOLD = 30_000
PREVIEW_CHARS = 2_000
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"


@dataclass
class CompactState:
    has_compacted: bool = False
    last_summary: str = ""
    recent_files: list[str] = field(default_factory=list)
    compact_requested: bool = False
    compact_focus: str | None = None


COMPACT_STATE = CompactState()


def estimate_context_size(messages: list[dict[str, Any]]) -> int:
    return len(str(messages))


def track_recent_file(state: CompactState, path: str) -> None:
    if path in state.recent_files:
        state.recent_files.remove(path)
    state.recent_files.append(path)
    if len(state.recent_files) > 5:
        state.recent_files[:] = state.recent_files[-5:]


def persist_large_output(tool_name: str, output: str) -> str:
    if len(output) <= PERSIST_THRESHOLD:
        return output

    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = TOOL_RESULTS_DIR / f"{tool_name}-{int(time.time() * 1000)}.txt"
    stored_path.write_text(output, encoding="utf-8")

    preview = output[:PREVIEW_CHARS]
    rel_path = stored_path.relative_to(WORKDIR)
    return (
        "<persisted-output>\n"
        f"Full output saved to: {rel_path}\n"
        "Preview:\n"
        f"{preview}\n"
        "</persisted-output>"
    )


def bash(command: str) -> str:
    """Run a shell command, persisting very large output outside active context."""

    return persist_large_output("bash", common.bash(command))


def read_file(path: str, limit: int | None = None) -> str:
    """Read a file, remembering it as a recent file for compaction recovery."""

    track_recent_file(COMPACT_STATE, path)
    return persist_large_output("read_file", common_read_file(path, limit))


def compact(focus: str = "") -> str:
    """Request a conversation compaction after this agent turn."""

    COMPACT_STATE.compact_requested = True
    COMPACT_STATE.compact_focus = focus or None
    return "Compaction requested. The harness will summarize history after this turn."


def collect_tool_result_blocks(messages: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    blocks: list[tuple[int, dict[str, Any]]] = []
    for index, message in enumerate(messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                blocks.append((index, block))
    return blocks


def micro_compact(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tool_results = collect_tool_result_blocks(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS:
        return messages

    for _, block in tool_results[:-KEEP_RECENT_TOOL_RESULTS]:
        content = block.get("content", "")
        if isinstance(content, str) and len(content) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run the tool if you need full detail.]"
    return messages


def write_transcript(messages: list[dict[str, Any]]) -> Path:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(message, default=str, ensure_ascii=False) + "\n")
    return path


def summarize_history(messages: list[dict[str, Any]]) -> str:
    conversation = json.dumps(messages, default=str, ensure_ascii=False)[:80_000]
    prompt = (
        "Summarize this coding-agent conversation so work can continue.\n"
        "Preserve:\n"
        "1. The current goal\n"
        "2. Important findings and decisions\n"
        "3. Files read or changed\n"
        "4. Remaining work\n"
        "5. User constraints and preferences\n"
        "Be compact but concrete.\n\n"
        f"{conversation}"
    )
    response = build_openai_model().invoke(prompt)
    return latest_assistant_text(response).strip() or extract_text(getattr(response, "content", ""))


def compact_history(messages: list[dict[str, Any]], state: CompactState, focus: str | None = None) -> list[dict[str, Any]]:
    transcript_path = write_transcript(messages)
    summary = summarize_history(messages)
    if focus:
        summary += f"\n\nFocus to preserve next: {focus}"
    if state.recent_files:
        recent_lines = "\n".join(f"- {path}" for path in state.recent_files)
        summary += f"\n\nRecent files to reopen if needed:\n{recent_lines}"

    state.has_compacted = True
    state.last_summary = summary
    return [{
        "role": "user",
        "content": (
            "This conversation was compacted so the agent can continue working.\n"
            f"Transcript saved to: {transcript_path.relative_to(WORKDIR)}\n\n"
            f"{summary}"
        ),
    }]


TOOLS = [bash, read_file, write_file, edit_file, compact]


def build_agent():
    return create_agent_runtime(SYSTEM, TOOLS)


def agent_loop(messages: list[dict[str, Any]], state: CompactState) -> str:
    messages[:] = micro_compact(messages)
    if estimate_context_size(messages) > CONTEXT_LIMIT:
        messages[:] = compact_history(messages, state)

    final_text = invoke_and_append(build_agent(), messages)
    if state.compact_requested:
        messages[:] = compact_history(messages, state, focus=state.compact_focus)
        state.compact_requested = False
        state.compact_focus = None
    return final_text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    compact_state = COMPACT_STATE
    while True:
        try:
            query = input("\033[36ms06-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        try:
            final = agent_loop(history, compact_state)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        print()
