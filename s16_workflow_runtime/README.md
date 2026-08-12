# s16: Workflow Runtime — Put the Recipe in Code

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *"Chatting turn-by-turn is like texting the chef every ten seconds. A workflow is a recipe the kitchen can follow."*
>
> **Harness layer**: Orchestration — a multi-agent script above the single-agent loop.
>
> Trust the model; engineer the harness. Workflows are that idea at the orchestration layer.

---

Picture cooking with a friend over text. “Chop the onions.” Wait. “Done?” Then the pan, then the salt. One dish survives that rhythm. A feast with twenty plates does not: you forget steps, repeat yourself, and if the phone dies you start over cold.

That is what it feels like when the model is both chef and clipboard — planning and doing inside the same chat. A **workflow** is the written recipe. The kitchen (the runtime) follows it. Helpers (subagents) taste and judge. The bowls of half-finished work sit on the counter, not in the group thread.

## Why bother with another harness?

The default Claude Code harness is already good at coding-shaped work: change something, run it, read the error, try again. One loop, one mind, a surprising amount of craft.

But some jobs are a different shape — deep research, security sweeps, agent teams, a review that fans out across a whole change set. For those, people have long built a second harness on top. You can still hand-write that layer in an SDK. Or — and this is the lively part — Claude can draft a harness **for this task**, run it, and keep the good ones.

Same course motto, one floor up: trust the model inside each step; decide the shape of the steps yourself.

## What goes wrong in a long chat

From s01 through s15, plan and action share one context window. That is wonderful when the next move depends on what you just found.

It frays when the job is long, massively parallel, rigidly structured, or needs a skeptical second opinion. Watch a long chat carefully and you will see familiar habits. It gets tired and declares victory after thirty-five of fifty review items. Asked to check its own homework, it grades kindly — the fox scoring the henhouse. And across many turns and compressions, the quiet constraint (“don’t touch X”) fades until nobody remembers why it was there.

Claude Code’s designers call these agentic laziness, self-preferential bias, and goal drift. The names matter less than the feeling: the same window that does the work is also trying to remember the plan. Chat history is a soft place to keep parallelism, stable result shapes, and a way to resume after a crash. Review-many-files, research-then-verify, migrate-N-modules — those jobs already know their shape. Soft memory is not enough.

## The idea, once it clicks

What if the plan lived in code?

Helpers still think — each at a clean desk, with one focused job. The **script** owns the loops, the fan-out, the merge. Intermediate results live in variables and a journal, not in the conversation. Laziness has a harder time stopping the fleet early. Self-checking bias meets a second helper who was not the author. Drift loses its grip because the topology is not rewritten every turn by a tired narrator.

In one line: workflows move orchestration from *intelligence* to *structure*. The model still judges inside each `agent()`; the script owns the map.

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

One `Workflow` tool call starts that run. Progress ticks while it works; one tool result comes back with launch info, the outcome, and task state.

## Two doors into the same kitchen

Claude Code is straightforward about how you enter.

Sometimes the model writes a JavaScript orchestration script for *this* task and hands it over as `script` (or later edits `scriptPath`). That is the **dynamic** door — a harness tailored while the problem is still warm.

Sometimes a good script has already been saved under something like `.claude/workflows/`. You call it by `name` and `args`. That is the **saved** door — the reusable residue of a run that earned its keep.

There is a cousin outside this lesson too: **static** harnesses you write ahead of time with the Agent SDK or `claude -p`. Those have to survive every edge case, so they stay generic. Dynamic ones are cut for *this* cloth; save them when the fit is right.

**This chapter is a Python teaching runtime.** Same ideas, every line readable. Our demo registers one saved workflow by name; the concepts map one-to-one onto Claude Code’s script world. We will not pretend “the model cannot submit executable code” — that was never true of Claude Code. We simply do not embed a full JavaScript interpreter here.

```python
# Teaching adapter: the saved door (name + args).
# Claude Code also accepts script / scriptPath / resumeFromRunId.
WORKFLOW_TOOL = {
    "name": "Workflow",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "object"},
            "resume_from_run_id": {"type": "string"},
            "resumeFromRunId": {"type": "string"},
        },
        "required": ["name"],
    },
}
```

## A few kitchen verbs

Imagine a school bake sale. Every table needs mix → bake → box. Helpers taste; the recipe decides order.

`agent(...)` is asking one helper to do one job. `pipeline(items, *stages)` is the default: each cake walks the stages on its own, so one can be boxing while another is still mixing. `parallel(...)` is the barrier — wait until every tray is back — and you only want that when the next step truly needs all of them together, like writing the scorecard after tasting the whole tray.

Around those sit quieter verbs: `phase` to announce where you are on the board, `log` for a short shout, `workflow` to nest one smaller recipe, `args` for the ingredients list, `budget` for how many oven-minutes (tokens) you may burn.

