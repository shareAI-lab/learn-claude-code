# s16: Workflow Runtime — Put the Recipe in Code

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *"Chatting turn-by-turn is like texting the chef every ten seconds. A workflow is a recipe the kitchen can follow."*
>
> **Harness layer**: Orchestration — a multi-agent script above the single-agent loop.
>
> Trust the model. Engineer the harness. Workflows are that idea one floor up.

---

Picture cooking with a friend over text. “Chop the onions.” Wait. “Done yet?” Then the pan, then the salt. One dish survives that rhythm. A feast with twenty plates does not: you forget steps, repeat yourself, and if the phone dies you start over cold.

That is what it feels like when one model is both chef and clipboard — planning and doing inside the same chat. A **workflow** is the written recipe. The kitchen (a small runtime) follows it. Helpers (subagents) taste and judge. Half-finished bowls sit on the counter — in variables and a journal — not in the group thread.

## Why another harness at all?

The default Claude Code harness is already strong at coding-shaped work: change something, run it, read the error, try again. One loop. One mind. A surprising amount of craft.

But some jobs want a **custom harness on top** — deep research, security sweeps, agent teams, a review that fans across a whole change set. You can hand-write that layer once in an SDK. Or — and this is the lively idea — Claude can draft a harness **for this task**, run it, and keep the good ones.

Claude Code’s designers put it simply: dynamic workflows let the model write its own multi-agent harness on the fly. Same course motto, raised one floor: trust the model inside each step; decide the shape of the steps yourself.

## What a long chat quietly does wrong

From s01 through s15, plan and action share one context window. That is wonderful when the next move depends on what you just found.

It frays when the job is long, massively parallel, rigidly structured, or needs a skeptical second opinion. Watch a long chat carefully and you will meet familiar habits before you ever learn their names.

It gets tired and declares victory after thirty-five of fifty review items. Asked to check its own homework, it grades kindly — the fox scoring the henhouse. Across many turns and compressions, the quiet constraint (“don’t touch X”) fades until nobody remembers why it was there.

Those are agentic laziness, self-preferential bias, and goal drift. The names matter less than the feeling: the same window that does the work is also trying to remember the plan. Chat history is a soft place to keep parallelism, stable result shapes, and a way to resume after a crash. Review-many-files, research-then-verify, migrate-N-modules — those jobs already know their shape. Soft memory is not enough.

## The idea, once it clicks

What if the plan lived in code?

Helpers still think — each at a clean desk, with one focused job. The **script** owns the loops, the fan-out, the merge. Intermediate results live in variables and a journal, not in the conversation. Laziness has a harder time stopping the fleet early. Self-checking bias meets a second helper who was not the author. Drift loses its grip because the topology is not rewritten every turn by a tired narrator.

In one line: **workflows move orchestration from intelligence to structure.** The model still judges inside each `agent()`; the script owns the map.

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

One `Workflow` tool call starts that run. Progress ticks while it works; one tool result comes back with launch info, the outcome, and task state.

## Two doors — and a cousin outside

Claude Code is straightforward about how you enter the kitchen.

Sometimes the model writes a JavaScript orchestration script for *this* task and hands it over as `script` (or later edits `scriptPath`). That is the **dynamic** door — a harness cut while the problem is still warm.

Sometimes a good script has already been saved under something like `.claude/workflows/`. You call it by `name` and `args`. That is the **saved** door — the reusable residue of a run that earned its keep.

There is also a cousin: **static** harnesses you write ahead of time with the Agent SDK or `claude -p`. Those must survive every edge case, so they stay generic. Dynamic ones are cut for *this* cloth; save them when the fit is right.

![Static harness vs dynamic workflow](images/dynamic-vs-static.png)

*From Claude Code’s design essay: same question, two harnesses. Left — a fixed search→verify→summarize pipeline that ends in a generic report. Right — a tailor-made workflow that reads your billing code, branches, and invites a devil’s advocate before recommending.*

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

## Three verbs the script speaks

Imagine a school bake sale. Every table needs mix → bake → box. Helpers taste; the recipe decides order.

![Workflow primitives: agent, parallel, pipeline](images/workflow-primitives.png)

*Official primitive card: one `agent`, then the two ways to run many — `parallel` (barrier) vs `pipeline` (each item streams its stages).*

`agent(prompt, opts?)` asks one helper to do one job. With a `schema`, the answer comes back as validated JSON — a socket the next stage can hold — with one retry if the first reply is messy. Real Claude Code also lets you pick `model`, `isolation` (worktree / remote), and `agentType`; this teaching runtime keeps the surface smaller so every line stays readable.

`pipeline(items, *stages)` is the default for multi-stage work. Each cake walks its stages alone, so one can be boxing while another is still mixing. No barrier between stages.

`parallel(thunks)` is the barrier — wait until every tray is back. Reach for it only when the next step truly needs all results together, like writing the scorecard after tasting the whole tray.

Around those sit quieter verbs: `phase` to announce where you are, `log` for a short shout, nested `workflow` one level deep, `args` for the ingredients list, `budget` for oven-minutes (tokens).

