from __future__ import annotations

import builtins
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from coding_deepgent import cli
from coding_deepgent import cli_service
from coding_deepgent.compact import COMPACT_BOUNDARY_PREFIX, COMPACT_SUMMARY_PREFIX
from coding_deepgent.sessions import JsonlSessionStore, SessionMessage
from coding_deepgent.sessions.records import message_id_for_index
from coding_deepgent.sessions.session_memory import (
    SESSION_MEMORY_STATE_KEY,
    write_session_memory_artifact,
)
from coding_deepgent.settings import Settings, load_settings

runner = CliRunner()


def _history_summary(history: list[SessionMessage]) -> list[tuple[str, str, str]]:
    return [(item.message_id, item.role, item.content) for item in history]


def _session_messages(*messages: tuple[str, str]) -> list[SessionMessage]:
    return [
        SessionMessage(
            message_id=message_id_for_index(index),
            created_at=f"2026-04-16T00:00:0{index}Z",
            role=role,
            content=content,
        )
        for index, (role, content) in enumerate(messages)
    ]


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
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
        "transcript_projection": None,
    }
    assert output == "done"


def test_help_lists_runtime_foundation_commands() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "sessions" in result.stdout
    assert "tasks" in result.stdout
    assert "plans" in result.stdout
    assert "config" in result.stdout
    assert "doctor" in result.stdout
    assert "ui" in result.stdout
    assert "ui-gateway" in result.stdout


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


def test_ui_command_runs_frontend_script(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args, *, cwd):
        captured["args"] = args
        captured["cwd"] = cwd
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["ui", "--fake"])

    assert result.exit_code == 0
    assert captured["args"] == ["npm", "run", "start:fake"]
    assert str(captured["cwd"]).endswith("coding-deepgent/frontend/cli")


