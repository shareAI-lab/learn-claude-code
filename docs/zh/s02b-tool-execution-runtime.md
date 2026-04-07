# s02b: Tool Execution Runtime (工具执行运行时)

> 这篇桥接文档解决的不是“工具怎么注册”，而是：
>
> **当模型一口气发出多个工具调用时，系统到底按什么规则执行、并发、回写、合并上下文？**

## 这一篇为什么要存在

`s02` 先教你：

- 工具 schema
- dispatch map
- tool_result 回流

这完全正确。  
因为工具调用先得成立，后面才谈得上复杂度。

但系统一旦长大，真正棘手的问题会变成下面这些：

- 多个工具能不能并行执行
- 哪些工具必须串行
- 工具执行过程中要不要先发进度消息
- 并发工具的结果应该按完成顺序回写，还是按原始出现顺序回写
- 工具执行会不会改共享上下文
- 多个并发工具如果都要改上下文，最后怎么合并

这些问题已经不是“工具注册”能解释的了。

它们属于更深一层：

**工具执行运行时。**

## 先解释几个名词

### 什么叫工具执行运行时

这里的运行时，不是指编程语言 runtime。

这里说的是：

> 当工具真正开始执行时，系统用什么规则去调度、并发、跟踪和回写这些工具。

### 什么叫 concurrency safe

你可以先把它理解成：

> 这个工具能不能和别的同类工具同时跑，而不会把共享状态搞乱。

例如很多只读工具常常是 concurrency safe：

- `read_file`
- 某些搜索工具
- 某些纯查询类 MCP 工具

而很多写操作不是：

- `write_file`
- `edit_file`
- 某些会改全局状态的工具

### 什么叫 progress message

有些工具跑得慢，不适合一直静默。

progress message 就是：

> 工具还没结束，但系统先把“它正在做什么”告诉上层。

### 什么叫 context modifier

有些工具执行完不只是返回结果，还会修改共享环境。

例如：

- 更新通知队列
- 更新 app state
- 更新“哪些工具正在运行”

这种“对共享上下文的修改动作”，就可以理解成 context modifier。

## 最小心智模型

先不要把工具执行想成：

```text
tool_use -> handler -> result
```

更接近真实可扩展系统的理解是：

```text
tool_use blocks
  ->
按执行安全性分批
  ->
每批决定串行还是并行
  ->
执行过程中可能产出 progress
  ->
最终按稳定顺序回写结果
  ->
必要时再合并 context modifiers
```

这里最关键的升级点有两个：

- 并发不是默认全开
- 上下文修改不是谁先跑完谁先直接乱写

## 关键数据结构

### 1. ToolExecutionBatch

教学版最小可以先用这样一个概念：

```python
batch = {
    "is_concurrency_safe": True,
    "blocks": [tool_use_1, tool_use_2, tool_use_3],
}
```

它的意义是：

- 不是每个工具都单独处理
- 系统会先把工具调用按可否并发分成一批一批

### 2. TrackedTool

如果你准备把执行层做得更稳、更清楚，建议显式跟踪每个工具：

```python
tracked_tool = {
    "id": "toolu_01",
    "name": "read_file",
    "status": "queued",   # queued / executing / completed / yielded
    "is_concurrency_safe": True,
    "pending_progress": [],
    "results": [],
    "context_modifiers": [],
}
```

这类结构的价值很大。

因为系统终于开始能回答：

- 哪些工具还在排队
- 哪些已经开始
- 哪些已经完成
- 哪些已经先吐出了中间进度

### 3. MessageUpdate

工具执行过程中，不一定只有最终结果。

最小可以先理解成：

```python
update = {
    "message": maybe_message,
    "new_context": current_context,
}
```

更完整的执行层里，一个工具执行运行时往往会产出两类更新：

- 要立刻往上游发的消息更新
- 只影响内部共享环境的 context 更新

### 4. Queued Context Modifiers

这是最容易被忽略、但很关键的一层。

在并发工具批次里，更稳的策略不是“谁先完成谁先改 context”，而是：

> 先把 context modifier 暂存起来，最后按原始工具顺序统一合并。

最小理解方式：

