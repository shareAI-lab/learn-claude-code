# coding-deepgent Circle 2 Expanded Product Parity Plan

Status: implemented local baseline
Updated: 2026-04-20
Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
Planning task: `.trellis/tasks/04-20-brainstorm-circle-2-parity-plan/`
Strategy: substrate-first

## Implemented Local Baseline

Implemented: 2026-04-20

Local expanded parity baseline is implemented for all Circle 2 waves using the
workspace-local durable `runtime.store` substrate. This baseline intentionally
does not claim hosted SaaS session ingress, multi-user auth, public marketplace
backend, or cross-machine workers.

Implemented modules:

* `event_stream`
* `worker_runtime`
* `mailbox`
* `teams`
* `remote`
* `extension_lifecycle`
* `continuity`

Implemented CLI surfaces:

* `coding-deepgent events ...`
* `coding-deepgent workers ...`
* `coding-deepgent mailbox ...`
* `coding-deepgent teams ...`
* `coding-deepgent remote ...`
* `coding-deepgent extension-lifecycle ...`
* `coding-deepgent continuity ...`
* `coding-deepgent acceptance circle2`

## Purpose

Circle 2 begins after the Circle 1 local daily-driver parity baseline.

Circle 1 intentionally avoided mailbox, coordinator/team runtime, durable daemon,
remote/IDE control plane, full extension lifecycle, and richer cross-day memory.
Circle 2 is where those expanded product-parity capabilities can be planned and
implemented without overloading the Circle 1 `subagents`, `sessions`, or
frontend bridge seams.

## Strategy Decision

Use a substrate-first sequence.

Rationale:

* current Circle 1 background subagent controls are active-process features, not
  durable workers
* mailbox and coordinator semantics need real delivery/lifecycle state
* remote/IDE surfaces need replayable event/control infrastructure
* daemon/worker substrate reduces the chance of faking durable behavior with
  process-local handles

## Evidence Ladder

Use the global evidence order from
`.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`:

1. real Claude Code public behavior
2. `cc-haha` source-backed implementation reference
3. high-quality analogous OSS
4. secondary analysis

For Circle 2, `cc-haha` evidence is sufficient to justify the major feature
families, but OSS fallback is still useful for implementation details around
runtime server boundaries, extension lifecycle, and sandbox/remote control.

## Source Evidence

### `cc-haha`

Worker / session ingress:

* `/root/claude-code-haha/src/cli/transports/ccrClient.ts`
  * worker lifecycle protocol
  * `PUT /worker`
  * worker heartbeat
  * visible client events
  * internal worker events for resume
  * worker state restore after restart
* `/root/claude-code-haha/src/cli/transports/SSETransport.ts`
* `/root/claude-code-haha/src/cli/transports/WebSocketTransport.ts`

Task lifecycle and control:

* `/root/claude-code-haha/src/cli/print.ts`
  * `task_started`
  * `task_progress`
  * `task_notification`
  * `session_state_changed`
  * `stop_task`
* `/root/claude-code-haha/src/entrypoints/sdk/controlSchemas.ts`

Mailbox / permission routing:

* `/root/claude-code-haha/src/context/mailbox.tsx`
* `/root/claude-code-haha/src/hooks/useInboxPoller.ts`
* `/root/claude-code-haha/src/hooks/useSwarmPermissionPoller.ts`
* `/root/claude-code-haha/src/hooks/toolPermission/handlers/swarmWorkerHandler.ts`

Coordinator / workers:

* `/root/claude-code-haha/src/cli/print.ts`
  * coordinator mode references and resume-mode matching
* `/root/claude-code-haha/src/components/PromptInput/*`
  * coordinator task selection/UI state
* `/root/claude-code-haha/src/state/AppStateStore.ts`
  * coordinator task index/count and worker permission state

Remote / IDE:

* `/root/claude-code-haha/src/remote/*`
* `/root/claude-code-haha/src/services/mcp/vscodeSdkMcp.ts`
* `/root/claude-code-haha/src/services/mcp/client.ts`
  * IDE-specific MCP server/tool handling

Daemon / cron / proactive:

* `/root/claude-code-haha/src/entrypoints/cli.tsx`
  * `--daemon-worker`
* `/root/claude-code-haha/src/cli/print.ts`
  * cron scheduler and proactive tick references
