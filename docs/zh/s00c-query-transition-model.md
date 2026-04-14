# s00c: Query Transition Model (查询转移模型)

> 这篇桥接文档专门解决一个问题：
>
> **为什么一个只会 `continue` 的 agent，不足以支撑完整系统，而必须显式知道“为什么继续到下一轮”？**

## 这一篇为什么要存在

主线里：

- `s01` 先教你最小循环
- `s06` 开始教上下文压缩
- `s11` 开始教错误恢复

这些都对。  
但如果你只分别学这几章，脑子里很容易还是停留在一种过于粗糙的理解：

> “反正 `continue` 了就继续呗。”

这在最小 demo 里能跑。  
但当系统开始长出恢复、压缩和外部控制以后，这样理解会很快失灵。

因为系统继续下一轮的原因其实很多，而且这些原因不是一回事：

- 工具刚执行完，要把结果喂回模型
- 输出被截断了，要续写
- 上下文刚压缩完，要重试
- 运输层刚超时了，要退避后重试
- stop hook 要求当前 turn 先不要结束
- token budget 还允许继续推进

如果你不把这些“继续原因”从一开始拆开，后面会出现三个大问题：

- 日志看不清
- 测试不好写
- 教学心智会越来越模糊

## 先解释几个名词

### 什么叫 transition

这里的 `transition`，你可以先把它理解成：

> 上一轮为什么转移到了下一轮。

它不是“消息内容”，而是“流程原因”。

### 什么叫 continuation

continuation 就是：

> 这条 query 当前还没有结束，要继续推进。

但 continuation 不止一种。

### 什么叫 query boundary

query boundary 就是一轮和下一轮之间的边界。

每次跨过这个边界，系统最好都知道：

- 这次为什么继续
- 这次继续前有没有修改状态
- 这次继续后应该怎么读主循环

## 最小心智模型

先不要把 query 想成一条线。

更接近真实情况的理解是：

```text
一条 query
  = 一组“继续原因”串起来的状态转移
```

例如：

```text
用户输入
  ->
模型产生 tool_use
  ->
工具执行完
  ->
tool_result_continuation
  ->
模型输出过长
  ->
max_tokens_recovery
  ->
压缩后继续
  ->
compact_retry
  ->
最终结束
```

这样看，你会更容易理解：

**系统不是单纯在 while loop 里转圈，而是在一串显式的转移原因里推进。**

## 关键数据结构

### 1. QueryState 里的 `transition`

最小版建议就把这类字段显式放进状态里：

```python
state = {
    "messages": [...],
    "turn_count": 3,
    "has_attempted_compact": False,
    "continuation_count": 1,
    "transition": None,
}
```

这里的 `transition` 不是可有可无。

它的意义是：

- 当前这轮为什么会出现
- 下一轮日志应该怎么解释
- 测试时应该断言哪条路径被走到

### 2. TransitionReason

教学版最小可以先这样分：

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "transport_retry",
    "stop_hook_continuation",
    "budget_continuation",
)
```

这几种原因的本质不一样：

- `tool_result_continuation`
  是正常主线继续
- `max_tokens_recovery`
  是输出被截断后的恢复继续
- `compact_retry`
  是上下文处理后的恢复继续
- `transport_retry`
  是基础设施抖动后的恢复继续
- `stop_hook_continuation`
  是外部控制逻辑阻止本轮结束
- `budget_continuation`
  是系统主动利用预算继续推进

### 3. Continuation Budget

更完整的 query 状态不只会说“继续”，还会限制：

- 最多续写几次
- 最多压缩后重试几次
- 某类恢复是不是已经尝试过

例如：

```python
state = {
    "max_output_tokens_recovery_count": 2,
    "has_attempted_reactive_compact": True,
}
```

这些字段的本质都是：

> continuation 不是无限制的。

## 最小实现

### 第一步：把 continue site 显式化

很多初学者写主循环时，所有继续逻辑都长这样：

```python
continue
```

教学版应该往前走一步：

```python
state["transition"] = "tool_result_continuation"
continue
```

### 第二步：不同继续原因，配不同状态修改

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["turn_count"] += 1
    state["transition"] = "tool_result_continuation"
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({
        "role": "user",
        "content": CONTINUE_MESSAGE,
    })
    state["max_output_tokens_recovery_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

重点不是“多写一行”。

重点是：

**每次继续之前，你都要知道自己做了什么状态更新，以及为什么继续。**

### 第三步：把恢复继续和正常继续分开

```python
if should_retry_transport(error):
    time.sleep(backoff(...))
    state["transition"] = "transport_retry"
    continue

if should_recompact(error):
    state["messages"] = compact_messages(state["messages"])
    state["transition"] = "compact_retry"
    continue
```

这时候你就开始得到一条非常清楚的控制链：

```text
继续
  不再是一个动作
  而是一类带原因的转移
```

## 一张真正应该建立的图

```text
query loop
  |
  +-- tool executed --------------------> transition = tool_result_continuation
  |
  +-- output truncated -----------------> transition = max_tokens_recovery
  |
  +-- compact just happened -----------> transition = compact_retry
  |
  +-- network / transport retry -------> transition = transport_retry
  |
  +-- stop hook blocked termination ---> transition = stop_hook_continuation
  |
  +-- budget says keep going ----------> transition = budget_continuation
```

## 它和逆向仓库主脉络为什么对得上

如果你去看更完整系统的查询入口，会发现它真正难的地方从来不是：

- 再调一次模型

而是：

- 什么时候该继续
- 继续前改哪份状态
- 继续属于哪一种路径

所以这篇桥接文档讲的，不是额外装饰，而是完整 query engine 的主骨架之一。

## 它和主线章节怎么接

- `s01` 让你先把 loop 跑起来
- `s06` 让你知道为什么上下文管理会介入继续路径
- `s11` 让你知道为什么恢复路径不是一种
- 这篇则把“继续原因”统一抬成显式状态

所以你可以把它理解成：

> 给前后几章之间补上一条“为什么继续”的统一主线。

## 初学者最容易犯的错

### 1. 只有 `continue`，没有 `transition`

这样日志和测试都会越来越难看。

### 2. 把所有继续都当成一种

这样会把：

- 正常主线继续
- 错误恢复继续
- 压缩后重试

全部混成一锅。

### 3. 没有 continuation budget

没有预算，系统就会在某些坏路径里无限试下去。

### 4. 把 `transition` 写进消息文本，而不是流程状态

消息是给模型看的。  
`transition` 是给系统自己看的。

### 5. 压缩、恢复、hook 都发生了，却没有统一的查询状态

这会导致控制逻辑散落在很多局部变量里，越长越乱。

## 教学边界

这篇最重要的，不是一次枚举完所有 transition 名字，而是先让你守住三件事：

- `continue` 最好总能对应一个显式的 `transition reason`
- 正常继续、恢复继续、压缩后重试，不应该被混成同一种路径
- continuation 需要预算和状态，而不是无限重来

只要这三点成立，你就已经能把 `s01 / s06 / s11` 真正串成一条完整主线。  
更细的 transition taxonomy、预算策略和日志分类，可以放到你把最小 query 状态机写稳以后再补。

## 读完这一篇你应该能说清楚

至少能完整说出这句话：

> 一条 query 不是简单 while loop，而是一串显式 continuation reason 驱动的状态转移。

如果这句话你已经能稳定说清，那么你再回头看 `s11`、`s19`，心智会顺很多。
