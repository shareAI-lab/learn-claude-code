# Changelog — s15 Integrated Harness

All notable changes to the `s15_integrated_harness/` lesson. The format is based on
[Keep a Changelog](https://keepachangelog.com/).

> **Snapshot note.** This file summarizes the working tree as of **2026-09-02 (UTC)**,
> while the s15 trace tooling / review workstream is still in flight. Items marked
> *(in progress)* may still change; where a change has a dedicated change note or
> review, it is referenced. Reports listed under [Sources](#sources) that do not yet
> exist on disk were still in production at snapshot time.

## [Unreleased] — snapshot 2026-09-02

### CLI additions

**New this workstream**

- **`trace_stats.py` — new trace validation + statistics CLI** (431 lines, stdlib only,
  no dependency on harness code). For every `<dir>/*.jsonl`:
  - validates each line against the schema `1.0` envelope written by
    `trace_runtime.py` (`schema_version`, `timestamp`, `monotonic_ns`, `run_id`,
    `event_id`, `event`, `data`), reporting offenders as `file:line`;
  - warns (not errors) on mid-file `run_id` changes, `schema_version` drift, a missing
    leading `run_start` / trailing `run_end`, and empty or fully malformed files;
  - aggregates per run (valid events, distinct turns, distinct agents, duration from
    `elapsed_ms`, `run_end` status) and across the directory: model calls by model,
    tool-call frequency, model stop reasons, `model_error` / `model_retry` counts,
    `tool_end` status (including a by-tool breakdown of non-`ok` outcomes), and
    approximate token totals from `model_response.data.usage` (null-safe for missing
    or `null` fields).
  - Modes: default = validation + stats; `--stats` (stats only, malformed lines
    skipped, not gated on); `--json` (machine-readable report); `--top N` truncates
    frequency tables (default 15).
  - Exit codes: `0` clean, `1` malformed lines found, `2` usage or I/O error.
  - Independent review: `trace_stats_review.md` — verdict **PASS** (validation rules
    match the recorder's real schema; stats math verified), with four open issues
    tracked under [Fixes](#fixes).
- **`trace_view.py`: new `--summary` flag.** Prints a machine-readable JSON object to
  stdout: `trace_file`; sorted `trace_files` + `trace_count` for the trace's
  directory; `event_count`; `events_by_type`; `duration_ms` (only when at least one
  event carries `monotonic_ns`); and `total_tokens` plus a `tokens` breakdown
  (`input_tokens` / `output_tokens` / `cache_tokens`, only when a `model_response`
  carries usage). Purely additive: the default human-readable rendering, the
  `--view`/`--width` interface, and exit codes are byte-for-byte unchanged, and no
  imports were added. Details: `trace_view_changes.md`.
- **`trace_stats.py` `--csv` output mode** *(in progress — not yet in the tree; the
  current file implements text + `--json` only).*

**Core lesson feature (documented in the READMEs at v15)**

- The harness CLI (`python s15_integrated_harness/code.py`) records **one JSONL trace
  per interactive process** via `trace_runtime.py` (638 lines, deliberately decoupled
  from the harness; importing the lesson or running unit tests uses
  `NullTraceRecorder` and creates no files). Files land in `traces/run_<UTC
  timestamp>_<run_id>.jsonl`, opened `0600`, line-buffered, and closed atomically by
  an `atexit` hook. Enabled by default; configured without touching the harness:
  `HARNESS_TRACE` (`0` disables), `HARNESS_TRACE_DIR` (default `traces`),
  `HARNESS_TRACE_OUTPUT` (`summary` safe default / `full`), `HARNESS_TRACE_PREVIEW_CHARS`
  (default 500).
  - Every record carries wall-clock + monotonic timestamps, `elapsed_ms`, run/turn/agent
    identity, parent agent + kind, span / parent-span IDs, causal IDs, thread identity,
    and a `data` payload. Boundary events are paired by `span_id` (`model_request →
    model_response | model_error`, outer `tool_start → tool_end` around inner
    `tool_execution_start → tool_execution_end`, agent lifecycle, background tasks,
    context prepare, permission/input waits).
  - Privacy by default: tool arguments are recursively redacted (key-name and text
    patterns: API keys, bearer/authorization headers, `sk-…` secrets, URL-embedded
    credentials); prompts, results, tasks, and messages are stored as bounded previews
    with character counts + SHA-256; `full` payloads only under
    `HARNESS_TRACE_OUTPUT=full`. Response metadata records requested action types, tool
    names, stop reason, latency, and provider token usage — never hidden
    reasoning content.
- **Trace viewer**: `trace_view.py` (603 lines, stdlib only) renders three sections —
  metrics (model/tool counts, tool mix, subagent/agent counts, max depth, max
  simultaneous active agents, tokens, model/tool time **and** overlap-merged
  `*_wall_time_ms` variants, human-only wait, workflow semaphore + agent-launch waits,
  approximate orchestration overhead), an agent/execution tree interleaving each
  agent's model calls and tools with child creation, and a parallel timeline
  (`M`/`T`/`B`/`W`/`A`/`L`/`P` symbols, `--width`). Selects the newest trace in
  `traces/` when given no path.

### Fixes

**Applied in this snapshot: none.** Code fixes are queued behind the audits; the
current file state still contains the findings below.

- `trace_stats.py` — issues from `trace_stats_review.md` (all verified against the
  current file, none fixed yet):
  - **M1 (Medium):** `--validate` is a no-op — the documented "validation only" mode
    does not exist (output and exit code are identical to default mode).
  - **L1 (Low):** I/O errors on `*.jsonl` files exit `1` instead of the documented `2`,
    and a mid-read failure (e.g. non-UTF-8 line) dies with a traceback.
  - **L2 (Low):** `--top 0` / `--top -1` produce surprising or empty tables
    (`(none observed)` shown even for non-empty counters).
  - **L3 (Low):** `--json` totals omit `tool_end_status_by_tool` (and `event_names`)
    that the text report shows.
- `code.py` — bug audit and performance audit are still in progress; their reports
  (`audit_report.md`, `perf_report.md`) are not yet on disk, and **no code.py change
  has been made in this snapshot**. Applying the top findings and the performance
  optimizations is queued as follow-up work.
- Docs: the READMEs' "Changes from s14" table says **25** built-in tools while the
  "Tools and Dispatch" section and `BUILTIN_TOOLS` itself have **26** (off-by-one in
  the table; flagged by `link_report.md`, fix pending). No Python version is stated in
  the docs, while `code.py` actually requires ≥ 3.10 (runtime-evaluated PEP 604
  unions) and `trace_runtime.py` ≥ 3.9 (`str.removeprefix`) — `hygiene_report.md`
  recommends documenting "Python 3.10+".
- Tooling: `run_tests.sh` / `make test` point at a `tests/` directory that does not
  exist yet, so `make test` currently fails with pytest's "file or directory not
  found" (hygiene finding #4); resolves once the test suite lands.

### Docs

- **Trilingual lesson README** — `README.md`, `README.zh.md`, `README.ja.md` —
  structure-aligned and synced at `v15` (footer markers match). Content includes:
  - a *Structured Execution Traces* section (trace env vars, event vocabulary with
    `span_id` pairing, viewer usage, and metric semantics — including the
    `model_time_ms` = provider-observed latency and orchestration-overhead-is-an-
    estimate caveats);
  - *Qwen/Qwen3.8-27B through Remote vLLM* (vLLM ≥ 0.17.0 serving flags with the
    `qwen3` reasoning + `qwen3_coder` tool parsers, `.env` / `ANTHROPIC_AUTH_TOKEN`
    setup, pre-flight validation guidance);
  - a *Trace Experiments* table (prompts A–E with expected trace shapes and
    comparison protocol);
  - a *Changes from s14* table (built-in tools 6 → 26, added mechanisms, event
    sources) — with the 25/26 off-by-one noted above.
- **Architecture diagrams** — three localized SVGs in `images/`:
  `system-architecture.en.svg`, `system-architecture.ja.svg`, and the Chinese
  `system-architecture.svg` (naming asymmetry noted as optional, not a defect). Each
  README references exactly its own variant. `image_audit_report.md`: 0 broken, 0
  duplicate, 0 unused references.
- **`ARCHITECTURE.md`** *(in progress — file currently ends mid-document)* — deep
  overview: thread/lifecycle table and lock inventory, the integrated agent-loop
  walkthrough (cron/background injection, compaction, tool-pool assembly, retry and
  max-tokens recovery, `harness_decision` events), tool dispatch (two explicit tables,
  per-block dispatch path, cwd scoping, child tool pools), the layered permission
  boundary (workspace scoping, `permission_hook`, async-turn fail-closed rule,
  teammate plan gate), and the hook system.
- **Audit / review notes in-tree** (read-only deliverables, no files modified by them):
  `trace_view_changes.md`, `trace_stats_review.md`, `image_audit_report.md`,
  `link_report.md` (0 broken links across the READMEs; 18 references `unverified` by
  policy — cross-dir lesson links and external URLs; all README command fences and
  named code symbols spot-checked against the actual source), and `hygiene_report.md`
  (syntax verification, Python-version analysis, stray artifacts, suggested
  `.gitignore` block).
- **`USAGE.md` quickstart** *(in progress — not yet on disk).*

### Tests

- **`Makefile`** — `test` (delegates to `run_tests.sh`), `lint`
  (`python3 -m py_compile` over all four modules — the authoritative byte-compile
  gate), and `clean` (removes `.pytest_cache`, `__pycache__` dirs, stray `*.pyc`).
- **`run_tests.sh`** — portable POSIX sh runner: pins cwd to the lesson root,
  `python3` → `python` fallback, verifies pytest is installed, then
  `pytest tests/ -v`.
- **`tests/` suite** *(in progress — not yet on disk; no pytest run has happened in
  the lesson dir, no `.pytest_cache` present).* Edge-case trace fixtures and
  robustness tests, plus a coverage review, are queued as follow-up.
- Hygiene context (`hygiene_report.md`): `__pycache__/` holds 6 stale `.pyc` files
  from two interpreter generations (CPython 3.12 + 3.14) — safe to `make clean`;
  live harness runtime state (`.tasks/`, `.transcripts/`, `.mailboxes/`,
  `.task_outputs/tool-results/`) exists because runs were started with the lesson dir
  as cwd — it is live session state, leave on disk but ignore via the suggested
  `.gitignore` block.

### Samples & assets

- **`traces/`** — four recorded runs under Python 3.12 against `Qwen/Qwen3.8-27B` via
  an Anthropic-compatible endpoint: three complete runs
  (`run_20260901T193828_…_83ce7412`, `run_20260901T200234_…_717f03f3`,
  `run_20260902T002404_…_4739e3b3`) plus one written by a live session at audit time
  (`run_20260902T004901_…_dc6a9685`, no `run_end` yet). Curation decision (keep a
  small committed sample set, ignore the rest) is pending; do not commit a file
  mid-write.

### Sources

Based on: `trace_view_changes.md`; `trace_stats_review.md`, `image_audit_report.md`,
`link_report.md`, `hygiene_report.md`; the trilingual READMEs (v15); `ARCHITECTURE.md`
(as of snapshot); full reads of `code.py` (3710 lines), `trace_runtime.py` (638),
`trace_view.py` (603), `trace_stats.py` (431); `Makefile`; `run_tests.sh`; `images/`;
`traces/` (envelope + event checks).

Not yet present on disk at snapshot time (in progress, to be folded in when they land):
`audit_report.md` and `perf_report.md` (code.py bug + performance audits), `USAGE.md`
(quickstart), `tests/` (suite + edge-case fixtures), and the trace-analysis findings.
