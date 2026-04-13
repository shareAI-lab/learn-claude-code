from __future__ import annotations

from typing import cast

from langchain.tools import ToolRuntime, tool

from coding_deepgent.memory.schemas import (
    MemoryNamespace,
    MemoryRecord,
    SaveMemoryInput,
)
from coding_deepgent.memory.store import save_memory_record


@tool(
    "save_memory",
    description=(
        "Save durable reusable knowledge or preferences as long-term memory. "
        "Do not save transient todos, current plans, task status, or one-off observations."
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
        content=content, namespace=cast(MemoryNamespace, namespace), source=source
    )
    store = runtime.store
    if store is None:
        return "Memory store is not configured; memory was not saved."
    record = MemoryRecord(
        content=validated.content,
        namespace=validated.namespace,
        source=validated.source,
    )
    key = save_memory_record(store, record)
    return f"Saved memory {key} in {validated.namespace}."
