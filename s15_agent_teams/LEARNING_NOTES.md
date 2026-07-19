# s15 Agent Teams 学习笔记

## 本节核心

s15 引入 Agent Teams，解决一个 Agent 的上下文和注意力难以同时覆盖大型任务所有模块的问题。

s06 的子 Agent 更像一次性临时工：收到任务、独立完成、返回结论。s15 的队友则拥有自己的线程、对话历史和工具集，还能通过文件收件箱继续交换消息。

本节新增三个核心机制：

- `MessageBus`：使用 `.mailboxes/*.jsonl` 收发消息。
- `spawn_teammate_thread()`：在独立 daemon 线程中运行队友。
- inbox 注入：Lead 将队友消息放回自己的 `history`。

完整主线是：

```text
Lead 调用 spawn_teammate
-> 初始 prompt 进入队友 messages
-> 队友独立调用 LLM 和工具
-> 队友提取最终 summary
-> MessageBus 写入 Lead inbox
-> Lead 通过外层检查或 check_inbox 读取
-> 消息进入 Lead history
```

核心目标是：**用独立上下文承载不同任务，再用显式消息连接必要信息。**

## 你的回答评价

整体掌握程度约为 **78%**。你已经理解队友与子 Agent 的区别、消费式邮箱，以及 `for ... else` 的基本控制流。接下来重点修正初始任务入口、inbox 触发时机和文件并发风险。

### 问题 1：完整数据流

你正确描述了“Alice 完成任务 → summary 发给 Lead inbox → Lead 读取并注入历史”。需要纠正的是：Alice 刚启动时不是先从 inbox 领取任务，也不是把任务注入 system prompt。

- `system` 保存固定身份、角色和行为要求。
- 初始 `prompt` 直接成为 Alice `messages` 中的第一条 user message。
- Alice 进入循环后，才在每轮顶部读取自己的 inbox，并追加 `<inbox>...</inbox>` user message。

准确流程是：

```text
spawn_teammate 的 prompt
-> Alice messages
-> Alice 执行任务
-> summary
-> Lead inbox
-> Lead history 或 check_inbox 的 tool_result
```

### 问题 2：s06 与 s15

你的回答正确：

- s06 子 Agent 通常完成一次任务后结束。
- s15 教学版队友可以连续进行最多 10 轮 LLM—工具交互。
- 二者上下文都隔离，但 s15 可以通过消息显式共享信息。
- s06 主要返回最终结论；s15 使用异步邮箱持续通信。

“共享信息”不等于共享完整上下文。Alice 看不到 Lead 的整个 `history`，Lead 也看不到 Alice 的完整 `messages`；双方只共享明确发送的内容。

### 问题 3：触发时机

你的回答方向正确，但“下一回合”取决于到达时间：Alice 在外层检查前写入时，结果会被注入并在下一回合可见；在检查后、main 阻塞于 `input()` 时才写入，下一次普通回合会先运行，结果通常要到再下一回合才被模型看到。

显式 `check_inbox` 会把读取结果作为 `tool_result` 返回，使同一个 `agent_loop` 立即继续处理。

因此：**外层检查负责回合间注入；`check_inbox` 可以在当前工具回合交付消息。**

### 问题 4：消费与并发

你说 `unlink()` 用于避免重复处理，基本正确：第一次读取返回消息并删除文件，第二次读取返回 `[]`。

关键竞态是 `Reader read_text() → Writer append → Reader unlink()`：Reader 没有读到刚追加的消息，却删除了整个文件，新消息因此丢失。

多个队友同时追加 `lead.jsonl` 时，因为没有文件锁，还可能出现写入交错或 JSONL 损坏。因此主要风险是消息丢失和内容损坏，不是重复交付。

### 问题 5：`for ... else`

你的回答正确。

- 找到文本时，内层 `break` 结束内容块循环，跳过 `else`。
- 没找到文本时，循环正常结束，执行 `else: continue`，检查更早消息。
- 外层 `break` 表示 summary 已找到，不再扫描历史。
- 所有消息都没有文本时，保留默认值 `"Done."`。