* `/root/claude-code-haha/src/skills/bundled/loop.ts`
* `/root/claude-code-haha/src/skills/bundled/scheduleRemoteAgents.ts`

Plugin / extension lifecycle:

* `/root/claude-code-haha/src/services/plugins/pluginOperations.ts`
* `/root/claude-code-haha/src/services/plugins/PluginInstallationManager.ts`
* `/root/claude-code-haha/src/services/mcp/config.ts`
  * plugin MCP loading, dedup, enabled/disabled config, marketplace/policy gates

Session / cross-day memory:

* `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
* `/root/claude-code-haha/src/services/extractMemories/extractMemories.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`

### Analogous OSS

OpenHands:

* Runtime docs describe a client-server runtime using Docker containers.
* Runtime README describes a `Runtime` interface, action execution client/server,
  multiple implementations including local, Docker, and remote, and plugin
  management.
* Reusable essence: isolate runtime lifecycle and action execution behind a
  formal runtime/control interface.

opencode:

* README describes provider-agnostic terminal coding agent with a TUI focus and
  client/server architecture where the TUI is only one possible client.
* Reusable essence: separate frontend clients from the backend agent/runtime
  server.

goose:

* README describes desktop app, CLI, and API surfaces over one local agent.
* Extension docs describe MCP-based extensions, enable/disable UX, extension
  management, malware checks, access controls, and extension directory.
* Reusable essence: extension lifecycle is a first-class product domain, not
  just schema validation.

## New Domain Boundaries

Circle 2 should introduce new domains instead of stretching Circle 1 modules:

* `daemon/`
  * process lifecycle
  * worker registry
  * heartbeats
  * durable run ownership
  * restart/recovery
* `worker_runtime/`
  * worker execution state
  * queued/running/cancelled/completed lifecycle
  * run logs/events
  * stop/cancel semantics
* `events/` or `event_stream/`
  * replayable user-visible events
  * internal worker events
  * delivery sequence/ack model
  * remote/TUI/CLI consumers
* `mailbox/`
  * addressable messages
  * inbox/outbox
  * send/receive/ack
  * permission response routing
* `teams/` or `orchestration/`
  * coordinator
  * worker roles
  * task assignment
  * progress synthesis
  * concurrency/write-scope rules
* `remote/`
  * remote session API
  * SSE/WebSocket gateway
  * control messages
  * replay/reconnect
* `extension_lifecycle/`
  * install/enable/disable/update
  * trust/source metadata
  * rollback
  * managed policy gates
* `continuity/` or extended `memory/`
  * cross-day session memory extraction
  * richer agent-private memory
  * long-session/cross-restart continuity policy

Do not hide these inside:

* `sessions/`
* `subagents/tools.py`
* `tool_system/`
* `frontend/producer.py`

## Circle 2 Waves

### Wave 1: Durable Daemon / Worker / Event Substrate

Goal:

* establish real durable lifecycle semantics before mailbox/coordinator/remote
  features are built

Primary modules:

* `daemon`
* `worker_runtime`
* `event_stream`
* `runtime`
* `sessions`

Planned features:

* local daemon command group
* worker registry
* durable worker records
* heartbeat and stale-worker detection
* restart-safe run ownership
* event stream with visible and internal events
* stop/cancel request model
* replayable event sequence numbers

Acceptance:

* a background run can survive parent CLI exit as durable state
* worker heartbeat/state can be inspected
* stop/cancel is persisted and eventually observed
* visible and internal events can be replayed in order

Out of scope:

* coordinator decisions
* mailbox message routing
* remote/IDE network API

### Wave 2: Mailbox / SendMessage Substrate

Goal:

* add addressable message delivery for agents/workers/human permission flows

Primary modules:

* `mailbox`
* `worker_runtime`
* `permissions`
* `event_stream`

Planned features:

* mailbox message schema
* inbox/outbox
* delivery status and ack
* idempotent send
* `SendMessage`-equivalent local tool
* permission request/response messages
* CLI/TUI mailbox inspection

Acceptance:

* worker can send message to parent/coordinator
* parent can reply
* permission request can route through mailbox without bypassing policy
* duplicate delivery is harmless

Out of scope:

* autonomous coordinator planning
* remote transport

### Wave 3: Coordinator / Worker Team Runtime

Goal:

* add local team runtime with coordinator and bounded workers

Primary modules:

* `teams` or `orchestration`
* `mailbox`
* `worker_runtime`
* `tasks`
* `subagents`
* `permissions`

Planned features:

* coordinator role
* worker role
* team task graph
* worker assignment
* progress synthesis
* worker stop/cancel
* write-scope/concurrency policy
* verifier/acceptance integration

Acceptance:

* coordinator can decompose a complex task into worker jobs
* workers report progress and results through mailbox/events
* coordinator can synthesize final status
* conflicting write scopes are blocked or serialized

Out of scope:

* remote/cloud workers
* cross-machine team runtime

### Wave 4: Remote / IDE Control Plane

Goal:

* make CLI/TUI only one consumer of a broader control plane

Primary modules:

* `remote`
* `event_stream`
* `daemon`
* `frontend`
* `mcp`

Planned features:

* local HTTP/SSE or WebSocket gateway
* replayable session event stream
* control messages
* remote permission bridge
* IDE MCP/control hooks
* reconnect/replay

Acceptance:

* a non-TUI client can observe session events
* a non-TUI client can issue bounded control messages
* reconnect receives missed events
* permission prompts remain policy-governed

Out of scope:

* hosted SaaS session ingress
* multi-user auth

### Wave 5: Extension Lifecycle

Goal:

* move beyond inspect/debug into install/enable/disable/update lifecycle

Primary modules:

* `extension_lifecycle`
* `plugins`
* `mcp`
* `skills`
* `hooks`
* `permissions`

Planned features:

* local install source registry
* enable/disable state
* update metadata
* trust/source policy
* rollback
* MCP/plugin dedup
* managed policy gates
* CLI/TUI extension manager surfaces

Acceptance:

* user can install/enable/disable/update a local extension
* invalid/untrusted extension is blocked with clear reason
* MCP/plugin duplicates are detected deterministically
* rollback restores prior state

Out of scope:

* public marketplace backend
* paid/hosted distribution

### Wave 6: Cross-Day Continuity And Richer Memory

Goal:

* strengthen continuity beyond a single-day Circle 1 session

Primary modules:

* `memory`
* `continuity`
* `sessions`
* `compact`
* `daemon`

Planned features:

* richer session-memory extraction
* cross-day memory artifacts
* agent-private memory lifecycle
* memory quality review
* session-memory compact integration
* away/resume summary
* workspace migration/export/import

Acceptance:

* long-running work can resume across process restarts and days
* current task, decisions, blockers, and next steps survive
* stale memory is detected and refreshed
* memory extraction remains bounded and auditable

Out of scope:

* organization/team memory sync unless explicitly scoped later

### Circle 2 Final: Expanded Parity Acceptance Harness

Acceptance workflows:

* Workflow D: Durable background lifecycle
  * start work
  * parent exits
  * worker state/events survive
  * control plane can inspect/stop/resume
* Workflow E: Local team execution
  * coordinator decomposes
  * workers execute bounded tasks
  * mailbox/progress/result synthesis works
* Workflow F: Remote/IDE control
  * secondary client observes and controls a live session
  * reconnect/replay is correct
* Workflow G: Extension lifecycle
  * install/enable/disable/update/rollback local extension
* Workflow H: Cross-day continuity
  * resume next day with session memory and evidence intact

## Risks

* Building coordinator before daemon will likely create process-local fake
  durability.
* Adding mailbox into `subagents` will make team routing hard to reason about.
* Adding remote/IDE to frontend JSONL bridge will blur local transport with
  control-plane API.
* Extension lifecycle without trust/source policy can create unsafe defaults.

## Out Of Scope For Circle 2 Unless Reopened

* hosted SaaS control plane
* multi-user auth/billing
* public marketplace backend
* enterprise managed settings sync
* full organization/team memory sync

## First Implementation Task

Create:

`.trellis/tasks/<date>-circle-2-wave-1-daemon-worker-event-substrate/`

Goal:

* implement the durable local daemon/worker/event substrate only

Must state before coding:

* durable worker record schema
* event stream schema
* stop/cancel semantics
* heartbeat/stale policy
* recovery/replay behavior
* which existing Circle 1 background controls are migrated or left process-local
