# s10a: Message & Prompt Pipeline

> **Deep Dive** -- Best read alongside s10. It shows why the system prompt is only one piece of the model's full input.

### When to Read This

When you're working on prompt assembly and want to see the complete input pipeline.

---

> This bridge document extends `s10`.
>
> It exists to make one crucial idea explicit:
>
> **the system prompt matters, but it is not the whole model input.**

## Why This Document Exists

`s10` already upgrades the system prompt from one giant string into a maintainable assembly process.

That is important.

But a higher-completion system goes one step further and treats the whole model input as a pipeline made from multiple sources:

- system prompt blocks
- normalized messages
- memory attachments
- reminder injections
- dynamic runtime context

So the true structure is:

**a prompt pipeline, not only a prompt builder.**

## Terms First

### Prompt block

A structured piece inside the system prompt, such as:

- core identity
- tool instructions
- memory section
- CLAUDE.md section

### Normalized message

A message that has already been converted into a stable shape suitable for the model API.

This is necessary because the raw system may contain:

- user messages
- assistant replies
- tool results
- reminder injections
- attachment-like content

Normalization ensures all of these fit the same structural contract before they reach the API.

### System reminder

A small temporary instruction injected for the current turn or current mode.

Unlike a long-lived prompt block, a reminder is usually short-lived and situational -- for example, telling the model it is currently in "plan mode" or that a certain tool is temporarily unavailable.

## The Smallest Useful Mental Model

Think of the full input as a pipeline:

```text
multiple sources
  |
  +-- system prompt blocks
  +-- messages
  +-- attachments
  +-- reminders
  |
  v
normalize
  |
  v
final API payload
```

The key teaching point is:

**separate the sources first, then normalize them into one stable input.**

## Why System Prompt Is Not Everything

The system prompt is the right place for:

- identity
- stable rules
- long-lived constraints
- tool capability descriptions

But it is usually the wrong place for:

- the latest `tool_result`
- one-turn hook injections
- temporary reminders
- dynamic memory attachments

Those belong in the message stream or in adjacent input surfaces.

## Core Structures

### `SystemPromptBlock`

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

### `PromptParts`

```python
parts = {
    "core": "...",
    "tools": "...",
    "skills": "...",
    "memory": "...",
    "claude_md": "...",
    "dynamic": "...",
}
```

### `NormalizedMessage`

```python
message = {
    "role": "user" | "assistant",
    "content": [...],
}
```

Treat `content` as a list of blocks, not just one string.

### `ReminderMessage`

```python
reminder = {
    "role": "system",
    "content": "Current mode: plan",
}
```

Even if your teaching implementation does not literally use `role="system"` here, you should still keep the mental split:

- long-lived prompt block
- short-lived reminder

## Minimal Implementation Path

### 1. Keep a `SystemPromptBuilder`

Do not throw away the prompt-builder step.

### 2. Make messages a separate pipeline

```python
def build_messages(raw_messages, attachments, reminders):
    messages = normalize_messages(raw_messages)
    messages = attach_memory(messages, attachments)
    messages = append_reminders(messages, reminders)
    return messages
```

### 3. Assemble the final payload only at the end

```python
payload = {
    "system": build_system_prompt(),
    "messages": build_messages(...),
    "tools": build_tools(...),
}
```

This is the important mental upgrade:

**system prompt, messages, and tools are parallel input surfaces, not replacements for one another.**

## Key Takeaway

**The model input is a pipeline of sources that are normalized late, not one mystical prompt blob. System prompt, messages, and tools are parallel surfaces that converge only at send time.**
