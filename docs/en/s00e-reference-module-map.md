# s00e: Reference Module Map

> **Deep Dive** -- Read this when you want to verify how the teaching chapters map to the real production codebase.

This is a calibration note for maintainers and serious learners. It does not turn the reverse-engineered source into required reading. Instead, it answers one narrow but important question: if you compare the high-signal module clusters in the reference repo with this teaching repo, is the current chapter order actually rational?

## Verdict First

Yes.

The current `s01 -> s19` order is broadly correct, and it is closer to the real design backbone than any naive "follow the source tree" order would be.

The reason is simple:

- the reference repo contains many surface-level directories
- but the real design weight is concentrated in a smaller set of control, state, task, team, worktree, and capability modules
- those modules line up with the current four-stage teaching path

So the right move is **not** to flatten the teaching repo into source-tree order.

The right move is:

- keep the current dependency-driven order
- make the mapping to the reference repo explicit
- keep removing low-value product detail from the mainline

## How This Comparison Was Done

The comparison was based on the reference repo's higher-signal clusters, especially modules around:

- `Tool.ts`
- `state/AppStateStore.ts`
- `coordinator/coordinatorMode.ts`
- `memdir/*`
- `services/SessionMemory/*`
- `services/toolUseSummary/*`
- `constants/prompts.ts`
- `tasks/*`
- `tools/TodoWriteTool/*`
- `tools/AgentTool/*`
- `tools/ScheduleCronTool/*`
- `tools/EnterWorktreeTool/*`
- `tools/ExitWorktreeTool/*`
- `tools/MCPTool/*`
- `services/mcp/*`
- `plugins/*`
- `hooks/toolPermission/*`

This is enough to judge the backbone without dragging you through every product-facing command, compatibility branch, or UI detail.

## The Real Mapping

| Reference repo cluster | Typical examples | Teaching chapter(s) | Why this placement is right |
|---|---|---|---|
| Query loop + control state | `Tool.ts`, `AppStateStore.ts`, query/coordinator state | `s00`, `s00a`, `s00b`, `s01`, `s11` | The real system is not just `messages[] + while True`. The teaching repo is right to start with the tiny loop first, then add the control plane later. |
| Tool routing and execution plane | `Tool.ts`, native tools, tool context, execution helpers | `s02`, `s02a`, `s02b` | The source clearly treats tools as a shared execution surface, not a toy dispatch table. The teaching split is correct. |
| Session planning | `TodoWriteTool` | `s03` | Session planning is a small but central layer. It belongs early, before durable tasks. |
| One-shot delegation | `AgentTool` in its simplest form | `s04` | The reference repo's agent spawning machinery is large, but the teaching repo is right to teach the smallest clean subagent first: fresh context, bounded task, summary return. |
| Skill discovery and loading | `DiscoverSkillsTool`, `skills/*`, prompt sections | `s05` | Skills are not random extras. They are a selective knowledge-loading layer, so they belong before prompt and context pressure become severe. |
| Context pressure and collapse | `services/toolUseSummary/*`, `services/contextCollapse/*`, compact logic | `s06` | The reference repo clearly has explicit compaction machinery. Teaching this before later platform features is correct. |
| Permission gate | `types/permissions.ts`, `hooks/toolPermission/*`, approval handlers | `s07` | Execution safety is a distinct gate, not "just another hook". Keeping it before hooks is the right teaching choice. |
| Hooks and side effects | `types/hooks.ts`, hook runners, lifecycle integrations | `s08` | The source separates extension points from the primary gate. Teaching them after permissions preserves that boundary. |
| Durable memory selection | `memdir/*`, `services/SessionMemory/*`, extract/select memory helpers | `s09` | The source makes memory a selective cross-session layer, not a generic notebook. Teaching this before prompt assembly is correct. |
| Prompt assembly | `constants/prompts.ts`, prompt sections, memory prompt loading | `s10`, `s10a` | The source builds inputs from many sections. The teaching repo is right to present prompt assembly as a pipeline instead of one giant string. |
| Recovery and continuation | query transition reasons, retry branches, compaction retry, token recovery | `s11`, `s00c` | The reference repo has explicit continuation logic. This belongs after loop, tools, compaction, permissions, memory, and prompt assembly already exist. |
| Durable work graph | task records, task board concepts, dependency unlocks | `s12` | The teaching repo correctly separates durable work goals from temporary session planning. |
| Live runtime tasks | `tasks/types.ts`, `LocalShellTask`, `LocalAgentTask`, `RemoteAgentTask`, `MonitorMcpTask` | `s13`, `s13a` | The source has a clear runtime-task union. This strongly validates the teaching split between `TaskRecord` and `RuntimeTaskState`. |
| Scheduled triggers | `ScheduleCronTool/*`, `useScheduledTasks` | `s14` | Scheduling appears after runtime work exists, which is exactly the correct dependency order. |
| Persistent teammates | `InProcessTeammateTask`, team tools, agent registries | `s15` | The source clearly grows from one-shot subagents into durable actors. Teaching teammates later is correct. |
| Structured team coordination | message envelopes, send-message flows, request tracking, coordinator mode | `s16` | Protocols make sense only after durable actors exist. The current order matches the real dependency. |
| Autonomous claiming and resuming | coordinator mode, task claiming, async worker lifecycle, resume logic | `s17` | Autonomy in the source is not magic. It is layered on top of actors, tasks, and coordination rules. The current placement is correct. |
| Worktree execution lanes | `EnterWorktreeTool`, `ExitWorktreeTool`, agent worktree helpers | `s18` | The reference repo treats worktree as an execution-lane boundary with closeout logic. Teaching it after tasks and teammates prevents concept collapse. |
| External capability bus | `MCPTool`, `services/mcp/*`, `plugins/*`, MCP resources/prompts/tools | `s19`, `s19a` | The source clearly places MCP and plugins at the outer platform boundary. Keeping this last is the right teaching choice. |

