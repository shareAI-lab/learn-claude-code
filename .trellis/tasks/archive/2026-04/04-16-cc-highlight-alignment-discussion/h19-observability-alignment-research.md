# H19 Alignment Research (cc-haha vs coding-deepgent)

> Source-backed inventory of cc-haha observability surface, local implementation state,
> and gap matrix for the H19 "Observability and evidence ledger" row currently marked
> `implemented` on the MVP dashboard.
>
> cc-haha root: `/root/claude-code-haha/`
> local root: `coding-deepgent/src/coding_deepgent/`
> Reading cutoff: 2026-04-17

---

## 1. cc-haha Observability Highlight Inventory

### A. Structured analytics pipeline

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| A1 | `logEvent(name, metadata)` with queued-until-sink pattern | `services/analytics/index.ts:96-164` | Events buffered before `attachAnalyticsSink` drains asynchronously via microtask; idempotent attach | Analytics can't block startup; attach timing doesn't lose events |
| A2 | Typed marker `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` | `services/analytics/index.ts:19` | Every string field logged must cast through this `never` type; compiler forces author to verify no code/paths leak | Compile-time PII discipline rather than runtime review |
| A3 | `_PROTO_*` key scheme for PII-tagged fields | `services/analytics/index.ts:33-58` (`stripProtoFields`) | 1P exporter hoists `_PROTO_*` to proto columns with stricter ACL; Datadog fanout strips them first | Two-tier PII access without per-sink filter maintenance |
| A4 | Event sampling via GrowthBook dynamic config | `services/analytics/index.ts:132-144`, `growthbook.ts` | `tengu_event_sampling_config` controls sample rate; rate injected into metadata | Cost/volume control without code changes |
| A5 | Enriched environment metadata for ants | `services/internalLogging.ts:17-89` | Kubernetes namespace + OCI container ID auto-added for `USER_TYPE === 'ant'`; external users get no such enrichment | Internal deployment-aware analytics; no external fingerprinting |
| A6 | Async + sync `logEvent` / `logEventAsync` | `index.ts:133-164` | Async variant for fire-and-forget events that must await sink; sync for hot path | Backpressure handling optional per callsite |

### B. Query-loop event taxonomy

| # | Event name | Source `query.ts` line | What it captures |
|---|---|---|---|
| B1 | `tengu_query_before_attachments` / `_after_attachments` | 1539, 1652 | Entry/exit of attachment assembly with count deltas |
| B2 | `tengu_auto_compact_succeeded` | 478 | Auto-compact completion metrics |
| B3 | `tengu_post_autocompact_turn` | 1525 | First turn after auto-compact (measures recovery quality) |
| B4 | `tengu_orphaned_messages_tombstoned` | 719 | Count of orphan tool_use/tool_result pairs replaced with tombstones |
| B5 | `tengu_model_fallback_triggered` | 932 | Model downgrade event (e.g., Opus → Sonnet) |
| B6 | `tengu_query_error` | 959 | API/protocol errors from query loop |
| B7 | `tengu_max_tokens_escalate` | 1204 | Output budget escalation decisions |
| B8 | `tengu_token_budget_completed` | 1349 | Budget-complete breakdown per request |
| B9 | `tengu_streaming_tool_execution_used` / `_not_used` | 1367, 1373 | Streaming path gating decisions |
| B10 | `tengu_cache_eviction_hint` | `agentToolUtils.ts:337-345` (subagent end) | Tells inference when a subagent's cache chain can be evicted |

