# s18: Prompt Caching

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > [ s18 ] s19`

> *"Cache the stable prefix, pay for the delta"* -- reuse expensive context across API calls.
>
> **Harness layer**: Cost optimization -- cached tokens cost ~25% of uncached tokens.

## Problem

By s17, the harness is sophisticated. But every API call sends the full system prompt + all prior messages. A 50-turn conversation with a large system prompt means paying for the same tokens 50 times.

## Solution

```
Turn 1 (no cache):
System (cached) + History (cached) + New message
= [CREATION]  [CREATION]  [normal]

Turn 2 (cache hit):
System (cached) + History (cached) + New message
= [READ]      [READ]      [normal]

Cached tokens cost ~25% of uncached tokens.
```

## How It Works

1. **Mark stable blocks with cache_control.**

```python
system = [
    {
        "type": "text",
        "text": LARGE_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]
```

2. **Cache message prefix.** Early messages are stable; recent ones are not.

```python
def build_cached_messages(messages, cache_up_to=3):
    cached = []
    for i, msg in enumerate(messages):
        if i < cache_up_to:
            msg["content"] = [
                {"type": "text", "text": msg["content"],
                 "cache_control": {"type": "ephemeral"}}
            ]
        cached.append(msg)
    return cached
```

3. **Read cache stats from usage.**

```python
usage = response.usage
created = usage.cache_creation_input_tokens  # tokens written to cache
read    = usage.cache_read_input_tokens       # tokens read from cache
```

## Try It

```sh
cd learn-claude-code
python agents/s18_prompt_caching.py
```

Try these:

1. `/demo` -- run 3 turns and compare cache creation vs cache read
2. `/stats` -- show cumulative cache statistics
3. Any normal text -- chat with caching enabled
