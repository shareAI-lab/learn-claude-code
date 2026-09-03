#!/usr/bin/env python3
"""Validate harness JSONL trace files and print aggregate statistics.

Usage:
    python3 trace_stats.py <dir>              # validate, then print stats (default)
    python3 trace_stats.py --validate <dir>   # validation only
    python3 trace_stats.py --stats <dir>      # stats only (malformed lines are skipped)

Every <dir>/*.jsonl file is one harness run recorded by trace_runtime.py: one
JSON object per line, each carrying a fixed envelope (schema_version,
timestamp, monotonic_ns, run_id, event_id, event, ..., data).  Validation
checks that every line is a JSON object with the required envelope fields and
reports offending lines as "file:line".  Stats aggregate, across all runs in
the directory: run files, models, tool-name frequency, stop/error reasons, and
approximate token totals (from model_response data.usage, when present).

Exit codes: 0 = clean, 1 = malformed lines found (default/--validate mode),
2 = usage or I/O error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

EXPECTED_SCHEMA_VERSION = "1.0"

REQUIRED_FIELDS = (
    "schema_version",
    "timestamp",
    "monotonic_ns",
    "run_id",
    "event_id",
    "event",
    "data",
)


class FileReport:
    """Validation + per-run facts for a single .jsonl trace file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: List[Dict[str, Any]] = []
        self.line_count = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.run_id: Optional[str] = None
        self.turns = 0
        self.agents = 0
        self.duration_ms = 0.0
        self.run_end_status: Optional[str] = None

    @property
    def name(self) -> str:
        return self.path.name


def check_record(line_no: int, record: Any) -> List[str]:
    """Hard validation errors for one parsed JSONL line."""
    if not isinstance(record, dict):
        return ["line %d: not a JSON object (got %s)" % (line_no, type(record).__name__)]
    errors = []
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        errors.append(
            "line %d: missing required field(s): %s" % (line_no, ", ".join(missing))
        )
    if "event" in record and not isinstance(record["event"], str):
        errors.append(
            "line %d: 'event' must be a string (got %s)"
            % (line_no, type(record["event"]).__name__)
        )
    if "data" in record and not isinstance(record["data"], dict):
        errors.append(
            "line %d: 'data' must be an object (got %s)"
            % (line_no, type(record["data"]).__name__)
        )
    return errors


def validate_file(path: Path) -> FileReport:
    report = FileReport(path)
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        report.errors.append("cannot open file: %s" % exc)
        return report
    with handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            report.line_count += 1
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                report.errors.append(
                    "line %d: invalid JSON (%s at column %d)" % (line_no, exc.msg, exc.colno)
                )
                continue
            record_errors = check_record(line_no, record)
            if record_errors:
                report.errors.extend(record_errors)
                continue
            report.records.append(record)
            if report.run_id is None:
                report.run_id = str(record.get("run_id"))
            elif record.get("run_id") and record["run_id"] != report.run_id:
                report.warnings.append(
                    "line %d: run_id changed to %r within one file"
                    % (line_no, record["run_id"])
                )
            if str(record.get("schema_version")) != EXPECTED_SCHEMA_VERSION:
                report.warnings.append(
                    "line %d: unexpected schema_version %r (expected %r)"
                    % (line_no, record.get("schema_version"), EXPECTED_SCHEMA_VERSION)
                )

    if not report.records:
        report.warnings.append("no valid records (file empty or fully malformed)")
        return report

    first_event = report.records[0]["event"]
    last_event = report.records[-1]["event"]
    if first_event != "run_start":
        report.warnings.append(
            "first event is %r, expected 'run_start' (file may be a fragment)" % first_event
        )
    if last_event != "run_end":
        report.warnings.append(
            "last event is %r, no 'run_end' (run interrupted or still recording?)" % last_event
        )

    turn_ids = {r.get("turn_id") for r in report.records if r.get("turn_id")}
    agent_ids = {r.get("agent_id") for r in report.records if r.get("agent_id")}
    report.turns = len(turn_ids)
    report.agents = len(agent_ids)

    elapsed = [
        r["elapsed_ms"]
        for r in report.records
        if isinstance(r.get("elapsed_ms"), (int, float))
    ]
    if elapsed:
        # elapsed_ms values are already milliseconds; do not rescale.
        report.duration_ms = max(0.0, max(elapsed) - min(elapsed))

    return report


