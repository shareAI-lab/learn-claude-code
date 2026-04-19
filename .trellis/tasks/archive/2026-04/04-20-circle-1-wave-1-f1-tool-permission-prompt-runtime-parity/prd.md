# Circle 1 Wave 1 F1 Tool-Permission-Prompt-Runtime Parity

## Goal

Strengthen the local runtime control loop so `coding-deepgent` can behave like
a daily-driver coding agent during real repository work, not only pass MVP
contracts.

## Acceptance Targets

* Workflow A improves materially: the agent can independently complete typical
  PR-level tasks in a medium-to-large repository with less user micromanagement.
* Tool discovery, selection, permission handling, and prompt/runtime control
  loop behavior feel dependable during sustained local coding tasks.
* The family has a clear parity judgment against real Claude Code public
  behavior and `cc-haha` runtime/tool references.

## Planned Features

* Re-audit local tool/runtime surfaces against daily-driver coding workflow
  expectations.
* Identify which current H01/H02/H03/runtime pieces are already strong enough
  and which remain only MVP-complete.
* Define a concrete implementation slice for the highest-value remaining gap.

## Planned Extensions

* Broad CLI/TUI polish
* Provider-specific runtime internals
* Full remote/IDE/runtime control-plane behavior

## Technical Notes

* Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Parent decomposition: `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`

## Implementation Summary

* Deferred tool execution is no longer artificially weaker than the main tool
  surface when the target deferred capability returns a bounded
  `Command(update=...)`.
* `invoke_deferred_tool` now preserves the deferred capability's real bounded
  result contract (`ToolMessage` or `Command(update=...)`) instead of throwing a
  runtime error for command-update tools.
* Focused tool-system tests now cover deferred command-update preservation.

## Verification

* `pytest -q coding-deepgent/tests/tool_system/test_tool_search.py coding-deepgent/tests/tool_system/test_tool_system_middleware.py -q`
* `ruff check coding-deepgent/src/coding_deepgent/tool_system/deferred.py coding-deepgent/tests/tool_system/test_tool_search.py .trellis/spec/backend/tool-capability-contracts.md`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/tool_system/deferred.py coding-deepgent/tests/tool_system/test_tool_search.py`
