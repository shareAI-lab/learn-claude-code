#!/usr/bin/env python3
"""Demo 3 -- Compare every sample trace, trace by trace.

What this demo shows
--------------------
The sample ``traces/`` directory holds several recorded CLI sessions, each with
a different shape (single-agent Q&A, tool-heavy inspection, delegated team work,
...):

    run_20260901T193828_408312Z_83ce7412.jsonl
    run_20260901T200234_810844Z_717f03f3.jsonl
    run_20260902T002404_246018Z_4739e3b3.jsonl
    run_20260902T004901_584576Z_dc6a9685.jsonl

This demo loops over every ``run_*.jsonl`` file and runs
``trace_view.py <file> --view metrics`` on each one, so you can compare
model/tool call counts, token usage, subagent counts, parallelism, and
orchestration overhead run by run.

It then shows how to *use* trace_stats.py programmatically: run it with
``--stats --json``, parse the JSON report, and print a compact per-run table
plus directory-wide totals.

Usage (works from any working directory)::

    python3 examples/demo3_compare_all_traces.py

Only the Python standard library is used.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

# examples/ lives inside s15_integrated_harness/, so the trace tools and the
# sample traces are always exactly one directory up from this script.
PARENT_DIR = Path(__file__).resolve().parent.parent
TRACE_VIEW = PARENT_DIR / "trace_view.py"
TRACE_STATS = PARENT_DIR / "trace_stats.py"
TRACES_DIR = PARENT_DIR / "traces"


def fail(message: str) -> "None":
    """Print a friendly error (not a traceback) and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def run_tool(args: list[str], title: str) -> str:
    """Run one trace-tool invocation, print the command and output, return stdout."""
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)
    command = [sys.executable, *[str(a) for a in args]]
    print("$ " + " ".join(shlex.quote(part) for part in command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip("\n"))
    if result.stderr:
        print(result.stderr.rstrip("\n"), file=sys.stderr)
    print(f"(exit code: {result.returncode})")
    if result.returncode != 0:
        fail(f"command failed with exit code {result.returncode}")
    return result.stdout


def print_comparison_table(report: dict) -> None:
    """Render a compact per-run table from trace_stats.py's JSON report."""
    print()
    print("=" * 74)
    print("Cross-run comparison (parsed from trace_stats.py --json output)")
    print("=" * 74)
    header = f"  {'run id':<16} {'events':>7} {'turns':>5} {'agents':>7} {'duration':>12}  status"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for entry in report["files"]:
        duration = entry["duration_ms"]
        duration_text = f"{duration / 1000:.1f}s" if duration >= 1000 else f"{duration:.0f}ms"
        print(
            "  {:<16} {:>7} {:>5} {:>7} {:>12}  {}".format(
                entry["run_id"] or "?",
                entry["events"],
                entry["turns"],
                entry["agents"],
                duration_text,
                entry["run_end_status"] or "unknown (no run_end)",
            )
        )
    totals = report["totals"]
    tokens = (
        totals["input_tokens"] + totals["output_tokens"]
        + totals["cache_creation_input_tokens"] + totals["cache_read_input_tokens"]
    )
    tool_calls = sum(totals["tool_calls"].values())
    print()
    print("  directory totals:")
    print(f"    records           : {totals['records']}")
    print(f"    model calls       : {totals['model_calls']}")
    print(f"    tool calls        : {tool_calls}")
    print(f"    model errors      : {sum(totals['model_errors'].values())}")
    print(f"    total tokens (approx): {tokens:,}")


def main() -> int:
    # Sanity checks so problems produce friendly messages instead of tracebacks.
    for required in (TRACE_VIEW, TRACE_STATS, TRACES_DIR):
        if not required.exists():
            fail(f"expected {required} to exist -- is the s15_integrated_harness checkout intact?")
    traces = sorted(TRACES_DIR.glob("run_*.jsonl"))
    if not traces:
        fail(f"no run_*.jsonl sample traces found in {TRACES_DIR}")

    print(f"Demo 3: compare {len(traces)} sample traces")
    print(f"  traces directory: {TRACES_DIR}")
    print()
    print("Step 1: per-run metrics (trace_view.py --view metrics on each file).")
    print("Compare, e.g., total_model_calls vs. total_tool_calls, maximum_parallel_")
    print("agents (1 = purely sequential), and orchestration_overhead_ms.")

    for index, trace in enumerate(traces, start=1):
        run_tool([TRACE_VIEW, trace, "--view", "metrics"],
                 f"Run {index}/{len(traces)}: metrics for {trace.name}")

    # --stats --json: stats only (no validation gate) so the exit code is 0
    # and stdout is exactly one JSON document we can parse.
    stdout = run_tool(
        [TRACE_STATS, TRACES_DIR, "--stats", "--json"],
        "Step 2: aggregate JSON report across all runs",
    )
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        fail(f"could not parse trace_stats.py JSON output: {exc}")
    print_comparison_table(report)

    print()
    print("Done: every per-run metrics view and the aggregate report exited 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
