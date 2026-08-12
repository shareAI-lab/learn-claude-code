# s16: Workflow Runtime — Put the Recipe in Code

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> Workflow = orchestration written as code. Script owns topology; the model judges each step.
>
> **Harness layer**: Orchestration — a multi-agent script above the single-agent loop.
>
> Trust the model. Engineer the harness. Workflows take that one floor up.

---

## Problem

On long jobs, plan and action share one chat: stop early, grade your own homework kindly, lose quiet constraints after compressions. Soft chat memory is a weak place for parallelism, stable result shapes, and resume.

Nudging turn-by-turn is like texting the chef every ten seconds. A **workflow** is a recipe the kitchen can follow.

## Idea

Helpers (subagents) still think. The **script** owns loops, fan-out, and merge. Intermediates live in variables and a journal — not the conversation.

**Orchestration moves from intelligence to structure.**

```text
  messages[] ──► Workflow(...) ──► tool_result
                      │
                      ▼
              script owns: agent / parallel / pipeline
                      │
                      ▼
                 variables + journal
```

One `Workflow` tool call starts the run; one result comes back when it finishes.

<details>
<summary>Runtime overview diagram</summary>

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

</details>

## Two doors

- **Dynamic**: model writes a JS orchestration script for *this* task (`script` / `scriptPath`).
- **Saved**: good script under `.claude/workflows/`; call by `name` + `args`.
- **Static** (cousin outside): Agent SDK / `claude -p` written ahead — usually more generic.

![Static vs dynamic](images/dynamic-vs-static.png)

*Left: fixed pipeline → generic report. Right: cut for your code → a specific recommendation.*

This chapter is a **Python teaching runtime** (no JS VM). Concepts map to Claude Code; the demo uses the Saved door. In the product the model can submit executable scripts — we just skip embedding a JS interpreter here.

```python
# teaching sketch — not the full schema
Workflow({ "name": "review-changes", "args": { "changes": "..." } })
# Claude Code also accepts: script | scriptPath | resumeFromRunId
```

## Three verbs

```text
  agent      one helper, one job (optional schema → validated JSON)
  pipeline   each item walks stages alone (default — no barrier)
  parallel   wait for every tray (barrier — use sparingly)
```

On failure the fleet continues: `parallel` → `null` in that slot; `pipeline` drops **that item** and its later stages. Filter before merge.

Resume: journal records calls in invocation order; replay the **longest unchanged prefix**, then run live. Real JS runtimes ban `Date.now()` / `Math.random()`. This demo does not fully sandbox that — write deterministic scripts anyway.

```text
  journal  [A] [B] [C] [D]
  resume    hit hit  ✂  live
```

<details>
<summary>Official primitive card + quieter verbs</summary>

![Workflow primitives](images/workflow-primitives.png)

*`agent`; `parallel` (barrier) vs `pipeline` (streaming stages). Claude Code also has `model` / `isolation` / `agentType`; teaching surface is smaller.*

Quieter: `phase`, `log`, nested `workflow`, `args`, `budget`.

</details>

## Two shapes + one sample

Feel two first (full six-pattern grid in the fold below):

```text
  Fanout          task ──► ● ● ● ● ══barrier══► synthesize
  Adversarial     worker ──► verifier×N  → keep what still stands
```

Sample `review-changes` = **Fanout** with **Adversarial** inside: `pipeline(audit, verify)` per dimension; `parallel` verifiers; keep only `isReal`.

```text
  correctness ── audit ── verify ──┐
  security    ── audit ── verify ──┤── confirmed
  performance ── audit ── verify ──┤
  style       ── audit ── verify ──┘
```

```python
# from code.py (abbreviated)
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    return {"confirmed": confirmed}
```

The fleet cannot stop early, the author is not the judge, and topology is not rewritten every chat turn.

<details>
<summary>Six-pattern grid + primitive map</summary>

![Six Workflow Patterns](images/six-workflow-patterns.png)

| Pattern | Primitive sketch | Skip when… |
|---------|------------------|------------|
| Classify-And-Act | `agent` → branch → `agent` | Same treatment for every item |
| Fanout-And-Synthesize | `pipeline` / `parallel` → merge | One pass already fits |
| Adversarial Verification | produce → `parallel(verify)` → filter | A wrong answer is cheap |
| Generate-And-Filter | `parallel(gens)` → filter | Answer space is already tiny |
| Tournament | pairwise judge `agent`s | A clear rubric picks a winner |
| Loop Until Done | `while` + stop + `budget` | Work size is known |

```python
# teaching sketch
kind = await ctx.agent("classify this ticket", schema=KIND)
if kind["type"] == "billing":
    return await ctx.agent("handle billing…")
```

</details>

<details>
<summary>Untrusted input: quarantine</summary>

The agent that *reads* tickets should not also hold PR keys. Readers stay read-only → structured summary; a trusted actor acts on the summary only.

```text
  backlog (untrusted) → [quarantine: readers → dedupe → summary] → [trusted: actor]
```

![Quarantine triage](images/quarantine-triage.png)

*High-privilege tools stay on the trusted side. Pair with `/loop` if the backlog never sleeps.*

</details>

<details>
<summary>How this hangs on s15</summary>

s15 stays the host loop; s16 only adds a `Workflow` tool. Product runs can be background; the teaching CLI keeps `demo` / `resume` in the foreground for phases and cache hits.

</details>

## Neighbors & when not

Who holds the plan? s06 one-shot delegate, s13 mailbox peers, s15 one loop, **s16 script + journal**, s17 asks “is the whole goal done?”

Ordinary coding: one s15 turn or one honest s06 often wins. Workflows cost tokens and coordination — reach for them when structure must outlast a single context.

## Try it

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow (real API)
python s16_workflow_runtime/code.py demo     # fixed fixture; watch phases
python s16_workflow_runtime/code.py resume   # same runId; expect cache hits
```

A full resume should show `agents=0 tokens=0`.

## Next

s16 is how a batch runs. [s17 Goal Loop](../s17_goal_loop/) asks: stop, or take another turn?

<!-- translation-sync: zh@v18, en@v18, ja@v18 -->
