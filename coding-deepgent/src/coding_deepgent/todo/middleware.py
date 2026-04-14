from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest

from coding_deepgent.context_payloads import (
    ContextPayload,
    merge_system_message_content,
)
from coding_deepgent.todo.renderers import reminder_text, render_plan_items
from coding_deepgent.todo.state import PlanningState, TodoItemState

TODO_WRITE_TOOL_NAME = "TodoWrite"


class PlanContextMiddleware(AgentMiddleware[PlanningState]):
    """Render todo state into the prompt and track stale-todo rounds."""

    state_schema = PlanningState

    def __init__(self) -> None:
        super().__init__()
        self._updated_this_turn = False

    def before_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        self._updated_this_turn = False
        return {
            key: value
            for key, value in (("todos", []), ("rounds_since_update", 0))
            if key not in state
        } or None

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable):
        if request.tool_call["name"] == TODO_WRITE_TOOL_NAME:
            self._updated_this_turn = True
        return handler(request)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        todos = cast(list[TodoItemState], request.state.get("todos", []))
        rounds_since_update = cast(int, request.state.get("rounds_since_update", 0))
        payloads: list[ContextPayload] = []

        if todos:
            payloads.append(
                ContextPayload(
                    kind="todo",
                    source="todo.current",
                    priority=100,
                    text="Current session todos:\n" + render_plan_items(todos),
                )
            )
            reminder = reminder_text(todos, rounds_since_update)
            if reminder:
                payloads.append(
                    ContextPayload(
                        kind="todo_reminder",
                        source="todo.reminder",
                        priority=110,
                        text=reminder,
                    )
                )

        if not payloads:
            return handler(request)

        current_blocks = (
            request.system_message.content_blocks
            if request.system_message is not None
            else []
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

    def after_model(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_ai_message = next(
            (
                message
                for message in reversed(messages)
                if isinstance(message, AIMessage)
            ),
            None,
        )
        if last_ai_message is None or not last_ai_message.tool_calls:
            return None

        todo_write_calls = [
            call
            for call in last_ai_message.tool_calls
            if call["name"] == TODO_WRITE_TOOL_NAME
        ]
        if len(todo_write_calls) <= 1:
            return None

        return {
            "messages": [
                ToolMessage(
                    content=(
                        "Error: The `TodoWrite` tool should never be called multiple times in "
                        "parallel. Call it once per model response so the session todos have "
                        "one unambiguous replacement."
                    ),
                    tool_call_id=call["id"],
                    status="error",
                )
                for call in todo_write_calls
            ]
        }

    def after_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        if self._updated_this_turn:
            return None
        if state.get("todos"):
            return {"rounds_since_update": state.get("rounds_since_update", 0) + 1}
        return None
