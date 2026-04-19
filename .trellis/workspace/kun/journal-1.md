# Journal - kun (Part 1)

> AI development session journal
> Started: 2026-04-14

---



## Session 1: Close coding-deepgent MVP local agent harness core

**Date**: 2026-04-15
**Task**: Close coding-deepgent MVP local agent harness core

### Summary

Completed Approach A MVP closeout through Stage 29, validated coding-deepgent end-to-end, published the MVP commit, archived completed stage tasks, and updated the canonical H01-H22 dashboard plus project handoff.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `9f60195` | (see git log) |
| `89fb741` | (see git log) |
| `fd3be9d` | (see git log) |
| `0355279` | (see git log) |
| `e58c9de` | (see git log) |
| `ede6869` | (see git log) |
| `26b0815` | (see git log) |
| `6342735` | (see git log) |
| `1ce15c0` | (see git log) |
| `18c2a1a` | (see git log) |
| `5883522` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: Session memory contribution seams and local updates

**Date**: 2026-04-15
**Task**: Session memory contribution seams and local updates

### Summary

Implemented session-memory deterministic assist, module contribution seams, and threshold-triggered local updates behind generic contribution providers. Validated focused session, compact, memory, CLI, ruff, and mypy checks. Archived completed planning and Stage 30A/30B tasks.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `5958b9c` | (see git log) |
| `921cbfc` | (see git log) |
| `5e675c8` | (see git log) |
| `7d6bf7c` | (see git log) |
| `2cfcbcd` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: Runtime pressure management closeout

**Date**: 2026-04-15
**Task**: Runtime pressure management closeout

### Summary

Implemented and validated coding-deepgent runtime context pressure loop: tool-result storage, microcompact, live auto/reactive compact, restoration, session-memory assist/refresh, runtime pressure evidence, settings-backed thresholds, Trellis contracts, and task archival.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `5271b82` | (see git log) |
| `ee1322b` | (see git log) |
| `833325d` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: Trellis consolidation and guide foundation

**Date**: 2026-04-15
**Task**: Trellis consolidation and guide foundation

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Trellis consolidation | Established `.trellis/` as the canonical mainline documentation layer for `coding-deepgent`, removed duplicated product governance docs, and cleaned tutorial/reference-only skill and test surfaces. |
| Custom skill migration | Migrated project-specific skill behavior into Trellis docs (`cc alignment`, `LangChain-native rules`, `staged execution`, `project handoff`) and removed the old custom skills while preserving `record-session`. |
| Doc system | Added Trellis doc map and interview-driven spec expansion guides, clarified plans-vs-specs, PRD-vs-journal, spec update triggers, handoff update policy, validation scope policy, and task archive policy. |
| Backend specs | Filled backend persistence, error handling, logging guidance; split oversized runtime/compact contracts into focused contract files; added Trellis markdown link smoke checker. |
| Chinese localization | Localized `.trellis/spec/guides/*.md` to Simplified Chinese while preserving English commands, paths, identifiers, and structured tokens. |

**Archived Tasks**:
- `04-15-trellis-custom-skill-migration`
- `04-15-trellis-docs-synthesis-interview`
- `04-15-trellis-docs-chinese-localization`
- `04-15-trellis-spec-consolidation`

**Updated Files**:
- `.trellis/workflow.md`
- `.trellis/project-handoff.md`
- `.trellis/plans/index.md`
- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/database-guidelines.md`
- `.trellis/spec/backend/error-handling.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/backend/quality-guidelines.md`
- `.trellis/spec/backend/langchain-native-guidelines.md`
- `.trellis/spec/backend/runtime-context-compaction-contracts.md`
- `.trellis/spec/backend/tool-result-storage-contracts.md`
- `.trellis/spec/backend/session-compact-contracts.md`
- `.trellis/spec/backend/runtime-pressure-contracts.md`
- `.trellis/spec/guides/index.md`
- `.trellis/spec/guides/trellis-doc-map-guide.md`
- `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`
- `.trellis/spec/guides/mainline-scope-guide.md`
- `.trellis/spec/guides/cc-alignment-guide.md`
- `.trellis/spec/guides/staged-execution-guide.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`
- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/*.md`
- `.trellis/scripts/check_trellis_links.py`

