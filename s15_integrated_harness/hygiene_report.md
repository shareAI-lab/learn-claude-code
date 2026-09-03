# Hygiene + Python Compatibility Audit — s15_integrated_harness

**Task:** task_24246d99 (read-only audit; no existing file was modified)
**Audited by:** test-reviewer
**Method note:** the bash tool was unavailable in this session ("interactive shell approval is unavailable"), so `py_compile` could not be executed directly. Instead, every module was verified by a complete read (all four `.py` files read in full), and the byte-compile state of `__pycache__` was inspected as corroborating evidence. The project's own `make lint` target (`python3 -m py_compile $(wildcard *.py)`) is the documented way to run the byte-compile check and should be run in any environment with a shell as the final gate.

## 1. Syntax / py_compile findings

| Module | Lines | Syntax status (full-read verification) | Corroboration |
|---|---|---|---|
| `code.py` | 3710 | OK — no syntax errors found; valid Python (3.10+ grammar, see §2) | `__pycache__/code.cpython-312.pyc` **and** `code.cpython-314.pyc` exist → imported/compiled successfully on Python 3.12 and 3.14 at some point |
| `trace_runtime.py` | 638 | OK | `trace_runtime.cpython-312.pyc` + `.cpython-314.pyc` present |
| `trace_view.py` | 603 | OK | `trace_view.cpython-312.pyc` + `.cpython-314.pyc` present |
| `trace_stats.py` | 431 | OK | No pyc (only ever run as `__main__` script, which leaves no bytecode cache) — full read found no issues |

No `match` statements, `except*` (exception groups), PEP 695 `type` statements, or walrus-operator misuse anywhere. All imports are stdlib or declared third-party (`anthropic`, `python-dotenv`, `pyyaml`, `pytest`).

## 2. Python version compatibility (target: 3.8+)

**Bottom line: the 3.8+ target is NOT met.** Actual minimums:

| Module | Has `from __future__ import annotations`? | Actual minimum Python | Why |
|---|---|---|---|
| `code.py` | **No** | **3.10** | PEP 604 unions (`X \| None`) in function signatures are evaluated at import time without the future import → `TypeError` on 3.8/3.9 |
| `trace_runtime.py` | Yes | **3.9** | `str.removeprefix()` used at runtime (not in an annotation) |
| `trace_view.py` | Yes | **3.8** | annotations only; runtime code uses 3.8-safe stdlib |
| `trace_stats.py` | Yes | **3.8** | uses `typing` generics only; runtime code is 3.8-safe |

### Evidence

