"""End-to-end CLI smoke tests for the s15 trace tooling.

Runs ``trace_view.py`` and ``trace_stats.py`` as subprocesses (the same way a
user would: ``python s15_integrated_harness/trace_view.py ...``) against a
small, self-contained sample trace written to a temp directory, and asserts
exit code 0 plus sane stdout.  Both CLIs are stdlib-only, so these tests do
not need the ``anthropic`` package or any running model server.

A second group of tests pins down the documented error contract:
``trace_stats.py`` exits 1 on malformed lines (default/--validate mode),
skips them under ``--stats`` (exit 0), and exits 2 on a missing directory.

The sample trace is generated at runtime in a temp directory, so the suite is
fully self-contained and leaves no fixture files in the repo.  The file runs
under pytest (``python3 -m pytest tests/``) or standalone
(``python3 tests/test_cli_smoke.py``) — no third-party dependencies.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LESSON_DIR = HERE.parent
TRACE_VIEW = LESSON_DIR / "trace_view.py"
TRACE_STATS = LESSON_DIR / "trace_stats.py"

SAMPLE_EVENTS = 11  # expected record count of the generated sample
SAMPLE_INPUT_TOKENS = 100
SAMPLE_OUTPUT_TOKENS = 42


# ---------------------------------------------------------------------------
# Sample trace generation
# ---------------------------------------------------------------------------


def _event(seq, event, data, *, span_id=None, parent_span_id=None,
           turn_id=None, agent_id="agent-root", agent_kind="lead"):
    """Build one trace record matching the trace_runtime.py envelope."""
    return {
        "schema_version": "1.0",
        "timestamp": "2026-09-02T00:00:00.000000Z",
        "monotonic_ns": seq * 1_000_000,
        "elapsed_ms": float(seq),
        "run_id": "run_smoketest",
        "turn_id": turn_id,
        "event_id": "evt_%06d" % seq,
        "event": event,
        "agent_id": agent_id,
        "parent_agent_id": None,
        "agent_kind": agent_kind,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "caused_by_event_id": None,
        "depends_on_event_ids": [],
        "thread": {"id": 1, "name": "MainThread"},
        "data": data,
    }


def _sample_trace():
    """One lead turn: model call -> harness dispatch -> one bash tool."""
    turn = "turn_000001"
    return [
        _event(1, "run_start",
               data={"runtime": "s15", "model": "test-model"}),
        _event(2, "turn_start", turn_id=turn,
               data={"trigger": "user",
                     "request": {"characters": 4, "preview": "ping"}}),
        _event(3, "model_request", turn_id=turn, span_id="span_000001",
               data={"model": "test-model", "tool_count": 1}),
        _event(4, "model_response", turn_id=turn, span_id="span_000001",
               data={"stop_reason": "tool_use",
                     "usage": {"input_tokens": SAMPLE_INPUT_TOKENS,
                               "output_tokens": SAMPLE_OUTPUT_TOKENS,
                               "cache_creation_input_tokens": None,
                               "cache_read_input_tokens": None}}),
        _event(5, "harness_decision", turn_id=turn,
               data={"decision": "dispatch_tools", "reason": "tool_use",
                     "tools": ["bash"]}),
        _event(6, "tool_start", turn_id=turn, span_id="span_000002",
               data={"tool": "bash", "arguments": {"command": "echo hi"}}),
        _event(7, "tool_execution_start", turn_id=turn, span_id="span_000003",
               parent_span_id="span_000002", data={"tool": "bash"}),
        _event(8, "tool_execution_end", turn_id=turn, span_id="span_000003",
               parent_span_id="span_000002",
               data={"status": "ok", "tool": "bash", "duration_ms": 5.0}),
        _event(9, "tool_end", turn_id=turn, span_id="span_000002",
               data={"status": "ok", "tool": "bash",
                     "result": {"preview": "hi", "characters": 2}}),
        _event(10, "turn_end", turn_id=turn,
               data={"trigger": "user", "status": "completed"}),
        _event(11, "run_end", data={"status": "completed"}),
    ]


def _write_trace(dir_path, events):
    path = dir_path / "run_smoketest.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events),
                    encoding="utf-8")
    return path


class _TempTraces:
    """Temp dir with the sample trace written; cleaned up on exit()."""

    def __init__(self, extra_lines=()):
        self.root = Path(tempfile.mkdtemp(prefix="s15_smoke_"))
        self.traces = self.root / "traces"
        self.traces.mkdir()
        self.file = _write_trace(self.traces, _sample_trace())
        for line in extra_lines:
            with self.file.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def exit(self):
        shutil.rmtree(self.root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


def metric_value(stdout, key):
    """Extract a 'key : value' cell from trace_view metrics output."""
    match = re.search(r"^\s*%s\s*:\s*(\S+)" % re.escape(key), stdout, re.M)
    assert match, "metric %r not found in output:\n%s" % (key, stdout)
    return match.group(1)


# ---------------------------------------------------------------------------
# trace_view.py — happy path
# ---------------------------------------------------------------------------


def test_trace_view_exists():
    assert TRACE_VIEW.is_file(), "trace_view.py missing from lesson dir"


def test_trace_stats_exists():
    assert TRACE_STATS.is_file(), "trace_stats.py missing from lesson dir"


def test_trace_view_default_view():
    """Default --view both: metrics + tree + timeline, exit 0, sane stdout."""
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.file)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        assert "Trace:" in result.stdout
        assert ctx.file.name in result.stdout

        # Metrics section with sane aggregate values.
        assert "Metrics" in result.stdout
        assert metric_value(result.stdout, "run_id") == "run_smoketest"
        assert metric_value(result.stdout, "total_model_calls") == "1"
        assert metric_value(result.stdout, "total_tool_calls") == "1"
        assert metric_value(result.stdout, "total_agents") == "1"
        assert metric_value(result.stdout, "input_tokens") == str(SAMPLE_INPUT_TOKENS)
        assert metric_value(result.stdout, "output_tokens") == str(SAMPLE_OUTPUT_TOKENS)
        assert metric_value(result.stdout, "total_runtime_ms") == "10.0"
        assert metric_value(result.stdout, "model_time_ms") == "1.0"
        assert metric_value(result.stdout, "tool_time_ms") == "1.0"

        # Tree section.
        assert "Agent / execution tree" in result.stdout
        assert "Root Agent" in result.stdout
        assert "Harness: dispatch_tools" in result.stdout
        assert "Tool: bash" in result.stdout

        # Timeline section.
        assert "Timeline" in result.stdout
        assert "Legend: M=model" in result.stdout
    finally:
        ctx.exit()


def test_trace_view_metrics_only():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.file, "--view", "metrics")
        assert result.returncode == 0, result.stderr
        assert "Metrics" in result.stdout
        assert metric_value(result.stdout, "total_model_calls") == "1"
        # tree/timeline sections must be absent
        assert "Agent / execution tree" not in result.stdout
        assert "Legend:" not in result.stdout
    finally:
        ctx.exit()


def test_trace_view_tree_only():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.file, "--view", "tree")
        assert result.returncode == 0, result.stderr
        assert "Agent / execution tree" in result.stdout
        assert "Root Agent" in result.stdout
        assert "Metrics" not in result.stdout
        assert "Legend:" not in result.stdout
    finally:
        ctx.exit()


def test_trace_view_timeline_only():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.file, "--view", "timeline",
                         "--width", "60")
        assert result.returncode == 0, result.stderr
        assert "Timeline" in result.stdout
        assert "Legend: M=model" in result.stdout
        assert "Metrics" not in result.stdout
        # the model/tool spans render under the root agent row
        assert "Root Agent" in result.stdout
    finally:
        ctx.exit()


def test_trace_view_summary_json():
    """--summary emits a machine-readable JSON report."""
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.file, "--summary")
        assert result.returncode == 0, result.stderr
        summary = json.loads(result.stdout)
        assert summary["event_count"] == SAMPLE_EVENTS
        assert summary["trace_count"] == 1
        assert summary["events_by_type"]["model_request"] == 1
        assert summary["events_by_type"]["tool_start"] == 1
        assert summary["tokens"]["input_tokens"] == SAMPLE_INPUT_TOKENS
        assert summary["tokens"]["output_tokens"] == SAMPLE_OUTPUT_TOKENS
        assert summary["total_tokens"] == (SAMPLE_INPUT_TOKENS +
                                           SAMPLE_OUTPUT_TOKENS)
        assert summary["duration_ms"] == 10.0
    finally:
        ctx.exit()


def test_trace_view_no_args_picks_latest():
    """With no path argument, trace_view picks the newest trace in traces/
    relative to the process working directory (like running from the repo
    root after `cd learn-claude-code`)."""
    ctx = _TempTraces()
    try:
        # ctx.root is the stand-in repo root; ctx.traces is its traces/ child.
        result = run_cli(TRACE_VIEW, cwd=ctx.root)
        assert result.returncode == 0, result.stderr
        assert "Trace:" in result.stdout
        assert "run_smoketest.jsonl" in result.stdout
    finally:
        ctx.exit()


def test_trace_view_missing_file_is_usage_error():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_VIEW, ctx.traces / "does_not_exist.jsonl")
        assert result.returncode == 2, (result.returncode, result.stdout,
                                        result.stderr)
        combined = result.stdout + result.stderr
        assert "does_not_exist" in combined
    finally:
        ctx.exit()


# ---------------------------------------------------------------------------
# trace_stats.py — happy path
# ---------------------------------------------------------------------------


def test_trace_stats_default():
    """Validation + stats: exit 0, well-formed report, sane aggregates."""
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.traces)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        assert "Trace stats:" in result.stdout
        assert "1 run file(s), %d event record(s)" % SAMPLE_EVENTS \
            in result.stdout
        # clean validation section
        assert "Validation" in result.stdout
        assert ("OK: all %d lines across 1 file(s) are well-formed."
                % SAMPLE_EVENTS) in result.stdout
        # per-run line
        assert "run_smoketest" in result.stdout
        assert "11 events, 1 turns, 1 agent(s)" in result.stdout
        assert "status=completed" in result.stdout
        # aggregates
        assert "test-model" in result.stdout
        assert "tool_use" in result.stdout
        assert "tool_end status: ok 1" in result.stdout
        assert "model_error: 0" in result.stdout
        assert "model_retry: 0" in result.stdout
        assert "model calls: 1 (usage reported on 1)" in result.stdout
        assert ("input %d | output %d | cache_write 0 | cache_read 0"
                % (SAMPLE_INPUT_TOKENS, SAMPLE_OUTPUT_TOKENS)) in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_validate_only():
    """--validate: exit 0 on a clean trace, validation section present.
    (Stats sections are always rendered by trace_stats; the mode only gates
    the exit code and the Validation section.)"""
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.traces, "--validate")
        assert result.returncode == 0, result.stderr
        assert "Validation" in result.stdout
        assert "OK: all %d lines" % SAMPLE_EVENTS in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_stats_only():
    """--stats: prints stats and skips the validation gate."""
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.traces, "--stats")
        assert result.returncode == 0, result.stderr
        assert "Runs" in result.stdout
        assert "Models (model_request)" in result.stdout
        assert "Validation" not in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_json():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.traces, "--json")
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert len(report["files"]) == 1
        file_report = report["files"][0]
        assert file_report["file"] == "run_smoketest.jsonl"
        assert file_report["run_id"] == "run_smoketest"
        assert file_report["events"] == SAMPLE_EVENTS
        assert file_report["errors"] == []
        assert file_report["run_end_status"] == "completed"
        totals = report["totals"]
        assert totals["records"] == SAMPLE_EVENTS
        assert totals["model_calls"] == 1
        assert totals["models"] == {"test-model": 1}
        assert totals["tool_calls"] == {"bash": 1}
        assert totals["stop_reasons"] == {"tool_use": 1}
        assert totals["input_tokens"] == SAMPLE_INPUT_TOKENS
        assert totals["output_tokens"] == SAMPLE_OUTPUT_TOKENS
    finally:
        ctx.exit()


# ---------------------------------------------------------------------------
# trace_stats.py — documented error contract
# ---------------------------------------------------------------------------


def test_trace_stats_malformed_line_fails_validation():
    ctx = _TempTraces(extra_lines=("this is not valid json\n",))
    try:
        result = run_cli(TRACE_STATS, ctx.traces)
        assert result.returncode == 1, (result.returncode, result.stdout,
                                        result.stderr)
        assert "ERROR: 1 malformed line(s):" in result.stdout
        assert "invalid JSON" in result.stdout
        # the 11 good records are still aggregated
        assert "11 event record(s)" in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_malformed_line_skipped_in_stats_mode():
    ctx = _TempTraces(extra_lines=("this is not valid json\n",))
    try:
        result = run_cli(TRACE_STATS, ctx.traces, "--stats")
        assert result.returncode == 0, (result.returncode, result.stdout,
                                        result.stderr)
        assert "11 event record(s)" in result.stdout
        assert "test-model" in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_missing_directory_exit_2():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.root / "no_such_dir")
        assert result.returncode == 2
        assert "directory not found" in result.stderr
    finally:
        ctx.exit()


def test_trace_stats_empty_directory_ok():
    ctx = _TempTraces()
    try:
        empty = ctx.root / "empty"
        empty.mkdir()
        result = run_cli(TRACE_STATS, empty)
        assert result.returncode == 0, result.stderr
        assert "No .jsonl trace files found" in result.stdout
    finally:
        ctx.exit()


def test_trace_stats_file_instead_of_directory_exit_2():
    ctx = _TempTraces()
    try:
        result = run_cli(TRACE_STATS, ctx.file)
        assert result.returncode == 2
        assert "not a directory" in result.stderr
    finally:
        ctx.exit()


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _failures = 0
    _tests = [(name, fn) for name, fn in sorted(globals().items())
              if name.startswith("test_") and callable(fn)]
    for name, fn in _tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report and continue
            _failures += 1
            print("FAIL %s: %s: %s" % (name, type(exc).__name__, exc))
        else:
            print("PASS %s" % name)
    print("\n%d/%d smoke tests passed" % (len(_tests) - _failures, len(_tests)))
    sys.exit(1 if _failures else 0)
