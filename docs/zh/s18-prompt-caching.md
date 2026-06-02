# s18: Prompt Caching (提示词缓存)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > [ s18 ] s19`

> *"缓存稳定前缀,只为增量付费"* -- 跨 API 调用复用昂贵的上下文。
>
> **Harness 层**: 成本优化 -- 缓存 token 的费用约为未缓存 token 的 25%。

## 问题

s17 之后,harness 很精密。但每次 API 调用都发送完整的 system prompt + 所有历史消息。50 轮对话配合大型 system prompt 意味着为同样的 token 付费 50 次。

## 解决方案

```
第 1 轮 (无缓存):
System (创建缓存) + History (创建缓存) + 新消息
= [CREATION]  [CREATION]  [正常]

第 2 轮 (缓存命中):
System (缓存) + History (缓存) + 新消息
= [READ]      [READ]      [正常]

缓存 token 的费用约为未缓存 token 的 25%。
```

## 工作原理

1. **用 cache_control 标记稳定块。**

```python
system = [
    {
        "type": "text",
        "text": LARGE_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]
```

2. **缓存消息前缀。** 早期消息是稳定的,近期的不是。

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

3. **从 usage 读取缓存统计。**

```python
usage = response.usage
created = usage.cache_creation_input_tokens  # 写入缓存的 token
read    = usage.cache_read_input_tokens       # 从缓存读取的 token
```

## 试一试

```sh
cd learn-claude-code
python agents/s18_prompt_caching.py
```

试试这些:

1. `/demo` -- 运行 3 轮,对比缓存创建 vs 缓存读取
2. `/stats` -- 显示累计缓存统计
3. 普通文本 -- 开启缓存的对话
