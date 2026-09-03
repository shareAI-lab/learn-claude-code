#!/usr/bin/env python3
"""Benchmark harness: time trace_stats.py and trace_view.py over the traces/.

Usage:
    python3 scripts/benchmark.py [traces_dir]     # default: <repo>/traces
    python3 scripts/benchmark.py traces --runs 5

The harness runs each command 3 times (default) and reports the best (minimum)
wall time per command, in milliseconds.  Wall time is measured around a real
subprocess invocation, so interpreter startup is included.

Coverage of "every trace in the traces/ dir":
  * trace_stats.py accepts a directory and processes all run_*.jsonl files in
    it in one invocation, so it is timed once against the whole directory.
  * trace_view.py takes a single trace file, so it is timed once per trace
    file to cover every trace.

Exit codes: 0 = all commands ran, 1 = at least one command reported a
validation/processing error (still timed), 2 = usage or setup error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACES_DIR = REPO_ROOT / "traces"

# script name -> (path, exit codes that count as "ran to completion")
# trace_stats.py: 0 = clean, 1 = malformed lines found (validation result,
# not a harness failure), 2 = usage or I/O error.
# trace_view.py: 0 = ok, 2 = argparse/IO error.
SCRIPTS = {
    "trace_stats.py": (REPO_ROOT / "trace_stats.py", {0, 1}),
    "trace_view.py": (REPO_ROOT / "trace_view.py", {0}),
}


@dataclass
class Row:
    script: str
    target: str          # human-readable description of what is being timed
    argv: List[str]      # full command line
    ok_codes: Set[int]   # exit codes considered a successful run

    @property
    def display_cmd(self) -> str:
        return " ".join(argv_display(part) for part in self.argv)


def argv_display(part: str) -> str:
    """Show argv entries relative to the repo root where possible."""
    try:
        path = Path(part)
        if path.is_absolute():
            return str(path.relative_to(REPO_ROOT))
    except ValueError:
        pass
    return part


@dataclass
class Result:
    best_ms: Optional[float] = None
    all_ms: List[float] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


def time_row(row: Row, runs: int) -> Result:
    """Run row.argv `runs` times; return best wall time and exit details."""
    result = Result(all_ms=[])
    for _ in range(runs):
        start = time.monotonic()
        proc = subprocess.run(
            row.argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        elapsed_ms = (time.monotonic() - start) * 1000.0
        result.all_ms.append(elapsed_ms)
        result.best_ms = (
            elapsed_ms if result.best_ms is None else min(result.best_ms, elapsed_ms)
        )
        result.exit_code = proc.returncode
        if proc.returncode not in row.ok_codes:
            stderr = (proc.stderr or "").strip()
            result.error = stderr.splitlines()[-1] if stderr else None
            break  # hard failure: further runs would just repeat it
    return result


def build_rows(traces_dir: Path) -> List[Row]:
    python = sys.executable or "python3"
    files = sorted(traces_dir.glob("*.jsonl"))
    rows: List[Row] = []
    stats_path, stats_ok = SCRIPTS["trace_stats.py"]
    rows.append(
        Row(
            script="trace_stats.py",
            target="all %d file(s) in %s/" % (len(files), traces_dir.name),
            argv=[python, str(stats_path), str(traces_dir)],
            ok_codes=stats_ok,
        )
    )
    view_path, view_ok = SCRIPTS["trace_view.py"]
    for file in files:
        rows.append(
            Row(
                script="trace_view.py",
                target=file.name,
                argv=[python, str(view_path), str(file)],
                ok_codes=view_ok,
            )
        )
    return rows


def print_table(rows: List[Row], results: List[Tuple[Row, Result]],
                traces_dir: Path, runs: int) -> None:
    header = ("script", "target", "best ms (of %d)" % runs, "exit", "status")
    table = [header]
    for row, res in results:
        if res.best_ms is None:
            best = "-"
        else:
            best = "%.1f" % res.best_ms
        status = "ok"
        if res.error is not None:
            status = "FAILED"
        elif res.exit_code not in row.ok_codes:
            status = "rc=%d" % res.exit_code
        elif row.ok_codes != {0}:
            # e.g. trace_stats.py reporting malformed lines
            status = "rc=%d (validated w/ errors)" % res.exit_code
        table.append((row.script, row.target, best,
                      str(res.exit_code) if res.exit_code is not None else "-",
                      status))

    widths = [max(len(line[i]) for line in table) for i in range(len(header))]
    fmt = "  ".join("%%-%ds" % w for w in widths)
    print(fmt % tuple(header))
    print(fmt % tuple("-" * w for w in widths))
    for line in table[1:]:
        print(fmt % line)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Time trace_stats.py and trace_view.py over every trace in "
                    "the traces/ dir (best of N wall times).",
    )
    parser.add_argument("traces_dir", nargs="?", default=str(DEFAULT_TRACES_DIR),
                        help="directory of run_*.jsonl traces (default: %(default)s)")
    parser.add_argument("--runs", type=int, default=3,
                        help="runs per command; the best (minimum) is reported "
                             "(default: %(default)s)")
    args = parser.parse_args(argv)

    if args.runs < 1:
        parser.error("--runs must be >= 1")

    traces_dir = Path(args.traces_dir)
    if not traces_dir.is_dir():
        print("error: not a directory: %s" % traces_dir, file=sys.stderr)
        return 2
    for name, (path, _ok) in SCRIPTS.items():
        if not path.is_file():
            print("error: script not found: %s" % path, file=sys.stderr)
            return 2

    files = sorted(traces_dir.glob("*.jsonl"))
    if not files:
        print("error: no .jsonl trace files found in %s" % traces_dir,
              file=sys.stderr)
        return 2

    rows = build_rows(traces_dir)
    results: List[Tuple[Row, Result]] = []
    for row in rows:
        results.append((row, time_row(row, args.runs)))

    try:
        rel = traces_dir.resolve().relative_to(REPO_ROOT)
        traces_label = str(rel)
    except ValueError:
        traces_label = str(traces_dir)
    print("Benchmark: %d trace(s) in %s, best of %d runs "
          "(wall ms, includes interpreter startup)"
          % (len(files), traces_label, args.runs))
    print()
    print_table(rows, results, traces_dir, args.runs)

    print()
    print("Commands timed:")
    for row, _res in results:
        print("  %s" % row.display_cmd)

    had_validation_errors = any(
        res.exit_code not in row.ok_codes and res.error is None
        for row, res in results
    )
    had_failures = any(res.error is not None for _row, res in results)
    if had_failures:
        print("\nFAILED commands:", file=sys.stderr)
        for row, res in results:
            if res.error is not None:
                print("  %s [%s] -> exit %d: %s"
                      % (row.script, row.target, res.exit_code, res.error),
                      file=sys.stderr)
        return 2
    return 1 if had_validation_errors else 0


if __name__ == "__main__":
    sys.exit(main())