**`code.py` (minimum 3.10):**
- PEP 604 in runtime-evaluated function annotations, e.g. `ConsoleBroker.ask(self, prompt: str | None = None)`, `_owner_in_progress(...) -> Task | None`, `validate_worktree_name(...) -> str | None`, `_registered_worktrees() -> tuple[dict[Path, dict[str, str]], str | None]`, `task_worktree_cwd(...) -> tuple[Path, str | None]`, `claim_next_task(...) -> Task | None`, `schedule_job(...) -> CronJob | str`, `_run_bash_process(...) -> tuple[str, int | None]`, `run_git(args: list[str], cwd: Path | None = None)`, `current_work_identity(...) -> tuple[int, str | None]`. On Python ≤ 3.9 the first of these raises `TypeError: unsupported operand type(s) for |` at module import — i.e. `import code` / `python code.py` fails immediately.
- Module-level variable annotations with built-in generics are also evaluated at runtime (PEP 526): `teammate_assignments: dict[str, dict[str, object]]`, `active_teammates: dict[str, str]`, `teammate_trace_ids: dict[str, str]`, `plan_gates: dict[str, str]`, `plan_request_ids: dict[str, str]`, `pending_requests: dict[str, ProtocolState]`, `SKILL_REGISTRY: dict[str, dict]`, `background_tasks: dict[str, dict]`, `background_results: dict[str, str]`, `scheduled_jobs: dict[str, CronJob]`, `cron_queue: list[CronJob]`, `_last_fired: dict[str, str]`, `mcp_tool_policies: dict[str, str]`, `mcp_clients: dict[str, MCPClient]` → 3.9+.
- 3.9-only runtime APIs: `Path.is_relative_to` (`safe_path`, `_task_path`, `_worktree_path`, `MessageBus._path`, `is_archive_marker`, `persisted_output_path`, `scan_skills`) and `str.removeprefix`/`removesuffix` (`persisted_output_path`, the `start_background_task` worker's `cwd_error.removeprefix("Error: ")`).
- The environment in which this lesson actually ran is 3.12/3.14 (see §3 pyc evidence), which is why this has never surfaced locally.

**`trace_runtime.py` (minimum 3.9):**
- `TraceRecorder.__init__` (≈line 230): `self.run_id.removeprefix("run_")` — `str.removeprefix` is 3.9+ and this is runtime code, so the future import does not help.
- Everything else is 3.8-safe (`importlib.metadata.version` is 3.8+; all PEP 604 / built-in-generic uses are annotations only).

**`trace_view.py` and `trace_stats.py` (3.8-safe):** future import present; no 3.9+ runtime APIs (no `removeprefix`, no `is_relative_to`, no dict `|` merge, no `match`); `dataclasses`, `Counter`, `defaultdict`, `argparse`, `pathlib` usage is all 3.8-compatible.

### If 3.8/3.9 support is actually required (otherwise fix the docs to say 3.10+)
1. `code.py`: add `from __future__ import annotations` (removes the PEP 604 import-time failure), then either (a) also drop the 3.9+ *module-level* variable annotations to `typing.Dict`/`typing.List` or remove them, or (b) accept 3.9; and replace `str.removeprefix/removesuffix` with slice equivalents and `Path.is_relative_to(p)` with a `p.relative_to(base)` in try/except (or `os.path.commonpath`) to reach 3.8.
2. `trace_runtime.py`: replace `self.run_id.removeprefix("run_")` with `self.run_id[4:]` (or a conditional slice) to reach 3.8.
3. Simplest, least-invasive option: state "Python 3.10+" in the READMEs/requirements and add `python_requires`-equivalent notes; the code already targets the 3.12/3.14 host.

## 3. Repo hygiene findings

### Stray artifacts present (should not be committed)
1. **`__pycache__/` — 6 stale .pyc files, two interpreter generations:**
   `code.cpython-312.pyc`, `code.cpython-314.pyc`, `trace_runtime.cpython-312.pyc`, `trace_runtime.cpython-314.pyc`, `trace_view.cpython-312.pyc`, `trace_view.cpython-314.pyc`.
   The 3.12 + 3.14 split means two different interpreters have compiled this tree (matches the traces: runs executed under Python 3.12.14; the current harness host is 3.14). Safe to delete wholesale (`make clean` does this); never commit.
2. **Live harness runtime state in the lesson dir** (created because `code.py` uses `WORKDIR = Path.cwd()` and recent runs were started from this directory):
   - `.tasks/` — **28 task-JSON files including the currently active task board** (my own in-flight task `task_24246d99.json` is among them). **Do not delete while the session is running**; it is live state.
   - `.transcripts/` — 4 `transcript_*.jsonl` compaction transcripts (contain conversation excerpts — treat as scratch, not course material).
   - `.mailboxes/lead.jsonl` — live team-message mailbox (can contain plan text/messages).
   - `.task_outputs/tool-results/` — **~130 `chatcmpl-tool-*.txt` persisted tool outputs** (full command output; large and session-specific).
   - Not present (good): `.memory/`, `.worktrees/`, `.scheduled_tasks.json`, `skills/`, `.env` (no credential file leaked into the lesson dir; `load_dotenv` picks up the repo-root `.env` instead).
3. **`traces/` — 4 run files, one of which is being written by a LIVE session right now** (`run_20260902T004901_584576Z_dc6a9685.jsonl`, ~2300+ lines and growing; visible teammate threads include the current one). The other three are complete and look like the curated sample set other tasks reference. Decision needed: keep 2–4 curated samples (commit deliberately) and ignore the rest; do not commit a file mid-write.

### Clean (no findings)
- No `.DS_Store`, no `*.swp`/`*.swo`, no `*~`, no `*.tmp`/`*.bak` anywhere under the lesson dir.
- No leftover `.pytest_cache` (tests have not been run here yet).
- `images/` contains exactly the 3 expected SVGs (`system-architecture.svg`, `.en.svg`, `.ja.svg`).
- No editor/OS cruft in `traces/` (only `run_*.jsonl`).

### Tooling inconsistencies (hygiene-adjacent)
4. **`run_tests.sh` and `Makefile` reference a `tests/` directory that does not exist in the lesson dir.** `run_tests.sh` ends with `exec "$PY" -m pytest tests/ -v` and `make test` delegates to it; there is no `tests/` here (verified by glob). As of this snapshot `make test` fails with pytest's "file or directory not found: tests/" (exit 4). The repo-root `tests/` directory does exist and is where the in-flight test work (task_a19fd461) may land — if tests live at the repo root, the lesson-local runner will never find them; either point the runner at `../tests/` (with an existence check) or create the lesson-local `tests/`.
5. `Makefile` `lint` target is correct and is the recommended py_compile gate: `$(PY) -m py_compile $(wildcard *.py)` (covers all four modules). `make clean` correctly removes `.pytest_cache`, all `__pycache__` dirs, and stray `*.pyc`.
6. `run_tests.sh` is valid POSIX sh (`set -eu`, no bashisms, `cd "$(dirname "$0")"`, python3→python fallback, pytest presence check) — no issues beyond finding #4.

## 4. Suggested `.gitignore` block

No `.gitignore` exists in the lesson dir. Add the following block at lesson level (or fold the generic entries into a repo-root `.gitignore` — the repo-root file was not readable from this session's working dir, so verify before duplicating entries):

```gitignore
# Python bytecode / test artifacts
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/

# s15 harness runtime state (created by code.py when run with cwd = lesson dir;
# the leading dots are part of the directory names)
.tasks/
.transcripts/
.mailboxes/
.task_outputs/
.memory/
.worktrees/
.scheduled_tasks.json
skills/

# Credentials (safety net; lesson loads .env from repo root)
.env

# Trace artifacts: ignore all runs, then force-add the curated samples
# you want to ship (git add -f traces/run_....jsonl)
traces/*.jsonl

# Editor / OS cruft
.DS_Store
*.swp
*.swo
*~
```

Notes on the block:
- The runtime-state entries match the dot-prefixed directories `code.py` creates (`.tasks/`, `.transcripts/`, ...); the leading dot is literal, not a gitignore feature. `skills/` has no dot (it is the user-provided skills dir).
- `traces/*.jsonl` + `git add -f` for the 2–4 curated samples keeps the lesson's documented sample set under VCS while quarantining live runs (and prevents committing `run_..._dc6a9685.jsonl` mid-write).
- If the repo root already ignores `__pycache__/` and `.DS_Store`, only the harness-runtime-state and `traces/` lines need to be added at lesson level.
- `.tasks/` and `.mailboxes/` are live right now; the ignore entry takes effect without deleting them.

## 5. Suggested actions (for the owner to execute — nothing was changed by this audit)

1. Run `make lint` in a shell-enabled session to get the authoritative py_compile confirmation (all four modules passed full-read syntax verification; expect success).
2. Fix the Python version claim: either document **3.10+** (recommended, matches the 3.12/3.14 host and the code as written) or apply the §2 backport steps.
3. Decide the `tests/` location and align `run_tests.sh`/`Makefile` with it (finding #4) — this is currently a broken entry point.
4. Delete `__pycache__/` (`make clean`) and keep it ignored.
5. Add the §4 `.gitignore` block; force-add the curated `traces/` samples; leave `.tasks/`, `.mailboxes/`, `.transcripts/`, `.task_outputs/` on disk (live) but ignored.
6. Optional: once the live run closes, prune `.task_outputs/tool-results/` and `.transcripts/` (scratch data), and consider whether `traces/run_20260902T004901_584576Z_dc6a9685.jsonl` deserves curation or deletion.