class Aggregate:
    """Directory-wide statistics built from validated records."""

    def __init__(self) -> None:
        self.record_count = 0
        self.model_calls = 0
        self.models: Counter = Counter()
        self.tools: Counter = Counter()
        self.stop_reasons: Counter = Counter()
        self.tool_end_status: Counter = Counter()
        self.tool_end_status_by_tool: Counter = Counter()
        self.model_errors: Counter = Counter()
        self.model_retries: Counter = Counter()
        self.event_names: Counter = Counter()
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_tokens = 0
        self.cache_read_tokens = 0
        self.calls_with_usage = 0

    def add_file(self, report: FileReport) -> None:
        for record in report.records:
            self.record_count += 1
            event = record["event"]
            data = record["data"]
            self.event_names[event] += 1

            if event == "run_end":
                report.run_end_status = str(data.get("status", "unknown"))
            elif event == "model_request":
                self.model_calls += 1
                self.models[str(data.get("model") or "unknown")] += 1
            elif event == "model_response":
                self.stop_reasons[str(data.get("stop_reason") or "unknown")] += 1
                usage = data.get("usage")
                if isinstance(usage, dict):
                    self.calls_with_usage += 1
                    self.input_tokens += int(usage.get("input_tokens") or 0)
                    self.output_tokens += int(usage.get("output_tokens") or 0)
                    self.cache_creation_tokens += int(
                        usage.get("cache_creation_input_tokens") or 0
                    )
                    self.cache_read_tokens += int(
                        usage.get("cache_read_input_tokens") or 0
                    )
            elif event == "model_error":
                self.model_errors[
                    str(data.get("error_type") or data.get("status") or "unknown")
                ] += 1
            elif event == "model_retry":
                self.model_retries[str(data.get("reason") or "unknown")] += 1
            elif event == "tool_start":
                self.tools[str(data.get("tool") or "unknown")] += 1
            elif event == "tool_end":
                status = str(data.get("status") or "unknown")
                self.tool_end_status[status] += 1
                if status != "ok":
                    self.tool_end_status_by_tool["%s / %s" % (status, data.get("tool") or "?")] += 1


def _table(counter: Counter, top: Optional[int] = None) -> List[str]:
    items = counter.most_common()
    if top is not None:
        items = items[:top]
    if not items:
        return ["    (none observed)"]
    width = max(len(str(name)) for name, _ in items)
    return ["    %-*s  %d" % (width, name, count) for name, count in items]


def _format_ms(value_ms: float) -> str:
    if value_ms >= 60000.0:
        return "%.1f min" % (value_ms / 60000.0)
    if value_ms >= 1000.0:
        return "%.1f s" % (value_ms / 1000.0)
    return "%.0f ms" % value_ms


