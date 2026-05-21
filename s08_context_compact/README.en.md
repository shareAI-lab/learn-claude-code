# s08: Context Compact — Context Will Fill Up, Have a Way to Make Room

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → s02 → s03 → s04 → s05 → s06 → s07 → `s08` → [s09](../s09_memory/) → s10 → ... → s20
> *"Context will fill up — have a way to make room"* — Four-layer compression pipeline: cheap first, expensive last.
>
> **Harness Layer**: Compression — clean memory, unlimited sessions.

---

## The Problem

The agent is running along, then freezes.

It has bash, read, write — all the capabilities it needs. But it read a 1000-line file (~4000 tokens), then read 30 more files, ran 20 commands. Every command's output, every file's contents, all pile up in the `messages` list.

The context window is finite. Once full, the API outright rejects the call: `prompt_too_long`.

Without compression, an agent simply cannot work on large projects.

---

## The Solution

![Compact Overview](images/compact-overview.en.svg)

The hook structure, skill loading, and sub-Agent from s07 are preserved, with some tools omitted to focus on compaction. The core change: insert three pre-processors (0 API calls) before each LLM call, trigger an LLM summary (1 API call) when tokens still exceed the threshold, and emergency-trim if the API throws an error.

Core design: cheap first, expensive last.

---

## How It Works

![Four-layer compression pipeline](images/compaction-layers.en.svg)

### L1: snip_compact — Trim Irrelevant Old Conversation

The agent ran 80 turns of conversation, accumulating 160 `messages`. The very first "help me create hello.py" is barely relevant to current work, yet it still occupies space.

Message count exceeds 50 → keep the first 3 (initial context) and the last 47 (current work), trim the middle:

```python
def snip_compact(messages, max_messages=50):
    if len(messages) <= max_messages:
        return messages
    keep_head, keep_tail = 3, max_messages - 3
    snipped = len(messages) - keep_head - keep_tail
    placeholder = {"role": "user",
                   "content": f"[snipped {snipped} messages from conversation middle]"}
    return messages[:keep_head] + [placeholder] + messages[-keep_tail:]
```

Entire messages are trimmed, but `tool_result` content within remaining messages keeps accumulating — message #34 may still hold 30KB of old file contents. → L2.

### L2: micro_compact — Placeholder for Old Tool Results

![Old results placeholder](images/micro-compact.en.svg)

The agent read 10 files consecutively. The full contents of reads 1–7 are still sitting in context, no longer needed, but hogging large amounts of space.

Keep only the 3 most recent `tool_result` entries intact; replace older ones with a one-line placeholder:

```python
KEEP_RECENT_TOOL_RESULTS = 3

def micro_compact(messages):
    tool_results = collect_tool_result_blocks(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS:
        return messages
    for _, _, block in tool_results[:-KEEP_RECENT_TOOL_RESULTS]:
        if len(block.get("content", "")) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
    return messages
```

Old results are cleared, but a single new result can be 500KB — one `cat` of a large file can max out the context. → L3.

### L3: tool_result_budget — Persist Large Results to Disk

![Large results to disk](images/layer1-budget.en.svg)

The model read 5 large files in one go; all `tool_result` blocks in the last user message total 500KB.

Sum the size of all `tool_result` blocks in the last user message. If over 200KB → sort by size, starting from the largest, persist to `.task_outputs/tool-results/`, keeping only a `<persisted-output>` marker + a 2000-character preview in context. The model sees the marker and knows the full content is on disk, re-reading it when needed.

```python
def tool_result_budget(messages, max_bytes=200_000):
    last = messages[-1]
    blocks = [(i, b) for i, b in enumerate(last["content"])
              if b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes:
        return messages
    ranked = sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True)
    for idx, block in ranked:
        if total <= max_bytes:
            break
        block["content"] = persist_large_output(block["tool_use_id"], str(block["content"]))
        total = recalculate_total(blocks)
    return messages
```

The first three layers are all plain-text / structural operations — 0 API calls — but they cannot "understand" conversation content. Context may still be too large. → L4.

### L4: compact_history — Full LLM Summary

![Full LLM summary](images/auto-compact.en.svg)

All three previous layers have run, but after 30 minutes of continuous work on a huge project, tokens still exceed the threshold.

Three-step process:

