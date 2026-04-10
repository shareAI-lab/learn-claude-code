from __future__ import annotations

from typing import Any, Sequence

from langchain_core.language_models.fake_chat_models import (
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from agents_langchain._deepagents_gating import build_stage_agent


class SpyFakeModel(FakeMessagesListChatModel):
    bound_tool_names: list[str] = []

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        self.bound_tool_names = [_tool_name(tool) for tool in tools]
        return self


def _tool_name(tool: dict[str, Any] | type | Any | BaseTool) -> str:
    if isinstance(tool, dict):
        return (
            tool.get("name")
            or tool.get("function", {}).get("name")
            or type(tool).__name__
        )
    return getattr(tool, "name", type(tool).__name__)


def _error_messages(result: dict[str, Any]) -> list[ToolMessage]:
    return [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
        and getattr(message, "status", None) == "error"
    ]


def test_s01_tools_exclude_planning_and_subagents() -> None:
    model = SpyFakeModel(responses=[AIMessage(content="done")])

    build_stage_agent("s01", model=model).invoke(
        {"messages": [{"role": "user", "content": "inspect the workspace"}]}
    )

    assert "write_todos" not in model.bound_tool_names
    assert "task" not in model.bound_tool_names
    assert {"ls", "read_file", "write_file", "edit_file", "glob", "grep"}.issubset(
        set(model.bound_tool_names)
    )


def test_s01_rejects_write_todos_at_runtime() -> None:
    model = SpyFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_todos",
                        "args": {
                            "todos": [
                                {
                                    "content": "Plan",
                                    "status": "in_progress",
                                }
                            ]
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    result = build_stage_agent("s01", model=model).invoke(
        {"messages": [{"role": "user", "content": "plan this work"}]}
    )

    errors = _error_messages(result)
    assert len(errors) == 1
    assert errors[0].name == "write_todos"
    assert "not a valid tool" in str(errors[0].content)


def test_s03_enables_write_todos_but_still_blocks_task() -> None:
    planning_model = SpyFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_todos",
                        "args": {
                            "todos": [
                                {
                                    "content": "Plan",
                                    "status": "in_progress",
                                }
                            ]
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    planning_result = build_stage_agent("s03", model=planning_model).invoke(
        {"messages": [{"role": "user", "content": "plan this work"}]}
    )

    assert "write_todos" in planning_model.bound_tool_names
    assert "task" not in planning_model.bound_tool_names
    assert planning_result["todos"] == [{"content": "Plan", "status": "in_progress"}]

    task_model = SpyFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "task",
                        "args": {"description": "delegate", "prompt": "inspect"},
                        "id": "call_2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    task_result = build_stage_agent("s03", model=task_model).invoke(
        {"messages": [{"role": "user", "content": "delegate this"}]}
    )

    errors = _error_messages(task_result)
    assert len(errors) == 1
    assert errors[0].name == "task"
    assert "not a valid tool" in str(errors[0].content)
