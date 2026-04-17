# L2-a: H11/H12 AgentDefinition and general runtime

## Goal

Implement H11/H12-A: introduce `AgentDefinition`, a `general + verifier` catalog, real read-only general child runtime, minimal structured result envelope, and fallback final-text scan.

## Requirements

* Define an `AgentDefinition` schema with at least `agent_type`, description/when-to-use, tool allowlist/disallow list, `max_turns`, and optional model profile.
* Register the MVP built-in catalog: `general` and `verifier`.
* Replace the current `general` stub with a bounded read-only child `create_agent` invocation.
* Keep `general` tools read-only: `read_file`, `glob`, `grep`, `task_get`, `task_list`, `plan_get`.
* Refactor verifier settings to read from `AgentDefinition`; keep verifier bounded and read-only.
* Add a result envelope with `input_tokens`, `output_tokens`, `total_tokens`, `total_duration_ms`, and `total_tool_use_count`.
* Add fallback last-text scan when the final assistant message is tool-only or otherwise lacks direct text.

## Acceptance Criteria

* [x] `run_subagent(agent_type="general")` executes a real child runtime, not a hard-coded acceptance string.
* [x] `general` cannot write files, edit files, run bash, call `TodoWrite`, or save plans.
* [x] `general.max_turns == 25` and `verifier.max_turns == 5` are declared in definitions, not hard-coded branches.
* [x] Verifier behavior and existing tests remain compatible.
* [x] Result envelope is parseable and includes minimal usage/duration/tool-count fields.

## Dependencies

* Depends on `L1-c` for shared `ToolCapability` metadata assumptions.

## Context Sources

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/prd.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Out of Scope

* Sidechain transcript persistence.
* Background/async agents.
* Mailbox / SendMessage.
* Write-capable coder agents.
* Full fork/cache parity.
