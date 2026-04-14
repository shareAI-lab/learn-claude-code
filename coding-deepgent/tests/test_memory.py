from __future__ import annotations

from typing import cast

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, ValidationError

from coding_deepgent.memory import (
    MemoryRecord,
    SaveMemoryInput,
    evaluate_memory_quality,
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
    assert [record.content for record in recall_memories(store, limit=1)] == [
        first.content
    ]
    assert recall_memories(None) == []


def test_memory_quality_policy_rejects_transient_and_duplicate_entries() -> None:
    existing = [
        MemoryRecord(
            content="Prefer LangChain stores for cross-session memory",
            namespace="project",
        )
    ]

    duplicate = evaluate_memory_quality(
        MemoryRecord(
            content=" prefer   langchain stores for cross-session MEMORY ",
            namespace="project",
        ),
        existing_records=existing,
    )
    transient = evaluate_memory_quality(
        MemoryRecord(content="Currently working on Stage 12D", namespace="project")
    )
    durable = evaluate_memory_quality(
        MemoryRecord(
            content="Use LangChain stores for cross-session memory",
            namespace="project",
        ),
        existing_records=existing,
    )

    assert duplicate.allowed is False
    assert duplicate.category == "duplicate"
    assert transient.allowed is False
    assert transient.category == "transient_state"
    assert durable.allowed is True
    assert durable.category == "accepted"


def test_memory_namespaces_are_isolated_for_recall_and_duplicates() -> None:
    store = InMemoryStore()
    project = MemoryRecord(
        content="Prefer LangChain stores for memory", namespace="project"
    )
    user = MemoryRecord(
        content="Prefer concise answers by default", namespace="user"
    )
    save_memory_record(store, project)
    save_memory_record(store, user)

    project_records = list_memory_records(store, "project")
    user_records = list_memory_records(store, "user")
    project_recall = recall_memories(store, namespace="project", query="LangChain")
    user_recall = recall_memories(store, namespace="user", query="concise")

    duplicate_in_same_namespace = evaluate_memory_quality(
        MemoryRecord(
            content=" prefer   langchain stores for MEMORY ", namespace="project"
        ),
        existing_records=project_records,
    )
    same_content_other_namespace = evaluate_memory_quality(
        MemoryRecord(
            content=" prefer   langchain stores for MEMORY ", namespace="user"
        ),
        existing_records=user_records,
    )

    assert [record.namespace for record in project_records] == ["project"]
    assert [record.namespace for record in user_records] == ["user"]
    assert [record.namespace for record in project_recall] == ["project"]
    assert [record.namespace for record in user_recall] == ["user"]
    assert duplicate_in_same_namespace.allowed is False
    assert same_content_other_namespace.allowed is True
