# s17: Autonomous Agents (自治智能体)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] > s18 > s19`

> *一个团队真正开始“自己运转”，不是因为 agent 数量变多，而是因为空闲的队友会自己去找下一份工作。*

## 这一章要解决什么问题

到了 `s16`，团队已经有：

- 持久队友
- 邮箱
- 协议
- 任务板

但还有一个明显瓶颈：

**很多事情仍然要靠 lead 手动分配。**

例如任务板上已经有 10 条可做任务，如果还要 lead 一个个点名：

- Alice 做 1
- Bob 做 2
- Charlie 做 3

那团队规模一大，lead 就会变成瓶颈。

所以这一章要解决的核心问题是：

**让空闲队友自己扫描任务板，找到可做的任务并认领。**

## 建议联读

- 如果你开始把 teammate、task、runtime slot 三层一起讲糊，先回 [`team-task-lane-model.md`](./team-task-lane-model.md)。
- 如果你读到“auto-claim”时开始疑惑“活着的执行槽位”到底放在哪，继续看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你开始忘记“长期队友”和“一次性 subagent”最根本的区别，回看 [`entity-map.md`](./entity-map.md)。

## 先解释几个名词

### 什么叫自治

这里的自治，不是完全没人管。

这里说的自治是：

> 在提前给定规则的前提下，队友可以自己决定下一步接哪份工作。

### 什么叫认领

认领，就是把一条原本没人负责的任务，标记成“现在由我负责”。

### 什么叫空闲阶段

空闲阶段不是关机，也不是消失。

它表示：

> 这个队友当前手头没有活，但仍然活着，随时准备接新活。

## 最小心智模型

最清楚的理解方式，是把每个队友想成在两个阶段之间切换：

```text
WORK
  |
  | 当前轮工作做完，或者主动进入 idle
  v
IDLE
  |
  +-- 看邮箱，有新消息 -> 回到 WORK
  |
  +-- 看任务板，有 ready task -> 认领 -> 回到 WORK
  |
  +-- 长时间什么都没有 -> shutdown
```

这里的关键不是“让它永远不停想”，而是：

**空闲时，按规则检查两类新输入：邮箱和任务板。**

## 关键数据结构

### 1. Claimable Predicate

和 `s12` 一样，这里最重要的是：

**什么任务算“当前这个队友可以安全认领”的任务。**

在当前教学代码里，判定已经不是单纯看 `pending`，而是：

```python
def is_claimable_task(task: dict, role: str | None = None) -> bool:
    return (
        task.get("status") == "pending"
        and not task.get("owner")
        and not task.get("blockedBy")
        and _task_allows_role(task, role)
    )
```

这 4 个条件缺一不可：

- 任务还没开始
- 还没人认领
- 没有前置阻塞
- 当前队友角色满足认领策略

最后一条很关键。

因为现在任务可以带：

- `claim_role`
- `required_role`

例如：

```python
task = {
    "id": 7,
    "subject": "Implement login page",
    "status": "pending",
    "owner": "",
    "blockedBy": [],
    "claim_role": "frontend",
}
```

这表示：

> 这条任务不是“谁空着谁就拿”，而是要先过角色条件。

### 2. 认领后的任务记录

一旦认领成功，任务记录至少会发生这些变化：

```python
{
    "id": 7,
    "owner": "alice",
    "status": "in_progress",
    "claimed_at": 1710000000.0,
    "claim_source": "auto",
}
```

这里新增的两个字段很值得单独记住：

- `claimed_at`：什么时候被认领
- `claim_source`：这次认领是 `auto` 还是 `manual`

因为到这一步，系统开始不只是知道“任务现在有人做了”，还开始知道：

- 这是谁拿走的
- 是主动扫描拿走，还是手动点名拿走

### 3. Claim Event Log

除了回写任务文件，这章还会把认领动作追加到：

```text
.tasks/claim_events.jsonl
```

每条事件大致长这样：

```python
{
    "event": "task.claimed",
    "task_id": 7,
    "owner": "alice",
    "role": "frontend",
    "source": "auto",
    "ts": 1710000000.0,
}
```

为什么这层日志重要？

因为它回答的是“自治系统刚刚做了什么”。

只看最终任务文件，你知道的是：

- 现在是谁 owner

而看事件日志，你才能知道：

