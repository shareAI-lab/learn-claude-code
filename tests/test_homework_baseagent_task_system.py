import json
import runpy
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, fields
from pathlib import Path

import pytest


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)

REQUIRED_TASK_TOOLS = {
    "create_task": {"subject"},
    "list_tasks": set(),
    "get_task": {"task_id"},
    "claim_task": {"task_id"},
    "complete_task": {"task_id"},
}


@pytest.fixture
def baseagent(monkeypatch, tmp_path):
    """Load BaseAgent with fake API modules and isolated task storage."""
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(
                create=None,
                stream=None,
            )

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)

    namespace = runpy.run_path(
        str(BASE_AGENT),
        run_name="not_main",
    )
    globals_ = namespace["agent_loop"].__globals__

    original_task_dir = globals_.get(
        "TASKS_DIR",
        globals_.get("TASK_DIR"),
    )
    task_dir = tmp_path / ".tasks"
    task_dir.mkdir()

    if "TASK_DIR" in globals_:
        monkeypatch.setitem(globals_, "TASK_DIR", task_dir)
    if "TASKS_DIR" in globals_:
        monkeypatch.setitem(globals_, "TASKS_DIR", task_dir)

    monkeypatch.setitem(
        globals_,
        "_ACCEPTANCE_ORIGINAL_TASK_DIR",
        original_task_dir,
    )
    monkeypatch.setitem(
        globals_,
        "_ACCEPTANCE_TASK_DIR",
        task_dir,
    )
    todo_file = tmp_path / ".todo.json"
    if "TODO_FILE" in globals_:
        monkeypatch.setitem(
            globals_,
            "TODO_FILE",
            todo_file,
        )
    monkeypatch.setitem(
        globals_,
        "_ACCEPTANCE_TODO_FILE",
        todo_file,
    )
    monkeypatch.setitem(globals_, "CURRENT_TODOS", [])

    return globals_


def make_task(
    baseagent,
    task_id,
    subject,
    *,
    description="",
    status="pending",
    owner=None,
    blocked_by=None,
):
    return baseagent["Task"](
        id=task_id,
        subject=subject,
        description=description,
        status=status,
        owner=owner,
        blockedBy=list(blocked_by or []),
    )


def assert_clear_error(result):
    assert isinstance(result, str)
    lowered = result.lower()
    assert any(
        marker in lowered
        for marker in (
            "error",
            "not found",
            "missing",
            "invalid",
            "corrupt",
            "cannot",
        )
    )


def test_task_model_has_required_fields(baseagent):
    assert [field.name for field in fields(baseagent["Task"])] == [
        "id",
        "subject",
        "description",
        "status",
        "owner",
        "blockedBy",
        "worktree",
    ]


def test_required_task_tools_are_registered(baseagent):
    schemas = {
        tool["name"]: tool
        for tool in baseagent["BUILTIN_TOOLS"]
    }

    for name, required in REQUIRED_TASK_TOOLS.items():
        assert name in schemas
        assert name in baseagent["BUILTIN_HANDLERS"]
        assert callable(baseagent["BUILTIN_HANDLERS"][name])
        assert schemas[name]["input_schema"]["type"] == "object"
        assert set(
            schemas[name]["input_schema"].get("required", [])
        ) == required


def test_task_storage_is_configured_as_dot_tasks(baseagent):
    original = baseagent["_ACCEPTANCE_ORIGINAL_TASK_DIR"]
    assert isinstance(original, Path)
    assert original.name == ".tasks"


def test_create_task_persists_utf8_json_and_reloads(baseagent):
    task = baseagent["create_task"](
        "检查解析器",
        "实现并测试中文解析器",
    )
    path = baseagent["_task_path"](task.id)

    assert path.parent == baseagent["_ACCEPTANCE_TASK_DIR"]
    assert path.name == f"{task.id}.json"
    assert path.exists()

    raw = path.read_text(encoding="utf-8")
    assert "检查解析器" in raw
    assert "实现并测试中文解析器" in raw
    assert "\n  \"subject\"" in raw
    assert "\\u68c0" not in raw.lower()

    stored = json.loads(raw)
    assert stored == asdict(task)
    assert asdict(baseagent["load_task"](task.id)) == asdict(task)


