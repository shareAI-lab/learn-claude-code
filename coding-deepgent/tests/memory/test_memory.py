from __future__ import annotations

from typing import cast

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, ValidationError

from coding_deepgent.memory import (
    DeleteMemoryInput,
    ListMemoryInput,
    MemoryRecord,
    SaveMemoryInput,
    delete_memory_record,
    list_memory_entries,
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
    assert schema["required"] == ["type"]
    assert "runtime" not in schema["properties"]
    assert "type" in schema["properties"]
    assert "rule" in schema["properties"]
    assert "fact_or_decision" in schema["properties"]

    with pytest.raises(ValidationError):
        SaveMemoryInput.model_validate({"task": "do not alias"})
    with pytest.raises(ValidationError):
        SaveMemoryInput.model_validate({"type": "feedback", "extra": "nope"})
    with pytest.raises(ValidationError):
        SaveMemoryInput.model_validate(
            {
                "type": "feedback",
                "rule": "Run lint before commit",
            }
        )
    with pytest.raises(ValidationError):
        ListMemoryInput.model_validate({"limit": 0})
    with pytest.raises(ValidationError):
        DeleteMemoryInput.model_validate({"type": "feedback", "key": " "})


def test_memory_store_save_list_and_recall_are_deterministic() -> None:
    store = InMemoryStore()
    first = MemoryRecord(
        type="feedback",
        rule="Run lint before commit",
        why="The repo requires clean validation before code submission",
        how_to_apply="Before any commit-like completion step, run lint first",
    )
    second = MemoryRecord(
        type="project",
        fact_or_decision="Use LangChain store for long-term memory",
        why="Cross-session continuity should not depend on transcript replay alone",
        how_to_apply="Prefer store-backed memory for durable reusable knowledge",
    )

    first_key = save_memory_record(store, first)
    second_key = save_memory_record(store, second)

    assert first_key != second_key
    assert [record.type for record in list_memory_records(store, "feedback")] == [
        "feedback"
    ]
    assert [record.type for record in list_memory_records(store, "project")] == [
        "project"
    ]
    assert [
        record.type
        for record in recall_memories(store, query="lint continuity", limit=2)
    ] == ["feedback", "project"]
    assert [record.type for record in recall_memories(store, limit=1)] == ["feedback"]
    assert recall_memories(None) == []


def test_memory_entries_expose_keys_and_delete_is_exact() -> None:
    store = InMemoryStore()
    record = MemoryRecord(
        type="feedback",
        rule="Run lint before commit",
        why="The repo requires clean validation before code submission",
        how_to_apply="Before any commit-like completion step, run lint first",
    )
    key = save_memory_record(store, record)

    entries = list_memory_entries(store, "feedback")

    assert [(entry.key, entry.record.type) for entry in entries] == [(key, "feedback")]
    assert delete_memory_record(store, memory_type="feedback", key="missing") is False
    assert delete_memory_record(store, memory_type="feedback", key=key) is True
    assert list_memory_entries(store, "feedback") == []


def test_memory_quality_policy_rejects_duplicate_transient_derivable_and_relative_time() -> None:
    existing = [
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        )
    ]

    duplicate = evaluate_memory_quality(
        MemoryRecord(
            type="feedback",
            rule=" run lint before commit ",
            why=" the repo requires clean validation before code submission ",
            how_to_apply=" before any commit-like completion step, run lint first ",
        ),
        existing_records=existing,
    )
    transient = evaluate_memory_quality(
        MemoryRecord(
            type="project",
            fact_or_decision="Currently working on Stage 12D",
            why="It is the active task right now",
            how_to_apply="Continue the task in this session",
        )
    )
    derivable = evaluate_memory_quality(
        MemoryRecord(
            type="project",
            fact_or_decision="The file list includes src/ and tests/",
            why="This is repository structure only",
            how_to_apply="Read the repo when you need it",
        )
    )
    relative_time = evaluate_memory_quality(
        MemoryRecord(
            type="project",
            fact_or_decision="The migration finishes next Tuesday",
            why="That is the target release date",
            how_to_apply="Plan the rollout around next Tuesday",
        )
    )
    durable = evaluate_memory_quality(
        MemoryRecord(
            type="project",
            fact_or_decision="Use LangChain store for long-term memory",
            why="Cross-session continuity should not depend on transcript replay alone",
            how_to_apply="Prefer store-backed memory for durable reusable knowledge",
        ),
    )

    assert duplicate.allowed is False
    assert duplicate.category == "duplicate"
    assert transient.allowed is False
    assert transient.category == "transient_state"
    assert derivable.allowed is False
    assert derivable.category == "derivable_information"
    assert relative_time.allowed is False
    assert relative_time.category == "relative_time"
    assert durable.allowed is True
    assert durable.category == "accepted"


def test_memory_types_are_isolated_for_recall_and_duplicates() -> None:
    store = InMemoryStore()
    feedback = MemoryRecord(
        type="feedback",
        rule="Run lint before commit",
        why="The repo requires clean validation before code submission",
        how_to_apply="Before any commit-like completion step, run lint first",
    )
    user = MemoryRecord(
        type="user",
        profile="User prefers concise answers by default",
        why_it_matters="Summaries should stay brief unless depth is requested",
        how_to_apply="Default to concise status updates and closers",
    )
    save_memory_record(store, feedback)
    save_memory_record(store, user)

    feedback_records = list_memory_records(store, "feedback")
    user_records = list_memory_records(store, "user")
    feedback_recall = recall_memories(store, memory_type="feedback", query="lint")
    user_recall = recall_memories(store, memory_type="user", query="concise")

    duplicate_in_same_type = evaluate_memory_quality(
        MemoryRecord(
            type="feedback",
            rule=" run lint before commit ",
            why=" the repo requires clean validation before code submission ",
            how_to_apply=" before any commit-like completion step, run lint first ",
        ),
        existing_records=feedback_records,
    )
    same_text_other_type = evaluate_memory_quality(
        MemoryRecord(
            type="user",
            profile="Run lint before commit",
            why_it_matters="The user wants reliable delivery",
            how_to_apply="Mention lint in completion summaries when relevant",
        ),
        existing_records=user_records,
    )

    assert [record.type for record in feedback_records] == ["feedback"]
    assert [record.type for record in user_records] == ["user"]
    assert [record.type for record in feedback_recall] == ["feedback"]
    assert [record.type for record in user_recall] == ["user"]
    assert duplicate_in_same_type.allowed is False
    assert same_text_other_type.allowed is True
