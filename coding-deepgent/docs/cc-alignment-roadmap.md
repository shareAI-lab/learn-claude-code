# coding-deepgent cc alignment roadmap

## Scope

`coding-deepgent` is the product-track LangChain/LangGraph implementation of selected Claude Code / cc-haha runtime ideas. This document records product-local alignment decisions for Stage 4 and later.

## Expected effect

Aligning Stage 4 should improve safety, maintainability, context quality, and testability. The local runtime effect is: tools run behind one deterministic permission decision layer, lifecycle hooks exist as a future extension seam, and prompt/context assembly becomes structured without replacing LangChain's `create_agent` runtime.

## Evidence policy

- Secondary target map: `lintsinghua/claude-code-book` / local `/root/claude-code-haha/docs/must-read/*`.
- Primary implementation evidence: local `NanmiCoder/cc-haha` checkout at `/root/claude-code-haha`, commit `d166eb8`.
- Local implementation must stay LangChain-first: `create_agent`, `AgentMiddleware`, strict Pydantic tools, `Command(update=...)`, state/context schemas, checkpointer/store before custom runtime.

## Alignment matrix

- `/root/claude-code-haha/src/types/permissions.ts:PermissionMode` -> external five-mode union (`default`, `plan`, `acceptEdits`, `bypassPermissions`, `dontAsk`) in `coding_deepgent.permissions.modes` -> align -> implement now; defer `auto` and `bubble`.
- `/root/claude-code-haha/src/utils/permissions/permissions.ts:ask/dontAsk branches` -> Stage 4 `ask` becomes deterministic non-executing `ToolMessage` + runtime event, and `dontAsk` converts the same path into explicit denial -> partial -> no UI/human-interrupt approval yet.
- `/root/claude-code-haha/src/Tool.ts:Tool.checkPermissions` and `ToolPermissionContext` -> `ToolGuardMiddleware` delegates to a product-local `PermissionManager` before handler execution -> align -> use LangChain `AgentMiddleware`, not a custom tool executor.
- `/root/claude-code-haha/src/utils/queryContext.ts:fetchSystemPromptParts` -> `PromptContext` exposes default system prompt parts, user context, and system context -> align -> keep builder small and compatible with `create_agent`.
- `/root/claude-code-haha/src/types/hooks.ts:HookEvent` and hook JSON output schemas -> local sync hook registry with strict `HookPayload` / `HookResult` schemas for selected lifecycle events -> partial -> no HTTP/prompt/agent hooks yet.
- `/root/claude-code-haha/src/query.ts:tool budget/snip/microcompact/context collapse/autocompact sequence` -> later `compact/` seam after prompt/context foundation -> defer -> Stage 5 candidate.
- `/root/claude-code-haha/src/utils/tasks.ts` and `src/tools/Task*Tool/*` -> future store-backed task domain separate from TodoWrite -> defer -> Stage 6 candidate.
- `/root/claude-code-haha/src/components/permissions/*` -> no local UI parity target -> do-not-copy -> Rich CLI only unless explicitly requested.

## Stage 5 memory/context rows

- `/root/claude-code-haha/src/memdir/memoryTypes.ts` -> `MemoryRecord` / `SaveMemoryInput` as strict Pydantic schemas -> partial -> store-backed foundation only.
- `/root/claude-code-haha/src/memdir/findRelevantMemories.ts` -> deterministic `recall_memories()` helper with bounded result count -> partial -> no embedding/vector recall yet.
- `/root/claude-code-haha/src/utils/queryContext.ts:fetchSystemPromptParts` -> prompt builder accepts rendered memory context as a distinct prompt section -> align -> use existing `create_agent` prompt path.
- `/root/claude-code-haha/src/query.ts:applyToolResultBudget` -> deterministic `apply_tool_result_budget()` helper for oversized tool-result strings -> partial -> no message-history projection/pruning in Stage 5.

## Next candidates

1. Stage 5: memory + context budget + compact seam.
2. Stage 6: skills + subagents + durable task graph.
3. Stage 7: MCP/plugin extension platform.
