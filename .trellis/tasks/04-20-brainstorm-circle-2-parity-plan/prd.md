# brainstorm: Circle 2 parity execution plan

## Goal

制定 `coding-deepgent` 的 `Circle 2` 专项执行计划，承接已完成的 Circle 1 local daily-driver parity baseline，明确 expanded product parity 的 waves、domain boundaries、source evidence、OSS fallback 触发点、验收方式和明确 out-of-scope。

## What I already know

* Circle 1 baseline 已完成并验证，包含 runtime core、CLI/TUI visibility/control、local extension inspect/debug surfaces、acceptance harness。
* Circle 2 不是继续补 CLI 小功能，而会引入 mailbox/coordinator/remote/IDE/daemon/extension lifecycle/cross-day continuity 等新架构边界。
* 现有 roadmap 已把 Circle 2 定位为 expanded product parity。
* 用户要求规划要对照 Claude Code / `cc-haha`，缺源码时先搜索高质量类似 OSS。
* `cc-haha` 有 worker lifecycle / session ingress / task events / mailbox / coordinator / daemon / cron / plugin lifecycle / session memory 的源码线索。
* OpenHands、opencode、goose 的公开源码/文档支持把 Circle 2 规划成 runtime substrate、client/server/control plane、extension lifecycle、memory/continuity 的架构序列。

## Assumptions (temporary)

* 本次 brainstorm 只制定 Circle 2 专项计划，不直接实现。
* Circle 2 需要拆成多个执行 wave，每个 wave 可独立 task 化、验证、归档。
* Circle 2 仍以本地产品价值为主，不做无价值的 closed-source 外观复制。

## Open Questions

* none

## Requirements (evolving)

* 明确 Circle 2 included / excluded boundaries。
* 每个 wave 必须说明 user/runtime effect、source evidence、domain ownership、acceptance criteria。
* 标记哪些能力需要 OSS fallback research。
* 避免污染现有 `sessions/`, `subagents/`, `runtime/`, `tool_system/` 边界。
* 明确 Circle 2 需要新增哪些 domain，例如 `mailbox`, `teams`, `daemon`, `remote`, `extension_lifecycle`。
* 明确哪些当前 Circle 1 能力只能作为 substrate，不能继续直接扩张，例如 active TUI background subagent control 不能假装是 daemon。

## Acceptance Criteria (evolving)

* [ ] Circle 2 plan defines waves and sequencing.
* [ ] Plan includes source evidence and missing-source fallback rules.
* [ ] Plan defines new domain boundaries.
* [ ] Plan defines Circle 2 acceptance harness.
* [ ] Plan states out-of-scope / deferred items.
* [ ] Plan asks maintainer to pick one sequencing strategy before implementation.

## Definition of Done (team quality bar)

* Trellis plan created/updated.
* PRD records final decisions.
* Source/OSS research notes captured where needed.
* No code implementation begins until plan is approved.

## Out of Scope (explicit)

* Implementing Circle 2 runtime code in this brainstorm task.
* Reopening Circle 1 unless planning finds a hard dependency.
* Marketplace distribution or remote SaaS backend implementation details unless needed for sequencing.

## Technical Notes

* Initial source of truth: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Resume status: `.trellis/project-handoff.md`
* Prior Circle 1 completion commits: `7248889`, `386602b`, `f073945`

## Auto-Context Findings

### Local `coding-deepgent` constraints

* Circle 1 added local file-backed `runtime.store`, session JSONL ledger, recovery/evidence/compact/collapse views, active TUI bridge controls, and extension inspect/debug surfaces.
* Current background subagent worker handles are process-local. Cross-process lifecycle requires a new daemon/worker substrate, not more CLI commands over the current manager.
* Current `subagents` domain supports bounded child/fork execution and background records, but not mailbox, coordinator, worker addressing, team routing, or durable delivery.
* Current `sessions` domain owns transcript/evidence/resume; it should not become a generic team/orchestration database.
* Current `plugins` and `mcp` are local inspect/debug seams; install/enable/update/trust lifecycle is intentionally outside Circle 1.

### `cc-haha` source notes

* Worker/session ingress:
  * `/root/claude-code-haha/src/cli/transports/ccrClient.ts`
  * worker lifecycle protocol, `PUT /worker`, heartbeat, event upload, internal events, restore after worker restart.
* Task lifecycle / stop control:
  * `/root/claude-code-haha/src/cli/print.ts`
  * `task_started`, `task_progress`, `task_notification`, `session_state_changed`, `stop_task`.
  * `/root/claude-code-haha/src/entrypoints/sdk/controlSchemas.ts`
  * explicit `stop_task` control schema.
* Mailbox / swarm permission:
  * `/root/claude-code-haha/src/context/mailbox.tsx`
  * `/root/claude-code-haha/src/hooks/useInboxPoller.ts`
  * `/root/claude-code-haha/src/hooks/useSwarmPermissionPoller.ts`
  * worker/leader permission messages and inbox polling.
* Coordinator:
  * `/root/claude-code-haha/src/cli/print.ts`
  * `coordinatorModeModule`, coordinator resume matching, worker-related status.
  * `/root/claude-code-haha/src/components/PromptInput/*`
  * coordinator task UI selection.
* Remote / IDE control:
  * `/root/claude-code-haha/src/cli/transports/SSETransport.ts`
  * `/root/claude-code-haha/src/cli/transports/WebSocketTransport.ts`
  * `/root/claude-code-haha/src/remote/*`
  * `/root/claude-code-haha/src/services/mcp/vscodeSdkMcp.ts`
