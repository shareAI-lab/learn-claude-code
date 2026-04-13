from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from coding_deepgent.tasks.schemas import (
    TaskCreateInput,
    TaskGetInput,
    TaskListInput,
    TaskRecord,
    TaskStatus,
    TaskUpdateInput,
)
from coding_deepgent.tasks.store import create_task, get_task, list_tasks, update_task


def _store(runtime: ToolRuntime):
    if runtime.store is None:
        raise RuntimeError("Task store is not configured")
    return runtime.store


def _render(record: TaskRecord) -> str:
    return record.model_dump_json()


@tool(
    "task_create",
    args_schema=TaskCreateInput,
    description="Create a durable coding-deepgent task. This is not TodoWrite state.",
)
def task_create(
    title: str,
    runtime: ToolRuntime,
    description: str = "",
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Create one durable task record."""
    return _render(
        create_task(
            _store(runtime),
            title=title,
            description=description,
            depends_on=depends_on,
            owner=owner,
            metadata=metadata,
        )
    )


@tool("task_get", args_schema=TaskGetInput, description="Get one durable task by id.")
def task_get(task_id: str, runtime: ToolRuntime) -> str:
    """Get a durable task by id."""
    return _render(get_task(_store(runtime), task_id))


@tool(
    "task_list",
    args_schema=TaskListInput,
    description="List durable coding-deepgent tasks in deterministic id order.",
)
def task_list(runtime: ToolRuntime, include_terminal: bool = False) -> str:
    """List durable tasks."""
    return (
        "\n".join(
            _render(record)
            for record in list_tasks(_store(runtime), include_terminal=include_terminal)
        )
        or "No tasks."
    )


@tool(
    "task_update",
    args_schema=TaskUpdateInput,
    description="Update durable task status, owner, or metadata with transition validation.",
)
def task_update(
    task_id: str,
    runtime: ToolRuntime,
    status: TaskStatus | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Update one durable task."""
    return _render(
        update_task(
            _store(runtime),
            task_id=task_id,
            status=status,
            owner=owner,
            metadata=metadata,
        )
    )
