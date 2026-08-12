# s16: Workflow Runtime — 把菜谱写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *“一轮轮聊天，像每隔十秒给厨师发一条短信。Workflow 是厨房能照着做的菜谱。”*
>
> **Harness 层**: 编排 — 在单 agent 循环之上，跑一套多 agent 脚本。
>
> 信任模型，工程化 harness。Workflow 就是编排层上的 harness 工程。

---

想象你和朋友用微信一起做饭。你发“先切洋葱”，等他回，再问“切好了吗？”，然后“热锅……”。一道菜还行；要办二十桌宴席，聊天就成了瓶颈：步骤记丢、反复叮嘱，手机一死还得从头来。

普通“模型当总指挥”的对话就是这样。**Workflow** 是写好的菜谱：厨房（runtime）按谱做，帮手（子 agent）负责判断，中间结果放在台面上的碗里 —— 不塞进群聊记录。

## 为什么需要 harness？

默认的 Claude Code harness 很擅长“写代码那种形状”的工作：改、跑、看报错、再试 —— 都在同一个循环里。

有些活需要**叠一层定制 harness**：深度调研、安全分析、agent teams、大规模 code review。你可以事先用 SDK 手写那层 harness；也可以 —— 这就是动态的想法 —— 让 Claude **为这次任务现场写一个 harness**，跑完，好用的再存下来。

课程的口号往上提一层：每一步里信任模型；步骤之间的结构，靠工程来定。

## 问题：一个窗口，三种走偏

从 s01 到 s15，模型在**同一个**上下文里既规划又执行。当“下一步取决于刚才发现了什么”时，这很合适。当任务又长、又要大规模并行、又要求死板结构、或需要对抗验证时，就会变脆。

Claude Code 的设计者给单窗口里常见的三种失败起了名字。用大白话说：

| 失败模式 | 感觉起来像什么 |
|----------|----------------|
| **Agentic laziness（偷懒收工）** | 五十项审查做到三十五，就说“做完了” |
| **Self-preferential bias（自我偏爱）** | 让它检查自己的结论时，总觉得自己更对 —— 狐狸给鸡窝打分 |
| **Goal drift（目标漂移）** | 原来的“别动 X”在多轮对话和压缩之后渐渐淡掉 |

对话历史也很难同时扛住并行、稳定的结果形状、以及续跑。审查很多文件、先调研再验证、按同一方式迁移 N 个模块 —— 这些活的**形状**事先就知道，更需要那三样。

## 一句话说清想法

**把编排从“靠聪明”挪到“靠结构”。**

子 agent 仍然负责判断 —— 各自干净的上下文、专注的目标。**脚本**负责循环、分发和合并。中间结果存在变量（和 journal）里，不进对话。分开的帮手 + 脚本掌握的控制流，就是对抗偷懒、自我检查偏差和漂移的办法。

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

一次 `Workflow` 工具调用启动这次脚本运行。运行中会发出生命周期和进度事件；最后一条工具结果带回启动信息、结果和任务状态。

## 两扇门 — 以及动态 vs 静态

Claude Code 用两扇门走进同一间厨房：

| 门 | 你传什么 | 什么时候用 |
|----|----------|------------|
| **动态（Dynamic）** | 一段编排用的 JavaScript（`script`，或之后的 `scriptPath`） | 模型为**这次任务**现写菜谱 |
| **已保存（Saved）** | `name` + `args` | 好用的菜谱放进例如 `.claude/workflows/`，按名字再跑 |

同一间厨房。动态是“现在写菜谱”；已保存是“从卡片盒里抽一张”—— 一次漂亮动态运行留下来的可复用残渣。

本课之外还有表亲：**静态** harness（事先写好的 Agent SDK / `claude -p` 编排）。静态的要覆盖所有边角，所以往往更泛用。动态的是为*这次*任务量身定做；合身了再存成 saved。

**本课是一个 Python 教学运行时。** 同样的想法，每行你都能读懂。演示按名字注册一个已保存的 workflow；概念和 Claude Code 的脚本世界一一对应。我们**不会**再说“模型不能提交可执行代码”——那是对 Claude Code 的误述。这里只是不嵌入完整的 JS 解释器。

```python
# 教学适配器：已保存这扇门（name + args）。
# Claude Code 还接受 script / scriptPath / resumeFromRunId。
WORKFLOW_TOOL = {
    "name": "Workflow",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "object"},
            "resume_from_run_id": {"type": "string"},
            "resumeFromRunId": {"type": "string"},
        },
        "required": ["name"],
    },
}
```

## 原语：用一次义卖来讲