1. **Save transcript**: Write the full conversation to `.transcripts/` in JSONL format. The transcript preserves a recoverable record, but the model's active context only contains the summary. For the model's current reasoning, the details are no longer in context. The teaching code does not provide a transcript retrieval tool.
2. **LLM generates summary**: Send conversation history to the LLM, asking it to preserve key information: current goals, important findings, modified files, remaining work, user constraints, etc.
3. **Replace message list**: All old messages are replaced with a single summary. The teaching version only keeps the summary; the real Claude Code re-attaches some recent files, plans, agent/skill/tool context after compaction.

```python
def compact_history(messages):
    transcript_path = write_transcript(messages)  # Save full conversation first
    summary = summarize_history(messages)          # LLM generates summary
    return [{"role": "user",
             "content": f"[Compacted]\n\n{summary}"}]
```

**Circuit breaker**: After 3 consecutive failures, stop retrying to prevent an infinite loop wasting API calls.

### Reactive: reactive_compact

Sometimes the API still returns `prompt_too_long` (413) — when context grows faster than compression triggers.

This triggers **reactive_compact**: more aggressive than compact_history, it retreats from the tail, trimming to an API-acceptable size with byte-level precision, keeping only the last 5 messages + summary.

```python
def reactive_compact(messages):
    transcript = write_transcript(messages)
    summary = summarize_history(messages)
    tail = messages[-5:]
    return [{"role": "user",
             "content": f"[Reactive compact]\n\n{summary}"}, *tail]
```

Reactive compact has a retry limit (default 1). If it still fails, an exception is raised instead of looping forever. Full error recovery is deferred to s11.

### Putting It All Together

```python
def agent_loop(messages):
    reactive_retries = 0
    while True:
        # Three pre-processors (0 API calls)
        # Order: budget first, so large content is persisted before placeholders
        messages[:] = tool_result_budget(messages)    # L3: persist large results
        messages[:] = snip_compact(messages)          # L1: trim middle
        messages[:] = micro_compact(messages)         # L2: old result placeholders

        # Still too much? LLM summary (1 API call)
        if estimate_token_count(messages) > THRESHOLD:
            messages[:] = compact_history(messages)

        try:
            response = client.messages.create(...)
        except PromptTooLongError:
            if reactive_retries < MAX_REACTIVE_RETRIES:
                messages[:] = reactive_compact(messages)  # Emergency
                reactive_retries += 1
                continue
            raise  # retry limit exceeded, raise exception
        # ... tool execution ...

        # compact tool: when the model actively calls it, triggers compact_history
        if block.name == "compact":
            messages[:] = compact_history(messages)
            results.append({..., "content": "[Compacted. History summarized.]"})
            messages.append({"role": "user", "content": results})
            break  # end current turn, start fresh with compacted context
```

**The order must not be swapped.** L3 (budget) runs before L2 (micro) because micro replaces old large tool_results with one-line placeholders — budget must persist the full content before that happens. This is why CC source puts `applyToolResultBudget` first.

---

## Changes From s07

| Component | Before (s07) | After (s08) |
|-----------|-------------|-------------|
| Context management | None (context grows unbounded) | Four-layer compression pipeline + emergency |
| New functions | — | snip_compact, micro_compact, tool_result_budget, compact_history, reactive_compact |
| Tools | bash, read_file, write_file, edit_file, glob, todo_write, task, load_skill (8) | 8 + compact (9) |
| Loop | LLM call → tool execution | Three pre-processors before each turn + threshold-triggered compact_history |
| Design principle | — | Cheap first, expensive last |

---

## Try It

```sh
cd learn-claude-code
python s08_context_compact/code.py
```

Try these prompts:

1. `Read the file README.md, then read code.py, then read s01_agent_loop/README.md` (read multiple files consecutively, observe L2 compressing old results)
2. `Read every file in s08_context_compact/` (read a large amount of content at once, observe L3 persisting to disk)
3. Chat for 20+ turns, observe whether `[auto compact]` or `[reactive compact]` appears

What to watch for: After each tool execution, are old `tool_result` entries compressed? When tokens exceed the threshold after extended conversation, is summarization triggered automatically?

---

## What's Next

Context compression lets an agent run for a long time without crashing. But after each compression, the preferences and constraints the user told it are also lost. Can we let the agent selectively remember important things?

s09 Memory → three subsystems: choosing what to remember, extracting key information, consolidating and organizing. Across compressions, across sessions.

<details>
<summary>Deep Dive Into CC Source Code</summary>

