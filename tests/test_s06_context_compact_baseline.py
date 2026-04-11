from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
from typing import Any

import pytest


s06 = pytest.importorskip("agents_deepagents.s06_context_compact")

EXPECTED_SOURCE_BACKED = {
    "apply_tool_result_budget",
    "microcompact_messages",
    "auto_compact_if_needed",
    "reactive_compact_on_overflow",
}
EXPECTED_INFERRED = {
    "snip_projection",
    "context_collapse",
}
EXPECTED_SIMPLIFICATION_SNIPPETS = {
    "cache",
    "telemetry",
    "session",
    "snip",
    "contextCollapse",
}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj: Any, name: str, value: Any) -> None:
    if isinstance(obj, dict):
        obj[name] = value
        return
    try:
        setattr(obj, name, value)
    except (AttributeError, dataclasses.FrozenInstanceError):
        object.__setattr__(obj, name, value)


def _has(obj: Any, name: str) -> bool:
    if isinstance(obj, dict):
        return name in obj
    return hasattr(obj, name)


def _call_with_supported_kwargs(func: Any, /, *args: Any, **kwargs: Any) -> Any:
    supported = inspect.signature(func).parameters
    filtered = {name: value for name, value in kwargs.items() if name in supported}
    return func(*args, **filtered)


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_message_text(item) for item in content)
    if isinstance(content, dict):
        return _message_text(content.get("text") or content.get("content") or "")
    return str(content)


def _message_content(message: Any) -> str:
    return _message_text(_get(message, "content", ""))


def _boundary_kind(boundary: Any) -> str:
    return str(
        _get(boundary, "kind", _get(boundary, "type", _get(boundary, "name", boundary)))
    )


def _tool_call_id(message: Any) -> str | None:
    return _get(
        message,
        "tool_call_id",
        _get(message, "tool_use_id", _get(message, "id")),
    )


def _make_message(
    role: str,
    content: str,
    *,
    kind: str = "text",
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> Any:
    message_cls = getattr(s06, "ContextMessage", None)
    payload = {
        "role": role,
        "content": content,
        "kind": kind,
        "type": kind,
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "name": tool_name,
    }
    if message_cls is None:
        return payload

    params = inspect.signature(message_cls).parameters
    kwargs = {}
    for name in params:
        if name == "self":
            continue
        if name == "is_tool_result":
            kwargs[name] = kind == "tool_result"
        elif name in {"tool_result", "is_compactable"}:
            kwargs[name] = kind == "tool_result"
        elif name in payload and payload[name] is not None:
            kwargs[name] = payload[name]
        elif name == "text":
            kwargs[name] = content

    try:
        return message_cls(**kwargs)
    except TypeError:
        return payload


def _make_state(messages: list[Any]) -> Any:
    state_cls = getattr(s06, "ContextCompressionState")
    defaults = {
        "messages": list(messages),
        "persisted_outputs": [],
        "replacement_decisions": {},
        "compact_boundaries": [],
        "summaries": [],
        "transitions": [],
    }
    try:
        params = inspect.signature(state_cls).parameters
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        params = {}

    kwargs = {name: value for name, value in defaults.items() if name in params}
    try:
        state = state_cls(**kwargs)
    except TypeError:
        state = state_cls()

    for name, value in defaults.items():
        current = _get(state, name, None)
        if current in (None, [], {}):
            _set(state, name, value.copy() if isinstance(value, list) else dict(value) if isinstance(value, dict) else value)
    return state


def _unwrap_state(result: Any, fallback_state: Any) -> tuple[Any, list[Any] | None]:
    state = fallback_state
    model_messages = None

    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, list):
                model_messages = item
            elif _has(item, "messages"):
                state = item
    elif isinstance(result, list):
        model_messages = result
    elif _has(result, "messages"):
        state = result

    if model_messages is None:
        for name in ("model_messages", "projected_messages", "visible_messages"):
            candidate = _get(state, name, None)
            if candidate is not None:
                model_messages = candidate
                break

    return state, model_messages


def _tool_messages_for(*tool_names: str) -> list[Any]:
    result = []
    for index, tool_name in enumerate(tool_names, start=1):
        result.extend(
            [
                _make_message("assistant", f"{tool_name} request {index}", kind="tool_use", tool_call_id=f"call-{index}", tool_name=tool_name),
                _make_message("tool", f"{tool_name} result {index}", kind="tool_result", tool_call_id=f"call-{index}", tool_name=tool_name),
            ]
        )
    return result


def test_s06_exports_stage_metadata_and_functions() -> None:
    assert set(getattr(s06, "SOURCE_BACKED_STAGES")) == EXPECTED_SOURCE_BACKED
    assert set(getattr(s06, "INFERRED_STAGES")) == EXPECTED_INFERRED
    simplifications = {str(item) for item in getattr(s06, "INTENTIONAL_SIMPLIFICATIONS")}
    for snippet in EXPECTED_SIMPLIFICATION_SNIPPETS:
        assert any(snippet in item for item in simplifications)

    for name in EXPECTED_SOURCE_BACKED | EXPECTED_INFERRED:
        assert hasattr(s06, name)


