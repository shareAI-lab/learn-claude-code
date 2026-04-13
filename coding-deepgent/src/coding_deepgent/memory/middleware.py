from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

from coding_deepgent.memory.recall import recall_memories, render_memories
from coding_deepgent.memory.schemas import MemoryNamespace


@dataclass(frozen=True, slots=True)
class MemoryContextMiddleware(AgentMiddleware):
    namespace: MemoryNamespace = "project"
    limit: int = 5

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        store = getattr(request.runtime, "store", None)
        query = " ".join(
            str(message.content)
            for message in request.messages[-3:]
            if hasattr(message, "content")
        )
        memories = recall_memories(
            store, namespace=self.namespace, query=query, limit=self.limit
        )
        rendered = render_memories(memories)
        if not rendered:
            return handler(request)

        current_blocks = (
            request.system_message.content_blocks if request.system_message else []
        )
        return handler(
            request.override(
                system_message=SystemMessage(
                    content=[*current_blocks, {"type": "text", "text": rendered}]  # type: ignore[list-item]
                )
            )
        )
