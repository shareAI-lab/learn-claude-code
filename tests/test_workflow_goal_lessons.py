from __future__ import annotations

import asyncio
import importlib.util
import json
import multiprocessing
import shutil
import subprocess
import sys
import threading
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_lesson(name: str, script: Path):
    spec = importlib.util.spec_from_file_location(name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def acquire_workflow_lock_in_child(
    script: str, store: str, run_id: str, results
) -> None:
    workflow = load_lesson("workflow_lock_child", Path(script))
    workflow.STORE = Path(store)
    try:
        with workflow.workflow_run_lock(run_id):
            results.put("acquired")
    except workflow.WorkflowInputError as exc:
        results.put(str(exc))


def run_lesson(script: Path, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=script.parent,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def test_workflow_runtime_resumes_from_journal(tmp_path: Path) -> None:
    script = tmp_path / "code.py"
    shutil.copy2(ROOT / "s16_workflow_runtime" / "code.py", script)

    first = run_lesson(script, "demo")
    resumed = run_lesson(script, "resume")

    assert "status=completed" in first
    assert "async_launched" in first
    assert "status=cached" in resumed
    assert "status=completed  agents=0  tokens=0" in resumed


def test_workflow_runtime_rejects_unsafe_artifact_names() -> None:
    workflow = load_lesson(
        "workflow_name_test", ROOT / "s16_workflow_runtime" / "code.py"
    )

    for name in ("../escape", "../../escape", "nested/name"):
        with pytest.raises(workflow.WorkflowInputError):
            workflow.validate_meta({"name": name, "description": "unsafe"})

    severity = workflow.FINDINGS_SCHEMA["properties"]["findings"]["items"][
        "properties"
    ]["severity"]
    validator = workflow.SimpleJsonSchema(severity)
    assert validator.validate("high") == (True, None)
    assert validator.validate("warning")[0] is False


def test_workflow_runtime_enforces_budget_and_shared_agent_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_limit_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    budget = workflow.Budget(total=1)
    with pytest.raises(workflow.WorkflowInputError):
        budget.add(2)
    assert budget.spent() == 0

    journal = workflow.WorkflowJournal(
        "wf_limit-test_0001", resume=False, store=tmp_path
    )
    task = workflow.LocalWorkflowTask("task", "wf_limit-test_0001", {})
    state = workflow.ExecutionState(
        task, journal, workflow.MockAgentRunner(), workflow.Budget(), {}
    )

    async def child(child_state, _args):
        return await child_state.agent("second call")

    monkeypatch.setattr(workflow, "AGENT_CAP", 1)
    monkeypatch.setitem(
        workflow.WORKFLOWS,
        "limit-child",
        ({"name": "limit-child", "description": "test"}, child),
    )

    async def run() -> None:
        await state.agent("first call")
        with pytest.raises(workflow.WorkflowInputError):
            await state.workflow("limit-child")

        async def fail_stage(_value, _item, _index):
            raise RuntimeError("stage failed")

        # Null-isolation: a failing stage drops that item, not the whole run.
        assert await state.pipeline(["item"], fail_stage) == [None]

    try:
        asyncio.run(run())
    finally:
        journal.close()


def test_workflow_runtime_rejects_corrupt_resume_journal(tmp_path: Path) -> None:
    workflow = load_lesson(
        "workflow_journal_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    run_id = "wf_corrupt_0001"
    (tmp_path / f"{run_id}.journal.jsonl").write_text("{not-json}\n")

    with pytest.raises(workflow.WorkflowInputError, match="line 1"):
        workflow.WorkflowJournal(run_id, resume=True, store=tmp_path)


def test_workflow_tool_adapter_uses_registry_and_returns_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_adapter_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)

    result = asyncio.run(
        workflow.WORKFLOW_HANDLERS["Workflow"](
            name="review-changes", args={"budget": None}
        )
    )

    assert workflow.WORKFLOW_TOOL["input_schema"]["required"] == ["name"]
    assert result["launched"]["workflowName"] == "review-changes"
    assert result["task"]["status"] == "completed"
    assert result["task"]["taskType"] == "local_workflow"
    assert len(result["result"]["confirmed"]) == 5
    snapshot = json.loads(
        (tmp_path / f"{result['task']['runId']}.json").read_text()
    )
    assert snapshot["workflowName"] == "review-changes"
    assert snapshot["args"] == {"budget": None}
    assert snapshot["task"]["status"] == "completed"

    json.dumps(result)


def test_fresh_workflow_runs_have_unique_identity_and_resume_validates_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_identity_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)

    first = asyncio.run(workflow.run_workflow("review-changes", {"budget": None}))
    second = asyncio.run(workflow.run_workflow("review-changes", {"budget": None}))

    assert first["task"]["runId"] != second["task"]["runId"]
    assert first["task"]["taskId"] != second["task"]["taskId"]
    with pytest.raises(workflow.WorkflowInputError, match="args do not match"):
        asyncio.run(
            workflow.run_workflow(
                "review-changes",
                {"budget": 1},
                resume_from_run_id=first["task"]["runId"],
            )
        )


def test_fresh_workflow_run_refuses_an_existing_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_collision_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)
    fixed_id = "wf_review-changes_0000000000001a7b"
    monkeypatch.setattr(workflow, "create_run_id", lambda _meta: fixed_id)

    first = asyncio.run(workflow.run_workflow("review-changes", {"budget": None}))
    first_snapshot = (tmp_path / f"{fixed_id}.json").read_text()
    first_output = (tmp_path / f"{fixed_id}.output.json").read_text()

    with pytest.raises(workflow.WorkflowInputError, match="unique workflow runId"):
        asyncio.run(workflow.run_workflow("review-changes", {"budget": None}))

    assert first["task"]["runId"] == fixed_id
    assert (tmp_path / f"{fixed_id}.json").read_text() == first_snapshot
    assert (tmp_path / f"{fixed_id}.output.json").read_text() == first_output


