# s16: Team Protocols (团队协议)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] > s17 > s18 > s19`

> *有了邮箱以后，团队已经能说话；有了协议以后，团队才开始会“按规矩协作”。*

## 这一章要解决什么问题

`s15` 已经让队友之间可以互相发消息。

但如果所有事情都只靠自由文本，会有两个明显问题：

- 某些动作必须明确批准或拒绝，不能只靠一句模糊回复
- 一旦多个请求同时存在，系统很难知道“这条回复对应哪一件事”

最典型的两个场景就是：

1. 队友要不要优雅关机
2. 某个高风险计划要不要先审批

这两件事看起来不同，但结构其实一样：

```text
一方发请求
另一方明确回复
双方都能用同一个 request_id 对上号
```

所以这一章要加的，不是更多自由聊天，而是：

**一层结构化协议。**

## 建议联读

- 如果你开始把普通消息和协议请求混掉，先回 [`glossary.md`](./glossary.md) 和 [`entity-map.md`](./entity-map.md)。
- 如果你准备继续读 `s17` 和 `s18`，建议先看 [`team-task-lane-model.md`](./team-task-lane-model.md)，这样后面自治认领和 worktree 车道不会一下子缠在一起。
- 如果你想重新确认协议请求最终怎样回流到主系统，可以配合看 [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md)。

## 先把几个词讲明白

### 什么是协议

协议可以简单理解成：

> 双方提前约定好“消息长什么样、收到以后怎么处理”。

### 什么是 request_id

`request_id` 就是请求编号。

它的作用是：

- 某个请求发出去以后有一个唯一身份
- 之后的批准、拒绝、超时都能准确指向这一个请求

### 什么是请求-响应模式

这个词听起来像高级概念，其实很简单：

```text
请求方：我发起一件事
响应方：我明确回答同意还是不同意
```

本章做的，就是把这种模式从“口头表达”升级成“结构化数据”。

## 最小心智模型

从教学角度，你可以先把协议看成两层：

```text
1. 协议消息
2. 请求追踪表
```

### 协议消息

```python
{
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
}
```

### 请求追踪表

```python
requests = {
    "req_001": {
        "kind": "shutdown",
        "status": "pending",
    }
}
```

只要这两层都存在，系统就能同时回答：

- 现在发生了什么
- 这件事目前走到哪一步

## 关键数据结构

### 1. ProtocolEnvelope

```python
message = {
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
    "timestamp": 1710000000.0,
}
```

它比普通消息多出来的关键字段就是：

- `type`
- `request_id`
- `payload`

### 2. RequestRecord

```python
request = {
    "request_id": "req_001",
    "kind": "shutdown",
    "from": "lead",
    "to": "alice",
    "status": "pending",
}
```

它负责记录：

- 这是哪种请求
- 谁发给谁
- 当前状态是什么

如果你想把教学版再往真实系统推进一步，建议不要只放在内存字典里，而是直接落盘：

```text
.team/requests/
  req_001.json
  req_002.json
```

这样系统就能做到：

- 请求状态可恢复
- 协议过程可检查
- 即使主循环继续往前，请求记录也不会丢

### 3. 状态机

本章里的状态机非常简单：

```text
pending -> approved
pending -> rejected
pending -> expired
```

这里再次提醒读者：

`状态机` 的意思不是复杂理论，  
只是“状态之间如何变化的一张规则表”。

## 最小实现

### 协议 1：优雅关机

“优雅关机”的意思不是直接把线程硬砍掉。  
而是：

1. 先发关机请求
2. 队友明确回复同意或拒绝
3. 如果同意，先收尾，再退出

发请求：

```python
def request_shutdown(target: str):
    request_id = new_id()
    requests[request_id] = {
        "kind": "shutdown",
        "target": target,
        "status": "pending",
    }
    bus.send(
        "lead",
        target,
        msg_type="shutdown_request",
        extra={"request_id": request_id},
        content="Please shut down gracefully.",
    )
```

收响应：

```python
def handle_shutdown_response(request_id: str, approve: bool):
    record = requests[request_id]
    record["status"] = "approved" if approve else "rejected"
```

### 协议 2：计划审批

这其实还是同一个请求-响应模板。

比如某个队友想做高风险改动，可以先提计划：

```python
def submit_plan(name: str, plan_text: str):
    request_id = new_id()
    requests[request_id] = {
        "kind": "plan_approval",
        "from": name,
        "status": "pending",
        "plan": plan_text,
    }
    bus.send(
        name,
        "lead",
        msg_type="plan_approval",
        extra={"request_id": request_id, "plan": plan_text},
        content="Requesting review.",
    )
```

