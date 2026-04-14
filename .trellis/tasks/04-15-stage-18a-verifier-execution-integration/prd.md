# Stage 18A: Verifier Execution Integration

## Goal

Upgrade the explicit verifier boundary from a structured contract-only seam to a real bounded verifier execution path on the existing `run_subagent` tool surface.

## Upgraded Function

The workflow system is upgraded from verifier plan-boundary plumbing to actual synchronous verifier execution using a read-only child agent invocation.

## Expected Benefit

* Product behavior: verifier calls now perform real verification work instead of returning a placeholder acceptance string.
* Reliability: the verifier runs against the durable plan boundary with a fixed read-only tool pool and explicit system instructions.
* Testability: execution wiring becomes locally testable without adding coordinator runtime, mailbox state, or background workers.

## Out of Scope

* coordinator runtime
* mailbox / SendMessage
* background worker execution
* approval UI
* automatic task mutation after verifier completion
* general subagent runtime deepening beyond verifier execution
* task-backed local agent lifecycle objects

## Requirements

* Keep `run_subagent` as the only model-visible entrypoint for verifier execution.
* Keep verifier execution synchronous and explicitly bounded to the current tool call.
* Execute verifier work through a real child-agent invocation instead of a placeholder string.
* Reuse the existing durable plan lookup and rendered verifier task payload from Stage 17D.
* Restrict the verifier child tool pool to the existing read-only allowlist:
  * `read_file`
  * `glob`
  * `grep`
  * `task_get`
  * `task_list`
  * `plan_get`
* Keep mutating tools unavailable to the verifier child:
  * no file edits
  * no task / plan mutation
  * no memory writes
  * no nested `run_subagent`
* Use a verifier-specific system prompt that preserves the read-only/adversarial verification role.
* Preserve the existing structured `VerifierSubagentResult` output contract.
* Keep the general subagent path unchanged for now.

## Acceptance Criteria

* [ ] verifier execution uses a real child-agent invocation when no test-only child factory is injected.
* [ ] verifier child receives only the read-only allowlisted tools.
* [ ] verifier child uses a verifier-specific system prompt instead of the generic placeholder behavior.
* [ ] verifier execution stays synchronous and does not introduce coordinator/background runtime.
* [ ] `run_subagent` still returns parseable `VerifierSubagentResult` JSON for verifier calls.
* [ ] general subagent behavior remains unchanged.
* [ ] Focused tests, targeted lint, and targeted mypy pass.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve reliability, testability, and product parity. The local runtime effect is: verifier calls now execute as a real read-only verification agent with bounded tools and explicit verifier instructions, while intentionally deferring cc-haha's richer background/team runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Verification agent role | built-in verification agent has a dedicated adversarial read-only prompt | verifier execution is harder to silently collapse into a friendly placeholder | verifier-specific child system prompt | partial | Align role now with a smaller prompt |
| Agent as tool | verification runs through the `AgentTool` path instead of prompt-only narration | local verifier should execute through the model/tool runtime, not just return acceptance text | real child invocation behind `run_subagent` | partial | Implement now on current tool surface |
| Disallowed mutating tools | verification agent excludes editing/writing/agent-recursion tools | local verifier remains safely read-only | fixed allowlist + forbidden mutation surfaces | align | Preserve and enforce |
| Background runtime | upstream verifier can run with richer task/runtime lifecycle | local runtime should stay synchronous and bounded for now | none | defer | Keep out of scope |

### Source files inspected

* `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`

## LangChain Architecture

Use:

* `create_agent` for the bounded verifier child invocation
* existing tool objects with a fixed read-only subset
* existing runtime context/store plumbing where needed
* a small verifier execution helper rather than a new orchestration layer

Avoid:

* coordinator/mailbox abstractions
* background execution wrappers
* prompt-only fake verifier execution
* speculative task-object runtime layers

## Technical Approach

* Keep the existing Stage 17D verifier plan rendering path.
* Add a small verifier execution helper that:
  * builds the fixed read-only tool subset
  * applies a verifier-specific system prompt
  * invokes a bounded child agent synchronously
  * extracts the final verifier text response
* Keep the test-only `child_agent_factory` seam for direct unit tests.
* Add focused tests for:
  * verifier execution integration path
  * exact verifier child tool set
  * verifier prompt/runtime wiring
  * unchanged general subagent behavior

## Checkpoint: Stage 18A

State:
- checkpoint

Verdict:
- ITERATE

Implemented:
- Replaced the verifier placeholder acceptance path with a real synchronous child-agent invocation on the existing `run_subagent` verifier branch.
- Added a fixed verifier child tool map limited to:
  - `read_file`
  - `glob`
  - `grep`
  - `task_get`
  - `task_list`
  - `plan_get`
- Added a verifier-specific read-only system prompt.
- Derived a bounded child runtime invocation with a verifier-specific agent name and thread id suffix.
- Preserved the Stage 17D durable plan lookup, rendered verifier task payload, and structured `VerifierSubagentResult` output.
- Preserved the existing general subagent behavior and the test-only `child_agent_factory` seam.

Verification:
- `pytest -q coding-deepgent/tests/test_subagents.py`
- `pytest -q coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_app.py`
- `ruff check coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_subagents.py`
- `mypy coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_subagents.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
  - `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
- Aligned:
  - verifier now executes as a real read-only agent/tool path rather than a prompt-only placeholder.
  - verifier keeps a dedicated verification-role system prompt and a bounded read-only tool surface.
- Deferred:
  - coordinator/background runtime
  - mailbox/message passing
  - richer task-backed local-agent lifecycle

LangChain architecture:
- Primitive used:
  - `create_agent`
  - fixed tool subset
  - `ToolGuardMiddleware`
  - existing runtime/store plumbing
- Why no heavier abstraction:
  - 18A only needs a bounded execution seam on the existing tool path; coordinator/task-object runtime remains outside scope.

Boundary findings:
- Importing the shared app runtime helper into the subagent module created a circular import through the tool container, so verifier execution now keeps a local invocation boundary.
- Verifier execution currently builds a fresh model for each verifier call; sharing parent-model/runtime optimization is a later concern and not needed for the current bounded stage.

Decision:
- adjust

Reason:
- Stage 18A is implemented and verified, but there is no explicit next verifier/runtime sub-stage defined in the current Trellis task set. Auto-continuing would create new scope without a written PRD or checkpoint target.
