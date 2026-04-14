from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from coding_deepgent import cli
from coding_deepgent import cli_service
from coding_deepgent.compact import COMPACT_BOUNDARY_PREFIX, COMPACT_SUMMARY_PREFIX
from coding_deepgent.sessions import JsonlSessionStore
from coding_deepgent.settings import Settings, load_settings

runner = CliRunner()


class FakeCompactSummarizer:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[dict[str, object]]] = []

    def invoke(self, messages: list[dict[str, object]]) -> str:
        self.requests.append(messages)
        return self.response


def _loaded_session(tmp_path: Path, session_id: str = "session-1"):
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id=session_id)
    store.append_message(context, role="assistant", content="existing")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Continue work",
                    "status": "in_progress",
                    "activeForm": "Continuing",
                }
            ],
            "rounds_since_update": 1,
        },
    )
    store.append_evidence(
        context,
        kind="verification",
        summary="pytest passed",
        status="passed",
    )
    return store.load_session(session_id=session_id, workdir=workdir)


def test_main_runs_one_integrated_prompt(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_once(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        return "done"

    monkeypatch.setattr(cli, "run_once", fake_run_once)
    monkeypatch.setattr(
        cli,
        "build_cli_runtime",
        lambda: cli_service.CliRuntime(
            settings_loader=load_settings,
            list_sessions=lambda: [],
            load_session=lambda session_id: _loaded_session(Path("/tmp"), session_id),
            run_prompt=fake_run_once,
            doctor_checks=lambda: [],
        ),
    )

    assert cli.main(["--prompt", "continue"]) == 0
    output = capsys.readouterr().out.strip()

    assert captured == {
        "prompt": "continue",
        "history": None,
        "session_state": None,
        "session_id": None,
    }
    assert output == "done"


def test_help_lists_runtime_foundation_commands() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "sessions" in result.stdout
    assert "config" in result.stdout
    assert "doctor" in result.stdout


def test_config_show_redacts_api_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")

    result = runner.invoke(cli.app, ["config", "show"])

    assert result.exit_code == 0
    assert "Configuration" in result.stdout
    assert "openai_api_key" in result.stdout
    assert "<set>" in result.stdout
    assert "sk-super-secret" not in result.stdout
    assert "https://example.invalid/v1" in result.stdout


def _empty_history(session_id: str):
    return _loaded_session(Path("/tmp/empty-history"), session_id)


def _unused_run_prompt(
    prompt: str, history=None, session_state=None, session_id=None
) -> str:
    del prompt, history, session_state, session_id
    return "unused"


def test_sessions_list_uses_runtime_provider(monkeypatch) -> None:
    runtime = cli_service.CliRuntime(
        settings_loader=lambda: Settings(
            workdir=Path("/tmp/work"), model_name="gpt-test"
        ),
        list_sessions=lambda: [
            cli_service.SessionSummaryView(
                session_id="session-1",
                updated_at="2026-04-13T00:00:00Z",
                message_count=4,
                workdir="/tmp/work",
            )
        ],
        load_session=_empty_history,
        run_prompt=_unused_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(cli.app, ["sessions", "list"])

    assert result.exit_code == 0
    assert "session-1" in result.stdout
    assert "2026-04-13T00:00:00Z" in result.stdout
    assert "/tmp/work" in result.stdout


def test_sessions_resume_uses_recovery_brief_continuation_history(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    loaded = _loaded_session(tmp_path)

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        return "resumed"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=fake_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app, ["sessions", "resume", "session-1", "--prompt", "continue"]
    )

    assert result.exit_code == 0
    assert captured == {
        "prompt": "continue",
        "history": [
            {
                "role": "system",
                "content": (
                    "Resumed session context. Use this brief as continuation "
                    "context, not as a new user request.\n\n"
                    "Session: session-1\n"
                    "Messages: 1\n"
                    "Updated: "
                    f"{loaded.summary.updated_at}\n"
                    "Active todos:\n"
                    "- Continue work\n"
                    "Recent evidence:\n"
                    "- [passed] verification: pytest passed\n"
                    "Recent compacts:\n"
                    "- none"
                ),
            },
            {"role": "assistant", "content": "existing"},
        ],
        "session_state": {
            "todos": [
                {
                    "content": "Continue work",
                    "status": "in_progress",
                    "activeForm": "Continuing",
                }
            ],
            "rounds_since_update": 1,
        },
        "session_id": "session-1",
    }
    assert "resumed" in result.stdout


def test_sessions_resume_defaults_to_latest_compacted_continuation_when_available(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first", message_index=0)
    store.append_message(context, role="assistant", content="done", message_index=1)
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        original_message_count=2,
        summarized_message_count=1,
        kept_message_count=1,
    )
    store.append_message(context, role="user", content="after compact", message_index=2)
    store.append_message(
        context, role="assistant", content="after compact answer", message_index=3
    )
    store.append_state_snapshot(
        context,
        state={"todos": [], "rounds_since_update": 0},
    )
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        return "resumed"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=fake_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app, ["sessions", "resume", "session-1", "--prompt", "continue"]
    )

    assert result.exit_code == 0
    history = captured["history"]
    assert isinstance(history, list)
    assert history[0]["role"] == "system"
    assert "Resumed session context" in str(history[0]["content"])
    assert history[1]["role"] == "system"
    assert COMPACT_BOUNDARY_PREFIX in str(history[1]["content"])
    assert history[2]["role"] == "user"
    assert COMPACT_SUMMARY_PREFIX in str(history[2]["content"])
    assert "Earlier work was summarized." in str(history[2]["content"])
    assert history[3] == {"role": "assistant", "content": "done"}
    assert history[4] == {"role": "user", "content": "after compact"}
    assert history[5] == {"role": "assistant", "content": "after compact answer"}
    assert captured["session_id"] == "session-1"
    assert "resumed" in result.stdout


def test_selected_continuation_history_uses_loaded_compacted_history(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first", message_index=0)
    store.append_message(context, role="assistant", content="done", message_index=1)
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        original_message_count=2,
        summarized_message_count=1,
        kept_message_count=1,
    )
    store.append_message(context, role="user", content="after compact", message_index=2)
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    history = cli_service.selected_continuation_history(loaded)

    assert history[0]["role"] == "system"
    assert history[1:] == loaded.compacted_history


def test_selected_continuation_history_preserves_resume_compact_and_evidence_without_duplication(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="existing", message_index=0)
    store.append_evidence(
        context,
        kind="verification",
        summary="pytest passed",
        status="passed",
        metadata={"plan_id": "plan-1", "verdict": "PASS"},
    )
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        original_message_count=2,
        summarized_message_count=1,
        kept_message_count=1,
    )
    store.append_message(context, role="assistant", content="after compact", message_index=1)

    loaded = store.load_session(session_id="session-1", workdir=workdir)
    history = cli_service.selected_continuation_history(loaded)

    assert history[0]["role"] == "system"
    assert str(history[0]["content"]).count("Resumed session context.") == 1
    assert "plan=plan-1" in str(history[0]["content"])
    assert "verdict=PASS" in str(history[0]["content"])
    assert history[1]["role"] == "system"
    assert history[2]["role"] == "user"
    assert "Earlier work was summarized." in str(history[2]["content"])
    assert history[3] == {"role": "assistant", "content": "after compact"}
    assert len(
        [message for message in history if "Resumed session context." in str(message.get("content", ""))]
    ) == 1


def test_sessions_resume_can_use_manual_compact_summary(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    loaded = _loaded_session(tmp_path)

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        return "resumed"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=fake_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--prompt",
            "continue",
            "--compact-summary",
            "<analysis>drop</analysis><summary>Earlier work is summarized.</summary>",
            "--compact-keep-last",
            "1",
        ],
    )

    assert result.exit_code == 0
    history = captured["history"]
    assert isinstance(history, list)
    assert history[0]["role"] == "system"
    assert "Resumed session context" in str(history[0]["content"])
    assert history[1]["role"] == "system"
    assert COMPACT_BOUNDARY_PREFIX in str(history[1]["content"])
    assert history[2]["role"] == "user"
    assert COMPACT_SUMMARY_PREFIX in str(history[2]["content"])
    assert "Earlier work is summarized." in str(history[2]["content"])
    assert "<analysis>" not in str(history[2]["content"])
    assert history[3] == {"role": "assistant", "content": "existing"}
    assert captured["session_state"] == loaded.state
    assert captured["session_id"] == "session-1"
    assert "resumed" in result.stdout


