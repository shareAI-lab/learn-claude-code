# s17: Goal Loop: The Model Proposes a Stop; an Independent Evaluator Decides Whether to Continue

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s15 → [s16](../s16_workflow_runtime/) → `s17`

> *"The model making no more tool calls means that one turn wants to stop. A separate evaluator decides whether the whole goal is complete."*
>
> **Harness layer: continued execution.** Check a completion condition at the end of every turn, and start another turn when work remains.

---

![Goal Loop overview](images/goal-loop-overview.svg)

Since s01, the agent loop has had one simple exit condition: when the model stops calling tools, the program returns.

That is enough for ordinary conversations, but not always for tasks such as "keep fixing until every test passes" or "finish every acceptance criterion." The model may believe the work is done after only part of it. No new `tool_use` means only that the current turn ended; it does not prove that the whole goal was achieved.

`/goal` adds one independent decision before the real return.

## /goal is a session-scoped Stop hook

Enter:

```text
/goal pytest tests/auth exits with code 0 and lint reports no errors
```

The program stores the completion condition and immediately gives it to the main model as the current task. You do not need to send a second "start working" prompt.

When the main model stops calling tools, the loop runs the Goal Stop hook before returning:

```python
if tool_results:
    messages.append({"role": "user", "content": tool_results})
    continue

decision = await self.goal.evaluate_after_turn(self.messages)
if decision.action == "block":
    self.messages.append({
        "role": "user",
        "content": decision.reason,
    })
    continue

return SessionResult(text=text, status=decision.action)
```

With no active goal, the hook allows the stop immediately, so the return condition is the same as in s01.

## The evaluator is separate from the worker

The main model edits code, runs commands, and solves the task. The Goal evaluator is a separate model call with one job: judge the completion condition.

`GoalController` owns the evaluator as an internal dependency of the Goal gate. It is not a second return path beside the main loop.

This lesson has no separate `CommandQueue`: when evaluation blocks the stop, the controller appends the reason to the same `messages[]` and starts the next turn. A larger host may use a shared queue to carry user input, background results, and continuation commands back into the session, but that queue is transport for the whole host, not a component owned by the Goal gate. Putting it inside the gate would blur the decision with the path used to deliver that decision.

The evaluator sees:

- the active Goal condition;
- the conversation so far;
- tool results that the worker placed in that conversation.

It has no tools. It cannot read a file or rerun a test on its own. It can only judge what is already present in the conversation:

```json
{
  "ok": false,
  "reason": "The conversation does not contain pytest's exit code yet.",
  "impossible": false
}
```

`ok=true` means the condition is satisfied. `ok=false` means another turn is needed. If the task can no longer be completed, the evaluator can return `impossible=true`.

## The conversation is the evaluator's input

The evaluator reads the current conversation. Tool results, worker explanations, and background-task notifications all enter it as messages, and the decision depends on what those messages actually say.

The evaluator input keeps the most recent complete messages. If the newest message alone is too large, it keeps that message's beginning and end so one tool result cannot fill the whole evaluator request.

That does not mean a bare "tests passed" claim must be accepted. The evaluator prompt explicitly requires concrete results from the conversation and tells the model not to assume an unreported command succeeded.

It is still a model reading text, so reliability depends on whether important results were surfaced clearly. The worker's system prompt therefore says:

> After running a verification command, report the command and its result clearly enough for an independent evaluator to inspect.

Goal Loop is not a test framework. Tools still perform the real verification. The Goal evaluator only decides whether those verification results are present in the current work record.

## A good completion condition is checkable

"Make the code good" is too vague. The evaluator cannot know what "good" means.

A useful condition states three things:

1. **End state:** what must be true when work is done;
2. **Check:** which command or output proves it;
3. **Constraints:** what must not be broken along the way.

For example:

```text
/goal finish the authentication migration until pytest tests/auth exits 0,
without modifying test files outside tests/auth
```

If you need to bound unattended work, use the main loop's global turn limit instead of hiding a fixed budget inside Goal:

