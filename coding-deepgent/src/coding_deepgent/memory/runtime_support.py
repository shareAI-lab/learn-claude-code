from __future__ import annotations

from coding_deepgent.memory.service import MemoryService


def runtime_memory_service(runtime: object) -> MemoryService | None:
    context = getattr(runtime, "context", None)
    service = getattr(context, "memory_service", None)
    return service if isinstance(service, MemoryService) else None


def runtime_project_scope(runtime: object) -> str:
    context = getattr(runtime, "context", None)
    workdir = getattr(context, "workdir", None)
    if workdir is None:
        return "default"
    return str(workdir)


def runtime_agent_scope(runtime: object) -> str | None:
    context = getattr(runtime, "context", None)
    agent_name = getattr(context, "agent_name", None)
    entrypoint = getattr(context, "entrypoint", "")
    if not isinstance(agent_name, str) or not agent_name:
        return None
    if isinstance(entrypoint, str) and (
        entrypoint.startswith("run_subagent:") or entrypoint == "run_fork"
    ):
        return agent_name
    return None
