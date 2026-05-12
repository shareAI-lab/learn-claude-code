# s11: Error Recovery

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > [ s11 ] > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- Three categories of recoverable failure: truncation, context overflow, and transient transport errors
- How to route each failure to the right recovery branch (continuation, compaction, or backoff)
- Why retry budgets prevent infinite loops
- How recovery state keeps the "why" visible instead of burying it in a catch block

Your agent is doing real work now -- reading files, writing code, calling tools across multiple turns. And real work produces real failures. Output gets cut off mid-sentence. The prompt grows past the model's context window. The API times out or hits a rate limit. If every one of these failures ends the run immediately, your system feels brittle and your users learn not to trust it. But here is the key insight: most of these failures are not true task failure. They are signals that the next step needs a different continuation path.

## The Problem

Your user asks the agent to refactor a large file. The model starts writing the new version, but the output hits `max_tokens` and stops mid-function. Without recovery, the agent just halts with a half-written file. The user has to notice, re-prompt, and hope the model picks up where it left off.

Or: the conversation has been running for 40 turns. The accumulated messages push the prompt past the model's context limit. The API returns an error. Without recovery, the entire session is lost.

Or: a momentary network hiccup drops the connection. Without recovery, the agent crashes even though the same request would succeed one second later.

Each of these is a different kind of failure, and each needs a different recovery action. A single catch-all retry cannot handle all three correctly.

## The Solution

Classify the failure first, choose the recovery branch second, and enforce a retry budget so the system cannot loop forever.

```text
LLM call
  |
  +-- stop_reason == "max_tokens"
  |      -> append continuation reminder
  |      -> retry
  |
  +-- prompt too long
  |      -> compact context
  |      -> retry
  |
  +-- timeout / rate limit / connection error
         -> back off
         -> retry
```

## How It Works

**Step 1. Track recovery state.** Before you can recover, you need to know how many times you have already tried. A simple counter per category prevents infinite loops:

```python
recovery_state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

**Step 2. Classify the failure.** Each failure maps to exactly one recovery kind. The classifier examines the stop reason and error text, then returns a structured decision:

```python
def choose_recovery(stop_reason: str | None, error_text: str | None) -> dict:
    if stop_reason == "max_tokens":
        return {"kind": "continue", "reason": "output truncated"}

    if error_text and "prompt" in error_text and "long" in error_text:
        return {"kind": "compact", "reason": "context too large"}

    if error_text and any(word in error_text for word in [
        "timeout", "rate", "unavailable", "connection"
    ]):
        return {"kind": "backoff", "reason": "transient transport failure"}

    return {"kind": "fail", "reason": "unknown or non-recoverable error"}
```

The separation matters: classify first, act second. That way the recovery reason stays visible in state instead of disappearing inside a catch block.

**Step 3. Handle continuation (truncated output).** When the model runs out of output space, the task did not fail -- the turn just ended too early. You inject a continuation reminder and retry:

```python
CONTINUE_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped. "
    "Do not restart or repeat."
)
```

Without this reminder, models tend to restart from the beginning or repeat what they already wrote. The explicit instruction to "continue directly" keeps the output flowing forward.

**Step 4. Handle compaction (context overflow).** When the prompt becomes too large, the problem is not the task itself -- the accumulated context needs to shrink before the next turn can proceed. You call the same `auto_compact` mechanism from s06 to summarize history, then retry:

```python
if decision["kind"] == "compact":
    messages = auto_compact(messages)
    continue
```

**Step 5. Handle backoff (transient errors).** When the error is probably temporary -- a timeout, a rate limit, a brief outage -- you wait and try again. Exponential backoff (doubling the delay each attempt, plus random jitter to avoid thundering-herd problems where many clients retry at the same instant) keeps the system from hammering a struggling server:

```python
def backoff_delay(attempt: int) -> float:
    delay = min(BACKOFF_BASE_DELAY * (2 ** attempt), BACKOFF_MAX_DELAY)
    jitter = random.uniform(0, 1)
    return delay + jitter