- 它是什么时候被拿走的
- 是谁拿走的
- 是空闲时自动拿走，还是人工调用 `claim_task`

### 4. Durable Request Record

这章虽然重点是自治，但它**不能从 `s16` 退回到“协议请求只放内存里”**。

所以当前代码里仍然保留了持久化请求记录：

```text
.team/requests/{request_id}.json
```

它保存的是：

- shutdown request
- plan approval request
- 对应的状态更新

这层边界很重要，因为自治队友并不是在“脱离协议系统另起炉灶”，而是：

> 在已有团队协议之上，额外获得“空闲时自己找活”的能力。

### 5. 身份块

当上下文被压缩后，队友有时会“忘记自己是谁”。

最小补法是重新注入一段身份提示：

```python
identity = {
    "role": "user",
    "content": "<identity>You are 'alice', role: frontend, team: default. Continue your work.</identity>",
}
```

当前实现里还会同时补一条很短的确认语：

```python
{"role": "assistant", "content": "I am alice. Continuing."}
```

这样做的目的不是好看，而是为了让恢复后的下一轮继续知道：

- 我是谁
- 我的角色是什么
- 我属于哪个团队

## 最小实现

### 第一步：让队友拥有 `WORK -> IDLE` 的循环

```python
while True:
    run_work_phase(...)
    should_resume = run_idle_phase(...)
    if not should_resume:
        break
```

### 第二步：在 IDLE 里先看邮箱

```python
def idle_phase(name: str, messages: list) -> bool:
    inbox = bus.read_inbox(name)
    if inbox:
        messages.append({
            "role": "user",
            "content": json.dumps(inbox),
        })
        return True
```

这一步的意思是：

如果有人明确找我，那我优先处理“明确发给我的工作”。

### 第三步：如果邮箱没消息，再按“当前角色”扫描可认领任务

```python
    unclaimed = scan_unclaimed_tasks(role)
    if unclaimed:
        task = unclaimed[0]
        claim_result = claim_task(
            task["id"],
            name,
            role=role,
            source="auto",
        )
```

这里当前代码有两个很关键的升级：

- `scan_unclaimed_tasks(role)` 不是无差别扫任务，而是带着角色过滤
- `claim_task(..., source="auto")` 会把“这次是自治认领”显式写进任务与事件日志

也就是说，自治不是“空闲了就乱抢一条”，而是：

> 按当前队友的角色、任务状态和阻塞关系，挑出一条真正允许它接手的工作。

### 第四步：认领后先补身份，再把任务提示塞回主循环

```python
        ensure_identity_context(messages, name, role, team_name)
        messages.append({
            "role": "user",
            "content": f"<auto-claimed>Task #{task['id']}: {task['subject']}</auto-claimed>",
        })
        messages.append({
            "role": "assistant",
            "content": f"{claim_result}. Working on it.",
        })
        return True
```

这一步非常关键。

因为“认领成功”本身还不等于“队友真的能顺利继续”。

还必须把两件事接回上下文里：

- 身份上下文
- 新任务提示

只有这样，下一轮 `WORK` 才不是无头苍蝇，而是：

> 带着明确身份和明确任务恢复工作。

### 第五步：长时间没事就退出

```python
    time.sleep(POLL_INTERVAL)
    ...
    return False
```

为什么需要这个退出路径？

因为空闲队友不一定要永远占着资源。  
教学版先做“空闲一段时间后关闭”就够了。

## 为什么认领必须是原子动作

“原子”这个词第一次看到可能不熟。

这里它的意思是：

> 认领这一步要么完整成功，要么不发生，不能一半成功一半失败。

为什么？

因为两个队友可能同时扫描到同一个可做任务。

如果没有锁，就可能发生：

- Alice 看见任务 3 没主人
- Bob 也看见任务 3 没主人
- 两人都把自己写成 owner

所以最小教学版也应该加一个认领锁：

```python
with claim_lock:
    task = load(task_id)
    if task["owner"]:
        return "already claimed"
    task["owner"] = name
    task["status"] = "in_progress"
    save(task)
```

## 身份重注入为什么重要

这是这章里一个很容易被忽视，但很关键的点。

当上下文压缩发生以后，队友可能丢掉这些关键信息：

- 我是谁
- 我的角色是什么
- 我属于哪个团队

