> **Note:** This file is an identical copy of `link_report.md` in the same directory, created to match the filename requested by the coordinator. `link_report.md` is the canonical deliverable for task task_462fc460; keep only one copy if you consolidate.

# s15 Integrated Harness — Link & Reference Audit

- **Workspace audited:** `/home1/11791/friedrichqi04/learn-claude-code/s15_integrated_harness/`
- **Files scanned:** `README.md` (344 lines), `README.zh.md` (303 lines), `README.ja.md` (303 lines). No other `.md` files exist in the lesson dir (verified with `glob **/*.md`).
- **Method / constraints:** read-only audit using `glob` + `read_file` only (bash blocked this session). Line numbers are 1-based. The repo root (`learn-claude-code/`) is **outside** this workspace, so any reference resolving outside the lesson dir (`../s14_*`, `../s16_*`, `../s09_*`, `cd learn-claude-code`) cannot be verified from here and is flagged `unverified` per task policy (not treated as failure). External `https://` URLs are likewise `unverified` (not resolvable via glob).
- **Status legend:** `ok` = referenced path/symbol verified to exist in workspace; `broken` = referenced path verified to be missing; `unverified` = outside workspace (cross-dir / repo root) or external URL.

## 1. Markdown links and image references

| file | line | reference | status | note |
|---|---|---|---|---|
| README.md | 3 | `README.md` | ok | same-dir; file exists |
| README.md | 3 | `README.zh.md` | ok | same-dir; file exists |
| README.md | 3 | `README.ja.md` | ok | same-dir; file exists |
| README.md | 5 | `../s14_mcp_plugin/` | unverified | cross-dir; repo root outside workspace; `glob ../s14_mcp_plugin/*` from lesson dir returns no match |
| README.md | 5 | `../s16_workflow_runtime/` | unverified | cross-dir; same reason as above |
| README.md | 35 | `images/system-architecture.en.svg` | ok | exists in `images/` |
| README.md | 283 | `https://huggingface.co/Qwen/Qwen3.8-27B` | unverified | external URL; not verifiable via glob |
| README.md | 283 | `https://recipes.vllm.ai/Qwen/Qwen3.8-27B` | unverified | external URL |
| README.md | 283 | `https://docs.vllm.ai/en/latest/serving/openai_compatible_server/` | unverified | external URL |
| README.md | 342 | `../s16_workflow_runtime/` | unverified | cross-dir; "Next" section link |
| README.zh.md | 3 | `README.md` | ok | same-dir; file exists |
| README.zh.md | 3 | `README.zh.md` | ok | same-dir; file exists |
| README.zh.md | 3 | `README.ja.md` | ok | same-dir; file exists |
| README.zh.md | 5 | `../s14_mcp_plugin/` | unverified | cross-dir; repo root outside workspace |
| README.zh.md | 5 | `../s16_workflow_runtime/` | unverified | cross-dir |
| README.zh.md | 35 | `images/system-architecture.svg` | ok | exists in `images/` |
| README.zh.md | 252 | `https://huggingface.co/Qwen/Qwen3.8-27B` | unverified | external URL |
| README.zh.md | 252 | `https://recipes.vllm.ai/Qwen/Qwen3.8-27B` | unverified | external URL |
| README.zh.md | 252 | `https://docs.vllm.ai/en/latest/serving/openai_compatible_server/` | unverified | external URL |
| README.zh.md | 301 | `../s16_workflow_runtime/` | unverified | cross-dir; "接下来" section link |
| README.ja.md | 3 | `README.md` | ok | same-dir; file exists |
| README.ja.md | 3 | `README.zh.md` | ok | same-dir; file exists |
| README.ja.md | 3 | `README.ja.md` | ok | same-dir; file exists |
| README.ja.md | 5 | `../s14_mcp_plugin/` | unverified | cross-dir; repo root outside workspace |
| README.ja.md | 5 | `../s16_workflow_runtime/` | unverified | cross-dir |
| README.ja.md | 35 | `images/system-architecture.ja.svg` | ok | exists in `images/` |
| README.ja.md | 252 | `https://huggingface.co/Qwen/Qwen3.8-27B` | unverified | external URL |
| README.ja.md | 252 | `https://recipes.vllm.ai/Qwen/Qwen3.8-27B` | unverified | external URL |
| README.ja.md | 252 | `https://docs.vllm.ai/en/latest/serving/openai_compatible_server/` | unverified | external URL |
| README.ja.md | 301 | `../s16_workflow_runtime/` | unverified | cross-dir; "次へ" section link |

**Subtotal: 30 references — 12 ok, 0 broken, 18 unverified (9 cross-dir + 9 external).**

## 2. File/path references in code fences and shell blocks

