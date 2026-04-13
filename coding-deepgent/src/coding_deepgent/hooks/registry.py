from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from coding_deepgent.hooks.events import HookEventName, HookPayload, HookResult

HookCallback = Callable[[HookPayload], HookResult]


@dataclass(slots=True)
class LocalHookRegistry:
    """Small sync hook registry for deterministic local lifecycle hooks."""

    _hooks: dict[HookEventName, list[HookCallback]] = field(default_factory=dict)

    def register(self, event: HookEventName, callback: HookCallback) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def run(self, payload: HookPayload) -> list[HookResult]:
        return [callback(payload) for callback in self._hooks.get(payload.event, [])]

    def has_hooks(self, event: HookEventName) -> bool:
        return bool(self._hooks.get(event))
