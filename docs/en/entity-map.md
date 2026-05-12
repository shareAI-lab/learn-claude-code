# Entity Map

> **Reference** -- Use this when concepts start to blur together. It tells you which layer each thing belongs to.

As you move into the second half of the repo, you will notice that the main source of confusion is often not code. It is the fact that many entities look similar while living on different layers. This map helps you keep them straight.

## How This Map Differs From Other Docs

- this map answers: **which layer does this thing belong to?**
- [`glossary.md`](./glossary.md) answers: **what does the word mean?**
- [`data-structures.md`](./data-structures.md) answers: **what does the state shape look like?**

## A Fast Layered Picture

```text
conversation layer
  - message
  - prompt block
  - reminder

action layer
  - tool call
  - tool result
  - hook event

work layer
  - work-graph task
  - runtime task
  - protocol request

execution layer
  - subagent
  - teammate
  - worktree lane

platform layer
  - MCP server
  - memory record
  - capability router
```

## The Most Commonly Confused Pairs

### `Message` vs `PromptBlock`

| Entity | What It Is | What It Is Not |
|---|---|---|
| `Message` | conversational content in history | not a stable system rule |
| `PromptBlock` | stable prompt instruction fragment | not one turn's latest event |

### `Todo / Plan` vs `Task`

| Entity | What It Is | What It Is Not |
|---|---|---|
| `todo / plan` | temporary session guidance | not a durable work graph |
| `task` | durable work node | not one turn's local thought |

### `Work-Graph Task` vs `RuntimeTaskState`

| Entity | What It Is | What It Is Not |
|---|---|---|
| work-graph task | durable goal and dependency node | not the live executor |
| runtime task | currently running execution slot | not the durable dependency node |

### `Subagent` vs `Teammate`

| Entity | What It Is | What It Is Not |
|---|---|---|
| subagent | one-shot delegated worker | not a long-lived team member |
| teammate | persistent collaborator with identity and inbox | not a disposable summary tool |

### `ProtocolRequest` vs normal message

| Entity | What It Is | What It Is Not |
|---|---|---|
| normal message | free-form communication | not a traceable approval workflow |
| protocol request | structured request with `request_id` | not casual chat text |

### `Task` vs `Worktree`

| Entity | What It Is | What It Is Not |
|---|---|---|
| task | what should be done | not a directory |
| worktree | where isolated execution happens | not the goal itself |

### `Memory` vs `CLAUDE.md`

| Entity | What It Is | What It Is Not |
|---|---|---|
| memory | durable cross-session facts | not the project rule file |
| `CLAUDE.md` | stable local rule / instruction surface | not user-specific long-term fact storage |

### `MCPServer` vs `MCPTool`

| Entity | What It Is | What It Is Not |
|---|---|---|
| MCP server | external capability provider | not one specific tool |
| MCP tool | one exposed capability | not the whole connection surface |

## Quick "What / Where" Table

| Entity | Main Job | Typical Place |
|---|---|---|
| `Message` | visible conversation context | `messages[]` |
| `PromptParts` | input assembly fragments | prompt builder |
| `PermissionRule` | execution decision rules | settings / session state |
| `HookEvent` | lifecycle extension point | hook system |
| `MemoryEntry` | durable fact | memory store |
| `TaskRecord` | work goal node | task board |
| `RuntimeTaskState` | live execution slot | runtime manager |
| `TeamMember` | persistent worker identity | team config |
| `MessageEnvelope` | structured teammate message | inbox |
| `RequestRecord` | protocol workflow state | request tracker |
| `WorktreeRecord` | isolated execution lane | worktree index |
| `MCPServerConfig` | external capability provider config | plugin / settings |

## Key Takeaway

**The more capable the system becomes, the more important clear entity boundaries become.**
