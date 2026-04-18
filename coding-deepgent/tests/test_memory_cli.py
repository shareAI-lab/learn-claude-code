from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from coding_deepgent import cli
from coding_deepgent.app import build_container as real_build_container
from coding_deepgent.memory.schemas import MemoryRecord

runner = CliRunner()


def test_memory_migrate_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODING_DEEPGENT_WORKDIR", str(tmp_path))
    monkeypatch.setenv("POSTGRES_URL", "")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("OFFLOAD_BACKEND", "none")

    result = runner.invoke(cli.app, ["memory", "migrate"])

    assert result.exit_code == 0
    assert "Memory backend schema is ready." in result.stdout


def test_memory_jobs_and_worker_commands(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODING_DEEPGENT_WORKDIR", str(tmp_path))
    monkeypatch.setenv("POSTGRES_URL", "")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("OFFLOAD_BACKEND", "none")
    container = real_build_container()
    service = container.memory_backend.service()
    service.enqueue_extraction(
        project_scope=str(tmp_path),
        agent_scope="coding-deepgent-test",
        source="agent_loop",
        text="User: run lint before commit",
    )

    monkeypatch.setattr(cli, "build_container", lambda: container)

    jobs_result = runner.invoke(cli.app, ["memory", "jobs"])
    assert jobs_result.exit_code == 0
    assert "extract_long_term_memory" in jobs_result.stdout
    assert "queued" in jobs_result.stdout

    worker_result = runner.invoke(cli.app, ["memory", "worker-run-once"])
    assert worker_result.exit_code == 0
    assert "Processed memory job" in worker_result.stdout

    records = service.list_records(
        project_scope=str(tmp_path), agent_scope="coding-deepgent-test"
    )
    assert records
    assert records[0].record.type == "feedback"


def test_memory_records_and_agent_scopes_commands(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODING_DEEPGENT_WORKDIR", str(tmp_path))
    monkeypatch.setenv("POSTGRES_URL", "")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("OFFLOAD_BACKEND", "none")
    container = real_build_container()
    service = container.memory_backend.service()
    stored = service.save_record(
        project_scope=str(tmp_path),
        agent_scope="coding-deepgent-test",
        record=MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="CLI inspection test",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
        source="manual",
    )

    monkeypatch.setattr(cli, "build_container", lambda: container)

    records_result = runner.invoke(
        cli.app, ["memory", "records", "--agent-scope", "coding-deepgent-test"]
    )
    assert records_result.exit_code == 0
    assert stored.id in records_result.stdout
    assert "coding-deepgent-test" in records_result.stdout

    scopes_result = runner.invoke(cli.app, ["memory", "agent-scopes"])
    assert scopes_result.exit_code == 0
    assert "coding-deepgent-test" in scopes_result.stdout
