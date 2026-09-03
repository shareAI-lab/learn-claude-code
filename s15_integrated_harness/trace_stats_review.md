# Review: trace_stats.py (trace validation/stats CLI)

**Task:** task_2e00bc77 deliverable — `s15_integrated_harness/trace_stats.py`
**Reviewed by:** test-reviewer
**Method:** full code reading of `trace_stats.py` (431 lines), `trace_runtime.py` (the writer, in full), `code.py` (the emitter, all 3710 lines), and cross-checking against the four sample traces in `traces/*.jsonl` (heads + tails of all four; mid-section of the large one). Bash was unavailable in this session, so verification is by careful code reading, as the task specifies.

## Verdict: PASS (with minor, non-blocking issues)

The validation rules match the schema the recorder actually writes, the statistics math is correct, missing/`null` token fields are handled safely, and the entry point behaves as documented for the common paths (missing dir, non-dir, empty dir, malformed lines, `--stats`, `--json`, exit codes 0/1/2). No correctness bug was found that would make the tool report wrong numbers or crash on the shipped sample traces. Six issues below: one Medium (documented `--validate` mode is a no-op), three Low, two informational.

---

## What was verified as correct

### Validation rules vs. the real schema (lines 29–39, 62–82, 85–152)
- `REQUIRED_FIELDS` = `schema_version, timestamp, monotonic_ns, run_id, event_id, event, data`. Every record written by `TraceRecorder.emit()` (trace_runtime.py) contains exactly this envelope plus optional fields (`elapsed_ms`, `turn_id`, `agent_id`, `parent_agent_id`, `agent_kind`, `span_id`, `parent_span_id`, `caused_by_event_id`, `depends_on_event_ids`, `thread`). Confirmed against the first line of all four sample files and the final `run_end` line of the three completed files. Treating the extras as optional is correct (they are legitimately `null`, e.g. `turn_id` on `run_start`/`run_end`).
- `EXPECTED_SCHEMA_VERSION = "1.0"` matches `SCHEMA_VERSION = "1.0"` in trace_runtime.py; mismatch is a warning, not an error — appropriate.
- `check_record` type checks (`event` must be str, `data` must be dict) match the writer, which always emits a string event and a dict `data`. Non-object JSON lines are reported with the right type name.
- First-event/last-event checks (lines 127–136) are consistent with the recorder: `TraceRecorder.__init__` always emits `run_start` first, `finish_run` emits `run_end` last. An interrupted run (no `run_end`) produces exactly the "run interrupted or still recording?" warning — which is the correct behavior for `traces/run_20260902T004901_584576Z_dc6a9685.jsonl`, which is still being appended to by a live session (last events observed mid-run; no `run_end` at the point of review).
- `run_end` status extraction (line 183) is safe: `finish_run` always writes `data.status` ("completed"/"error" from `close_tracing`, "process_exit" from the atexit hook); `data.get("status", "unknown")` cannot crash.
- Empty / fully-malformed files hit the early return at lines 123–125 before `records[0]` is touched — no `IndexError`.
- `run_id` change warning (lines 110–116) is correct: one recorder instance = one `run_id` per file, so a change is genuinely anomalous.
- Blank lines are skipped and not counted in `line_count`; the "OK: all N lines" message (lines 243–247) is only shown when `total_errors == 0`, so it is accurate.

