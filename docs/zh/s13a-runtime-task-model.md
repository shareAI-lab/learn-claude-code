# s13a: Runtime Task Model (运行时任务模型)

> 这篇桥接文档专门解决一个非常容易混淆的问题：
>
> **任务板里的 task，和后台/队友/监控这些“正在运行的任务”，不是同一个东西。**

## 建议怎么联读

这篇最好夹在下面几份文档中间读：

- 先看 [`s12-task-system.md`](./s12-task-system.md)，确认工作图任务在讲什么。
- 再看 [`s13-background-tasks.md`](./s13-background-tasks.md)，确认后台执行在讲什么。
- 如果词开始混，再回 [`glossary.md`](./glossary.md)。
- 如果想把字段和状态彻底对上，再对照 [`data-structures.md`](./data-structures.md) 和 [`entity-map.md`](./entity-map.md)。

## 为什么必须单独讲这一篇

主线里：

- `s12` 讲的是任务系统
- `s13` 讲的是后台任务

这两章各自都没错。  
但如果不额外补一层桥接，很多读者很快就会把两种“任务”混在一起。

例如：

- 任务板里的 “实现 auth 模块”
- 后台执行里的 “正在跑 pytest”
- 队友执行里的 “alice 正在做代码改动”

这些都可以叫“任务”，但它们不在同一层。

为了让整个仓库接近满分，这一层必须讲透。

## 先解释两个完全不同的“任务”

### 第一种：工作图任务

这就是 `s12` 里的任务板节点。

它回答的是：

- 要做什么
- 谁依赖谁
- 谁认领了
- 当前进度如何

它更像：

> 工作计划中的一个可跟踪工作单元。

### 第二种：运行时任务

这类任务回答的是：

- 现在有什么执行单元正在跑
- 它是什么类型
- 是在运行、完成、失败还是被杀掉
- 输出文件在哪

它更像：

> 系统当前活着的一条执行槽位。

## 最小心智模型

你可以先把两者画成两张表：

```text
工作图任务
  - durable
  - 面向目标与依赖
  - 生命周期更长

运行时任务
  - runtime
  - 面向执行与输出
  - 生命周期更短
```

它们的关系不是“二选一”，而是：

```text
一个工作图任务
  可以派生
一个或多个运行时任务
```

例如：

```text
工作图任务：
  "实现 auth 模块"

运行时任务：
  1. 后台跑测试
  2. 启动一个 coder teammate
  3. 监控一个 MCP 服务返回结果
```

## 为什么这层区别非常重要

如果不区分这两层，后面很多章节都会开始缠在一起：

- `s13` 的后台任务会和 `s12` 的任务板混淆
- `s15-s17` 的队友任务会不知道该挂在哪
- `s18` 的 worktree 到底绑定哪一层任务，也会变模糊

所以你要先记住一句：

**工作图任务管“目标”，运行时任务管“执行”。**

## 关键数据结构

### 1. WorkGraphTaskRecord

这就是 `s12` 里的那条 durable task。

```python
task = {
    "id": 12,
    "subject": "Implement auth module",
    "status": "in_progress",
    "blockedBy": [],
    "blocks": [13],
    "owner": "alice",
    "worktree": "auth-refactor",
}
```

### 2. RuntimeTaskState

教学版可以先用这个最小形状：

```python
runtime_task = {
    "id": "b8k2m1qz",
    "type": "local_bash",
    "status": "running",
    "description": "Run pytest",
    "start_time": 1710000000.0,
    "end_time": None,
    "output_file": ".task_outputs/b8k2m1qz.txt",
    "notified": False,
}
```

这里的字段重点在于：

- `type`：它是什么执行单元
- `status`：它现在在运行态还是终态
- `output_file`：它的产出在哪
- `notified`：结果有没有回通知系统

### 3. RuntimeTaskType

你不必在教学版里一次性实现所有类型，  
但应该让读者知道“运行时任务”是一个类型族，而不只是 `background shell` 一种。

最小类型表可以先这样讲：

```text
local_bash
local_agent
remote_agent
in_process_teammate
monitor
workflow
```

## 最小实现

### 第一步：继续保留 `s12` 的任务板

这一层不要动。

### 第二步：单独加一个 RuntimeTaskManager

```python
class RuntimeTaskManager:
    def __init__(self):
        self.tasks = {}
```

### 第三步：后台运行时创建 runtime task

```python
def spawn_bash_task(command: str):
    task_id = new_runtime_id()
    runtime_tasks[task_id] = {
        "id": task_id,
        "type": "local_bash",
        "status": "running",
        "description": command,
    }
```

### 第四步：必要时把 runtime task 关联回工作图任务

```python
runtime_tasks[task_id]["work_graph_task_id"] = 12
```

这一步不是必须一上来就做，但如果系统进入多 agent / worktree 阶段，就会越来越重要。

## 一张真正清楚的图

```text
Work Graph
  task #12: Implement auth module
        |
        +-- spawns runtime task A: local_bash (pytest)
        +-- spawns runtime task B: local_agent (coder worker)
        +-- spawns runtime task C: monitor (watch service status)

Runtime Task Layer
  A/B/C each have:
  - own runtime ID
  - own status
  - own output
  - own lifecycle
```

## 它和后面章节怎么连

这层一旦讲清楚，后面几章会顺很多：

- `s13` 后台命令，本质上是 runtime task
- `s15-s17` 队友/agent，也可以看成 runtime task 的一种
- `s18` worktree 主要绑定工作图任务，但也会影响运行时执行环境
- `s19` 某些外部监控或异步调用，也可能落成 runtime task

所以后面只要你看到“有东西在后台活着并推进工作”，都可以先问自己两句：

- 它是不是某个 durable work graph task 派生出来的执行槽位。
- 它的状态是不是应该放在 runtime layer，而不是任务板节点里。

## 初学者最容易犯的错

### 1. 把后台 shell 直接写成任务板状态

这样 durable task 和 runtime state 就混在一起了。

### 2. 认为一个工作图任务只能对应一个运行时任务

现实里很常见的是一个工作目标派生多个执行单元。

### 3. 用同一套状态名描述两层对象

例如：

- 工作图任务的 `pending / in_progress / completed`
- 运行时任务的 `running / completed / failed / killed`

这两套状态最好不要混。

### 4. 忽略 output file 和 notified 这类运行时字段

工作图任务不太关心这些，运行时任务非常关心。

## 教学边界

这篇最重要的，不是把运行时字段一次加满，而是先把下面三层对象彻底拆开：

- durable task 是长期工作目标
- runtime task 是当前活着的执行槽位
- notification / output 只是运行时把结果带回来的通道

运行时任务类型枚举、增量输出 offset、槽位清理策略，都可以等你先把这三层边界手写清楚以后再扩展。

## 一句话记住

**工作图任务管“长期目标和依赖”，运行时任务管“当前活着的执行单元和输出”。**

**`s12` 的 task 是工作图节点，`s13+` 的 runtime task 是系统里真正跑起来的执行单元。**