```

**Step 6. Wire it into the loop.** The recovery logic sits right inside the agent loop. Each branch either adjusts the messages and continues, or gives up:

```python
while True:
    try:
        response = client.messages.create(...)
        decision = choose_recovery(response.stop_reason, None)
    except Exception as e:
        response = None
        decision = choose_recovery(None, str(e).lower())

    if decision["kind"] == "continue":
        messages.append({"role": "user", "content": CONTINUE_MESSAGE})
        continue

    if decision["kind"] == "compact":
        messages = auto_compact(messages)
        continue

    if decision["kind"] == "backoff":
        time.sleep(backoff_delay(...))
        continue

    if decision["kind"] == "fail":
        break
```

The point is not clever code. The point is: classify, choose, retry with a budget.

## What Changed from s10

| Aspect | s10: System Prompt | s11: Error Recovery |
|--------|--------------------|--------------------|
| Core concern | Assemble model input from sections | Handle failures without crashing |
| Loop behavior | Runs until end_turn or tool_use | Adds recovery branches before giving up |
| Compaction | Not addressed | Triggered reactively on context overflow |
| Retry logic | Not addressed | Budgeted per failure category |
| State tracking | Prompt sections | Recovery counters |

## A Note on Real Systems

Real agent systems also persist session state to disk, so that a crash does not destroy a long-running conversation. Session persistence, checkpointing, and resumption are separate concerns from error recovery -- but they complement it. Recovery handles the failures you can retry in-process; persistence handles the failures you cannot. This teaching harness focuses on the in-process recovery paths, but keep in mind that production systems need both layers.

## Read Together

- If you start losing track of why the current query is still continuing, go back to [`s00c-query-transition-model.md`](./s00c-query-transition-model.md).
- If context compaction and error recovery are starting to look like the same mechanism, reread [`s06-context-compact.md`](./s06-context-compact.md) to separate "shrink context" from "recover after failure."
- If you are about to move into `s12`, keep [`data-structures.md`](./data-structures.md) nearby because the task system adds a new durable work layer on top of recovery state.

## Common Beginner Mistakes

**Mistake 1: using one retry rule for every error.** Different failures need different recovery actions. Retrying a context-overflow error without compacting first will just produce the same error again.

**Mistake 2: no retry budget.** Without budgets, the system can loop forever. Each recovery category needs its own counter and its own maximum.

**Mistake 3: hiding the recovery reason.** The system should know *why* it is retrying. That reason should stay visible in state -- as a structured decision object -- not disappear inside a catch block.

## Try It

```sh
cd learn-claude-code
python agents/s11_error_recovery.py
```

Try forcing:

- a long response (to trigger max_tokens continuation)
- a large context (to trigger compaction)
- a temporary timeout (to trigger backoff)

Then observe which recovery branch the system chooses and how the retry counter increments.

## What You've Mastered

At this point, you can:

- Classify agent failures into three recoverable categories and one terminal category
- Route each failure to the correct recovery branch: continuation, compaction, or backoff
- Enforce retry budgets so the system never loops forever
- Keep recovery decisions visible as structured state instead of burying them in exception handlers
- Explain why different failure types need different recovery actions

## Stage 2 Complete

You have finished Stage 2 of the harness. Look at what you have built since Stage 1:

- **s07 Permission System** -- the harness asks before acting, and the user controls what gets auto-approved
- **s08 Hook System** -- external scripts run at lifecycle points without touching the agent loop
- **s09 Memory System** -- durable facts survive across sessions
- **s10 System Prompt** -- the prompt is an assembly pipeline with clear sections, not one big string
- **s11 Error Recovery** -- failures route to the right recovery path instead of crashing

Your agent started Stage 2 as a working loop that could call tools and manage context. It finishes Stage 2 as a system that governs itself: it checks permissions, runs hooks, remembers what matters, assembles its own instructions, and recovers from failures without human intervention.

That is a real agent harness. If you stopped here and built a product on top of it, you would have something genuinely useful.

But there is more to build. Stage 3 introduces structured work management -- task lists, background execution, and scheduled jobs. The agent stops being purely reactive and starts organizing its own work across time. See you in [s12: Task System](./s12-task-system.md).

## Key Takeaway

> Most agent failures are not true task failure -- they are signals to try a different continuation path, and the harness should classify them and recover automatically.