def test_ui_console_script_entry_runs_ui_command(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_frontend_ui(*, fake: bool) -> int:
        captured["fake"] = fake
        return 0

    monkeypatch.setattr(cli, "_run_frontend_ui", fake_run_frontend_ui)

    assert cli.ui_cli(["--fake"]) == 0
    assert captured == {"fake": True}


def test_ui_command_reports_missing_frontend_dependencies(monkeypatch, tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend" / "cli"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "_frontend_cli_dir", lambda: frontend_dir)

    result = runner.invoke(cli.app, ["ui"])

    assert result.exit_code != 0
    assert "Frontend CLI dependencies are not installed" in result.stderr


def test_ui_command_reports_missing_npm(monkeypatch, tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend" / "cli"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "package.json").write_text("{}", encoding="utf-8")
    (frontend_dir / "node_modules").mkdir()
    monkeypatch.setattr(cli, "_frontend_cli_dir", lambda: frontend_dir)

    def fake_run(args, *, cwd):
        del args, cwd
        raise FileNotFoundError("npm")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["ui", "--fake"])

    assert result.exit_code != 0
    assert "npm is required" in result.stderr


def test_ui_gateway_command_runs_uvicorn(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_app = object()

    def fake_create_app(*, fake):
        captured["fake"] = fake
        return fake_app

    def fake_run(app, *, host, port):
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(cli, "_load_ui_gateway_runtime", lambda: (fake_create_app, fake_run))

    result = runner.invoke(cli.app, ["ui-gateway", "--fake", "--host", "0.0.0.0", "--port", "3030"])

    assert result.exit_code == 0
    assert captured["fake"] is True
    assert captured["app"] is fake_app
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 3030


def test_load_ui_gateway_runtime_reports_missing_web_dependencies(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "uvicorn":
            raise ModuleNotFoundError("No module named 'uvicorn'", name="uvicorn")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(cli.ClickException, match="optional web dependencies"):
        cli._load_ui_gateway_runtime()


def _empty_history(session_id: str):
    return _loaded_session(Path("/tmp/empty-history"), session_id)


def _unused_run_prompt(
    prompt: str, history=None, session_state=None, session_id=None, transcript_projection=None
) -> str:
    del prompt, history, session_state, session_id, transcript_projection
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


def test_sessions_inspect_renders_projection_visibility(
    monkeypatch,
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-inspect")
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="First message collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    state = {"todos": [], "rounds_since_update": 0}
    write_session_memory_artifact(
        state,
        content="Current focus is inspect.",
        message_count=2,
        token_count=2,
        tool_call_count=0,
    )
    store.append_state_snapshot(context, state=state)
    loaded = store.load_session(session_id="session-inspect", workdir=workdir)
    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=_unused_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        ["sessions", "inspect", "session-inspect", "--limit", "5"],
    )

    assert result.exit_code == 0
    assert "Session Inspect" in result.stdout
    assert "projection: mode=collapse" in result.stdout
    assert "session_memory: current" in result.stdout
    assert "Compression Timeline" in result.stdout
    assert "collapse-0 collapse" in result.stdout
    assert "Model Projection" in result.stdout
    assert "source=collapse_summary" in result.stdout
    assert "Raw Transcript Visibility" in result.stdout
    assert "msg-000000 role=user hidden" in result.stdout


def test_tasks_list_renders_durable_task_table(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_service,
        "task_records",
        lambda settings, include_terminal=False: [
            cli_service.TaskRecord(
                id="task-1",
                title="Implement control surface",
                status="pending",
                owner="kun",
                metadata={"ready": "true"},
            )
        ],
    )

    result = runner.invoke(cli.app, ["tasks", "list"])

    assert result.exit_code == 0
    assert "Tasks" in result.stdout
    assert "task-1" in result.stdout
    assert "Implement control surface" in result.stdout


def test_tasks_create_parses_metadata(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_task_record(settings, **kwargs):
        del settings
        captured.update(kwargs)
        return cli_service.TaskRecord(
            id="task-1",
            title=str(kwargs["title"]),
            description=str(kwargs["description"]),
            owner=kwargs["owner"],
            metadata=kwargs["metadata"] or {},
        )

    monkeypatch.setattr(cli_service, "create_task_record", fake_create_task_record)

    result = runner.invoke(
        cli.app,
        [
            "tasks",
            "create",
            "Ship control surface",
            "--description",
            "Add CLI controls",
            "--owner",
            "kun",
            "--metadata",
            "type=workflow",
            "--metadata",
            "priority=high",
        ],
    )

    assert result.exit_code == 0
    assert captured["metadata"] == {"type": "workflow", "priority": "high"}
    assert "Ship control surface" in result.stdout
    assert "Task" in result.stdout


def test_plans_list_and_save_use_cli_service(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_service,
        "plan_records",
        lambda settings: [
            cli_service.PlanArtifact(
                id="plan-1",
                title="Ship plan",
                content="Implement controls.",
                verification="pytest -q coding-deepgent/tests",
                task_ids=["task-1"],
            )
        ],
    )

    saved: dict[str, object] = {}

    def fake_create_plan_record(settings, **kwargs):
        del settings
        saved.update(kwargs)
        return cli_service.PlanArtifact(
            id="plan-2",
            title=str(kwargs["title"]),
            content=str(kwargs["content"]),
            verification=str(kwargs["verification"]),
            task_ids=list(kwargs["task_ids"] or []),
            metadata=kwargs["metadata"] or {},
        )

    monkeypatch.setattr(cli_service, "create_plan_record", fake_create_plan_record)

    list_result = runner.invoke(cli.app, ["plans", "list"])
    save_result = runner.invoke(
        cli.app,
        [
            "plans",
            "save",
            "Control plan",
            "--content",
            "Implement CLI controls.",
            "--verification",
            "pytest -q coding-deepgent/tests/cli/test_cli.py",
            "--task-id",
            "task-1",
            "--metadata",
            "phase=wave2b",
        ],
    )

    assert list_result.exit_code == 0
    assert "Plans" in list_result.stdout
    assert "plan-1" in list_result.stdout
    assert save_result.exit_code == 0
    assert saved["metadata"] == {"phase": "wave2b"}
    assert saved["task_ids"] == ["task-1"]
    assert "Control plan" in save_result.stdout


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
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
    assert captured["prompt"] == "continue"
    assert captured["history"] == [
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
    ]
    assert captured["session_state"] == {
        "todos": [
            {
                "content": "Continue work",
                "status": "in_progress",
                "activeForm": "Continuing",
            }
        ],
        "rounds_since_update": 1,
    }
    assert captured["session_id"] == "session-1"
    assert captured["transcript_projection"] is not None
    assert "resumed" in result.stdout


def test_sessions_resume_session_memory_option_updates_state_before_run(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    loaded = _loaded_session(tmp_path)

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
            "--session-memory",
            "Current focus is deterministic assist.",
        ],
    )

    assert result.exit_code == 0
    assert captured["prompt"] == "continue"
    assert isinstance(captured["session_state"], dict)
    artifact = captured["session_state"][SESSION_MEMORY_STATE_KEY]
    assert artifact["content"] == "Current focus is deterministic assist."
    assert artifact["source"] == "manual"
    assert artifact["message_count"] == 1
    assert artifact["updated_at"]
    history = captured["history"]
    assert isinstance(history, list)
    assert "Current-session memory:" not in str(history[0]["content"])
    assert "Current focus is deterministic assist." not in str(history[0]["content"])
    assert captured["session_id"] == "session-1"


def test_sessions_resume_rejects_session_memory_without_prompt(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)

    runtime = cli_service.CliRuntime(
        settings_loader=load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: loaded,
        run_prompt=_unused_run_prompt,
        doctor_checks=lambda: [],
    )
    monkeypatch.setattr(cli, "build_cli_runtime", lambda: runtime)

    result = runner.invoke(
        cli.app,
        [
            "sessions",
            "resume",
            "session-1",
            "--session-memory",
            "Current focus is deterministic assist.",
        ],
    )

    assert result.exit_code != 0
    assert result.exception is not None


def test_sessions_resume_rejects_blank_session_memory(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)
    called: list[str] = []

    def run_prompt(
        prompt: str, history=None, session_state=None, session_id=None, transcript_projection=None
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
            "--session-memory",
            "   ",
        ],
    )

    assert result.exit_code != 0
    assert called == []


def test_sessions_resume_defaults_to_latest_compacted_continuation_when_available(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="done")
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_message(context, role="user", content="after compact")
    store.append_message(context, role="assistant", content="after compact answer")
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
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="done")
    store.append_compact(
        context,
        trigger="manual",
        summary="Earlier work was summarized.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_message(context, role="user", content="after compact")
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    history = cli_service.selected_continuation_history(loaded)

    assert history[0]["role"] == "system"
    assert history[1:] == loaded.compacted_history


def test_selected_continuation_history_prefers_loaded_collapsed_history(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="done")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="Earlier work was collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    history = cli_service.selected_continuation_history(loaded)
    projection = cli_service.selected_continuation_projection(loaded)

    assert history[0]["role"] == "system"
    assert history[1:] == loaded.collapsed_history
    assert projection.entries[0] == ()
    assert projection.entries[1] == ()
    assert projection.entries[2] == ()
    assert projection.entries[3] == (message_id_for_index(1),)


def test_selected_continuation_history_preserves_resume_compact_and_evidence_without_duplication(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="existing")
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
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_message(context, role="assistant", content="after compact")

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
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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


def test_sessions_resume_generated_compact_summary_uses_session_memory_assist(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    loaded = _loaded_session(tmp_path)
    summarizer = FakeCompactSummarizer("<summary>Generated compact summary.</summary>")

    def fake_run_prompt(
        prompt: str,
        history=None,
        session_state=None,
        session_id=None,
        transcript_projection=None,
    ) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        captured["session_state"] = session_state
        captured["session_id"] = session_id
        captured["transcript_projection"] = transcript_projection
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
            "--session-memory",
            "Current focus is deterministic assist.",
            "--generate-compact-summary",
        ],
    )

    assert result.exit_code == 0
    assert len(summarizer.requests) == 1
    assert summarizer.requests[0][-2]["role"] == "system"
    assert "Current focus is deterministic assist." in str(
        summarizer.requests[0][-2]["content"]
    )


def test_generated_compacted_continuation_history_ignores_stale_session_memory_assist(
    tmp_path: Path,
) -> None:
    loaded = _loaded_session(tmp_path)
    loaded.state[SESSION_MEMORY_STATE_KEY] = {
        "content": "Current focus is deterministic assist.",
        "source": "manual",
        "message_count": 0,
        "updated_at": "2026-04-15T00:00:00Z",
    }
    summarizer = FakeCompactSummarizer("<summary>Generated compact summary.</summary>")

    history = cli_service.generated_compacted_continuation_history(
        loaded,
        summarizer=summarizer,
        keep_last=1,
    )

    assert len(summarizer.requests) == 1
    assert len(summarizer.requests[0]) == 2
    assert summarizer.requests[0][0] == {"role": "assistant", "content": "existing"}
    assert summarizer.requests[0][-1]["role"] == "user"
    assert "Session memory artifact" not in str(summarizer.requests[0])
    assert isinstance(history, list)


def test_generated_compacted_continuation_history_refreshes_missing_session_memory(
    tmp_path: Path,
) -> None:
    loaded = _loaded_session(tmp_path)
    summarizer = FakeCompactSummarizer("<summary>Generated compact summary.</summary>")

    cli_service.generated_compacted_continuation_history(
        loaded,
        summarizer=summarizer,
        keep_last=1,
    )

    assert loaded.state[SESSION_MEMORY_STATE_KEY]["content"] == (
        "Generated compact summary."
    )
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["source"] == "generated_compact"
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["message_count"] == 1


def test_generated_compacted_continuation_history_refreshes_stale_enough_memory(
    tmp_path: Path,
) -> None:
    loaded = _loaded_session(tmp_path)
    loaded.state[SESSION_MEMORY_STATE_KEY] = {
        "content": "Old memory.",
        "source": "manual",
        "message_count": 1,
        "updated_at": "2026-04-15T00:00:00Z",
    }
    loaded = replace(
        loaded,
        history=_session_messages(
            ("user", "one"),
            ("assistant", "two"),
            ("user", "three"),
            ("assistant", "four"),
            ("user", "five"),
        ),
        summary=replace(loaded.summary, message_count=5),
    )
    summarizer = FakeCompactSummarizer("<summary>Generated compact summary.</summary>")

    cli_service.generated_compacted_continuation_history(
        loaded,
        summarizer=summarizer,
        keep_last=1,
    )

    assert loaded.state[SESSION_MEMORY_STATE_KEY]["content"] == (
        "Generated compact summary."
    )
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["source"] == "generated_compact"
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["message_count"] == 5


def test_sessions_resume_rejects_manual_and_generated_compact_together(
    monkeypatch, tmp_path: Path
) -> None:
    loaded = _loaded_session(tmp_path)
    called: list[str] = []

    def run_prompt(
        prompt: str, history=None, session_state=None, session_id=None, transcript_projection=None
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
        prompt: str, history=None, session_state=None, session_id=None, transcript_projection=None
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
        prompt: str, history=None, session_state=None, session_id=None, transcript_projection=None
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
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
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
    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "first"),
        (message_id_for_index(1), "assistant", "done"),
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
    assert _history_summary(resumed.history) == [
        (message_id_for_index(0), "user", "first"),
        (message_id_for_index(1), "assistant", "done"),
        (message_id_for_index(2), "user", "second"),
        (message_id_for_index(3), "assistant", "done"),
    ]
    assert resumed.summary.evidence_count == 2
    assert [record["message_id"] for record in message_records] == [
        message_id_for_index(0),
        message_id_for_index(1),
        message_id_for_index(2),
        message_id_for_index(3),
    ]


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

    assert _history_summary(resumed.history) == [
        (message_id_for_index(0), "user", "first"),
        (message_id_for_index(1), "assistant", "done"),
        (message_id_for_index(2), "user", "second"),
        (message_id_for_index(3), "assistant", "done"),
    ]
    assert resumed.summary.compact_count == 1
    assert resumed.compacts[0].summary == "Earlier work was summarized."
    assert resumed.compacts[0].start_message_id == message_id_for_index(0)
    assert resumed.compacts[0].end_message_id == message_id_for_index(0)
    assert resumed.compacts[0].covered_message_ids == (message_id_for_index(0),)
    assert [record["message_id"] for record in message_records] == [
        message_id_for_index(0),
        message_id_for_index(1),
        message_id_for_index(2),
        message_id_for_index(3),
    ]


def test_doctor_reports_dependencies_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "Doctor" in result.stdout
    assert "openai_api_key" in result.stdout
    assert "<set>" in result.stdout
    assert "sk-super-secret" not in result.stdout
