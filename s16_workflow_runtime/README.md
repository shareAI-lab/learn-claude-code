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

Same course motto, raised one floor: trust the model inside each step; decide the shape of the steps yourself.

## What a long chat quietly does wrong

From s01 through s15, plan and action share one context window. Wonderful when the next move depends on what you just found. It frays when the job is long, massively parallel, rigidly structured, or needs a skeptical second opinion.

Watch a long chat carefully and you will meet the habits before you learn their names. It gets tired and declares victory after thirty-five of fifty review items. Asked to check its own homework, it grades kindly — the fox scoring the henhouse. Across many turns and compressions, the quiet “don’t touch X” fades until nobody remembers why it was there.

Those are agentic laziness, self-preferential bias, and goal drift. The names matter less than the feeling: the same window that does the work is also trying to remember the plan. Soft chat memory is a weak place to keep parallelism, stable result shapes, and resume.

## The idea, once it clicks

What if the plan lived in code?

Helpers still think — each at a clean desk. The **script** owns loops, fan-out, and merge. Intermediate results live in variables and a journal, not in the conversation. Laziness struggles to stop the fleet early. Self-checking bias meets a second helper who was not the author. Drift loses its grip because the topology is not rewritten every turn by a tired narrator.

**Workflows move orchestration from intelligence to structure.** The model still judges inside each `agent()`; the script owns the map.

```text
  messages[] ──► Workflow(...) ──► tool_result { launched, result, task }
                      │
                      ▼
              ┌───────────────┐
              │  script owns  │
              │  the topology │
              └───────┬───────┘
                      │ agent / parallel / pipeline
                      ▼
                 variables + journal
```

One `Workflow` tool call starts that run. Progress ticks while it works; one tool result comes back when the recipe finishes.

<details>
<summary>Runtime overview diagram (optional)</summary>

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

</details>

## Two doors — and a cousin outside

Claude Code is straightforward about how you enter.

**Dynamic** — the model writes a JavaScript orchestration script for *this* task (`script`, later `scriptPath`). A harness cut while the problem is still warm.

**Saved** — a good script already lives under something like `.claude/workflows/`. You call it by `name` + `args`. The reusable residue of a run that earned its keep.

Outside sits a cousin: **static** harnesses you write ahead with the Agent SDK or `claude -p`. Those must survive every edge case, so they stay generic. Dynamic ones are cut for *this* cloth; save them when the fit is right.

![Static harness vs dynamic workflow](images/dynamic-vs-static.png)

*Same question, two harnesses. Left: fixed search→verify→summarize → a generic report. Right: read your billing code, branch, invite a devil’s advocate → a specific recommendation.*

**This chapter is a Python teaching runtime.** Same ideas, every line readable. The demo registers one saved workflow by name; concepts map 1:1 to Claude Code’s script world. We will not pretend “the model cannot submit executable code” — that was never true of Claude Code. We simply skip embedding a JS interpreter.

```python
# teaching sketch — saved door (not the full Claude Code schema)
Workflow({ "name": "review-changes", "args": { "changes": "..." } })

# Claude Code also accepts: script | scriptPath | resumeFromRunId
```

## Three verbs the script speaks

School bake sale. Every table: mix → bake → box. Helpers taste; the recipe decides order.

```text
  agent      one helper, one job
  pipeline   each cake walks stages alone   (default — no barrier)
  parallel   wait until EVERY tray is back  (barrier — use sparingly)
```

`agent(prompt, opts?)` asks one helper. With `schema`, you get validated JSON — a socket the next stage can hold — and one retry if the first reply is messy.

`pipeline` lets cake A box while cake B is still mixing. `parallel` is for when the next step truly needs all results together — tasting every tray before the scorecard.

```python
# teaching sketch — shape only (see code.py for the runnable sample)
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

When a helper fails, the fleet stays kind: a `parallel` miss becomes `null` in that slot; a `pipeline` miss drops **that item** and skips its later stages. Filter before you merge.

When the kitchen pauses, a journal on disk remembers calls in *invocation* order. Resume replays the **longest unchanged prefix**; at the first change, everything after runs live. Real JS runtimes ban `Date.now()` / `Math.random()` so the notebook stays aligned. This Python demo does not fully sandbox that — write deterministic scripts anyway.

```text
  journal   [A] [B] [C] [D]
  resume     hit hit  ✂  live   ← prefix breaks at C
```

<details>
<summary>Official primitive card + quieter verbs</summary>

![Workflow primitives](images/workflow-primitives.png)

*Official card: `agent`, then `parallel` (barrier) vs `pipeline` (streaming stages). Claude Code also exposes `model` / `isolation` / `agentType`; our teaching runtime keeps a smaller surface.*

Quieter verbs: `phase`, `log`, nested `workflow` (one level), `args`, `budget`.

</details>

## Once you can write the recipe — the pattern toolbox

The verbs are flour and heat. What people keep reinventing are a handful of *shapes* — a toolbox, not a mandatory menu.

![Six Workflow Patterns](images/six-workflow-patterns.png)

*Official six-pattern grid. Script owns topology; this lesson speaks each shape with `agent` / `parallel` / `pipeline` / journal.*

Three shapes matter most for the sample ahead — feel them before the names pile up.

**Fanout-And-Synthesize** — fifty files will not fit one tired context. Split, run many, merge at a barrier.

```text
  task ──► ● ● ● ● ══barrier══► synthesize
```

**Adversarial Verification** — the fox must not grade the henhouse. A worker produces; independent verifiers try to knock it down; only survivors remain.

```text
  worker ──► verifier
         ├──► verifier
         └──► verifier   → keep what still stands
