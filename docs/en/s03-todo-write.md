# s03: TodoWrite

`s01 > s02 > [ s03 ] > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- How session planning keeps the model on track during multi-step tasks
- How a structured todo list with status tracking replaces fragile free-form plans
- How gentle reminders (nag injection) pull the model back when it drifts

Have you ever asked an AI to do a complex task and watched it lose track halfway through? You say "refactor this module: add type hints, docstrings, tests, and a main guard" and it nails the first two steps, then wanders off into something you never asked for. This is not a model intelligence problem -- it is a working memory problem. As tool results pile up in the conversation, the original plan fades. By step 4, the model has effectively forgotten steps 5 through 10. You need a way to keep the plan visible.

## The Problem

On multi-step tasks, the model drifts. It repeats work, skips steps, or improvises once the system prompt fades behind pages of tool output. The context window (the total amount of text the model can hold in working memory at once) is finite, and earlier instructions get pushed further away with every tool call. A 10-step refactoring might complete steps 1-3, then the model starts making things up because it simply cannot "see" steps 4-10 anymore.

## The Solution

Give the model a `todo` tool that maintains a structured checklist. Then inject gentle reminders when the model goes too long without updating its plan.

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> | Tools   |
| prompt |      |       |      | + todo  |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                          |
              +-----------+-----------+
              | TodoManager state     |
              | [ ] task A            |
              | [>] task B  <- doing  |
              | [x] task C            |
              +-----------------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## How It Works

**Step 1.** TodoManager stores items with statuses. The "one `in_progress` at a time" constraint forces the model to finish what it started before moving on.

```python
class TodoManager:
    def update(self, items: list) -> str:
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress")
        self.items = validated
        return self.render()  # returns the checklist as formatted text
```

**Step 2.** The `todo` tool goes into the dispatch map like any other tool -- no special wiring needed, just one more entry in the dictionary you built in s02.

```python
TOOL_HANDLERS = {
    # ...base tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

**Step 3.** A nag reminder injects a nudge if the model goes 3+ rounds without calling `todo`. This is the write-back trick (feeding tool results back into the conversation) used for a new purpose: the harness (the code wrapping around the model) quietly inserts a reminder into the results payload before it is appended to messages.

```python
if rounds_since_todo >= 3:
    results.insert(0, {
        "type": "text",
        "text": "<reminder>Update your todos.</reminder>",
    })
messages.append({"role": "user", "content": results})
```

The "one in_progress at a time" constraint forces sequential focus. The nag reminder creates accountability. Together, they keep the model working through its plan instead of drifting.

## What Changed From s02

| Component      | Before (s02)     | After (s03)                |
|----------------|------------------|----------------------------|
| Tools          | 4                | 5 (+todo)                  |
| Planning       | None             | TodoManager with statuses  |
| Nag injection  | None             | `<reminder>` after 3 rounds|
| Agent loop     | Simple dispatch  | + rounds_since_todo counter|

## Try It

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`

Watch the model create a plan, work through it step by step, and check off items as it goes. If it forgets to update the plan for a few rounds, you will see the `<reminder>` nudge appear in the conversation.

## What You've Mastered

At this point, you can:

- Add session planning to any agent by dropping a `todo` tool into the dispatch map.
- Enforce sequential focus with the "one in_progress at a time" constraint.
- Use nag injection to pull the model back on track when it drifts.
- Explain why structured state beats free-form prose for multi-step plans.

Keep three boundaries in mind: `todo` here means "plan for the current conversation", not a durable task database. The tiny schema `{id, text, status}` is enough. A direct reminder is enough -- you do not need a sophisticated planning UI yet.

## What's Next

Your agent can now plan its work and stay on track. But every file it reads, every bash output it produces -- all of it stays in the conversation forever, eating into the context window. A five-file investigation might burn thousands of tokens (roughly word-sized pieces -- a 1000-line file uses about 4000 tokens) that the parent conversation never needs again. In s04, you will learn how to spin up subagents with fresh, isolated context -- so the parent stays clean and the model stays sharp.

## Key Takeaway

> Once the plan lives in structured state instead of free-form prose, the agent drifts much less.