def test_empty_and_populated_task_lists_are_stable_and_readable(
    baseagent,
):
    assert baseagent["list_tasks"]() == []
    assert "no tasks" in baseagent["run_list_tasks"]().lower()

    task_b = make_task(
        baseagent,
        "task_b",
        "second",
        status="in_progress",
        owner="alice",
        blocked_by=["task_a"],
    )
    task_a = make_task(
        baseagent,
        "task_a",
        "first",
    )
    baseagent["save_task"](task_b)
    baseagent["save_task"](task_a)

    tasks = baseagent["list_tasks"]()
    assert [task.id for task in tasks] == [
        "task_a",
        "task_b",
    ]

    output = baseagent["run_list_tasks"]()
    assert output.index("task_a") < output.index("task_b")
    for marker in (
        "first",
        "second",
        "pending",
        "in_progress",
        "alice",
        "task_a",
    ):
        assert marker in output


def test_get_task_returns_complete_json(baseagent):
    task = make_task(
        baseagent,
        "task_details",
        "inspect parser",
        description="read every parser module",
        status="in_progress",
        owner="reviewer",
        blocked_by=["task_setup"],
    )
    baseagent["save_task"](task)

    assert json.loads(
        baseagent["run_get_task"](task.id)
    ) == asdict(task)


def test_generated_task_ids_do_not_overwrite_on_collision(
    baseagent,
    monkeypatch,
):
    monkeypatch.setattr(
        baseagent["time"],
        "time",
        lambda: 1234567890,
    )
    values = iter([7, 7, 8])
    monkeypatch.setattr(
        baseagent["random"],
        "randint",
        lambda _start, _end: next(values),
    )

    first = baseagent["create_task"]("first")
    second = baseagent["create_task"]("second")

    assert first.id != second.id
    assert len(list(
        baseagent["_ACCEPTANCE_TASK_DIR"].glob("*.json")
    )) == 2
    assert baseagent["load_task"](first.id).subject == "first"
    assert baseagent["load_task"](second.id).subject == "second"


def test_missing_dependency_blocks_start_and_claim(baseagent):
    task = baseagent["create_task"](
        "blocked work",
        blockedBy=["task_missing"],
    )

    assert baseagent["can_start"](task.id) is False
    result = baseagent["claim_task"](
        task.id,
        owner="worker",
    )
    assert "blocked" in result.lower()

    stored = baseagent["load_task"](task.id)
    assert stored.status == "pending"
    assert stored.owner is None


def test_upstream_completion_unblocks_downstream(baseagent):
    upstream = baseagent["create_task"]("inspect parser")
    downstream = baseagent["create_task"](
        "fix parser",
        blockedBy=[upstream.id],
    )

    blocked = baseagent["claim_task"](
        downstream.id,
        owner="fixer",
    )
    assert "blocked" in blocked.lower()

    claimed = baseagent["claim_task"](
        upstream.id,
        owner="inspector",
    )
    assert claimed.lower().startswith("claimed")

    completed = baseagent["complete_task"](upstream.id)
    assert "completed" in completed.lower()
    assert "fix parser" in completed
    assert baseagent["can_start"](downstream.id) is True

    downstream_claim = baseagent["claim_task"](
        downstream.id,
        owner="fixer",
    )
    assert downstream_claim.lower().startswith("claimed")


def test_state_machine_rejects_invalid_transitions_and_preserves_owner(
    baseagent,
):
    task = baseagent["create_task"]("run tests")

    early_complete = baseagent["complete_task"](task.id)
    assert "cannot" in early_complete.lower()

    first_claim = baseagent["claim_task"](
        task.id,
        owner="qa-agent",
    )
    assert first_claim.lower().startswith("claimed")
    assert baseagent["load_task"](task.id).owner == "qa-agent"

    second_claim = baseagent["claim_task"](
        task.id,
        owner="other-agent",
    )
    assert "cannot" in second_claim.lower()

    first_complete = baseagent["complete_task"](task.id)
    assert first_complete.lower().startswith("completed")
    completed = baseagent["load_task"](task.id)
    assert completed.status == "completed"
    assert completed.owner == "qa-agent"

    second_complete = baseagent["complete_task"](task.id)
    assert "cannot" in second_complete.lower()