学校义卖要烤很多蛋糕。每张桌子都要：搅拌 → 烘烤 → 装箱。帮手负责尝和判断；菜谱决定顺序。

| 原语 | 在厨房里的意思 |
|------|----------------|
| `agent(prompt, {schema, label, phase})` | 请一个帮手做一件事 |
| `pipeline(items, *stages)` | **默认。** 每块蛋糕自己走完搅拌→烘烤→装箱。A 在装箱时，B 可能还在搅拌 |
| `parallel(thunks)` | 等**所有**托盘都回来 —— 只有下一步真的需要全部结果时才用 |
| `phase(title)` | 在进度板上宣布“现在进入烘烤” |
| `log(message)` | 喊一句短状态 |
| `workflow(name, args)` | 套用一份更小的菜谱（只嵌一层） |
| `args` | 这次运行的“食材清单” |
| `budget` | 还能烧多少“烤箱分钟”（token） |

默认用 `pipeline`。只有下一步必须凑齐上一阶段全部结果时，才用 `parallel` —— 比如要先尝完所有托盘再写评分表。

```python
# 每个审查维度独立走 审计 → 验证（阶段之间不等齐）。
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

## 有品味的模式（不是清单倾销）

把模式想成菜谱风格。示例 `review-changes` 主要用了三种：

| 模式 | 大白话 | 在示例里 |
|------|--------|----------|
| **Fan-out-and-synthesize（分发再汇总）** | 拆开干，每人一张干净桌子，再合并 | 四个维度在 `pipeline` 里审计，最后合成确认列表 |
| **Adversarial verification（对抗验证）** | 第二个帮手专门来挑刺 | 每条 finding 先过 verify agent 才作数 |
| **Generate-and-filter（生成再过滤）** | 先产出候选，只留通过检验的 | findings 进来 → 只留 `isReal` |

同一工具箱里还有别的风格，以后会遇到：**classify-and-act**（按类型分流）、**tournament**（比武再选冠军）、**loop-until-done**（直到没有新发现再停）。只有当额外成本能换来更清楚或更稳妥的结果时，才上模式。

## 让答案机器能读

如果帮手回来写散文，下一阶段就很难把 finding 和 verdict 一一对应。传入 `schema`：运行时要求 JSON、做校验，不对就**重试一次**。再不对，这次调用报错（见下面的空值隔离）。

```python
out = await ctx.agent(
    f"检查这段变更里有没有{dimension}相关的问题：\n{changes}",
    schema=FINDINGS_SCHEMA,
    label=f"audit:{dimension}",
)
# out 是带 "findings" 的字典，不是一段话
```

跟你聊天可以用自然语言；流水线需要接口对得上。

## 一个帮手失败时

不能因为一个托盘糊了，整支队伍停工。

- **`parallel`**：失败的 thunk 在该槽位变成 `null` / `None`；整个 gather 不会因此拒绝。
- **`pipeline`**：某个 stage 失败时，**该 item** 变成 `null` / `None`，并跳过它后面的 stage；其他 item 继续。

合并前要小心过滤 —— 常见写法是 `if r` / `.filter(Boolean)`。

```python
verdicts = await ctx.parallel([...])  # 有些位置可能是 None
confirmed = [
    f for f, v in zip(findings, verdicts)
    if v and v.get("isReal")
]
```

## Journal 与续跑

每次运行都有一个 `runId`。每个 `agent()` 结束后，运行时往磁盘上的 journal 追加一行。把它想成笔记本：按你**召唤**帮手的顺序记，而不是按他们从烤箱回来的先后。

续跑时（`resume_from_run_id` / `resumeFromRunId`），脚本仍从开头执行，但是：

1. 按调用顺序，把每次 `agent()` 和下一条 journal 记录比对。
2. **最长未改前缀** → 缓存命中（直接回放）。
3. 遇到**第一个**改过或未完成的调用，前缀断开。
4. **之后全部实跑** —— 即使 journal 更后面还躺着旧 key，也不能偷懒命中。

所以真正的 JS workflow 运行时会禁止 `Date.now()`、`Math.random()` 和裸的 `new Date()`：不确定的时钟和骰子会改 prompt 或调用顺序，笔记本就对不上了。这个 Python 演示不会完整沙箱这些 —— 但脚本仍应写成确定性的。

```text
journal:  [A ✓] [B ✓] [C ✓] [D ✓]
续跑:     A 命中 → B 命中 → C 改过 → D 实跑（不会悄悄命中旧的 D）
```

## 跟着示例走：`review-changes`

四个审查维度走同一条两阶段路径 —— 先分发，再对抗验证，再过滤：

```text
correctness ── 审计 ── 验证 ──┐
security    ── 审计 ── 验证 ──┤── 合并确认过的问题
performance ── 审计 ── 验证 ──┤
style       ── 审计 ── 验证 ──┘
```

1. **Review** — 每个维度的审计员返回结构化 findings（干净桌子 → 少串味）。
2. **Verify** — 每条 finding 交给对抗性检查（在 verify 阶段里用 `parallel`），作者不当裁判。
3. 只保留被标成真实的问题，再按严重程度排序。

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"确认了 {len(confirmed)} 个真实问题")
    return {"confirmed": confirmed}
```