### C. Per-agent / per-session persistent artifacts

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| C1 | `getDumpPromptsPath(agentIdOrSession)` JSONL per session/agent | `services/api/dumpPrompts.ts:59-65` | Each API request appended; init state + fingerprint-based dedup avoid duplicating identical init payloads | Replayable API log per-session/per-agent without bloat |
| C2 | Cached last 5 API requests (ants only) | `dumpPrompts.ts:14-38` | In-memory circular buffer for `/issue` command | Ant support tools have recent context without session scan |
| C3 | Init fingerprint dedup | `dumpPrompts.ts:74+` | Hash model/tools/system to skip duplicate init dumps | Dump cost stays O(unique-init-shapes), not O(requests) |
| C4 | `recordSidechainTranscript(messages, agentId, parentUuid)` | `utils/sessionStorage.ts:1451` | Per-agent JSONL transcript with `lastRecordedUuid` parent chain; initial batch fire-and-forget | Full replayable agent transcript separate from analytics |
| C5 | `writeAgentMetadata` / `readAgentMetadata` | `utils/sessionStorage.ts:283-295` | Sidecar JSON for agentType/worktreePath/description | Resume routing without replaying spawn args |
| C6 | `getAgentTranscriptPath(agentId)` under session dir | `utils/sessionStorage.ts:247` | Subagent transcripts co-located with parent session on disk | Resume/recovery locality; one directory copy moves everything |

### D. Perfetto hierarchical tracing

| # | Highlight | Source `utils/telemetry/perfettoTracing.ts` | Function | Benefit |
|---|---|---|---|---|
| D1 | `registerAgent(agentId, agentType, parentId)` / `unregisterAgent` | L392, L416 | Agent tree registration with parent link | Visualize the subagent graph with parent chain |
| D2 | LLM request spans | L425-L499 | `startLLMRequestPerfettoSpan` / `endLLMRequestPerfettoSpan`, separates TTFT / completion / token counters | Per-request latency attribution at request granularity |
| D3 | Tool spans | L690-L727 | `startToolPerfettoSpan` / `endToolPerfettoSpan` around every tool call | Tool-level latency visibility |
| D4 | User-input spans | L768-L838 | Wraps each prompt submission; interaction span encloses the full loop | User-perceived latency measurement |
| D5 | Instants + counters | L840-L884 | `emitPerfettoInstant` / `emitPerfettoCounter` for token counters, snapshot points | Timeline annotations without span machinery |
| D6 | Stale-span eviction + max-event cap | L1083, L1113 | Protects long-running sessions from unbounded trace memory | Observability without memory leak |

### E. Debug logging and lifecycle reporting

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| E1 | `logForDebugging(msg, {level})` with structured levels | `utils/debug.ts` (used throughout) | Gated by dev/verbose flags; consistent `[Agent:…]` / `[AgentSummary]` prefixes | Uniform debug output without ad-hoc console.log |
| E2 | `emitTaskProgress` for SDK consumers | `utils/task/sdkProgress.ts` | Progress event stream to SDK clients: taskId, tokens, tool uses, summary, lastToolName | External UI can follow subagent progress |
| E3 | `pushApiMetricsEntry(ttftMs)` parent forwarding | `runAgent.ts:762-768` | Subagent's TTFT bubbles to parent's API metrics display | UX metrics unified across agent tree |
| E4 | `tengu_cache_eviction_hint` on subagent end | `agentToolUtils.ts:337-345` | Inference layer gets signal to evict child's cache chain | Cache efficiency for long-running sessions |

### F. Evidence / recovery surface (persistent ledger)

| # | Highlight | Source | Function | Benefit |
|---|---|---|---|---|
| F1 | Session JSONL with per-event timestamps | `sessionStorage.ts` | Single ordered log of messages, state snapshots, tool results | Deterministic recovery / forensics |
| F2 | `conversationRecovery.ts` | (file present) | Recovery brief assembly from JSONL | Resume UX |
| F3 | `toolResultStorage.ts` content replacement records | (file present) | Stable replacement state for large outputs across resumes | Cache-stable resume |

---

## 2. Local coding-deepgent Current State

### 2.1 Runtime event sink

`runtime/events.py` — `RuntimeEvent(kind, message, session_id, metadata, created_at)`;
protocols `RuntimeEventSink` + `NullEventSink` + `InMemoryEventSink`.

