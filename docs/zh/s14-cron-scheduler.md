# s14: Cron Scheduler (定时调度)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] > s15 > s16 > s17 > s18 > s19`

> *如果后台任务解决的是“稍后回来拿结果”，那么定时调度解决的是“将来某个时间再开始做事”。*

## 这一章要解决什么问题

`s13` 已经让系统学会了把慢命令放到后台。

但后台任务默认还是“现在就启动”。

很多真实需求并不是现在做，而是：

- 每天晚上跑一次测试
- 每周一早上生成报告
- 30 分钟后提醒我继续检查某个结果

如果没有调度能力，用户就只能每次手动再说一遍。  
这会让系统看起来像“只能响应当下”，而不是“能安排未来工作”。

所以这一章要加上的能力是：

**把一条未来要执行的意图，先记下来，等时间到了再触发。**

## 建议联读

- 如果你还没完全分清 `schedule`、`task`、`runtime task` 各自表示什么，先回 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你想重新看清“一条触发最终是怎样回到主循环里的”，可以配合读 [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md)。
- 如果你开始把“未来触发”误以为“又多了一套执行系统”，先回 [`data-structures.md`](./data-structures.md)，确认调度记录和运行时记录不是同一个表。

## 先解释几个名词

### 什么是调度器

调度器，就是一段专门负责“看时间、查任务、决定是否触发”的代码。

### 什么是 cron 表达式

`cron` 是一种很常见的定时写法。

最小 5 字段版本长这样：

```text
分 时 日 月 周
```

例如：

```text
*/5 * * * *   每 5 分钟
0 9 * * 1     每周一 9 点
30 14 * * *   每天 14:30
```

如果你是初学者，不用先背全。

这一章真正重要的不是语法细节，而是：

> “系统如何把一条未来任务记住，并在合适时刻放回主循环。”

### 什么是持久化调度

持久化，意思是：

> 就算程序重启，这条调度记录还在。

## 最小心智模型

先把调度看成 3 个部分：

```text
1. 调度记录
2. 定时检查器
3. 通知队列
```

它们之间的关系是：

```text
schedule_create(...)
  ->
把记录写到列表或文件里
  ->
后台检查器每分钟看一次“现在是否匹配”
  ->
如果匹配，就把 prompt 放进通知队列
  ->
主循环下一轮把它当成新的用户消息喂给模型
```

这条链路很重要。

因为它说明了一点：

**定时调度并不是另一套 agent。它最终还是回到同一条主循环。**

## 关键数据结构

### 1. ScheduleRecord

```python
schedule = {
    "id": "job_001",
    "cron": "0 9 * * 1",
    "prompt": "Run the weekly status report.",
    "recurring": True,
    "durable": True,
    "created_at": 1710000000.0,
    "last_fired_at": None,
}
```

字段含义：

- `id`：唯一编号
- `cron`：定时规则
- `prompt`：到点后要注入主循环的提示
- `recurring`：是不是反复触发
- `durable`：是否落盘保存
- `created_at`：创建时间
- `last_fired_at`：上次触发时间

### 2. 调度通知

```python
{
    "type": "scheduled_prompt",
    "schedule_id": "job_001",
    "prompt": "Run the weekly status report.",
}
```

### 3. 检查周期

教学版建议先按“分钟级”思考，而不是“秒级严格精度”。

因为大多数 cron 任务本来就不是为了卡秒执行。

## 最小实现

### 第一步：允许创建一条调度记录

```python
def create(self, cron_expr: str, prompt: str, recurring: bool = True):
    job = {
        "id": new_id(),
        "cron": cron_expr,
        "prompt": prompt,
        "recurring": recurring,
        "created_at": time.time(),
        "last_fired_at": None,
    }
    self.jobs.append(job)
    return job
```

### 第二步：写一个定时检查循环

```python
def check_loop(self):
    while True:
        now = datetime.now()
        self.check_jobs(now)
        time.sleep(60)
```

最小教学版先每分钟检查一次就足够。

### 第三步：时间到了就发通知

```python
def check_jobs(self, now):
    for job in self.jobs:
        if cron_matches(job["cron"], now):
            self.queue.put({
                "type": "scheduled_prompt",
                "schedule_id": job["id"],
                "prompt": job["prompt"],
            })
            job["last_fired_at"] = now.timestamp()
```

### 第四步：主循环像处理后台通知一样处理定时通知

```python
notifications = scheduler.drain()
for item in notifications:
    messages.append({
        "role": "user",
        "content": f"[scheduled:{item['schedule_id']}] {item['prompt']}",
    })
```

这样一来，定时任务最终还是由模型接手继续做。

## 为什么这章放在后台任务之后

因为这两章解决的问题很接近，但不是同一件事。

可以这样区分：

| 机制 | 回答的问题 |
|---|---|
| 后台任务 | “已经启动的慢操作，结果什么时候回来？” |
| 定时调度 | “一件事应该在未来什么时候开始？” |

这个顺序对初学者很友好。

因为先理解“异步结果回来”，再理解“未来触发一条新意图”，心智会更顺。

## 初学者最容易犯的错

### 1. 一上来沉迷 cron 语法细节

这章最容易跑偏到一大堆表达式规则。

但教学主线其实不是“背语法”，而是：

**调度记录如何进入通知队列，又如何回到主循环。**

### 2. 没有 `last_fired_at`

没有这个字段，系统很容易在短时间内重复触发同一条任务。

### 3. 只放内存，不支持落盘

如果用户希望“明天再提醒我”，程序一重启就没了，这就不是真正的调度。

### 4. 把调度触发结果直接在后台默默执行

教学主线里更清楚的做法是：

- 时间到了
- 先发通知
- 再让主循环决定怎么处理

这样系统行为更透明，读者也更容易理解。

### 5. 误以为定时任务必须绝对准点

很多初学者会把调度想成秒表。

但这里更重要的是“有计划地触发”，而不是追求毫秒级精度。

## 如何接到整个系统里

到了这一章，系统已经有两条重要的“外部事件输入”：

- 后台任务完成通知
- 定时调度触发通知

二者最好的统一方式是：

**都走通知队列，再在下一次模型调用前统一注入。**

这样主循环结构不会越来越乱。

## 教学边界

这一章先讲清一条主线就够了：

**调度器做的是“记住未来”，不是“取代主循环”。**

所以教学版先只需要让读者看清：

- schedule record 负责记住未来何时开工
- 真正执行工作时，仍然回到任务系统和通知队列
- 它只是多了一种“开始入口”，不是多了一条新的主循环

多进程锁、漏触发补报、自然语言时间语法这些，都应该排在这条主线之后。

## 试一试

```sh
cd learn-claude-code
python agents/s14_cron_scheduler.py
```

可以试试这些任务：

1. 建一个每分钟触发一次的小任务，观察它是否会按时进入通知队列。
2. 建一个只触发一次的任务，确认触发后是否会消失。
3. 重启程序，检查持久化的调度记录是否还在。

读完这一章，你应该能自己说清这句话：

**后台任务是在“等结果”，定时调度是在“等开始”。**