def test_invalid_resume_does_not_overwrite_completed_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_resume_guard_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)
    result = asyncio.run(
        workflow.run_workflow("review-changes", {"budget": None})
    )
    run_id = result["task"]["runId"]
    snapshot_path = tmp_path / f"{run_id}.json"
    output_path = tmp_path / f"{run_id}.output.json"
    journal_path = tmp_path / f"{run_id}.journal.jsonl"
    snapshot = snapshot_path.read_text()
    output = output_path.read_text()
    journal_path.write_text("not-json\n")

    with pytest.raises(workflow.WorkflowInputError, match="invalid resume journal"):
        asyncio.run(
            workflow.run_workflow(
                "review-changes", resume_from_run_id=run_id
            )
        )

    assert snapshot_path.read_text() == snapshot
    assert output_path.read_text() == output


def test_active_workflow_run_rejects_concurrent_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_active_run_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)
    run_id = "wf_slow-test_0000000000001a7b"
    monkeypatch.setattr(workflow, "create_run_id", lambda _meta: run_id)
    started = asyncio.Event()
    release = asyncio.Event()
    meta = {"name": "slow-test", "description": "hold the run open"}

    async def slow_workflow(_ctx, _args):
        started.set()
        await release.wait()
        return {"invocation": 1}

    async def exercise():
        first = asyncio.create_task(
            workflow.WorkflowTool().call(meta, slow_workflow)
        )
        await started.wait()
        try:
            with pytest.raises(workflow.WorkflowInputError, match="already active"):
                await workflow.WorkflowTool().call(
                    meta, slow_workflow, resume_from_run_id=run_id
                )
        finally:
            release.set()
        return await first

    result = asyncio.run(exercise())

    assert result["result"] == {"invocation": 1}
    assert json.loads((tmp_path / f"{run_id}.output.json").read_text()) == {
        "invocation": 1
    }


def test_workflow_run_lock_is_cross_process(tmp_path: Path) -> None:
    workflow = load_lesson(
        "workflow_process_lock_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    workflow.STORE = tmp_path
    run_id = "wf_process-lock_0000000000001a7b"
    context = multiprocessing.get_context("spawn")
    results = context.Queue()

    with workflow.workflow_run_lock(run_id):
        child = context.Process(
            target=acquire_workflow_lock_in_child,
            args=(str(ROOT / "s16_workflow_runtime" / "code.py"),
                  str(tmp_path), run_id, results),
        )
        child.start()
        child.join(5)

    assert child.exitcode == 0
    assert "already active" in results.get(timeout=1)


def test_workflow_tool_extends_the_integrated_host_pool() -> None:
    workflow = load_lesson(
        "workflow_host_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    host = types.SimpleNamespace(
        assemble_tool_pool=lambda: (
            [{"name": "bash", "input_schema": {}}],
            {"bash": lambda **_: "ok"},
        )
    )

    workflow.install_workflow_tool(host)
    tools, handlers = host.assemble_tool_pool()

    assert [tool["name"] for tool in tools] == ["bash", "Workflow"]
    assert handlers["Workflow"] is workflow.run_workflow_sync


def test_anthropic_runner_parses_json_and_records_real_usage() -> None:
    workflow = load_lesson(
        "workflow_real_runner_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(
                type="text", text='```json\n{"ok": true}\n```'
            )],
            usage=types.SimpleNamespace(input_tokens=11, output_tokens=7),
        )

    client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=create)
    )
    runner = workflow.AnthropicAgentRunner(client, "deepseek-v4-flash")

    result = runner.run(
        "Check the supplied change.",
        schema={
            "type": "object",
            "required": ["ok"],
            "properties": {"ok": {"type": "boolean"}},
        },
        label="check",
    )

    assert result.value == {"ok": True}
    assert result.tokens == 18
    assert calls[0]["model"] == "deepseek-v4-flash"
    assert "tools" not in calls[0]


