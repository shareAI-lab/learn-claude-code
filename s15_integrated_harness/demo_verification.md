# Demo verification — s15_integrated_harness/examples/

Task: run every script in `examples/` end-to-end from the repo root, capture
stdout/stderr and exit codes, and verify each demo produces the output
promised in its docstring. Per the task rules, only demo scripts may be
fixed — `code.py` and the library tools (`trace_view.py`, `trace_stats.py`,
`trace_runtime.py`) are off-limits; failures that originate in the tools are
documented here instead.

**Execution status (important).** The verification agent's sandbox blocks the
shell tool for asynchronous turns ("interactive shell approval is
unavailable during an asynchronous turn"), so the demos were **not executed
by that agent**. The commands below were handed to the lead (main thread,
where interactive approval is available) for execution; exit codes and
observed output are recorded per demo below, marked **PENDING** until the
lead's run is reported. The exact working directory for the delegated runs
is `/home1/11791/friedrichqi04/learn-claude-code/s15_integrated_harness`
(the demos are cwd-independent: every path resolves relative to the script
file itself, so any working directory yields identical behavior).
Everything else in this document (CLI-surface
matching, JSON-schema matching, sample-data checks, expected behavior per
code path) is a full static verification performed by reading the demo
scripts, the two tools they invoke, and the sample trace files.

**Demo set verified (3 scripts):**

- `examples/demo1_view_latest_trace.py`
- `examples/demo2_validate_and_stats.py`
- `examples/demo3_compare_all_traces.py`

**Sample data present at verification time (4 files in `traces/`):**

| File | Lines | First event | Last event | Notes |
| --- | --- | --- | --- | --- |
| `run_20260901T193828_408312Z_83ce7412.jsonl` | 74 | `agent_start` (evt_000002) | `run_end` status=completed | head line (`run_start`) missing from the saved sample |
| `run_20260901T200234_810844Z_717f03f3.jsonl` | 72 | `agent_start` (evt_000002) | `run_end` status=completed | same |
| `run_20260902T002404_246018Z_4739e3b3.jsonl` | 113 | `agent_start` (evt_000002) | `run_end` status=completed | same |
| `run_20260902T004901_584576Z_dc6a9685.jsonl` | 5500+ and growing | `agent_start` (evt_000002) | mid-run (no `run_end` yet) | **live trace of the current session** — grows while demos run |

Every inspected line carries the full fixed envelope
(`schema_version`, `timestamp`, `monotonic_ns`, `run_id`, `event_id`,
`event`, `data`, ...), so `trace_stats.py` validation is expected to report
**OK** (exit 0) with warning-level findings only:

- all 4 files: "first event is 'agent_start', expected 'run_start' (file may
  be a fragment)" — because the samples omit their first line;
- the live file additionally: "last event is ..., no 'run_end' (run
  interrupted or still recording?)" — because it is still being recorded.

Warnings do not affect the exit code in `trace_stats.py` (only hard
malformed-line errors do, exit 1).

---

## Demo 1 — `demo1_view_latest_trace.py`

**Promised behavior (docstring):** view one trace (default: newest file in
`../traces/`, or `--trace <path>`) with `trace_view.py`:
(1) `--view metrics`, (2) `--view timeline --width 100`,
(3) `--summary` JSON (event counts, duration, token totals); optional
`--with-tree` runs the default view (metrics + agent/execution tree) first.
Prints each command with `$ ...`, its stdout/stderr, and `(exit code: N)`;
exits non-zero with a friendly `error: ...` message if any invocation fails
or if `trace_view.py` / `traces/` / the trace file is missing. Stdlib only.

**Command (run from the repo root):**

```sh
python3 examples/demo1_view_latest_trace.py
# and the opt-in mode:
python3 examples/demo1_view_latest_trace.py --with-tree
```

**Exit code:** PENDING (expected 0)

**Verdict:** PENDING execution — static verification PASS, see below.

**Fixes made:** none.

**Static verification (passed):**

- Path resolution: `PARENT_DIR = Path(__file__).resolve().parent.parent` →
  `s15_integrated_harness/`; `TRACE_VIEW` and `TRACES_DIR` exist.
- `latest_trace()` uses the same convention as `trace_view._latest_trace`
  (newest by mtime of `run_*.jsonl`); 4 candidate files present.
- All four subprocess invocations match the current `trace_view.py` CLI:
  - `trace_view.py <trace>` → default `--view both` (metrics + tree +
    timeline) — valid.
  - `--view metrics` — valid choice.
  - `--view timeline --width 100` — `--width` exists (int, default 90).
  - `--summary` — exists (added by task task_78e5b648); prints a JSON
    document with `trace_file`, `trace_files`, `trace_count`, `event_count`,
    `events_by_type`, `duration_ms`, `total_tokens`, `tokens{...}` — matching
    the docstring's "event counts, duration, token totals".
- None of the four sample traces contain lines that would trip
  `load_trace` (every line is a JSON object with a string `event` field —
  verified on the first/last lines of each file; the validator used by the
  tool raises only on non-dict lines or missing `event`).
- Docstring nuance (cosmetic, not a failure): the default view prints
  metrics + tree **+ timeline** (`--view both`), while the docstring
  describes it as "metrics *plus* the full agent/execution tree". The
  promised sections are all present; the extra timeline is additive.

**Observed output:** PENDING (lead execution).

---

## Demo 2 — `demo2_validate_and_stats.py`

