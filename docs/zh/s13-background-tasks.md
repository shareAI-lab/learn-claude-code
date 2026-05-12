# s13: Background Tasks (后台任务)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ] > s14 > s15 > s16 > s17 > s18 > s19`

> *慢命令可以在旁边等，主循环不必陪着发呆。*

## 这一章要解决什么问题

前面几章里，工具调用基本都是：

```text
模型发起
  ->
立刻执行
  ->
立刻返回结果
```

这对短命令没有问题。  
但一旦遇到这些慢操作，就会卡住：

- `npm install`
- `pytest`
- `docker build`
- 大型代码生成或检查任务

如果主循环一直同步等待，会出现两个坏处：

- 模型在等待期间什么都做不了
- 用户明明还想继续别的工作，却被整轮流程堵住

所以这一章要解决的是：

**把“慢执行”移到后台，让主循环继续推进别的事情。**

## 建议联读

- 如果你还没有彻底稳住“任务目标”和“执行槽位”是两层对象，先看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你开始分不清哪些状态该落在 `RuntimeTaskRecord`、哪些还应留在任务板，回看 [`data-structures.md`](./data-structures.md)。
- 如果你开始把后台执行理解成“另一条主循环”，先看 [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)，重新校正“并行的是执行与等待，不是主循环本身”。

## 先把几个词讲明白

### 什么叫前台

前台指的是：

> 主循环这轮发起以后，必须立刻等待结果的执行路径。

### 什么叫后台

后台不是神秘系统。  
后台只是说：

> 命令先在另一条执行线上跑，主循环先去做别的事。

### 什么叫通知队列

通知队列就是一条“稍后再告诉主循环”的收件箱。

后台任务完成以后，不是直接把全文硬塞回模型，  
而是先写一条摘要通知，等下一轮再统一带回去。

## 最小心智模型

这一章最关键的句子是：

**主循环仍然只有一条，并行的是等待，不是主循环本身。**

可以把结构画成这样：

```text
主循环
  |
  +-- background_run("pytest")
  |      -> 立刻返回 task_id
  |
  +-- 继续别的工作
  |
  +-- 下一轮模型调用前
         -> drain_notifications()
         -> 把摘要注入 messages

后台执行线
  |
  +-- 真正执行 pytest
  +-- 完成后写入通知队列
```

如果读者能牢牢记住这张图，后面扩展成更复杂的异步系统也不会乱。

## 关键数据结构

### 1. RuntimeTaskRecord

```python
task = {
    "id": "a1b2c3d4",
    "command": "pytest",
    "status": "running",
    "started_at": 1710000000.0,
    "result_preview": "",
    "output_file": "",
}
```

这些字段分别表示：

- `id`：唯一标识
- `command`：正在跑什么命令
- `status`：运行中、完成、失败、超时
- `started_at`：什么时候开始
- `result_preview`：先给模型看的简短摘要
- `output_file`：完整输出写到了哪里

教学版再往前走一步时，建议把它直接落成两份文件：

```text
.runtime-tasks/
  a1b2c3d4.json   # RuntimeTaskRecord
  a1b2c3d4.log    # 完整输出
```

这样读者会更容易理解：

- `json` 记录的是运行状态
- `log` 保存的是完整产物
- 通知只负责把 `preview` 带回主循环

### 2. Notification

```python
notification = {
    "type": "background_completed",
    "task_id": "a1b2c3d4",
    "status": "completed",
    "preview": "tests passed",
}
```

通知只负责做一件事：

> 告诉主循环“有结果回来了，你要不要看”。

它不是完整日志本体。

## 最小实现

### 第一步：登记后台任务

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self.notifications = []
        self.lock = threading.Lock()
```

这里最少要有两块状态：

- `tasks`：当前有哪些后台任务
- `notifications`：哪些结果已经回来，等待主循环领取

### 第二步：启动后台执行线

“线程”这个词第一次见可能会有点紧张。  
你可以先把它理解成：

> 同一个程序里，另一条可以独立往前跑的执行线。

```python
def run(self, command: str) -> str:
    task_id = new_id()
    self.tasks[task_id] = {
        "id": task_id,
        "command": command,
        "status": "running",
    }

    thread = threading.Thread(
        target=self._execute,
        args=(task_id, command),
        daemon=True,
    )
    thread.start()
    return task_id
