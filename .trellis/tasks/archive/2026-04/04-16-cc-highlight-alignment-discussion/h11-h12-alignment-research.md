# H11/H12 Alignment Research (cc-haha vs coding-deepgent)

> Source-backed inventory of cc-haha subagent highlights, local implementation state,
> and gap matrix to drive the next brainstorm round.
>
> cc-haha root: `/root/claude-code-haha/`
> local root: `coding-deepgent/src/coding_deepgent/`
> Reading cutoff: 2026-04-17

---

## 1. cc-haha Highlight Inventory

### A. Tool entry / agent schema

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| A1 | `Agent` tool with `subagent_type` param + per-type `whenToUse` catalog | `tools/AgentTool/AgentTool.tsx`, `builtInAgents.ts` | Model selects agent variant; per-agent system prompt, tool pool, model, permission mode | Model-visible agent discovery, prompt-cache partitioning per agent |
| A2 | Per-agent `tools: []` or `['*']` with `disallowedTools` and `allowedAgentTypes` spec | `agentToolUtils.ts:122-225` (`resolveAgentTools`) | Wildcard expansion + deny-list + per-agent-type allowlist baked into Agent tool schema | Deterministic capability surface per agent |
| A3 | Per-agent `permissionMode` override, gated by parent mode | `runAgent.ts:416-452` | Agent can declare `bubble`/`plan`/`acceptEdits`; not applied if parent is bypass/acceptEdits/auto | Read-only agents can't be hijacked into write mode |
| A4 | Per-agent frontmatter `hooks` scoped to agent lifecycle | `runAgent.ts:564-575`, `utils/hooks/registerFrontmatterHooks.ts` | Register-on-spawn, clear-on-exit; Stop→SubagentStop auto-rewrite | Agents ship their own lifecycle side-effects without leaking to parent |
| A5 | Per-agent `skills` preload | `runAgent.ts:578-646` | Skill names resolved via multiple strategies (exact/plugin-qualified/suffix); loaded content injected as initial user message with `isMeta` | Skills activate deterministically per agent |
| A6 | Per-agent `mcpServers` additive to parent | `runAgent.ts:95-217` | Inline `{name: cfg}` or string reference; inline creates dedicated clients with cleanup, referenced shares parent's memoized client | Agent-specific MCP without leaking or duplicate-cleanup |
| A7 | Per-agent `omitClaudeMd` / gitStatus strip for read-only agents | `runAgent.ts:386-410` | Explore/Plan drop CLAUDE.md (~5-15 Gtok/week) + stale gitStatus (~1-3 Gtok/week) | Context-budget optimization on high-volume agents |
| A8 | Per-agent `effort`, `maxTurns`, `model` overrides | `runAgent.ts:340, 482-485, 756` | Applied via `getAgentModel`, `agentGetAppState`, `query({maxTurns})` | Cost/quality tuning per agent profile |
| A9 | `criticalSystemReminder_EXPERIMENTAL` passthrough | `runAgent.ts:711-713` | Per-agent critical reminder threaded through subagent context | Targeted guardrail injection |

