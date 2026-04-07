# s11: Error Recovery (错误恢复)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > [ s11 ] > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *错误不是例外，而是主循环必须预留出来的一条正常分支。*

## 这一章要解决什么问题

到了 `s10`，你的 agent 已经有了：

- 主循环
- 工具调用
- 规划
- 上下文压缩
- 权限、hook、memory、system prompt

这时候系统已经不再是一个“只会聊天”的 demo，而是一个真的在做事的程序。

问题也随之出现：

- 模型输出写到一半被截断
- 上下文太长，请求直接失败
- 网络暂时抖动，API 超时或限流

如果没有恢复机制，主循环会在第一个错误上直接停住。  
这对初学者很危险，因为他们会误以为“agent 不稳定是模型的问题”。

实际上，很多失败并不是“任务真的失败了”，而只是：

**这一轮需要换一种继续方式。**

所以这一章的目标只有一个：

**把“报错就崩”升级成“先判断错误类型，再选择恢复路径”。**

## 建议联读

- 如果你开始分不清“为什么这一轮还在继续”，先回 [`s00c-query-transition-model.md`](./s00c-query-transition-model.md)，重新确认 transition reason 为什么是独立状态。
- 如果你在恢复逻辑里又把上下文压缩和错误恢复混成一团，建议顺手回看 [`s06-context-compact.md`](./s06-context-compact.md)，区分“为了缩上下文而压缩”和“因为失败而恢复”。
- 如果你准备继续往 `s12` 走，建议把 [`data-structures.md`](./data-structures.md) 放在旁边，因为后面任务系统会在“恢复状态之外”再引入新的 durable work 状态。

## 先解释几个名词

### 什么叫恢复

恢复，不是把所有错误都藏起来。

恢复的意思是：

- 先判断这是不是临时问题
- 如果是，就尝试一个有限次数的补救动作
- 如果补救失败，再把失败明确告诉用户

### 什么叫重试预算

重试预算，就是“最多试几次”。

比如：

- 续写最多 3 次
- 网络重连最多 3 次

如果没有这个预算，程序就可能无限循环。

### 什么叫状态机

状态机这个词听起来很大，其实意思很简单：

> 一个东西会在几个明确状态之间按规则切换。

在这一章里，主循环就从“普通执行”变成了：

- 正常执行
- 续写恢复
- 压缩恢复
- 退避重试
- 最终失败

## 最小心智模型

不要把错误恢复想得太神秘。

教学版只需要先区分 3 类问题：

```text
1. 输出被截断
   模型还没说完，但 token 用完了

2. 上下文太长
   请求装不进模型窗口了

3. 临时连接失败
   网络、超时、限流、服务抖动
```

对应 3 条恢复路径：

```text
LLM call
  |
  +-- stop_reason == "max_tokens"
  |      -> 注入续写提示
  |      -> 再试一次
  |
  +-- prompt too long
  |      -> 压缩旧上下文
  |      -> 再试一次
  |
  +-- timeout / rate limit / transient API error
         -> 等一会儿
         -> 再试一次
```

这就是最小但正确的恢复模型。

## 关键数据结构

### 1. 恢复状态

```python
recovery_state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

它的作用不是“记录一切”，而是：

- 防止无限重试
- 让每种恢复路径各算各的次数

### 2. 恢复决策

```python
{
    "kind": "continue" | "compact" | "backoff" | "fail",
    "reason": "why this branch was chosen",
}
```

把“错误长什么样”和“接下来怎么做”分开，会更清楚。

### 3. 续写提示

```python
CONTINUE_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped. "
    "Do not restart or repeat."
)
```

这条提示非常重要。

因为如果你只说“继续”，模型经常会：

- 重新总结
- 重新开头
- 重复已经输出过的内容

## 最小实现

先写一个恢复选择器：

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

再把它接进主循环：

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

    # 正常工具处理
```

注意这里的重点不是代码花哨，而是：

- 先分类
- 再选动作
- 每条动作有自己的预算

## 三条恢复路径分别在补什么洞

### 路径 1：输出被截断时，做续写

这个问题的本质不是“模型不会”，而是“这一轮输出空间不够”。

所以最小补法是：

1. 追加一条续写消息
2. 告诉模型不要重来，不要重复
3. 让主循环继续