领导审批：

```python
def review_plan(request_id: str, approve: bool, feedback: str = ""):
    record = requests[request_id]
    record["status"] = "approved" if approve else "rejected"
    bus.send(
        "lead",
        record["from"],
        msg_type="plan_approval_response",
        extra={"request_id": request_id, "approve": approve},
        content=feedback,
    )
```

看到这里，读者应该开始意识到：

**本章最重要的不是“关机”或“计划”本身，而是同一个协议模板可以反复复用。**

## 协议请求不是普通消息

这一点一定要讲透。

邮箱里虽然都叫“消息”，但 `s16` 以后其实已经分成两类：

### 1. 普通消息

适合：

- 讨论
- 提醒
- 补充说明

### 2. 协议消息

适合：

- 审批
- 关机
- 交接
- 签收

它至少要带：

- `type`
- `request_id`
- `from`
- `to`
- `payload`

最简单的记法是：

- 普通消息解决“说了什么”
- 协议消息解决“这件事走到哪一步了”

## 如何接到团队系统里

这章真正补上的，不只是两个新工具名，而是一条新的协作回路：

```text
某个队友 / lead 发起请求
  ->
写入 RequestRecord
  ->
把 ProtocolEnvelope 投递进对方 inbox
  ->
对方下一轮 drain inbox
  ->
按 request_id 更新请求状态
  ->
必要时再回一条 response
  ->
请求方根据 approved / rejected 继续后续动作
```

你可以把它理解成：

- `s15` 给了团队“邮箱”
- `s16` 现在给邮箱里的某些消息加上“编号 + 状态机 + 回执”

如果少了这条结构化回路，团队虽然能沟通，但无法稳定协作。

## MessageEnvelope、ProtocolEnvelope、RequestRecord、TaskRecord 的边界

这 4 个对象很容易一起打结。最稳的记法是：

| 对象 | 它回答什么问题 | 典型字段 |
|---|---|---|
| `MessageEnvelope` | 谁跟谁说了什么 | `from` / `to` / `content` |
| `ProtocolEnvelope` | 这是不是一条结构化请求或响应 | `type` / `request_id` / `payload` |
| `RequestRecord` | 这件协作流程现在走到哪一步 | `kind` / `status` / `from` / `to` |
| `TaskRecord` | 真正的工作项是什么、谁在做、还卡着谁 | `subject` / `status` / `blockedBy` / `owner` |

一定要牢牢记住：

- 协议请求不是任务本身
- 请求状态表也不是任务板
- 协议只负责“协作流程”
- 任务系统才负责“真正的工作推进”

## 这一章的教学边界

教学版先只讲 2 类协议就够了：

- `shutdown`
- `plan_approval`

因为这两类已经足够把下面几件事讲清楚：

- 什么是结构化消息
- 什么是 request_id
- 为什么要有请求状态表
- 为什么协议不是自由文本

等这套模板学稳以后，你完全可以再扩展：

- 任务认领协议
- 交接协议
- 结果签收协议

但这些都应该建立在本章的统一模板之上。

## 初学者最容易犯的错

### 1. 没有 `request_id`

没有编号，多个请求同时存在时很快就会乱。

### 2. 收到请求以后只回一句自然语言

例如：

```text
好的，我知道了
```

人类可能看得懂，但系统很难稳定处理。

### 3. 没有请求状态表

如果系统不记录 `pending` / `approved` / `rejected`，协议其实就没有真正落地。

### 4. 把协议消息和普通消息混成一种结构

这样后面一多，处理逻辑会越来越混。

## 学完这一章，你应该真正掌握什么

学完以后，你应该能独立复述下面几件事：

1. 团队协议的核心，是“请求-响应 + request_id + 状态表”。
2. 协议消息和普通聊天消息不是一回事。
3. 关机协议和计划审批虽然业务不同，但底层模板可以复用。
4. 团队一旦进入结构化协作，就要靠协议，而不是只靠自然语言。

如果这 4 点已经非常稳定，说明这一章真正学到了。

## 下一章学什么

这一章解决的是：

> 团队如何按规则协作。

下一章 `s17` 要解决的是：

> 如果没有人每次都手动派活，队友能不能在空闲时自己找任务、自己恢复工作。

也就是从“协议化协作”继续走向“自治行为”。
