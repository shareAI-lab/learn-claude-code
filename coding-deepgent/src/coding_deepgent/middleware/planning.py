from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

from coding_deepgent.state import PlanningState
from coding_deepgent.tools.planning import reminder_text, render_plan_items


class PlanningMiddleware(AgentMiddleware[PlanningState]):
    """Render planning state into the prompt and track stale-plan rounds."""

    state_schema = PlanningState

    def before_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        updates: dict[str, Any] = {}
        if "plan_items" not in state:
            updates["plan_items"] = []
        if "rounds_since_update" not in state:
            updates["rounds_since_update"] = 0
        if "updated_this_turn" not in state:
            updates["updated_this_turn"] = False
        return updates or None

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        plan_items = request.state.get("plan_items", [])
        rounds_since_update = request.state.get("rounds_since_update", 0)
        extra_blocks: list[dict[str, str]] = []

        if plan_items:
            extra_blocks.append(
                {
                    "type": "text",
                    "text": "Current session plan:\n" + render_plan_items(plan_items),
                }
            )
            reminder = reminder_text(plan_items, rounds_since_update)
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

    def after_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        if state.get("updated_this_turn"):
            return {"updated_this_turn": False}
        if state.get("plan_items"):
            return {"rounds_since_update": state.get("rounds_since_update", 0) + 1}
        return None
