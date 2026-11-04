from __future__ import annotations

import asyncio
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "web" / "src" / "data" / "scenarios"
GENERATED_VERSIONS = ROOT / "web" / "src" / "data" / "generated" / "versions.json"


def load_scenario(lesson: str) -> dict:
    return json.loads((SCENARIOS / f"{lesson}.json").read_text())


def load_lesson(name: str, script: Path):
    spec = importlib.util.spec_from_file_location(name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_s10_scenario_builds_the_task_graph_in_two_phases() -> None:
    steps = load_scenario("s10")["steps"]
    create_calls = [
        (index, json.loads(step["content"]))
        for index, step in enumerate(steps)
        if step.get("toolName") == "create_task"
        and step["type"] == "tool_call"
    ]
    create_results = [
        (index, step["content"])
        for index, step in enumerate(steps)
        if step.get("toolName") == "create_task"
        and step["type"] == "tool_result"
    ]
    update_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "update_task"
        and step["type"] == "tool_call"
    )
    update = json.loads(steps[update_index]["content"])
    task_ids = [
        re.fullmatch(r"Created (task_[0-9a-f]{8}): .+", content).group(1)
        for _, content in create_results
    ]

    assert len(create_calls) == len(create_results) == 2
    assert all("blockedBy" not in content for _, content in create_calls)
    assert max(index for index, _ in create_results) < update_index
    assert update == {
        "task_id": task_ids[1],
        "addBlockedBy": [task_ids[0]],
    }
    claim_inputs = [
        json.loads(step["content"])
        for step in steps
        if step.get("toolName") == "claim_task"
        and step["type"] == "tool_call"
    ]
    assert all(set(claim_input) == {"task_id"} for claim_input in claim_inputs)


def test_s13_scenario_uses_the_real_plan_protocol() -> None:
    steps = load_scenario("s13")["steps"]
    spawn = next(
        step for step in steps
        if step.get("toolName") == "spawn_teammate"
        and '"name":"backend"' in step.get("content", "")
    )
    claim_index = next(
        index for index, step in enumerate(steps)
        if "spawn_teammate(backend" in step.get("content", "")
    )
    request_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "request_plan"
    )
    review_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "review_plan"
    )
    response_index = next(
        index for index, step in enumerate(steps)
        if "plan_approval_response" in step.get("content", "")
    )
    create_indices = [
        index for index, step in enumerate(steps)
        if step.get("toolName") == "create_task"
        and step["type"] == "tool_call"
    ]
    update_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "update_task"
        and step["type"] == "tool_call"
    )
    first_spawn_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "spawn_teammate"
        and step["type"] == "tool_call"
    )

    review = json.loads(steps[review_index]["content"])
    spawn_input = json.loads(spawn["content"])
    assert spawn_input["require_plan"] is True
    assert re.fullmatch(r"task_[0-9a-f]{8}", spawn_input["task_id"])
    assert claim_index < request_index < review_index < response_index
    assert review["request_id"] == "req_000007"
    assert re.fullmatch(r"req_\d{6}", review["request_id"])
    assert review["approve"] is True
    assert "approved" not in review
    assert all(
        "blockedBy" not in json.loads(steps[index]["content"])
        for index in create_indices
    )
    assert max(create_indices) < update_index < first_spawn_index
    assert json.loads(steps[update_index]["content"]) == {
        "task_id": "task_5e6f7a8b",
        "addBlockedBy": ["task_1a2b3c4d"],
    }


def test_s15_scenario_calls_the_discovered_mcp_tool() -> None:
    steps = load_scenario("s15")["steps"]
    bash_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "bash"
    )
    approval_index = next(
        index for index, step in enumerate(steps)
        if "permission: user approved" in step.get("content", "")
    )
    connect_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "connect_mcp"
    )
    status_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "mcp__deploy__status"
        and step["type"] == "tool_call"
    )
    result_index = next(
        index for index, step in enumerate(steps)
        if step.get("toolName") == "mcp__deploy__status"
        and step["type"] == "tool_result"
    )
    notification_index = next(
        index for index, step in enumerate(steps)
        if "task_notification(status=completed)" in step.get("content", "")
    )

    bash_call = json.loads(steps[bash_index]["content"])
    assert bash_call == {
        "command": "python -m unittest tests.test_agent_teams_runtime",
        "run_in_background": True,
    }
    assert bash_index < approval_index < notification_index
    assert connect_index < status_index < result_index


def test_s15_runtime_discovers_and_dispatches_mcp_tools(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MODEL_ID", "test-model")
    harness = load_lesson(
        "integrated_mcp_scenario_test",
        ROOT / "s15_integrated_harness" / "code.py",
    )
    harness.WORKDIR = tmp_path

    _, handlers_before = harness.assemble_tool_pool()
    assert "mcp__deploy__status" not in handlers_before
    assert "Connected to MCP server 'deploy'" in harness.connect_mcp("deploy")

    tools_after, handlers_after = harness.assemble_tool_pool()
    assert "mcp__deploy__status" in {tool["name"] for tool in tools_after}
    assert handlers_after["mcp__deploy__status"](service="web") == (
        "[deploy] web: running (v1.4.2)"
    )


def test_s16_scenario_matches_the_deterministic_runtime(tmp_path: Path) -> None:
    scenario = load_scenario("s16")
    workflow_call = next(
        step for step in scenario["steps"]
        if step.get("toolName") == "Workflow" and step["type"] == "tool_call"
    )
    workflow_result = next(
        step for step in scenario["steps"]
        if step.get("toolName") == "Workflow" and step["type"] == "tool_result"
    )
    call_input = json.loads(workflow_call["content"])
    shown_result = json.loads(workflow_result["content"])

    workflow = load_lesson(
        "workflow_scenario_test", ROOT / "s16_workflow_runtime" / "code.py"
    )
    workflow.STORE = tmp_path
    workflow.create_run_id = lambda _meta: "wf_review-changes_0000000000001a7b"
    actual = asyncio.run(workflow.run_workflow(**call_input))

    assert set(call_input) <= set(workflow.WORKFLOW_TOOL["input_schema"]["properties"])
    assert shown_result == actual


def test_generated_s16_metadata_extends_s15_without_registry_false_positives() -> None:
    versions = json.loads(GENERATED_VERSIONS.read_text())
    by_id = {version["id"]: version for version in versions["versions"]}
    s15 = by_id["s15"]
    s16 = by_id["s16"]

    assert set(s15["tools"]) < set(s16["tools"])
    assert s16["newTools"] == ["Workflow"]
    assert "Workflow" in s16["tools"]
    assert "review-changes" not in s16["tools"]
    chapter_dirs = {
        path.name.split("_", 1)[0]: path
        for path in ROOT.glob("s[0-9][0-9]_*")
    }
    for lesson_id in ("s11", "s12", "s13", "s14", "s15", "s16"):
        assert by_id[lesson_id]["source"] == (
            chapter_dirs[lesson_id] / "code.py"
        ).read_text()
    signatures = {
        function["name"]: function["signature"]
        for function in s16["functions"]
    }
    assert signatures["run_workflow"].startswith("async def run_workflow(")
