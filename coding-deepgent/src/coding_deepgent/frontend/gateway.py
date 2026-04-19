from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from coding_deepgent.settings import Settings, load_settings

from .adapters.sse import sse_consumer
from .runs import FrontendRunConflictError, FrontendRunService, RunRecord


class RunCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    thread_id: str | None = None


class RunResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    created_at: str
    updated_at: str
    error: str | None = None


def create_app(
    *,
    fake: bool = False,
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings or load_settings()
    service = FrontendRunService(settings=active_settings, fake=fake)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.frontend_run_service = service
        yield

    app = FastAPI(
        title="coding-deepgent frontend gateway",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "coding-deepgent-frontend-gateway"}

    @app.post("/api/runs", response_model=RunResponse)
    async def create_run(body: RunCreateRequest) -> RunResponse:
        record = _start_run(service, body)
        return _record_to_response(record)

    @app.post("/api/runs/stream")
    async def stream_run(body: RunCreateRequest) -> StreamingResponse:
        record = _start_run(service, body)
        return StreamingResponse(
            sse_consumer(service.bridge, record.run_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Location": f"/api/runs/{record.run_id}",
            },
        )

    @app.get("/api/runs/{run_id}", response_model=RunResponse)
    async def get_run(run_id: str) -> RunResponse:
        record = service.run_manager.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return _record_to_response(record)

    @app.get("/api/runs/{run_id}/stream")
    async def join_run_stream(
        run_id: str,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        record = service.run_manager.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return StreamingResponse(
            sse_consumer(service.bridge, run_id, last_event_id=last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app


def _start_run(service: FrontendRunService, body: RunCreateRequest) -> RunRecord:
    thread_id = body.thread_id or f"thread-{service.settings.workdir.name}"
    try:
        return service.start_run(thread_id=thread_id, prompt=body.prompt)
    except FrontendRunConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _record_to_response(record: RunRecord) -> RunResponse:
    payload: dict[str, Any] = {
        "run_id": record.run_id,
        "thread_id": record.thread_id,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "error": record.error,
    }
    return RunResponse(**payload)