@pytest.mark.parametrize(
    "task_id",
    [
        "../outside",
        "/tmp/outside",
        "task_bad/child",
        "..",
    ],
)
def test_invalid_task_ids_cannot_escape_task_directory(
    baseagent,
    task_id,
):
    with pytest.raises(ValueError):
        baseagent["_task_path"](task_id)


def test_valid_task_path_stays_inside_task_directory(baseagent):
    path = baseagent["_task_path"]("task_safe_123")
    assert path.resolve().is_relative_to(
        baseagent["_ACCEPTANCE_TASK_DIR"].resolve()
    )


@pytest.mark.parametrize(
    "handler_name",
    [
        "run_get_task",
        "run_claim_task",
        "run_complete_task",
    ],
)
def test_missing_tasks_return_clear_handler_errors(
    baseagent,
    handler_name,
):
    result = baseagent[handler_name]("task_missing")
    assert_clear_error(result)


def test_corrupt_json_does_not_break_task_listing(baseagent):
    valid = make_task(
        baseagent,
        "task_valid",
        "valid task",
    )
    baseagent["save_task"](valid)
    (
        baseagent["_ACCEPTANCE_TASK_DIR"]
        / "task_corrupt.json"
    ).write_text("{not valid json", encoding="utf-8")

    tasks = baseagent["list_tasks"]()
    assert [task.id for task in tasks] == ["task_valid"]
    assert "task_valid" in baseagent["run_list_tasks"]()


def test_corrupt_task_detail_returns_clear_error(baseagent):
    (
        baseagent["_ACCEPTANCE_TASK_DIR"]
        / "task_corrupt.json"
    ).write_text("{not valid json", encoding="utf-8")

    result = baseagent["run_get_task"]("task_corrupt")
    assert_clear_error(result)


def test_todo_write_and_durable_tasks_remain_independent(baseagent):
    task = baseagent["create_task"]("durable work")
    original_task = asdict(baseagent["load_task"](task.id))
    todos = [{
        "content": "current session step",
        "status": "in_progress",
    }]

    result = baseagent["run_todo_write"](todos)
    assert "updated 1" in result.lower()
    assert baseagent["CURRENT_TODOS"] == todos
    assert asdict(baseagent["load_task"](task.id)) == original_task

    baseagent["claim_task"](task.id, owner="agent")
    baseagent["complete_task"](task.id)
    assert baseagent["CURRENT_TODOS"] == todos
    assert not baseagent["_ACCEPTANCE_TODO_FILE"].exists()


def test_system_prompt_distinguishes_todos_from_durable_tasks(
    baseagent,
):
    prompt = baseagent["assemble_system_prompt"]({}).lower()

    assert "todo_write" in prompt
    assert "create_task" in prompt
    assert "durable" in prompt
    assert "current" in prompt


def test_task_state_transitions_define_a_shared_lock(baseagent):
    assert "TASK_LOCK" in baseagent
    lock = baseagent["TASK_LOCK"]
    assert callable(getattr(lock, "acquire", None))
    assert callable(getattr(lock, "release", None))


def test_simultaneous_claims_have_exactly_one_winner(baseagent):
    task = baseagent["create_task"]("single-owner work")
    worker_count = 8
    barrier = threading.Barrier(worker_count)

    def worker(index):
        try:
            barrier.wait(timeout=5)
            result = baseagent["claim_task"](
                task.id,
                owner=f"agent-{index}",
            )
            return "result", result
        except Exception as exc:
            return "error", repr(exc)

    with ThreadPoolExecutor(
        max_workers=worker_count,
    ) as pool:
        futures = [
            pool.submit(worker, index)
            for index in range(worker_count)
        ]
        results = [
            future.result(timeout=10)
            for future in futures
        ]

    errors = [
        value
        for kind, value in results
        if kind == "error"
    ]
    assert errors == []

    successes = [
        value
        for kind, value in results
        if kind == "result"
        and value.lower().startswith("claimed")
    ]
    assert len(successes) == 1

    stored = baseagent["load_task"](task.id)
    assert stored.status == "in_progress"
    assert stored.owner in {
        f"agent-{index}"
        for index in range(worker_count)
    }
