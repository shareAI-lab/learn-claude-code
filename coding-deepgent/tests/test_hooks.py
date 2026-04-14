from __future__ import annotations

import pytest
from pydantic import ValidationError

from coding_deepgent.hooks import (
    HookDispatchOutcome,
    HookPayload,
    HookResult,
    LocalHookRegistry,
)


def test_local_hook_registry_runs_matching_hooks_in_order() -> None:
    registry = LocalHookRegistry()
    seen: list[str] = []

    def first(payload: HookPayload) -> HookResult:
        seen.append(f"first:{payload.event}")
        return HookResult(reason="first")

    def second(payload: HookPayload) -> HookResult:
        seen.append(f"second:{payload.event}")
        return HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "second"}
        )

    registry.register("PreToolUse", first)
    registry.register("PreToolUse", second)

    results = registry.run(HookPayload(event="PreToolUse", data={"tool": "bash"}))

    assert seen == ["first:PreToolUse", "second:PreToolUse"]
    assert [result.reason for result in results] == ["first", "second"]
    assert results[1].continue_ is False


def test_local_hook_registry_dispatch_aggregates_block_and_context() -> None:
    registry = LocalHookRegistry()

    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult(additional_context="ctx-1"),
    )
    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult.model_validate(
            {
                "continue": False,
                "decision": "block",
                "reason": "blocked",
                "additional_context": "ctx-2",
            }
        ),
    )

    outcome = registry.dispatch(
        HookPayload(event="UserPromptSubmit", data={"message": "hello"})
    )

    assert isinstance(outcome, HookDispatchOutcome)
    assert outcome.blocked is True
    assert outcome.reason == "blocked"
    assert outcome.additional_context == ("ctx-1", "ctx-2")


def test_hook_result_schema_rejects_unknown_fields_and_decisions() -> None:
    with pytest.raises(ValidationError):
        HookResult.model_validate({"decision": "maybe"})
    with pytest.raises(ValidationError):
        HookResult.model_validate({"continue": True, "extra": "nope"})


def test_hook_payload_rejects_unknown_events() -> None:
    with pytest.raises(ValidationError):
        HookPayload.model_validate({"event": "UnknownEvent", "data": {}})
