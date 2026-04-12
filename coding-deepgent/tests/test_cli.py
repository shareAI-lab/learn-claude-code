from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from coding_deepgent import cli, config

runner = CliRunner()


def test_main_runs_one_integrated_prompt(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_once(prompt: str, history=None) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        return "done"

    monkeypatch.setattr(cli, "run_once", fake_run_once)
    monkeypatch.setattr(
        cli,
        "build_cli_runtime",
        lambda: cli.CliRuntime(
            settings_loader=config.load_settings,
            list_sessions=lambda: [],
            load_session=lambda session_id: [],
            run_prompt=fake_run_once,
            doctor_checks=lambda: [],
        ),
    )

    assert cli.main(["--prompt", "continue"]) == 0
    output = capsys.readouterr().out.strip()

    assert captured == {"prompt": "continue", "history": None}
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


def _empty_history(session_id: str) -> list[dict[str, object]]:
    del session_id
    return []


def _unused_run_prompt(prompt: str, history=None) -> str:
    del prompt, history
    return "unused"


def test_sessions_list_uses_runtime_provider(monkeypatch) -> None:
    runtime = cli.CliRuntime(
        settings_loader=lambda: config.ProjectSettings(
            workdir=Path("/tmp/work"), model_name="gpt-test"
        ),
        list_sessions=lambda: [
            cli.SessionSummary(
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


def test_sessions_resume_passes_loaded_history(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_prompt(prompt: str, history=None) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        return "resumed"

    runtime = cli.CliRuntime(
        settings_loader=config.load_settings,
        list_sessions=lambda: [],
        load_session=lambda session_id: [{"role": "assistant", "content": "existing"}],
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
        "history": [{"role": "assistant", "content": "existing"}],
    }
    assert "resumed" in result.stdout


def test_doctor_reports_dependencies_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "Doctor" in result.stdout
    assert "openai_api_key" in result.stdout
    assert "<set>" in result.stdout
    assert "sk-super-secret" not in result.stdout
