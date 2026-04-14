from __future__ import annotations

from typing import cast

from langchain.tools import ToolRuntime, tool

from coding_deepgent.memory.schemas import (
    MemoryNamespace,
    MemoryRecord,
    SaveMemoryInput,
)
from coding_deepgent.memory.policy import evaluate_memory_quality
from coding_deepgent.memory.store import list_memory_records, save_memory_record


@tool(
    "save_memory",
    args_schema=SaveMemoryInput,
    description=(
        "Save durable reusable knowledge or preferences as long-term memory. "
        "Do not save transient todos, current plans, task status, recovery notes, "
        "duplicates, or one-off observations."
    ),
)
def save_memory(
    content: str,
    runtime: ToolRuntime,
    namespace: str = "project",
    source: str = "agent",
) -> str:
    """Save reusable long-term memory through the LangGraph store seam."""

    validated = SaveMemoryInput(
        content=content,
        namespace=cast(MemoryNamespace, namespace),
        source=source,
        runtime=runtime,
    )
    store = runtime.store
    if store is None:
        return "Memory store is not configured; memory was not saved."
    record = MemoryRecord(
        content=validated.content,
        namespace=validated.namespace,
        source=validated.source,
    )
    quality = evaluate_memory_quality(
        record,
        existing_records=list_memory_records(store, validated.namespace),
    )
    if not quality.allowed:
        return f"Memory not saved: {quality.reason}."

    key = save_memory_record(store, record)
    return f"Saved memory {key} in {validated.namespace}."
