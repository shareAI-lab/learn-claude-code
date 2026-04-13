from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

from coding_deepgent.tasks import (
    TaskCreateInput,
    TaskRecord,
    create_task,
    get_task,
    is_task_ready,
    task_create,
    task_get,
    task_list,
    task_namespace,
    task_update,
    update_task,
)


def runtime_with_store(store: InMemoryStore) -> SimpleNamespace:
    return SimpleNamespace(store=store)


def test_task_store_transitions_dependencies_and_ready_rule() -> None:
    store = InMemoryStore()
    parent = create_task(store, title="Parent")
    child = create_task(store, title="Child", depends_on=[parent.id])

    assert is_task_ready(store, child) is False
    assert (
        update_task(store, task_id=parent.id, status="in_progress").status
        == "in_progress"
    )
    assert (
        update_task(store, task_id=parent.id, status="completed").status == "completed"
    )
    assert is_task_ready(store, get_task(store, child.id)) is True

    with pytest.raises(ValueError):
        update_task(store, task_id=parent.id, status="pending")


def test_task_tools_are_strict_and_do_not_mutate_todo_state() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)

    created = cast(Any, task_create).func("Implement tests", runtime)
    task_id = TaskRecord.model_validate_json(created).id

    assert (
        TaskRecord.model_validate_json(cast(Any, task_get).func(task_id, runtime)).title
        == "Implement tests"
    )
    assert task_id in cast(Any, task_list).func(runtime)
    assert (
        TaskRecord.model_validate_json(
            cast(Any, task_update).func(task_id, runtime, status="in_progress")
        ).status
        == "in_progress"
    )
    assert store.search(task_namespace())

    with pytest.raises(ValidationError):
        TaskCreateInput.model_validate({"content": "wrong", "runtime": runtime})
