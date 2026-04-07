# s00d: Chapter Order Rationale

> **Deep Dive** -- Read this after completing Stage 1 (s01-s06) or whenever you wonder "why is the course ordered this way?"

This note is not about one mechanism. It answers a more basic teaching question: why does this curriculum teach the system in the current order instead of following source-file order, feature hype, or raw implementation complexity?

## Conclusion First

The current `s01 -> s19` order is structurally sound.

Its strength is not just breadth. Its strength is that it grows the system in the same order you should understand it:

1. Build the smallest working agent loop.
2. Add the control-plane and hardening layers around that loop.
3. Upgrade session planning into durable work and runtime state.
4. Only then expand into persistent teams, isolated execution lanes, and external capability buses.

That is the right teaching order because it follows:

**dependency order between mechanisms**

not file order or product packaging order.

## The Four Dependency Lines

This curriculum is really organized by four dependency lines:

1. `core loop dependency`
2. `control-plane dependency`
3. `work-state dependency`
4. `platform-boundary dependency`

In plain English:

```text
first make the agent run
  -> then make it run safely
  -> then make it run durably
  -> then make it run as a platform
```

## The Real Shape of the Sequence

```text
s01-s06
  build one working single-agent system

s07-s11
  harden and control that system

s12-s14
  turn temporary planning into durable work + runtime

s15-s19
  expand into teammates, protocols, autonomy, isolated lanes, and external capability
```

After each stage, you should be able to say:

- after `s06`: "I can build one real single-agent harness"
- after `s11`: "I can make that harness safer, steadier, and easier to extend"
- after `s14`: "I can manage durable work, background execution, and time-triggered starts"
- after `s19`: "I understand the platform boundary of a high-completion agent system"

## Why The Early Chapters Must Stay In Their Current Order

### `s01` must stay first

Because it establishes:

- the minimal entry point
- the turn-by-turn loop
- why tool results must flow back into the next model call

Without this, everything later becomes disconnected feature talk.

### `s02` must immediately follow `s01`

Because an agent that cannot route intent into tools is still only talking, not acting.

`s02` is where learners first see the harness become real:

- model emits `tool_use`
- the system dispatches to a handler
- the tool executes
- `tool_result` flows back into the loop

### `s03` should stay before `s04`

This is an important guardrail.

You should first understand:

- how the current agent organizes its own work

before learning:

- when to delegate work into a separate sub-context

If `s04` comes too early, subagents become an escape hatch instead of a clear isolation mechanism.

### `s05` should stay before `s06`

These two chapters solve two halves of the same problem:

- `s05`: prevent unnecessary knowledge from entering the context
- `s06`: manage the context that still must remain active

That order matters. A good system first avoids bloat, then compacts what is still necessary.

## Why `s07-s11` Form One Hardening Block

These chapters all answer the same larger question:

**the loop already works, so how does it become stable, safe, and legible as a real system?**

### `s07` should stay before `s08`

Permission comes first because the system must first answer:

- may this action happen at all
- should it be denied
- should it ask the user first

Only after that should you teach hooks, which answer:

- what extra behavior attaches around the loop

So the correct teaching order is:

**gate first, extend second**

### `s09` should stay before `s10`

This is another very important ordering decision.

`s09` teaches:

- what durable information exists
- which facts deserve long-term storage

`s10` teaches:

- how multiple information sources are assembled into model input

That means:

- memory defines one content source
- prompt assembly explains how all content sources are combined

If you reverse them, prompt construction starts to feel arbitrary and mysterious.

### `s11` is the right closing chapter for this block

Error recovery is not an isolated feature.

It is where the system finally needs to explain:

- why it is continuing
- why it is retrying
- why it is stopping

That only becomes legible after the input path, tool path, state path, and control path already exist.

## Why `s12-s14` Must Stay Goal -> Runtime -> Schedule

This is the easiest part of the curriculum to teach badly if the order is wrong.

### `s12` must stay before `s13`

`s12` teaches:

- what work exists
- dependency relations between work nodes
- when downstream work unlocks

`s13` teaches:

- what live execution is currently running
- where background results go
- how runtime state writes back

That is the crucial distinction:

- `task` is the durable work goal
- `runtime task` is the live execution slot

If `s13` comes first, you will almost certainly collapse those two into one concept.

### `s14` must stay after `s13`

Cron does not add another kind of task.

It adds a new start condition:

**time becomes one more way to launch work into the runtime**

So the right order is:

`durable task graph -> runtime slot -> schedule trigger`

## Why `s15-s19` Should Stay Team -> Protocol -> Autonomy -> Worktree -> Capability Bus

### `s15` defines who persists in the system

Before protocols or autonomy make sense, the system needs durable actors:

- who teammates are
- what identity they carry
- how they persist across work

### `s16` then defines how those actors coordinate

Protocols should not come before actors.

Protocols exist to structure:

- who requests
- who approves
- who responds
- how requests remain traceable

### `s17` only makes sense after both

Autonomy is easy to teach vaguely.

But in a real system it only becomes clear after:

- persistent teammates exist
- structured coordination already exists

Otherwise "autonomous claiming" sounds like magic instead of the bounded mechanism it really is.

### `s18` should stay before `s19`

Worktree isolation is a local execution-boundary problem:

- where parallel work actually runs
- how one work lane stays isolated from another

That should become clear before moving outward into:

- plugins
- MCP servers
- external capability routing

Otherwise you risk over-focusing on external capability and under-learning the local platform boundary.

### `s19` is correctly last

It is the outer platform boundary.

It only becomes clean once you already understand:

- local actors
- local work lanes
- local durable work
- local runtime execution
- then external capability providers

## Five Reorders That Would Make The Course Worse

1. Moving `s04` before `s03`
   This teaches delegation before local planning.

2. Moving `s10` before `s09`
   This teaches prompt assembly before the learner understands one of its core inputs.

3. Moving `s13` before `s12`
   This collapses durable goals and live runtime slots into one confused idea.

4. Moving `s17` before `s15` or `s16`
   This turns autonomy into vague polling magic.

5. Moving `s19` before `s18`
   This makes the external platform look more important than the local execution boundary.

## A Good Maintainer Check Before Reordering

Before moving chapters around, ask:

1. Does the learner already understand the prerequisite concept?
2. Will this reorder blur two concepts that should stay separate?
3. Is this chapter mainly about goals, runtime state, actors, or capability boundaries?
4. If I move it earlier, will the reader still be able to build the minimal correct version?
5. Am I optimizing for understanding, or merely copying source-file order?

If the honest answer to the last question is "source-file order", the reorder is probably a mistake.

## Key Takeaway

**A good chapter order is not just a list of mechanisms. It is a sequence where each chapter feels like the next natural layer grown from the previous one.**
