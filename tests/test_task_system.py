import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s10_task_system" / "code.py"


def load_lesson(workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")

    module_name = f"s10_task_system_test_{id(workdir)}"
    spec = importlib.util.spec_from_file_location(module_name, LESSON)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules[module_name] = module
    try:
        os.chdir(workdir)
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        sys.modules.pop(module_name, None)
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def tool_call(name: str, **arguments):
    return types.SimpleNamespace(name=name, input=arguments, id="tool-1")


def test_s10_keeps_the_s04_kernel_and_adds_task_tools() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        lesson = load_lesson(workdir)

        assert [tool["name"] for tool in lesson.TOOLS] == [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "create_task",
            "update_task",
            "list_tasks",
            "get_task",
            "claim_task",
            "complete_task",
        ]
        assert lesson.permission_hook in lesson.HOOKS["PreToolUse"]
        assert hasattr(lesson, "execute_tool")
        assert not hasattr(lesson, "MEMORY_DIR")
        assert not (workdir / ".tasks").exists()

        tools = {tool["name"]: tool for tool in lesson.TOOLS}
        create_schema = tools["create_task"]["input_schema"]
        update_schema = tools["update_task"]["input_schema"]
        assert "blockedBy" not in create_schema["properties"]
        assert create_schema["additionalProperties"] is False
        assert update_schema["required"] == ["task_id", "addBlockedBy"]


def test_dependencies_gate_claim_and_completion_checks_owner() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        lesson = load_lesson(workdir)

        schema = lesson.create_task("create schema")
        api = lesson.create_task("write API")
        lesson.update_task(api.id, [schema.id])

        assert lesson.claim_task(api.id) == f"Blocked by: ['{schema.id}']"
        assert "Claimed" in lesson.claim_task(schema.id)
        assert "Unblocked: write API" in lesson.complete_task(schema.id)
        assert "Claimed" in lesson.claim_task(api.id)
        assert "owned by agent, not other" in lesson.complete_task(
            api.id, owner="other"
        )
        assert "Completed" in lesson.complete_task(api.id)
        assert lesson.load_task(api.id).status == "completed"


def test_dependencies_are_added_after_create_returns_runtime_ids() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        create_results = [
            lesson.execute_tool(tool_call("create_task", subject=subject))
            for subject in (
                "create schema",
                "write API",
                "write tests",
                "write docs",
            )
        ]
        task_ids = [result.split()[1].rstrip(":") for result in create_results]
        schema_id, api_id, tests_id, docs_id = task_ids

        update_results = [
            lesson.execute_tool(tool_call(
                "update_task", task_id=api_id, addBlockedBy=[schema_id]
            )),
            lesson.execute_tool(tool_call(
                "update_task", task_id=tests_id, addBlockedBy=[api_id]
            )),
            lesson.execute_tool(tool_call(
                "update_task", task_id=docs_id, addBlockedBy=[schema_id]
            )),
        ]

        assert all(not result.startswith("Error:") for result in update_results)
        assert lesson.load_task(schema_id).blockedBy == []
        assert lesson.load_task(api_id).blockedBy == [schema_id]
        assert lesson.load_task(tests_id).blockedBy == [api_id]
        assert lesson.load_task(docs_id).blockedBy == [schema_id]


def test_invalid_and_missing_task_ids_become_tool_results() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        invalid = lesson.execute_tool(tool_call("get_task", task_id="../outside"))
        missing = lesson.execute_tool(
            tool_call("claim_task", task_id="task_00000000")
        )

        assert invalid.startswith("Error: Invalid task ID")
        assert missing.startswith("Error:")


def test_create_retries_instead_of_overwriting_an_existing_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        values = iter(["deadbeef", "deadbeef", "cafebabe"])
        monkeypatch.setattr(lesson.secrets, "token_hex", lambda _size: next(values))

        first = lesson.create_task("first")
        second = lesson.create_task("second")

        assert first.id == "task_deadbeef"
        assert second.id == "task_cafebabe"
        assert [task.subject for task in lesson.list_tasks()] == ["second", "first"]


def test_update_rejects_invalid_graph_changes_without_partial_mutation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        dependency = lesson.create_task("create schema")
        target = lesson.create_task("write API")

        missing = lesson.execute_tool(tool_call(
            "update_task",
            task_id=target.id,
            addBlockedBy=[dependency.id, "task_00000000"],
        ))
        self_dependency = lesson.execute_tool(tool_call(
            "update_task", task_id=target.id, addBlockedBy=[target.id]
        ))

        assert missing == "Error: Dependency not found: task_00000000"
        assert self_dependency == "Error: Task cannot depend on itself"
        assert lesson.load_task(target.id).blockedBy == []


def test_update_is_idempotent_and_rejects_cycles_or_started_tasks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        first = lesson.create_task("first")
        second = lesson.create_task("second")
        third = lesson.create_task("third")

        lesson.update_task(second.id, [first.id, first.id])
        lesson.update_task(second.id, [first.id])
        lesson.update_task(third.id, [second.id])

        cycle = lesson.execute_tool(tool_call(
            "update_task", task_id=first.id, addBlockedBy=[third.id]
        ))
        assert cycle.startswith("Error: Dependency cycle detected")
        assert lesson.load_task(first.id).blockedBy == []
        assert lesson.load_task(second.id).blockedBy == [first.id]

        assert "Claimed" in lesson.claim_task(first.id)
        started = lesson.execute_tool(tool_call(
            "update_task", task_id=first.id, addBlockedBy=[second.id]
        ))
        assert "only be updated while pending and unowned" in started


def test_task_store_rejects_a_symlink_outside_the_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as outside:
            workdir = Path(tmp)
            (workdir / ".tasks").symlink_to(
                Path(outside), target_is_directory=True
            )
            lesson = load_lesson(workdir)

            output = lesson.execute_tool(
                tool_call("create_task", subject="unsafe")
            )

            assert output == "Error: Task store escapes the workspace"
            assert list(Path(outside).iterdir()) == []
