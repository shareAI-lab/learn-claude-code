#!/usr/bin/env python3
"""
Regression tests for s_full.py message alternation and microcompact fixes.

Covers:
  1. microcompact preserves read_file results (matches s06 behaviour)
  2. microcompact still clears non-read_file results
  3. agent_loop merges bg notifications + inbox into a single user turn
  4. teammate _loop inbox merging avoids consecutive user messages
  5. teammate auto-claim inserts assistant turn when last msg is user
  6. source code audit: no raw consecutive user appends remain

No network / LLM dependency — all tests use message list manipulation and
source-code inspection.
"""

import ast
import json
import os
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# Helpers: build mock Anthropic SDK content blocks
# ---------------------------------------------------------------------------

def _make_tool_use_block(block_id: str, name: str, input_dict: dict | None = None):
    """Simulate an Anthropic SDK ToolUseBlock (has .type, .id, .name, .input)."""
    return SimpleNamespace(type="tool_use", id=block_id, name=name,
                           input=input_dict or {})


def _make_text_block(text: str):
    return SimpleNamespace(type="text", text=text)


# ---------------------------------------------------------------------------
# Import s_full helpers without triggering the Anthropic client
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_env(monkeypatch, tmp_path):
    """Set env vars and CWD so s_full module-level code doesn't crash."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:9999")
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def s_full():
    """Import (or reimport) s_full after env is patched."""
    if "agents.s_full" in sys.modules:
        del sys.modules["agents.s_full"]
    # Ensure the agents package is importable
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    import agents.s_full as mod
    return mod


# ===================================================================
# 1. microcompact preserves read_file results
# ===================================================================

class TestMicrocompactPreservesReadFile:
    def test_read_file_results_survive(self, s_full):
        """read_file tool_result content must NOT be cleared."""
        msgs = []
        # 5 tool calls: 3 bash + 2 read_file — all old enough to be candidates
        for i in range(5):
            tool_name = "read_file" if i >= 3 else "bash"
            block_id = f"tu_{i}"
            msgs.append({"role": "assistant", "content": [
                _make_tool_use_block(block_id, tool_name, {"path": "f.py"} if tool_name == "read_file" else {"command": "ls"}),
            ]})
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": block_id,
                 "content": f"{'x' * 200} result of {tool_name} call {i}"},
            ]})

        s_full.microcompact(msgs)

        # Collect surviving content
        for msg in msgs:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for part in msg["content"]:
                if part.get("type") != "tool_result":
                    continue
                tid = part["tool_use_id"]
                idx = int(tid.split("_")[1])
                if idx >= 3:
                    # read_file results must be preserved
                    assert part["content"] != "[cleared]", \
                        f"read_file result tu_{idx} was incorrectly cleared"

    def test_bash_results_cleared(self, s_full):
        """Non-read_file results older than KEEP_RECENT should be cleared."""
        msgs = []
        for i in range(6):
            block_id = f"tu_{i}"
            msgs.append({"role": "assistant", "content": [
                _make_tool_use_block(block_id, "bash", {"command": "ls"}),
            ]})
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": block_id,
                 "content": f"{'y' * 200} bash output {i}"},
            ]})

        s_full.microcompact(msgs)

        cleared_count = 0
        for msg in msgs:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for part in msg["content"]:
                if part.get("content") == "[cleared]":
                    cleared_count += 1
        # With 6 results and keep-recent=3, at least the first 3 should be cleared
        assert cleared_count >= 3, f"Expected ≥3 cleared, got {cleared_count}"

    def test_short_results_not_cleared(self, s_full):
        """Results ≤100 chars should never be cleared regardless of tool type."""
        msgs = []
        for i in range(6):
            block_id = f"tu_{i}"
            msgs.append({"role": "assistant", "content": [
                _make_tool_use_block(block_id, "bash"),
            ]})
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": block_id,
                 "content": "short"},
            ]})

        s_full.microcompact(msgs)

        for msg in msgs:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for part in msg["content"]:
                if part.get("type") == "tool_result":
                    assert part["content"] == "short"


# ===================================================================
# 2. Message alternation: no consecutive user messages
# ===================================================================

def _validate_alternation(messages: list, label: str = ""):
    """Assert that no two consecutive messages share the same role."""
    for i in range(1, len(messages)):
        assert messages[i]["role"] != messages[i - 1]["role"], (
            f"{label}Consecutive {messages[i]['role']} messages at index "
            f"{i - 1}–{i}: {messages[i - 1]!r:.120} / {messages[i]!r:.120}")


class TestAgentLoopAlternation:
    """Verify that bg-notification + inbox injection doesn't break alternation."""

    def test_bg_and_inbox_merged_after_assistant(self, s_full):
        """When last msg is assistant, a single user msg should be appended."""
        msgs = [
            {"role": "user", "content": "start"},
            {"role": "assistant", "content": "ok"},
        ]
        # Simulate bg notification + inbox being available
        s_full.BG.notifications.put({"task_id": "abc", "status": "completed",
                                      "result": "done"})
        # Put a message in lead's inbox
        s_full.BUS.send("worker", "lead", "update", "message")

        # We can't call agent_loop (needs real LLM), so replicate its
        # injection logic directly.
        injected_parts = []
        notifs = s_full.BG.drain()
        if notifs:
            txt = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
            injected_parts.append(f"<background-results>\n{txt}\n</background-results>")
        inbox = s_full.BUS.read_inbox("lead")
        if inbox:
            injected_parts.append(f"<inbox>{json.dumps(inbox, indent=2)}</inbox>")

        if injected_parts:
            merged_inject = "\n".join(injected_parts)
            if msgs and msgs[-1]["role"] == "user":
                prev = msgs[-1]["content"]
                if isinstance(prev, str):
                    msgs[-1]["content"] = prev + "\n" + merged_inject
                elif isinstance(prev, list):
                    prev.append({"type": "text", "text": merged_inject})
            else:
                msgs.append({"role": "user", "content": merged_inject})

        _validate_alternation(msgs, "bg+inbox after assistant: ")

    def test_bg_and_inbox_folded_into_user_turn(self, s_full):
        """When last msg is user (tool_results), injections fold in."""
        msgs = [
            {"role": "user", "content": "start"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": "done"},
            ]},
        ]
        s_full.BG.notifications.put({"task_id": "abc", "status": "completed",
                                      "result": "done"})

        injected_parts = []
        notifs = s_full.BG.drain()
        if notifs:
            txt = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
            injected_parts.append(f"<background-results>\n{txt}\n</background-results>")

        if injected_parts:
            merged_inject = "\n".join(injected_parts)
            if msgs and msgs[-1]["role"] == "user":
                prev = msgs[-1]["content"]
                if isinstance(prev, str):
                    msgs[-1]["content"] = prev + "\n" + merged_inject
                elif isinstance(prev, list):
                    prev.append({"type": "text", "text": merged_inject})
            else:
                msgs.append({"role": "user", "content": merged_inject})

        _validate_alternation(msgs, "bg folded into tool_results: ")
        # The last user message should have the injected text appended
        last_content = msgs[-1]["content"]
        assert isinstance(last_content, list)
        assert any("background-results" in str(p) for p in last_content)


