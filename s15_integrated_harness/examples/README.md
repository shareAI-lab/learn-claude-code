# s15 trace examples

Self-contained demos that run the standard-library trace tools on the sample
traces in [`../traces/`](../traces/) (recorded CLI sessions, one JSONL file per
run). Each script resolves paths relative to its own location, so it works
from any working directory with no setup:

```sh
cd s15_integrated_harness
python3 examples/demo1_view_latest_trace.py
python3 examples/demo2_validate_and_stats.py
python3 examples/demo3_compare_all_traces.py
```

| Script | Runs | Shows |
|--------|------|-------|
| `demo1_view_latest_trace.py` | `trace_view.py` | One trace rendered as derived metrics, an ASCII per-agent timeline, and a JSON summary. Add `--with-tree` for the full metrics + agent/execution tree; `--trace <file>` to pick a different sample. |
| `demo2_validate_and_stats.py` | `trace_stats.py` | Validation of the JSON envelope on every line of every run file, plus aggregate text statistics (models, tool frequency, stop reasons, errors, tokens) and the `--json` machine-readable report. |
| `demo3_compare_all_traces.py` | both | `trace_view.py --view metrics` for every `traces/run_*.jsonl`, then parses `trace_stats.py --stats --json` into a compact cross-run comparison table. |

The scripts use only the Python standard library, echo each command they run,
print the tool output, and exit non-zero with a clear message if any tool
invocation fails.
