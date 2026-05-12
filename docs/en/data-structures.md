# Core Data Structures

> **Reference** -- Use this when you lose track of where state lives. Each record has one clear job.

The easiest way to get lost in an agent system is not feature count -- it is losing track of where the state actually lives. This document collects the core records that appear again and again across the mainline and bridge docs so you always have one place to look them up.

## Recommended Reading Together

- [`glossary.md`](./glossary.md) for term meanings
- [`entity-map.md`](./entity-map.md) for layer boundaries
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) for task vs runtime-slot separation
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) for MCP beyond tools

## Two Principles To Keep In Mind

### Principle 1: separate content state from process-control state

- `messages`, `tool_result`, and memory text are content state
- `turn_count`, `transition`, and retry flags are process-control state

### Principle 2: separate durable state from runtime-only state

- tasks, memory, and schedules are usually durable
- runtime slots, permission decisions, and live MCP connections are usually runtime state

## Query And Conversation State

### `Message`

Stores conversation and tool round-trip history.

### `NormalizedMessage`

Stable message shape ready for the model API.

### `QueryParams`

External input used to start one query process.

### `QueryState`

Mutable state that changes across turns.

### `TransitionReason`

Explains why the next turn exists.

### `CompactSummary`

Compressed carry-forward summary when old context leaves the hot window.

## Prompt And Input State

### `SystemPromptBlock`

One stable prompt fragment.

### `PromptParts`

Separated prompt fragments before final assembly.

### `ReminderMessage`

Temporary one-turn or one-mode injection.

## Tool And Control-Plane State

### `ToolSpec`

What the model knows about one tool.

### `ToolDispatchMap`

Name-to-handler routing table.

### `ToolUseContext`

Shared execution environment visible to tools.

### `ToolResultEnvelope`

Normalized result returned into the main loop.

### `PermissionRule`

Policy that decides allow / deny / ask.

### `PermissionDecision`

Structured output of the permission gate.

### `HookEvent`

Normalized lifecycle event emitted around the loop.

## Durable Work State

### `TaskRecord`

Durable work-graph node with goal, status, and dependency edges.

### `ScheduleRecord`

Rule describing when work should trigger.

### `MemoryEntry`

Cross-session fact worth keeping.

## Runtime Execution State

### `RuntimeTaskState`

Live execution-slot record for background or long-running work.

### `Notification`

Small result bridge that carries runtime outcomes back into the main loop.

### `RecoveryState`

State used to continue coherently after failures.

## Team And Platform State

### `TeamMember`

Persistent teammate identity.

### `MessageEnvelope`

Structured message between teammates.

### `RequestRecord`

Durable record for approvals, shutdowns, handoffs, or other protocol workflows.

### `WorktreeRecord`

Record for one isolated execution lane.

### `MCPServerConfig`

Configuration for one external capability provider.

### `CapabilityRoute`

Routing decision for native, plugin, or MCP-backed capability.

## A Useful Quick Map

| Record | Main Job | Usually Lives In |
|---|---|---|
| `Message` | conversation history | `messages[]` |
| `QueryState` | turn-by-turn control | query engine |
| `ToolUseContext` | tool execution environment | tool control plane |
| `PermissionDecision` | execution gate outcome | permission layer |
| `TaskRecord` | durable work goal | task board |
| `RuntimeTaskState` | live execution slot | runtime manager |
| `TeamMember` | persistent teammate | team config |
| `RequestRecord` | protocol state | request tracker |
| `WorktreeRecord` | isolated execution lane | worktree index |
| `MCPServerConfig` | external capability config | settings / plugin config |

## Key Takeaway

**High-completion systems become much easier to understand when every important record has one clear job and one clear layer.**