Every emitter writes through `context.event_sink.emit(event)` from `RuntimeContext`.
In-memory sink is the default wiring; CLI service can swap.

### 2.2 Session JSONL store

`sessions/store_jsonl.py:JsonlSessionStore` methods:

- `append_message`, `append_state_snapshot`, `append_evidence`, `append_compact`, `append_collapse`

`sessions/records.py` record types: `MESSAGE_RECORD_TYPE`, `TRANSCRIPT_EVENT_RECORD_TYPE`,
`STATE_SNAPSHOT_RECORD_TYPE`, `EVIDENCE_RECORD_TYPE`, plus `COMPACT_EVENT_KIND` and
`COLLAPSE_EVENT_KIND` for trigger labels.

`SessionEvidence(kind, summary, status, created_at, subject?, metadata?)` — status vocab
`recorded | completed | blocked | denied | passed | failed | partial`.

### 2.3 Runtime → Evidence bridge

`sessions/evidence_events.py:RUNTIME_EVIDENCE_KINDS` maps 8 runtime event kinds to
persistent evidence:

```
hook_blocked | permission_denied | snip | microcompact | context_collapse
| auto_compact | reactive_compact | subagent_spawn_guard
```

Plus `verification` evidence emitted from `subagents/tools.py:record_verifier_evidence`.

Metadata is whitelisted to a fixed key set; unknown keys are dropped.

### 2.4 Recovery brief

`sessions/resume.py:build_recovery_brief` produces a `RecoveryBrief` with:
- session_id, updated_at, message_count
- active_todos (pending / in_progress) from state
- contribution_sections (pluggable `RECOVERY_BRIEF_CONTRIBUTIONS`)
- recent_evidence (last 5) + recent_compacts (last 3)

`render_recovery_brief` formats to text; `build_resume_context_message` wraps it into
a `role:system` message for resume injection with `RESUME_CONTEXT_MESSAGE_PREFIX`.

### 2.5 Not present locally

- No analytics backend (no Datadog / no first-party event logging / no GrowthBook sampling)
- No typed-marker PII discipline on event metadata
- No Perfetto tracing (no agent hierarchy spans, no LLM/tool spans, no TTFT counters)
- No per-request API dump (`getDumpPromptsPath` equivalent)
- No query-level events (B1-B9 taxonomy)
- No per-agent transcript / metadata sidecar (subagent transcripts currently: only verifier verdict → evidence)
- No cache eviction hint
- No SDK progress stream
- No debug-level structured logger beyond Python `logging` (grep shows no `logForDebugging` equivalent)

---

## 3. Gap Matrix

Legend: **Local** = aligned / partial / missing / do-not-copy (internal-ant-only or
provider-specific). **MVP-critical?** reflects whether the item blocks a concrete H01-H11
behavior or safety gate. Roadmap says H19 is `implemented` — these gaps indicate whether
that label is defensible or overstated.

