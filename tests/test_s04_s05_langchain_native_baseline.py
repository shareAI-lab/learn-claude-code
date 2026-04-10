from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from agents_deepagents import s04_subagent as s04
from agents_deepagents import s05_skill_loading as s05


def _tool_name(tool: dict[str, Any] | type | Any | BaseTool) -> str:
    if isinstance(tool, dict):
        return (
            tool.get("name")
            or tool.get("function", {}).get("name")
            or type(tool).__name__
        )
    return getattr(tool, "name", getattr(tool, "__name__", type(tool).__name__))


class RecordingFakeModel(FakeMessagesListChatModel):
    bound_tool_names: list[str] = []
    seen_messages: list[list[Any]] = []

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        self.bound_tool_names = [_tool_name(tool) for tool in tools]
        return self

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ):
        self.seen_messages.append(list(messages))
        return super()._generate(
            messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )


def _system_text(message: SystemMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text", "")))
    return "\n".join(texts)


def test_s04_uses_native_task_tool_with_fresh_child_context() -> None:
    main_model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "task",
                        "args": {
                            "description": "Inspect README.md and return one short summary.",
                            "subagent_type": s04.SUBAGENT_TYPE,
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Parent integrated the child summary."),
        ]
    )
    child_model = RecordingFakeModel(
        responses=[AIMessage(content="README summary from child.")]
    )

    result = s04.build_agent(
        model=main_model,
        subagent_model=child_model,
    ).invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "First inspect setup.py, then delegate the README check.",
                }
            ]
        }
    )

    assert "task" in main_model.bound_tool_names
    assert set(child_model.bound_tool_names) == {"bash", "read_file", "write_file", "edit_file"}
    assert len(child_model.seen_messages) == 1
    assert [type(message).__name__ for message in child_model.seen_messages[0]] == [
        "SystemMessage",
        "HumanMessage",
    ]
    assert (
        child_model.seen_messages[0][1].content
        == "Inspect README.md and return one short summary."
    )

    tool_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0].name == "task"
    assert "README summary from child." in str(tool_messages[0].content)


def test_s05_uses_skills_middleware_instead_of_load_skill_tool(
    tmp_path: Path,
) -> None:
    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    skills_dir.joinpath("SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n\nUse this skill.\n",
        encoding="utf-8",
    )

    model = RecordingFakeModel(responses=[AIMessage(content="done")])
    backend = FilesystemBackend(root_dir=tmp_path, virtual_mode=True)

    s05.build_agent(
        model=model,
        backend=backend,
        skill_sources=["/skills"],
    ).invoke({"messages": [{"role": "user", "content": "Need a skill."}]})

    assert "load_skill" not in model.bound_tool_names
    assert set(model.bound_tool_names) == {"bash", "read_file", "write_file", "edit_file"}

    system_messages = [
        message
        for message in model.seen_messages[0]
        if isinstance(message, SystemMessage)
    ]
    assert len(system_messages) == 1
    system_text = _system_text(system_messages[0])
    assert "Demo skill" in system_text
    assert "/skills/demo/SKILL.md" in system_text