**Verification**:
- `python3 ./.trellis/scripts/check_trellis_links.py` passed
- Focused `coding-deepgent` skill/plugin tests had passed earlier after root tutorial `skills/` removal

**Status**:
[OK] **Completed**

**Next Steps**:
- Continue using Trellis-first workflow for new `coding-deepgent` tasks
- If needed, localize additional high-value Trellis docs beyond `spec/guides/*` in a later phased pass


### Git Commits

| Hash | Message |
|------|---------|
| `7fffb8c` | (see git log) |
| `dbb8ae9` | (see git log) |
| `d6d0f0f` | (see git log) |
| `4ef12ca` | (see git log) |
| `4241062` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 5: Trellis review fixes and rollback verification

**Date**: 2026-04-15
**Task**: Trellis review fixes and rollback verification

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Rollback verification | Verified that prior Chinese localization rollback had restored high-value `guides/*` and `plans/*` to English content, then fixed the remaining broken local `.omx` links introduced by the rollback. |
| Trellis review fixes | Repaired the main review findings in current Trellis docs: removed deleted reference-layer paths from backend index, restored `plans/index.md` as a real planning entrypoint, updated `master-plan-coding-deepgent-reconstructed.md` to point to surviving `.trellis/plans/...` evidence, and removed duplicate workspace-journal routing from the doc map. |
| Session hygiene | Cleared a stale `.current-task` pointer that referenced an empty `04-15-trellis-plans-chinese-localization` directory so future sessions will not resume an invalid task context. |

**Updated Files**:
- `.trellis/spec/backend/index.md`
- `.trellis/plans/index.md`
- `.trellis/plans/master-plan-coding-deepgent-reconstructed.md`
- `.trellis/spec/guides/trellis-doc-map-guide.md`
- `.trellis/.current-task`

**Verification**:
- `python3 ./.trellis/scripts/check_trellis_links.py` passed
- Reviewed current Trellis baseline for stale deleted-path references and navigation regressions

**Status**:
[OK] **Completed**

**Next Steps**:
- If needed, either delete or properly initialize `04-15-trellis-plans-chinese-localization` before using it again
- Continue normal `coding-deepgent` work with the repaired Trellis entrypoints


### Git Commits

| Hash | Message |
|------|---------|
| `cb9f8fe` | (see git log) |
| `9141539` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 6: Archive active Trellis tasks and validate Approach A MVP cleanup

**Date**: 2026-04-15
**Task**: Archive active Trellis tasks and validate Approach A MVP cleanup

### Summary