## s15 相比 s14 的变化

s14 解决“什么时候产生工作”，s15 解决“一项工作由谁分担”。

| 对比项 | s14 Cron Scheduler | s15 Agent Teams |
|---|---|---|
| Agent 数量 | 一个 Agent | 一个 Lead + 多个队友 |
| 触发来源 | 时间匹配 | Lead 工具调用 |
| 新线程 | Cron 调度线程 | 每个队友一个线程 |
| 中间状态 | `scheduled_jobs`、`cron_queue` | 邮箱、`active_teammates` |
| 注入格式 | `[Scheduled]` | `[Inbox]` |
| 新工具 | schedule/list/cancel | spawn/send/check |

s15 沿用了 prompt 组装、Task System、后台任务和 Cron 等能力，但为了聚焦团队机制，没有完整展示错误恢复、记忆和技能系统。两章可以组合：Cron 负责到点产生任务，Lead 再启动多个队友并汇总结果。

## s15 队友与 s06 子 Agent

| 对比项 | s06 子 Agent | s15 队友 |
|---|---|---|
| 定位 | 一次性委派 | 可继续通信的协作者 |
| 生命周期 | 完成单次调用后返回 | 最多 10 轮 |
| 上下文 | 独立 | 独立 |
| 信息共享 | 最终结论 | 显式 inbox 消息 |
| 主动通信 | 通常没有 | 有 `send_message` |
| 执行方式 | 临时子调用 | 独立 daemon 线程 |

多个 Agent 不共享同一个 `messages`，可以避免工具结果互相污染、上下文快速膨胀和多线程修改同一列表，并保留各自清晰的推理边界。

一句话：**上下文保持隔离，协作依赖消息。**

## 整体架构

s15 可以拆成四层：

1. **Lead**：主线程中的完整 Agent Loop，负责拆分任务、启动队友和汇总结果。
2. **Teammate**：独立线程、system、messages 和简化工具集。
3. **MessageBus**：通过 `.mailboxes/{agent}.jsonl` 连接 Agent。
4. **History Injection**：把外部消息转换成 Lead 能处理的对话内容。

Lead 新增三个团队工具：

- `spawn_teammate`：创建队友线程。
- `send_message`：向队友邮箱写消息。
- `check_inbox`：在当前 Agent Loop 中读取 Lead 邮箱。

队友不会直接修改 Lead 的 `history`，只通过 MessageBus 发送数据。

## MessageBus：文件收件箱

邮箱目录在启动时创建：

```python
MAILBOX_DIR = WORKDIR / ".mailboxes"
MAILBOX_DIR.mkdir(exist_ok=True)
```

### 消息格式

每条消息包含 `from`、`to`、`content`、`type` 和时间戳 `ts`。

每个 Agent 有一个 JSONL 文件，例如：

```text
.mailboxes/alice.jsonl
.mailboxes/bob.jsonl
.mailboxes/lead.jsonl
```

### 发送

`send()` 以追加模式写入一行 JSON：

```python
with open(inbox, "a") as f:
    f.write(json.dumps(msg) + "\n")
```

追加模式会保留旧消息，并在文件不存在时创建文件。

### 读取

`read_inbox()`：

1. 文件不存在时返回 `[]`。
2. 用 `read_text().splitlines()` 读取所有行。
3. 对非空行执行 `json.loads()`。
4. 用 `unlink()` 删除整个邮箱文件。

它是消费式读取，而不是查看式读取。

### 为什么使用文件

- 直观，可以在终端观察。
- 线程之间不必共享内存队列。
- 不需要额外消息服务。
- 通信状态与对话历史分离。

但文件本身不提供锁、确认、重试和事务，所以这只是教学版消息总线。

## Teammate Thread：独立队友循环

### 启动与防重名

`active_teammates` 记录正在运行的名字：

