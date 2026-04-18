from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

PROMPT_DUMP_ENV = "CODING_DEEPGENT_DUMP_PROMPTS"
PROMPT_DUMP_DIR = ".coding-deepgent/prompt-dumps"
MAX_DUMP_STRING_CHARS = 20_000
MAX_DUMP_SEQUENCE_ITEMS = 200

_SECRET_NAME_PARTS = ("api_key", "token", "secret", "password", "authorization")


def prompt_dump_enabled(env: Mapping[str, str] | None = None) -> bool:
    active_env = env or os.environ
    return active_env.get(PROMPT_DUMP_ENV, "").strip() == "1"


def dump_model_request_if_enabled(
    context: object,
    *,
    request: object,
    messages: Sequence[object],
    input_token_estimate: int | None = None,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    if not prompt_dump_enabled(env):
        return None
    workdir = getattr(context, "workdir", None)
    if not isinstance(workdir, Path):
        return None
    path = _dump_path(context)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "record_type": "model_request",
        "version": 1,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "session_id": str(getattr(context, "session_id", "unknown")),
        "agent_name": str(getattr(context, "agent_name", "unknown")),
        "entrypoint": str(getattr(context, "entrypoint", "unknown")),
        "model": type(getattr(request, "model", None)).__name__,
        "input_token_estimate": input_token_estimate,
        "system_message": _message_payload(getattr(request, "system_message", None)),
        "messages": [_message_payload(message) for message in messages],
        "tool_names": _tool_names(getattr(request, "tools", ())),
        "tool_choice": _safe_value(getattr(request, "tool_choice", None)),
        "model_settings": _safe_value(getattr(request, "model_settings", {})),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str))
        handle.write("\n")
    return path


def _dump_path(context: object) -> Path:
    workdir = getattr(context, "workdir")
    session_id = _safe_path_part(str(getattr(context, "session_id", "unknown")))
    agent_name = _safe_path_part(str(getattr(context, "agent_name", "agent")))
    return workdir / PROMPT_DUMP_DIR / f"{session_id}__{agent_name}.jsonl"


def _safe_path_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return cleaned.strip(".-") or "unknown"


def _message_payload(message: object) -> dict[str, object] | None:
    if message is None:
        return None
    if isinstance(message, dict):
        payload = {
            "role": _safe_value(message.get("role")),
            "content": _safe_value(message.get("content")),
        }
        if "tool_calls" in message:
            payload["tool_calls"] = _safe_value(message.get("tool_calls"))
        return payload
    payload = {
        "type": str(getattr(message, "type", type(message).__name__)),
        "content": _safe_value(getattr(message, "content", "")),
    }
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        payload["tool_calls"] = _safe_value(tool_calls)
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        payload["tool_call_id"] = _safe_value(tool_call_id)
    return payload


def _tool_names(tools: object) -> list[str]:
    if not isinstance(tools, Sequence) or isinstance(tools, (str, bytes, bytearray)):
        return []
    names: list[str] = []
    for tool in tools[:MAX_DUMP_SEQUENCE_ITEMS]:
        name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
        names.append(str(name or type(tool).__name__))
    return names


def _safe_value(value: object, *, field_name: str = "") -> object:
    if any(part in field_name.lower() for part in _SECRET_NAME_PARTS):
        return "<redacted>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= MAX_DUMP_STRING_CHARS:
            return value
        return {
            "text": value[:MAX_DUMP_STRING_CHARS],
            "truncated": True,
            "original_chars": len(value),
        }
    if isinstance(value, Mapping):
        return {
            str(key): _safe_value(item, field_name=str(key))
            for key, item in list(value.items())[:MAX_DUMP_SEQUENCE_ITEMS]
        }
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [
            _safe_value(item, field_name=field_name)
            for item in list(value)[:MAX_DUMP_SEQUENCE_ITEMS]
        ]
    return str(value)
