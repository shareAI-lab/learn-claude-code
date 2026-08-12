import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, fields
from types import SimpleNamespace

import pytest

from homework.agent_app.config import AppConfig
from homework.agent_app.core.prompt import assemble_system_prompt
from homework.agent_app.features import tasks
from homework.agent_app.features.todos import run_todo_write
from homework.agent_app.runtime import SessionState
from homework.agent_app.tools.registry import ToolRegistry


REQUIRED_TASK_TOOLS = {
    "create_task": {"subject"},
    "list_tasks": set(),
    "get_task": {"task_id"},
    "claim_task": {"task_id"},
    "complete_task": {"task_id"},
}


@pytest.fixture
def task_store(tmp_path):
    return tasks.TaskStore(root=tmp_path / ".tasks")


@pytest.fixture
def task_tools(task_store):
    registry = ToolRegistry()
    tasks.register_task_tools(registry, task_store)
    return registry.snapshot()


def make_task(
    task_id,
    subject,
    *,
    description="",
    status="pending",
    owner=None,
    blocked_by=None,
):
    return tasks.Task(
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


def test_task_creation_is_store_scoped(task_store):
    task = tasks.create_task(task_store, "inspect parser")

    assert tasks.load_task(task_store, task.id).subject == "inspect parser"


def test_store_scoped_simultaneous_claim_has_one_winner(task_store):
    task = tasks.create_task(task_store, "single owner")
    worker_count = 4
    barrier = threading.Barrier(worker_count)

    def claim(index):
        barrier.wait(timeout=5)
        return tasks.claim_task(task_store, task.id, f"agent-{index}")

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        results = [
            future.result(timeout=10)
            for future in [
                pool.submit(claim, index) for index in range(worker_count)
            ]
        ]

    assert sum(result.startswith("Claimed") for result in results) == 1


def test_task_model_has_required_fields():
    assert [field.name for field in fields(tasks.Task)] == [
        "id",
        "subject",
        "description",
        "status",
        "owner",
        "blockedBy",
        "worktree",
    ]


def test_required_task_tools_are_registered(task_tools):
    registered, handlers = task_tools
    schemas = {tool["name"]: tool for tool in registered}

    for name, required in REQUIRED_TASK_TOOLS.items():
        assert name in schemas
        assert callable(handlers[name])
        assert schemas[name]["input_schema"]["type"] == "object"
        assert set(schemas[name]["input_schema"].get("required", [])) == required


def test_task_storage_is_configured_as_dot_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")

    assert AppConfig.from_env(tmp_path).task_dir == tmp_path / ".tasks"


def test_create_task_persists_utf8_json_and_reloads(task_store):
    task = tasks.create_task(
        task_store,
        "检查解析器",
        "实现并测试中文解析器",
    )
    path = tasks.task_path(task_store, task.id)

    assert path.parent == task_store.root
    assert path.name == f"{task.id}.json"
    assert path.exists()

    raw = path.read_text(encoding="utf-8")
    assert "检查解析器" in raw
    assert "实现并测试中文解析器" in raw
    assert '\n  "subject"' in raw
    assert "\\u68c0" not in raw.lower()

    assert json.loads(raw) == asdict(task)
    assert asdict(tasks.load_task(task_store, task.id)) == asdict(task)


def test_empty_and_populated_task_lists_are_stable_and_readable(
    task_store,
    task_tools,
):
    _, handlers = task_tools
    assert tasks.list_tasks(task_store) == []
    assert "no tasks" in handlers["list_tasks"]().lower()

    task_b = make_task(
        "task_b",
        "second",
        status="in_progress",
        owner="alice",
        blocked_by=["task_a"],
    )
    task_a = make_task("task_a", "first")
    tasks.save_task(task_store, task_b)
    tasks.save_task(task_store, task_a)

    stored = tasks.list_tasks(task_store)
    assert [task.id for task in stored] == ["task_a", "task_b"]

    output = handlers["list_tasks"]()
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


def test_get_task_returns_complete_json(task_store, task_tools):
    _, handlers = task_tools
    task = make_task(
        "task_details",
        "inspect parser",
        description="read every parser module",
        status="in_progress",
        owner="reviewer",
        blocked_by=["task_setup"],
    )
    tasks.save_task(task_store, task)

    assert json.loads(handlers["get_task"](task.id)) == asdict(task)


def test_generated_task_ids_do_not_overwrite_on_collision(
    task_store,
    monkeypatch,
):
    values = iter(["same", "tmp1", "same", "different", "tmp2"])
    monkeypatch.setattr(
        tasks.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=next(values)),
    )

    first = tasks.create_task(task_store, "first")
    second = tasks.create_task(task_store, "second")

    assert first.id == "task_same"
    assert second.id == "task_different"
    assert len(list(task_store.root.glob("*.json"))) == 2
    assert tasks.load_task(task_store, first.id).subject == "first"
    assert tasks.load_task(task_store, second.id).subject == "second"


def test_missing_dependency_blocks_start_and_claim(task_store):
    task = tasks.create_task(
        task_store,
        "blocked work",
        blockedBy=["task_missing"],
    )

    assert tasks.can_start(task_store, task.id) is False
    result = tasks.claim_task(task_store, task.id, owner="worker")
    assert "blocked" in result.lower()

    stored = tasks.load_task(task_store, task.id)
    assert stored.status == "pending"
    assert stored.owner is None