def test_apply_tool_result_budget_persists_large_output(tmp_path: Path) -> None:
    stage = getattr(s06, "apply_tool_result_budget")
    state = _make_state(
        [
            _make_message("user", "inspect the repository"),
            _make_message(
                "tool",
                "A" * 80000,
                kind="tool_result",
                tool_call_id="call-large",
                tool_name="bash",
            ),
        ]
    )

    result = _call_with_supported_kwargs(
        stage,
        state,
        storage_dir=tmp_path / "tool-results",
        persist_dir=tmp_path / "tool-results",
        tool_results_dir=tmp_path / "tool-results",
        preview_chars=96,
        per_result_budget=512,
        tool_result_budget=512,
    )
    state, _ = _unwrap_state(result, state)

    message_text = "\n".join(_message_content(message) for message in _get(state, "messages", []))
    assert "<persisted-output>" in message_text

    persisted_outputs = list(_get(state, "persisted_outputs", []))
    assert persisted_outputs, "expected persisted output metadata"
    stored_path = Path(_get(persisted_outputs[0], "path", _get(persisted_outputs[0], "file_path")))
    assert stored_path.exists()
    assert stored_path.read_text().startswith("A")


def test_aggregate_budget_reuses_frozen_replacement_decisions(tmp_path: Path) -> None:
    first_state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Need two tool results"),
            message(
                "t-small",
                "tool",
                "S" * 80,
                name="bash",
                tool_call_id="tool-small",
                group_id="round-1",
            ),
            message(
                "t-large",
                "tool",
                "L" * 140,
                name="read_file",
                tool_call_id="tool-large",
                group_id="round-1",
            ),
        ]
    )
    first_result = s06.apply_tool_result_budget(
        first_state,
        storage_dir=tmp_path,
        per_tool_threshold=999,
        per_message_budget=210,
        preview_chars=50,
    )

    assert "tool-large" in first_result.replacement_decisions

    second_state = s06.ContextCompressionState(
        messages=[
            message("u2", "user", "Replay the same round"),
            message(
                "t-small-2",
                "tool",
                "S" * 80,
                name="bash",
                tool_call_id="tool-small",
                group_id="round-2",
            ),
            message(
                "t-large-2",
                "tool",
                "L" * 140,
                name="read_file",
                tool_call_id="tool-large",
                group_id="round-2",
            ),
        ],
        persisted_outputs=first_result.persisted_outputs,
        replacement_decisions=first_result.replacement_decisions,
    )
    second_result = s06.apply_tool_result_budget(
        second_state,
        storage_dir=tmp_path,
        per_tool_threshold=999,
        per_message_budget=500,
        preview_chars=50,
    )

    assert second_result.model_messages[2].content.startswith("<persisted-output>")


def test_snip_projection_preserves_canonical_history() -> None:
    state = s06.ContextCompressionState(
        messages=[
            message(f"m{index}", "user" if index % 2 else "assistant", f"msg {index}")
            for index in range(1, 9)
        ]
    )

    result = _call_with_supported_kwargs(
        stage,
        state,
        storage_dir=tmp_path / "tool-results",
        persist_dir=tmp_path / "tool-results",
        tool_results_dir=tmp_path / "tool-results",
        preview_chars=64,
        total_budget=2048,
        aggregate_budget=2048,
        message_budget=2048,
    )
    state, _ = _unwrap_state(result, state)
    decisions = dict(_get(state, "replacement_decisions", {}))
    assert decisions
    assert {"call-big-1", "call-big-2"} & set(decisions)

    rerun = _call_with_supported_kwargs(
        stage,
        state,
        storage_dir=tmp_path / "tool-results",
        persist_dir=tmp_path / "tool-results",
        tool_results_dir=tmp_path / "tool-results",
    )
    rerun_state, _ = _unwrap_state(rerun, state)
    rerun_decisions = dict(_get(rerun_state, "replacement_decisions", {}))
    assert decisions == rerun_decisions


def test_snip_projection_keeps_source_history_but_shrinks_model_view() -> None:
    stage = getattr(s06, "snip_projection")
    messages = [
        _make_message("user", "first user message " + "u" * 4000),
        _make_message("assistant", "first assistant message " + "a" * 4000),
        _make_message("user", "latest user request"),
        _make_message("assistant", "latest assistant reply"),
    ]
    state = _make_state(messages)

    result = _call_with_supported_kwargs(
        stage,
        state,
        max_chars=1024,
        threshold=1024,
        keep_recent=2,
    )
    state, model_messages = _unwrap_state(result, state)

    assert len(_get(state, "messages")) == len(messages)
    assert "first user message" in _message_content(_get(state, "messages")[0])
    assert model_messages is not None
    assert len(model_messages) <= len(messages)
    assert any("snip" in _boundary_kind(boundary).lower() for boundary in _get(state, "compact_boundaries", []))


