from __future__ import annotations

from enum import StrEnum


class RuntimeAgentRole(StrEnum):
    MAIN = "main"
    SUBAGENT = "subagent"
    FORK = "fork"
    COORDINATOR = "coordinator"
    WORKER = "worker"


CURRENT_RUNTIME_ROLES = (
    RuntimeAgentRole.MAIN,
    RuntimeAgentRole.SUBAGENT,
    RuntimeAgentRole.FORK,
)
FUTURE_TEAM_RUNTIME_ROLES = (
    RuntimeAgentRole.COORDINATOR,
    RuntimeAgentRole.WORKER,
)
