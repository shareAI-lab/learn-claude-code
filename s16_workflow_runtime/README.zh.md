# s16: Workflow Runtime — 把菜谱写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *“一轮轮聊天，像每隔十秒给厨师发一条短信。Workflow 是厨房能照着做的菜谱。”*
>
> **Harness 层**: 编排 — 在单 agent 循环之上，跑一套多 agent 脚本。

---

想象你和朋友用微信一起做饭。你发“先切洋葱”，等他回，再问“切好了吗？”，然后“热锅……”。一道菜还行；要办二十桌宴席，聊天就成了瓶颈：步骤记丢、反复叮嘱，手机一死还得从头来。

普通“模型当总指挥”的对话就是这样。**Workflow** 是写好的菜谱：厨房（runtime）按谱做，帮手（子 agent）负责判断，中间结果放在台面上的碗里 —— 不塞进群聊记录。

## 问题在哪

从 s01 到 s15，每一轮都由模型决定下一步调用什么工具。当“下一步取决于刚才发现了什么”时，这很合适。

有些任务的形状事先就知道：

- 按多个维度审查很多文件
- 先调研，再验证，再合并
- 用同一种方式迁移 N 个模块

如果模型只能把计划“记”在 `messages[]` 里，会发生三件事：编排噪音占满上下文、中途计划漂移、崩了就得把做完的活重做一遍。

你需要并行、稳定的结果形状，以及能续跑。把这三样只寄存在对话历史里，太脆弱。

## 一句话说清想法

**把计划写进代码。** 子 agent 仍然负责判断；脚本负责循环、分发和合并。中间结果存在变量里，不进对话。

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

一次 `Workflow` 工具调用启动这次脚本运行。运行中会发出生命周期和进度事件；最后一条工具结果带回启动信息、结果和任务状态。

## 两扇门

Claude Code 对“工作流怎么启动”是诚实的：

| 门 | 你传什么 | 什么时候用 |
|----|----------|------------|
| **动态（Dynamic）** | 一段编排用的 JavaScript（`script`，或之后的 `scriptPath`） | 模型为**这次任务**现写菜谱 |
| **已保存（Saved）** | `name` + `args` | 好用的菜谱放进例如 `.claude/workflows/`，按名字再跑 |

同一间厨房。动态是“现在写菜谱”，已保存是“从卡片盒里抽一张”。

**本课是一个 Python 教学运行时。** 用同样的想法，但每行你都能读懂。演示按名字注册一个已保存的 workflow；概念和 Claude Code 的脚本世界一一对应。我们**不会**再说“模型不能提交可执行代码”——那是对 Claude Code 的误述。这里只是不嵌入完整的 JS 解释器。

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

四个审查维度走同一条两阶段路径：

```text
correctness ── 审计 ── 验证 ──┐
security    ── 审计 ── 验证 ──┤── 合并确认过的问题
performance ── 审计 ── 验证 ──┤
style       ── 审计 ── 验证 ──┘
```

1. **Review** — 每个维度的审计员返回结构化 findings。
2. **Verify** — 每条 finding 交给对抗性检查（在 verify 阶段里用 `parallel`）。
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

[s17 Goal Loop](../s17_goal_loop/) 会问一个独立判断器：该停，还是再来一轮？

<!-- translation-sync: zh@v11, en@v11, ja@v11 -->