def test_sessions_resume_can_generate_manual_compact_summary(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    loaded = _loaded_session(tmp_path)
    summarizer = FakeCompactSummarizer(
        "<analysis>drop</analysis><summary>Generated compact summary.</summary>"
    )

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        return "resumed"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=fake_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)
    monkeypatch.setattr(cli, "build_openai_model", lambda _settings: summarizer)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--prompt",
            "continue",
            "--generate-compact-summary",
            "--compact-instructions",
            "Focus on code changes.",
            "--compact-keep-last",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert len(summarizer.requests) == 1
    assert summarizer.requests[0][0] == {"role": "assistant", "content": "existing"}
    assert "Focus on code changes." in str(summarizer.requests[0][-1]["content"])
    history = captured["history"]
    assert isinstance(history, list)
    assert "Resumed session context" in str(history[0]["content"])
    assert COMPACT_BOUNDARY_PREFIX in str(history[1]["content"])
    assert COMPACT_SUMMARY_PREFIX in str(history[2]["content"])
    assert "Generated compact summary." in str(history[2]["content"])
    assert captured["session_state"] == loaded.state
    assert captured["session_id"] == "session-1"
    assert "resumed" in result.stdout


def test_sessions_resume_rejects_manual_and_generated_compact_together(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)
    called: list[str] = []

    def run_prompt(
        prompt: str, history=None, session_state=None, session_id=None
    ) -> str:
        del history, session_state, session_id
        called.append(prompt)
        return "unused"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--prompt",
            "continue",
            "--compact-summary",
            "Manual summary.",
            "--generate-compact-summary",
        ],
    )

    assert result.exit_code != 0
    assert called == []


