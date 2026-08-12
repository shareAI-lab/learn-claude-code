"""Thread-safe ordered tool registration and per-round snapshots."""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True)
class ToolRegistry:
    _tools: dict[str, dict] = field(default_factory=dict)
    _handlers: dict[str, Callable | None] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def register(self, schema: dict, handler: Callable | None = None) -> None:
        name = schema.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("tool schema requires a name")
        with self._lock:
            if name in self._tools:
                raise ValueError(f"duplicate tool registration: {name}")
            self._tools[name] = copy.deepcopy(schema)
            self._handlers[name] = handler

    def snapshot(self) -> tuple[list[dict], dict[str, Callable]]:
        with self._lock:
            tools = [copy.deepcopy(schema) for schema in self._tools.values()]
            handlers = {
                name: handler
                for name, handler in self._handlers.items()
                if handler is not None
            }
        return tools, handlers
