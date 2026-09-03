# Contributing — s15 Integrated Harness

Guidelines for working in `s15_integrated_harness/`. Everything here is verified
against the files in this directory; every command below references files and
flags that exist as written.

**Short orientation.** `code.py` is the lesson itself: one agent loop with tools,
permissions, hooks, tasks, teams, worktrees, compaction, background bash, cron,
memory, skills, and MCP. Around it sit small **standard-library-only** tools for
the JSONL traces that loop records: `trace_view.py`, `trace_stats.py`,
`scripts/`, `examples/`, and `tests/`.

## Prerequisites

| Component | Python | Dependencies |
| --- | --- | --- |
| Harness CLI (`code.py`) | **3.10+** (runtime-evaluated PEP 604 annotations such as `str \| None` in `ConsoleBroker.ask`; also uses 3.9+ APIs like `Path.is_relative_to`) | `pip install anthropic python-dotenv pyyaml` (per `code.py`'s docstring), plus a `.env` with `MODEL_ID` and `ANTHROPIC_API_KEY` |
| Trace tooling, benchmark, demos, tests (`trace_view.py`, `trace_stats.py`, `scripts/*`, `examples/*`, `tests/*`) | 3.8+ (the lesson is developed and run on CPython 3.12/3.14) | **None — Python standard library only, no pip installs** (`pytest` only if you run the suite via `run_tests.sh`; the smoke test also runs standalone) |

Notes:

- `code.py` imports `fcntl` (file locking), `signal`, and process groups — it
  targets POSIX systems (Linux/macOS).
- A `.env` at the repository root works: `code.py` calls
  `load_dotenv(override=True)` and reads `MODEL_ID` from the environment at
  import time (`os.environ["MODEL_ID"]` — it raises `KeyError` without it).

## Running the main loop (`code.py`)

`code.py` is an **interactive REPL, not a flag-driven CLI**: it has no
`argparse` and takes no command-line arguments. The prompt is `s15 >> `; type
`q`, `exit`, or an empty line to quit. All configuration is by environment
variable (verified in `code.py` and `trace_runtime.py`):

| Variable | Required | Default | Effect |
| --- | --- | --- | --- |
| `MODEL_ID` | yes | — | model used for all calls |
| `ANTHROPIC_API_KEY` | yes (for the provider) | via `.env` | provider auth |
| `ANTHROPIC_BASE_URL` | no | Anthropic API | endpoint override (e.g. a remote vLLM `/v1/messages`) |
| `FALLBACK_MODEL_ID` | no | none | fallback model after repeated 529 errors |
| `HARNESS_TRACE` | no | on | `0`/`false`/`no`/`off` disables tracing |
| `HARNESS_TRACE_DIR` | no | `traces` (relative to the working directory) | where `run_*.jsonl` files are written |
| `HARNESS_TRACE_OUTPUT` | no | `summary` | `full` additionally stores complete redacted payloads |
| `HARNESS_TRACE_PREVIEW_CHARS` | no | `500` | preview length in bounded trace fields |

The working directory matters: `code.py` sets `WORKDIR = Path.cwd()` and creates
runtime state (`.tasks/`, `.transcripts/`, `.mailboxes/`,
`.task_outputs/tool-results/`, `traces/`) there. Run it from the repository root
(as the README does), or from anywhere you are happy for that state to live.

Examples:

```sh
# 1) Standard run (repo root has a .env with MODEL_ID + ANTHROPIC_API_KEY)
cd learn-claude-code
python s15_integrated_harness/code.py

# 2) Same run with tracing disabled
HARNESS_TRACE=0 python s15_integrated_harness/code.py

# 3) Point at a remote Anthropic-compatible endpoint (e.g. vLLM, see README)
ANTHROPIC_API_KEY=EMPTY \
ANTHROPIC_BASE_URL=http://your-vllm-host:8000 \
python s15_integrated_harness/code.py
```

On start, a traced run prints `[trace] <path>` — the `traces/run_<UTC
timestamp>_<run_id>.jsonl` file being written for that process.

## Running the tests

```sh
# Full suite (run_tests.sh is POSIX sh; `make test` delegates to it)
sh run_tests.sh
# or
make test

# A single test file via pytest
python3 -m pytest tests/test_cli_smoke.py -v

# Or standalone — no pytest required (prints PASS/FAIL per test, exits 1 on failure)
python3 tests/test_cli_smoke.py
```

- `run_tests.sh` pins cwd to the lesson root, honors `PYTHON` (default
  `python3`, falling back to `python`), checks that pytest is installed
  (`pip install pytest`), then runs `python3 -m pytest tests/ -v`.
- The current suite is `tests/test_cli_smoke.py`: end-to-end smoke tests that run
  `trace_view.py` and `trace_stats.py` as subprocesses against a self-contained
  sample trace generated in a temp directory. It needs no `anthropic` package, no
  model server, and leaves no fixture files in the repo.
- `make lint` byte-compiles every module in the directory (run it before
  committing); `make clean` removes `.pytest_cache`, `__pycache__/`, and stray
  `*.pyc` files.

## Running the benchmark

`scripts/benchmark.py` (stdlib only) times the two trace CLIs as real subprocess
calls — `trace_stats.py` once over the whole traces directory, `trace_view.py`
once per trace file — and reports the best (minimum) wall time per command,
interpreter startup included.

Actual CLI (verified in `scripts/benchmark.py`):

```sh
python3 scripts/benchmark.py                 # default: <this dir>/traces, best of 3 runs
python3 scripts/benchmark.py traces          # explicit traces dir
python3 scripts/benchmark.py traces --runs 5 # more runs per command (--runs must be >= 1)
```

Exit codes: `0` = all commands ran; `1` = at least one command reported a
validation/processing error (still timed, e.g. `trace_stats.py` finding malformed
lines); `2` = usage or setup error (bad directory, missing script, no `.jsonl`
files).

## Generating, viewing, and summarizing traces

### Generate

Running `code.py` (with tracing enabled, the default) writes one JSONL file per
CLI process to `HARNESS_TRACE_DIR` (default `traces/` relative to the working
directory): `run_<UTC timestamp>_<run_id>.jsonl`, opened `0600`, one JSON object
per line, flushed immediately, closed with a `run_end` record on normal exit and
via `atexit`. Sample runs are committed under `traces/`.

### View one trace — `trace_view.py`

```
python3 trace_view.py [trace.jsonl] [--view {both,tree,timeline,metrics}] [--width N] [--summary]
```

- With no path, it picks the newest `run_*.jsonl` in `traces/` **relative to the
  current working directory** (so run it from inside `s15_integrated_harness/`
  to view the bundled samples).
- `--view` default `both` = metrics + agent/execution tree; `timeline` draws the
  per-agent ASCII chart, `metrics` prints only the derived numbers.
- `--width` (default `90`) sets the timeline chart width.
- `--summary` prints a machine-readable JSON summary (event counts by type,
  duration, token totals) instead of the human-readable sections.
- Exit codes: `0` ok; `2` usage or I/O error (missing file, invalid JSON, empty
  trace).

```sh
cd s15_integrated_harness

# Newest bundled sample, default view (metrics + tree)
python3 trace_view.py

# A specific sample: just the timeline, wider
python3 trace_view.py traces/run_20260901T193828_408312Z_83ce7412.jsonl --view timeline --width 120

# Machine-readable summary for scripting
python3 trace_view.py traces/run_20260901T193828_408312Z_83ce7412.jsonl --summary
```

### Validate + summarize all runs — `trace_stats.py`

```
python3 trace_stats.py <dir> [--validate | --stats] [--top N] [--json]
```

- Default mode: validate every line of every `<dir>/*.jsonl` against the schema
  `1.0` envelope, then print per-run facts and directory-wide aggregates
  (models, tool frequency, stop reasons, errors/retries, token totals).
- `--stats`: stats only; malformed lines are skipped, not gated on.
- `--validate`: the documented validation mode; in the current implementation it
  renders the same sections as the default mode (see `trace_stats_review.md`,
  finding M1) — the exit-code contract is the same either way.
- `--top N` (default `15`) truncates frequency tables; `--json` emits the
  machine-readable report.
- Exit codes: `0` clean; `1` malformed lines found (default/`--validate` modes);
  `2` usage or I/O error (missing or non-directory path).

```sh
cd s15_integrated_harness

python3 trace_stats.py traces
python3 trace_stats.py traces --stats --top 5
python3 trace_stats.py traces --json
```

### HTML workflow visualization

```sh
# Self-contained HTML (no external assets) from one trace; safe to regenerate
# while the traced run is still writing (open spans are marked "open at snapshot")
python3 scripts/trace_workflow_viz.py traces/run_20260901T193828_408312Z_83ce7412.jsonl -o out.html
```

`-o/--output` defaults to `trace_workflow_viz.html`.

### Self-contained demos

`examples/` walks the tools on the bundled samples; each script resolves paths
relative to its own location, so it works from any working directory
(stdlib only):

```sh
python3 examples/demo1_view_latest_trace.py          # trace_view.py: metrics, timeline, --summary
python3 examples/demo1_view_latest_trace.py --with-tree --trace traces/run_....jsonl
python3 examples/demo2_validate_and_stats.py         # trace_stats.py: default, --stats --top 5, --json
python3 examples/demo3_compare_all_traces.py         # per-run metrics + cross-run table
```

See `examples/README.md` for what each demo shows.

## Project layout

| File / dir | Purpose |
| --- | --- |
| `code.py` | The integrated harness: agent loop, 26 built-in tools + dynamic MCP tools, hooks/permission, todo + task graph, subagents/teams, worktrees, layered compaction, background bash, cron, memory/skills. REPL entry point — env-var configuration, no CLI flags. |
| `trace_runtime.py` | Structured JSONL trace recorder (schema `1.0`): envelope, span pairing, credential redaction, bounded previews + SHA-256. Created only by the CLI entry point; imports/tests get a no-op `NullTraceRecorder`. |
| `trace_view.py` | Stdlib viewer for one trace: `--view both/tree/timeline/metrics`, `--width`, `--summary` JSON. |
| `trace_stats.py` | Stdlib validator + cross-run aggregator for a directory of traces: `--validate`/`--stats`, `--top`, `--json`. |
| `scripts/benchmark.py` | Best-of-N wall-time benchmark of `trace_stats.py` + `trace_view.py` over a traces directory (`[traces_dir]`, `--runs`). |
| `scripts/trace_workflow_viz.py` | Renders one trace as a self-contained HTML workflow visualization (`trace`, `-o/--output`). |
| `examples/` | Three self-contained stdlib demos of the trace tools (`demo1` supports `--trace`, `--with-tree`); see `examples/README.md`. |
| `tests/test_cli_smoke.py` | End-to-end CLI smoke tests for `trace_view.py`/`trace_stats.py`; runs under pytest or standalone. |
| `run_tests.sh`, `Makefile` | Test entry points: `sh run_tests.sh` / `make test` (pytest), `make lint` (byte-compile), `make clean`. |
| `traces/*.jsonl` | Sample recorded runs (one per CLI process). **Append-only data** — see Conventions. |
| `images/*.svg` | Localized system-architecture diagrams (`.en.svg`, `.ja.svg`, Chinese `system-architecture.svg`), each referenced by its own README. |
| `README.md` / `README.zh.md` / `README.ja.md` | Trilingual lesson docs (synced at v15 per their footer markers). |
| `ARCHITECTURE.md`, `DESIGN.md` | Deep-dive architecture overview; compaction design doc. |
| `CHANGELOG.md` | Change history for this lesson directory. |
| `hygiene_report.md`, `image_audit_report.md`, `link_report.md`, `link_audit_report.md`, `trace_stats_review.md`, `trace_view_changes.md` | Read-only audit/review notes and change notes produced during tooling work. |

## Conventions

- **Type hints and docstrings on all new/changed code.** Every module in this
  directory is fully annotated (with `from __future__ import annotations` where
  needed); keep it that way.
- **No third-party dependencies outside `code.py`.** The trace tools,
  `scripts/`, `examples/`, and `tests/` are stdlib-only on purpose — that is what
  keeps the smoke tests and demos runnable anywhere. `code.py`'s declared
  dependency set is `anthropic`, `python-dotenv`, `pyyaml` (its docstring is the
  source of truth).
- **Treat `traces/*.jsonl` as append-only data.** Do not hand-edit, reformat, or
  truncate recorded traces: the recorder appends one flushed line per event,
  files are opened `0600`, and a missing trailing `run_end` is a *running*
  session, not corruption (`trace_stats.py` reports it as a warning, not an
  error). Viewers and the benchmark are read-only consumers; new tooling should
  stay that way.
- **CLI tools follow the 0/1/2 exit-code convention**: `0` clean, `1` a
  validation/processing finding (still a successful run), `2` usage or I/O
  error — and each carries a `Usage:` docstring, like `trace_stats.py` and
  `scripts/benchmark.py`.
- **Tests are self-contained**: build their input in temp directories (as
  `tests/test_cli_smoke.py` does), assert on exit codes and stdout, and leave no
  fixture files in the repo.
- **Keep the tree clean**: run `make lint` before committing; do not commit
  `__pycache__/` or live harness runtime state (`.tasks/`, `.transcripts/`,
  `.mailboxes/`, `.task_outputs/`) — `make clean` removes the build artifacts.

## Further reading

- `README.md` (and `README.zh.md`, `README.ja.md`) — lesson content, model/vLLM
  setup, trace experiments.
- `ARCHITECTURE.md` — threads, agent loop, dispatch, permission layers.
- `DESIGN.md` — the compaction pipeline and trace data flow.
- `CHANGELOG.md` — what changed and where findings are tracked.