```python
queued_context_modifiers = {
    "toolu_01": [modify_ctx_a],
    "toolu_02": [modify_ctx_b],
}
```

## 最小实现

### 第一步：先分清哪些工具能并发

```python
def is_concurrency_safe(tool_name: str, tool_input: dict) -> bool:
    return tool_name in {"read_file", "search_files"}
```

### 第二步：先分批，再执行

```python
batches = partition_tool_calls(tool_uses)

for batch in batches:
    if batch["is_concurrency_safe"]:
        run_concurrently(batch["blocks"])
    else:
        run_serially(batch["blocks"])
```

### 第三步：并发批次先吐进度，再收最终结果

```python
for update in run_concurrently(...):
    if update.get("message"):
        yield update["message"]
```

### 第四步：context modifier 不要乱序落地

```python
queued_modifiers = {}

for update in concurrent_updates:
    if update.get("context_modifier"):
        queued_modifiers[update["tool_id"]].append(update["context_modifier"])

for tool in original_batch_order:
    for modifier in queued_modifiers.get(tool["id"], []):
        context = modifier(context)
```

这一步是整篇里最容易被低估，但其实最接近真实系统开始长出执行运行时的点之一。

## 一张真正应该建立的图

```text
tool_use blocks
  |
  v
partition by concurrency safety
  |
  +-- read-only / safe batch -----> concurrent execution
  |                                   |
  |                                   +-- progress updates
  |                                   +-- final results
  |                                   +-- queued context modifiers
  |
  +-- exclusive batch ------------> serial execution
                                      |
                                      +-- direct result + direct context update
```

## 为什么这层比“dispatch map”更接近真实系统主脉络

最小 demo 里：

```python
handlers[tool_name](tool_input)
```

就够了。

但在更完整系统里，真正复杂的不是“找到 handler”。

真正复杂的是：

- 多工具之间如何共存
- 哪些能并发
- 并发时如何保证回写顺序稳定
- 并发时如何避免共享 context 被抢写
- 工具报错时是否中止其他工具

所以这层讲的不是边角优化，而是：

> 工具系统从“可调用”升级到“可调度”的关键一步。

## 它和前后章节怎么接

- `s02` 先教你工具为什么能被调用
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) 讲工具为什么会长成统一控制面
- 这篇继续讲，工具真的开始运行以后，系统如何调度它们
- `s07`、`s13`、`s19` 往后都还会继续用到这层心智

尤其是：

- 权限系统会影响工具能不能执行
- 后台任务会影响工具是否立即结束
- MCP / plugin 会让工具来源更多、执行形态更复杂

## 初学者最容易犯的错

### 1. 看到多个工具调用，就默认全部并发

这样很容易把共享状态搞乱。

### 2. 只按完成顺序回写结果

如果你完全按“谁先跑完谁先写”，主循环看到的顺序会越来越不稳定。

### 3. 并发工具直接同时改共享 context

这会制造很多很难解释的隐性状态问题。

### 4. 认为 progress message 是“可有可无的 UI 装饰”

它其实会影响：

- 上层何时知道工具还活着
- 长工具调用期间用户是否困惑
- streaming 执行体验是否稳定

### 5. 只讲工具 schema，不讲工具调度

这样读者最后只会“注册工具”，却不理解真实 agent 为什么还要长出工具执行运行时。

## 教学边界

这篇最重要的，不是把工具调度层一次讲成一个庞大 runtime，而是先让读者守住三件事：

- 工具调用要先分批，而不是默认看到多个 `tool_use` 就全部并发
- 并发执行和稳定回写是两件事，不应该混成一个动作
- 共享 context 的修改最好先排队，再按稳定顺序统一合并

只要这三条边界已经清楚，后面的权限、后台任务和 MCP 接入就都有地方挂。  
更细的队列模型、取消策略、流式输出协议，都可以放到你把这条最小运行时自己手搓出来以后再补。

## 读完这一篇你应该能说清楚

至少能完整说出这句话：

> 工具系统不只是 `tool_name -> handler`，它还需要一层执行运行时来决定哪些工具并发、哪些串行、结果如何回写、共享上下文如何稳定合并。

如果这句话你已经能稳定说清，那么你对 agent 工具层的理解，就已经比“会注册几个工具”深一大层了。