def test_upstream_completion_unblocks_downstream(task_store):
    upstream = tasks.create_task(task_store, "inspect parser")
    downstream = tasks.create_task(
        task_store,
        "fix parser",
        blockedBy=[upstream.id],
    )

    blocked = tasks.claim_task(task_store, downstream.id, owner="fixer")
    assert "blocked" in blocked.lower()

    claimed = tasks.claim_task(task_store, upstream.id, owner="inspector")
    assert claimed.lower().startswith("claimed")

    completed = tasks.complete_task(task_store, upstream.id)
    assert "completed" in completed.lower()
    assert "fix parser" in completed
    assert tasks.can_start(task_store, downstream.id) is True

    downstream_claim = tasks.claim_task(
        task_store,
        downstream.id,
        owner="fixer",
    )
    assert downstream_claim.lower().startswith("claimed")


def test_state_machine_rejects_invalid_transitions_and_preserves_owner(
    task_store,
):
    task = tasks.create_task(task_store, "run tests")

    early_complete = tasks.complete_task(task_store, task.id)
    assert "cannot" in early_complete.lower()

    first_claim = tasks.claim_task(task_store, task.id, owner="qa-agent")
    assert first_claim.lower().startswith("claimed")
    assert tasks.load_task(task_store, task.id).owner == "qa-agent"

    second_claim = tasks.claim_task(task_store, task.id, owner="other-agent")
    assert "cannot" in second_claim.lower()

    first_complete = tasks.complete_task(task_store, task.id)
    assert first_complete.lower().startswith("completed")
    completed = tasks.load_task(task_store, task.id)
    assert completed.status == "completed"
    assert completed.owner == "qa-agent"

    second_complete = tasks.complete_task(task_store, task.id)
    assert "cannot" in second_complete.lower()


@pytest.mark.parametrize(
    "task_id",
    ["../outside", "/tmp/outside", "task_bad/child", ".."],
)
def test_invalid_task_ids_cannot_escape_task_directory(task_store, task_id):
    with pytest.raises(ValueError):
        tasks.task_path(task_store, task_id)


def test_valid_task_path_stays_inside_task_directory(task_store):
    path = tasks.task_path(task_store, "task_safe_123")
    assert path.resolve().is_relative_to(task_store.root.resolve())


@pytest.mark.parametrize("handler_name", ["get_task", "claim_task", "complete_task"])
def test_missing_tasks_return_clear_handler_errors(task_tools, handler_name):
    _, handlers = task_tools
    assert_clear_error(handlers[handler_name]("task_missing"))


def test_corrupt_json_does_not_break_task_listing(task_store, task_tools):
    _, handlers = task_tools
    valid = make_task("task_valid", "valid task")
    tasks.save_task(task_store, valid)
    (task_store.root / "task_corrupt.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    stored = tasks.list_tasks(task_store)
    assert [task.id for task in stored] == ["task_valid"]
    assert "task_valid" in handlers["list_tasks"]()


def test_corrupt_task_detail_returns_clear_error(task_store, task_tools):
    _, handlers = task_tools
    task_store.root.mkdir(parents=True, exist_ok=True)
    (task_store.root / "task_corrupt.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    assert_clear_error(handlers["get_task"]("task_corrupt"))


def test_todo_write_and_durable_tasks_remain_independent(task_store):
    session = SessionState()
    task = tasks.create_task(task_store, "durable work")
    original_task = asdict(tasks.load_task(task_store, task.id))
    todos = [{"content": "current session step", "status": "in_progress"}]

    result = run_todo_write(session, todos)
    assert "updated 1" in result.lower()
    assert session.todos == todos
    assert asdict(tasks.load_task(task_store, task.id)) == original_task

    tasks.claim_task(task_store, task.id, owner="agent")
    tasks.complete_task(task_store, task.id)
    assert session.todos == todos


def test_system_prompt_distinguishes_todos_from_durable_tasks():
    prompt = assemble_system_prompt(
        {"enabled_tools": ["todo_write", "create_task"]}
    ).lower()

    assert "todo_write" in prompt
    assert "create_task" in prompt
    assert "durable" in prompt
    assert "current" in prompt


def test_task_state_transitions_define_a_store_owned_lock(task_store):
    assert callable(getattr(task_store.lock, "acquire", None))
    assert callable(getattr(task_store.lock, "release", None))


def test_simultaneous_claims_have_exactly_one_winner(task_store):
    task = tasks.create_task(task_store, "single-owner work")
    worker_count = 8
    barrier = threading.Barrier(worker_count)

    def worker(index):
        try:
            barrier.wait(timeout=5)
            result = tasks.claim_task(
                task_store,
                task.id,
                owner=f"agent-{index}",
            )
            return "result", result
        except Exception as exc:
            return "error", repr(exc)

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        results = [
            future.result(timeout=10)
            for future in [
                pool.submit(worker, index) for index in range(worker_count)
            ]
        ]

    assert [value for kind, value in results if kind == "error"] == []
    successes = [
        value
        for kind, value in results
        if kind == "result" and value.lower().startswith("claimed")
    ]
    assert len(successes) == 1

    stored = tasks.load_task(task_store, task.id)
    assert stored.status == "in_progress"
    assert stored.owner in {
        f"agent-{index}" for index in range(worker_count)
    }