```python
# Each review dimension walks audit → verify on its own.
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

When a helper fails, the fleet stays kind. A failing `parallel` thunk becomes `null` in that slot; the gather itself does not reject. A failing `pipeline` stage drops **that item** to null and skips its later stages; other items keep walking. Filter with care before you merge.

And when the kitchen pauses? Every run has a `runId` and a journal on disk — a notebook ordered by the moment you *called* each helper. Resume walks the script from the top and replays the **longest unchanged prefix**. At the first changed or unfinished call, everything after runs live. That is why real JS runtimes ban `Date.now()` and `Math.random()`: clocks and dice make the notebook stop lining up. This Python demo does not fully sandbox that — write deterministic scripts anyway.

```text
journal:  [A ok] [B ok] [C ok] [D ok]
resume:   A hit → B hit → C changed → D runs live
```

## Once you can write the recipe — the pattern toolbox

The verbs are flour and heat. What people keep reinventing are a handful of *shapes*. Think of them as a toolbox, not a mandatory menu.

![Six Workflow Patterns](images/six-workflow-patterns.png)

*The official six-pattern grid — a toolbox, not a mandatory menu. The script owns the topology; this lesson speaks each shape with `agent` / `parallel` / `pipeline` / `phase` / journal.*

**Classify-And-Act.** Pain: one generic helper is mediocre at everything. Shape: a classifier looks, then routes to specialist A, B, or C. Here: one `agent({schema})` returns a label; the script branches to the right follow-up `agent` (or a nested `workflow`). Skip it when every item truly needs the same treatment.

**Fanout-And-Synthesize.** Pain: fifty files will not fit one tired context, and they contaminate each other if they try. Shape: split, run many, wait at a barrier, merge. Here: `pipeline` for per-item stages, or `parallel` when the next step needs every result; merge in ordinary Python after the gather. Skip it for three related files a single pass can hold.

**Adversarial Verification.** Pain: the fox grades the henhouse. Shape: a worker produces; independent verifiers try to refute; only survivors remain. Here: a produce `agent`, then `parallel` of verifier `agent`s (schema’d), then a filter. Phases help (“Review” then “Verify”). Skip it when a wrong answer is cheap.

**Generate-And-Filter.** Pain: you need options, not the first clever-sounding idea. Shape: many generators spill into a rubric + dedupe filter. Here: `parallel` over generators, then script-side filter (or one judge `agent`). Journal matters when generation is expensive. Skip it when the space of good answers is already tiny.

**Tournament.** Pain: absolute scores are mushy for taste and ranking. Shape: pairwise judges, a bracket, a winner — comparative judgment beats lonely scoring. Here: rounds of `parallel` judge `agent`s over pairs until one remains. Skip it when a clear rubric already picks a winner in one pass.

**Loop Until Done.** Pain: you do not know how many passes the mine still holds. Shape: keep spawning while “new findings?” is yes; stop on dry rounds. Here: a `while` over `agent`/`parallel`, a schema’d stop check, and a hard `budget`. Pair with journal resume on a long dig. Skip it when the work has a known size — a fixed `pipeline` is simpler.

After a few have faces, the toolbox fits in one glance:

| Pattern | Primitive sketch | Reach for it when… |
|---------|------------------|--------------------|
| Classify-And-Act | `agent` → branch → `agent` | Items need different specialists |
| Fanout-And-Synthesize | `pipeline` / `parallel` → merge | Many clean desks, then one summary |
| Adversarial Verification | produce → `parallel(verify)` → filter | Wrong answers are expensive |
| Generate-And-Filter | `parallel(gens)` → rubric filter | You need options, then taste |
| Tournament | pairwise judge `agent`s | Ranking / taste without a sharp scale |
| Loop Until Done | `while` + stop + `budget` | Unknown amount of buried work |

Compositions are normal. Deep research often stacks fanout → filter → verify → synthesize. Our sample is a smaller chord of two notes.

### When workflows meet untrusted input

One more shape is worth keeping near the toolbox: **quarantine triage**. Support tickets, bug reports, and user feedback are untrusted. You do not want the agent that *reads* them to also hold the keys that open a PR.

![Quarantine triage](images/quarantine-triage.png)

*Readers stay in a read-only quarantine, classify and dedupe, and pass only a structured summary across. High-privilege tools live on the trusted side — they act on summaries, never on raw content. Pair with `/loop` if the backlog never sleeps.*

In this lesson’s primitives that is still just scripts and agents: a `pipeline` or `parallel` of low-privilege reader `agent`s, a structured summary in a variable, then a separate actor `agent` (or nested `workflow`) that may write. The interesting part is the airlock — who is allowed to see the raw text.

## Walking `review-changes` — a composition

The sample is not “one pattern.” It is **Fanout-And-Synthesize** with **Adversarial Verification** inside — and a light generate-and-filter when only `isReal` findings survive.

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── confirmed findings
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
         fanout                         synthesize
              └── each finding: skeptical verify ──┘
```

`pipeline(DIMENSIONS, audit, verify)` gives each dimension its own desk. Inside `verify`, `parallel` of verifier agents is the adversarial chord. Ordinary list filtering is the synthesize step. Phases mark Review then Verify; the journal remembers every `agent()` so a pause does not redo the audits.

You can almost feel the three failure modes losing their favorite seats: the fleet cannot stop after two dimensions, the author is not the judge, and the topology does not drift mid-run.

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"confirmed {len(confirmed)} real finding(s)")
    return {"confirmed": confirmed}
```

<details>
<summary>How this hangs on s15 without replacing it</summary>

s15 is still the host loop. s16 only adds a tool named `Workflow`. You (or the model) ask for a saved name; the adapter finds the script and runs it.

In the real product, that run can sit in the background with notifications while the session stays responsive. Our teaching CLI keeps `demo` / `resume` in the foreground so you can watch phases and cache hits. Same ideas; we say so when we simplify. The main loop borrows one tool the way it borrows `bash` or `task`.

</details>

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

<!-- translation-sync: zh@v16, en@v16, ja@v16 -->
