# Circle 1 Wave 1 F5 Bounded Subagent-Fork Daily-Driver

## Goal

Strengthen bounded local subagent and fork workflows so they become a reliable
personal-efficiency tool during complex coding tasks.

## Acceptance Targets

* Workflow C improves materially through bounded child execution.
* Local subagent/fork behavior becomes dependable enough for daily use without
  requiring full mailbox/coordinator/team-runtime parity.
* Remaining parity gaps for bounded local child execution are prioritized.

## Planned Features

* Re-audit local `run_subagent` / `run_fork` / resume / background slices
  against single-developer complex-task use.
* Identify the highest-value bounded child-runtime gap.
* Define the next implementation slice for this family.

## Planned Extensions

* Mailbox / `SendMessage`
* Coordinator synthesis
* Richer team-runtime lifecycle

## Technical Notes

* Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Parent decomposition: `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`

## Implementation Summary

* Added `subagent_list` as a deferred background-run discovery tool.
* The tool lists active background subagent/fork runs by default and can include
  terminal runs with `include_terminal=True`.
* Registered the new tool in the subagent package, tool container, and
  capability registry so it is reachable through `ToolSearch` /
  `invoke_deferred_tool`.
* This closes a practical daily-driver gap: the user/model no longer has to
  remember a run id perfectly to inspect active background work.

## Verification

* `pytest -q coding-deepgent/tests/subagents/test_subagents.py::test_subagent_list_reports_active_and_terminal_background_runs coding-deepgent/tests/tool_system/test_tool_search.py::test_tool_search_returns_deferred_builtin_subagent_controls -q`
* `ruff check coding-deepgent/src/coding_deepgent/subagents/background.py coding-deepgent/src/coding_deepgent/subagents/schemas.py coding-deepgent/src/coding_deepgent/subagents/__init__.py coding-deepgent/src/coding_deepgent/containers/tool_system.py coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/tool_system/test_tool_search.py`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/subagents/background.py coding-deepgent/src/coding_deepgent/subagents/schemas.py coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/tool_system/test_tool_search.py`