### B. Runtime child-loop

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| B1 | `createSubagentContext` isolated child context | `runAgent.ts:700-714`, `utils/forkedAgent.ts` | New agentId, own messages/readFileState/abortController; sync shares setAppState+responseLength, async fully isolated | Clean parent/child runtime boundary without global state |
| B2 | Async vs sync AbortController policy | `runAgent.ts:524-528` | Sync: shares parent's; Async: fresh unlinked controller (or explicit child-linked via `createChildAbortController` when parent aborts must cascade) | Correct cancellation semantics for foreground vs background |
| B3 | `shouldAvoidPermissionPrompts` + `awaitAutomatedChecksBeforeDialog` flags | `runAgent.ts:436-463` | Async agents without UI auto-deny; async with UI waits for classifier/hook before dialog | Background agents never block on missing UI |
| B4 | `allowedTools` replaces session rules, preserves SDK cliArg | `runAgent.ts:465-479` | Per-spawn tool permission scope without parent rule leakage | Correct least-privilege per spawn |
| B5 | SubagentStart hooks with `additionalContexts` | `runAgent.ts:530-555` | Hook-returned text injected as `createAttachmentMessage({type: 'hook_additional_context'})` before query | Extension point for agent-specific prelude without prompt rewrites |
| B6 | `filterIncompleteToolCalls` before spawn | `runAgent.ts:866-904` | Strips assistant messages whose tool_uses lack matching tool_results | API-error prevention on inherited context |
| B7 | Side-chain transcript: O(1) per message with parent-chain UUID | `runAgent.ts:735-805`, `utils/sessionStorage.ts:recordSidechainTranscript` | Each message appended with `lastRecordedUuid` as parent link; initial batch fire-and-forget | Transcript is sufficient to reconstruct the tree |
| B8 | Per-agent metadata persisted | `runAgent.ts:738-742` | `writeAgentMetadata(agentId, {agentType, worktreePath, description})` | Enables resume routing without replaying spawn args |
| B9 | `transcriptSubdir` grouping | `runAgent.ts:351-353` | Optional `workflows/<runId>/` grouping for coordinated subagents | Multi-subagent run isolation on disk |
| B10 | Perfetto hierarchy trace | `runAgent.ts:356-359, 832` | Register parent+child for agent-tree visualization | Observability of agent graph |
| B11 | Per-agent API dump path | `runAgent.ts:362-366` | Dedicated `getDumpPromptsPath(agentId)` for API call replay | Debuggability per agent |
| B12 | Finally-block cleanup inventory | `runAgent.ts:816-858` | MCP, session hooks, prompt cache tracking, file state cache, perfetto, todos entry, bash tasks, monitor-MCP tasks all cleaned in one place | No-leak lifecycle invariant |
| B13 | `killShellTasksForAgent` on exit | `runAgent.ts:847`, `tasks/LocalShellTask/killShellTasks.ts` | Background bash tasks spawned by agent get killed when agent exits (prevents PPID=1 zombies) | Real cleanup of spawned processes |
| B14 | Attachment / max_turns_reached passthrough | `runAgent.ts:771-790` | `structured_output` attachments yielded; `max_turns_reached` breaks loop cleanly | Structured-output and turn-limit semantics honored |
| B15 | Stream event TTFT forwarding | `runAgent.ts:762-768` | Parent's API metrics display updates during subagent | UX metrics visibility during subagent |

### C. Fork / cache

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| C1 | Implicit-fork mode (no `subagent_type`) | `forkSubagent.ts:32-71` | `FORK_AGENT` synthetic definition with `tools:['*']`, `model:'inherit'`, `permissionMode:'bubble'`, `maxTurns:200` | One-command "run same agent in background" |
| C2 | Recursive-fork guard | `forkSubagent.ts:78-89` | Detect `<FORK_BOILERPLATE>` in history → reject new fork | Prevent runaway fork trees |
| C3 | `buildForkedMessages` byte-identical prefix | `forkSubagent.ts:107-169` | Every child gets identical placeholder tool_results + per-child directive text block as final diff | Maximizes prompt-cache sharing across parallel forks |
| C4 | `useExactTools` bypass of resolveAgentTools | `runAgent.ts:500-502, 682-684` | Fork inherits parent's thinking config + isNonInteractive for byte-exact API prefix | Cache-identical forks |
| C5 | `override.systemPrompt` threads rendered bytes | `runAgent.ts:508-518`, `resumeAgent.ts:116-148` | Reconstructing via `getSystemPrompt` risks GrowthBook drift; threading rendered bytes is stable | Cache-stable system prompt across fork lineage |
| C6 | Worktree notice injection for isolated fork children | `forkSubagent.ts:205-210` | Child gets explicit path-translation guidance when spawned in isolated worktree | Avoids silent path drift |
| C7 | `onCacheSafeParams` exposes fork handle to background summarizer | `runAgent.ts:721-730`, `services/AgentSummary/agentSummary.ts` | Subagent emits its CacheSafeParams so another fork can share its cache for periodic summaries | Zero-additional-cache summaries |

### D. Resume

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| D1 | Transcript-based resume with sanitization | `resumeAgent.ts:63-74` | Filter unresolvedToolUses + orphanedThinking + whitespaceOnlyAssistant; load metadata in parallel | Clean resume without API errors |
| D2 | `reconstructForSubagentResume` content-replacement state | `resumeAgent.ts:75-79`, `utils/toolResultStorage.ts` | Rebuild replacement state so same tool results get replaced (prompt cache stable) | Cache stability across resume |
| D3 | Worktree stat + utime bump | `resumeAgent.ts:82-97` | Verify worktree still exists; bump mtime so stale-cleanup doesn't delete it | Resume robustness with isolated worktrees |
| D4 | Fork-resume system prompt reconstruction | `resumeAgent.ts:102-148` | Prefer `renderedSystemPrompt`; fallback reconstructs via `buildEffectiveSystemPrompt` | Preserve byte-exact prefix across resume |

