#!/usr/bin/env python3
"""Demo 2 -- Validate and summarize all sample traces with trace_stats.py.

What this demo shows
--------------------
``trace_stats.py`` looks at a *directory* of ``run_*.jsonl`` trace files (each
one is a full CLI session recorded by ``trace_runtime.py``) and does two jobs:

  * Validation: every line must be a JSON object carrying the fixed envelope
    (schema_version, timestamp, monotonic_ns, run_id, event_id, event, data).
    Offending lines are reported as ``file:line``.  A clean directory ends
    with status ``OK``.
  * Statistics: aggregates across every run in the directory -- per-run facts
    (events, turns, agents, duration, final status), model names, tool-call
    frequency, stop reasons, error/retry counts, and approximate token totals.

Exit-code contract (the demo treats these as normal outcomes, not crashes):

  0  clean: every line well-formed
  1  validation found malformed lines (they are printed, run still "succeeded")
  2  usage or I/O error (e.g. directory not found)

This demo runs three modes against the bundled ``traces/`` directory::

    python3 examples/demo2_validate_and_stats.py

  1) default mode       validation + text statistics
  2) --stats --top 5    statistics only, shortened frequency tables
  3) --json             machine-readable JSON report

Only the Python standard library is used.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

# examples/ lives inside s15_integrated_harness/, so the trace tool and the
# sample traces are always exactly one directory up from this script.
PARENT_DIR = Path(__file__).resolve().parent.parent
TRACE_STATS = PARENT_DIR / "trace_stats.py"
TRACES_DIR = PARENT_DIR / "traces"


def fail(message: str) -> "None":
    """Print a friendly error (not a traceback) and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def run_tool(args: list[str], title: str, allow_returncodes=(0, 1)) -> int:
    """Run one trace-tool invocation and print the command, output, and code.

    ``allow_returncodes``: trace_stats.py legitimately exits 1 when validation
    finds malformed lines -- that is a successful demo run, so 0 and 1 are
    both accepted here.  Anything else fails the demo.
    """
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
    if result.returncode not in allow_returncodes:
        fail(f"command failed with exit code {result.returncode}")
    if result.returncode == 1:
        print("note: exit 1 means validation reported malformed lines above --")
        print("      that is a finding the tool is designed to surface, not a crash.")
    return result.returncode


def main() -> int:
    # Sanity checks so problems produce friendly messages instead of tracebacks.
    if not TRACE_STATS.is_file():
        fail(f"trace tool not found: {TRACE_STATS}")
    if not TRACES_DIR.is_dir():
        fail(f"sample trace directory not found: {TRACES_DIR}")
    if not list(TRACES_DIR.glob("*.jsonl")):
        fail(f"no .jsonl trace files found in {TRACES_DIR}")

    print("Demo 2: validate + aggregate the sample traces with trace_stats.py")
    print(f"  directory: {TRACES_DIR} ({len(list(TRACES_DIR.glob('*.jsonl')))} run file(s))")
    print(f"  tool     : {TRACE_STATS}")
    print()
    print("Each run_*.jsonl file is one harness session; every line is one event")
    print("with a fixed envelope.  Validation checks that envelope; statistics")
    print("then aggregate model/tool/error/token data across all runs.")

    run_tool([TRACE_STATS, TRACES_DIR],
             "1) Default mode: validation + aggregate text statistics",
             allow_returncodes=(0, 1))
    run_tool([TRACE_STATS, TRACES_DIR, "--stats", "--top", "5"],
             "2) --stats only (no validation gate; shorter frequency tables)")
    run_tool([TRACE_STATS, TRACES_DIR, "--json"],
             "3) --json: machine-readable report (same data, scripted-friendly)",
             allow_returncodes=(0, 1))

    print()
    print("Done: all trace_stats.py invocations above finished within the")
    print("documented exit-code contract (0 = clean, 1 = validation findings).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