### 3.1 Analytics pipeline (A)

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| A1 | Queued-until-sink pattern | missing | **Y (architectural)** — `RuntimeEventSink` currently emits-immediately; no buffering. Means events emitted before CLI wires the sink are silently dropped. | **close in MVP**: add a `QueuedEventSink` default that replays on attach (mirror cc's microtask drain) |
| A2 | Typed PII-safety marker | missing | N — no external analytics backend to leak to | defer |
| A3 | `_PROTO_*` PII-tagged keys | missing | N | defer (follows A2) |
| A4 | Event sampling | missing | N — provider-specific | defer |
| A5 | Environment enrichment | missing | N — we're not an internal telemetry service | do-not-copy |
| A6 | Sync vs async emit | partial (all emit is sync; no async variant) | N — in-process sink is already sync-fast | defer; revisit if an external sink is ever added |

### 3.2 Query-loop taxonomy (B)

| # | Event | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| B1 | Attachment boundaries | missing | N — we don't have an attachments layer equivalent | defer with ADR |
| B2 | auto_compact_succeeded | **partial** — `auto_compact` kind exists as RuntimeEvent → evidence (completed) | **Y (semantic)** — we record the attempt but not success/metrics separately | **close in MVP**: split "attempted" vs "succeeded" statuses; include hidden_message_count / token_savings metadata |
| B3 | post_autocompact_turn | missing | **Y (correctness signal)** — this is the canary for "did auto-compact destroy context?"; without it we have no way to audit compact quality | **close in MVP**: emit a runtime event on the first turn after any compact/collapse with token-count before/after |
| B4 | orphaned_messages_tombstoned | missing | **Y (invariant)** — projection pipeline already has this notion; need the event when it fires | **close in MVP**: emit `orphan_tombstoned` runtime event with count + reason |
| B5 | model_fallback_triggered | missing | N for MVP — no model-fallback logic in mainline yet | defer |
| B6 | query_error | **partial** — Python exceptions log through `logging` but there's no structured runtime event | **Y (ops)** — without a structured error event, post-mortem depends on stderr capture | **close in MVP**: emit `query_error` runtime event with error class + phase + retry count |
| B7 | max_tokens_escalate | missing | N — no output budget escalation yet | defer |
| B8 | token_budget_completed | missing | **Y (small)** — compact/pressure decisions already compute token counts; publishing them as a runtime event costs nothing | **close in MVP**: emit per-response `token_budget` event |
| B9 | streaming_tool_execution | n/a | N — Streaming stage explicitly deferred by user | do-not-copy for MVP |
| B10 | cache_eviction_hint | missing | N — provider-specific | defer |

### 3.3 Persistent artifacts (C)

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| C1 | API request dump (`dumpPrompts`) | missing | **Y (debuggability)** — without API dump, debugging "what did we send the model" depends on provider logs which are often rate-limited or lag | **close in MVP**: optional dev-mode API dump per session (env-gated); fingerprint dedup copy-worthy |
| C2 | Last-N cache for ant support | missing | N — ant-specific UX | do-not-copy |
| C3 | Init fingerprint dedup | dependent on C1 | N until C1 lands | tie to C1 |
| C4 | Sidechain transcript with parent-chain UUID | missing for subagent (**already flagged in H11/H12 as close-in-MVP B7**) | **Y** — redundant with H11/H12 decision; reiterate here | already decided: close in MVP with subagent sidechain PR |
| C5 | Agent metadata sidecar | missing (**already H11/H12 B8 close-in-MVP**) | **Y** | already decided |
| C6 | Per-agent transcript under session dir | partially in the H11/H12 decision (sidechain in parent JSONL with fields, not per-agent files) | N — intentional divergence | do-not-copy; documented in H11/H12 PRD |

### 3.4 Perfetto / hierarchical tracing (D)

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| D1 | Agent-tree registration | missing | N — H11/H12 sidechain already gives parent→child lineage via parent_message_id | defer with ADR |
| D2-D6 | LLM / tool / user spans, instants, counters | missing | N — observability polish, not correctness | defer with ADR: "latency tracing is a post-MVP concern; RuntimeEvent timestamps are sufficient for MVP debugging" |

### 3.5 Debug logging + SDK progress (E)

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| E1 | Structured debug logger | partial (Python `logging`, no consistent prefix or level gating per-agent) | **Y (small)** — add a tiny `logger_for(agent_name)` helper that adds agent context automatically; copy-cheap | **close in MVP**: convention + helper |
| E2 | SDK progress stream | missing | N — no external SDK consumer yet | defer with ADR |
| E3 | Parent TTFT forwarding | missing | N — no TTFT capture at all | defer (bundle with D2) |
| E4 | cache_eviction_hint | missing | N | defer (B10) |

### 3.6 Evidence / recovery surface (F)

| # | Highlight | Local | MVP-critical? | Suggested action |
|---|---|---|---|---|
| F1 | Session JSONL ordered log | **aligned** (`JsonlSessionStore` with 5 append methods + record types) | — | no action |
| F2 | Recovery brief assembly | **aligned or better** — local has pluggable `contribution_sections` which cc doesn't; active-todos + recent-evidence + recent-compacts covered | — | no action |
| F3 | Content replacement records | missing (no equivalent of `toolResultStorage` cache-stable replacement) | **Y (for H05 consumer)** — already mentioned in compression staged plan | already scoped by `tool-result-storage-contracts.md`, track under H05 staged sub-tasks not H19 |

---

## 4. H19 Closeout Verdict

**H19 dashboard status should be downgraded from `implemented` to `implemented-minimal`**
with an explicit MVP closeout stage containing the items marked "close in MVP" in §3:

Required for defensible `implemented`:

1. **A1** Queued-until-sink event sink (drop-proof emission during startup)
2. **B2** Split `auto_compact` into attempted + succeeded with metrics
3. **B3** `post_autocompact_turn` recovery canary
4. **B4** `orphan_tombstoned` event
5. **B6** Structured `query_error` runtime event
6. **B8** `token_budget` per-response event
7. **C1** Optional dev-mode API dump (env-gated)
8. **E1** Agent-scoped structured debug logger helper

Items explicitly deferred with ADR (not gating H19 closeout):

- A2-A6 analytics backend parity (no external backend in MVP)
- B1, B5, B7, B9, B10 query events not backed by local features yet
- C2, C5 ant-specific / SDK-specific conveniences
- D1-D6 Perfetto latency tracing
- E2, E3 SDK/TTFT features

Items already scoped elsewhere (not re-tracked):

- C4, C5 covered by H11/H12 sub-task B
- F3 covered by tool-result-storage-contracts

---

## 5. Candidate Discussion Order

Shortest dependency chain first.

1. **Queued-until-sink + agent-scoped logger (A1 + E1)** — foundational wrapper, no new schemas, 1 small PR.
2. **Compact-quality runtime events (B2 + B3 + B4)** — all fire from the compact pipeline; PR touches `compact/` and `evidence_events.py` in one place.
3. **Structured query_error + token_budget (B6 + B8)** — runtime-level events fired from the agent loop wrapper; requires light wiring in `agent_runtime_service.py`.
4. **Dev-mode API dump (C1)** — env-gated, no impact on production path; can land last or be shelved if H01 tool-module alignment plan already covers it.
5. **Explicit deferral ADR** — one page capturing D1-D6, A2-A6, E2-E3 with cc source references.

---

## 6. Open Questions for Maintainer

Only blocking/preference items.

1. **Q — A1 queued-sink default**: should the default `RuntimeEventSink` become buffered-then-drain, or should CLI always construct a concrete sink before any runtime emits? cc's choice is buffer-by-default with microtask drain; ours could be "fail loudly if no sink" which forces explicit wiring.
2. **Q — B3 recovery canary metric**: for the "first turn after compact" event, which token counts matter most — pre-compact total / post-compact total / new-turn input / new-turn output, or all four? cc logs all four.
3. **Q — C1 API dump gating**: env variable opt-in (`CODING_DEEPGENT_DUMP_PROMPTS=1`) only, or also a CLI flag? cc has both; a dev-only env is cheapest.
4. **Q — MVP closeout stage name**: land these under an existing Stage 28 closeout slot (where H19/H20 minimal is noted), or a dedicated stage 30+ row? Affects only planning, not code.
5. **Q — B8 token_budget scope**: record it per-response (every assistant turn) or only at compact-decision boundaries? Every-turn is cheap and matches cc; per-boundary is leaner but loses trend data.

---

## Appendix: Items deliberately excluded

- UI Teleport/ink rendering → do-not-copy (Python mainline has no TUI)
- Agent ID generator details → internal implementation
- First-party event-logging exporter / BQ proto hoisting → internal infra
- LSPDiagnosticRegistry passive feedback → LSP integration not in MVP
- Prompt-cache-break detection → provider-specific observability