```python
if name in active_teammates:
    return f"Teammate '{name}' already exists"
```

它只保存布尔值，不保存线程句柄、取消操作或完整状态机。

### 独立上下文

队友的 system prompt 保存名字、角色、工具使用要求和向 Lead 汇报的规则；初始任务则作为第一条 user message 单独进入 `messages`。

### 简化工具集

队友只有四个工具：

- `bash`
- `read_file`
- `write_file`
- `send_message`

它没有 Task、Cron 和 `spawn_teammate`，因此不能嵌套创建更多队友。

### 循环流程

教学版最多循环 10 次：

```text
读取自己的 inbox
-> 必要时追加 <inbox> user message
-> 调用 LLM
-> 执行 tool_use
-> 追加 tool_result
-> 继续或结束
```

如果 `stop_reason != "tool_use"`，队友结束当前工作。真实系统会进入 idle loop 等待新消息，而不是立刻退出。

### 完成与退出

队友提取最近的文本作为 summary：

```python
BUS.send(name, "lead", summary, "result")
active_teammates.pop(name, None)
```

线程使用：

```python
threading.Thread(target=run, daemon=True).start()
```

daemon 线程不会阻止主进程退出。若用户退出时队友仍在写文件，线程可能被直接终止，这也是 s16 需要关机协议的原因。

## Lead 的两种 inbox 触发路径

### 路径一：外层自动注入

main 在一次 `agent_loop()` 返回后检查 inbox：

```text
用户输入
-> history append query
-> agent_loop
-> 打印 Lead 回复
-> BUS.read_inbox("lead")
-> history append [Inbox]
-> 等待下一次用户输入
```

注入的是普通 user message：

```python
{"role": "user", "content": f"[Inbox]\n{inbox_text}"}
```

它不会立即再次调用 LLM。因此“自动注入”不等于“自动唤醒”。

### 路径二：主动工具读取

LLM 调用 `check_inbox` 时：

```text
assistant tool_use
-> run_check_inbox()
-> BUS.read_inbox("lead")
-> 返回文本
-> user tool_result
-> 同一个 agent_loop 继续
```

这条路径可以在当前用户回合处理队友结果。

### 为什么放在 `agent_loop()` 外

- 分离职责：Agent Loop 处理同步 LLM—工具链，main 处理回合间外部事件。
- 保持 `assistant tool_use -> user tool_result` 正确配对。
- 避免队友线程直接并发修改 Lead history。
- 避免 inbox 消息递归触发无限 Lead 回合。

### 两种到达时序

Alice 在外层检查前完成：

```text
Alice 写邮箱
-> Lead agent_loop 返回
-> main 读取并注入
-> 下一回合模型看到
```

Alice 在外层检查后完成：

```text
main 检查为空并等待 input
-> Alice 写邮箱
-> 下一次普通 agent_loop 先运行
-> 回合结束后 main 才注入
-> 再下一回合模型看到
```

如果下一次提示明确要求检查 inbox，模型可调用工具并在当前回合取得结果。

### 两条路径竞争消费

工具路径和外层路径都调用 `BUS.read_inbox("lead")`。由于读取后删除文件，先执行的一方消费消息，后执行的一方看到空邮箱。

若 `check_inbox` 已经取得 Alice 结果，外层随后返回 `[]` 并不代表消息丢失，因为结果已经作为 `tool_result` 进入 history。

## 队友最终 summary 的提取

代码先设置：

```python
summary = "Done."
```

再用 `reversed(messages)` 从新到旧寻找最近的 Assistant 文本：

```python
for msg in reversed(messages):
    if msg["role"] == "assistant" and isinstance(msg["content"], list):
        for b in msg["content"]:
            if getattr(b, "type", None) == "text":
                summary = b.text
                break
        else:
            continue
        break
```

控制流是：

```text
找到 text
-> 内层 break
-> 跳过 inner for 的 else
-> 外层 break

没找到 text
-> inner for 正常结束
-> else: continue
-> 检查更早消息
```