### Stats math (lines 155–212)
- `record_count` counts only fully valid records; malformed lines are excluded from every aggregate. Correct per the docstring.
- `model_calls` / `models`: keyed on `model_request` events, `data.model` — the exact field `TracedMessages` writes (including auxiliary calls: `memory_extract`, `compaction_summary`, teammate/one-shot calls, which all go through the wrapped client). `None` model → "unknown". Verified field names against trace_runtime.py and against `model_request` records in all four samples.
- `stop_reasons`: keyed on `model_response.data.stop_reason` (written as `getattr(response, "stop_reason", None)`); `None` → "unknown". Samples show `tool_use`, `end_turn`, `max_tokens` — all counted as-is.
- Token totals (lines 189–199): `int(usage.get(...) or 0)` is safe for `null` values (all four samples have `cache_creation_input_tokens: null` / `cache_read_input_tokens: null` on every `model_response`) and for missing keys; a missing/non-dict `usage` is skipped entirely (`isinstance` guard), and `calls_with_usage` is only incremented when a usage dict is present. No rescale bug: values are token counts as written.
- `model_error` (lines 200–203): `TracedMessages` rewrites the span's end event to `model_error` with `data = {status: "error", purpose, model, error_type, error, ...}`; the `error_type`-first fallback chain (`error_type` → `status` → "unknown") matches that payload.
- `model_retry` (lines 204–205): `code.py with_retry()` emits `model_retry` with `data.reason` = `"429"` or `"529"` (plus `attempt`, `max_attempts`, `delay_ms`, `model`); keying on `reason` is correct.
- `tools` (lines 206–207): `tool_start.data.tool` comes from `trace_tool_data(block)` (`tool: block.name or "unknown"`); matches all `tool_start` records seen in the samples.
- `tool_end_status` / by-tool breakdown (lines 208–212): `code.py` finishes tool spans with `status` ∈ {`ok`, `error`, `denied`, `scheduled`}; the samples confirm `denied` in the wild (run_dc6a9685, evt_001911: bash denied on an async turn). `None`/missing status → "unknown". All values flow through the same `status != "ok"` bucket — no crash path.
- Per-run facts (lines 138–150): `turns`/`agents` are distinct-id sets (teammate ids like `agent-team_000013` and `agent-root` confirmed in samples; teammate events carry the lead's `turn_id` via `restore_context`, which is counted once — correct). `duration_ms = max(elapsed) - min(elapsed)` over numeric `elapsed_ms` only (bools excluded by the `isinstance` check); the "do not rescale" comment is right — `elapsed_ms` is already milliseconds in the envelope.
- `render_json` (lines 343–380) serializes everything it claims to; `null` for missing `run_id`/`run_end_status` is valid JSON.

### Entry point, args, error paths (lines 383–431)
- Missing directory → stderr + exit 2; path exists but is not a directory → stderr + exit 2. Matches docstring.
- Directory with no `*.jsonl` → message + exit 0 (reasonable: nothing to report is not an error; see note below under Low #3 re: documented exit codes).
- `argparse` handles missing positional / unknown flags with its standard usage error → exit 2.
- `--stats`: validation section suppressed (`do_validate = not args.stats`), exit always 0 — matches "malformed lines are skipped, not gated on"; malformed lines are still visible in `--json` `files[].errors`.
- Default and `--validate`: exit 1 iff any file has errors, else 0 — matches docstring.
- `main()` returns via `sys.exit(main())`; no global state; single-pass streaming read (memory is fine for these file sizes).

---

## Issues

### M1 — Medium: `--validate` is a no-op; the documented "validation only" mode does not exist
- **Where:** docstring line 5 (`--validate <dir>  # validation only`), argparse help lines 389–390, `main()` lines 419–426, `render_text()` (stats sections unconditional, lines 278–339).
- **What:** `do_validate = not args.stats`. In default mode `do_validate` is already `True`, so `--validate` changes nothing: the text output is byte-identical to the default mode (validation section *and* all stats sections are printed), and the exit-code expression `args.validate or do_validate` is True in both modes. There is no flag combination that prints validation only.
- **Impact:** A user who runs `python3 trace_stats.py --validate traces` per the documented usage expecting a concise validation report gets the full stats report. The mode promised by two pieces of documentation does not exist.
- **Fix (pick one):**
  1. Make it real: compute `do_stats = not args.validate` and gate the "Runs"/"Models"/... sections in `render_text` on it (signature: `render_text(..., do_validate, do_stats, top)`); keep the exit-code logic as-is. Or
  2. If a separate validate-only mode is unnecessary, remove the `--validate` flag (keep `--stats` for suppression) and fix the docstring line 5 and help text to say default mode is "validation + stats".

### L1 — Low: file I/O errors don't honor the documented exit code, and mid-read failures crash with a traceback
- **Where:** docstring lines 16–17 ("2 = usage or I/O error"); `validate_file()` lines 87–91 (open) and 92–121 (iteration); `main()` lines 412–426.
- **What:** (a) An unreadable `*.jsonl` file (permission denied, `IsADirectoryError`) is recorded as a normal file *error* (`report.errors`) and therefore produces exit **1** ("malformed lines found"), not the documented exit **2** for I/O errors. (b) Errors during the read loop itself — `OSError` mid-read, or `UnicodeDecodeError` on a non-UTF-8 line (possible for hand-edited traces; the recorder always writes ASCII, so only external edits can trigger this) — are not caught: the tool dies with a traceback and a generic exit 1, and no per-line report is produced.
- **Fix:** wrap the `for line_no, line in enumerate(handle, start=1)` body/loop in `try/except (OSError, UnicodeDecodeError)` and record `"line %d: read error: %s" % (line_no, exc)` (for a decode error, report the line that failed to decode); decide deliberately whether open/read failures return 2 (track an `io_errors` flag on `FileReport` and return 2 from `main` when set, taking precedence over exit 1) or 1, and make the docstring say the same thing.

### L2 — Low: `--top` accepts 0 and negative values with surprising results
- **Where:** `main()` lines 393–394 (`type=int`, no validation); `_table()` lines 215–220.
- **What:** `_table` does `items = items[:top]`. With `--top -1` and N rows you silently get N−1 rows (Python negative slicing), and with `--top 0` you get zero rows *plus* the misleading `(none observed)` placeholder even when the counter is non-empty.
- **Fix:** validate in `main` after parsing — e.g. `if args.top < 0: parser.error("--top must be >= 0")` (yields exit 2, consistent with the docstring) — or clamp in `_table` with `items = items[:max(0, top)]` and only print `(none observed)` when the counter itself is empty (`if not counter: return [...]` instead of testing the sliced list).

### L3 — Low: `--json` report omits fields that the text report shows
- **Where:** `render_json()` totals, lines 362–376, vs. `Aggregate` lines 161–173.
- **What:** `tool_end_status_by_tool` (the per-tool breakdown of non-ok `tool_end`s, which the text report prints under "Errors and non-ok outcomes") and `event_names` are never included in the JSON `totals`. A script consuming `--json` cannot reproduce the "by tool" breakdown.
- **Fix:** add to `totals`:
  ```python
  "tool_end_status_by_tool": dict(agg.tool_end_status_by_tool),
  "event_names": dict(agg.event_names),   # optional, but free and useful
  ```

### I1 — Informational: run duration is `max(elapsed) - min(elapsed)`, not time-since-process-start
- **Where:** `validate_file()` lines 143–150.
- **What:** the first record's `elapsed_ms` is ~3–10 ms (measured at recorder construction), so reported duration is short by that offset (e.g. run_83ce7412 spans elapsed 3.394 → 1385692.551 ms; reported ≈ 1385689.2 ms). Negligible at these magnitudes, but if exact wall time matters, use the last record's `elapsed_ms` directly (it is measured from the same `_started_ns` as everything else) and drop the `min`.
- **Fix (optional):** `report.duration_ms = max(0.0, max(elapsed))` (i.e., last/max elapsed), or document the approximation in the "Runs" section header.

### I2 — Informational: "Errors and non-ok outcomes" lumps normal background outcomes with failures
- **Where:** `add_file()` line 211 (`if status != "ok"`), `render_text()` section label lines 290–302.
- **What:** background bash tools end with `tool_end` status `"scheduled"` (code.py `start_background_task`), which is a *normal* outcome, not an error; it is bucketed next to `denied`/`error` in both the summary line and the `by tool` table. Similarly, `stop_reasons` and the token totals include auxiliary model calls (`memory_extract`, `compaction_summary` — e.g. samples show `stop_reason: "max_tokens"` on `memory_extract` calls), which is fine but worth knowing when reading the tables.
- **Fix (optional):** exclude `"scheduled"` from `tool_end_status_by_tool` (keep it in the overall `tool_end_status` count), and/or label the tokens/stop-reason sections "including auxiliary calls (memory/compaction)".

---

## Notes / observations (no action required)

- `traces/run_20260902T004901_584576Z_dc6a9685.jsonl` was still growing during this review (a live harness session is writing it; teammate threads like `teammate-test-reviewer` are visible in it). Expect `trace_stats.py` to emit the "no 'run_end'" warning for that file until the run closes — correct behavior.
- `model_error` / `model_retry` / `denied` paths were verified by reading the emitting code (`TracedMessages` in trace_runtime.py, `with_retry` in code.py, the tool-dispatch spans); none of the sampled prefixes I read contained a `model_error` or `model_retry` record, so those counters were not exercised by the samples themselves — only by `denied` (run_dc6a9685).
- `validate_file` catches `OSError` only around `path.open`, not around iteration — see L1.
- Minor cosmetic: the "OK: all N lines" count excludes blank lines (by design), so for files containing blank lines it understates physical line count; harmless.
- `glob("*.jsonl")` also matches hidden files (pathlib semantics); none exist in `traces/`, so no impact.

## Suggested regression checks for whoever fixes these (for the test suite)

1. `--validate` output must differ from default output (or the flag must be removed and docs fixed).
2. A directory containing a `*.jsonl` file with an invalid UTF-8 byte must not traceback; exit code must match the docstring.
3. `--top 0` / `--top -1` must not print `(none observed)` for a non-empty counter (or be rejected with exit 2).
4. `--json` totals must contain `tool_end_status_by_tool`.
5. A file with all-malformed lines must produce the "no valid records" warning and still be listed in `files[]` with 0 events.