def test_sessions_resume_rejects_compact_options_without_prompt(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)
    called: list[str] = []

    def run_prompt(
        prompt: str, history=None, session_state=None, session_id=None
    ) -> str:
        del history, session_state, session_id
        called.append(prompt)
        return "unused"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--compact-instructions",
            "Focus on code changes.",
        ],
    )

    assert result.exit_code != 0
    assert called == []


def test_sessions_resume_rejects_compact_instructions_without_generation(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)
    called: list[str] = []

    def run_prompt(
        prompt: str, history=None, session_state=None, session_id=None
    ) -> str:
        del history, session_state, session_id
        called.append(prompt)
        return "unused"

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--prompt",
            "continue",
            "--compact-instructions",
            "Focus on code changes.",
        ],
    )

    assert result.exit_code != 0
    assert called == []


def test_sessions_resume_without_prompt_shows_recovery_brief(
    monkeypatch, tmp_path: Path
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-brief")
    store.append_message(context, role="user", content="start")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Inspect repo",
                    "status": "in_progress",
                    "activeForm": "Inspecting",
                }
            ],
            "rounds_since_update": 0,
        },
    )
    store.append_evidence(
        context,
        kind="verification",
        summary="pytest passed",
        status="passed",
    )
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        original_message_count=2,
        summarized_message_count=1,
        kept_message_count=1,
    )
    loaded = store.load_session(session_id="session-brief", workdir=workdir)

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=_unused_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(cli.app, ["sessions", "resume", "session-brief"])

    assert result.exit_code == 0
    assert "Session: session-brief" in result.stdout
    assert "Inspect repo" in result.stdout
    assert "[passed] verification: pytest passed" in result.stdout
    assert "[manual] Earlier work was summarized." in result.stdout


