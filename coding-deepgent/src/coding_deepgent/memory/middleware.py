from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

from coding_deepgent.context_payloads import (
    ContextPayload,
    merge_system_message_content,
)
from coding_deepgent.memory.recall import recall_memories, render_memories
from coding_deepgent.memory.runtime_support import (
    runtime_agent_scope,
    runtime_memory_service,
    runtime_project_scope,
)
from coding_deepgent.memory.schemas import MemoryType
from coding_deepgent.memory.state_snapshot import (
    build_long_term_memory_snapshot,
    build_long_term_memory_snapshot_from_durable_records,
    write_long_term_memory_snapshot,
)


@dataclass(frozen=True, slots=True)
class MemoryContextMiddleware(AgentMiddleware):
    memory_type: MemoryType | None = None
    limit: int = 5
    snapshot_limit: int = 12

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        store = getattr(request.runtime, "store", None)
        service = runtime_memory_service(request.runtime)
        project_scope = runtime_project_scope(request.runtime)
        agent_scope = runtime_agent_scope(request.runtime)
        if hasattr(request.state, "__setitem__"):
            write_long_term_memory_snapshot(
                cast(MutableMapping[str, Any], request.state),
                (
                    build_long_term_memory_snapshot_from_durable_records(
                        service.list_records(project_scope=project_scope, limit=self.snapshot_limit)
                    )
                    if service is not None
                    else build_long_term_memory_snapshot(store, limit=self.snapshot_limit)
                ),
            )
        query = " ".join(
            str(message.content)
            for message in request.messages[-3:]
            if hasattr(message, "content")
        )
        memories = recall_memories(
            store,
            service=service,
            project_scope=project_scope,
            agent_scope=agent_scope,
            memory_type=self.memory_type,
            query=query,
            limit=self.limit,
        )
        rendered = render_memories(memories)
        if not rendered:
            return handler(request)

        current_blocks = (
            request.system_message.content_blocks if request.system_message else []
        )
        payloads = [
            ContextPayload(
                kind="memory",
                source=(
                    f"memory.{self.memory_type}"
                    if self.memory_type is not None
                    else "memory.long_term"
                ),
                priority=200,
                text=rendered,
            )
        ]
        return handler(
            request.override(
                system_message=SystemMessage(
                    content=merge_system_message_content(
                        current_blocks, payloads
                    )  # type: ignore[list-item]
                )
            )
        )
