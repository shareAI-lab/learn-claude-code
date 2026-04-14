from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from coding_deepgent.tasks.schemas import (
    PlanGetInput,
    PlanSaveInput,
    TaskCreateInput,
    TaskGetInput,
    TaskListInput,
    TaskRecord,
    TaskStatus,
    TaskUpdateInput,
)
from coding_deepgent.tasks.store import (
    create_plan,
    create_task,
    get_plan,
    get_task,
    is_task_ready,
    list_tasks,
    task_graph_needs_verification,
    update_task,
)


def _store(runtime: ToolRuntime):
    if runtime.store is None:
        raise RuntimeError("Task store is not configured")
    return runtime.store


def _render(record: TaskRecord) -> str:
    return record.model_dump_json()


def _render_plan(record) -> str:
    return record.model_dump_json()


def _render_list_record(runtime: ToolRuntime, record: TaskRecord) -> str:
    ready = str(is_task_ready(_store(runtime), record)).lower()
    return _render(
        record.model_copy(update={"metadata": {**record.metadata, "ready": ready}})
    )


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
            _render_list_record(runtime, record)
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
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Update one durable task."""
    store = _store(runtime)
    updated = update_task(
        store,
        task_id=task_id,
        status=status,
        depends_on=depends_on,
        owner=owner,
        metadata=metadata,
    )
    if status == "completed" and task_graph_needs_verification(store):
        return _render(
            updated.model_copy(
                update={
                    "metadata": {
                        **updated.metadata,
                        "verification_nudge": "true",
                    }
                }
            )
        )
    return _render(updated)


@tool(
    "plan_save",
    args_schema=PlanSaveInput,
    description="Save an explicit durable implementation plan artifact with verification criteria.",
)
def plan_save(
    title: str,
    content: str,
    verification: str,
    runtime: ToolRuntime,
    task_ids: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Save one durable plan artifact."""
    return _render_plan(
        create_plan(
            _store(runtime),
            title=title,
            content=content,
            verification=verification,
            task_ids=task_ids,
            metadata=metadata,
        )
    )


@tool("plan_get", args_schema=PlanGetInput, description="Get one durable plan artifact.")
def plan_get(plan_id: str, runtime: ToolRuntime) -> str:
    """Get a durable plan artifact by id."""
    return _render_plan(get_plan(_store(runtime), plan_id))