def test_real_runner_output_retries_once_after_invalid_json(
    tmp_path: Path,
) -> None:
    workflow = load_lesson(
        "workflow_real_runner_retry_test",
        ROOT / "s16_workflow_runtime" / "code.py",
    )
    responses = iter([
        types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="not json")],
            usage=types.SimpleNamespace(input_tokens=3, output_tokens=2),
        ),
        types.SimpleNamespace(
            content=[types.SimpleNamespace(
                type="text", text='Result:\n```json\n{"ok": true}\n```\nDone.'
            )],
            usage=types.SimpleNamespace(input_tokens=4, output_tokens=3),
        ),
    ])
    client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **_kwargs: next(responses))
    )
    runner = workflow.AnthropicAgentRunner(client, "test-model")
    journal = workflow.WorkflowJournal(
        "wf_json-retry_0001", resume=False, store=tmp_path
    )
    task = workflow.LocalWorkflowTask("task", "wf_json-retry_0001", {})
    state = workflow.ExecutionState(
        task, journal, runner, workflow.Budget(), {}
    )

    try:
        result = asyncio.run(state.agent(
            "Return a result.",
            schema={
                "type": "object",
                "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}},
            },
            label="json-retry",
        ))
    finally:
        journal.close()

    assert result == {"ok": True}
    assert task.usage == {"agents": 1, "tokens": 12}


def test_install_workflow_tool_selects_the_host_api_runner() -> None:
    workflow = load_lesson(
        "workflow_runner_factory_test",
        ROOT / "s16_workflow_runtime" / "code.py",
    )
    client = object()
    host = types.SimpleNamespace(
        client=client,
        MODEL="deepseek-v4-flash",
        assemble_tool_pool=lambda: ([], {}),
    )

    workflow.install_workflow_tool(host)
    runner = workflow.RUNNER_FACTORY()

    assert isinstance(runner, workflow.AnthropicAgentRunner)
    assert runner.client is client
    assert runner.model == "deepseek-v4-flash"


def test_parallel_agent_calls_do_not_block_the_event_loop(tmp_path: Path) -> None:
    workflow = load_lesson(
        "workflow_parallel_runner_test",
        ROOT / "s16_workflow_runtime" / "code.py",
    )
    barrier = threading.Barrier(2)

    class BarrierRunner:
        def run(self, prompt, schema=None, label=None):
            barrier.wait(timeout=2)
            return workflow.RunnerOutput({"label": label}, 1)

    journal = workflow.WorkflowJournal(
        "wf_parallel-test_0001", resume=False, store=tmp_path
    )
    task = workflow.LocalWorkflowTask("task", "wf_parallel-test_0001", {})
    state = workflow.ExecutionState(
        task, journal, BarrierRunner(), workflow.Budget(), {}
    )

    async def run():
        return await state.parallel([
            lambda: state.agent("first", label="first"),
            lambda: state.agent("second", label="second"),
        ])

    try:
        result = asyncio.run(run())
    finally:
        journal.close()

    assert result == [{"label": "first"}, {"label": "second"}]
    assert task.usage == {"agents": 2, "tokens": 2}


