# s16: Workflow Runtime — put the plan in code

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

[s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *Don't keep the plan only in chat.* The script owns order; the model owns each judgment.
>
> **Harness layer**: orchestration — a multi-agent script on top of the single agent loop.

## Problem

You already know how to let a model read files, edit code, and read errors in one loop. Some jobs, though, have an order you **already know**: review by dimension, then adversarial checks, then merge. If that order lives only in chat, the model stops halfway and calls it done, grades its own homework too kindly, and after a few compressions even "don't touch X" disappears.

Soft conversation can't carry parallelism, stable result shapes, or crash-and-resume. You don't need a chattier model. You need **orchestration written down**.

## Solution

```text
  your chat ──► Workflow(...) ──► one result back
                    │
                    ▼
            script: agent / pipeline / parallel
                    │
                    ▼
              vars + journal (keep intermediates here, not in the thread)
```

Subagents still think; the **script** owns loops, fan-out, and merge. Intermediates live in variables and a journal, not the host dialogue.

One line: **move orchestration from intelligence to structure.**

![static harness vs dynamic workflow](images/dynamic-vs-static.png)

*Left: a generic fixed pipeline. Right: a harness cut for this task.*

Claude Code has two doors: **dynamic** — the model writes JS for this task (`script` / `scriptPath`); **saved** — rerun a good script with `name` + `args`. Outside sits static SDK / `claude -p` orchestration. This lesson is a **Python teaching runtime** (no JS VM): same ideas, demo on the saved door. In the product the model can submit scripts — we just don't run JS here.

## How it works

**1. Three verbs**

```text
  agent      one helper, one job (optional schema → JSON you can pass on)
  pipeline   each item walks stages on its own (default; no barrier)
  parallel   wait for every result (barrier; use sparingly)
```

On failure: a `parallel` slot becomes `null`; `pipeline` drops that item. The fleet does not sink. Filter before you merge.

**2. Resume from a notebook, not chat memory**

The journal records `agent()` calls in **invocation order**. Resume replays the longest unchanged prefix; after the first change, everything runs live. Real JS runtimes ban `Date.now()` / `Math.random()` so the notebook can match — keep teaching scripts deterministic too.

```text
  journal  [A] [B] [C] [D]
  resume    hit  hit  ✂ live
```

**3. One sample: fan-out + adversarial**

`review-changes` is not "one pattern". It is **Fanout** with **Adversarial** inside: `pipeline(audit, verify)` per dimension, then `parallel` verifiers, keep only findings that still stand.

```text
  correctness ── audit ── verify ──┐
  security    ── audit ── verify ──┤── confirmed
  performance ── audit ── verify ──┤
  style       ── audit ── verify ──┘
```

```python
# from code.py — the shape is the point
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    return {"confirmed": confirmed}
```

The fleet can't stop early, authors don't referee themselves, and topology isn't rewritten by a tired chat turn.

<details>
<summary>Six common shapes (pattern toolbox)</summary>

![Six workflow patterns](images/six-workflow-patterns.png)

| Pattern | In plain words | Primitives |
|------|------|----------|
| Classify-And-Act | Sort, then hand off | `agent` → branch → `agent` |
| Fanout-And-Synthesize | Split, then merge | `pipeline` / `parallel` → synthesize |
| Adversarial Verification | Don't let the fox grade the henhouse | produce → `parallel(verify)` → filter |
| Generate-And-Filter | Many drafts, then a ruler | `parallel(gens)` → filter |
| Tournament | Pairwise to a winner | judge `agent` |
| Loop Until Done | Keep going while "anything new?" | `while` + stop + `budget` |

`review-changes` ≈ Fanout + Adversarial. Research stacks often go fan-out → filter → verify → synthesize.

</details>

<details>
<summary>Dynamic / saved / static & official primitives</summary>

```python
# teaching sketch
Workflow({ "name": "review-changes", "args": { "changes": "..." } })
# Claude Code also accepts: script | scriptPath | resumeFromRunId
```

![Workflow primitives](images/workflow-primitives.png)

</details>

<details>
<summary>Untrusted input: quarantine reads</summary>

The agent that reads tickets should not also hold the keys to open a PR. Readers only read → summary; the trusted side acts on the summary.

```text
  backlog → [quarantine: read / dedupe / summarize] → [trusted: act]
```

![quarantine triage](images/quarantine-triage.png)

</details>

Who owns the plan? s06 is one-shot dispatch, s13 is teammates with a mailbox, s15 is one chat loop, **s16 is script + journal**, s17 asks at the door whether the whole goal is done. For ordinary file edits, s15 or one s06 is often enough. Workflows cost tokens and coordination — reach for them when **structure must outlive a single conversation**.

## Try it

```bash
python s16_workflow_runtime/code.py demo
python s16_workflow_runtime/code.py resume
```

First run: watch Review → Verify. Second run on the same id: expect mostly `cached` (ideally `agents=0 tokens=0`). For the full host loop, run `code.py` with no args.

s15 is still the loop; this chapter only adds a `Workflow` tool. [s17](../s17_goal_loop/) asks a different question: should we stop?

<!-- translation-sync: zh@v19, en@v19, ja@v19 -->