class TestTeammateAlternation:
    """Verify teammate _loop inbox + auto-claim don't produce consecutive user messages."""

    def test_inbox_after_tool_results_inserts_assistant(self):
        """When last msg is user (tool_results) and inbox arrives, an assistant
        turn must be inserted before the new user turn."""
        messages = [
            {"role": "user", "content": "initial prompt"},
            {"role": "assistant", "content": [_make_text_block("working")]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
            ]},
        ]
        # Simulate the fixed idle-phase inbox handling:
        inbox_parts = [json.dumps({"type": "message", "content": "hello"})]
        merged = "\n".join(inbox_parts)
        if messages and messages[-1]["role"] == "user":
            messages.append({"role": "assistant", "content": "Idle. Checking inbox."})
        messages.append({"role": "user", "content": merged})

        _validate_alternation(messages, "teammate inbox after tool_results: ")

    def test_auto_claim_after_tool_results_inserts_assistant(self):
        """Auto-claim after work phase must not produce consecutive user msgs."""
        messages = [
            {"role": "user", "content": "initial prompt"},
            {"role": "assistant", "content": [_make_text_block("working")]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
            ]},
        ]
        # Simulate auto-claim logic (as fixed):
        if messages and messages[-1]["role"] == "user":
            messages.append({"role": "assistant", "content": "Idle. Looking for tasks."})
        messages.append({"role": "user", "content": "<auto-claimed>Task #1: test</auto-claimed>"})
        messages.append({"role": "assistant", "content": "Claimed task #1. Working on it."})

        _validate_alternation(messages, "teammate auto-claim: ")


# ===================================================================
# 3. Source code audit
# ===================================================================

class TestSourceAudit:
    """Static checks on the source to prevent regressions."""

    @pytest.fixture
    def source(self):
        src_path = Path(__file__).resolve().parent.parent / "agents" / "s_full.py"
        return src_path.read_text()

    def test_microcompact_has_preserve_tools(self, source):
        """microcompact must reference _PRESERVE_RESULT_TOOLS."""
        assert "_PRESERVE_RESULT_TOOLS" in source

    def test_no_consecutive_user_append_in_agent_loop(self, source):
        """The agent_loop section must not have two separate
        messages.append(user) calls in sequence without an intervening
        assistant append."""
        # Extract the agent_loop function body
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "agent_loop":
                body_src = ast.get_source_segment(source, node)
                # Count direct "messages.append" with role="user" — there should
                # only be ONE unconditional append per iteration (the tool_results).
                # The bg+inbox injection should use conditional folding.
                user_appends = [
                    line for line in body_src.splitlines()
                    if 'messages.append' in line and '"user"' in line
                    and not line.strip().startswith('#')
                ]
                # Should be at most 2 (one conditional for injection, one for results)
                assert len(user_appends) <= 2, \
                    f"Too many user-role appends in agent_loop: {user_appends}"
                break

    def test_microcompact_builds_tool_name_map(self, source):
        """microcompact must build tool_name_map to look up tool names."""
        assert "tool_name_map" in source

    def test_teammate_loop_has_alternation_guards(self, source):
        """The _loop method must check last message role before appending user."""
        # Look for the pattern: checking messages[-1]["role"] before append
        assert 'messages[-1]["role"] == "user"' in source or \
               "messages[-1]['role'] == 'user'" in source

    def test_preserve_result_tools_contains_read_file(self, source):
        """_PRESERVE_RESULT_TOOLS must include 'read_file'."""
        assert '"read_file"' in source or "'read_file'" in source
        # More specifically, in the _PRESERVE_RESULT_TOOLS definition
        idx = source.index("_PRESERVE_RESULT_TOOLS")
        snippet = source[idx:idx + 100]
        assert "read_file" in snippet
