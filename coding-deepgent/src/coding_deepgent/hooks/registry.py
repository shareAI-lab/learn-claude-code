from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from coding_deepgent.hooks.events import HookEventName, HookPayload, HookResult

HookCallback = Callable[[HookPayload], HookResult]


@dataclass(frozen=True, slots=True)
class HookDispatchOutcome:
    results: tuple[HookResult, ...]
    blocked: bool
    reason: str | None = None
    additional_context: tuple[str, ...] = ()


@dataclass(slots=True)
class LocalHookRegistry:
    """Small sync hook registry for deterministic local lifecycle hooks."""

    _hooks: dict[HookEventName, list[HookCallback]] = field(default_factory=dict)

    def register(self, event: HookEventName, callback: HookCallback) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def run(self, payload: HookPayload) -> list[HookResult]:
        return [callback(payload) for callback in self._hooks.get(payload.event, [])]

    def dispatch(self, payload: HookPayload) -> HookDispatchOutcome:
        results = tuple(self.run(payload))
        blocked_result = next(
            (
                result
                for result in results
                if result.continue_ is False or result.decision == "block"
            ),
            None,
        )
        additional_context = tuple(
            result.additional_context
            for result in results
            if result.additional_context is not None
        )
        return HookDispatchOutcome(
            results=results,
            blocked=blocked_result is not None,
            reason=blocked_result.reason if blocked_result is not None else None,
            additional_context=additional_context,
        )

    def has_hooks(self, event: HookEventName) -> bool:
        return bool(self._hooks.get(event))
