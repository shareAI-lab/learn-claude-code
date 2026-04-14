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
    task_graph_needs_verification,
    task_update,
    update_task,
    validate_task_graph,
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


def test_task_graph_rejects_missing_self_and_cycle_dependencies() -> None:
    store = InMemoryStore()
    parent = create_task(store, title="Parent")
    child = create_task(store, title="Child", depends_on=[parent.id])

    with pytest.raises(ValueError, match="Unknown task dependencies"):
        create_task(store, title="Missing dependency", depends_on=["task-missing"])

    with pytest.raises(ValueError, match="cannot depend on itself"):
        update_task(store, task_id=child.id, depends_on=[child.id])

    with pytest.raises(ValueError, match="cycle"):
        update_task(store, task_id=parent.id, depends_on=[child.id])

    store.put(
        task_namespace(),
        child.id,
        child.model_copy(update={"depends_on": [child.id]}).model_dump(),
    )
    with pytest.raises(ValueError, match="cannot depend on itself"):
        validate_task_graph(store)


def test_task_update_requires_blocked_reason_or_dependency() -> None:
    store = InMemoryStore()
    task = create_task(store, title="Investigate failure")
    blocker = create_task(store, title="Collect logs")

    with pytest.raises(ValueError, match="blocked tasks require"):
        update_task(store, task_id=task.id, status="blocked")

    assert (
        update_task(
            store,
            task_id=task.id,
            status="blocked",
            metadata={"blocked_reason": "Need logs"},
        ).status
        == "blocked"
    )
    other = create_task(store, title="Wait on dependency")
    assert (
        update_task(
            store,
            task_id=other.id,
            status="blocked",
            depends_on=[blocker.id],
        ).depends_on
        == [blocker.id]
    )


def test_task_graph_needs_verification_after_closing_three_tasks() -> None:
    store = InMemoryStore()
    first = create_task(store, title="Implement feature")
    second = create_task(store, title="Update docs")
    third = create_task(store, title="Run smoke")

    assert task_graph_needs_verification(store) is False
    for task in (first, second, third):
        update_task(store, task_id=task.id, status="in_progress")
        update_task(store, task_id=task.id, status="completed")

    assert task_graph_needs_verification(store) is True


def test_task_graph_with_verification_task_does_not_need_nudge() -> None:
    store = InMemoryStore()
    first = create_task(store, title="Implement feature")
    second = create_task(store, title="Update docs")
    verify = create_task(store, title="Verify implementation")

    for task in (first, second, verify):
        update_task(store, task_id=task.id, status="in_progress")
        update_task(store, task_id=task.id, status="completed")

    assert task_graph_needs_verification(store) is False


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
    assert '"ready":"true"' in cast(Any, task_list).func(runtime)
    assert (
        TaskRecord.model_validate_json(
            cast(Any, task_update).func(
                task_id, runtime, status="in_progress"
            )
        ).status
        == "in_progress"
    )
    assert store.search(task_namespace())

    with pytest.raises(ValidationError):
        TaskCreateInput.model_validate({"content": "wrong", "runtime": runtime})


def test_task_update_tool_marks_verification_nudge_in_output_metadata() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)
    tasks = [
        create_task(store, title="Implement feature"),
        create_task(store, title="Update docs"),
        create_task(store, title="Run smoke"),
    ]
    for task in tasks[:2]:
        update_task(store, task_id=task.id, status="in_progress")
        update_task(store, task_id=task.id, status="completed")
    update_task(store, task_id=tasks[2].id, status="in_progress")

    output = cast(Any, task_update).func(
        tasks[2].id,
        runtime,
        status="completed",
    )

    assert (
        TaskRecord.model_validate_json(output).metadata["verification_nudge"]
        == "true"
    )
    assert get_task(store, tasks[2].id).metadata == {}
