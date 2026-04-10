#!/usr/bin/env python3
# LangChain track: compression -- compaction remains harness code around the framework runtime.
"""
s06_context_compact.py - Context Compact with LangChain

LangChain owns the agent graph and tool loop.  The harness still owns context
budget policy: persist large tool outputs, micro-compact older tool messages,
and summarize history when the active conversation gets too large.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

try:
    from agents_langchain._common import (
        OUTPUT_LIMIT,
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        message_text,
        read_file as read_file_impl,
        run_bash as run_bash_impl,
        write_file as write_file_impl,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from _common import (
        OUTPUT_LIMIT,
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        message_text,
        read_file as read_file_impl,
        run_bash as run_bash_impl,
        write_file as write_file_impl,
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
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results-langchain"


@dataclass
class CompactState:
    has_compacted: bool = False
    last_summary: str = ""
    recent_files: list[str] = field(default_factory=list)
    pending_manual_compact: bool = False
    pending_focus: str | None = None


def estimate_context_size(messages: list[Any]) -> int:
    return len(str(messages))


def track_recent_file(state: CompactState, path: str) -> None:
    if path in state.recent_files:
        state.recent_files.remove(path)
    state.recent_files.append(path)
    if len(state.recent_files) > 5:
        state.recent_files[:] = state.recent_files[-5:]


def persist_large_output(label: str, output: str) -> str:
    if len(output) <= PERSIST_THRESHOLD:
        return output[:OUTPUT_LIMIT]

    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = TOOL_RESULTS_DIR / f"{int(time.time() * 1000)}-{label}.txt"
    stored_path.write_text(output)

    rel_path = stored_path.relative_to(WORKDIR)
    return (
        "<persisted-output>\n"
        f"Full output saved to: {rel_path}\n"
        "Preview:\n"
        f"{output[:PREVIEW_CHARS]}\n"
        "</persisted-output>"
    )


def micro_compact(messages: list[Any]) -> list[Any]:
    """Replace older verbose ToolMessages with short placeholders."""

    tool_messages = [msg for msg in messages if getattr(msg, "type", None) == "tool"]
    if len(tool_messages) <= KEEP_RECENT_TOOL_RESULTS:
        return messages

    old_tool_ids = {id(msg) for msg in tool_messages[:-KEEP_RECENT_TOOL_RESULTS]}
    compacted: list[Any] = []
    for msg in messages:
        if id(msg) in old_tool_ids and len(message_text(msg)) > 120:
            msg.content = "[Earlier tool result compacted. Re-run the tool if you need full detail.]"
        compacted.append(msg)
    return compacted


def write_transcript(messages: list[Any]) -> Path:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPT_DIR / f"langchain_transcript_{int(time.time())}.jsonl"
    with path.open("w") as handle:
        for message in messages:
            handle.write(json.dumps(str(message), ensure_ascii=False) + "\n")
    return path


def summarize_history(messages: list[Any]) -> str:
    conversation = "\n".join(str(message) for message in messages)[:80_000]
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
    response = build_openai_chat_model().invoke(prompt)
    return message_text(response).strip()


def compact_history(messages: list[Any], state: CompactState, focus: str | None = None) -> list[dict[str, str]]:
    transcript_path = write_transcript(messages)
    print(f"[transcript saved: {transcript_path}]")

    summary = summarize_history(messages)
    if focus:
        summary += f"\n\nFocus to preserve next: {focus}"
    if state.recent_files:
        recent_lines = "\n".join(f"- {path}" for path in state.recent_files)
        summary += f"\n\nRecent files to reopen if needed:\n{recent_lines}"

    state.has_compacted = True
    state.last_summary = summary
    state.pending_manual_compact = False
    state.pending_focus = None

    return [{
        "role": "user",
        "content": "This conversation was compacted so the agent can continue working.\n\n" + summary,
    }]


def build_tools(state: CompactState):
    @tool
    def bash(command: str) -> str:
        """Run a shell command in the current workspace."""

        return persist_large_output("bash", run_bash_impl(command))

    @tool
    def read_file(path: str, limit: int | None = None) -> str:
        """Read file contents and remember the file as recently relevant."""

        track_recent_file(state, path)
        return persist_large_output("read_file", read_file_impl(path, limit))

    @tool
    def write_file(path: str, content: str) -> str:
        """Write content to a workspace file."""

        track_recent_file(state, path)
        return write_file_impl(path, content)

    @tool
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact text occurrence in a workspace file."""

        track_recent_file(state, path)
        return edit_file_impl(path, old_text, new_text)

    @tool
    def compact(focus: str = "") -> str:
        """Request a history compaction after the current LangChain agent turn."""

        state.pending_manual_compact = True
        state.pending_focus = focus or None
        return "Compaction requested; the harness will summarize history after this turn."

    return [bash, read_file, write_file, edit_file, compact]


def invoke_agent(messages: list[Any], state: CompactState, query: str) -> list[Any]:
    messages = micro_compact(messages)
    if estimate_context_size(messages) > CONTEXT_LIMIT:
        print("[auto compact]")
        messages = compact_history(messages, state)

    agent = create_agent(build_openai_chat_model(), tools=build_tools(state), system_prompt=SYSTEM)
    result = agent.invoke({"messages": [*messages, {"role": "user", "content": query}]})
    updated = list(result["messages"])

    if state.pending_manual_compact:
        print("[manual compact]")
        updated = compact_history(updated, state, focus=state.pending_focus)
    return updated


if __name__ == "__main__":
    history: list[Any] = []
    compact_state = CompactState()
    while True:
        try:
            query = input("\033[36mlc-s06 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history = invoke_agent(history, compact_state, query)
        print(latest_text(history))
        print()
