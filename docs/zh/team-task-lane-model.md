# Team Task Lane Model (队友-任务-车道模型)

> 到了 `s15-s18`，读者最容易混掉的，不是某个函数名，而是：
>
> **系统里到底是谁在工作、谁在协调、谁在记录目标、谁在提供执行目录。**

## 这篇桥接文档解决什么问题

如果你一路从 `s15` 看到 `s18`，脑子里很容易把下面这些词混在一起：

- teammate
- protocol request
- task
- runtime task
- worktree

它们都和“工作推进”有关。  
但它们不是同一层。

如果这层边界不单独讲清，后面读者会经常出现这些困惑：

- 队友是不是任务本身？
- `request_id` 和 `task_id` 有什么区别？
- worktree 是不是后台任务的一种？
- 一个任务完成了，为什么 worktree 还能保留？

这篇就是专门用来把这几层拆开的。

## 建议怎么联读

最推荐的读法是：

1. 先看 [`s15-agent-teams.md`](./s15-agent-teams.md)，确认长期队友在讲什么。
2. 再看 [`s16-team-protocols.md`](./s16-team-protocols.md)，确认请求-响应协议在讲什么。
3. 再看 [`s17-autonomous-agents.md`](./s17-autonomous-agents.md)，确认自治认领在讲什么。
4. 最后看 [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md)，确认隔离执行车道在讲什么。

如果你开始混：

- 回 [`entity-map.md`](./entity-map.md) 看模块边界。
- 回 [`data-structures.md`](./data-structures.md) 看记录结构。
- 回 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 看“目标任务”和“运行时执行槽位”的差别。

## 先给结论

先记住这一组最重要的区分：

```text
teammate
  = 谁在长期参与协作

protocol request
  = 团队内部一次需要被追踪的协调请求

task
  = 要做什么

runtime task / execution slot
  = 现在有什么执行单元正在跑

worktree
  = 在哪做，而且不和别人互相踩目录
```

这五层里，最容易混的是最后三层：

- `task`
- `runtime task`
- `worktree`

所以你必须反复问自己：

- 这是“目标”吗？
- 这是“执行中的东西”吗？
- 这是“执行目录”吗？

## 一张最小清晰图

```text
Team Layer
  teammate: alice (frontend)
  teammate: bob (backend)

Protocol Layer
  request_id=req_01
  kind=plan_approval
  status=pending

Work Graph Layer
  task_id=12
  subject="Implement login page"
  owner="alice"
  status="in_progress"

Runtime Layer
  runtime_id=rt_01
  type=in_process_teammate
  status=running

Execution Lane Layer
  worktree=login-page
  path=.worktrees/login-page
  status=active
```

你可以看到：

- `alice` 不是任务
- `request_id` 不是任务
- `runtime_id` 也不是任务
- `worktree` 更不是任务

真正表达“这件工作本身”的，只有 `task_id=12` 那层。

## 1. Teammate：谁在长期协作

这是 `s15` 开始建立的层。

它回答的是：

- 这个长期 worker 叫什么
- 它是什么角色
- 它当前是 working、idle 还是 shutdown
- 它有没有独立 inbox

最小例子：

```python
member = {
    "name": "alice",
    "role": "frontend",
    "status": "idle",
}
```

这层的核心不是“又多开一个 agent”。

而是：

> 系统开始有长期存在、可重复接活、可被点名协作的身份。

## 2. Protocol Request：谁在协调什么

这是 `s16` 建立的层。

它回答的是：

- 有谁向谁发起了一个需要追踪的请求
- 这条请求是什么类型
- 它现在是 pending、approved 还是 rejected

最小例子：

```python
request = {
    "request_id": "a1b2c3d4",
    "kind": "plan_approval",
    "from": "alice",
    "to": "lead",
    "status": "pending",
}
```

这一层不要和普通聊天混。

因为它不是“发一条消息就算完”，而是：

> 一条可以被继续更新、继续审核、继续恢复的协调记录。

