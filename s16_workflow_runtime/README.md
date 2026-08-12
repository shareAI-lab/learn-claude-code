# s16: Workflow Runtime — Put the Recipe in Code

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *"Chatting turn-by-turn is like texting the chef every ten seconds. A workflow is a recipe the kitchen can follow."*
>
> **Harness layer**: Orchestration — run a multi-agent script above the single-agent loop.
>
> Trust the model; engineer the harness. Workflows are harness engineering at the orchestration layer.

---

Imagine you are cooking with a friend over text. You send “chop the onions,” wait, ask “are they done?”, then “now the pan…”. It works for one dish. For a feast with twenty dishes, that chat becomes the bottleneck: you forget steps, repeat yourself, and if the phone dies you start over.

That is ordinary model-as-orchestrator chatting. A **workflow** is the written recipe: the kitchen (runtime) follows it, helpers (subagents) do judgment, and intermediate bowls sit on the counter — not in the group chat.

## Why a harness at all?

The default Claude Code harness is excellent at coding-shaped work: edit, run, read the error, try again — all in one loop.

Some jobs need a **custom harness on top**: deep research, security analysis, agent teams, large code review. You could hand-write that harness once in an SDK. Or — and this is the dynamic idea — Claude can **write a harness for this task on the fly**, run it, and optionally save the good ones.

Course motto, one layer up: trust the model inside each step; engineer the structure around the steps.

## The problem: one window, three ways to fail

From s01 through s15, the model plans and executes in the **same** context. Great when the next move depends on what you just found. Weak when the job is long, massively parallel, rigidly structured, or adversarial.

Claude Code’s designers name three failure modes that show up in that single window. In plain language:

| Failure mode | What it feels like |
|--------------|--------------------|
| **Agentic laziness** | Stops halfway through a fifty-item review and says “done” after thirty-five |
| **Self-preferential bias** | Likes its own findings when asked to check itself — the fox grading the henhouse |
| **Goal drift** | The original “don’t touch X” fades across many turns and compressions |

Chat history is also a weak place to store parallelism, stable result shapes, and resume. You need those for review-many-files, research-then-verify, migrate-N-modules — jobs whose **shape** is already known.

## The idea in one breath

**Move orchestration from intelligence to structure.**

Subagents still think — each in a clean context with a focused job. The **script** owns loops, fan-out, and merge. Intermediate results live in variables (and a journal), not in the conversation. Separate helpers + script-owned control flow is how you fight laziness, self-checking bias, and drift.

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

One `Workflow` tool call starts that scripted run. Lifecycle and progress events fire while it works; one tool result comes back with launch info, the result, and task state.

## Two doors — and dynamic vs static

Claude Code opens two doors into the same kitchen:

| Door | What you pass | When |
|------|----------------|------|
| **Dynamic** | A JavaScript orchestration script (`script`, or later `scriptPath`) | The model writes a recipe for *this* task |
| **Saved** | `name` + `args` | A good recipe lives under e.g. `.claude/workflows/` and you rerun it |

Same kitchen. Dynamic is “write the recipe now.” Saved is “pull the card from the box” — the reusable residue of a good dynamic run.

There is also a cousin outside this lesson: **static** harnesses (Agent SDK / `claude -p` orchestrations you write ahead of time). Static ones must work for every edge case, so they stay generic. Dynamic ones are tailor-made for *this* task; save them when the cut fits well.

**This lesson is a Python teaching runtime.** Same ideas, every line readable. Our demo registers a saved workflow by name; concepts map 1:1 to Claude Code’s script world. We do **not** claim “the model cannot submit executable code” — that was wrong for Claude Code. We simply skip embedding a full JS interpreter here.

```python
# Teaching adapter: saved door (name + args).
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

## Primitives, taught with a kitchen story

You are running a school bake sale. Each table needs mix → bake → box. Helpers taste and judge; the recipe decides the order.

| Primitive | Kitchen meaning |
|-----------|-----------------|
| `agent(prompt, {schema, label, phase})` | Ask one helper to do one job |
| `pipeline(items, *stages)` | **Default.** Each cake goes through mix→bake→box on its own. Cake A can be boxing while cake B is still mixing |
| `parallel(thunks)` | Wait until **every** tray comes back — only when the next step needs all of them together |
| `phase(title)` | Announce “we’re in baking now” on the progress board |
| `log(message)` | Shout a short status line |
| `workflow(name, args)` | Call a smaller recipe (one level deep) |
| `args` | The ingredients list passed into this run |
| `budget` | How many “oven minutes” (tokens) you may spend |

Default to `pipeline`. Reach for `parallel` only when the next step truly needs every prior result at once — like tasting all trays before writing the scorecard.

```python
# Each dimension walks audit → verify on its own (no barrier between stages).
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

## Patterns with taste (not a laundry list)

Think of patterns as recipe styles. Our sample `review-changes` leans on three:

| Pattern | Plain meaning | In the sample |
|---------|---------------|---------------|
| **Fan-out-and-synthesize** | Split the work, give each piece a clean desk, then merge | Four dimensions audit in a `pipeline`, then one confirmed list |
| **Adversarial verification** | A second helper tries to knock the first one’s work down | Each finding faces a verify agent before it counts |
| **Generate-and-filter** | Produce candidates, keep only what survives a test | Findings in → only `isReal` out |

Same toolbox, other styles you will meet later: **classify-and-act** (route by type), **tournament** (compete, then pick a winner), **loop-until-done** (keep going until nothing new appears). Use a pattern only when its cost earns a clearer or safer result.

## Make answers machine-readable

If a helper returns a poem, the next stage cannot reliably zip findings to verdicts. Pass a `schema`: the runtime asks for JSON, validates it, and retries **once**. Fail again and that call errors (see null-isolation below).

