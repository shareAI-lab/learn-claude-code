from __future__ import annotations

from pathlib import Path

from langchain.messages import ToolMessage

from coding_deepgent.compact import (
    PERSISTED_OUTPUT_CLOSING_TAG,
    PERSISTED_OUTPUT_TAG,
    maybe_persist_large_tool_result,
    tool_results_dir,
)
from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext


def runtime_context(workdir: Path) -> RuntimeContext:
    return RuntimeContext(
        session_id="session-1",
        workdir=workdir,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="test-agent",
        skill_dir=workdir / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
    )


def test_maybe_persist_large_tool_result_replaces_large_content_with_preview(
    tmp_path: Path,
) -> None:
    context = runtime_context(tmp_path)
    message = ToolMessage(content="x" * 5000, tool_call_id="call:1")

    result = maybe_persist_large_tool_result(
        message,
        runtime_context=context,
        max_inline_chars=4000,
        preview_chars=20,
    )

    assert result is not message
    assert PERSISTED_OUTPUT_TAG in str(result.content)
    assert PERSISTED_OUTPUT_CLOSING_TAG in str(result.content)
    assert ".coding-deepgent/tool-results/session-1/call-1.txt" in str(result.content)
    assert result.artifact == {
        "kind": "persisted_output",
        "path": ".coding-deepgent/tool-results/session-1/call-1.txt",
        "original_length": 5000,
        "preview_chars": 20,
        "serialized_kind": "text",
        "has_more": True,
    }
    stored = tool_results_dir(context) / "call-1.txt"
    assert stored.exists()
    assert stored.read_text(encoding="utf-8") == "x" * 5000


def test_maybe_persist_large_tool_result_keeps_small_content_inline(
    tmp_path: Path,
) -> None:
    context = runtime_context(tmp_path)
    message = ToolMessage(content="small", tool_call_id="call-1")

    result = maybe_persist_large_tool_result(
        message,
        runtime_context=context,
        max_inline_chars=4000,
    )

    assert result is message
    assert not tool_results_dir(context).exists()


def test_maybe_persist_large_tool_result_preserves_existing_artifact(
    tmp_path: Path,
) -> None:
    context = runtime_context(tmp_path)
    message = ToolMessage(
        content="y" * 4500,
        tool_call_id="call-1",
        artifact={"upstream": True},
    )

    result = maybe_persist_large_tool_result(
        message,
        runtime_context=context,
        max_inline_chars=4000,
        preview_chars=10,
    )

    assert result.artifact == {
        "kind": "persisted_output",
        "path": ".coding-deepgent/tool-results/session-1/call-1.txt",
        "original_length": 4500,
        "preview_chars": 10,
        "serialized_kind": "text",
        "has_more": True,
        "upstream_artifact": {"upstream": True},
    }
