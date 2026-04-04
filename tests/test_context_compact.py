"""Unit tests for micro_compact and estimate_tokens (s06_context_compact.py)."""
from __future__ import annotations

import tempfile
import types
from pathlib import Path

import pytest

from conftest import load_agent_module


@pytest.fixture()
def compact_module():
    with tempfile.TemporaryDirectory() as tmp:
        module = load_agent_module("s06_context_compact.py", Path(tmp))
        yield module


# -- estimate_tokens --

class TestEstimateTokens:
    def test_basic(self, compact_module):
        msgs = [{"role": "user", "content": "a" * 400}]
        result = compact_module.estimate_tokens(msgs)
        assert result == len(str(msgs)) // 4

    def test_empty_messages(self, compact_module):
        assert compact_module.estimate_tokens([]) == len(str([])) // 4


# -- micro_compact --

def _tool_use_block(tool_id: str, name: str):
    """Create a mock tool_use block (SimpleNamespace mimicking Anthropic SDK object)."""
    return types.SimpleNamespace(type="tool_use", id=tool_id, name=name, input={})


def _tool_result(tool_id: str, content: str):
    """Create a tool_result dict."""
    return {"type": "tool_result", "tool_use_id": tool_id, "content": content}


def _make_messages(n_results: int, tool_name: str = "bash"):
    """Build a message list with n tool_use/tool_result pairs.

    Each pair is: assistant message with tool_use block, then user message with tool_result.
    """
    messages = []
    for i in range(n_results):
        tid = f"tool_{i}"
        messages.append({
            "role": "assistant",
            "content": [_tool_use_block(tid, tool_name)],
        })
        messages.append({
            "role": "user",
            "content": [_tool_result(tid, f"Output line {'x' * 200} for call {i}")],
        })
    return messages


class TestMicroCompact:
    def test_few_results_unchanged(self, compact_module):
        """With <= KEEP_RECENT results, nothing is compacted."""
        messages = _make_messages(3)  # exactly KEEP_RECENT
        original_contents = [
            messages[i]["content"][0]["content"]
            for i in range(1, len(messages), 2)
        ]
        compact_module.micro_compact(messages)
        for idx, i in enumerate(range(1, len(messages), 2)):
            assert messages[i]["content"][0]["content"] == original_contents[idx]

    def test_clears_old_results(self, compact_module):
        """With > KEEP_RECENT results, oldest are replaced with placeholder."""
        messages = _make_messages(5)
        compact_module.micro_compact(messages)
        # First 2 results (index 0,1) should be compacted
        assert messages[1]["content"][0]["content"] == "[Previous: used bash]"
        assert messages[3]["content"][0]["content"] == "[Previous: used bash]"
        # Last 3 results should be preserved
        assert messages[5]["content"][0]["content"].startswith("Output line")
        assert messages[7]["content"][0]["content"].startswith("Output line")
        assert messages[9]["content"][0]["content"].startswith("Output line")

    def test_preserves_read_file(self, compact_module):
        """read_file results are never compacted."""
        messages = _make_messages(5, tool_name="read_file")
        compact_module.micro_compact(messages)
        # All should be preserved since tool_name is read_file
        for i in range(1, len(messages), 2):
            assert messages[i]["content"][0]["content"].startswith("Output line")

    def test_skips_short_content(self, compact_module):
        """Content <= 100 chars is not compacted."""
        messages = []
        for i in range(5):
            tid = f"tool_{i}"
            messages.append({
                "role": "assistant",
                "content": [_tool_use_block(tid, "bash")],
            })
            messages.append({
                "role": "user",
                "content": [_tool_result(tid, "short")],  # <= 100 chars
            })
        compact_module.micro_compact(messages)
        # All should be preserved because content is short
        for i in range(1, len(messages), 2):
            assert messages[i]["content"][0]["content"] == "short"

    def test_unknown_tool_name(self, compact_module):
        """When tool_use_id has no matching tool_use block, uses 'unknown'."""
        messages = [
            # No assistant message with matching tool_use
            {"role": "user", "content": [_tool_result("orphan_0", "x" * 200)]},
            {"role": "user", "content": [_tool_result("orphan_1", "x" * 200)]},
            {"role": "user", "content": [_tool_result("orphan_2", "x" * 200)]},
            {"role": "user", "content": [_tool_result("orphan_3", "x" * 200)]},
        ]
        compact_module.micro_compact(messages)
        # First result should be compacted with "unknown"
        assert messages[0]["content"][0]["content"] == "[Previous: used unknown]"