```python
if response.stop_reason == "max_tokens":
    if state["continuation_attempts"] >= 3:
        return "Error: output recovery exhausted"
    state["continuation_attempts"] += 1
    messages.append({"role": "user", "content": CONTINUE_MESSAGE})
    continue
```

### 路径 2：上下文太长时，先压缩再重试

这里要先明确一点：

压缩不是“把历史删掉”，而是：

**把旧对话从原文，变成一份仍然可继续工作的摘要。**

最小压缩结果建议至少保留：

- 当前任务是什么
- 已经做了什么
- 关键决定是什么
- 下一步准备做什么

```python
def auto_compact(messages: list) -> list:
    summary = summarize_messages(messages)
    return [{
        "role": "user",
        "content": "This session was compacted. Continue from this summary:\n" + summary,
    }]
```

### 路径 3：连接抖动时，退避重试

“退避”这个词的意思是：

> 别立刻再打一次，而是等一小会儿再试。

为什么要等？

因为这类错误往往是临时拥堵：

- 刚超时
- 刚限流
- 服务器刚好抖了一下

如果你瞬间连续重打，只会更容易失败。

```python
def backoff_delay(attempt: int) -> float:
    return min(1.0 * (2 ** attempt), 30.0) + random.uniform(0, 1)
```

## 如何接到主循环里

最干净的接法，是把恢复逻辑放在两个位置：

### 位置 1：模型调用外层

负责处理：

- API 报错
- 网络错误
- 超时

### 位置 2：拿到 response 以后

负责处理：

- `stop_reason == "max_tokens"`
- 正常的 `tool_use`
- 正常的结束

也就是说，主循环现在不只是“调模型 -> 执行工具”，而是：

```text
1. 调模型
2. 如果调用报错，判断是否可以恢复
3. 如果拿到响应，判断是否被截断
4. 如果需要恢复，就修改 messages 或等待
5. 如果不需要恢复，再进入正常工具分支
```

## 初学者最容易犯的错

### 1. 把所有错误都当成一种错误

这样会导致：

- 该续写的去压缩
- 该等待的去重试
- 该失败的却无限拖延

### 2. 没有重试预算

没有预算，主循环就可能永远卡在“继续”“继续”“继续”。

### 3. 续写提示写得太模糊

只写一个“continue”通常不够。  
你要明确告诉模型：

- 不要重复
- 不要重新总结
- 直接从中断点接着写

### 4. 压缩后没有告诉模型“这是续场”

如果压缩后只给一份摘要，不告诉模型“这是前文摘要”，模型很可能重新向用户提问。

### 5. 恢复过程完全没有日志

教学系统最好打印类似：

- `[Recovery] continue`
- `[Recovery] compact`
- `[Recovery] backoff`

这样读者才看得见主循环到底做了什么。

## 这一章和前后章节怎么衔接

- `s06` 讲的是“什么时候该压缩”
- `s10` 讲的是“系统提示词怎么组装”
- `s11` 讲的是“当执行失败时，主循环怎么续下去”
- `s12` 开始，恢复机制会保护更长、更复杂的任务流

所以 `s11` 的位置非常关键。

它不是外围小功能，而是：

**把 agent 从“能跑”推进到“遇到问题也能继续跑”。**

## 教学边界

这一章先把 3 条最小恢复路径讲稳就够了：

- 输出截断后续写
- 上下文过长后压缩再试
- 请求抖动后退避重试

对教学主线来说，重点不是把所有“为什么继续下一轮”的原因一次讲全，而是先让读者明白：

**恢复不是简单 try/except，而是系统知道该怎么续下去。**

更大的 query 续行模型、预算续行、hook 介入这些内容，应该放回控制平面的桥接文档里看，而不是抢掉这章主线。

## 试一试

```sh
cd learn-claude-code
python agents/s11_error_recovery.py
```

可以试试这些任务：

1. 让模型生成一段特别长的内容，观察它是否会自动续写。
2. 连续读取一些大文件，观察上下文压缩是否会介入。
3. 临时制造一次请求失败，观察系统是否会退避重试。

读这一章时，你真正要记住的不是某个具体异常名，而是这条主线：

**错误先分类，恢复再执行，失败最后才暴露给用户。**
