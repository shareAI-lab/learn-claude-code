"""coding-deepgent public package surface."""

from __future__ import annotations

from typing import Any


__all__ = ["agent_loop", "build_agent"]


def __getattr__(name: str) -> Any:
    if name == "agent_loop":
        from .app import agent_loop

        return agent_loop
    if name == "build_agent":
        from .app import build_agent

        return build_agent
    raise AttributeError(name)
