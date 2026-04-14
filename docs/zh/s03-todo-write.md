# s03: TodoWrite (会话内规划)

`s00 > s01 > s02 > [ s03 ] > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *计划不是替模型思考，而是把“正在做什么”明确写出来。*

## 这一章要解决什么问题

到了 `s02`，agent 已经会读文件、写文件、跑命令。

问题也马上出现了：

- 多步任务容易走一步忘一步
- 明明已经做过的检查，会重复再做
- 一口气列出很多步骤后，很快又回到即兴发挥

这是因为模型虽然“能想”，但它的当前注意力始终受上下文影响。  
如果没有一块**显式、稳定、可反复更新**的计划状态，大任务就很容易漂。

所以这一章要补上的，不是“更强的工具”，而是：

**让 agent 把当前会话里的计划外显出来，并且持续更新。**

## 先解释几个名词

### 什么是会话内规划

这里说的规划，不是长期项目管理，也不是磁盘上的任务系统。

它更像：

> 为了完成当前这次请求，先把接下来几步写出来，并在过程中不断更新。

### 什么是 todo

`todo` 在这一章里只是一个载体。

你不要把它理解成“某个特定产品里的某个工具名”，更应该把它理解成：

> 模型用来写入当前计划的一条入口。

### 什么是 active step

`active step` 可以理解成“当前正在做的那一步”。

教学版里我们用 `in_progress` 表示它。  
这么做的目的不是形式主义，而是帮助模型维持焦点：

> 同一时间，先把一件事做完，再进入下一件。

### 什么是提醒

提醒不是替模型规划，而是当它连续几轮都忘记更新计划时，轻轻拉它回来。

## 先立清边界：这章不是任务系统

这是这一章最重要的边界。

`s03` 讲的是：

- 当前会话里的轻量计划
- 用来帮助模型聚焦下一步
- 可以随任务推进不断改写

它**不是**：

- 持久化任务板
- 依赖图
- 多 agent 共用的工作图
- 后台运行时任务管理

这些会在 `s12-s14` 再系统展开。

如果你现在就把 `s03` 讲成完整任务平台，初学者会很快混淆：

- “当前这一步要做什么”
- “整个系统长期还有哪些工作项”

## 最小心智模型

把这一章先想成一个很简单的结构：

```text
用户提出大任务
   |
   v
模型先写一份当前计划
   |
   v
计划状态
  - [ ] 还没做
  - [>] 正在做
  - [x] 已完成
   |
   v
每做完一步，就更新计划
```

更具体一点：

```text
1. 先拆几步
2. 选一项作为当前 active step
3. 做完后标记 completed
4. 把下一项改成 in_progress
5. 如果好几轮没更新，系统提醒一下
```

这就是最小版本最该教清楚的部分。

## 关键数据结构

### 1. PlanItem

最小条目可以长这样：

```python
{
    "content": "Read the failing test",
    "status": "pending" | "in_progress" | "completed",
    "activeForm": "Reading the failing test",
}
```

这里的字段分别表示：

- `content`：这一步要做什么
- `status`：这一步现在处在什么状态
- `activeForm`：当它正在进行中时，可以用更自然的进行时描述

### 2. PlanningState

除了计划条目本身，还应该有一点最小运行状态：

```python
{
    "items": [...],
    "rounds_since_update": 0,
}
```

`rounds_since_update` 的意思很简单：

> 连续多少轮过去了，模型还没有更新这份计划。

### 3. 状态约束

教学版推荐先立一条简单规则：

```text
同一时间，最多一个 in_progress
```

这不是宇宙真理。  
它只是一个非常适合初学者的教学约束：

**强制模型聚焦当前一步。**

## 最小实现

### 第一步：准备一个计划管理器

```python
class TodoManager:
    def __init__(self):
        self.items = []
```

### 第二步：允许模型整体更新当前计划

```python
def update(self, items: list) -> str:
    validated = []
    in_progress_count = 0

    for item in items:
        status = item.get("status", "pending")
        if status == "in_progress":
            in_progress_count += 1
        validated.append({
            "content": item["content"],
            "status": status,
            "activeForm": item.get("activeForm", ""),
        })

    if in_progress_count > 1:
        raise ValueError("Only one item can be in_progress")

    self.items = validated
    return self.render()
```

教学版让模型“整份重写”当前计划，比做一堆局部增删改更容易理解。

### 第三步：把计划渲染成可读文本

```python
def render(self) -> str:
    lines = []
    for item in self.items:
        marker = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }[item["status"]]
        lines.append(f"{marker} {item['content']}")
    return "\n".join(lines)
```

### 第四步：把 `todo` 接成一个工具

```python
TOOL_HANDLERS = {
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "bash": run_bash,
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

### 第五步：如果连续几轮没更新计划，就提醒

```python
if rounds_since_update >= 3:
    results.insert(0, {
        "type": "text",
        "text": "<reminder>Refresh your plan before continuing.</reminder>",
    })
```

这一步的核心意义不是“催促”本身，而是：

> 系统开始把“计划状态是否失活”也看成主循环的一部分。

## 它如何接到主循环里

这一章以后，主循环不再只维护：

- `messages`

还开始维护一份额外的会话状态：

- `PlanningState`

也就是说，agent loop 现在不只是在“对话”。

它还在维持一块当前工作面板：

```text
messages          -> 模型看到的历史
planning state    -> 当前计划的显式外部状态
```

这就是这一章真正想让你学会的升级：

**把“当前要做什么”从模型脑内，移到系统可观察的状态里。**

## 为什么这章故意不讲成任务图

因为这里的重点是：

- 帮模型聚焦下一步
- 让当前进度变得外显
- 给主循环一个“过程性状态”

而不是：

- 任务依赖
- 长期持久化
- 多人协作任务板
- 后台运行槽位

如果你已经开始关心这些问题，说明你快进入：

- [`s12-task-system.md`](./s12-task-system.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## 初学者最容易犯的错

### 1. 把计划写得过长

计划不是越多越好。

如果一上来列十几步，模型很快就会失去维护意愿。

### 2. 不区分“当前一步”和“未来几步”

如果同时有很多个 `in_progress`，焦点就会散。

### 3. 把会话计划当成长期任务系统

这会让 `s03` 和 `s12` 的边界完全混掉。

### 4. 只在开始时写一次计划，后面从不更新

那这份计划就失去价值了。

### 5. 以为 reminder 是可有可无的小装饰

不是。

提醒机制说明了一件很重要的事：

> 主循环不仅要执行动作，还要维护动作过程中的结构化状态。

## 教学边界

这一章讲的是：

**会话里的外显计划状态。**

它还不是后面那种持久任务系统，所以边界要守住：

- 这里的 `todo` 只服务当前会话，不负责跨阶段持久化
- `{id, text, status}` 这种小结构已经够教会核心模式
- reminder 直接一点没问题，重点是让模型持续更新计划

这一章真正要让读者看见的是：

**当计划进入结构化状态，而不是散在自然语言里时，agent 的漂移会明显减少。**

## 一句话记住

**`s03` 的 todo，不是任务平台，而是当前会话里的“外显计划状态”。**