**Promised behavior (docstring):** validate + aggregate all sample traces in
`../traces/` with `trace_stats.py` in three modes: (1) default
(validation + text statistics), (2) `--stats --top 5` (stats only, shorter
tables), (3) `--json` (machine-readable report). Treats exit codes 0 (clean)
and 1 (validation findings) as successful demo runs; prints a note when exit
1 occurs. Exits non-zero with `error: ...` if the tool, the directory, or
any `.jsonl` file is missing, or if a tool invocation exits with 2.
Stdlib only.

**Command (run from the repo root):**

```sh
python3 examples/demo2_validate_and_stats.py
```

**Exit code:** PENDING (expected 0)

**Verdict:** PENDING execution — static verification PASS, see below.

**Fixes made:** none.

**Static verification (passed):**

- All three subprocess invocations match the current `trace_stats.py` CLI:
  positional `directory`, `--validate`/`--stats` (mutually exclusive),
  `--top <int>` (default 15), `--json`.
- Exit-code contract matches the tool's `main()`:
  - default mode → returns 1 iff hard malformed lines found, else 0;
  - `--stats` mode → always 0 (validation is skipped, not gated on);
  - `--json` in default mode → same 0/1 contract as default, JSON on stdout.
  The demo's `allow_returncodes=(0, 1)` for modes 1 and 3 and `(0, 1)`
  (default) for mode 2 therefore always accept the legitimate outcomes.
- Expected validation outcome for the current sample data: **exit 0** with
  "OK: all N lines across 4 file(s) are well-formed" plus the
  fragment/no-run_end **warnings** listed at the top of this document.
  (Warnings are printed but do not change the exit code, so the demo will
  *not* print its "exit 1 means ..." note under current data.)
- The demo's stderr handling prints tool stderr verbatim; the tools print to
  stderr only on usage/I-O errors (exit 2), which cannot occur here because
  the directory and files exist.
- Docstring nuance (cosmetic): "A clean directory ends with status `OK`" —
  the tool prints "OK: all ... well-formed" under the `Validation` heading;
  wording matches in substance.

**Observed output:** PENDING (lead execution).

---

## Demo 3 — `demo3_compare_all_traces.py`

**Promised behavior (docstring):** loop over every `run_*.jsonl` in
`../traces/` and run `trace_view.py <file> --view metrics` per run for
side-by-side comparison; then run `trace_stats.py <dir> --stats --json`,
parse the JSON, and print a compact per-run table
(run id, events, turns, agents, duration, status) plus directory-wide
totals (records, model calls, tool calls, model errors, approximate token
sum). Friendly `error: ...` + non-zero exit if the tools/directory/traces
are missing, if any tool exits non-zero, or if the JSON does not parse.
Stdlib only.

**Command (run from the repo root):**

```sh
python3 examples/demo3_compare_all_traces.py
```

**Exit code:** PENDING (expected 0)

**Verdict:** PENDING execution — static verification PASS, see below.

**Fixes made:** none.

**Static verification (passed):**

- Step 1: one `trace_view.py <file> --view metrics` call per trace file —
  valid CLI; every sample file passes `load_trace`.
- Step 2: `trace_stats.py <dir> --stats --json`:
  - `--stats` forces exit 0 (validation not gated on), so stdout is exactly
    one JSON document — parseable;
  - schema cross-checked field by field against `render_json()`:
    - `files[]`: `run_id` ✓, `events` ✓, `turns` ✓, `agents` ✓,
      `duration_ms` ✓, `run_end_status` ✓ (all present in the JSON the tool
      emits; the demo also handles `run_end_status: null` via
      `or "unknown (no run_end)"`, which is exactly what the live fragment
      file will produce);
    - `totals`: `records` ✓, `model_calls` ✓, `tool_calls` (dict; demo sums
      `.values()`) ✓, `model_errors` (dict; demo sums `.values()`) ✓,
      `input_tokens` / `output_tokens` / `cache_creation_input_tokens` /
      `cache_read_input_tokens` ✓ — every key the demo reads exists.
- `fail()` after a non-zero tool exit cannot be triggered: all 4 per-run
  metrics calls operate on loadable files, and the aggregate call exits 0
  in `--stats` mode.
- Docstring nuance (cosmetic): the four sample file names listed in the
  docstring match the directory contents exactly at verification time; the
  demo itself loops over the glob, so added/removed samples would not break
  it (the live file is one of the four listed).

**Observed output:** PENDING (lead execution).

---

## Summary

| Demo | Command | Exit code | Verdict | Fixes made |
| --- | --- | --- | --- | --- |
| 1 view latest trace | `python3 examples/demo1_view_latest_trace.py` | PENDING (expected 0) | PENDING — static PASS | none |
| 1 (opt-in) with tree | `python3 examples/demo1_view_latest_trace.py --with-tree` | PENDING (expected 0) | PENDING — static PASS | none |
| 2 validate + stats | `python3 examples/demo2_validate_and_stats.py` | PENDING (expected 0) | PENDING — static PASS | none |
| 3 compare all traces | `python3 examples/demo3_compare_all_traces.py` | PENDING (expected 0) | PENDING — static PASS | none |

No demo-script bugs were found, so no demo script was modified. No tool or
library code was touched. The only open item is the actual execution, which
requires a main-thread (interactive-approval) shell and was delegated to the
lead; results will be filled into the table and each demo section as soon
as the run is reported.
