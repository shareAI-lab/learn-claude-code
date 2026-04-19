from __future__ import annotations

import threading
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from langchain.tools import ToolRuntime, tool

from coding_deepgent.sessions.records import SessionContext
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore
from coding_deepgent.subagents.schemas import (
    BackgroundSubagentRun,
    BackgroundRuntimeSnapshot,
    BackgroundSubagentSendInput,
    BackgroundSubagentStatusInput,
    BackgroundSubagentStopInput,
    RunBackgroundSubagentInput,
)
from coding_deepgent.subagents.forking import fingerprint_text, tool_surface_snapshot
from coding_deepgent.subagents.tools import (
    resume_fork_task,
    resume_subagent_task,
    resolve_agent_definition,
    run_fork_task,
    run_subagent_task,
)

BACKGROUND_SUBAGENT_NAMESPACE = ("coding_deepgent_subagent_background_runs",)
TERMINAL_BACKGROUND_STATUSES = {"completed", "failed", "cancelled"}


class BackgroundRunStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...

    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...

    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


@dataclass(frozen=True, slots=True)
class BackgroundWorkerHandle:
    thread: threading.Thread
    snapshot: BackgroundRuntimeSnapshot


def _store(runtime: ToolRuntime) -> BackgroundRunStore:
    if runtime.store is None:
        raise RuntimeError("Background subagent runtime requires task/store support")
    return runtime.store


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def save_background_run(
    store: BackgroundRunStore,
    record: BackgroundSubagentRun,
) -> BackgroundSubagentRun:
    store.put(BACKGROUND_SUBAGENT_NAMESPACE, record.run_id, record.model_dump())
    return record


def get_background_run(store: BackgroundRunStore, run_id: str) -> BackgroundSubagentRun:
    item = store.get(BACKGROUND_SUBAGENT_NAMESPACE, run_id)
    if item is None:
        raise KeyError(f"Unknown background subagent run: {run_id}")
    return BackgroundSubagentRun.model_validate(_item_value(item))


def _runtime_thread_id(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    fallback = str(getattr(context, "session_id", "unknown"))
    config = getattr(runtime, "config", None)
    if not isinstance(config, dict):
        return fallback
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return fallback
    return str(configurable.get("thread_id", fallback))


def _runtime_workdir(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    workdir = getattr(context, "workdir", None)
    return str(workdir) if workdir is not None else ""


def _runtime_snapshot(
    runtime: ToolRuntime,
    *,
    parent_thread_id: str,
) -> BackgroundRuntimeSnapshot:
    context = getattr(runtime, "context", None)
    session_id = str(getattr(context, "session_id", parent_thread_id) or parent_thread_id)
    entrypoint = str(getattr(context, "entrypoint", "unknown") or "unknown")
    agent_name = str(getattr(context, "agent_name", "coding-deepgent") or "coding-deepgent")
    rendered_prompt = getattr(context, "rendered_system_prompt", None)
    rendered_prompt_fingerprint = (
        fingerprint_text(rendered_prompt)
        if isinstance(rendered_prompt, str) and rendered_prompt.strip()
        else None
    )
    projection = getattr(context, "visible_tool_projection", None)
    tool_pool_fingerprint: str | None = None
    if projection is not None:
        try:
            tool_pool_fingerprint = tool_surface_snapshot(projection).fingerprint
        except Exception:
            tool_pool_fingerprint = None
    return BackgroundRuntimeSnapshot(
        session_id=session_id,
        parent_thread_id=parent_thread_id,
        workdir=_runtime_workdir(runtime),
        entrypoint=entrypoint,
        agent_name=agent_name,
        has_session_context=isinstance(getattr(context, "session_context", None), SessionContext),
        rendered_prompt_fingerprint=rendered_prompt_fingerprint,
        tool_pool_fingerprint=tool_pool_fingerprint,
    )


def _append_notification(
    runtime: ToolRuntime,
    record: BackgroundSubagentRun,
) -> None:
    context = getattr(runtime, "context", None)
    session_context = getattr(context, "session_context", None)
    if not isinstance(session_context, SessionContext):
        return
    status = (
        "completed"
        if record.status == "completed"
        else "cancelled"
        if record.status == "cancelled"
        else "failed"
    )
    summary = (
        f"{record.title} completed."
        if record.status == "completed"
        else f"{record.title} cancelled."
        if record.status == "cancelled"
        else f"{record.title} failed."
    )
    JsonlSessionStore(session_context.store_dir).append_evidence(
        session_context,
        kind="subagent_notification",
        summary=summary,
        status=status,
        subject=record.run_id,
        metadata={
            "run_id": record.run_id,
            "mode": record.mode,
            "agent_type": record.agent_type,
            "child_thread_id": record.child_thread_id,
            "status": record.status,
            "pending_inputs": len(record.pending_inputs),
            "total_invocations": record.total_invocations,
            "runtime_snapshot": record.runtime_snapshot.model_dump()
            if record.runtime_snapshot is not None
            else None,
        },
    )


def _clip_activity(text: str, *, limit: int = 96) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: limit - 3].rstrip()}..."


