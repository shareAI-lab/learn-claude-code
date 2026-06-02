# s15: Workflow Orchestration

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > [ s15 ] s16 > s17 > s18 > s19`

> *"Orchestration is code, not prompts"* -- deterministic multi-agent pipelines.
>
> **Harness layer**: Workflow primitives -- the harness scripts control agent flow, not the model.

## Problem

By s14, the agent can use any tool. But complex tasks need multiple agents working in structured patterns. Should agent A finish before B starts? Should C and D run in parallel? The model can decide this, but it's unreliable -- every invocation makes a different choice.

Put the flow in code, not in prompts.

## Solution

```
parallel() -- fan-out N independent agents:
+-----------+     +-----------+     +-----------+
| Agent A   |     | Agent B   |     | Agent C   |   (all run at once)
| review    |     | review    |     | review    |
+-----+-----+     +-----+-----+     +-----+-----+
      |                |                |
      +----------------+----------------+
                       |
                 collect results

pipeline() -- each item flows through stages:
Item 1: [Stage1 ---- Stage2 ---- Stage3]
Item 2:    [Stage1 ---- Stage2 ---- Stage3]   (overlapping)
```

## How It Works

Three primitives:

1. **`parallel(tasks)`** -- fan out N agents simultaneously.

```python
def parallel(tasks):
    # tasks: [{"prompt": "...", "system": "...", "label": "..."}, ...]
    # returns: [{"label": "...", "result": "..."}, ...]
    threads = []
    for task in tasks:
        t = threading.Thread(target=run_agent, args=(task,))
        threads.append(t); t.start()
    for t in threads:
        t.join()
    return results
```

2. **`pipeline(items, stages)`** -- pass items through sequential stages.

```python
def pipeline(items, stages):
    # stages: [{"name": "...", "prompt_fn": fn}, ...]
    results = []
    for item in items:
        prev = item
        for stage in stages:
            prev = run_agent(stage["prompt_fn"](item, prev), ...)
        results.append(prev)
    return results
```

3. **`phase(name)`** -- context manager for progress tracking.

```python
with phase("1. Parallel Reviews"):
    reviews = parallel(tasks)
with phase("2. Synthesis"):
    report = run_agent(synthesis_prompt, ...)
```

## Try It

```sh
cd learn-claude-code
python agents/s15_workflow_orchestration.py
```

Try these:

1. `/review` -- run 3-agent parallel code review (bugs, style, security)
2. `/demo` -- full workflow demo with sample code
3. `/pipeline <text>` -- run summarize-extract pipeline on text
