# s10a: Message & Prompt Pipeline (消息与提示词管道)

> 这篇桥接文档是 `s10` 的扩展。  
> 它要补清一个很关键的心智：
>
> **system prompt 很重要，但它不是模型完整输入的全部。**

## 为什么要补这一篇

`s10` 已经把 system prompt 从“大字符串”升级成“可维护的组装流水线”，这一步非常重要。

但当系统开始长出更多输入来源时，还会继续往前走一步：

它会发现，真正送给模型的输入，不只包含：

- system prompt

还包含：

- 规范化后的 messages
- memory attachments
- hook 注入消息
- system reminder
- 当前轮次的动态上下文

也就是说，真正的输入更像一条完整管道：

**Prompt Pipeline，而不只是 Prompt Builder。**

## 先解释几个名词

### 什么是 prompt block

你可以把 `prompt block` 理解成：

> system prompt 内部的一段结构化片段。

例如：

- 核心身份说明
- 工具说明
- memory section
- CLAUDE.md section

### 什么是 normalized message

`normalized message` 的意思是：

> 把不同来源、不同格式的消息整理成统一、稳定、可发给模型的消息形式。

为什么需要这一步？

因为系统里可能出现：

- 普通用户消息
- assistant 回复
- tool_result
- 系统提醒
- attachment 包裹消息

如果不先整理，模型输入层会越来越乱。

### 什么是 system reminder

这在 `s10` 已经提到过。

它不是长期规则，而是：

> 只在当前轮或当前阶段临时追加的一小段系统信息。

## 最小心智模型

把完整输入先理解成下面这条流水线：

```text
多种输入来源
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
final api payload
```

这条图里最重要的不是“normalize”这个词有多高级，而是：

**所有来源先分清边界，再在最后一步统一整理。**

## system prompt 为什么不是全部

这是初学者非常容易混的一个点。

system prompt 适合放：

- 身份
- 规则
- 工具能力描述
- 长期说明

但有些东西不适合放进去：

- 这一轮刚发生的 tool_result
- 某个 hook 刚注入的补充说明
- 某条 memory attachment
- 当前临时提醒

这些更适合存在消息流里，而不是塞进 prompt block。

## 关键数据结构

### 1. SystemPromptBlock

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

最小教学版可以只理解成：

- 一段文本
- 可选的缓存信息

### 2. PromptParts

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

### 3. NormalizedMessage

```python
message = {
    "role": "user" | "assistant",
    "content": [...],
}
```

这里的 `content` 建议直接理解成“块列表”，而不是只是一段字符串。  
因为后面你会自然遇到：

- text block
- tool_use block
- tool_result block
- attachment-like block

### 4. ReminderMessage

```python
reminder = {
    "role": "system",
    "content": "Current mode: plan",
}
```

教学版里你不一定真的要用 `system` role 单独传，但心智上要区分：

- 这是长期 prompt block
- 还是当前轮临时 reminder

## 最小实现

### 第一步：继续保留 `SystemPromptBuilder`

这一步不能丢。

### 第二步：把消息输入做成独立管道

```python
def build_messages(raw_messages, attachments, reminders):
    messages = normalize_messages(raw_messages)
    messages = attach_memory(messages, attachments)
    messages = append_reminders(messages, reminders)
    return messages
```

### 第三步：在最后一层统一生成 API payload

```python
payload = {
    "system": build_system_prompt(),
    "messages": build_messages(...),
    "tools": build_tools(...),
}
```

这一步特别关键。

它会让读者明白：

**system prompt、messages、tools 是并列输入面，而不是互相替代。**

## 一张更完整但仍然容易理解的图

```text
Prompt Blocks
  - core
  - tools
  - memory
  - CLAUDE.md
  - dynamic context

Messages
  - user messages
  - assistant messages
  - tool_result messages
  - injected reminders

Attachments
  - memory attachment
  - hook attachment

          |
          v
   normalize + assemble
          |
          v
     final API payload
```

## 什么时候该放在 prompt，什么时候该放在 message

可以先记这个简单判断法：

### 更适合放在 prompt block

- 长期稳定规则
- 工具列表
- 长期身份说明
- CLAUDE.md

### 更适合放在 message 流

- 当前轮 tool_result
- 刚发生的提醒
- 当前轮追加的上下文
- 某次 hook 输出

### 更适合做 attachment

- 大块但可选的补充信息
- 需要按需展开的说明

## 初学者最容易犯的错

### 1. 把所有东西都塞进 system prompt

这样会让 prompt 越来越脏，也会模糊稳定信息和动态信息的边界。

### 2. 完全不做 normalize

随着消息来源增多，输入格式会越来越不稳定。

### 3. 把 memory、hook、tool_result 都当成一类东西

它们都能影响模型，但进入输入层的方式并不相同。

### 4. 忽略“临时 reminder”这一层

这会让很多本该只活一轮的信息，被错误地塞进长期 system prompt。

## 它和 `s10`、`s19` 的关系

- `s10` 讲 prompt builder
- 这篇讲 message + prompt 的完整输入管道
- `s19` 则会把 MCP 带来的额外说明和外部能力继续接入这条管道

也就是说：

**builder 是 prompt 的内部结构，pipeline 是模型输入的整体结构。**

## 教学边界

这篇最重要的，不是罗列所有输入来源，而是先把三条管线边界讲稳：

- 什么该进 system blocks
- 什么该进 normalized messages
- 什么只应该作为临时 reminder 或 attachment

只要这三层边界清楚，读者就已经能自己搭出一条可靠输入管道。  
更细的 cache scope、attachment 去重和大结果外置，都可以放到后续扩展里再补。

## 一句话记住

**真正送给模型的，不只是一个 prompt，而是“prompt blocks + normalized messages + attachments + reminders”组成的输入管道。**