```

这一步最重要的不是线程本身，而是：

**主循环拿到 `task_id` 后就可以先继续往前走。**

### 第三步：完成后写通知

```python
def _execute(self, task_id: str, command: str):
    try:
        result = subprocess.run(..., timeout=300)
        status = "completed"
        preview = (result.stdout + result.stderr)[:500]
    except subprocess.TimeoutExpired:
        status = "timeout"
        preview = "command timed out"

    with self.lock:
        self.tasks[task_id]["status"] = status
        self.notifications.append({
            "type": "background_completed",
            "task_id": task_id,
            "status": status,
            "preview": preview,
        })
```

这里体现的思想很重要：

**后台执行负责产出结果，通知队列负责把结果送回主循环。**

### 第四步：下一轮前排空通知

```python
def before_model_call(messages: list):
    notifications = bg.drain_notifications()
    if not notifications:
        return

    text = "\n".join(
        f"[bg:{n['task_id']}] {n['status']} - {n['preview']}"
        for n in notifications
    )
    messages.append({"role": "user", "content": text})
```

这样模型在下一轮就会知道：

- 哪个后台任务完成了
- 是成功、失败还是超时
- 如果要看全文，该再去读文件

## 为什么完整输出不要直接塞回 prompt

这是本章必须讲透的点。

如果后台任务输出几万行日志，你不能每次都把全文塞回上下文。  
更稳的做法是：

1. 完整输出写磁盘
2. 通知里只放简短摘要
3. 模型真的要看全文时，再调用 `read_file`

这背后的心智很重要：

**通知负责提醒，文件负责存原文。**

## 如何接到主循环里

从 `s13` 开始，主循环多出一个标准前置步骤：

```text
1. 先排空通知队列
2. 再调用模型
3. 普通工具照常同步执行
4. 如果模型调用 background_run，就登记后台任务并立刻返回 task_id
5. 下一轮再把后台结果带回模型
```

教学版最小工具建议先做两个：

- `background_run`
- `background_check`

这样已经足够支撑最小异步执行闭环。

## 这一章和任务系统的边界

这是本章最容易和 `s12` 混掉的地方。

### `s12` 的 task 是什么

`s12` 里的 `task` 是：

> 工作目标

它关心的是：

- 要做什么
- 谁依赖谁
- 现在总体进度如何

### `s13` 的 background task 是什么

本章里的后台任务是：

> 正在运行的执行单元

它关心的是：

- 哪个命令正在跑
- 跑到什么状态
- 结果什么时候回来

所以最稳的记法是：

- `task` 更像工作板
- `background task` 更像运行中的作业

两者相关，但不是同一个东西。

## 初学者最容易犯的错

### 1. 以为“后台”就是更复杂的主循环

不是。  
主循环仍然尽量保持单主线。

### 2. 只开线程，不登记状态

这样任务一多，你根本不知道：

- 谁还在跑
- 谁已经完成
- 谁失败了

### 3. 把长日志全文塞进上下文

上下文很快就会被撑爆。

### 4. 把 `s12` 的工作目标和本章的运行任务混为一谈

这会让后面多 agent 和调度章节全部打结。

## 教学边界

这一章只需要先把一个最小运行时模式讲清楚：

- 慢工作在后台跑
- 主循环继续保持单主线
- 结果通过通知路径在后面回到模型

只要这条模式稳了，线程池、更多 worker 类型、更复杂的事件系统都可以后补。

这章真正要让读者守住的是：

**并行的是等待与执行槽位，不是主循环本身。**

## 学完这一章，你应该真正掌握什么

学完以后，你应该能独立复述下面几句话：

1. 主循环只有一条，并行的是等待，不是主循环本身。
2. 后台任务至少需要“任务表 + 通知队列”两块状态。
3. `background_run` 应该立刻返回 `task_id`，而不是同步卡住。
4. 通知只放摘要，完整输出放文件。

如果这 4 句话都已经非常清楚，说明你已经掌握了后台任务系统的核心。

## 下一章学什么

这一章解决的是：

> 慢命令如何在后台运行。

下一章 `s14` 要解决的是：

> 如果连“启动后台任务”这件事都不一定由当前用户触发，而是由时间触发，该怎么做。

也就是从“异步运行”继续走向“定时触发”。
