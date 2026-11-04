from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "s17_goal_loop" / "code.py"
MODULE_NAME = "s17_goal_loop_under_test"
SPEC = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
goal_loop = importlib.util.module_from_spec(SPEC)
sys.modules[MODULE_NAME] = goal_loop
SPEC.loader.exec_module(goal_loop)


def text_response(text: str):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def tool_response(name: str, arguments: dict, tool_use_id: str = "tool-1"):
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                id=tool_use_id,
                name=name,
                input=arguments,
            )
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected model call")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


class RecordingEvaluator:
    def __init__(self, evaluations=None, error: Exception | None = None):
        self.evaluations = list(evaluations or [])
        self.error = error
        self.calls = []

    async def evaluate(self, condition, messages):
        self.calls.append((condition, list(messages)))
        if self.error:
            raise self.error
        if not self.evaluations:
            raise AssertionError("unexpected evaluator call")
        return self.evaluations.pop(0)


def make_session(
    tmp_path: Path,
    responses,
    evaluations,
    *,
    block_cap: int = 8,
    background_running=None,
):
    client = FakeClient(responses)
    evaluator = RecordingEvaluator(evaluations)
    goal = goal_loop.GoalController(evaluator, block_cap=block_cap)
    session = goal_loop.AgentSession(
        client=client,
        model="worker-model",
        goal=goal,
        workdir=tmp_path,
        background_running=background_running,
    )
    return session, client, evaluator