Archived all remaining active Trellis tasks, completed the release validation / PR cleanup task, clarified coding-deepgent release-facing docs around the stage-11 compatibility anchor versus Trellis live Stage 29 MVP status, and verified coding-deepgent with pytest, ruff, mypy, and contract regression checks.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `27690e4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 7: Progressive context pressure pipeline and Trellis commit policy

**Date**: 2026-04-16
**Task**: Progressive context pressure pipeline and Trellis commit policy

### Summary

Enabled AI-managed commits in Trellis workflow, implemented progressive runtime pressure pipeline with Snip/MicroCompact/Collapse/AutoCompact, and captured context-engineering follow-up roadmap tasks.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `08f0ebe` | (see git log) |
| `b72f2f7` | (see git log) |
| `a0f36a5` | (see git log) |
| `1ad78c6` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 8: Runtime pressure compression hardening

**Date**: 2026-04-16
**Task**: Runtime pressure compression hardening

### Summary

Implemented Stage 1 and Stage 2 of context compression: MicroCompact observability, time-based and token-budget pruning, AutoCompact circuit breaker/PTL retry, structured live compaction results, active-todo restoration, Pre/PostCompact hook context, and split Stage 3 on stable message IDs after full validation.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `2f62df2` | (see git log) |
| `a5bba07` | (see git log) |
| `11f3f46` | (see git log) |
| `1725ff3` | (see git log) |
| `3b5a236` | (see git log) |
| `161fefb` | (see git log) |
| `a01fde9` | (see git log) |
| `8a05cd3` | (see git log) |
| `c174f10` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 9: Integrated Memory Module Closeout

**Date**: 2026-04-18
**Task**: Integrated Memory Module Closeout

### Summary

Closed out the integrated memory module: four-type long-term memory, feedback enforcement, memory management tools, and separate long-term/current-session recovery visibility.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `bb58c31` | (see git log) |
| `9bca6c0` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 10: Fork explicit entrypoint and cache-safe contract

**Date**: 2026-04-18
**Task**: Fork explicit entrypoint and cache-safe contract

### Summary

Added explicit run_fork entrypoint with same-config sibling fork contract, runtime prompt/tool snapshot seams, fork continuity metadata, tests, and Trellis spec updates.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `2c8a2d5` | (see git log) |
| `2e6e2df` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 11: Memory Backend And Unified Context Closeout

**Date**: 2026-04-18
**Task**: Memory Backend And Unified Context Closeout

### Summary

Completed the unified context/memory model and durable memory backend: added project rules layer, durable PostgreSQL long-term memory, Redis-backed job pipeline, S3-compatible archive storage, focused tests, and validated live PostgreSQL/Redis/MinIO wiring.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `2646cb9` | (see git log) |
| `7ef9e6c` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 12: Memory productization closeout

**Date**: 2026-04-18
**Task**: Memory productization closeout

### Summary

Productized automatic memory extraction inspection, agent-private memory scope inspection, and snapshot refresh closeout; validated focused pytest, ruff, and mypy; archived the Trellis task.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `672e56a` | (see git log) |
| `d0e6f49` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 13: H12 fork runtime closeout

**Date**: 2026-04-19
**Task**: H12 fork runtime closeout

### Summary

(Add summary)

### Main Changes

| Area | What was completed |
|------|---------------------|
| Batch 1 | Effective `max_turns`, per-agent model routing, built-in `explore`/`plan`, local custom subagents, fork continuity metadata, subagent/fork resume foundation |
| Batch 2 | Background subagent runtime, progress + notification, queued follow-up input, plugin-provided subagent definitions |
| H12 closeout | Explicit `run_fork` remains the only fork surface, `run_fork(background=true)` background fork runtime, stop/cancel semantics, workdir hardening, roadmap/spec closeout |

**Validated**:
- `pytest -q coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_tool_system_middleware.py`
- `ruff check`
- `mypy`

**Updated Files**:
- `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
- `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
- `.trellis/spec/backend/task-workflow-contracts.md`
- `coding-deepgent/src/coding_deepgent/subagents/background.py`
- `coding-deepgent/src/coding_deepgent/subagents/loader.py`
- `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
- `coding-deepgent/src/coding_deepgent/subagents/tools.py`
- `coding-deepgent/src/coding_deepgent/subagents/__init__.py`
- `coding-deepgent/src/coding_deepgent/containers/tool_system.py`
- `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
- `coding-deepgent/src/coding_deepgent/plugins/schemas.py`
- `coding-deepgent/src/coding_deepgent/plugins/registry.py`
- `coding-deepgent/src/coding_deepgent/extensions_service.py`
- `coding-deepgent/src/coding_deepgent/runtime/context.py`
- `coding-deepgent/src/coding_deepgent/runtime/invocation.py`
- `coding-deepgent/src/coding_deepgent/settings.py`
- `coding-deepgent/tests/test_subagents.py`
- `coding-deepgent/tests/test_plugins.py`
- `coding-deepgent/tests/test_tool_system_registry.py`


### Git Commits

| Hash | Message |
|------|---------|
| `9be06b2` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 14: Deferred Tool Discovery And Subagent Contract Closeout

**Date**: 2026-04-19
**Task**: Deferred Tool Discovery And Subagent Contract Closeout

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Stage 0 | Restored clean baseline by aligning app tool-surface expectations, no-network test defaults, hook evidence metadata, and handoff wording. |
| Stage 1 | Added `ToolSearch` and `invoke_deferred_tool` so deferred builtin and MCP capabilities can stay off the initial main tool list while remaining searchable and executable through the shared tool-policy/middleware path. |
| Stage 2 | Consolidated subagent/fork contracts by moving advanced lifecycle controls onto the deferred surface and exposing `resume_subagent` / `resume_fork` as structured tool surfaces. |
| Specs | Updated canonical H01 / task-workflow / infrastructure contracts plus roadmap, deferred ADR, and project handoff to reflect the new deferred-discovery and subagent lifecycle boundaries. |
| Validation | `ruff check` on touched code/tests, `mypy` on touched typed modules, focused pytest on app/tool-system/mcp/tool-search/subagents, and full `pytest -q coding-deepgent/tests` (`371 passed`). |

**Notes**:
- Left the user's existing `.env.example` deletion untouched.
- Left generated `.coding-deepgent/memory.db` untracked and out of commits.


### Git Commits

| Hash | Message |
|------|---------|
| `e3da016` | (see git log) |
| `d27cf24` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 15: Consolidate coding-deepgent release readiness

**Date**: 2026-04-19
**Task**: Consolidate coding-deepgent release readiness

### Summary

Committed the coding-deepgent runtime/frontend readiness snapshot, reorganized product tests into domain directories, validated 386 Python tests plus frontend typecheck/tests, and recorded Core Release Gate as READY_WITH_FOLLOW_UPS.

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `79f8f05` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 16: Minimal Web UI Over Frontend Gateway

**Date**: 2026-04-19
**Task**: Minimal Web UI Over Frontend Gateway

### Summary

Added a minimal browser UI over `coding-deepgent ui-gateway`, wiring the new SSE gateway foundation into a static web shell that can submit prompts and render the shared frontend event stream.

### Main Changes

| Area | Description |
|------|-------------|
| Gateway | Added `coding-deepgent ui-gateway` SSE foundation and `/ui` route for a minimal browser shell |
| Web UI | Added `coding-deepgent/frontend/web/index.html` to submit prompts, connect `EventSource`, and render user/assistant/tool/runtime/todo/recovery events |
| Docs | Updated `coding-deepgent/README.md` and frontend/backend directory specs to reflect CLI/embedded/browser adapter layering |
| Validation | `pytest -q tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py tests/cli/test_cli.py` (56 passed), `ruff check ...`, `mypy src/coding_deepgent/frontend`, and gateway/CLI help smoke all passed |

**Outcome**:
- Browser UI now consumes the SSE gateway instead of the CLI JSONL adapter.
- CLI, embedded Python, and browser each have their own adapter over the shared producer/runtime foundation.
- True runtime HITL remains explicitly deferred; the web shell only visualizes permission requests.


### Git Commits

| Hash | Message |
|------|---------|
| `818fb6d` | (see git log) |
| `d90baab` | (see git log) |

### Testing

- [OK] `pytest -q tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py tests/cli/test_cli.py`
- [OK] `ruff check src/coding_deepgent/frontend src/coding_deepgent/cli.py tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/structure/test_structure.py tests/cli/test_cli.py`
- [OK] `mypy src/coding_deepgent/frontend`
- [OK] `PYTHONPATH=src python3 -m coding_deepgent --help`

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 17: Release validation and ui-gateway dependency cleanup

**Date**: 2026-04-19
**Task**: Release validation and ui-gateway dependency cleanup

### Summary

Validated the current frontend gateway release candidate, fixed the optional web dependency packaging gap, and archived the Trellis cleanup task.

### Main Changes

- Validated the `coding-deepgent` release candidate changes around `ui-gateway`, frontend gateway, and the minimal web shell.
- Confirmed focused Python, frontend CLI, static, and fake smoke checks passed.
- Closed the release blocker where `ui-gateway` depended on `fastapi` / `uvicorn` without declaring them in project metadata.
- Added the optional `web` dependency group, CLI missing-dependency guidance, README install notes, and regression coverage for the gateway runtime loader.
- Archived `04-19-backend-next-step-release-validation-pr-cleanup` after writing the implementation checkpoint into the task PRD.


### Git Commits

| Hash | Message |
|------|---------|
| `7a80b8c` | (see git log) |
| `8af4f5b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