### E. Lifecycle / lineage / persistence

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| E1 | `LocalAgentTaskState` strict schema | `tasks/LocalAgentTask/LocalAgentTask.tsx:116-148` | agentId, agentType, status, prompt, selectedAgent, result, error, progress, messages, pendingMessages, retain, diskLoaded, evictAfter, isBackgrounded, notified | Rich task record drives UI, recovery, dedup |
| E2 | Foreground/background split with signal | L280-L614 | `registerAgentForeground` returns promise that resolves on auto-background timeout or user trigger; `backgroundAgentTask` flips state mid-loop | User can hand off a running agent to background mid-run |
| E3 | `pendingMessages` drained at tool-round boundaries | L162-L192 | SendMessage tool enqueues; agent loop drains at round start | Safe mid-run input injection (no race with active tool call) |
| E4 | `appendMessageToLocalAgent` UI-transcript append | L175-L180 | Append to task.messages for UI without routing to API | Separates display-channel from agent-input-channel |
| E5 | `isPanelAgentTask` single-source predicate | L159-L161 | One predicate all pill/panel filters must use | No UI drift between filters |
| E6 | Parent-child abort cascade | L466-L490 (`registerAsyncAgent`) | Child AbortController linked to optional `parentAbortController` | In-process teammate aborts its subagents |
| E7 | `enqueueAgentNotification` single-shot + XML payload | L197-L262 | `notified` flag atomic check-and-set; TASK_NOTIFICATION tag with outputFile/status/summary/result/usage/worktree | Dedup notifications; model-parseable |
| E8 | `evictTaskOutput` + task-output symlink | `utils/task/diskOutput.ts` | Output file is a symlink to agent transcript path; eviction cleans symlink only | Disk recovery without duplicate writes |
| E9 | Progress tracker with usage + recent activities | L41-L115 | input_tokens (cumulative→latest), output_tokens (summed); `recentActivities` with classification (isSearch/isRead) and activity description | Accurate token accounting + human-readable progress |
| E10 | Cache eviction hint on subagent end | `agentToolUtils.ts:337-345` | Logs `tengu_cache_eviction_hint` with last_request_id | Inference layer can evict subagent's cache chain |
| E11 | Partial-result on kill | `agentToolUtils.ts:488-500`, lifecycle:658-667 | Extract last assistant text from messages; include in killed notification | Kill still returns what was accomplished |
| E12 | `retain` + `diskLoaded` cycle | L141-L148 | UI holding task blocks eviction, triggers disk bootstrap once, enables stream-append | UI can hold a background task open for viewing |

### F. Summary / return-value

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| F1 | Background periodic summarization | `services/AgentSummary/agentSummary.ts:46-179` | 30s timer forks subagent conversation with `canUseTool=deny` + identical cache params → 3-5 word present-tense summary | Live "what is agent doing" without extra cache burn |
| F2 | Cache-preserving summarization (no maxOutputTokens, tools kept but denied) | L94-L119 | Don't clamp budget_tokens (thinking config drift busts cache); keep tools in request, deny via callback | Prompt-cache sharing invariant |
| F3 | Summary gating: coordinator/fork/SDK-opt-in | `agentToolUtils.ts:517-553` | Only enabled when coordinator mode, fork enabled, or SDK summaries opt-in | Cost control |
| F4 | `finalizeAgentTool` strict result schema | `agentToolUtils.ts:227-357` | `{agentId, agentType, content, totalDurationMs, totalTokens, totalToolUseCount, usage}` with full cache creation/read breakdown | Machine-readable subagent result envelope |
| F5 | Fallback last-text scan when final message is pure tool_use | L303-L317 | Walk backward if final assistant has no text block | Robust result extraction |

### G. Built-in catalog

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| G1 | Tiered catalog with feature flags | `builtInAgents.ts:13-72` | general-purpose + statusline-setup (always), explore+plan (A/B), claude-code-guide (non-SDK), verification (flagged) | Staged rollout + entrypoint-aware surface |
| G2 | Coordinator mode swap | L35-L43 | Replaces entire catalog with `getCoordinatorAgents()` when in coordinator mode | Alternate agent-team topology |
| G3 | SDK kill-switch env | L25-L30 | `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS` for blank-slate SDK users | Embedder flexibility |
| G4 | Source tier trust: built-in / plugin / policySettings / user | `utils/settings/pluginOnlyPolicy.ts:isSourceAdminTrusted`, runAgent:117, 564 | Admin-trusted sources keep full frontmatter (hooks/MCP); user sources gated | Supply-chain boundary |