```python
# Each review dimension walks audit → verify on its own.
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

## Patterns, when they earn their keep

You do not need a catalog. Notice what our sample already does, and you have three styles in hand.

It **fans out** the change across review dimensions, each on a clean desk, then **synthesizes** one confirmed list. That is fan-out-and-synthesize — useful when pieces would contaminate each other in one crowded context.

Inside verify, a second helper tries to knock each finding down. That is adversarial verification — the structural answer to grading your own homework.

What survives is a filter over what was generated. Generate-and-filter: candidates in, only the ones that pass out.

The same toolbox holds other cuts you will meet later — classify-and-act, tournament, loop-until-done. Borrow a style only when the extra cost buys clarity or safety you could not get cheaper.

## Answers the next stage can hold

If a helper returns a poem, the next stage cannot zip findings to verdicts. Pass a `schema`. The runtime asks for JSON, checks it, and gives **one** retry. Fail again and that call errors — which brings us to how the fleet stays kind under failure.

```python
out = await ctx.agent(
    f"Inspect this change for {dimension} issues:\n{changes}",
    schema=FINDINGS_SCHEMA,
    label=f"audit:{dimension}",
)
```

Chat with you can stay prose. A pipeline needs sockets that fit.

## When one tray burns

The fleet should not stop because one helper had a bad oven.

In `parallel`, a failing thunk becomes `null` / `None` in that slot; the gather itself does not reject. In `pipeline`, a failing stage drops **that item** to null and skips its later stages; the other items keep walking. Filter with care before you merge — `if r`, or `.filter(Boolean)` in the JS world.

```python
verdicts = await ctx.parallel([...])  # some slots may be None
confirmed = [
    f for f, v in zip(findings, verdicts)
    if v and v.get("isReal")
]
```

## A notebook you can reopen

Every run gets a `runId`. As each `agent()` finishes, a line lands in a journal on disk — a notebook ordered by the moment you *called* the helper, not by who wandered back from the oven first.

Resume (`resume_from_run_id` / `resumeFromRunId`) runs the script from the top again, but kindly. Call by call, in order, it matches the next journal line. The longest unchanged prefix replays from cache. At the first changed or unfinished call, the prefix breaks — and everything after runs live, even if an old key still sits further down the notebook. No silent leaps over a break.

That is also why real JavaScript workflow runtimes ban `Date.now()`, `Math.random()`, and bare `new Date()`. Clocks and dice make prompts or call order wobble, and the notebook stops lining up. This Python demo does not fully sandbox that. Write deterministic scripts anyway.

```text
journal:  [A ✓] [B ✓] [C ✓] [D ✓]
resume:   A hit → B hit → C changed → D runs live
```

## Walking `review-changes`

Four dimensions share one two-stage path — fan out, verify adversarially, keep what survives:

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── confirmed findings
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
```

Review puts each auditor at its own desk so correctness talk does not bleed into security talk. Verify hands every finding to a skeptic who was not the author. Only the real ones remain, sorted by severity. You can almost feel the three failure modes losing their favorite seats.

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"confirmed {len(confirmed)} real finding(s)")
    return {"confirmed": confirmed}
```

## Hanging on s15 without replacing it

s15 is still the host loop. s16 only adds a tool named `Workflow`. You (or the model) ask for a saved name; the adapter finds the script and runs it.

In the real product, that run can sit in the background with notifications while the session stays responsive. Our teaching CLI keeps `demo` and `resume` in the foreground so you can watch phases and cache hits without squinting. Same ideas; we say so when we simplify.

The main loop does not become a workflow engine. It borrows one tool the way it borrows `bash` or `task`.

## Turning the gem: who holds the plan?

Look at the neighbors and the same object shows a new face. The useful question is not “how many agents?” but **who owns the topology**, and where the half-finished bowls live.

| Neighbor | Who holds the plan | Where intermediates live | Best for |
|----------|--------------------|--------------------------|----------|
| [s06 Subagent](../s06_subagent/) | Model, one-shot | Mostly discarded | One dirty subtask, isolated |
| [s13 Agent Teams](../s13_agent_teams/) | Lead, turn by turn + mailbox | Shared tasks / messages | Long-running peers |
| [s15 Integrated Harness](../s15_integrated_harness/) | Model in one loop | Conversation `messages[]` | Cumulative coding agent |
| **s16 Workflow** | **Script** | **Variables + journal** | Structured fan-out and verify |
| [s17 Goal Loop](../s17_goal_loop/) | Evaluator at stop time | Conversation as evidence | “Is the whole goal done?” |

Cheaper paths still win often: a skill as a soft plan, a short multi-agent chat, a hand-written static orchestrator, or one larger model turn. Reach for a workflow when the structure must outlast a single context — not because a panel of reviewers sounds impressive.

## And when to leave it on the shelf

Workflows spend tokens and coordination. Most ordinary coding does not need five reviewers.

Before you spin one up, ask whether the job truly wants more compute and a custom harness. If a normal s15 turn — or one honest s06 subagent — will do, stop there. Restraint is part of the thought: parallelism and specialization have to earn their keep.

## Try it

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow (real API)
python s16_workflow_runtime/code.py demo     # fixed fixture; watch phases
python s16_workflow_runtime/code.py resume   # same runId; expect cache hits
```

Watch Review give way to Verify. Watch agents flip from `done` to `cached` on a full resume. At the end, a short confirmed list — and on a clean resume, `agents=0 tokens=0`, which is the notebook saying: nothing needed reheating.

## Next

s16 is how a batch runs. [s17 Goal Loop](../s17_goal_loop/) asks a different question at the door: should we stop, or take another turn? Pair them when a repeatable recipe also needs a hard “done.”

<!-- translation-sync: zh@v13, en@v13, ja@v13 -->