```bash
MAX_TURNS=20 python s17_goal_loop/code.py \
  "/goal fix the type errors until npm run typecheck exits 0"
```

## Unfinished work returns to the same loop

When the evaluator says the condition is not met, it returns a short reason:

```text
The conversation has no complete test result. Run pytest tests/auth and report its exit code.
```

The program appends that reason to `messages[]` and executes `continue` in the current `while` loop. The main model starts another turn without waiting for the user to type "continue."

There is no separate continuation queue. Goal evaluation happens at the loop's return boundary, and unfinished work returns through that same boundary.

## Wait before judging unfinished background work

A Workflow, background command, or other asynchronous task may still be running when the main model ends its current turn.

Evaluating immediately would be premature because the important result has not returned to the conversation. The Goal Stop hook returns `defer`, keeps the Goal active, and skips the evaluator. When the task finishes, the host passes its completion message to `submit_background_result()`; that message enters the same `messages[]`, and the loop resumes.

A Workflow notification has no mechanical privilege. It enters the conversation like other messages, and the evaluator judges the actual result it contains.

## Automatic continuation still needs an exit

Goal has no hidden default budget of twenty turns. The evaluator judges the condition again after each completed turn.

No automatic mechanism should monopolize one request forever, however. This lesson keeps two general exits outside the goal itself:

- the main loop's global `max_turns`;
- a cap on consecutive Stop-hook blocks.

When a limit is reached, the program returns control to the user. It does not mark the goal complete and does not silently clear it. The user can inspect status, provide more information, continue, or clear the goal.

An evaluator error follows the same rule: stop automatic continuation, leave the goal active, and surface the error instead of claiming success when completion could not be judged.

## Inspect, replace, and clear

One session has at most one active Goal.

```text
/goal
```

Shows the condition, elapsed time, evaluation count, main Agent token spend, and the latest evaluator reason.

```text
/goal a new completion condition
```

Replaces the previous Goal and begins work under the new condition immediately.

```text
/goal clear
```

Clears the active Goal. `stop`, `off`, `reset`, `none`, and `cancel` are accepted aliases.

`GoalController.restore()` can restore a still-active Goal from `goal_status` events persisted by the host; this lesson's CLI does not persist a whole session. A completed, failed, or cleared Goal does not restart. The condition carries over, while turn count, elapsed time, and token baseline start fresh.

## What the code adds

This is an independent mechanism example built on the S04 kernel. It keeps the five base tools and the four hook points, then adds four Goal-specific pieces:

| Piece | Responsibility |
|---|---|
| `GoalState` | Store the condition, evaluation count, start time, and latest reason |
| `PromptGoalEvaluator` | Use a separate model call to judge the conversation |
| `GoalController` | Set, inspect, clear, and run the Goal Stop hook |
| `AgentSession` | Connect the Stop hook to the original return boundary |

The integration point is only a few lines:

```python
decision = await self.goal.evaluate_after_turn(self.messages)
if decision.action == "block":
    continue
return SessionResult(text=text, status=decision.action)
```

## Try it

Install dependencies and prepare `.env`:

```bash
pip install -r requirements.txt

# .env
ANTHROPIC_API_KEY=...
MODEL_ID=...

# Optional: use a smaller model for Goal evaluation
GOAL_EVALUATOR_MODEL_ID=...
```

Start the interactive session:

```bash
python s17_goal_loop/code.py
```

Then enter:

```text
/goal python -m pytest exits with code 0
```

You can also set a Goal directly from the command line:

```bash
python s17_goal_loop/code.py "/goal python -m pytest exits with code 0"
```

## Relationship to s16

s16 answers how a batch of work should run: which steps are concurrent, how results are verified, and how an interrupted run resumes.

s17 answers whether the entire task is complete. A Workflow may finish successfully while the user's final requirements are still unmet. Once the Workflow result enters the conversation, the Goal evaluator decides whether the session should stop or continue.

You can use either mechanism on its own. When one host connects them, the Workflow completion message enters the conversation and Goal Loop decides whether the overall task needs another turn.

<!-- translation-sync: zh@v6, en@v6, ja@v6 -->