两个简化点：

- 一条消息有多个文本块时只取第一个。
- 内容块若变成字典，`getattr()` 不会读取 `b["type"]`。

当前代码保存的是 Anthropic SDK 内容块对象，所以该实现能够提取 `b.text`。

## 异步时序与并发风险

### 读取—删除竞态

`read_text()` 和 `unlink()` 不是原子操作：

```text
Reader 读取旧内容
-> Writer 追加新消息
-> Reader 删除文件
```

Writer 的新消息会被删除，但没有出现在 Reader 的返回值中。

### 并发追加

Alice 和 Bob 可能同时向 `lead.jsonl` 写入。教学版没有线程锁或文件锁，不能保证所有平台上的写入都完整分行，可能出现交错或 JSON 损坏。

### 共享状态

`active_teammates` 也没有锁。当前通常只有 Lead 主线程负责 spawn，风险较低，但它本身并不是并发安全的注册表。

可靠系统还需要消息 ID、确认、重试、文件锁或事务型存储。

## 教学版实现的局限

- 没有文件锁、消息确认和失败重试。
- 没有独立 poller 自动唤醒 Lead。
- 队友最多 10 轮，没有永久 idle loop。
- daemon 线程可能随主进程直接终止。
- 没有 `shutdown_request` / `shutdown_approved` 握手。
- 没有权限请求向 Lead 冒泡。
- 队友没有共享 Task System 工具。
- summary 只提取一个文本块。

这些局限说明：**能通信，不等于已经具备可靠的分布式协作协议。**

s16 会继续加入消息约定和体面关机流程。

## 关键代码定位

| 机制 | 位置 |
|---|---|
| 邮箱目录 | `code.py:591` |
| `MessageBus` | `code.py:595` |
| `read_inbox()` | `code.py:611` |
| `active_teammates` | `code.py:624` |
| `spawn_teammate_thread()` | `code.py:629` |
| 队友 inbox 注入 | `code.py:671` |
| summary 提取 | `code.py:696` |
| 三个团队 handler | `code.py:717` |
| Lead 工具定义 | `code.py:805` |
| `agent_loop()` | `code.py:847` |
| main inbox 注入 | `code.py:920` |

推荐阅读顺序：

```text
MessageBus
-> spawn_teammate_thread
-> 队友工具循环
-> summary 提取
-> check_inbox
-> main 外层注入
```

## 重点理解

学完后应能解释：

1. system、初始 prompt 和后续 inbox 分别进入哪里。
2. 为什么每个 Agent 使用独立 `messages`。
3. 外层自动注入为什么不会立即唤醒 Lead。
4. `check_inbox` 为什么能在当前回合交付结果。
5. `read_text() + unlink()` 为什么可能丢消息。
6. `for ... else` 与两个 `break` 如何选出 summary。
7. daemon、10 轮限制和无关机协议意味着什么。

三个关键边界：

```text
固定身份 vs 运行时消息
独立上下文 vs 显式通信
同步回合 vs 异步事件
```

## 复习问题

1. `role` 和 `prompt` 分别进入队友的什么位置？
2. 队友收到后续 inbox 消息时，如何加入自己的 `messages`？
3. 外层读取 inbox 后为什么不会自动调用 LLM？
4. Alice 在外层检查后才发结果，Lead 最早可通过哪两条路径处理？
5. 为什么 `check_inbox` 消费后，外层检查可能返回空？
6. Writer 在 `read_text()` 和 `unlink()` 之间追加会发生什么？
7. 内容只有 `tool_use` 时，summary 提取怎样继续？
8. 所有 Assistant 消息都没有文本时，summary 是什么？

## 记忆口诀

```text
角色写 system，
任务进 messages；
队友独立跑，
消息写邮箱；
工具当轮读，
外层回合注入；
读取即删除，
无锁可能丢；
倒序找 text，
summary 报 Lead。
```

一句话总结：

**独立上下文，文件通信，回合间注入。**
