# s12: Task System (任务系统)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > [ s12 ] > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *Todo 只能提醒你“有事要做”，任务系统才能告诉你“先做什么、谁在等谁、哪一步还卡着”。*

## 这一章要解决什么问题

`s03` 的 todo 已经能帮 agent 把大目标拆成几步。

但 todo 仍然有两个明显限制：

- 它更像当前会话里的临时清单
- 它不擅长表达“谁先谁后、谁依赖谁”

例如下面这组工作：

```text
1. 先写解析器
2. 再写语义检查
3. 测试和文档可以并行
4. 最后整体验收
```

这已经不是单纯的列表，而是一张“依赖关系图”。

如果没有专门的任务系统，agent 很容易出现这些问题：

- 前置工作没做完，就贸然开始后面的任务
- 某个任务完成以后，不知道解锁了谁
- 多个 agent 协作时，没有统一任务板可读

所以这一章要做的升级是：

**把“会话里的 todo”升级成“可持久化的任务图”。**

## 建议联读

- 如果你刚从 `s03` 过来，先回 [`data-structures.md`](./data-structures.md)，重新确认 `TodoItem / PlanState` 和 `TaskRecord` 不是同一层状态。
- 如果你开始把“对象边界”读混，先回 [`entity-map.md`](./entity-map.md)，把 message、task、runtime task、teammate 这几层拆开。
- 如果你准备继续读 `s13`，建议把 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 先放在手边，因为从这里开始最容易把 durable task 和 runtime task 混成一个词。

## 先把几个词讲明白

### 什么是任务

这里的 `task` 指的是：

> 一个可以被跟踪、被分配、被完成、被阻塞的小工作单元。

它不是整段用户需求，而是用户需求拆出来的一小块工作。

### 什么是依赖

依赖的意思是：

> 任务 B 必须等任务 A 完成，才能开始。

### 什么是任务图

任务图就是：

> 任务节点 + 依赖连线

你可以把它理解成：

- 点：每个任务
- 线：谁依赖谁

### 什么是 ready

`ready` 的意思很简单：

> 这条任务现在已经满足开工条件。

也就是：

- 自己还没开始
- 前置依赖已经全部完成

## 最小心智模型

本章最重要的，不是复杂调度算法，而是先回答 4 个问题：

1. 现在有哪些任务？
2. 每个任务是什么状态？
3. 哪些任务还被卡住？
4. 哪些任务已经可以开始？

只要这 4 个问题能稳定回答，一个最小任务系统就已经成立了。

## 关键数据结构

### 1. TaskRecord

```python
task = {
    "id": 1,
    "subject": "Write parser",
    "description": "",
    "status": "pending",
    "blockedBy": [],
    "blocks": [],
    "owner": "",
}
```

每个字段都对应一个很实用的问题：

- `id`：怎么唯一找到这条任务
- `subject`：这条任务一句话在做什么
- `description`：还有哪些补充说明
- `status`：现在走到哪一步
- `blockedBy`：还在等谁
- `blocks`：它完成后会解锁谁
- `owner`：现在由谁来做

### 2. TaskStatus

教学版先只保留最少 4 个状态：

```text
pending -> in_progress -> completed
deleted
```

解释如下：

- `pending`：还没开始
- `in_progress`：已经有人在做
- `completed`：已经做完
- `deleted`：逻辑删除，不再参与工作流

### 3. Ready Rule

这是本章最关键的一条判断规则：

```python
def is_ready(task: dict) -> bool:
    return task["status"] == "pending" and not task["blockedBy"]
```

如果你把这条规则讲明白，读者就会第一次真正明白：

**任务系统的核心不是“保存清单”，而是“判断什么时候能开工”。**

## 最小实现

### 第一步：让任务落盘

不要只把任务放在 `messages` 里。  
教学版最简单的做法，就是“一任务一文件”：

```text
.tasks/
  task_1.json
  task_2.json
  task_3.json
```

创建任务时，直接写成一条 JSON 记录：

```python
class TaskManager:
    def create(self, subject: str, description: str = "") -> dict:
        task = {
            "id": self._next_id(),
            "subject": subject,
            "description": description,
            "status": "pending",
            "blockedBy": [],
            "blocks": [],
            "owner": "",
        }
        self._save(task)
        return task
```