def test_run_once_records_new_and_resumed_session_transcript(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        workdir=tmp_path,
        session_dir=tmp_path / ".coding-deepgent" / "sessions",
        model_name="gpt-test",
    )

    def fake_agent_loop(
        messages: list[dict[str, object]],
        *,
        session_state=None,
        session_id=None,
        container=None,
    ) -> str:
        del session_id, container
        if session_state is not None:
            session_state["todos"] = [
                {
                    "content": "Resume task",
                    "status": "in_progress",
                    "activeForm": "Resuming",
                }
            ]
            session_state["rounds_since_update"] = 0
        messages.append({"role": "assistant", "content": "done"})
        return "done"

    monkeypatch.setattr(cli_service, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "agent_loop", fake_agent_loop)

    first = cli.run_once("first")
    assert first == "done"

    store = JsonlSessionStore(settings.session_dir)
    [summary] = store.list_sessions(workdir=tmp_path)
    loaded = store.load_session(session_id=summary.session_id, workdir=tmp_path)
    assert loaded.history == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "done"},
    ]
    assert loaded.summary.evidence_count == 1

    second = cli.run_once(
        "second",
        history=cli_service.continuation_history(loaded),
        session_state=loaded.state,
        session_id=loaded.summary.session_id,
    )
    assert second == "done"

    resumed = store.load_session(session_id=summary.session_id, workdir=tmp_path)
    raw_records = [
        json.loads(line)
        for line in (
            store.transcript_path_for(session_id=summary.session_id, workdir=tmp_path)
            .read_text(encoding="utf-8")
            .splitlines()
        )
    ]
    message_records = [
        record for record in raw_records if record.get("record_type") == "message"
    ]
    assert resumed.history == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "done"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "done"},
    ]
    assert resumed.summary.evidence_count == 2
    assert [record["message_index"] for record in message_records] == [0, 1, 2, 3]


def test_run_once_passes_recording_session_context_to_agent(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        workdir=tmp_path,
        session_dir=tmp_path / ".coding-deepgent" / "sessions",
        model_name="gpt-test",
    )
    seen_contexts: list[object] = []

    def fake_agent_loop(
        messages: list[dict[str, object]],
        *,
        session_state=None,
        session_id=None,
        session_context=None,
        container=None,
    ) -> str:
        del session_state, session_id, container
        seen_contexts.append(session_context)
        messages.append({"role": "assistant", "content": "done"})
        return "done"

    monkeypatch.setattr(cli_service, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "agent_loop", fake_agent_loop)

    assert cli.run_once("first") == "done"

    assert len(seen_contexts) == 1
    assert seen_contexts[0] is not None
    assert getattr(seen_contexts[0], "session_id")
    assert getattr(seen_contexts[0], "transcript_path").exists()


def test_run_once_records_compact_metadata_without_message_index_skew(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        workdir=tmp_path,
        session_dir=tmp_path / ".coding-deepgent" / "sessions",
        model_name="gpt-test",
    )

    def fake_agent_loop(
        messages: list[dict[str, object]],
        *,
        session_state=None,
        session_id=None,
        container=None,
    ) -> str:
        del session_state, session_id, container
        messages.append({"role": "assistant", "content": "done"})
        return "done"

    monkeypatch.setattr(cli_service, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "agent_loop", fake_agent_loop)

    first = cli.run_once("first")
    assert first == "done"
    store = JsonlSessionStore(settings.session_dir)
    [summary] = store.list_sessions(workdir=tmp_path)
    loaded = store.load_session(session_id=summary.session_id, workdir=tmp_path)

    second = cli.run_once(
        "second",
        history=cli_service.compacted_continuation_history(
            loaded,
            summary="<summary>Earlier work was summarized.</summary>",
            keep_last=1,
        ),
        session_state=loaded.state,
        session_id=loaded.summary.session_id,
    )
    assert second == "done"

    resumed = store.load_session(session_id=summary.session_id, workdir=tmp_path)
    raw_records = [
        json.loads(line)
        for line in (
            store.transcript_path_for(session_id=summary.session_id, workdir=tmp_path)
            .read_text(encoding="utf-8")
            .splitlines()
        )
    ]
    message_records = [
        record for record in raw_records if record.get("record_type") == "message"
    ]

    assert resumed.history == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "done"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "done"},
    ]
    assert resumed.summary.compact_count == 1
    assert resumed.compacts[0].summary == "Earlier work was summarized."
    assert resumed.compacts[0].original_message_count == 2
    assert resumed.compacts[0].summarized_message_count == 1
    assert resumed.compacts[0].kept_message_count == 1
    assert [record["message_index"] for record in message_records] == [0, 1, 2, 3]


def test_doctor_reports_dependencies_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "Doctor" in result.stdout
    assert "openai_api_key" in result.stdout
    assert "<set>" in result.stdout
    assert "sk-super-secret" not in result.stdout
