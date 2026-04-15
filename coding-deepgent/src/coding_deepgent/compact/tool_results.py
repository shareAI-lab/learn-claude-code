from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.messages import ToolMessage

from coding_deepgent.runtime.context import RuntimeContext

PERSISTED_OUTPUT_TAG = "<persisted-output>"
PERSISTED_OUTPUT_CLOSING_TAG = "</persisted-output>"
TOOL_RESULTS_DIR = ".coding-deepgent/tool-results"
DEFAULT_PREVIEW_CHARS = 2000


@dataclass(frozen=True, slots=True)
class PersistedToolResult:
    relative_path: str
    absolute_path: Path
    original_length: int
    preview: str
    has_more: bool
    serialized_kind: str


def maybe_persist_large_tool_result(
    result: ToolMessage,
    *,
    runtime_context: RuntimeContext,
    max_inline_chars: int | None,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> ToolMessage:
    if result.status != "success":
        return result
    if max_inline_chars is None or max_inline_chars < 1:
        return result

    serialized, serialized_kind = _serialize_content(result.content)
    if len(serialized) <= max_inline_chars:
        return result

    persisted = persist_tool_result(
        serialized,
        runtime_context=runtime_context,
        tool_call_id=result.tool_call_id,
        serialized_kind=serialized_kind,
        preview_chars=preview_chars,
    )
    artifact = {
        "kind": "persisted_output",
        "path": persisted.relative_path,
        "original_length": persisted.original_length,
        "preview_chars": preview_chars,
        "serialized_kind": persisted.serialized_kind,
        "has_more": persisted.has_more,
    }
    if result.artifact is not None:
        artifact["upstream_artifact"] = result.artifact

    return ToolMessage(
        content=build_large_tool_result_message(persisted),
        tool_call_id=result.tool_call_id,
        artifact=artifact,
        status=result.status,
        additional_kwargs=dict(result.additional_kwargs),
        response_metadata=dict(result.response_metadata),
        name=result.name,
        id=result.id,
    )


def persist_tool_result(
    content: str,
    *,
    runtime_context: RuntimeContext,
    tool_call_id: str,
    serialized_kind: str,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> PersistedToolResult:
    result_dir = tool_results_dir(runtime_context)
    result_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{sanitize_path_segment(tool_call_id)}.{_file_extension(serialized_kind)}"
    absolute_path = result_dir / filename
    if not absolute_path.exists():
        absolute_path.write_text(content, encoding="utf-8")

    preview = content[:preview_chars]
    relative_path = absolute_path.relative_to(runtime_context.workdir).as_posix()
    return PersistedToolResult(
        relative_path=relative_path,
        absolute_path=absolute_path,
        original_length=len(content),
        preview=preview,
        has_more=len(content) > preview_chars,
        serialized_kind=serialized_kind,
    )


def tool_results_dir(runtime_context: RuntimeContext) -> Path:
    return (
        runtime_context.workdir
        / TOOL_RESULTS_DIR
        / sanitize_path_segment(runtime_context.session_id)
    )


def build_large_tool_result_message(result: PersistedToolResult) -> str:
    lines = [
        PERSISTED_OUTPUT_TAG,
        (
            f"Output too large ({result.original_length} chars). "
            f"Full output saved to: {result.relative_path}"
        ),
        "",
        f"Preview (first {len(result.preview)} chars):",
        result.preview,
    ]
    if result.has_more:
        lines.append("...")
    lines.append(PERSISTED_OUTPUT_CLOSING_TAG)
    return "\n".join(lines)


def sanitize_path_segment(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return sanitized.strip(".-") or "value"


def _serialize_content(content: Any) -> tuple[str, str]:
    if isinstance(content, str):
        return content, "text"
    if isinstance(content, list):
        return json.dumps(content, ensure_ascii=False, sort_keys=True, default=str), "json"
    return str(content), "text"


def _file_extension(serialized_kind: str) -> str:
    return "json" if serialized_kind == "json" else "txt"