def test_unmet_goal_continues_automatically_until_achieved(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        session, client, evaluator = make_session(
            tmp_path,
            responses=[
                text_response("I changed the implementation."),
                text_response("pytest now exits with code 0."),
            ],
            evaluations=[
                goal_loop.GoalEvaluation(
                    ok=False,
                    reason="No test result appears in the conversation.",
                ),
                goal_loop.GoalEvaluation(
                    ok=True,
                    reason="The latest turn reports the required test result.",
                ),
            ],
        )

        result = await session.submit(
            "/goal pytest exits with code 0"
        )

        assert result.status == "achieved"
        assert session.goal.active is None
        assert len(client.messages.calls) == 2
        assert len(evaluator.calls) == 2
        assert any(
            "No test result appears" in str(message["content"])
            for message in session.messages
            if message["role"] == "user"
        )

    asyncio.run(scenario())


def test_worker_tool_result_reaches_the_goal_evaluator(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        session, client, evaluator = make_session(
            tmp_path,
            responses=[
                tool_response("bash", {"command": "printf passed"}),
                text_response("The command exited successfully."),
            ],
            evaluations=[
                goal_loop.GoalEvaluation(
                    ok=True,
                    reason="The conversation contains exit_code=0.",
                )
            ],
        )

        result = await session.submit(
            "/goal the verification command exits with code 0"
        )

        assert result.status == "achieved"
        assert len(client.messages.calls) == 2
        assert client.messages.calls[0]["tools"] == goal_loop.TOOLS
        _condition, messages = evaluator.calls[0]
        assert any(
            "exit_code=0" in goal_loop._plain_content(message["content"])
            for message in messages
        )

    asyncio.run(scenario())


def test_evaluator_receives_the_conversation_without_origin_filtering(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        session, _client, evaluator = make_session(
            tmp_path,
            responses=[text_response("tests passed")],
            evaluations=[
                goal_loop.GoalEvaluation(
                    ok=True,
                    reason="The transcript contains a passing test result.",
                )
            ],
        )

        await session.submit("/goal tests pass")

        _condition, messages = evaluator.calls[0]
        assert any(
            message["role"] == "assistant"
            and goal_loop._plain_content(message["content"]) == "tests passed"
            for message in messages
        )

    asyncio.run(scenario())


def test_background_work_defers_evaluation() -> None:
    async def scenario() -> None:
        evaluator = RecordingEvaluator(
            [goal_loop.GoalEvaluation(ok=True, reason="done")]
        )
        controller = goal_loop.GoalController(evaluator)
        controller.set_goal("background report is ready")

        decision = await controller.evaluate_after_turn(
            [{"role": "assistant", "content": "still running"}],
            background_running=True,
        )

        assert decision.action == "defer"
        assert controller.active is not None
        assert evaluator.calls == []

    asyncio.run(scenario())


def test_background_result_reenters_the_same_goal_loop(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        running = True
        session, client, evaluator = make_session(
            tmp_path,
            responses=[
                text_response("The background test is still running."),
                text_response("The background result says pytest passed."),
            ],
            evaluations=[
                goal_loop.GoalEvaluation(
                    ok=True,
                    reason="The completion notification contains a passing result.",
                )
            ],
            background_running=lambda: running,
        )

        deferred = await session.submit("/goal pytest exits with code 0")
        assert deferred.status == "defer"
        assert evaluator.calls == []

        running = False
        completed = await session.submit_background_result(
            "pytest: 12 passed; exit_code=0"
        )

        assert completed.status == "achieved"
        assert len(client.messages.calls) == 2
        assert len(evaluator.calls) == 1
        assert any(
            "Background task completed" in str(message["content"])
            for message in session.messages
        )

    asyncio.run(scenario())


def test_block_cap_returns_control_but_keeps_goal_active(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        session, client, _evaluator = make_session(
            tmp_path,
            responses=[
                text_response("attempt one"),
                text_response("attempt two"),
                text_response("attempt three"),
            ],
            evaluations=[
                goal_loop.GoalEvaluation(ok=False, reason="missing result 1"),
                goal_loop.GoalEvaluation(ok=False, reason="missing result 2"),
                goal_loop.GoalEvaluation(ok=False, reason="missing result 3"),
            ],
            block_cap=2,
        )

        result = await session.submit("/goal impossible for now")

        assert result.status == "limit"
        assert session.goal.active is not None
        assert len(client.messages.calls) == 3

    asyncio.run(scenario())


def test_impossible_goal_is_recorded_as_failed() -> None:
    async def scenario() -> None:
        evaluator = RecordingEvaluator(
            [
                goal_loop.GoalEvaluation(
                    ok=False,
                    impossible=True,
                    reason="The required service does not exist.",
                )
            ]
        )
        controller = goal_loop.GoalController(evaluator)
        controller.set_goal("deploy to the missing service")

        decision = await controller.evaluate_after_turn(
            [{"role": "assistant", "content": "service not found"}]
        )

        assert decision.action == "failed"
        assert controller.active is None
        assert controller.last_status["failed"] is True
        assert controller.status().startswith("Goal failed:")

    asyncio.run(scenario())


def test_evaluator_error_returns_control_and_keeps_goal() -> None:
    async def scenario() -> None:
        evaluator = RecordingEvaluator(error=RuntimeError("API unavailable"))
        controller = goal_loop.GoalController(evaluator)
        controller.set_goal("tests pass")

        decision = await controller.evaluate_after_turn([])

        assert decision.action == "error"
        assert "API unavailable" in decision.reason
        assert controller.active is not None

    asyncio.run(scenario())


def test_restore_reinstalls_only_an_active_goal() -> None:
    evaluator = RecordingEvaluator()
    active_events = [
        {
            "type": "goal_status",
            "condition": "tests pass",
            "active": True,
            "met": False,
            "failed": False,
            "reason": "still failing",
        }
    ]
    restored = goal_loop.GoalController.restore(evaluator, active_events)

    assert restored.active is not None
    assert restored.active.condition == "tests pass"
    assert restored.active.iterations == 0
    assert restored.active.last_reason is None

    achieved_events = active_events + [
        {
            "type": "goal_status",
            "condition": "tests pass",
            "active": False,
            "met": True,
            "failed": False,
            "reason": "done",
        }
    ]
    completed = goal_loop.GoalController.restore(evaluator, achieved_events)
    assert completed.active is None


@pytest.mark.parametrize("alias", sorted(goal_loop.CLEAR_ALIASES))
def test_clear_aliases(alias: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        evaluator = RecordingEvaluator()
        controller = goal_loop.GoalController(evaluator)
        controller.set_goal("tests pass")
        session = goal_loop.AgentSession(
            client=FakeClient([]),
            model="worker-model",
            goal=controller,
            workdir=tmp_path,
        )

        result = await session.submit(f"/goal {alias}")

        assert result.status == "cleared"
        assert controller.active is None

    asyncio.run(scenario())


def test_goal_length_is_bounded() -> None:
    controller = goal_loop.GoalController(RecordingEvaluator())
    with pytest.raises(goal_loop.GoalError, match="4000"):
        controller.set_goal("x" * (goal_loop.MAX_GOAL_LENGTH + 1))


def test_prompt_evaluator_uses_a_tool_free_json_response() -> None:
    async def scenario() -> None:
        client = FakeClient(
            [
                text_response(
                    '{"ok": false, "reason": "test output is missing", '
                    '"impossible": false}'
                )
            ]
        )
        evaluator = goal_loop.PromptGoalEvaluator(
            client=client,
            model="evaluator-model",
        )

        result = await evaluator.evaluate(
            "tests pass",
            [{"role": "assistant", "content": "implementation updated"}],
        )

        assert result.ok is False
        assert result.reason == "test output is missing"
        call = client.messages.calls[0]
        assert "tools" not in call
        assert call["model"] == "evaluator-model"

    asyncio.run(scenario())


def test_evaluator_rejects_conflicting_terminal_states() -> None:
    with pytest.raises(goal_loop.GoalError, match="both ok and impossible"):
        goal_loop._parse_json_object(
            '{"ok": true, "reason": "conflicting", "impossible": true}'
        )


def test_bash_output_keeps_exit_code_when_the_tail_is_trimmed(
    tmp_path: Path,
) -> None:
    controller = goal_loop.GoalController(RecordingEvaluator())
    session = goal_loop.AgentSession(
        client=FakeClient([]),
        model="worker-model",
        goal=controller,
        workdir=tmp_path,
    )

    output = session._run_tool(
        "bash",
        {
            "command": (
                "python -c \"import sys; "
                "print('x' * 40000); sys.exit(7)\""
            )
        },
    )

    assert output.startswith("exit_code=7\n")
    assert len(output) <= 30000


def test_read_file_cannot_escape_the_workdir(tmp_path: Path) -> None:
    controller = goal_loop.GoalController(RecordingEvaluator())
    session = goal_loop.AgentSession(
        client=FakeClient([]),
        model="worker-model",
        goal=controller,
        workdir=tmp_path,
    )

    with pytest.raises(goal_loop.GoalError, match="current repository"):
        session._run_tool("read_file", {"path": "../outside.txt"})


def test_transcript_trimming_keeps_complete_recent_messages() -> None:
    messages = [
        {"role": "user", "content": "old-" + "x" * 100},
        {"role": "assistant", "content": "recent result"},
    ]
    rendered = goal_loop.transcript_text(messages, max_characters=40)

    assert "recent result" in rendered
    assert "old-" not in rendered


def test_transcript_trims_the_middle_of_one_oversized_message() -> None:
    rendered = goal_loop.transcript_text(
        [{"role": "user", "content": "START" + "x" * 100 + "END"}],
        max_characters=40,
    )

    assert len(rendered) == 40
    assert rendered.startswith("USER:\nSTART")
    assert rendered.endswith("END")
    assert "middle omitted" in rendered


def test_goal_loop_keeps_the_s04_base_tools_and_permission_hook(
    tmp_path: Path,
) -> None:
    controller = goal_loop.GoalController(RecordingEvaluator())
    session = goal_loop.AgentSession(
        client=FakeClient([]),
        model="worker-model",
        goal=controller,
        workdir=tmp_path,
    )

    assert {tool["name"] for tool in goal_loop.TOOLS} == {
        "bash", "read_file", "write_file", "edit_file", "glob"
    }
    block = SimpleNamespace(
        name="write_file",
        input={"path": "../outside.txt", "content": "blocked"},
    )
    assert "outside" in session.trigger_hooks("PreToolUse", block)
    assert not (tmp_path.parent / "outside.txt").exists()


def test_goal_loop_file_tools_use_the_current_repository(tmp_path: Path) -> None:
    controller = goal_loop.GoalController(RecordingEvaluator())
    session = goal_loop.AgentSession(
        client=FakeClient([]),
        model="worker-model",
        goal=controller,
        workdir=tmp_path,
    )

    assert "Wrote" in session._run_tool(
        "write_file", {"path": "src/value.txt", "content": "old"}
    )
    assert "Edited" in session._run_tool(
        "edit_file",
        {"path": "src/value.txt", "old_text": "old", "new_text": "new"},
    )
    assert session._run_tool("glob", {"pattern": "src/*.txt"}) == "src/value.txt"
    assert (tmp_path / "src" / "value.txt").read_text() == "new"