def test_workflow_default_entry_extends_the_real_s15_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_ID", "test-model")
    workflow = load_lesson(
        "workflow_real_host_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    host = workflow.load_integrated_host()

    workflow.install_workflow_tool(host)
    tools, handlers = host.assemble_tool_pool()
    names = [tool["name"] for tool in tools]

    assert len(host.BUILTIN_TOOLS) == 25
    assert names[:-1] == [tool["name"] for tool in host.BUILTIN_TOOLS]
    assert names[-1] == "Workflow"
    assert handlers["Workflow"] is workflow.run_workflow_sync
    assert handlers["Workflow"](name="missing") == (
        "Error: unknown workflow 'missing'"
    )


def test_workflow_tool_adapter_uses_saved_name_surface() -> None:
    """Teaching adapter stays on name/args; Claude Code also has script/scriptPath."""
    workflow = load_lesson(
        "workflow_schema_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    properties = workflow.WORKFLOW_TOOL["input_schema"]["properties"]

    assert set(properties) == {
        "name",
        "args",
        "resume_from_run_id",
        "resumeFromRunId",
    }
    assert "description" not in properties
    assert "script" not in properties
    assert "scriptPath" not in properties
    with pytest.raises(workflow.WorkflowInputError, match="name must be a string"):
        asyncio.run(workflow.run_workflow({"name": "review-changes"}))
    with pytest.raises(workflow.WorkflowInputError, match="unknown workflow"):
        asyncio.run(workflow.run_workflow("missing"))


def test_parallel_and_pipeline_isolate_failures(tmp_path: Path) -> None:
    workflow = load_lesson(
        "workflow_null_isolation_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    journal = workflow.WorkflowJournal(
        "wf_null-iso_0001", resume=False, store=tmp_path
    )
    task = workflow.LocalWorkflowTask("task", "wf_null-iso_0001", {})
    state = workflow.ExecutionState(
        task, journal, workflow.MockAgentRunner(), workflow.Budget(), {}
    )

    async def ok():
        return await state.agent("ok", label="ok")

    async def boom():
        raise RuntimeError("helper crashed")

    async def stage_ok(value, _item, _index):
        return f"ok:{value}"

    async def stage_fail(value, _item, _index):
        if value == "bad":
            raise RuntimeError("stage crashed")
        return f"next:{value}"

    async def stage_later(value, _item, _index):
        return f"final:{value}"

    async def run():
        parallel_out = await state.parallel([ok, boom, ok])
        pipeline_out = await state.pipeline(
            ["good", "bad", "also"], stage_fail, stage_later
        )
        return parallel_out, pipeline_out

    try:
        parallel_out, pipeline_out = asyncio.run(run())
    finally:
        journal.close()

    assert parallel_out[1] is None
    assert parallel_out[0] is not None and parallel_out[2] is not None
    assert pipeline_out == ["final:next:good", None, "final:next:also"]


def test_resume_uses_longest_unchanged_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_prefix_resume_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)
    run_id = "wf_prefix-test_0000000000001a7b"
    monkeypatch.setattr(workflow, "create_run_id", lambda _meta: run_id)
    calls: list[str] = []

    class TrackingRunner:
        def run(self, prompt, schema=None, label=None):
            calls.append(label or prompt)
            return workflow.RunnerOutput({"label": label, "prompt": prompt}, 1)

    monkeypatch.setattr(workflow, "RUNNER_FACTORY", TrackingRunner)
    meta = {"name": "prefix-test", "description": "prefix resume"}

    async def script_v1(ctx, _args):
        a = await ctx.agent("one", label="a")
        b = await ctx.agent("two", label="b")
        c = await ctx.agent("three", label="c")
        return [a, b, c]

    async def script_v2(ctx, _args):
        # a unchanged, b's prompt changes → prefix breaks; c must run live
        # even though an old "c" key exists further down the journal.
        a = await ctx.agent("one", label="a")
        b = await ctx.agent("two-changed", label="b")
        c = await ctx.agent("three", label="c")
        return [a, b, c]

    first = asyncio.run(workflow.WorkflowTool().call(meta, script_v1))
    assert first["task"].status == "completed"
    assert calls == ["a", "b", "c"]

    calls.clear()
    resumed = asyncio.run(
        workflow.WorkflowTool().call(
            meta, script_v2, resume_from_run_id=run_id
        )
    )
    assert resumed["task"].status == "completed"
    assert calls == ["b", "c"], "after the first miss, later calls must run live"
    assert resumed["result"][0] == {"label": "a", "prompt": "one"}
    assert resumed["result"][1]["prompt"] == "two-changed"
    assert resumed["task"].usage["agents"] == 2


def test_resume_from_run_id_camel_case_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = load_lesson(
        "workflow_resume_alias_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    monkeypatch.setattr(workflow, "STORE", tmp_path)
    first = asyncio.run(
        workflow.run_workflow("review-changes", {"budget": None})
    )
    resumed = asyncio.run(
        workflow.run_workflow(
            "review-changes",
            resumeFromRunId=first["task"]["runId"],
        )
    )
    assert resumed["task"]["status"] == "completed"
    assert resumed["task"]["usage"]["agents"] == 0