* Daemon / cron / proactive:
  * `/root/claude-code-haha/src/entrypoints/cli.tsx`
  * `--daemon-worker`
  * `/root/claude-code-haha/src/cli/print.ts`
  * cron scheduler and proactive tick references.
  * `/root/claude-code-haha/src/skills/bundled/loop.ts`
  * `/root/claude-code-haha/src/skills/bundled/scheduleRemoteAgents.ts`
* Extension lifecycle:
  * `/root/claude-code-haha/src/services/plugins/pluginOperations.ts`
  * `/root/claude-code-haha/src/services/plugins/PluginInstallationManager.ts`
  * `/root/claude-code-haha/src/services/mcp/config.ts`
  * plugin MCP loading, dedup, enabled/disabled config, marketplace/policy gates.
* Session/cross-day memory:
  * `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  * `/root/claude-code-haha/src/services/extractMemories/extractMemories.ts`
  * `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`

## Research Notes

### What similar tools do

* OpenHands uses a sandbox/runtime client-server architecture with clear runtime interfaces, action execution server, event stream, and multiple runtime implementations including Docker/local/remote. Relevant sources: OpenHands runtime docs and `openhands/runtime/README.md`.
* opencode advertises provider-agnostic TUI and client/server architecture, where TUI is only one possible client.
* goose is a local desktop/CLI/API agent and treats extensions as MCP-based with install/enable/disable and access-control concepts.

### Constraints from our repo/project

* LangChain/LangGraph-native runtime should remain the hidden implementation default.
* Existing `runtime.store` can support durable records, but not durable process worker handles.
* Team/multi-agent runtime must not be added by overloading `run_subagent`, `sessions`, or `task` records.
* Remote/IDE surfaces must be separate from CLI/TUI JSONL bridge.

### Feasible approaches here

**Approach A: Substrate-first Circle 2** (Recommended)

* How it works:
  * Wave 1 daemon/worker/session-event substrate.
  * Wave 2 mailbox/send-message over durable substrate.
  * Wave 3 coordinator/worker team runtime.
  * Wave 4 remote/IDE control plane.
  * Wave 5 extension lifecycle.
  * Wave 6 cross-day continuity/memory.
* Pros:
  * Avoids fake mailbox/team features over process-local handles.
  * Aligns with `cc-haha` worker/session ingress evidence and OpenHands/opencode client/server patterns.
  * Gives later coordinator/remote work a real lifecycle foundation.
* Cons:
  * First wave is infrastructure-heavy and user-visible payoff is delayed.

**Approach B: User-visible team first**

* How it works:
  * Build mailbox/coordinator user flows first using current file store and active process.
  * Add daemon/remote later.
* Pros:
  * Faster visible parity with Agent/teams concepts.
  * Good for demos.
* Cons:
  * High risk of repeating the Circle 1 background-subagent problem: process-local behavior masquerading as durable team runtime.
  * Likely refactor later.

**Approach C: Remote/IDE first**

* How it works:
  * Turn existing frontend SSE/gateway into a remote control plane first.
  * Then add worker/session ingress and coordinator.
* Pros:
  * UI/control-plane progress is visible quickly.
  * Aligns with opencode multi-client and OpenHands client/server directions.
* Cons:
  * Remote UI without daemon/worker substrate can become thin transport over weak lifecycle.
  * Coordinator/mailbox still need later architectural work.

## Expansion Sweep

### Future evolution

* Circle 2 likely becomes the boundary where `coding-deepgent` needs durable process orchestration, not only in-memory background threads.
* Remote/IDE/daemon work should preserve a future API surface, not hard-code one CLI/TUI implementation.

### Related scenarios

* Permission prompts from workers must route to a leader/human without bypassing current permission policy.
* Task/progress events should reuse session evidence/event stream concepts but not pollute transcript messages.

### Failure and edge cases

* Worker crash/restart, duplicate delivery, stale run ownership, stop/cancel races.
* Message delivery idempotency, permission response timeout, remote reconnect/replay.
* Extension install/enable trust and rollback.

## Preliminary Recommendation

Use Approach A: substrate-first. Circle 2 should start with a durable daemon/worker/session-event substrate, then mailbox, then coordinator/team runtime, then remote/IDE, then extension lifecycle, then cross-day memory.

## Decision (ADR-lite)

**Context**: Circle 2 introduces durable background lifecycle, mailbox, coordinator/team runtime, remote/IDE control, extension lifecycle, and cross-day continuity. These features cannot safely be modeled as more fields on current process-local subagent/background APIs.

**Decision**: Use Approach A, substrate-first. Build durable daemon/worker/session-event substrate before mailbox/coordinator/remote features.

**Consequences**:

* First Circle 2 implementation wave will be infrastructure-heavy.
* Later mailbox/coordinator/remote/IDE features can build on real lifecycle semantics instead of fake process-local handles.
* Current Circle 1 active-TUI background controls remain valid as local process features, but not as durable team runtime.

## Final Requirements

* Create a Circle 2 execution plan that starts with daemon/worker/session-event substrate.
* Split Circle 2 into ordered waves with clear scope, domain ownership, and acceptance criteria.
* Include source evidence and OSS fallback notes for each wave.
* Explicitly prevent boundary pollution in `sessions`, `subagents`, `runtime`, and `tool_system`.
* Define Circle 2 acceptance harness before implementation begins.

## Final Acceptance Criteria

* [x] Circle 2 plan defines waves and sequencing.
* [x] Plan includes source evidence and missing-source fallback rules.
* [x] Plan defines new domain boundaries.
* [x] Plan defines Circle 2 acceptance harness.
* [x] Plan states out-of-scope / deferred items.
* [x] Plan asks maintainer to pick one sequencing strategy before implementation.

## Output

* `.trellis/plans/coding-deepgent-circle-2-expanded-parity-plan.md`
