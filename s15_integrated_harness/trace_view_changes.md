# trace_view.py — changes

## Changes

Added an optional `--summary` flag that prints a machine-readable JSON object to
stdout, while the default human-readable rendering, CLI interface, and exit codes
are 100% unchanged.

1. **New `build_summary(path, events)` helper** (inserted after `calculate_metrics`,
   before `_short`): builds a plain JSON-serializable dict containing:
   - `trace_file` — the trace file that was loaded,
   - `trace_files` — sorted list of `run_*.jsonl` files in the trace's directory,
   - `trace_count` — number of trace files,
   - `event_count` — total number of events in the loaded trace,
   - `events_by_type` — event counts keyed by event name (sorted),
   - `duration_ms` — wall duration in ms, included only if at least one event
     carries a `monotonic_ns` timestamp,
   - `total_tokens` and a `tokens` breakdown (`input_tokens`, `output_tokens`,
     `cache_tokens`), included only if at least one `model_response` event carries
     usage data.
   Token accounting mirrors the existing logic in `calculate_metrics`
   (sums `input_tokens`, `output_tokens`, and both cache fields).

2. **New argparse flag in `main()`**: `parser.add_argument("--summary",
   action="store_true", ...)` — purely additive; `--view`, `--width`, and the
   positional `trace` argument are untouched.

3. **New branch in `main()`** immediately after trace loading: when `--summary`
   is set, prints `json.dumps(build_summary(path, events), indent=2)` and
   returns 0, skipping the human-readable sections. Without the flag the code
   path is byte-for-byte identical to before (same output, same exit codes).

No imports were added (`json`, `Counter`, `Path`, and `Any` were already
imported). `code.py`, `trace_runtime.py`, and `trace_stats.py` were not modified.