### H. Handoff safety

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| H1 | `classifyHandoffIfNeeded` transcript classifier on handoff | `agentToolUtils.ts:389-481` | In `auto` mode, LLM classifier reviews subagent output for policy violation → prepends SECURITY WARNING or blocks | Defense-in-depth against prompt-inject-exfil on subagent boundary |

---

## 2. Local coding-deepgent Current State

Sources inspected: `subagents/schemas.py`, `subagents/tools.py`, `subagents/__init__.py`,
`tasks/schemas.py`, `tasks/store.py`, `tasks/tools.py`; grep for `subagent|fork|AgentTool|child_runtime`
turned up only `runtime/context.py`, `runtime/invocation.py`, `sessions/evidence_events.py`,
`settings.py`, `tool_system/capabilities.py`, `containers/tool_system.py` — no additional
subagent-runtime surface.

Local surface:

- One tool `run_subagent` (`subagents/tools.py:425-455`) with `RunSubagentInput` schema: `task`, `agent_type ∈ {general, verifier}`, `plan_id?`, `max_turns` (pinned to 1).
- Two agent types:
  - `general`: returns stub string `"Subagent {agent_type} accepted task synchronously: {task}"` when no factory injected (`tools.py:369-375`). **No actual LLM child agent is invoked** in the shipped path.
  - `verifier`: real `create_agent` child via `_execute_verifier_subagent` (`tools.py:205-238`), read-only allowlist (`read_file`, `glob`, `grep`, `task_get`, `task_list`, `plan_get`), `ToolGuardMiddleware` with `build_capability_registry`, strict system prompt, final line must match `VERDICT: PASS|FAIL|PARTIAL`.
- `RuntimeInvocation` clone: `thread_id = <parent>:verifier:<plan_id>`, agent name suffix `-verifier` (`tools.py:167-188`).
- `append_evidence` on verdict parse (`tools.py:260-300`).
- `_subagent_spawn_pressure_guard` rejects spawn above `subagent_spawn_guard_ratio` of context window (`tools.py:378-422`).
- `SubagentResult` / `VerifierSubagentResult` dataclass/BaseModel; verifier returns JSON, general returns plain content.

---

## 3. Gap Matrix

