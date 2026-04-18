from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

from coding_deepgent.context_payloads import (
    ContextPayload,
    merge_system_message_content,
)
from coding_deepgent.sessions.session_memory import (
    read_session_memory_artifact,
    session_memory_status,
)


@dataclass(frozen=True, slots=True)
class SessionMemoryContextMiddleware(AgentMiddleware):
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        artifact = read_session_memory_artifact(request.state)
        if artifact is None:
            return handler(request)

        payloads = [
            ContextPayload(
                kind="memory",
                source="memory.current_session",
                priority=210,
                text=_render_current_session_memory(
                    artifact.content,
                    status=session_memory_status(
                        artifact, current_message_count=len(request.messages)
                    ),
                ),
            )
        ]
        current_blocks = (
            request.system_message.content_blocks if request.system_message else []
        )
        return handler(
            request.override(
                system_message=SystemMessage(
                    content=merge_system_message_content(
                        current_blocks, payloads
                    )  # type: ignore[list-item]
                )
            )
        )


def _render_current_session_memory(content: str, *, status: str) -> str:
    return (
        "Current-session memory:\n"
        f"- [{status}] {content}\n\n"
        "Treat this as the working summary of the active long conversation."
    )
