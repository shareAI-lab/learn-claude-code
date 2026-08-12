import threading
from types import SimpleNamespace

import homework.agent_app.cli as cli
from homework.agent_app.cli import main


def test_cli_exits_without_agent_turn(monkeypatch):
    runtime = SimpleNamespace(stop_event=threading.Event())
    calls = []
    stopped = []

    def stop_threads(seen_runtime, threads):
        seen_runtime.stop_event.set()
        stopped.append(threads)

    monkeypatch.setattr("builtins.input", lambda _prompt: "q")
    main(
        runtime_factory=lambda: runtime,
        run_turn=lambda _runtime, _query=None: calls.append("turn"),
        start_threads=lambda _runtime: [],
        stop_threads=stop_threads,
    )

    assert calls == []
    assert runtime.stop_event.is_set()
    assert stopped == [[]]


def test_cli_runs_user_turn_under_runtime_lock(monkeypatch):
    class RecordingLock:
        def __init__(self):
            self.entered = 0

        def __enter__(self):
            self.entered += 1

        def __exit__(self, *_args):
            self.entered -= 1

    runtime = SimpleNamespace(
        stop_event=threading.Event(),
        agent_lock=RecordingLock(),
        hooks=SimpleNamespace(trigger=lambda *_args: None),
    )
    queries = iter(["hello", "q"])
    seen = []
    monkeypatch.setattr("builtins.input", lambda _prompt: next(queries))

    main(
        runtime_factory=lambda: runtime,
        run_turn=lambda _runtime, query=None: seen.append(
            (query, runtime.agent_lock.entered)
        ),
        start_threads=lambda _runtime: [],
        stop_threads=lambda seen_runtime, _threads: seen_runtime.stop_event.set(),
    )

    assert seen == [("hello", 1)]


def test_stop_runtime_threads_sets_event_and_joins():
    from homework.agent_app.cli import stop_runtime_threads

    runtime = SimpleNamespace(stop_event=threading.Event())

    class Thread:
        def __init__(self):
            self.timeouts = []

        def join(self, timeout=None):
            self.timeouts.append(timeout)

    threads = [Thread(), Thread()]
    stop_runtime_threads(runtime, threads)

    assert runtime.stop_event.is_set()
    assert [thread.timeouts for thread in threads] == [[1.0], [1.0]]


def test_queue_processor_holds_agent_lock_while_running_turn(monkeypatch):
    events = []

    class StopEvent:
        def __init__(self):
            self.calls = 0

        def wait(self, _timeout):
            self.calls += 1
            return self.calls > 1

    class Lock:
        def acquire(self, *, blocking):
            assert blocking is False
            events.append("acquire")
            return True

        def release(self):
            events.append("release")

    runtime = SimpleNamespace(
        stop_event=StopEvent(),
        scheduler=object(),
        agent_lock=Lock(),
    )
    queue_checks = iter([True, True])
    monkeypatch.setattr(cli, "has_cron_queue", lambda _state: next(queue_checks))
    monkeypatch.setattr(
        cli,
        "run_agent_turn",
        lambda seen_runtime: events.append(("turn", seen_runtime)),
    )

    cli._queue_processor_loop(runtime)

    assert events == ["acquire", ("turn", runtime), "release"]


def test_start_runtime_threads_loads_jobs_and_starts_both_workers(monkeypatch):
    created = []
    loaded = []

    class Thread:
        def __init__(self, *, target, args, daemon, name):
            created.append((target, args, daemon, name, self))
            self.started = False

        def start(self):
            self.started = True

    runtime = SimpleNamespace(
        scheduler=object(),
        config=object(),
        stop_event=threading.Event(),
    )
    monkeypatch.setattr(cli, "load_durable_jobs", lambda state, config: loaded.append((state, config)))
    monkeypatch.setattr(cli.threading, "Thread", Thread)

    threads = cli.start_runtime_threads(runtime)

    assert loaded == [(runtime.scheduler, runtime.config)]
    assert [item[3] for item in created] == [
        "cron-scheduler",
        "cron-queue-processor",
    ]
    assert all(item[2] is True for item in created)
    assert all(thread.started for thread in threads)
