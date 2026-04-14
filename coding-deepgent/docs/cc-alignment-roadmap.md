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

## Stage 6 skills/tasks/subagents rows

- `/root/claude-code-haha/src/tools/SkillTool/SkillTool.ts` -> local `load_skill` tool loads one `SKILL.md` by explicit name -> partial -> no plugin/MCP/remote skills.
- `/root/claude-code-haha/src/utils/tasks.ts` and `/root/claude-code-haha/src/tools/Task*Tool/*` -> store-backed `task_create/get/list/update` with strict transitions -> partial -> no coordinator/team runtime yet.
- `/root/claude-code-haha/src/tools/AgentTool/AgentTool.tsx` -> minimal synchronous/stateless `run_subagent` tool with exact child-tool allowlist -> partial -> no background/worktree/mailbox/resume.
- `/root/claude-code-haha/src/tools/SendMessageTool/*` -> mailbox/send-message semantics -> defer -> requires later multi-agent runtime.

## Prior completed candidates

1. Stage 5: memory + context budget + compact seam.
2. Stage 6: skills + subagents + durable task graph.
3. Stage 7: local MCP/plugin extension foundation.

## Stage 7 MCP/plugin extension rows

## Expected effect

Aligning Stage 7 should improve product extensibility, capability registration, and future ecosystem readiness. The local runtime effect is: already-discovered MCP tools can be carried into the LangChain agent tool list through typed `ToolCapability` entries, MCP resources stay as separate read-surface metadata, and local plugin manifests can declare bounded local capabilities without executing plugin code or replacing the runtime.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| MCP tool provenance | `/root/claude-code-haha/src/services/mcp/types.ts` models connected servers, serialized tools, resources, and scoped config metadata | keep extension tool origin visible and deterministic | `coding_deepgent.mcp.MCPSourceMetadata` + `MCPToolDescriptor` | partial | Convert already-discovered local descriptors only; no connection manager |
| MCP resources | `/root/claude-code-haha/src/services/mcp/utils.ts:filterResourcesByServer` keeps resources separate from tools | prevent read surfaces becoming executable capabilities | `MCPResourceRegistry` | align | Store resources outside `CapabilityRegistry` |
| MCP connection/config breadth | `/root/claude-code-haha/src/services/mcp/config.ts` and `MCPConnectionManager.tsx` cover config merging, auth, and multiple transports | avoid premature protocol/platform creep | none in Stage 7 | defer | Official LangChain adapters remain future connection seam |
| Plugin manifest loading | `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts` loads plugin metadata/components from filesystem/cache sources | local extension declarations become deterministic and inspectable | `coding_deepgent.plugins.loader` + `PluginRegistry` | partial | Strict local `plugin.json` metadata only |
| Plugin MCP/platform fields | `/root/claude-code-haha/src/utils/plugins/schemas.ts` allows rich commands/skills/hooks/MCP/LSP/platform fields | protect current runtime from silent mutation | `PluginManifest(extra="forbid")` | do-not-copy now | Only `name`, `description`, `version`, `skills`, `tools`, `resources` |
| Skill extension bridge | `/root/claude-code-haha/src/tools/SkillTool/*` and plugin skill loading normalize multiple skill sources | preserve future skill packaging path | manifest `skills: tuple[str, ...]` | partial | Declare local identifiers only; no forked/remote/plugin skill execution |
| Hook/platform integration | `/root/claude-code-haha/src/utils/hooks/*` provides a programmable extension layer | useful later, but unsafe to merge with manifest foundation now | existing Stage 4 hook registry | defer | Plugins cannot declare hook/runtime settings in Stage 7 |

### Stage 7 references

- cc-haha source evidence: `/root/claude-code-haha/src/services/mcp/types.ts`, `/root/claude-code-haha/src/services/mcp/config.ts`, `/root/claude-code-haha/src/services/mcp/utils.ts`, `/root/claude-code-haha/src/utils/plugins/schemas.ts`, `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`, `/root/claude-code-haha/src/utils/plugins/mcpPluginIntegration.ts`, `/root/claude-code-haha/src/tools/SkillTool/constants.ts`, `/root/claude-code-haha/src/tools/SkillTool/prompt.ts`, `/root/claude-code-haha/docs/must-read/06-extension-platform.md`.
- LangChain reference: official LangChain MCP docs describe `langchain-mcp-adapters`, `MultiServerMCPClient.get_tools()`, stateless default sessions, and a separate resource-loading path via `get_resources()` / resource blobs.

## Updated next candidates

1. Stage 7.x: richer MCP config loading only if it can use official LangChain adapter seams without new runtime loops.
2. Stage 8: recovery/checkpoint UX, task continuation, or multi-agent coordination once extension surfaces remain stable.


## Stage 8 recovery/evidence/runtime-continuation rows

## Expected effect