### 第二步：把依赖关系写成双向

如果任务 A 完成后会解锁任务 B，最好同时维护两边：

- A 的 `blocks` 里有 B
- B 的 `blockedBy` 里有 A

```python
def add_dependency(self, task_id: int, blocks_id: int):
    task = self._load(task_id)
    blocked = self._load(blocks_id)

    if blocks_id not in task["blocks"]:
        task["blocks"].append(blocks_id)
    if task_id not in blocked["blockedBy"]:
        blocked["blockedBy"].append(task_id)

    self._save(task)
    self._save(blocked)
```

这样做的好处是：

- 从前往后读得懂
- 从后往前也读得懂

### 第三步：完成任务时自动解锁后续任务

```python
def complete(self, task_id: int):
    task = self._load(task_id)
    task["status"] = "completed"
    self._save(task)

    for other in self._all_tasks():
        if task_id in other["blockedBy"]:
            other["blockedBy"].remove(task_id)
            self._save(other)
```

这一步非常关键。

因为它说明：

**任务系统不是静态记录表，而是会随着完成事件自动推进的工作图。**

### 第四步：把任务工具接给模型

教学版最小工具集建议先只做这 4 个：

- `task_create`
- `task_update`
- `task_get`
- `task_list`

这样模型就能：

- 新建任务
- 更新状态
- 看单条任务
- 看整张任务板

## 如何接到主循环里

从 `s12` 开始，主循环第一次拥有了“会话外状态”。

典型流程是：

```text
用户提出复杂目标
  ->
模型决定先拆任务
  ->
调用 task_create / task_update
  ->
任务落到 .tasks/
  ->
后续轮次继续读取并推进
```

这里要牢牢记住一句话：

**todo 更像本轮计划，task 更像长期工作板。**

## 这一章和 s03、s13 的边界

这一层边界必须讲清楚，不然后面一定会混。

### 和 `s03` 的区别

| 机制 | 更适合什么 |
|---|---|
| `todo` | 当前会话里快速列步骤 |
| `task` | 持久化工作、依赖关系、多人协作 |

如果只是“先看文件，再改代码，再跑测试”，todo 往往就够。  
如果是“跨很多轮、多人协作、还要管依赖”，就要上 task。

### 和 `s13` 的区别

本章的 `task` 指的是：

> 一条工作目标

它回答的是：

- 要做什么
- 现在做到哪一步
- 谁在等谁

它不是：

- 某个正在后台跑的 `pytest`
- 某个正在执行的 worker
- 某条当前活着的执行线程

后面这些属于下一章要讲的：

> 运行中的执行任务

## 初学者最容易犯的错

### 1. 只会创建任务，不会维护依赖

那最后得到的还是一张普通清单，不是任务图。

### 2. 任务只放内存，不落盘

系统一重启，整个工作结构就没了。

### 3. 完成任务后不自动解锁后续任务

这样系统永远不知道下一步谁可以开工。

### 4. 把工作目标和运行中的执行混成一层

这会导致后面 `s13` 的后台任务系统很难讲清。

## 教学边界

这一章先要守住的，不是任务平台以后还能长出多少管理功能，而是任务记录本身的最小主干：

- `TaskRecord`
- 依赖关系
- 持久化
- 就绪判断

只要读者已经能把 todo 和 task、工作目标和运行执行明确分开，并且能手写一个会解锁后续任务的最小任务图，这章就已经讲到位了。

## 学完这一章，你应该真正掌握什么

学完以后，你应该能独立说清这几件事：

1. 任务系统比 todo 多出来的核心能力，是“依赖关系”和“持久化”。
2. `TaskRecord` 是本章最关键的数据结构。
3. `blockedBy` / `blocks` 让系统能看懂前后关系。
4. `is_ready()` 让系统能判断“谁现在可以开始”。

如果这 4 件事都已经清楚，说明你已经能从 0 到 1 手写一个最小任务系统。

## 下一章学什么

这一章解决的是：

> 工作目标如何被长期组织。

下一章 `s13` 要解决的是：

> 某个慢命令正在后台跑时，主循环怎么继续前进。

也就是从“工作图”走向“运行时执行层”。