def test_microcompact_messages_replaces_older_compactable_tool_results() -> None:
    stage = getattr(s06, "microcompact_messages")
    messages = [
        _make_message("user", "compact old outputs"),
        _make_message("tool", "old bash output " + "b" * 2000, kind="tool_result", tool_call_id="call-1", tool_name="bash"),
        _make_message("tool", "old read output " + "r" * 2000, kind="tool_result", tool_call_id="call-2", tool_name="read_file"),
        _make_message("tool", "recent grep output " + "g" * 2000, kind="tool_result", tool_call_id="call-3", tool_name="grep"),
    ]
    state = _make_state(messages)

    result = _call_with_supported_kwargs(
        stage,
        state,
        keep_recent=1,
        keep_recent_results=1,
        recent_to_keep=1,
    )
    state, _ = _unwrap_state(result, state)
    compacted_messages = _get(state, "messages")

    assert len(_message_content(compacted_messages[1])) < len(_message_content(messages[1]))
    assert len(_message_content(compacted_messages[2])) < len(_message_content(messages[2]))
    assert "recent grep output" in _message_content(compacted_messages[3])
    assert any("micro" in _boundary_kind(boundary).lower() for boundary in _get(state, "compact_boundaries", []))


def test_context_collapse_summarizes_older_groups_without_splitting_tool_pairs() -> None:
    stage = getattr(s06, "context_collapse")
    messages = [
        _make_message("user", "old task"),
        *_tool_messages_for("bash"),
        _make_message("assistant", "old follow-up"),
        _make_message("user", "recent task"),
        *_tool_messages_for("read_file"),
        _make_message("assistant", "recent follow-up"),
    ]
    state = _make_state(messages)

    result = _call_with_supported_kwargs(
        stage,
        state,
        summarizer=lambda batch: "collapse-summary::" + "|".join(
            filter(None, (_tool_call_id(message) for message in batch))
        ),
        collapse_threshold=1,
        keep_recent_groups=1,
        max_chars=256,
    )
    state, model_messages = _unwrap_state(result, state)

    assert _get(state, "summaries"), "expected stored collapse summary"
    if model_messages is not None:
        old_pair_ids = {
            _tool_call_id(message)
            for message in messages
            if _tool_call_id(message) in {"call-1"}
        }
        visible_old_pair_ids = {
            _tool_call_id(message)
            for message in model_messages
            if _tool_call_id(message) in old_pair_ids
        }
        assert visible_old_pair_ids in (set(), old_pair_ids)
        assert any("recent task" in _message_content(message) for message in model_messages)


def test_auto_compact_if_needed_returns_summary_plus_recent_context() -> None:
    stage = getattr(s06, "auto_compact_if_needed")
    messages = [
        _make_message("user", "history " + "h" * 5000),
        _make_message("assistant", "response " + "r" * 5000),
        _make_message("user", "keep me recent"),
    ]
    state = _make_state(messages)

    result = _call_with_supported_kwargs(
        stage,
        state,
        summarizer=lambda batch: "auto-summary",
        threshold=256,
        max_chars=256,
        keep_recent=1,
    )
    state, model_messages = _unwrap_state(result, state)

    assert _get(state, "summaries"), "expected compact summary"
    joined_visible = "\n".join(_message_content(message) for message in (model_messages or []))
    assert "auto-summary" in joined_visible or any(
        "auto-summary" in str(item) for item in _get(state, "summaries", [])
    )
    assert "keep me recent" in joined_visible or "keep me recent" in _message_content(_get(state, "messages")[-1])
    assert any("compact" in _boundary_kind(boundary).lower() for boundary in _get(state, "compact_boundaries", []))


def test_reactive_compact_on_overflow_attempts_collapse_before_full_compact() -> None:
    collapse = getattr(s06, "context_collapse")
    reactive = getattr(s06, "reactive_compact_on_overflow")
    messages = [
        _make_message("user", "very old task " + "o" * 5000),
        *_tool_messages_for("bash"),
        _make_message("assistant", "old analysis " + "a" * 5000),
        _make_message("user", "recent task " + "r" * 5000),
        _make_message("assistant", "recent analysis " + "b" * 5000),
    ]
    state = _make_state(messages)

    collapsed = _call_with_supported_kwargs(
        collapse,
        state,
        summarizer=lambda batch: "collapse-summary",
        collapse_threshold=1,
        keep_recent_groups=1,
        max_chars=256,
    )
    collapsed_state, _ = _unwrap_state(collapsed, state)

    result = _call_with_supported_kwargs(
        reactive,
        collapsed_state,
        RuntimeError("prompt too long"),
        exception=RuntimeError("prompt too long"),
        error=RuntimeError("prompt too long"),
        summarizer=lambda batch: "reactive-summary",
        threshold=64,
        max_chars=64,
        keep_recent=1,
    )
    recovered_state, _ = _unwrap_state(result, collapsed_state)

    transitions = [str(item) for item in _get(recovered_state, "transitions", [])]
    assert transitions, "expected recovery transition metadata"
    collapse_indexes = [
        index for index, item in enumerate(transitions) if "collapse" in item.lower()
    ]
    reactive_indexes = [
        index for index, item in enumerate(transitions) if "reactive" in item.lower()
    ]
    assert collapse_indexes, "expected collapse-drain attempt before fallback"
    if reactive_indexes:
        assert min(collapse_indexes) < min(reactive_indexes)
