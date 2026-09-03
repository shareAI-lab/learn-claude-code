#!/usr/bin/env python3
"""Demo 1 -- View one trace with trace_view.py.

What this demo shows
--------------------
``trace_view.py`` renders a single harness JSONL trace (one file per CLI run,
written to ``traces/`` by ``trace_runtime.py``) in three compact ways:

  1. ``--view metrics``  derived numbers: model/tool call counts, token usage,
                         wall-clock vs. summed model/tool time, human wait,
                         orchestration overhead, ...
  2. ``--view timeline`` an ASCII Gantt-style chart: one row per agent, one
                         column per moment of the run.  Letters name the kind
                         of span (M=model, T=tool, B=background tool,
                         W=workflow node, A=active cycle, L=lifecycle,
                         P=user/permission wait).
  3. ``--summary``       a machine-readable JSON summary (event counts,
                         duration, token totals).

The default view (no ``--view``) prints metrics *plus* the full agent/execution
tree, which interleaves every agent's model calls, tools, and child agents.
For long runs that tree can be hundreds of lines, so it is opt-in here via
``--with-tree`` -- pass the flag to see it.

Usage (works from any working directory; paths are resolved relative to this
script, so no setup is needed)::

    python3 examples/demo1_view_latest_trace.py
    python3 examples/demo1_view_latest_trace.py --trace traces/run_....jsonl
    python3 examples/demo1_view_latest_trace.py --with-tree

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

# examples/ lives inside s15_integrated_harness/, so the trace tool and the
# sample traces are always exactly one directory up from this script.
PARENT_DIR = Path(__file__).resolve().parent.parent
TRACE_VIEW = PARENT_DIR / "trace_view.py"
TRACES_DIR = PARENT_DIR / "traces"


def fail(message: str) -> "None":
    """Print a friendly error (not a traceback) and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def latest_trace() -> Path:
    """Pick the newest sample trace, same convention as trace_view.py itself."""
    candidates = sorted(TRACES_DIR.glob("run_*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        fail(f"no run_*.jsonl sample traces found in {TRACES_DIR}")
    return candidates[-1]


def run_tool(args: list[str], title: str) -> None:
    """Run one trace-tool invocation, echo the command, print its output.

    Exits the demo with a clear message if the tool reports failure.
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
    if result.returncode != 0:
        fail(f"command failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--trace", type=Path, default=None,
        help="trace JSONL to view (default: newest file in ../traces/)",
    )
    parser.add_argument(
        "--with-tree", action="store_true",
        help="also print the default metrics + agent-tree view "
             "(can be very long for big runs)",
    )
    args = parser.parse_args()

    # Sanity checks so problems produce friendly messages instead of tracebacks.
    if not TRACE_VIEW.is_file():
        fail(f"trace tool not found: {TRACE_VIEW}")
    if not TRACES_DIR.is_dir():
        fail(f"sample trace directory not found: {TRACES_DIR}")
    trace = args.trace or latest_trace()
    if not trace.is_file():
        fail(f"trace file not found: {trace}")

    print("Demo 1: view one trace with trace_view.py")
    print(f"  trace: {trace}")
    print(f"  tool : {TRACE_VIEW}")
    print()
    print("A JSONL trace has one JSON object per event (run_start, model_request,")
    print("tool_start, agent_create, run_end, ...).  trace_view.py pairs boundary")
    print("events into spans and derives the views below from them.")

    if args.with_tree:
        # Default view: metrics + the full agent/execution tree.
        run_tool([TRACE_VIEW, trace], "Default view: metrics + agent/execution tree")

    run_tool([TRACE_VIEW, trace, "--view", "metrics"],
             "1) Derived metrics for this run")
    run_tool([TRACE_VIEW, trace, "--view", "timeline", "--width", "100"],
             "2) ASCII timeline: one row per agent across the run")
    run_tool([TRACE_VIEW, trace, "--summary"],
             "3) Machine-readable JSON summary")

    print()
    print("Done: all trace_view.py invocations above exited 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
