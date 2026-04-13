from __future__ import annotations

from typing import cast

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, ValidationError

from coding_deepgent.memory import (
    MemoryRecord,
    SaveMemoryInput,
    list_memory_records,
    recall_memories,
    save_memory,
    save_memory_record,
)


def test_save_memory_schema_is_strict_and_model_visible() -> None:
    tool_call_schema = cast(type[BaseModel], save_memory.tool_call_schema)
    schema = tool_call_schema.model_json_schema()

    assert save_memory.name == "save_memory"
    assert schema["required"] == ["content"]
    assert "tool_call_id" not in schema["properties"]
    assert "content" in schema["properties"]

    with pytest.raises(ValidationError):
        SaveMemoryInput.model_validate({"task": "do not alias"})
    with pytest.raises(ValidationError):
        SaveMemoryInput.model_validate({"content": "remember", "extra": "nope"})


def test_memory_store_save_list_and_recall_are_deterministic() -> None:
    store = InMemoryStore()
    first = MemoryRecord(
        content="Use LangChain store for long-term memory", namespace="project"
    )
    second = MemoryRecord(
        content="Keep Todo separate from durable tasks", namespace="project"
    )

    first_key = save_memory_record(store, first)
    second_key = save_memory_record(store, second)

    assert first_key != second_key
    assert [record.content for record in list_memory_records(store, "project")] == [
        first.content,
        second.content,
    ]
    assert [
        record.content for record in recall_memories(store, query="LangChain", limit=2)
    ] == [first.content]
    assert recall_memories(None) == []