> The following is based on analysis of CC source code `compact.ts`, `autoCompact.ts`, `microCompact.ts`, and `query.ts`.

### Execution Order Comparison

The teaching version labels layers L1/L2/L3/L4 for pedagogical clarity, but actual execution order does not match the numbering:

| Dimension | Teaching Version | Claude Code |
|-----------|-----------------|-------------|
| Execution order | budget → snip → micro → auto | budget → snip → micro → collapse → auto (`query.ts:379-468`) |
| snip_compact | Keep head 3 + tail 47 | CC only enables on main thread; implementation not in open-source repo (`HISTORY_SNIP` feature gate), but interface is visible: `snipCompactIfNeeded(messages)` → `{ messages, tokensFreed, boundaryMessage? }`, also exposes `SnipTool` for model-initiated snipping. Teaching version's 3/47 are simplified parameters |
| micro_compact | Text placeholder replacement | Two paths: time-based clears content directly, cached uses API `cache_edits` (legacy path removed) |
| micro_compact whitelist | By position (most recent 3) | time-based triggers by time threshold; cached triggers by count (`microCompact.ts`) |
| tool_result_budget | 200KB characters | 200,000 characters (`toolLimits.ts:49`) |
| compact_history threshold | Character count estimate | Precise tokens: `contextWindow - maxOutputTokens - 13_000` |
| Summary requirements | 5 categories of info | 9 sections + `<analysis>`/`<summary>` dual tags |
| Compression prompt | Simple prompt | Double-ended hard guardrails forbidding tool calls |
| PTL retry | Yes (simplified) | `truncateHeadForPTLRetry()` retreats by message groups (`compact.ts:243-290`) |
| Post-compaction recovery | None (teaching version only keeps summary) | Auto re-read recent files, plans, agent/skill/tool context |
| Circuit breaker | 3 times | 3 times (`autoCompact.ts:70`) |
| Reactive retry | 1 time | CC has more granular tiered retries |

### Execution Order Details

The real order in CC source `query.ts`:

1. `applyToolResultBudget` (L379): persist large results first, ensuring full content is saved
2. `snipCompact` (L403): trim middle messages
3. `microcompact` (L414): old result placeholders
4. `contextCollapse` (L441): independent context management system (not in teaching version)
5. `autoCompact` (L454): LLM full summary

The teaching version's budget → snip → micro order matches this. The teaching version does not have the contextCollapse mechanism.

### Full Constant Reference

| Constant | Value | Source File |
|----------|-------|-------------|
| `AUTOCOMPACT_BUFFER_TOKENS` | 13,000 | `autoCompact.ts:62` |
| `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | 3 | `autoCompact.ts:70` |
| `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | 20,000 | `autoCompact.ts:30` |
| `POST_COMPACT_TOKEN_BUDGET` | 50,000 | `compact.ts:123` |
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | 5 | `compact.ts:122` |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5,000 | `compact.ts:124` |
| Time micro_compact interval | 60 minutes | `timeBasedMCConfig.ts` |
| `MAX_COMPACT_STREAMING_RETRIES` | 2 | `compact.ts:131` |

### contextCollapse and sessionMemoryCompact

CC source code has two additional mechanisms not covered in this teaching version:

- **contextCollapse**: An independent context management system that, when enabled, suppresses proactive autocompact (`autoCompact.ts:215-222`), with collapse's commit/blocking flow taking over context management. Manual `/compact` and reactive fallback remain independent paths, unaffected by contextCollapse.
- **sessionMemoryCompact**: Before compact_history, CC first attempts a lightweight summary using existing session memory (covered in s09) without calling the LLM. This mechanism becomes clearer after learning s09.

### What Does the Compression Prompt Look Like?

CC's compression prompt has two hard requirements:

1. **Absolutely no tool calls**: It begins with `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.`, and appends another REMINDER at the end
2. **Analyze first, then summarize**: The model must first reason in an `<analysis>` tag, then output the formal summary in a `<summary>` tag. The analysis is stripped during formatting

### Teaching Version Simplifications Are Intentional

- micro_compact uses text placeholders → we don't have API-level `cache_edits` access
- Tokens estimated via character count → precise tokenizers are out of scope
- Post-compaction recovery omitted → teaching version only keeps summary, does not auto re-attach files
- Two auxiliary mechanisms not covered → they fall in the 10% detail category

The core design principle, cheap first, expensive last, is fully preserved.

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