```

**Generate-And-Filter** — you need options, not the first clever-sounding idea. Many generators, then a rubric (and dedupe).

The same toolbox holds **Classify-And-Act** (route to a specialist), **Tournament** (pairwise judges to a winner), and **Loop Until Done** (keep spawning while “new findings?” is yes, with a hard `budget`). Borrow a style only when its cost buys clarity or safety.

<details>
<summary>How each pattern maps to this lesson’s primitives</summary>

| Pattern | Primitive sketch | Skip when… |
|---------|------------------|------------|
| Classify-And-Act | `agent` → branch → `agent` | Every item needs the same treatment |
| Fanout-And-Synthesize | `pipeline` / `parallel` → merge | A single pass already fits |
| Adversarial Verification | produce → `parallel(verify)` → filter | A wrong answer is cheap |
| Generate-And-Filter | `parallel(gens)` → filter | The answer space is already tiny |
| Tournament | pairwise judge `agent`s | A clear rubric picks a winner in one pass |
| Loop Until Done | `while` + stop + `budget` | The work has a known size |

```python
# teaching sketch — classify then act
kind = await ctx.agent("classify this ticket", schema=KIND)
if kind["type"] == "billing":
    return await ctx.agent("handle billing…")
```

Compositions are normal: deep research often stacks fanout → filter → verify → synthesize.

</details>

### When workflows meet untrusted input

Support tickets and user feedback are untrusted. The agent that *reads* them should not also hold the keys that open a PR. Keep an airlock: readers stay read-only, pass only a structured summary; a trusted actor acts on the summary — never the raw text.

```text
  backlog (untrusted)
       │
       ▼
  ┌─ QUARANTINE (read-only) ─┐
  │  readers → dedupe → summary │
  └────────────┬───────────────┘
               ▼
  ┌─ TRUSTED (high privilege) ─┐
  │  actor → fix / escalate     │
  └─────────────────────────────┘
```

<details>
<summary>Official quarantine figure</summary>

![Quarantine triage](images/quarantine-triage.png)

*Readers classify and dedupe in quarantine; high-privilege tools live on the trusted side. Pair with `/loop` if the backlog never sleeps.*

</details>

## Walking `review-changes` — a composition

The sample is not “one pattern.” It is **Fanout-And-Synthesize** with **Adversarial Verification** inside — and a light filter when only `isReal` findings survive.

```text
  correctness ── audit ── verify ──┐
  security    ── audit ── verify ──┤── confirmed
  performance ── audit ── verify ──┤
  style       ── audit ── verify ──┘
       fanout        ▲                synthesize
                     └── skeptical verify per finding
```

`pipeline(DIMENSIONS, audit, verify)` gives each dimension its own desk. Inside `verify`, `parallel` of verifier agents is the adversarial chord. List filtering is the synthesize step. Phases mark Review → Verify; the journal remembers every `agent()` so a pause does not redo the audits.

You can almost feel the three failure modes losing their seats: the fleet cannot stop after two dimensions, the author is not the judge, and the topology does not drift mid-run.

```python
# from code.py — runnable sample (abbreviated)
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"confirmed {len(confirmed)} real finding(s)")
    return {"confirmed": confirmed}
```

<details>
<summary>How this hangs on s15 (without replacing it)</summary>

s15 is still the host loop. s16 only adds a `Workflow` tool. You (or the model) ask for a saved name; the adapter runs the script.

In the product, the run can sit in the background with notifications. Our teaching CLI keeps `demo` / `resume` in the foreground so phases and cache hits are easy to watch. Same ideas; we say so when we simplify.

</details>

## Turning the gem: who holds the plan?

The useful question is not “how many agents?” but **who owns the topology**, and where the half-finished bowls live.

| Neighbor | Who holds the plan | Where intermediates live | Best for |
|----------|--------------------|--------------------------|----------|
| [s06 Subagent](../s06_subagent/) | Model, one-shot | Mostly discarded | One dirty subtask |
| [s13 Agent Teams](../s13_agent_teams/) | Lead + mailbox | Shared tasks / messages | Long-running peers |
| [s15 Integrated Harness](../s15_integrated_harness/) | Model in one loop | `messages[]` | Cumulative coding agent |
| **s16 Workflow** | **Script** | **Variables + journal** | Structured fan-out + verify |
| [s17 Goal Loop](../s17_goal_loop/) | Evaluator at stop | Conversation as evidence | “Is the whole goal done?” |

Cheaper paths still win often: a skill as a soft plan, a short multi-agent chat, a hand-written static orchestrator, or one larger model turn. Reach for a workflow when structure must outlast a single context — not because a panel sounds impressive.

## And when to leave it on the shelf

Workflows spend tokens and coordination. Most ordinary coding does not need five reviewers.

Ask whether the job truly wants more compute and a custom harness. If a normal s15 turn — or one honest s06 subagent — will do, stop there. Restraint is part of the design thought.

## Try it

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow (real API)
python s16_workflow_runtime/code.py demo     # fixed fixture; watch phases
python s16_workflow_runtime/code.py resume   # same runId; expect cache hits
```

Watch Review give way to Verify. On a full resume, agents flip to `cached` and you should see `agents=0 tokens=0` — the notebook saying nothing needed reheating.

## Next

s16 is how a batch runs. [s17 Goal Loop](../s17_goal_loop/) asks a different question at the door: should we stop, or take another turn?

<!-- translation-sync: zh@v17, en@v17, ja@v17 -->
