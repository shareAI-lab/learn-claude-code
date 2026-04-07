# s00a: Query Control Plane (查询控制平面)

> 这不是新的主线章节，而是一份桥接文档。  
> 它用来回答一个问题：
>
> **为什么一个结构更完整的 agent，不会只靠 `messages[]` 和一个 `while True` 就够了？**

## 这一篇为什么要存在

主线里的 `s01` 会先教你做出一个最小可运行循环：

```text
用户输入
  ->
模型回复
  ->
如果要调工具就执行
  ->
把结果喂回去
  ->
继续下一轮
```

这条主线是对的，而且必须先学这个。

但当系统开始长功能以后，真正支撑一个完整 harness 的，不再只是“循环”本身，而是：

**一层专门负责管理查询过程的控制平面。**

这一层在真实系统里通常会统一处理：

- 当前对话消息
- 当前轮次
- 为什么继续下一轮
- 是否正在恢复错误
- 是否已经压缩过上下文
- 是否需要切换输出预算
- hook 是否暂时影响了结束条件

如果不把这层讲出来，读者虽然能做出一个能跑的 demo，但很难自己把系统推到接近 95%-99% 的完成度。

## 先解释几个名词

### 什么是 query

这里的 `query` 不是“数据库查询”。

这里说的 query，更接近：

> 系统为了完成用户当前这一次请求，而运行的一整段主循环过程。

也就是说：

- 用户说一句话
- 系统可能要经过很多轮模型调用和工具调用
- 最后才结束这一次请求

这整段过程，就可以看成一条 query。

### 什么是控制平面

`控制平面` 这个词第一次看会有点抽象。

它的意思其实很简单：

> 不是直接做业务动作，而是负责协调、调度、决定流程怎么往下走的一层。

在这里：

- 模型回复内容，算“业务内容”
- 工具执行结果，算“业务动作”
- 决定“要不要继续下一轮、为什么继续、现在属于哪种继续”，这层就是控制平面

### 什么是 transition

`transition` 可以翻成“转移原因”。

它回答的是：

> 上一轮为什么没有结束，而是继续下一轮了？

例如：

- 因为工具刚执行完
- 因为输出被截断，要续写
- 因为刚做完压缩，要重试
- 因为 hook 要求继续
- 因为预算还允许继续

## 最小心智模型

先把 query 控制平面想成 3 层：

```text
1. 输入层
   - messages
   - system prompt
   - user/system context

2. 控制层
   - 当前状态 state
   - 当前轮 turn
   - 当前继续原因 transition
   - 恢复/压缩/预算等标记

3. 执行层
   - 调模型
   - 执行工具
   - 写回消息
```

它的工作不是“替代主循环”，而是：

**让主循环从一个小 demo，升级成一个能管理很多分支和状态的系统。**

## 为什么只靠 `messages[]` 不够

很多初学者第一次实现 agent 时，会把所有状态都堆进 `messages[]`。

这在最小 demo 里没问题。

但一旦系统长出下面这些能力，就不够了：

- 你要知道自己是不是已经做过一次 reactive compact
- 你要知道输出被截断已经续写了几次
- 你要知道这次继续是因为工具，还是因为错误恢复
- 你要知道当前轮是否启用了特殊输出预算

这些信息不是“对话内容”，而是“流程控制状态”。

所以它们不该都硬塞进 `messages[]` 里。

## 关键数据结构

### 1. QueryParams

这是进入 query 引擎时的外部输入。

最小形状可以这样理解：

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "fallback_model": None,
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

它的作用是：

- 带进来这次查询一开始已知的输入
- 这些值大多不在每轮里随便乱改

### 2. QueryState

这才是跨迭代真正会变化的部分。

最小教学版建议你把它显式做成一个结构：

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "continuation_count": 0,
    "has_attempted_compact": False,
    "max_output_tokens_override": None,
    "stop_hook_active": False,
    "turn_count": 1,
    "transition": None,
}
```

它的价值在于：

- 把“会变的流程状态”集中放在一起
- 让每个 continue site 修改的是同一份 state，而不是散落在很多局部变量里

### 3. TransitionReason

建议你单独定义一组继续原因：

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

这不是为了炫技。

它的作用很实在：

- 日志更清楚
- 调试更清楚
- 测试更清楚
- 教学更清楚

## 最小实现

### 第一步：把外部输入和内部状态分开

```python
def query(params):
    state = {
        "messages": params["messages"],
        "tool_use_context": params["tool_use_context"],
        "continuation_count": 0,
        "has_attempted_compact": False,
        "max_output_tokens_override": params.get("max_output_tokens_override"),
        "turn_count": 1,
        "transition": None,
    }
```

### 第二步：每一轮先读 state，再决定如何执行

```python
while True:
    messages = state["messages"]
    transition = state["transition"]
    turn_count = state["turn_count"]

    response = call_model(...)
    ...
```

### 第三步：所有“继续下一轮”的地方都写回 state

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["transition"] = "tool_result_continuation"
    state["turn_count"] += 1
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({"role": "user", "content": CONTINUE_MESSAGE})
    state["continuation_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

这一点非常关键。

**不要只做 `continue`，要知道自己为什么 continue。**

## 一张真正清楚的心智图

```text
params
  |
  v
init state
  |
  v
query loop
  |
  +-- normal assistant end --------------> terminal
  |
  +-- tool_use --------------------------> write tool_result -> transition=tool_result_continuation
  |
  +-- max_tokens ------------------------> inject continue -> transition=max_tokens_recovery
  |
  +-- prompt too long -------------------> compact -> transition=compact_retry
  |
  +-- transport error -------------------> backoff -> transition=transport_retry
  |
  +-- stop hook asks to continue --------> transition=stop_hook_continuation
```

## 它和 `s01`、`s11` 的关系

- `s01` 负责建立“最小主循环”
- `s11` 负责建立“错误恢复分支”
- 这一篇负责把两者再往上抽象一层，解释为什么一个更完整的系统会出现一个 query control plane

所以这篇不是替代主线，而是把主线补完整。

## 初学者最容易犯的错

### 1. 把所有控制状态都塞进消息里

这样日志和调试都会很难看，也会让消息层和控制层混在一起。

### 2. `continue` 了，但没有记录为什么继续

短期看起来没问题，系统一复杂就会变成黑盒。

### 3. 每个分支都直接改很多局部变量

这样后面你很难看出“哪些状态是跨轮共享的”。

### 4. 把 query loop 讲成“只是一个 while True”

这对最小 demo 是真话，对一个正在长出控制面的 harness 就不是完整真话了。

## 教学边界

这篇最重要的，不是把所有控制状态一次列满，而是先让你守住三件事：

- query loop 不只是 `while True`，而是一条带着共享状态往前推进的控制面
- 每次 `continue` 都应该有明确原因，而不是黑盒跳转
- 消息层、工具回写、压缩恢复、重试恢复，最终都要回到同一份 query 状态上

更细的 `transition taxonomy`、预算跟踪、prefetch 等扩展，可以放到你把这条最小控制面真正手搓稳定以后再补。

## 一句话记住

**更完整的 query loop 不只是“循环”，而是“拿着一份跨轮状态不断推进的查询控制平面”。**
