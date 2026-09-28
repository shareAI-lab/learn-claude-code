import runpy
import sys
import types
from pathlib import Path


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


def test_prepare_reinserts_active_request_archived_by_snip_compact(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    request = "compare s08 and s09 context handling"
    # Earlier conversation turns occupy the head of the history, so the
    # active request sits before a long tool-call burst — the shape that
    # lets snip_compact archive it into the middle section.
    messages = [
        {"role": "user", "content": "earlier question one"},
        {"role": "assistant", "content": [{"type": "text", "text": "answer one"}]},
        {"role": "user", "content": "earlier question two"},
        {"role": "assistant", "content": [{"type": "text", "text": "answer two"}]},
        {"role": "user", "content": request},
        {"role": "assistant", "content": [{"type": "text", "text": "starting"}]},
    ]
    for index in range(26):
        tool_id = f"tool-{index}"
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": f"out-{index}"}
            ]},
        ])

    prepared = lesson["COMPACTOR"].prepare(list(messages), request)
    rendered = "\n".join(
        message["content"] for message in prepared
        if message.get("role") == "user"
        and isinstance(message.get("content"), str)
    )
    assert "Current user request" in rendered
    assert request in rendered


def test_prepare_is_idempotent_when_still_over_message_limit(
        tmp_path, monkeypatch):
    """agent_loop calls prepare() every iteration; the reinsertion must not
    stack up duplicate request messages or re-archive on every pass."""
    lesson = load_lesson(monkeypatch, tmp_path)
    request = "compare s08 and s09 context handling"
    messages = [
        {"role": "user", "content": "earlier question one"},
        {"role": "assistant", "content": [{"type": "text", "text": "answer one"}]},
        {"role": "user", "content": "earlier question two"},
        {"role": "assistant", "content": [{"type": "text", "text": "answer two"}]},
        {"role": "user", "content": request},
        {"role": "assistant", "content": [{"type": "text", "text": "starting"}]},
    ]
    for index in range(26):
        tool_id = f"tool-{index}"
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": f"out-{index}"}
            ]},
        ])

    compactor = lesson["COMPACTOR"]
    prepared = compactor.prepare(list(messages), request)
    assert len(prepared) <= 50  # prepare() leaves the list within the snip limit
    assert prepared[0]["content"] == f"Current user request:\n{request}"
    transcripts_before = list(
        (tmp_path / ".transcripts").glob("transcript_*.jsonl"))

    prepared_again = compactor.prepare(list(prepared), request)

    assert prepared_again == prepared
    request_messages = [
        message for message in prepared_again
        if isinstance(message.get("content"), str)
        and message["content"].startswith("Current user request:")
    ]
    assert len(request_messages) == 1
    assert len(list((tmp_path / ".transcripts").glob("transcript_*.jsonl"))) \
        == len(transcripts_before)


def test_prepare_does_not_duplicate_active_request_visible_in_tail(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    request = "summarize the naming pattern"
    messages = [{"role": "user", "content": request}]

    prepared = lesson["COMPACTOR"].prepare(list(messages), request)

    assert len([message for message in prepared
                if message.get("role") == "user"
                and message.get("content") == request]) == 1
    assert not any(isinstance(message.get("content"), str)
                   and message["content"].startswith("Current user request")
                   for message in prepared)
