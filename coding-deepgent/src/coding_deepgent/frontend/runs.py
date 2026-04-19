from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from coding_deepgent.settings import Settings, load_settings

from .producer import BridgeSession, PromptRunner, build_default_prompt_runner, build_fake_prompt_runner
from .protocol import FrontendEvent, SubmitPromptInput, dump_frontend_event
from .stream_bridge import MemoryStreamBridge

RunStatus = Literal["pending", "running", "completed", "failed", "interrupted"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RunRecord:
    run_id: str
    thread_id: str
    status: RunStatus
    created_at: str
    updated_at: str
    error: str | None = None
    worker: threading.Thread | None = field(default=None, repr=False)


class FrontendRunManager:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def create(self, thread_id: str) -> RunRecord:
        run_id = str(uuid.uuid4())
        now = _now_iso()
        record = RunRecord(
            run_id=run_id,
            thread_id=thread_id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._runs[run_id] = record
        return record

    def create_or_reject(self, thread_id: str) -> RunRecord:
        with self._lock:
            inflight = [
                record
                for record in self._runs.values()
                if record.thread_id == thread_id
                and record.status in {"pending", "running"}
            ]
            if inflight:
                raise FrontendRunConflictError(
                    f"Thread {thread_id} already has an active run"
                )
        return self.create(thread_id)

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_by_thread(self, thread_id: str) -> list[RunRecord]:
        with self._lock:
            return [record for record in self._runs.values() if record.thread_id == thread_id]

    def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return
            record.status = status
            record.updated_at = _now_iso()
            if error is not None:
                record.error = error


class FrontendRunService:
    """Background run lifecycle for future SSE/Gateway consumers."""

    def __init__(
        self,
        *,
        bridge: MemoryStreamBridge | None = None,
        run_manager: FrontendRunManager | None = None,
        settings: Settings | None = None,
        prompt_runner: PromptRunner | None = None,
        fake: bool = False,
    ) -> None:
        self.bridge = bridge or MemoryStreamBridge()
        self.run_manager = run_manager or FrontendRunManager()
        self.settings = settings or load_settings()
        self.prompt_runner = prompt_runner or (
            build_fake_prompt_runner() if fake else build_default_prompt_runner(self.settings)
        )
        self._sessions: dict[str, BridgeSession] = {}
        self._lock = threading.Lock()

    def start_run(self, *, thread_id: str, prompt: str) -> RunRecord:
        record = self.run_manager.create_or_reject(thread_id)
        self.bridge.publish(
            record.run_id,
            "metadata",
            {"run_id": record.run_id, "thread_id": record.thread_id},
        )
        worker = threading.Thread(
            target=self._run_worker,
            args=(record, prompt),
            daemon=True,
        )
        record.worker = worker
        worker.start()
        return record

    def _run_worker(self, record: RunRecord, prompt: str) -> None:
        self.run_manager.set_status(record.run_id, "running")
        session = self._session_for(record.thread_id)
        try:
            session.handle(
                SubmitPromptInput(text=prompt),
                lambda event: self._publish_frontend_event(record.run_id, event),
            )
        except Exception as exc:  # pragma: no cover - defensive worker failure
            self.run_manager.set_status(record.run_id, "failed", error=str(exc))
            self.bridge.publish(
                record.run_id,
                "error",
                {"message": str(exc), "name": type(exc).__name__},
            )
        else:
            current = self.run_manager.get(record.run_id)
            if current is not None and current.status == "running":
                self.run_manager.set_status(record.run_id, "completed")
        finally:
            self.bridge.publish_end(record.run_id)

    def _publish_frontend_event(self, run_id: str, event: FrontendEvent) -> None:
        self.bridge.publish(run_id, event.type, dump_frontend_event(event))
        if event.type == "run_failed":
            self.run_manager.set_status(run_id, "failed", error=event.error)
        elif event.type == "run_finished":
            current = self.run_manager.get(run_id)
            if current is not None and current.status == "running":
                self.run_manager.set_status(run_id, "completed")

    def _session_for(self, thread_id: str) -> BridgeSession:
        with self._lock:
            session = self._sessions.get(thread_id)
            if session is None:
                session = BridgeSession(
                    settings=self.settings,
                    prompt_runner=self.prompt_runner,
                    session_id=thread_id,
                )
                self._sessions[thread_id] = session
            return session


class FrontendRunConflictError(RuntimeError):
    """Raised when a thread already has a pending/running frontend run."""