| file | line | reference | status | note |
|---|---|---|---|---|
| README.md | 210 | `traces` (`HARNESS_TRACE_DIR=traces`) | ok | `traces/` dir exists with 4 `run_*.jsonl` files |
| README.md | 213 | `s15_integrated_harness/code.py` | ok | `code.py` exists in lesson dir; path matches dir name |
| README.md | 216 | `traces/run_<timestamp>_<id>.jsonl` | ok | pattern matches existing files (e.g. `run_20260902T004901_584576Z_dc6a9685.jsonl`) |
| README.md | 238 | `s15_integrated_harness/trace_view.py traces/run_....jsonl` | ok | `trace_view.py` exists; `traces/run_*.jsonl` pattern valid (arg-less form defaults to latest trace in `traces/`, matching `_latest_trace(Path("traces"))`) |
| README.md | 239 | `trace_view.py --view tree` | ok | `tree` is a valid `--view` choice in `trace_view.py` argparse |
| README.md | 240 | `trace_view.py --view timeline --width 120` | ok | `timeline` valid; `--width` accepted |
| README.md | 241 | `trace_view.py --view metrics` | ok | `metrics` valid |
| README.md | 253 | `.env` (model-path diagram) | unverified | user-created runtime config (loaded via `load_dotenv`), not a repo artifact |
| README.md | 275–279 | `.env` dotenv block | unverified | example env config, not a repo file |
| README.md | 315 | `cd learn-claude-code` | unverified | repo root is outside this workspace |
| README.md | 316 | `s15_integrated_harness/code.py` | ok | exists |
| README.zh.md | 210 | `traces` | ok | dir exists |
| README.zh.md | 213 | `s15_integrated_harness/code.py` | ok | exists |
| README.zh.md | 219–222 | `s15_integrated_harness/trace_view.py` (×4 invocations) | ok | exists; `--view tree/timeline/metrics` valid |
| README.zh.md | 242 | `.env` | unverified | runtime config file, not a repo artifact |
| README.zh.md | 274 | `cd learn-claude-code` | unverified | repo root outside workspace |
| README.zh.md | 275 | `s15_integrated_harness/code.py` | ok | exists |
| README.ja.md | 210 | `traces` | ok | dir exists |
| README.ja.md | 213 | `s15_integrated_harness/code.py` | ok | exists |
| README.ja.md | 219–222 | `s15_integrated_harness/trace_view.py` (×4 invocations) | ok | exists; `--view` values valid |
| README.ja.md | 242 | `.env` | unverified | runtime config file |
| README.ja.md | 274 | `cd learn-claude-code` | unverified | repo root outside workspace |
| README.ja.md | 275 | `s15_integrated_harness/code.py` | ok | exists |

## 3. Functions / symbols named in code fences (spot-check against `code.py`)

All verified by reading `code.py` (3710 lines) and `trace_view.py` / `trace_runtime.py` / a sample trace JSONL.

