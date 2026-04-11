from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest

from coding_deepgent.renderers.planning import reminder_text, render_plan_items
from coding_deepgent.state import PlanningState


class PlanningMiddleware(AgentMiddleware[PlanningState]):
    """Render planning state into the prompt and track stale-plan rounds."""

    state_schema = PlanningState

    def __init__(self) -> None:
        super().__init__()
        self._updated_this_turn = False

    def before_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        self._updated_this_turn = False
        return {
            key: value
            for key, value in (("items", []), ("rounds_since_update", 0))
            if key not in state
        } or None

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable):
        if request.tool_call["name"] == "todo":
            self._updated_this_turn = True
        return handler(request)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        items = request.state.get("items", [])
        rounds_since_update = request.state.get("rounds_since_update", 0)
        extra_blocks: list[dict[str, str]] = []

        if items:
            extra_blocks.append(
                {
                    "type": "text",
                    "text": "Current session plan:\n" + render_plan_items(items),
                }
            )
            reminder = reminder_text(items, rounds_since_update)
            if reminder:
                extra_blocks.append({"type": "text", "text": reminder})

        if not extra_blocks:
            return handler(request)

        return handler(
            request.override(
                system_message=SystemMessage(
                    content=[*request.system_message.content_blocks, *extra_blocks]
                )
            )
        )

    def after_model(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_ai_message = next(
            (message for message in reversed(messages) if isinstance(message, AIMessage)),
            None,
        )
        if last_ai_message is None or not last_ai_message.tool_calls:
            return None

        todo_calls = [call for call in last_ai_message.tool_calls if call["name"] == "todo"]
        if len(todo_calls) <= 1:
            return None

        return {
            "messages": [
                ToolMessage(
                    content=(
                        "Error: The `todo` tool should never be called multiple times in "
                        "parallel. Call it once per model response so the session plan has "
                        "one unambiguous replacement."
                    ),
                    tool_call_id=call["id"],
                    status="error",
                )
                for call in todo_calls
            ]
        }

    def after_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        if self._updated_this_turn:
            return None
        if state.get("items"):
            return {"rounds_since_update": state.get("rounds_since_update", 0) + 1}
        return None