Aligning Stage 8 should improve long-task continuity and verification readiness. The local runtime effect is: a recorded session can be resumed with history, latest runtime state, and recent evidence visible as a recovery brief, while later Task, Memory, and Subagent upgrades can attach to the same recovery/evidence seam.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Transcript recovery | `/root/claude-code-haha/docs/must-read/02-agent-runtime.md` describes transcript + metadata as resume prerequisites | resumed sessions expose enough execution context to continue | `JsonlSessionStore` history/state/evidence loading | partial | Add session evidence records; defer full metadata runtime |
| Task/runtime continuation | `/root/claude-code-haha/docs/must-read/04-task-workflow.md` describes stop/resume/poll around task runtime | future task/subagent work can link evidence to continuation | session-scoped evidence first | defer/partial | Defer task-level evidence store until task-core upgrade |
| LangChain runtime | official LangChain docs describe `create_agent`, runtime context/store, and thread IDs | continuation stays on LangGraph runtime seams | `RuntimeInvocation`, session `thread_id`, CLI resume | align | Preserve runtime boundary; no custom query loop |
| Evidence ledger | cc-haha session/task analysis keeps transcripts and execution facts separate from UI | tests and runtime facts become recoverable context | `SessionEvidence` + `RecoveryBrief` | partial | No model-visible evidence tool in Stage 8 |

## Updated next candidates after Stage 8

1. Facility B: Permission / trust boundary hardening.
2. Facility C: Hooks / lifecycle expansion.
3. Facility D: MCP / plugin real loading via official adapter seams.
4. Then resume the nine cc-core primary system upgrades.


## Stage 9 permission/trust-boundary rows

## Expected effect

Aligning Stage 9 should improve deterministic safety before later Skill, Task, Session, and MCP/plugin upgrades. The local runtime effect is: permission rules become typed local settings, trusted extra directories can be granted without global path weakening, and extension capabilities carry trust metadata so policy can treat them more conservatively than builtin tools.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Permission layering | `/root/claude-code-haha/docs/must-read/05-permission-security.md` shows mode/rules/filesystem/strategy layers | preserve one permission runtime around all tools | `PermissionManager` + `ToolGuardMiddleware` | align | Harden existing path rather than redesign |
| Rule sources and directories | cc-haha permission types/settings track rule origins and additional directories | allow explicit trusted scope without broadening workspace safety | typed settings-backed rules + `trusted_workdirs` | partial | local-only settings first |
| Extension trust | later MCP/plugin tools expand execution surface | distinguish builtin vs extension trust at policy time | `ToolCapability(source, trusted)` | partial | deterministic conservative trust only |

## Updated next candidates after Stage 9

1. Facility C: Hooks / lifecycle expansion.
2. Facility D: MCP / plugin real loading via official adapter seams.
3. Then resume the nine cc-core primary system upgrades.


## Stage 10 hooks/lifecycle rows

## Expected effect

Aligning Stage 10 should improve lifecycle extensibility before deeper Memory, Task, Session, and Skill upgrades. The local runtime effect is: deterministic local hooks can now observe and, where safe, block key lifecycle moments at the app and tool boundaries without replacing the LangChain runtime.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Hook event/result schema | `/root/claude-code-haha/src/types/hooks.ts` validates hook outputs and event-specific payloads | keep typed local hook contracts | `HookPayload`, `HookResult`, `HookDispatchOutcome` | align | local sync schema only |
| Hook runtime integration | cc-haha docs describe hooks as a programmable middleware layer, not an afterthought | lifecycle extension seam lives at real runtime boundaries | `app.agent_loop()` + `ToolGuardMiddleware` | partial | local sync + deterministic block only |
| Hook platform breadth | cc-haha supports session/frontmatter/skill/HTTP/async hooks | avoid platform creep before the local seam proves useful | defer broader hook surfaces | defer | async/plugin/remote hooks remain later work |

## Updated next candidates after Stage 10

1. Facility D: MCP / plugin real loading via official adapter seams.
2. Then resume the nine cc-core primary system upgrades with facilities A/B/C in place.


## Stage 11 MCP/plugin real loading rows

## Expected effect

Aligning Stage 11 should turn the local MCP/plugin foundation into a usable local loading seam. The local runtime effect is: root `.mcp.json` config becomes a strict project config surface, official adapter-backed MCP tool loading can contribute capabilities when available, and plugin declarations are validated against known local capabilities/skills without opening platform or trust-scope creep.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| `.mcp.json` config | Deep Agents / Claude-compatible docs use root `.mcp.json` as MCP config surface | familiar local config surface | typed root `.mcp.json` loader | partial | root-only in this stage |
| Official MCP loading | LangChain docs use `MultiServerMCPClient(...).get_tools()` | real tools flow through official adapter seam | optional adapter-backed loader | align | adapter required but not auto-installed |
| Plugin declaration validation | Stage 7 local plugin manifests declare local tools/skills/resources | plugins can safely reference known capabilities without runtime control | validated plugin registry | partial | validation-only, no runtime replacement |

## Updated next candidates after Stage 11

1. Resume the nine cc-core primary system upgrades with facilities A/B/C/D in place.
2. Revisit dependency installation for first-class MCP support only if the user explicitly asks.
