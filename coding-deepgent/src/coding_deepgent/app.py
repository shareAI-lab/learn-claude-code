from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from coding_deepgent.config import build_openai_model, load_settings
from coding_deepgent.middleware import PlanContextMiddleware
from coding_deepgent.rendering import latest_assistant_text, normalize_messages
from coding_deepgent.state import PlanningState, default_session_state
from coding_deepgent.tools import bash, edit_file, read_file, write_file, todo_write

SYSTEM_PROMPT = (
    "You are coding-deepgent, an independent cumulative LangChain cc product. "
    f"Current workspace: {load_settings().workdir}. "
    "Use the TodoWrite tool when explicit progress tracking helps on multi-step work, "
    "preserve exactly one in-progress todo, include activeForm for every todo, "
    "and prefer tools over prose."
)
TOOLS = [bash, read_file, write_file, edit_file, todo_write]
SESSION_STATE: dict[str, Any] = default_session_state()


def build_agent():
    return create_agent(
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[PlanContextMiddleware()],
        state_schema=PlanningState,
        name="coding-deepgent",
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    normalized = normalize_messages(messages)
    result = build_agent().invoke({"messages": normalized, **SESSION_STATE})
    SESSION_STATE.update(
        {
            "todos": result.get("todos", []),
            "rounds_since_update": result.get("rounds_since_update", 0),
        }
    )
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text