## 3. Task：要做什么

这是 `s12` 的工作图任务，也是 `s17` 自治认领的对象。

它回答的是：

- 目标是什么
- 谁负责
- 是否有阻塞
- 当前进度如何

最小例子：

```python
task = {
    "id": 12,
    "subject": "Implement login page",
    "status": "in_progress",
    "owner": "alice",
    "blockedBy": [],
}
```

这层的关键词是：

**目标**

不是目录，不是协议，不是进程。

## 4. Runtime Task / Execution Slot：现在有什么执行单元在跑

这一层在 `s13` 的桥接文档里已经单独解释过，但到了 `s15-s18` 必须再提醒一次。

比如：

- 一个后台 shell 正在跑
- 一个长期 teammate 正在工作
- 一个 monitor 正在观察外部状态

这些都更像：

> 正在运行的执行槽位

而不是“任务目标本身”。

最小例子：

```python
runtime = {
    "id": "rt_01",
    "type": "in_process_teammate",
    "status": "running",
    "work_graph_task_id": 12,
}
```

这里最重要的边界是：

- 一个任务可以派生多个 runtime task
- 一个 runtime task 通常只是“如何执行”的一个实例

## 5. Worktree：在哪做

这是 `s18` 建立的执行车道层。

它回答的是：

- 这份工作在哪个独立目录里做
- 这条目录车道对应哪个任务
- 这条车道现在是 active、kept 还是 removed

最小例子：

```python
worktree = {
    "name": "login-page",
    "path": ".worktrees/login-page",
    "task_id": 12,
    "status": "active",
}
```

这层的关键词是：

**执行边界**

它不是工作目标本身，而是：

> 让这份工作在独立目录里推进的执行车道。

## 这五层怎么连起来

你可以把后段章节连成下面这条链：

```text
teammate
  通过 protocol request 协调
  认领 task
  作为一个 runtime execution slot 持续运行
  在某条 worktree lane 里改代码
```

如果写得更具体一点，会变成：

```text
alice (teammate)
  ->
收到或发起一个 request_id
  ->
认领 task #12
  ->
开始作为执行单元推进工作
  ->
进入 worktree "login-page"
  ->
在 .worktrees/login-page 里运行命令和改文件
```

## 一个最典型的混淆例子

很多读者会把这句话说成：

> “alice 就是在做 login-page 这个 worktree 任务。”

这句话把三层东西混成了一句：

- `alice`：队友
- `login-page`：worktree
- “任务”：工作图任务

更准确的说法应该是：

> `alice` 认领了 `task #12`，并在 `login-page` 这条 worktree 车道里推进它。

一旦你能稳定地这样表述，后面几章就不容易乱。

## 初学者最容易犯的错

### 1. 把 teammate 和 task 混成一个对象

队友是执行者，任务是目标。

### 2. 把 `request_id` 和 `task_id` 混成一个 ID

一个负责协调，一个负责工作目标，不是同一层。

### 3. 把 runtime slot 当成 durable task

运行时执行单元会结束，但 durable task 还可能继续存在。

### 4. 把 worktree 当成任务本身

worktree 只是执行目录边界，不是任务目标。

### 5. 只会讲“系统能并行”，却说不清每层对象各自负责什么

这是最常见也最危险的模糊表达。

真正清楚的教学，不是说“这里好多 agent 很厉害”，而是能把下面这句话讲稳：

> 队友负责长期协作，请求负责协调流程，任务负责表达目标，运行时槽位负责承载执行，worktree 负责隔离执行目录。

## 读完这篇你应该能自己说清楚

至少能完整说出下面这两句话：

1. `s17` 的自治认领，认领的是 `s12` 的工作图任务，不是 `s13` 的运行时槽位。
2. `s18` 的 worktree，绑定的是任务的执行车道，而不是把任务本身变成目录。

如果这两句你已经能稳定说清，`s15-s18` 这一大段主线就基本不会再拧巴了。