def render_text(directory: Path, reports: List[FileReport], agg: Aggregate,
                do_validate: bool, top: int) -> str:
    lines: List[str] = []
    total_errors = sum(len(r.errors) for r in reports)
    lines.append("Trace stats: %s" % directory)
    lines.append("  %d run file(s), %d event record(s)" % (len(reports), agg.record_count))
    lines.append("")

    if do_validate:
        lines.append("Validation")
        if total_errors == 0:
            lines.append(
                "  OK: all %d lines across %d file(s) are well-formed."
                % (sum(r.line_count for r in reports), len(reports))
            )
        else:
            lines.append("  ERROR: %d malformed line(s):" % total_errors)
            for report in reports:
                for error in report.errors:
                    lines.append("    - %s: %s" % (report.name, error))
        for report in reports:
            for warning in report.warnings:
                lines.append("  warning: %s: %s" % (report.name, warning))
        lines.append("")

    lines.append("Runs")
    if not reports:
        lines.append("    (none)")
    for index, report in enumerate(reports, start=1):
        status = report.run_end_status or "unknown (no run_end)"
        lines.append(
            "  %d. %-14s %s  %d events, %d turns, %d agent(s), %s, status=%s"
            % (
                index,
                report.run_id or "?",
                report.name,
                len(report.records),
                report.turns,
                report.agents,
                _format_ms(report.duration_ms),
                status,
            )
        )
    lines.append("")

    lines.append("Models (model_request)")
    lines.extend(_table(agg.models, top))
    lines.append("")

    lines.append("Tool calls (tool_start)")
    lines.extend(_table(agg.tools, top))
    lines.append("")

    lines.append("Model stop reasons (model_response)")
    lines.extend(_table(agg.stop_reasons, top))
    lines.append("")

    lines.append("Errors and non-ok outcomes")
    if agg.tool_end_status:
        lines.append(
            "  tool_end status: "
            + ", ".join(
                "%s %d" % (status, count) for status, count in agg.tool_end_status.most_common()
            )
        )
        if agg.tool_end_status_by_tool:
            lines.append("    by tool:")
            lines.extend(_table(agg.tool_end_status_by_tool, top))
    else:
        lines.append("  tool_end status: (none observed)")
    if agg.model_errors:
        lines.append(
            "  model_error: "
            + ", ".join(
                "%s %d" % (name, count) for name, count in agg.model_errors.most_common()
            )
        )
    else:
        lines.append("  model_error: 0")
    if agg.model_retries:
        lines.append(
            "  model_retry: "
            + ", ".join(
                "%s %d" % (name, count) for name, count in agg.model_retries.most_common()
            )
        )
    else:
        lines.append("  model_retry: 0")
    lines.append("")

    lines.append("Tokens (approx; summed over model_response data.usage)")
    if agg.model_calls:
        lines.append(
            "  model calls: %d (usage reported on %d)" % (agg.model_calls, agg.calls_with_usage)
        )
        lines.append(
            "  input %s | output %s | cache_write %s | cache_read %s"
            % (
                format(agg.input_tokens, ","),
                format(agg.output_tokens, ","),
                format(agg.cache_creation_tokens, ","),
                format(agg.cache_read_tokens, ","),
            )
        )
    else:
        lines.append("  (no model calls observed)")
    lines.append("")
    return "\n".join(lines)


def render_json(directory: Path, reports: List[FileReport], agg: Aggregate) -> str:
    return json.dumps(
        {
            "directory": str(directory),
            "files": [
                {
                    "file": report.name,
                    "run_id": report.run_id,
                    "lines": report.line_count,
                    "events": len(report.records),
                    "turns": report.turns,
                    "agents": report.agents,
                    "duration_ms": round(report.duration_ms, 3),
                    "run_end_status": report.run_end_status,
                    "errors": report.errors,
                    "warnings": report.warnings,
                }
                for report in reports
            ],
            "totals": {
                "records": agg.record_count,
                "model_calls": agg.model_calls,
                "models": dict(agg.models),
                "tool_calls": dict(agg.tools),
                "stop_reasons": dict(agg.stop_reasons),
                "tool_end_status": dict(agg.tool_end_status),
                "model_errors": dict(agg.model_errors),
                "model_retries": dict(agg.model_retries),
                "input_tokens": agg.input_tokens,
                "output_tokens": agg.output_tokens,
                "cache_creation_input_tokens": agg.cache_creation_tokens,
                "cache_read_input_tokens": agg.cache_read_tokens,
                "model_calls_with_usage": agg.calls_with_usage,
            },
        },
        indent=2,
        sort_keys=False,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate JSONL trace files in a directory and print aggregate stats.",
    )
    parser.add_argument("directory", help="directory containing run_*.jsonl trace files")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true",
                      help="run validation only and exit (default: validation + stats)")
    mode.add_argument("--stats", action="store_true",
                      help="print stats only; malformed lines are skipped, not gated on")
    parser.add_argument("--top", type=int, default=15,
                        help="max rows in frequency tables (default: 15)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit a machine-readable JSON report instead of text")
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    if not directory.exists():
        print("error: directory not found: %s" % directory, file=sys.stderr)
        return 2
    if not directory.is_dir():
        print("error: not a directory: %s" % directory, file=sys.stderr)
        return 2

    files = sorted(directory.glob("*.jsonl"))
    if not files:
        print("No .jsonl trace files found in %s" % directory)
        return 0

    reports = [validate_file(path) for path in files]
    total_errors = sum(len(report.errors) for report in reports)

    aggregate = Aggregate()
    for report in reports:
        aggregate.add_file(report)

    do_validate = not args.stats
    if args.as_json:
        print(render_json(directory, reports, aggregate))
    else:
        print(render_text(directory, reports, aggregate, do_validate, args.top))

    if args.validate or do_validate:
        return 1 if total_errors else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