```python
out = await ctx.agent(
    f"Inspect this change for {dimension} issues:\n{changes}",
    schema=FINDINGS_SCHEMA,
    label=f"audit:{dimension}",
)
# out is a dict with "findings", not a paragraph
```

Free-form prose is fine for chatting with you. Pipelines need sockets that fit.

## When one helper fails

A fleet should not stop because one tray burned.

- **`parallel`**: a failing thunk becomes `null` / `None` in that slot; the gather itself does not reject.
- **`pipeline`**: a failing stage drops **that item** to `null` / `None` and skips its remaining stages; other items keep going.

Filter with care — usually `if r` / `.filter(Boolean)` — before you merge.

```python
verdicts = await ctx.parallel([...])  # some entries may be None
confirmed = [
    f for f, v in zip(findings, verdicts)
    if v and v.get("isReal")
]
```

## Journal + resume

Every run gets a `runId`. As each `agent()` finishes, the runtime appends a line to a journal on disk. Think of a notebook that lists helpers in the order you *called* them, not the order they wandered back from the oven.

On resume (`resume_from_run_id` / `resumeFromRunId`), the script runs from the top again, but:

1. Compare each `agent()` call, in call order, to the next journal line.
2. **Longest unchanged prefix** → cache hits (instant replay).
3. At the **first** changed or unfinished call, the prefix breaks.
4. **Everything after that runs live** — even if an old key still sits later in the journal.

That is why real JS workflow runtimes ban `Date.now()`, `Math.random()`, and bare `new Date()`: nondeterministic clocks and dice change prompts or call order, and the notebook no longer matches. This Python demo does not fully sandbox that — still write deterministic scripts.

```text
journal:  [A ✓] [B ✓] [C ✓] [D ✓]
resume:   A hit → B hit → C changed → D runs live (no silent hit on old D)
```

## Walk the sample: `review-changes`

Four review dimensions walk the same two-stage path — fan-out, then adversarial verify, then filter:

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── merge confirmed findings
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
```

1. **Review** — each dimension’s auditor returns structured findings (clean desks → less cross-contamination).
2. **Verify** — each finding gets an adversarial checker (`parallel` inside the verify stage) so the author is not also the judge.
3. Keep only findings marked real; sort by severity.

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"confirmed {len(confirmed)} real finding(s)")
    return {"confirmed": confirmed}
```

## How this plugs into s15

s15 is still the host loop. s16 adds one tool: `Workflow`. The model (or you) asks for a saved name; the adapter resolves the registry and runs the script.

| | Claude Code / Pi (product) | This teaching CLI |
|--|----------------------------|-------------------|
| Script language | JavaScript in a sandbox | Python functions you can read |
| Dynamic door | Model writes `script` / edits `scriptPath` | Explained in docs; demo uses saved `name` |
| Host while running | Background + notification; session stays responsive | `demo` / `resume` run in the foreground for clarity |
| Ideas | Same primitives, journal, prefix resume | Teaching model — precise where we simplify |

The main loop does not become a workflow engine. It borrows one tool, the way it borrows `bash` or `task`.

## Neighbors: who holds the plan?

Workflows are not “more agents.” They change **who owns the topology**.

| Neighbor | Who holds the plan | Where intermediate results live | Best for |
|----------|--------------------|---------------------------------|----------|
| [s06 Subagent](../s06_subagent/) | Model, one-shot | Discarded except final summary | Isolate one dirty subtask |
| [s13 Agent Teams](../s13_agent_teams/) | Lead model turn-by-turn + mailbox | Shared tasks / messages | Long-running peers, human-like collaboration |
| [s15 Integrated Harness](../s15_integrated_harness/) | Model in one loop | Conversation `messages[]` | Cumulative coding agent |
| **s16 Workflow** | **Script** | **Script variables + journal** | Known / large structured fan-out + verify |
| [s17 Goal Loop](../s17_goal_loop/) | Evaluator at the stop boundary | Conversation as evidence | “Is the whole goal done?” |

Cheaper alternatives still win often: a skill or prompt as a soft plan, a short multi-agent chat, a hand-written static SDK orchestrator, or simply one bigger model turn. Reach for a workflow when structure must outlast a single context — not because panels sound impressive.

## When *not* to use a workflow

Workflows cost tokens and coordination. Most ordinary coding does **not** need a panel of five reviewers.

Ask: does this job really need more compute and a custom harness? If a normal s15 turn (or one s06 subagent) is enough, stop there. Restraint is part of the design thought — parallelism and specialization have to earn their keep.

## Try it

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow tool (real API)
python s16_workflow_runtime/code.py demo     # fixed fixture: watch phases + agents
python s16_workflow_runtime/code.py resume   # same runId; prefix should be all cache hits
```

What to watch for:

- `workflow_phase` lines for Review, then Verify
- each `workflow_agent` flip from `done` (first run) to `cached` (full resume)
- a short confirmed list at the end; full resume shows `agents=0 tokens=0`

## Relative to s15 → next is s17

| | s15 Integrated Harness | s16 Workflow Runtime |
|--|------------------------|----------------------|
| Loop | One model-driven loop | Same loop; one tool runs a script |
| Who decides the next step | Model, each round | Script owns the batch shape |
| Multi-agent | One-shot subagents | Scripted, resumable `agent()` calls |
| Failure / resume | Conversation memory | Null-isolation + journal prefix |

**s16 = how a batch runs. s17 = whether the whole goal is done.**

[s17 Goal Loop](../s17_goal_loop/) asks an independent evaluator: should we stop, or take another turn? Pair them when a repeatable workflow also needs a hard completion check.

<!-- translation-sync: zh@v12, en@v12, ja@v12 -->