## The Most Important Validation Points

The reference repo strongly confirms five teaching choices.

### 1. `s03` should stay before `s12`

The source contains both:

- small session planning
- larger durable task/runtime machinery

Those are not the same thing.

The teaching repo is correct to teach:

`session planning first -> durable tasks later`

### 2. `s09` should stay before `s10`

The source builds the model input from multiple sources, including memory.

That means:

- memory is one input source
- prompt assembly is the pipeline that combines sources

So memory should be explained before prompt assembly.

### 3. `s12` must stay before `s13`

The runtime-task union in the reference repo is one of the strongest pieces of evidence in the whole comparison.

It shows that:

- durable work definitions
- live running executions

must stay conceptually separate.

If `s13` came first, you would almost certainly merge those two layers.

### 4. `s15 -> s16 -> s17` is the right order

The source has:

- durable actors
- structured coordination
- autonomous resume / claiming behavior

Autonomy depends on the first two. So the current order is correct.

### 5. `s18` should stay before `s19`

The reference repo treats worktree isolation as a local execution-boundary mechanism.

That should be understood before you are asked to reason about:

- external capability providers
- MCP servers
- plugin-installed surfaces

Otherwise external capability looks more central than it really is.

## What This Teaching Repo Should Still Avoid Copying

The reference repo contains many things that are real, but should still not dominate the teaching mainline:

- CLI command surface area
- UI rendering details
- telemetry and analytics branches
- product integration glue
- remote and enterprise wiring
- platform-specific compatibility code
- line-by-line naming trivia

These are valid implementation details.

They are not the right center of a 0-to-1 teaching path.

## Where The Teaching Repo Must Be Extra Careful

The mapping also reveals several places where things can easily drift into confusion.

### 1. Do not merge subagents and teammates into one vague concept

The reference repo's `AgentTool` spans:

- one-shot delegation
- async/background workers
- teammate-like persistent workers
- worktree-isolated workers

That is exactly why the teaching repo should split the story across:

- `s04`
- `s15`
- `s17`
- `s18`

### 2. Do not teach worktree as "just a git trick"

The source shows closeout, resume, cleanup, and isolation state around worktrees.

So `s18` should keep teaching:

- lane identity
- task binding
- keep/remove closeout
- resume and cleanup concerns

not just `git worktree add`.

### 3. Do not reduce MCP to "remote tools"

The source includes:

- tools
- resources
- prompts
- elicitation / connection state
- plugin mediation

So `s19` should keep a tools-first teaching path, but still explain the wider capability-bus boundary.

## Final Judgment

Compared against the high-signal module clusters in the reference repo, the current chapter order is sound.

The biggest remaining quality gains do **not** come from another major reorder.

They come from:

- cleaner bridge docs
- stronger entity-boundary explanations
- tighter multilingual consistency
- web pages that expose the same learning map clearly

## Key Takeaway

**The best teaching order is not the order files appear in a repo. It is the order in which dependencies become understandable to a learner who wants to rebuild the system.**
