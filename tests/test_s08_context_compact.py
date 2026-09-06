import runpy
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s08_context_compact" / "code.py"


def load_lesson(monkeypatch, workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(workdir)
    return runpy.run_path(str(LESSON))


def test_glob_double_star_matches_files_at_any_depth(tmp_path, monkeypatch):
    (tmp_path / "root.py").write_text("")
    (tmp_path / "one").mkdir()
    (tmp_path / "one" / "one.py").write_text("")
    (tmp_path / "one" / "two").mkdir()
    (tmp_path / "one" / "two" / "deep.py").write_text("")
    lesson = load_lesson(monkeypatch, tmp_path)

    matches = set(lesson["run_glob"]("**/*.py").splitlines())

    assert matches == {"root.py", "one/one.py", "one/two/deep.py"}


def test_prepare_preserves_tool_results_while_context_is_within_limit(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = []
    expected_results = []
    for index in range(5):
        tool_id = f"tool-{index}"
        result = f"result-{index}:" + "x" * 200
        expected_results.append(result)
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": result}
            ]},
        ])
    messages.append({"role": "assistant", "content": [
        {"type": "text", "text": "continue"}
    ]})

    prepared = lesson["COMPACTOR"].prepare(messages, "inspect the repository")
    actual_results = [
        block["content"]
        for message in prepared
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "tool_result"
    ]

    assert actual_results == expected_results


def test_prepare_micro_compacts_tool_results_after_context_exceeds_limit(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = []
    for index in range(5):
        tool_id = f"tool-{index}"
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id,
                 "content": f"result-{index}:" + "x" * 1000}
            ]},
        ])
    messages.append({"role": "assistant", "content": [
        {"type": "text", "text": "continue"}
    ]})
    compactor = lesson["COMPACTOR"]
    compactor.CONTEXT_CHAR_LIMIT = 4500

    prepared = compactor.prepare(messages, "inspect the repository")
    actual_results = [
        block["content"]
        for message in prepared
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "tool_result"
    ]

    assert all(result.startswith("[Earlier tool result saved at ")
               for result in actual_results[:2])
    for index, result in enumerate(actual_results[:2]):
        saved_path = Path(result.removeprefix(
            "[Earlier tool result saved at ").removesuffix("]"))
        assert saved_path.read_text() == f"result-{index}:" + "x" * 1000
    assert all(result.startswith(f"result-{index}:")
               for index, result in enumerate(actual_results[2:], start=2))


def test_prepare_persists_oversized_unseen_result_before_full_compact(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    output = "latest-result:" + "x" * 60000
    messages = [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "latest", "name": "read_file", "input": {}}
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "latest", "content": output}
        ]},
    ]
    compactor = lesson["COMPACTOR"]
    compactor.summarize_history = lambda _messages: (_ for _ in ()).throw(
        AssertionError("full compaction should not run"))

    prepared = compactor.prepare(messages, "inspect the result")
    content = prepared[-1]["content"][0]["content"]

    assert len(prepared) == 2
    assert content.startswith("<persisted-output>")
    saved_line = next(line for line in content.splitlines()
                      if line.startswith("Full output: "))
    assert Path(saved_line.removeprefix("Full output: ")).read_text() == output


@pytest.mark.parametrize("error_message", [
    "prompt is too long: 210445 tokens > 200000 maximum",
    "prompt_too_long",
    "too many tokens",
])
def test_agent_loop_compacts_and_retries_context_overflow(
        tmp_path, monkeypatch, error_message):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = [{"role": "user", "content": "continue"}]
    compacted = [{"role": "user", "content": "compacted history"}]
    requests = []
    response = types.SimpleNamespace(
        content=[types.SimpleNamespace(type="text", text="Recovered")])

    def create(**kwargs):
        requests.append(list(kwargs["messages"]))
        if len(requests) == 1:
            raise RuntimeError(error_message)
        return response

    compact = Mock(return_value=compacted)
    monkeypatch.setattr(lesson["client"].messages, "create", create)
    monkeypatch.setattr(lesson["COMPACTOR"], "reactive_compact", compact)

    lesson["agent_loop"](messages, "continue")

    assert len(requests) == 2
    assert requests[1] == compacted
    compact.assert_called_once()
    assert compact.call_args.args[1] == "continue"
    assert messages == [*compacted,
                        {"role": "assistant", "content": response.content}]


def test_agent_loop_stops_after_one_reactive_retry(tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = [{"role": "user", "content": "continue"}]
    first_error = RuntimeError("prompt is too long: first request")
    retry_error = RuntimeError("prompt is too long: retry")
    create = Mock(side_effect=[first_error, retry_error])
    compact = Mock(return_value=list(messages))
    monkeypatch.setattr(lesson["client"].messages, "create", create)
    monkeypatch.setattr(lesson["COMPACTOR"], "reactive_compact", compact)

    with pytest.raises(RuntimeError) as caught:
        lesson["agent_loop"](messages, "continue")

    assert caught.value is retry_error
    assert create.call_count == 2
    compact.assert_called_once()


def test_agent_loop_propagates_unrelated_errors(tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    error = RuntimeError("invalid API key")
    create = Mock(side_effect=error)
    compact = Mock()
    monkeypatch.setattr(lesson["client"].messages, "create", create)
    monkeypatch.setattr(lesson["COMPACTOR"], "reactive_compact", compact)

    with pytest.raises(RuntimeError) as caught:
        lesson["agent_loop"]([{"role": "user", "content": "continue"}], "continue")

    assert caught.value is error
    create.assert_called_once()
    compact.assert_not_called()