如果没有这些信息，队友后续行为很容易漂。

所以一个很实用的做法是：

如果发现 messages 的开头已经没有身份块，就把身份块重新插回去。

这里你可以把它理解成一条恢复规则：

> 任何一次从 idle 恢复、或任何一次压缩后恢复，只要身份上下文可能变薄，就先补身份，再继续工作。

## 为什么 s17 不能从 s16 退回“内存协议”

这是一个很容易被漏讲，但其实非常重要的点。

很多人一看到“自治”，就容易只盯：

- idle
- auto-claim
- 轮询

然后忘了 `s16` 已经建立过的另一条主线：

- 请求必须可追踪
- 协议状态必须可恢复

所以现在教学代码里，像：

- shutdown request
- plan approval

仍然会写进：

```text
.team/requests/{request_id}.json
```

也就是说，`s17` 不是推翻 `s16`，而是在 `s16` 上继续加一条新能力：

```text
协议系统继续存在
  +
自治扫描与认领开始存在
```

这两条线一起存在，团队才会像一个真正的平台，而不是一堆各自乱跑的 worker。

## 如何接到前面几章里

这一章其实是前面几章第一次真正“串起来”的地方：

- `s12` 提供任务板
- `s15` 提供持久队友
- `s16` 提供结构化协议
- `s17` 则让队友在没有明确点名时，也能自己找活

所以你可以把 `s17` 理解成：

**从“被动协作”升级到“主动协作”。**

## 自治的是“长期队友”，不是“一次性 subagent”

这层边界如果不讲清，读者很容易把 `s04` 和 `s17` 混掉。

`s17` 里的自治执行者，仍然是 `s15` 那种长期队友：

- 有名字
- 有角色
- 有邮箱
- 有 idle 阶段
- 可以反复接活

它不是那种：

- 接一条子任务
- 做完返回摘要
- 然后立刻消失

的一次性 subagent。

同样地，这里认领的也是：

- `s12` 里的工作图任务

而不是：

- `s13` 里的后台执行槽位

所以这章其实是在两条已存在的主线上再往前推一步：

- 长期队友
- 工作图任务

再把它们用“自治认领”连接起来。

如果你开始把下面这些词混在一起：

- teammate
- protocol request
- task
- runtime task

建议回看：

- [`team-task-lane-model.md`](./team-task-lane-model.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## 初学者最容易犯的错

### 1. 只看 `pending`，不看 `blockedBy`

如果一个任务虽然是 `pending`，但前置任务还没完成，它就不应该被认领。

### 2. 只看状态，不看 `claim_role` / `required_role`

这会让错误的队友接走错误的任务。

教学版虽然简单，但从这一章开始，已经应该明确告诉读者：

- 并不是所有 ready task 都适合所有队友
- 角色条件本身也是 claim policy 的一部分

### 3. 没有认领锁

这会直接导致重复抢同一条任务。

### 4. 空闲阶段只轮询任务板，不看邮箱

这样队友会错过别人明确发给它的消息。

### 5. 认领了任务，但没有写 claim event

这样最后你只能看到“任务现在被谁做”，却看不到：

- 它是什么时候被拿走的
- 是自动认领还是手动认领

### 6. 队友永远不退出

教学版里，长时间无事可做时退出是合理的。  
否则读者会更难理解资源何时释放。

### 7. 上下文压缩后不重注入身份

这很容易让队友后面的行为越来越不像“它本来的角色”。

## 教学边界

这一章先只把自治主线讲清楚：

**空闲检查 -> 安全认领 -> 恢复工作。**

只要这条链路稳了，读者就已经真正理解了“自治”是什么。

更细的 claim policy、公平调度、事件驱动唤醒、长期保活，都应该建立在这条最小自治链之后，而不是抢在前面。

## 试一试

```sh
cd learn-claude-code
python agents/s17_autonomous_agents.py
```

可以试试这些任务：

1. 先建几条 ready task，再生成两个队友，观察它们是否会自动分工。
2. 建几条被阻塞的任务，确认队友不会错误认领。
3. 让某个队友进入 idle，再发一条消息给它，观察它是否会重新被唤醒。

这一章要建立的核心心智是：

**自治不是让 agent 乱跑，而是让它在清晰规则下自己接住下一份工作。**
