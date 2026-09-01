"""Structured execution tracing for the integrated harness.

The module deliberately has no dependency on the harness implementation.  A
TraceRecorder is created only by a CLI entry point; importing a lesson keeps
using NullTraceRecorder and therefore creates no files.
"""

from __future__ import annotations

import atexit
import contextlib
import contextvars
import hashlib
import importlib.metadata
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


SCHEMA_VERSION = "1.0"
DEFAULT_PREVIEW_CHARS = 500
DEFAULT_ARGUMENT_CHARS = 2048
_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|credential|password|secret|"
    r"(?:access|auth|bearer|refresh)[_-]?token|^token$)",
    re.IGNORECASE,
)
_SECRET_TEXT_PATTERNS = (
    re.compile(r"(?i)(\bauthorization\s*:\s*bearer\s+)[^\s,'\";]+"),
    re.compile(
        r"(?i)(\b(?:[a-z0-9]+[_-])*(?:api[_-]?key|authorization|credential|password|secret|"
        r"(?:access|auth|bearer|refresh)[_-]?token)\b\s*[:=]\s*)"
        r"(?:['\"]?)[^\s,'\";]+"
    ),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(://)[^/@\s:]+:[^/@\s]+@"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return dict(value.__dict__)
        except Exception:
            pass
    return str(value)


def _json_text(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=True, sort_keys=True, default=_json_default
        )
    except Exception:
        return repr(value)


def _redact_text(value: str) -> str:
    redacted = value
    for index, pattern in enumerate(_SECRET_TEXT_PATTERNS):
        if index in {0, 1}:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        elif index == 2:
            redacted = pattern.sub("[REDACTED]", redacted)
        else:
            redacted = pattern.sub(r"\1[REDACTED]@", redacted)
    return redacted


def _block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


@dataclass
class SpanHandle:
    recorder: "BaseTraceRecorder"
    start_event: str
    end_event: str
    span_id: str | None = None
    started_ns: int = 0
    end_data: dict[str, Any] = field(default_factory=dict)
    _token: contextvars.Token | None = None

    def finish(self, **data: Any) -> None:
        self.end_data.update(data)


class BaseTraceRecorder:
    enabled = False
    run_id: str | None = None
    path: Path | None = None

    def new_id(self, prefix: str) -> str:
        return f"{prefix}_000000"

    def emit(self, event: str, data: dict[str, Any] | None = None, **_: Any) -> str:
        return "evt_000000"

    @contextlib.contextmanager
    def span(
        self,
        start_event: str,
        end_event: str,
        data: dict[str, Any] | None = None,
        **_: Any,
    ) -> Iterator[SpanHandle]:
        yield SpanHandle(self, start_event, end_event)

    @contextlib.contextmanager
    def turn_scope(self, _turn_id: str | None) -> Iterator[None]:
        yield

    @contextlib.contextmanager
    def agent_scope(
        self,
        _agent_id: str | None,
        _parent_agent_id: str | None = None,
        _agent_kind: str | None = None,
    ) -> Iterator[None]:
        yield

    @contextlib.contextmanager
    def model_scope(self, _purpose: str) -> Iterator[None]:
        yield

    @contextlib.contextmanager
    def restore_context(self, _context: dict[str, Any]) -> Iterator[None]:
        yield

    def capture_context(self) -> dict[str, Any]:
        return {}

    def current_agent_id(self) -> str | None:
        return None

    def current_parent_agent_id(self) -> str | None:
        return None

    def current_turn_id(self) -> str | None:
        return None

    def current_span_id(self) -> str | None:
        return None

    def safe_value(self, value: Any, max_chars: int | None = None) -> Any:
        return value

    def summarize_output(self, value: Any) -> dict[str, Any]:
        return {}

    def finish_run(self, status: str = "completed", **data: Any) -> None:
        return None


class NullTraceRecorder(BaseTraceRecorder):
    """No-op recorder used for imports, tests, and HARNESS_TRACE=0."""


class TraceRecorder(BaseTraceRecorder):
    enabled = True

    def __init__(
        self,
        directory: Path,
        runtime_name: str,
        run_data: dict[str, Any] | None = None,
        output_mode: str = "summary",
        preview_chars: int = DEFAULT_PREVIEW_CHARS,
        argument_chars: int = DEFAULT_ARGUMENT_CHARS,
    ):
        directory.mkdir(parents=True, exist_ok=True)
        self.run_id = f"run_{uuid.uuid4().hex[:8]}"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        self.path = directory / f"run_{stamp}_{self.run_id.removeprefix('run_')}.jsonl"
        self.runtime_name = runtime_name
        self.output_mode = output_mode if output_mode in {"summary", "full"} else "summary"
        self.preview_chars = max(0, preview_chars)
        self.argument_chars = max(0, argument_chars)
        self._started_ns = time.perf_counter_ns()
        self._lock = threading.RLock()
        self._counters: dict[str, int] = {}
        self._closed = False
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_EXCL,
            0o600,
        )
        self._handle = os.fdopen(
            descriptor, "a", encoding="utf-8", buffering=1
        )
        self._turn_id = contextvars.ContextVar(
            f"trace_turn_{id(self)}", default=None
        )
        self._agent_id = contextvars.ContextVar(
            f"trace_agent_{id(self)}", default=None
        )
        self._parent_agent_id = contextvars.ContextVar(
            f"trace_parent_agent_{id(self)}", default=None
        )
        self._agent_kind = contextvars.ContextVar(
            f"trace_agent_kind_{id(self)}", default=None
        )
        self._span_id = contextvars.ContextVar(
            f"trace_span_{id(self)}", default=None
        )
        self._model_purpose = contextvars.ContextVar(
            f"trace_model_purpose_{id(self)}", default="unspecified"
        )
        atexit.register(self.finish_run, "process_exit")
        payload = {
            "runtime": runtime_name,
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
            "output_mode": self.output_mode,
            "packages": {
                "anthropic": _package_version("anthropic"),
                "python": os.sys.version.split()[0],
            },
        }
        payload.update(run_data or {})
        self.emit("run_start", payload)

    def new_id(self, prefix: str) -> str:
        with self._lock:
            value = self._counters.get(prefix, 0) + 1
            self._counters[prefix] = value
        return f"{prefix}_{value:06d}"

    def _write(self, record: dict[str, Any]) -> None:
        with self._lock:
            if self._closed:
                return
            self._handle.write(
                json.dumps(record, ensure_ascii=True, default=_json_default) + "\n"
            )
            self._handle.flush()

    def emit(
        self,
        event: str,
        data: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
        parent_agent_id: str | None = None,
        agent_kind: str | None = None,
        turn_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        caused_by_event_id: str | None = None,
        depends_on_event_ids: list[str] | None = None,
    ) -> str:
        now_ns = time.perf_counter_ns()
        event_id = self.new_id("evt")
        record = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": _utc_now(),
            "monotonic_ns": now_ns,
            "elapsed_ms": round((now_ns - self._started_ns) / 1_000_000, 3),
            "run_id": self.run_id,
            "turn_id": turn_id if turn_id is not None else self._turn_id.get(),
            "event_id": event_id,
            "event": event,
            "agent_id": agent_id if agent_id is not None else self._agent_id.get(),
            "parent_agent_id": (
                parent_agent_id
                if parent_agent_id is not None
                else self._parent_agent_id.get()
            ),
            "agent_kind": agent_kind if agent_kind is not None else self._agent_kind.get(),
            "span_id": span_id,
            "parent_span_id": (
                parent_span_id
                if parent_span_id is not None
                else self._span_id.get()
            ),
            "caused_by_event_id": caused_by_event_id,
            "depends_on_event_ids": depends_on_event_ids or [],
            "thread": {
                "id": threading.get_ident(),
                "name": threading.current_thread().name,
            },
            "data": self.safe_value(data or {}, max_chars=self.argument_chars),
        }
        self._write(record)
        return event_id

    @contextlib.contextmanager
    def span(
        self,
        start_event: str,
        end_event: str,
        data: dict[str, Any] | None = None,
        *,
        span_id: str | None = None,
        agent_id: str | None = None,
        parent_agent_id: str | None = None,
        caused_by_event_id: str | None = None,
    ) -> Iterator[SpanHandle]:
        span_id = span_id or self.new_id("span")
        parent_span = self._span_id.get()
        started_ns = time.perf_counter_ns()
        start_id = self.emit(
            start_event,
            data,
            agent_id=agent_id,
            parent_agent_id=parent_agent_id,
            span_id=span_id,
            parent_span_id=parent_span,
            caused_by_event_id=caused_by_event_id,
        )
        token = self._span_id.set(span_id)
        handle = SpanHandle(
            self,
            start_event,
            end_event,
            span_id=span_id,
            started_ns=started_ns,
            _token=token,
        )
        try:
            yield handle
        except BaseException as exc:
            handle.end_data.setdefault("status", "error")
            handle.end_data.setdefault("error_type", type(exc).__name__)
            handle.end_data.setdefault("error", str(exc))
            raise
        finally:
            duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
            handle.end_data.setdefault("status", "ok")
            handle.end_data["duration_ms"] = round(duration_ms, 3)
            self._span_id.reset(token)
            self.emit(
                handle.end_event,
                handle.end_data,
                agent_id=agent_id,
                parent_agent_id=parent_agent_id,
                span_id=span_id,
                parent_span_id=parent_span,
                caused_by_event_id=start_id,
            )

    @contextlib.contextmanager
    def turn_scope(self, turn_id: str | None) -> Iterator[None]:
        token = self._turn_id.set(turn_id)
        try:
            yield
        finally:
            self._turn_id.reset(token)

    @contextlib.contextmanager
    def agent_scope(
        self,
        agent_id: str | None,
        parent_agent_id: str | None = None,
        agent_kind: str | None = None,
    ) -> Iterator[None]:
        agent_token = self._agent_id.set(agent_id)
        parent_token = self._parent_agent_id.set(parent_agent_id)
        kind_token = self._agent_kind.set(agent_kind)
        try:
            yield
        finally:
            self._agent_kind.reset(kind_token)
            self._parent_agent_id.reset(parent_token)
            self._agent_id.reset(agent_token)

    @contextlib.contextmanager
    def model_scope(self, purpose: str) -> Iterator[None]:
        token = self._model_purpose.set(purpose)
        try:
            yield
        finally:
            self._model_purpose.reset(token)

    def capture_context(self) -> dict[str, Any]:
        return {
            "turn_id": self._turn_id.get(),
            "agent_id": self._agent_id.get(),
            "parent_agent_id": self._parent_agent_id.get(),
            "agent_kind": self._agent_kind.get(),
            "span_id": self._span_id.get(),
            "model_purpose": self._model_purpose.get(),
        }

    @contextlib.contextmanager
    def restore_context(self, context: dict[str, Any]) -> Iterator[None]:
        tokens = [
            (self._turn_id, self._turn_id.set(context.get("turn_id"))),
            (self._agent_id, self._agent_id.set(context.get("agent_id"))),
            (
                self._parent_agent_id,
                self._parent_agent_id.set(context.get("parent_agent_id")),
            ),
            (self._agent_kind, self._agent_kind.set(context.get("agent_kind"))),
            (self._span_id, self._span_id.set(context.get("span_id"))),
            (
                self._model_purpose,
                self._model_purpose.set(context.get("model_purpose", "unspecified")),
            ),
        ]
        try:
            yield
        finally:
            for variable, token in reversed(tokens):
                variable.reset(token)

    def current_agent_id(self) -> str | None:
        return self._agent_id.get()

    def current_parent_agent_id(self) -> str | None:
        return self._parent_agent_id.get()

    def current_turn_id(self) -> str | None:
        return self._turn_id.get()

    def current_span_id(self) -> str | None:
        return self._span_id.get()

    def model_purpose(self) -> str:
        return self._model_purpose.get()

    def safe_value(self, value: Any, max_chars: int | None = None) -> Any:
        max_chars = self.argument_chars if max_chars is None else max_chars
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                key_text = str(key)
                if _SECRET_KEY.search(key_text):
                    result[key_text] = "[REDACTED]"
                else:
                    result[key_text] = self.safe_value(item, max_chars=max_chars)
            return result
        if isinstance(value, (list, tuple)):
            return [self.safe_value(item, max_chars=max_chars) for item in value]
        if isinstance(value, set):
            return [self.safe_value(item, max_chars=max_chars) for item in sorted(value, key=str)]
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        if isinstance(value, str):
            redacted = _redact_text(value)
            if len(value) > max_chars:
                return {
                    "characters": len(value),
                    "sha256": hashlib.sha256(redacted.encode("utf-8")).hexdigest(),
                    "preview": redacted[:max_chars],
                    "truncated": True,
                }
            return redacted
        if value is None or isinstance(value, (int, float, bool)):
            return value
        return self.safe_value(_json_default(value), max_chars=max_chars)

    def summarize_output(self, value: Any) -> dict[str, Any]:
        text = value if isinstance(value, str) else _json_text(value)
        redacted = _redact_text(text)
        summary = {
            "characters": len(text),
            "sha256": hashlib.sha256(redacted.encode("utf-8")).hexdigest(),
            "preview": redacted[: self.preview_chars],
            "truncated": len(text) > self.preview_chars,
        }
        if self.output_mode == "full":
            summary["full"] = self.safe_value(redacted, max_chars=max(len(redacted), 1))
        return summary

    def finish_run(self, status: str = "completed", **data: Any) -> None:
        with self._lock:
            if self._closed:
                return
            payload = {"status": status, **data}
            # Keep the closed check, final record, and close atomic. RLock lets
            # emit() and _write() safely acquire this same lock recursively.
            self.emit("run_end", payload)
            self._closed = True
            self._handle.flush()
            self._handle.close()


