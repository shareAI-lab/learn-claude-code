# Stage 21: Tool And Permission Closeout

## Goal

Close the highest-value remaining H01/H02 MVP gaps by auditing and tightening the tool-first capability runtime and local permission/hard-safety boundary.

## Function Summary

This stage should identify and implement the smallest concrete changes that make the current tool surface and permission runtime count as MVP-complete for Approach A, without adding UI approval, auto classifier, or remote trust flows.

## Expected Benefit

* Reliability: model-facing tools obey one clearer runtime contract.
* Safety: dangerous tool execution paths have fewer policy gaps.
* Testability: tool/permission contracts become easier to verify with focused tests.
* Product parity: H01/H02 move from broad partial to explicit MVP closeout or tightly scoped residual partial.

## Corresponding Highlights

* `H01 Tool-first capability runtime`
* `H02 Permission runtime and hard safety`

## Corresponding Modules

* `coding_deepgent.tool_system`
* `coding_deepgent.permissions`
* `coding_deepgent.filesystem`
* domain tool modules with model-facing capability exposure

## Out Of Scope

* HITL UI
* auto permission classifier
* remote trust/auth flows
* marketplace/install/update flows
* coordinator/mailbox/background runtime

## Acceptance Criteria

* [x] cc-haha source mapping for H01/H02 is recorded in this stage PRD.
* [x] local H01/H02 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H01/H02 become implemented or remain partial with an explicit minimal residual.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve reliability, safety, and testability. The local runtime effect is: model-facing tools obey a stricter capability/runtime contract, and permission decisions remain fail-closed with clearer regression coverage around workspace safety and policy-code mapping.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Tool-first runtime seam | `Tool.ts` and `AgentTool` treat tools as first-class runtime objects with explicit permission/call behavior | prevent silent drift in model-facing tool contracts | capability registry hardening + projection tests | partial | Align contract now; defer richer AgentTool runtime |
| Allowlist / runtime capability shape | `runAgent.ts` and `loadAgentsDir.ts` preserve explicit tool allow/disallow shaping | keep local tool exposure explicit and bounded | capability projection and declarable/exposure tests | partial | Align through registry projections |
| Hard permission / filesystem safety | permission types + filesystem shell/path gates are hard safety chokepoints | keep local shell/path execution fail-closed | `PermissionManager`, `ToolPolicy`, `pattern_policy`, trusted-workdir wiring tests | align | Close out MVP with contract tests now |
| Rich team/agent permission lifecycle | `AgentTool` includes deeper agent selection, teammate, resume, and lifecycle flows | useful later but not required for current MVP | none | defer | Keep out of Stage 21 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/Tool.ts`
* `/root/claude-code-haha/src/tools/AgentTool/AgentTool.tsx`
* `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentToolUtils.ts`
* `/root/claude-code-haha/src/tools/AgentTool/loadAgentsDir.ts`
* `/root/claude-code-haha/src/tools/AgentTool/forkSubagent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/resumeAgent.ts`
* `/root/claude-code-haha/src/types/permissions.ts`
* `/root/claude-code-haha/src/utils/permissions/permissions.ts`
* `/root/claude-code-haha/src/utils/permissions/filesystem.ts`
* `/root/claude-code-haha/src/tools/BashTool/bashPermissions.ts`
* `/root/claude-code-haha/src/tools/PowerShellTool/powershellPermissions.ts`
* `/root/claude-code-haha/src/tools/PowerShellTool/modeValidation.ts`

## Technical Approach

* Harden H01 by rejecting duplicate builtin tool names before the capability registry can be fed a silently overwritten `tool_by_name` mapping.
* Add H01 contract tests for:
  * duplicate-name rejection
  * enabled/disabled capability exposure
  * extension exposure projection
  * container wiring of permission settings
* Add H02 contract tests for:
  * `ToolPolicyCode` mapping
  * negative `pattern_policy()` cases for workspace escape patterns

## Checkpoint: Stage 21

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added a duplicate builtin tool-name guard in `build_builtin_capabilities()`.
- Added H01 contract tests for duplicate names, enabled/disabled exposure projection, extension projection, and container-level permission/trusted-workdir wiring.
- Added H02 contract tests for `ToolPolicyCode` mapping and `pattern_policy()` workspace-escape rejection.

Corresponding highlights:
- `H01 Tool-first capability runtime`
- `H02 Permission runtime and hard safety`

Corresponding modules:
- `coding_deepgent.tool_system.capabilities`
- `coding_deepgent.permissions.manager`
- `coding_deepgent.filesystem.policy`
- `coding_deepgent.containers.tool_system`
- `coding_deepgent.containers.app`

Tradeoff / complexity:
- Chosen: close H01/H02 with contract hardening and one small code guard instead of a broader runtime redesign.
- Deferred: richer AgentTool lifecycle, remote/team permission flows, UI approval, classifier logic.
- Why this complexity is worth it now: H01/H02 were already broadly implemented; the remaining MVP risk was mostly silent contract drift and edge-case gaps.

Verification:
- `pytest -q coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_permissions.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_mcp.py coding-deepgent/tests/test_tools.py`
- `ruff check coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_permissions.py`
- `mypy coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_permissions.py`

Boundary findings:
- The main residual H01/H02 risk was contract-level, not architectural.
- `tool_by_name` duplicate overwrite needed an explicit guard to keep the tool-first runtime fail-closed.

Decision:
- continue

Reason:
- Stage 21 is complete and Stage 22 (H03/H04 prompt + dynamic context closeout) remains a direct next milestone from the canonical dashboard.