def _recent_activities(*items: str) -> list[str]:
    activities = [_clip_activity(item) for item in items if item.strip()]
    return activities[-5:]


def _result_summary(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return _clip_activity(stripped, limit=72)
    return "No summary yet."


def _background_title(*, mode: str, agent_type: str) -> str:
    if mode == "background_fork":
        return "Background fork"
    return f"Background subagent: {agent_type}"


def _terminal_progress(record: BackgroundSubagentRun) -> str:
    if record.status == "completed":
        return f"{record.title} completed."
    if record.status == "cancelled":
        return f"{record.title} cancelled."
    return f"{record.title} failed."


class BackgroundSubagentManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._workers: dict[str, BackgroundWorkerHandle] = {}

    def is_active(self, run_id: str) -> bool:
        worker = self._workers.get(run_id)
        return worker is not None and worker.thread.is_alive()

    def start_subagent(
        self,
        *,
        task: str,
        runtime: ToolRuntime,
        agent_type: str,
        plan_id: str | None,
        max_turns: int | None,
    ) -> BackgroundSubagentRun:
        definition = resolve_agent_definition(agent_type, runtime=runtime)
        run_id = f"bgrun-{uuid.uuid4().hex[:12]}"
        parent_thread_id = _runtime_thread_id(runtime)
        child_thread_id = f"{parent_thread_id}:{agent_type}:{run_id}"
        runtime_snapshot = _runtime_snapshot(runtime, parent_thread_id=parent_thread_id)
        record = BackgroundSubagentRun(
            run_id=run_id,
            mode="background_subagent",
            agent_type=agent_type,
            status="queued",
            title=_background_title(mode="background_subagent", agent_type=agent_type),
            parent_thread_id=parent_thread_id,
            child_thread_id=child_thread_id,
            workdir=_runtime_workdir(runtime),
            requested_max_turns=max_turns,
            effective_max_turns=min(max_turns or definition.max_turns, definition.max_turns),
            model_profile=definition.model_profile,
            plan_id=plan_id,
            runtime_snapshot=runtime_snapshot,
            pending_inputs=[task],
            progress_summary="Queued background subagent run.",
            summary_text="Queued background subagent run.",
            recent_activities=_recent_activities(f"Queued: {task}"),
        )
        return self._start_record(record=record, runtime=runtime)

    def start_fork(
        self,
        *,
        intent: str,
        runtime: ToolRuntime,
        max_turns: int | None,
    ) -> BackgroundSubagentRun:
        run_id = f"bgfork-{uuid.uuid4().hex[:12]}"
        parent_thread_id = _runtime_thread_id(runtime)
        child_thread_id = f"{parent_thread_id}:fork:{run_id}"
        effective_max_turns = 25 if max_turns is None else min(max_turns, 25)
        runtime_snapshot = _runtime_snapshot(runtime, parent_thread_id=parent_thread_id)
        record = BackgroundSubagentRun(
            run_id=run_id,
            mode="background_fork",
            agent_type="fork",
            status="queued",
            title=_background_title(mode="background_fork", agent_type="fork"),
            parent_thread_id=parent_thread_id,
            child_thread_id=child_thread_id,
            workdir=_runtime_workdir(runtime),
            requested_max_turns=max_turns,
            effective_max_turns=effective_max_turns,
            runtime_snapshot=runtime_snapshot,
            pending_inputs=[intent],
            progress_summary="Queued background fork run.",
            summary_text="Queued background fork run.",
            recent_activities=_recent_activities(f"Queued: {intent}"),
        )
        return self._start_record(record=record, runtime=runtime)

    def status(self, *, run_id: str, runtime: ToolRuntime) -> BackgroundSubagentRun:
        with self._lock:
            return get_background_run(_store(runtime), run_id)

    def send_input(
        self,
        *,
        run_id: str,
        message: str,
        runtime: ToolRuntime,
    ) -> BackgroundSubagentRun:
        with self._lock:
            record = get_background_run(_store(runtime), run_id)
            if record.status in {"failed", "cancelled"}:
                raise RuntimeError("Cannot send input to a failed or cancelled background run")
            updated = record.model_copy(
                update={
                    "pending_inputs": [*record.pending_inputs, message],
                    "status": "running" if self.is_active(run_id) else "queued",
                    "stop_requested": False,
                    "progress_summary": (
                        f"{record.title} is processing queued follow-up input."
                        if self.is_active(run_id)
                        else f"Queued follow-up input for {record.title.lower()}."
                    ),
                    "recent_activities": _recent_activities(
                        *record.recent_activities,
                        f"Queued follow-up: {message}",
                    ),
                    "notified": False,
                    "error": None,
                }
            )
            save_background_run(_store(runtime), updated)
            if not self.is_active(run_id):
                self._spawn_worker(run_id=run_id, runtime=runtime)
            return get_background_run(_store(runtime), run_id)

    def stop(
        self,
        *,
        run_id: str,
        runtime: ToolRuntime,
    ) -> BackgroundSubagentRun:
        with self._lock:
            record = get_background_run(_store(runtime), run_id)
            if record.status in TERMINAL_BACKGROUND_STATUSES:
                return record
            updated = record.model_copy(
                update={
                    "stop_requested": True,
                    "progress_summary": f"Stop requested for {record.title.lower()}.",
                    "recent_activities": _recent_activities(
                        *record.recent_activities,
                        "Stop requested",
                    ),
                }
            )
            if not self.is_active(run_id):
                updated = updated.model_copy(
                    update={
                        "status": "cancelled",
                        "pending_inputs": [],
                        "progress_summary": _terminal_progress(
                            updated.model_copy(update={"status": "cancelled"})
                        ),
                    }
                )
                if not updated.notified:
                    _append_notification(runtime, updated)
                    updated = updated.model_copy(update={"notified": True})
            save_background_run(_store(runtime), updated)
            return get_background_run(_store(runtime), run_id)

    def _start_record(
        self,
        *,
        record: BackgroundSubagentRun,
        runtime: ToolRuntime,
    ) -> BackgroundSubagentRun:
        with self._lock:
            save_background_run(_store(runtime), record)
            self._spawn_worker(run_id=record.run_id, runtime=runtime)
            return get_background_run(_store(runtime), record.run_id)

    def _spawn_worker(self, *, run_id: str, runtime: ToolRuntime) -> None:
        worker = self._workers.get(run_id)
        if worker is not None and worker.thread.is_alive():
            return
        record = get_background_run(_store(runtime), run_id)
        snapshot = record.runtime_snapshot or _runtime_snapshot(
            runtime,
            parent_thread_id=record.parent_thread_id,
        )
        thread = threading.Thread(
            target=self._worker,
            kwargs={"run_id": run_id, "runtime": runtime, "snapshot": snapshot},
            daemon=True,
            name=f"coding-deepgent-background-agent-{run_id}",
        )
        self._workers[run_id] = BackgroundWorkerHandle(thread=thread, snapshot=snapshot)
        thread.start()

    def _worker(
        self,
        *,
        run_id: str,
        runtime: ToolRuntime,
        snapshot: BackgroundRuntimeSnapshot,
    ) -> None:
        del snapshot  # durable facts live on the run record; live runtime drives current invoke.
        try:
            while True:
                with self._lock:
                    record = get_background_run(_store(runtime), run_id)
                    if record.stop_requested:
                        cancelled = record.model_copy(
                            update={
                                "status": "cancelled",
                                "pending_inputs": [],
                                "progress_summary": _terminal_progress(
                                    record.model_copy(update={"status": "cancelled"})
                                ),
                                "summary_text": _result_summary(record.latest_result or "Cancelled."),
                            }
                        )
                        if not cancelled.notified:
                            _append_notification(runtime, cancelled)
                            cancelled = cancelled.model_copy(update={"notified": True})
                        save_background_run(_store(runtime), cancelled)
                        return
                    if not record.pending_inputs:
                        terminal = (
                            record
                            if record.status in TERMINAL_BACKGROUND_STATUSES
                            else record.model_copy(
                                update={
                                    "status": "completed",
                                    "progress_summary": _terminal_progress(
                                        record.model_copy(update={"status": "completed"})
                                    ),
                                }
                            )
                        )
                        if terminal.status in TERMINAL_BACKGROUND_STATUSES and not terminal.notified:
                            _append_notification(runtime, terminal)
                            terminal = terminal.model_copy(update={"notified": True})
                        save_background_run(_store(runtime), terminal)
                        return

                    current_input = record.pending_inputs[0]
                    updated = record.model_copy(
                        update={
                            "pending_inputs": record.pending_inputs[1:],
                            "status": "running",
                            "progress_summary": f"{record.title} is running.",
                            "recent_activities": _recent_activities(
                                *record.recent_activities,
                                f"Started: {current_input}",
                            ),
                        }
                    )
                    save_background_run(_store(runtime), updated)

                try:
                    result: object
                    if updated.mode == "background_fork":
                        if updated.total_invocations == 0:
                            result = run_fork_task(
                                intent=current_input,
                                runtime=runtime,
                                max_turns=updated.requested_max_turns,
                                run_id=updated.run_id,
                            )
                        else:
                            result = resume_fork_task(
                                child_thread_id=updated.child_thread_id,
                                runtime=runtime,
                                follow_up=current_input,
                            )
                    elif updated.total_invocations == 0:
                        result = run_subagent_task(
                            task=current_input,
                            runtime=runtime,
                            agent_type=updated.agent_type,
                            plan_id=updated.plan_id,
                            max_turns=updated.requested_max_turns,
                            run_id=updated.run_id,
                        )
                    else:
                        result = resume_subagent_task(
                            subagent_thread_id=updated.child_thread_id,
                            runtime=runtime,
                            follow_up=current_input,
                        )
                except Exception as exc:
                    with self._lock:
                        failed = get_background_run(_store(runtime), run_id).model_copy(
                            update={
                                "status": "failed",
                                "error": str(exc),
                                "progress_summary": _terminal_progress(
                                    updated.model_copy(update={"status": "failed"})
                                ),
                                "summary_text": _result_summary(str(exc)),
                                "recent_activities": _recent_activities(
                                    *updated.recent_activities,
                                    f"Failed: {exc}",
                                ),
                            }
                        )
                        if not failed.notified:
                            _append_notification(runtime, failed)
                            failed = failed.model_copy(update={"notified": True})
                        save_background_run(_store(runtime), failed)
                    return

                with self._lock:
                    latest = get_background_run(_store(runtime), run_id)
                    if latest.stop_requested:
                        next_status = "cancelled"
                        next_summary = _terminal_progress(
                            latest.model_copy(update={"status": "cancelled"})
                        )
                    else:
                        next_status = "running" if latest.pending_inputs else "completed"
                        next_summary = (
                            f"{latest.title} has queued follow-up input."
                            if latest.pending_inputs
                            else _terminal_progress(
                                latest.model_copy(update={"status": "completed"})
                            )
                        )
                    updated_record = latest.model_copy(
                        update={
                            "status": next_status,
                            "child_thread_id": getattr(
                                result,
                                "child_thread_id",
                                latest.child_thread_id,
                            ),
                            "latest_result": str(getattr(result, "content", "")),
                            "summary_text": _result_summary(
                                str(getattr(result, "content", ""))
                            ),
                            "rendered_prompt_fingerprint": getattr(
                                result,
                                "rendered_prompt_fingerprint",
                                latest.rendered_prompt_fingerprint,
                            ),
                            "tool_pool_fingerprint": getattr(
                                getattr(result, "tool_pool_identity", None),
                                "fingerprint",
                                latest.tool_pool_fingerprint,
                            ),
                            "placeholder_layout_version": getattr(
                                getattr(result, "placeholder_layout", None),
                                "version",
                                latest.placeholder_layout_version,
                            ),
                            "error": None,
                            "progress_summary": next_summary,
                            "recent_activities": _recent_activities(
                                *latest.recent_activities,
                                f"Completed: {getattr(result, 'content', '')}",
                            ),
                            "input_tokens": latest.input_tokens
                            + int(getattr(result, "input_tokens", 0)),
                            "output_tokens": latest.output_tokens
                            + int(getattr(result, "output_tokens", 0)),
                            "total_tokens": latest.total_tokens
                            + int(getattr(result, "total_tokens", 0)),
                            "total_duration_ms": latest.total_duration_ms
                            + int(getattr(result, "total_duration_ms", 0)),
                            "total_tool_use_count": latest.total_tool_use_count
                            + int(getattr(result, "total_tool_use_count", 0)),
                            "total_invocations": latest.total_invocations + 1,
                        }
                    )
                    if updated_record.status in TERMINAL_BACKGROUND_STATUSES and not updated_record.notified:
                        _append_notification(runtime, updated_record)
                        updated_record = updated_record.model_copy(update={"notified": True})
                    save_background_run(_store(runtime), updated_record)
                    if updated_record.status in TERMINAL_BACKGROUND_STATUSES:
                        return
        finally:
            with self._lock:
                self._workers.pop(run_id, None)


BACKGROUND_SUBAGENT_MANAGER = BackgroundSubagentManager()


@tool(
    "run_subagent_background",
    args_schema=RunBackgroundSubagentInput,
    description="Start a background subagent run and return immediately with a run id.",
)
def run_subagent_background(
    task: str,
    runtime: ToolRuntime,
    agent_type: str = "general",
    plan_id: str | None = None,
    max_turns: int = 25,
) -> str:
    record = BACKGROUND_SUBAGENT_MANAGER.start_subagent(
        task=task,
        runtime=runtime,
        agent_type=agent_type,
        plan_id=plan_id,
        max_turns=max_turns,
    )
    return record.model_dump_json()


@tool(
    "subagent_status",
    args_schema=BackgroundSubagentStatusInput,
    description="Read one background subagent or background fork status by run id.",
)
def subagent_status(run_id: str, runtime: ToolRuntime) -> str:
    return BACKGROUND_SUBAGENT_MANAGER.status(run_id=run_id, runtime=runtime).model_dump_json()


@tool(
    "subagent_send_input",
    args_schema=BackgroundSubagentSendInput,
    description="Queue follow-up input for an existing background subagent or background fork run.",
)
def subagent_send_input(run_id: str, message: str, runtime: ToolRuntime) -> str:
    return BACKGROUND_SUBAGENT_MANAGER.send_input(
        run_id=run_id,
        message=message,
        runtime=runtime,
    ).model_dump_json()


@tool(
    "subagent_stop",
    args_schema=BackgroundSubagentStopInput,
    description="Request stop for an active or queued background subagent or background fork run.",
)
def subagent_stop(run_id: str, runtime: ToolRuntime) -> str:
    return BACKGROUND_SUBAGENT_MANAGER.stop(run_id=run_id, runtime=runtime).model_dump_json()