class TracedMessages:
    def __init__(self, raw_messages: Any, recorder: BaseTraceRecorder):
        self._raw_messages = raw_messages
        self._recorder = recorder

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_messages, name)

    def create(self, **kwargs: Any) -> Any:
        recorder = self._recorder
        messages = kwargs.get("messages", [])
        system = kwargs.get("system", "")
        context_chars = len(_json_text(messages)) + len(_json_text(system))
        request_data = {
            "purpose": (
                recorder.model_purpose()
                if isinstance(recorder, TraceRecorder)
                else "unspecified"
            ),
            "model": kwargs.get("model"),
            "message_count": len(messages) if isinstance(messages, list) else None,
            "context_characters": context_chars,
            "tool_count": len(kwargs.get("tools", []) or []),
            "max_tokens": kwargs.get("max_tokens"),
            "stream": bool(kwargs.get("stream", False)),
        }
        with recorder.span(
            "model_request", "model_response", request_data
        ) as model_span:
            try:
                response = self._raw_messages.create(**kwargs)
            except Exception as exc:
                model_span.end_event = "model_error"
                model_span.finish(
                    status="error",
                    purpose=request_data["purpose"],
                    model=request_data["model"],
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise

            actions = []
            for block in getattr(response, "content", []) or []:
                block_type = _block_value(block, "type", "unknown")
                if block_type == "tool_use":
                    actions.append(
                        {
                            "type": "tool_use",
                            "tool_call_id": _block_value(block, "id"),
                            "tool": _block_value(block, "name"),
                        }
                    )
                elif block_type == "text":
                    actions.append({"type": "text", "present": True})
                elif block_type in {"thinking", "redacted_thinking"}:
                    actions.append({"type": block_type, "present": True})
                else:
                    actions.append({"type": block_type})

            usage = getattr(response, "usage", None)
            usage_data = None
            if usage is not None:
                usage_data = {
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                    "cache_creation_input_tokens": getattr(
                        usage, "cache_creation_input_tokens", None
                    ),
                    "cache_read_input_tokens": getattr(
                        usage, "cache_read_input_tokens", None
                    ),
                }
            model_span.finish(
                status="ok",
                purpose=request_data["purpose"],
                model=request_data["model"],
                stop_reason=getattr(response, "stop_reason", None),
                requested_actions=actions,
                usage=usage_data,
            )
            return response


class TracedClient:
    """Delegate every client attribute except the traced messages API."""

    def __init__(self, raw_client: Any, recorder: BaseTraceRecorder):
        self._raw_client = raw_client
        self.messages = TracedMessages(raw_client.messages, recorder)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_client, name)


def trace_enabled_from_env() -> bool:
    value = os.getenv("HARNESS_TRACE", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def create_recorder(
    workdir: Path,
    runtime_name: str,
    run_data: dict[str, Any] | None = None,
) -> BaseTraceRecorder:
    if not trace_enabled_from_env():
        return NullTraceRecorder()
    directory_value = os.getenv("HARNESS_TRACE_DIR", "traces")
    directory = Path(directory_value)
    if not directory.is_absolute():
        directory = workdir / directory
    output_mode = os.getenv("HARNESS_TRACE_OUTPUT", "summary").strip().lower()
    try:
        preview_chars = int(
            os.getenv("HARNESS_TRACE_PREVIEW_CHARS", str(DEFAULT_PREVIEW_CHARS))
        )
    except ValueError:
        preview_chars = DEFAULT_PREVIEW_CHARS
    return TraceRecorder(
        directory,
        runtime_name,
        run_data=run_data,
        output_mode=output_mode,
        preview_chars=preview_chars,
    )


def wrap_client(client: Any, recorder: BaseTraceRecorder) -> Any:
    if not recorder.enabled or isinstance(client, TracedClient):
        return client
    return TracedClient(client, recorder)