Legend: Local = aligned / partial / missing / do-not-copy (UI-only or product-disaligned).
MVP-critical? reflects the roadmap's "H11 full agent-team lifecycle deferred, H12 minimal-only" boundary —
items only matter for MVP if they block a concrete H01-H11 behavior.

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| A1 | Agent tool + `subagent_type` catalog with `whenToUse` | partial (2 hard-coded types, no whenToUse surfaced to model) | **Y** — model cannot meaningfully pick between general and future agents without descriptions | **close in MVP**: add `whenToUse`/description to local agent catalog; separate "general" placeholder from real implementation |
| A2 | Per-agent tool pool resolution + disallow list | partial (hard-coded `CHILD_TOOL_OBJECTS` / `FORBIDDEN_CHILD_TOOLS`) | **Y** — future built-ins (plan, explore) will need different pools without refactor | **close in MVP**: introduce `AgentDefinition` schema with `tools`, `disallowed_tools`; derive allowlist from it |
| A3 | Per-agent permission mode override | missing | N — permission runtime H02 treats parent mode as authoritative; agent-level override is nice-to-have | defer with ADR — note when H17 plugin/H18 hooks may require |
| A4 | Frontmatter hooks scoped to agent lifecycle | missing | N for MVP — frontmatter loader not in MVP | defer |
| A5 | Skills preload per agent | missing | N — H15 baseline only | defer |
| A6 | Per-agent MCP additive | missing | N — H16 baseline only | defer |
| A7 | ClaudeMd/gitStatus strip for read-only agents | missing | N — optimization, not correctness | defer |
| A8 | model/effort/maxTurns per-agent | partial (maxTurns pinned to 1; no model override) | **Y** — verifier already needs its own model profile separate from parent; `max_turns=1` forbids multi-step verification | **close in MVP**: unpin max_turns; allow per-agent model override via AgentDefinition |
| A9 | Critical system reminder experimental | missing | N | do-not-copy for MVP |
| B1 | `createSubagentContext` isolated child | partial (verifier clones `RuntimeContext`, general path doesn't run a child at all) | **Y** — general subagent has no real runtime; this is the biggest correctness gap | **close in MVP**: land a real general-purpose child runtime via `create_agent`, mirroring verifier's invocation pattern |
| B2 | Async vs sync abort policy | missing (only sync, no AbortController analogue) | N for MVP — async/background deferred under H11 "full lifecycle deferred" | defer with ADR |
| B3 | Auto-deny permission prompts for async | n/a (no async) | N | defer (bundle with B2) |
| B4 | Per-spawn `allowedTools` replaces session rules | partial (hard-coded allowlist per agent_type) | **Y** — once A1/A2 land, we need the runtime path to honor declared allowlist at spawn | **close in MVP** alongside A2 |
| B5 | SubagentStart hooks additional context | missing | N for MVP — H18 baseline only | defer |
| B6 | `filterIncompleteToolCalls` on forked history | n/a (no context fork) | N | defer (with C1) |
| B7 | Side-chain transcript with parent-chain UUID | **missing** | **Y** — verifier evidence only records verdict, not the full child transcript; no way to audit what the subagent saw or did | **close in MVP**: persist subagent JSONL transcript with `parent_thread_id` / `parent_message_id` linkage (mirror `recordSidechainTranscript`) |
| B8 | Per-agent metadata on disk | missing | **Y** — prerequisite for B7 / any future resume | **close in MVP** with B7 |
| B9 | `transcriptSubdir` grouping | missing | N | defer |
| B10 | Perfetto trace | missing | N — observability polish | defer |
| B11 | Per-agent API dump | missing | N — debugging | defer |
| B12 | Finally-block cleanup inventory | partial (no cleanup hooks; verifier child is short-lived) | N for MVP — no leaking resources yet (no MCP, no hooks, no shell tasks) | defer; revisit when B2 lands |
| B13 | Kill shell tasks for agent | missing | N — no bash task integration in subagent path | defer |
| B14 | max_turns_reached clean break | missing (`max_turns=1` hard-pinned, no break semantics) | **Y** — bundled with A8 unpin | **close in MVP** with A8 |
| B15 | TTFT forwarding | missing | N — UX metric | defer |
| C1 | Implicit fork (no subagent_type, inherit parent context) | missing | N — fork is explicit H12 extension; roadmap says minimal only | defer with ADR (explicit cc highlight to not copy yet) |
| C2-C7 | All fork/cache machinery | missing | N — H12 minimal-only | defer |
| D1-D4 | Resume | missing | N for MVP — resume belongs to H06 surface and is closed for main session; subagent resume is extension | defer with ADR |
| E1 | Task state schema | partial (`SubagentResult` dataclass, no durable task record for subagent execution) | **Y (small)** — we already have a Task store (H09); subagent execution should produce a task-graph-backed record, not a bare dataclass | **close in MVP**: persist subagent invocation as a task record or durable `SubagentRun` for audit; link to verifier evidence |
| E2 | Foreground/background + signal | missing | N — async deferred | defer |
| E3 | `pendingMessages` drain | missing | N — SendMessage is H13 deferred | defer |
| E4 | UI-transcript append | do-not-copy (UI-only) | N | do-not-copy |
| E5 | `isPanelAgentTask` predicate | do-not-copy (UI-only) | N | do-not-copy |
| E6 | Parent-child abort cascade | missing | N — requires B2 | defer |
| E7 | Agent notification with XML payload + `notified` single-shot | partial (only evidence record, no task-notification envelope) | **Y (small)** — once A1/B7 land, a minimal completion envelope with token/tool-use/duration is cheap and gives model/hooks a canonical handoff structure | **close in MVP**: emit a structured `subagent_result` runtime event with token/toolUse/duration/plan_id even for general |
| E8 | Output symlink + eviction | missing | N — depends on async | defer |
| E9 | Progress tracker with usage + activities | missing | **Y (small)** — token count is a roadmap H20-minimal concern; at minimum record total_input/output tokens per subagent so compact/cost counters can see it | **close in MVP**: capture child usage in `SubagentResult` and propagate to evidence + runtime event |
| E10 | Cache eviction hint | missing | N — provider-specific (H20 deferred) | defer |
| E11 | Partial result on kill | missing | N — no kill path yet | defer |
| E12 | Retain/diskLoaded | do-not-copy (UI-only) | N | do-not-copy |
| F1-F3 | Background summarization | missing | N — requires async + coordinator; H14 deferred | defer |
| F4 | Strict result schema | partial (`SubagentResult` dataclass, `VerifierSubagentResult` BaseModel) | **Y (small)** — needs usage fields + agent_type + content block parity | **close in MVP** with E7/E9 |
| F5 | Fallback last-text scan | missing | **Y** — verifier current extraction requires non-empty assistant text; a final tool_use-only message would raise | **close in MVP**: mirror the fallback walk |
| G1 | Tiered catalog | **missing** — only 2 types, no feature flags, no `whenToUse` | **Y** — roadmap explicitly wants built-in agents (H11 "all subagents enter as tools") | **close in MVP**: introduce `BUILT_IN_AGENTS` list with general, verifier (+ planned explore/plan placeholders behind flags) |
| G2 | Coordinator swap | missing | N — H14 deferred | do-not-copy for MVP |
| G3 | SDK kill-switch | missing | N | defer |
| G4 | Source tier trust | missing | N — no plugin/policy settings yet | defer |
| H1 | Handoff classifier | missing | N — H19 partial, classifier is advanced | defer with ADR |

---

## 4. Candidate Discussion Order

Shortest dependency chain first. Each item builds on the previous.

1. **Real general-purpose child runtime (B1 + A1 surface)**
   Today `general` is a stub. Closing this replaces the largest correctness gap and makes H11 "all subagents enter as tools" true for the non-verifier case. Depends on nothing.
2. **Agent catalog + AgentDefinition schema (A1 + A2 + A8)**
   Introduce `AgentDefinition` (agent_type, description/whenToUse, tools allowlist, disallowed_tools, model?, max_turns?) and refactor the hard-coded verifier/general into registered definitions. Depends on (1). Blocks (3) and (4).
3. **Subagent transcript + metadata persistence (B7 + B8 + E1)**
   Persist child JSONL transcript and per-agent metadata record, linked to parent thread + parent message UUID. Closes the "no audit of what subagent saw/did" gap. Depends on (2).
4. **Structured subagent result envelope (F4 + E7 + E9 + F5)**
   Expand `SubagentResult` to carry `agent_type`, usage (input/output tokens, total duration), tool-use count; emit a canonical runtime event; add fallback last-text scan. Depends on (2), pairs with (3).
5. **Explicit ADR for deferred items (B2/B13, C1-C7, D1-D4, F1-F3, H1)**
   One document capturing what is intentionally not copied in MVP and why, with pointers back to cc source. Depends on (1)-(4) for context. Matches Stage 29 deferred-boundary ADR already on the roadmap.

---

## 5. Open Questions for Maintainer

Only blocking/preference items.

1. **Q — Scope of "real general-purpose child runtime"**: do we keep MVP general as a single read-only-tools agent (mirror verifier's allowlist minus plan/task reads) or extend it to include write tools (`write_file`, `edit_file`, `bash`) so it can execute, not only research? Roadmap text says "agent-as-tool" but doesn't pin the capability class.
2. **Q — Agent catalog minimum set**: for MVP, is `general + verifier` sufficient, or must we land `explore` and `plan` built-ins (cc-haha's `EXPLORE_AGENT`, `PLAN_AGENT`) before H11 can be called closed? Roadmap treats them as future; `generalPurposeAgent` is the only must-have in cc.
3. **Q — Transcript persistence boundary**: should subagent transcripts live in the same JSONL store as the parent session (sidechain with `parent_id` field), or in a separate per-agent directory keyed by agent_id? cc uses per-agent paths with metadata; our session store is already thread-keyed.
4. **Q — Result envelope model**: do we surface the full token/usage breakdown (cache creation/read separately) at this stage, or only total tokens? H20 is `implemented-minimal` — decoupling subagent usage from full cost instrumentation is possible but divergent from cc.
5. **Q — `max_turns` unpinning**: what is the MVP ceiling for general-purpose subagent turns? cc's general default is configurable per agent; our current pin of 1 blocks iterative subagent work entirely.

---

## Appendix: Items deliberately excluded from this research

- UI-only / React concerns (panel, pill, tooltip, color manager) → do-not-copy for Python mainline
- Analytics event names (`tengu_*`) → observability layer, H19 partial
- Perfetto and dump-prompts paths → debug polish, not MVP
- InProcessTeammateTask / RemoteAgentTask / DreamTask → H13/H21 deferred
- Coordinator mode full architecture → H14 deferred