## 怎样接到 s15

s15 仍是宿主循环。s16 只多一个工具：`Workflow`。模型（或你）给出已保存的名字；适配器查 registry，再跑脚本。

| | Claude Code / Pi（产品） | 本课教学 CLI |
|--|--------------------------|--------------|
| 脚本语言 | 沙箱里的 JavaScript | 可读的 Python 函数 |
| 动态门 | 模型写 `script` / 改 `scriptPath` | 文档说明；演示走已保存的 `name` |
| 运行时宿主 | 后台 + 通知，会话保持可响应 | `demo` / `resume` 前台跑，方便观察 |
| 想法 | 同一套原语、journal、前缀续跑 | 教学模型 —— 简化处会说清楚 |

主循环不会变成 workflow 引擎。它只是多借一把工具，就像借 `bash` 或 `task` 一样。

## 邻居们：谁握着计划？

Workflow 不是“多派几个 agent”。它改的是**谁拥有拓扑结构**。

| 邻居 | 谁握着计划 | 中间结果住哪 | 最适合 |
|------|------------|--------------|--------|
| [s06 子 Agent](../s06_subagent/) | 模型，一次性 | 除最终摘要外丢掉 | 隔离一个脏的子任务 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead 模型逐轮 + 邮箱 | 共享任务 / 消息 | 长跑同伴、偏人类协作 |
| [s15 Agent Harness 集成](../s15_integrated_harness/) | 模型在一个循环里 | 对话 `messages[]` | 累积型 coding agent |
| **s16 Workflow** | **脚本** | **脚本变量 + journal** | 已知 / 大规模结构化分发 + 验证 |
| [s17 Goal Loop](../s17_goal_loop/) | 停止边界上的判断器 | 对话当证据 | “整个目标做完了吗？” |

更便宜的替代方案经常就够用：skill / prompt 当软计划、一小段多 agent 闲聊、手写静态 SDK 编排，或者干脆更大的单轮模型调用。当结构必须比单个上下文活得更久时，再伸手去拿 workflow —— 不是因为“专家团”听起来很酷。

## 什么时候*别*用 workflow

Workflow 要花 token，也有协调成本。大多数普通写代码的活，**不需要**五人评审团。

问问自己：这件事真的需要更多算力和定制 harness 吗？如果普通的 s15 一轮（或一个 s06 子 agent）就够，就停在那儿。克制也是设计思想的一部分 —— 并行和分工必须赚回自己的成本。

## 试一下

```bash
python s16_workflow_runtime/code.py          # s15 宿主 + Workflow 工具（真实 API）
python s16_workflow_runtime/code.py demo     # 固定数据：观察阶段和 agent
python s16_workflow_runtime/code.py resume   # 同一个 runId；前缀应全部缓存命中
```

留意这些：

- `workflow_phase`：先 Review，再 Verify
- 每个 `workflow_agent`：第一次是 `done`，完整续跑变成 `cached`
- 结尾有一份简短的确认列表；全命中续跑显示 `agents=0 tokens=0`

## 相对 s15 → 下一站 s17

| | s15 Agent Harness 集成 | s16 Workflow Runtime |
|--|------------------------|----------------------|
| 循环 | 单个、模型驱动 | 同一循环；一个工具跑脚本 |
| 谁决定下一步 | 模型逐轮决定 | 脚本规定整批形状 |
| 多 agent | 一次性子 agent | 可脚本化、可续跑的 `agent()` |
| 失败 / 续跑 | 靠对话记忆 | 空值隔离 + journal 前缀 |

**s16 = 一批活怎么跑。s17 = 整个目标算不算做完。**

[s17 Goal Loop](../s17_goal_loop/) 会问一个独立判断器：该停，还是再来一轮？可重复的 workflow 若还需要硬性完成条件，可以和它配对。

<!-- translation-sync: zh@v12, en@v12, ja@v12 -->
