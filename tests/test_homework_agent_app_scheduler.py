import json
from datetime import datetime

from homework.agent_app.config import AppConfig
from homework.agent_app.features.scheduler import (
    CronJob,
    SchedulerState,
    cron_scheduler_loop,
    load_durable_jobs,
    schedule_job,
    validate_cron,
)


def config_for(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    return AppConfig.from_env(tmp_path)


def test_scheduler_state_is_isolated(tmp_path, monkeypatch):
    config = config_for(tmp_path, monkeypatch)
    first = SchedulerState()
    second = SchedulerState()

    job = schedule_job(
        first,
        config,
        "*/5 * * * *",
        "run checks",
        recurring=True,
        durable=False,
    )

    assert isinstance(job, CronJob)
    assert job.id in first.jobs
    assert second.jobs == {}


def test_validate_cron_rejects_invalid_field():
    assert validate_cron("60 * * * *") == "minute: Value 60 out of bounds [0-59]"


class StopAfterFirstWait:
    def __init__(self):
        self.waits = 0

    def wait(self, _seconds):
        self.waits += 1
        return self.waits > 1


def test_scheduler_removes_one_shot_job_after_firing(tmp_path, monkeypatch):
    config = config_for(tmp_path, monkeypatch)
    state = SchedulerState()
    job = schedule_job(
        state,
        config,
        "* * * * *",
        "run once",
        recurring=False,
        durable=False,
    )

    cron_scheduler_loop(
        state,
        config,
        StopAfterFirstWait(),
        now=lambda: datetime(2026, 8, 12, 9, 30),
    )

    assert state.queue == [job]
    assert state.jobs == {}


def test_load_durable_jobs_loads_only_valid_jobs(tmp_path, monkeypatch):
    config = config_for(tmp_path, monkeypatch)
    config.scheduled_tasks_path.write_text(
        json.dumps([
            {
                "id": "valid",
                "cron": "0 9 * * 1",
                "prompt": "weekly review",
                "recurring": True,
                "durable": True,
            },
            {
                "id": "invalid",
                "cron": "60 * * * *",
                "prompt": "bad job",
                "recurring": True,
                "durable": True,
            },
        ]),
        encoding="utf-8",
    )
    state = SchedulerState()

    load_durable_jobs(state, config)

    assert list(state.jobs) == ["valid"]


def test_scheduler_fires_job_once_per_minute(tmp_path, monkeypatch):
    config = config_for(tmp_path, monkeypatch)
    state = SchedulerState()
    job = schedule_job(
        state,
        config,
        "* * * * *",
        "check once this minute",
        recurring=True,
        durable=False,
    )
    minute = datetime(2026, 8, 12, 9, 30)

    cron_scheduler_loop(state, config, StopAfterFirstWait(), now=lambda: minute)
    cron_scheduler_loop(state, config, StopAfterFirstWait(), now=lambda: minute)

    assert state.queue == [job]