| reference (as documented) | status | note |
|---|---|---|
| `trigger_hooks("PreToolUse", block)` | ok | `def trigger_hooks(event, *args)` in code.py |
| `tool_result(block.id, blocked)` (python fence, line ~111 in each README) | ok | illustrative pseudocode — no `tool_result()` function exists; real loop appends a `{"type": "tool_result", "tool_use_id": ..., "content": ...}` dict (agent_loop). Hook call itself is real |
| `TOOL_HANDLERS / MCP handlers / background dispatch` (architecture diagram) | ok | diagram pseudocode; real symbols are `BUILTIN_HANDLERS` / local `handlers` + `mcp__*` entries from `assemble_tool_pool()` |
| `assemble_tool_pool()` | ok | `def assemble_tool_pool()`; merges `BUILTIN_TOOLS` + MCP tools, rejects normalized name collisions as documented |
| `BUILTIN_TOOLS` / 26-tool list | ok | exactly 26 entries incl. `compact` (bash, read_file, write_file, edit_file, glob, todo_write, task, load_skill, compact, create_task, update_task, list_tasks, get_task, claim_task, complete_task, schedule_cron, list_crons, cancel_cron, spawn_teammate, list_teammates, send_message, request_shutdown, request_plan, review_plan, create_worktree, connect_mcp); trace `model_request` records also show `tool_count: 26` |
| `connect_mcp("docs")` / `mcp__docs__search` | ok | `def connect_mcp()`; `MOCK_SERVERS` has `docs` (search, get_version) and `deploy`; prefix format `mcp__server__tool` |
| `create_worktree(name, task_id)` / `remove_worktree()` | ok | both defined; removal stays host-side (not in `BUILTIN_TOOLS`) as documented |
| `assemble_system_prompt(context)` | ok | defined; assembles identity/tools/tasks/teams/workspace/memory/compaction + skills catalog + MCP servers |
| `load_skill(name)` | ok | defined; `SKILL_REGISTRY` scanned from `skills/` (runtime dir) |
| `extract_memories()` / `consolidate_memories()` | unverified | call sites exist in code.py (`remember_after_turn` via `MEMORY_RUNTIME`), but definitions live in `../s09_memory/code.py` — cross-dir, outside this workspace |
| `../s09_memory/code.py` (loaded by `load_memory_runtime()`) | unverified | cross-dir import; repo root outside workspace; `.memory/MEMORY.md` catalog it reads is a runtime path, not a repo artifact |
| `snip_compact` / `micro_compact` / `compact_history` / `tool_result_budget` | ok | all defined; `prepare_context()` runs exactly `tool_result_budget → snip_compact → (micro_compact → fit_tool_results) → compact_history` as documented; `micro_compact` keeps latest 3 (`KEEP_RECENT_TOOL_RESULTS = 3`) and targets 80% of limit as documented |
| `should_run_background` / `start_background_task` | ok | both defined; only explicit `run_in_background=true` bash calls qualify, per docs |
| `SUB_SYSTEM` / child tool pools | ok | `SUB_SYSTEM`, `SUB_TOOLS`, `SUB_HANDLERS` defined; subagent and teammate pools both exclude `task`/`spawn_teammate` as documented |
| `MessageBus` | ok | `class MessageBus` with `wait_for_messages`, inbox read before every model call, as documented |
| `request_shutdown` / `request_plan` / `review_plan` | ok | `run_request_shutdown`, `run_request_plan`, `run_review_plan` defined and wired into `BUILTIN_HANDLERS` |
| `compact` tool | ok | schema in `BUILTIN_TOOLS`; handled inline in `agent_loop` (not via `BUILTIN_HANDLERS`), so 26 tools / 25 handlers is consistent |
| `cron_queue` / `pending_delivery` / durable one-shot jobs | ok | `cron_queue`, `CronJob.pending_delivery`, `_enqueue_due_job` persist before queueing; at-least-once semantics via `acknowledge_cron_jobs`/`restore_cron_jobs` as documented |
| trace event names in the fenced list (`run_start` … `run_end`) | ok | verified against `trace_runtime.py`, `code.py` emit sites, `trace_view.py` `START_TO_END`, and a live sample (`traces/run_20260902T004901_…jsonl`): `run_start`, `turn_start`, `agent_active_start`, `model_request/model_response`, `harness_decision`, `tool_start/tool_end`, `tool_execution_start/end`, `permission_wait_start/end`, `context_prepare/context_prepared` all present; `agent_create/agent_start/agent_end`, `background_queued/start/end/notification` emitted in code.py |
| `traces/*.jsonl` sample data | ok | 4 files present; schema fields (wall-clock + monotonic time, run/turn/agent identity, span/parent span, causal IDs, thread, event data) match the README description |

## 4. Other observations (not broken links)

1. **Tool-count inconsistency (EN/ZH/JA):** the "Changes from s14" table says s15 has **25** built-in tools, while the "Tools and Dispatch" section says **26** (and `BUILTIN_TOOLS` actually has 26). The table cell appears off by one.
2. Runtime-created paths mentioned in prose (`.tasks/task_*.json`, `.memory/MEMORY.md`, `.worktrees/`, `.mailboxes/`, `.transcripts/`, `.task_outputs/tool-results/`, `.scheduled_tasks.json`, `skills/`) do not exist in the repo — correct, they are created at runtime; not link defects.
3. All three READMEs carry the matching `<!-- translation-sync: zh@v15, en@v15, ja@v15 -->` footer; the three files are structurally aligned.
4. `images/` contains all three architecture SVGs (`system-architecture.svg`, `.en.svg`, `.ja.svg`); each README links exactly its own variant.
5. `trace_stats.py` exists in the lesson dir but is not referenced by any README (no broken reference either way).

## 5. Summary

- **Broken links found: 0.** Every in-workspace relative link and image reference in `README.md`, `README.zh.md`, and `README.ja.md` resolves.
- **12 ok** (9 language-switcher links + 3 architecture images) and **18 unverified** (9 cross-dir links to `../s14_mcp_plugin/` and `../s16_workflow_runtime/` — repo root is outside the audited workspace, flagged per policy, not failures — plus 9 external documentation URLs).
- All file references in shell blocks (`code.py`, `trace_view.py`, `traces/`) and all obviously-checkable functions named in code fences were verified against the actual source; only the s09 memory-runtime definitions (`extract_memories`, `consolidate_memories`) and the two cross-dir lesson links remain unverified due to workspace boundaries.
