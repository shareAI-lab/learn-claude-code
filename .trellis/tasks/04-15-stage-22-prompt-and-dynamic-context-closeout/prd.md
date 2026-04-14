# Stage 22: Prompt And Dynamic Context Closeout

## Goal

Close the highest-value remaining H03/H04 MVP gaps by auditing and tightening the layered prompt contract and the dynamic context assembly path.

## Function Summary

This stage should identify and implement the smallest concrete changes that make prompt layering and dynamic context assembly count as MVP-complete for Approach A, without turning prompt text into a giant manual or introducing a custom query runtime.

## Expected Benefit

* Reliability: prompt and context responsibilities are clearer and less likely to drift.
* Context-efficiency: dynamic context stays bounded and purposeful.
* Maintainability: prompt logic and dynamic context injection are easier to audit and test.

## Corresponding Highlights

* `H03 Layered prompt contract`
* `H04 Dynamic context protocol`

## Corresponding Modules

* `coding_deepgent.prompting`
* `coding_deepgent.runtime`
* `coding_deepgent.memory`
* `coding_deepgent.sessions`
* `coding_deepgent.compact`
* `coding_deepgent.middleware`

## Out Of Scope

* giant prompt rewrites
* custom query runtime
* provider-specific cache tuning
* UI/TUI prompt surfaces
* coordinator / mailbox / background runtime

## Acceptance Criteria

* [x] cc-haha source mapping for H03/H04 is recorded in this stage PRD.
* [x] local H03/H04 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H03/H04 become implemented or remain partial with an explicit minimal residual.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve reliability, context-efficiency, and maintainability. The local runtime effect is: prompt assembly stays layered and settings-backed, while dynamic context stays typed, bounded, and composition-safe across resume, todo, memory, and compact flows.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Layered prompt assembly | prompt order and cache-safe boundary matter more than giant prompt text | prevent prompt customization drift and keep stable base prompt semantics | prompt layering contract tests for `build_system_prompt` / `build_prompt_context` | partial | Align contract now; defer richer cache-specific machinery |
| Dynamic context via attachments | dynamic context is a protocol, not a loose prompt string | keep local context typed, ordered, bounded, and merge-safe | model-call composition test across resume + todo + memory; explicit H04 MVP boundary | partial | Align bounded protocol now |
| Extension / coordinator prompt branches | upstream has broader coordinator, proactive, attachment, and UI-driven prompt paths | useful later but not required for current MVP | none | defer | Keep out of Stage 22 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/constants/prompts.ts`
* `/root/claude-code-haha/src/utils/systemPrompt.ts`
* `/root/claude-code-haha/src/utils/queryContext.ts`
* `/root/claude-code-haha/src/context.ts`
* `/root/claude-code-haha/src/utils/api.ts`
* `/root/claude-code-haha/src/services/api/claude.ts`
* `/root/claude-code-haha/src/commands/btw/btw.tsx`
* `/root/claude-code-haha/src/cli/print.ts`
* `/root/claude-code-haha/src/utils/attachments.ts`
* `/root/claude-code-haha/src/utils/messages.ts`
* `/root/claude-code-haha/src/components/messages/nullRenderingAttachments.ts`
* `/root/claude-code-haha/src/components/messages/AttachmentMessage.tsx`
* `/root/claude-code-haha/src/utils/sessionStart.ts`
* `/root/claude-code-haha/src/services/tools/toolHooks.ts`

## Technical Approach

* Close H03 with direct settings-backed prompt layering tests instead of rewriting prompt composition.
* Close H04 with a model-call-boundary composition test that proves:
  * resume context stays in message history, not duplicated into the system prompt
  * todo context appears before memory context
  * memory context and todo context compose cleanly through shared payload merge behavior
* Narrow H04 MVP boundary explicitly:
  * included: typed/bounded dynamic context for resume, todo, memory, and compact flows
  * deferred from this stage: `skills/resources` as first-class context payload kinds

## Checkpoint: Stage 22

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added a direct `build_system_prompt(settings)` test to pin the H03 layered prompt contract.
- Added an end-to-end model-call composition test proving resume history, todo context, and memory context compose without duplication and with stable ordering.
- Explicitly narrowed H04 MVP closeout to the current typed/bounded local protocol for resume, todo, memory, and compact-related context.

Corresponding highlights:
- `H03 Layered prompt contract`
- `H04 Dynamic context protocol`

Corresponding modules:
- `coding_deepgent.prompting`
- `coding_deepgent.agent_service`
- `coding_deepgent.context_payloads`
- `coding_deepgent.memory.middleware`
- `coding_deepgent.todo.middleware`
- `coding_deepgent.sessions`

Tradeoff / complexity:
- Chosen: contract tests plus explicit boundary clarification.
- Deferred: skills/resources as first-class context payload kinds, prompt cache machinery, coordinator/proactive branches, UI rendering polish.
- Why this complexity is worth it now: H03/H04 were already mostly implemented; the remaining MVP risk was silent composition drift and an unclear scope boundary.

Verification:
- `pytest -q coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_context_payloads.py coding-deepgent/tests/test_memory_context.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_cli.py::test_sessions_resume_uses_recovery_brief_continuation_history`
- `ruff check coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_memory_integration.py`
- `mypy coding-deepgent/src/coding_deepgent/prompting/builder.py coding-deepgent/src/coding_deepgent/agent_service.py coding-deepgent/src/coding_deepgent/context_payloads.py coding-deepgent/src/coding_deepgent/memory/middleware.py coding-deepgent/src/coding_deepgent/todo/middleware.py coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_memory_integration.py`

Boundary findings:
- H04 should not silently imply skills/resources attachment parity in the current MVP.
- Resume context belongs in message history, while todo/memory remain dynamic system-context payloads; that split is part of the local contract.

Decision:
- continue

Reason:
- Stage 22 is complete and Stage 23 (H05/H06 context pressure + session continuity closeout) remains the next direct milestone from the canonical dashboard.
