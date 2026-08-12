# s16: Workflow Runtime — 把编排写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

[s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *计划别只活在嘴上。* 脚本管先后，模型管每一步判断。
>
> **Harness 层**: 编排 — 在单 agent 循环之上，再跑一套多 agent 脚本。

## 问题

你已经会让模型在一个循环里读文件、改代码、看报错。可有些活你其实**早就知道先后顺序**：先分维度审，再找人挑刺，最后汇总。若顺序只靠聊天记住，模型会做到一半喊完工，自己批改自己偏甜，压几轮上下文后连「别动 X」都丢了。

软对话扛不住并行、稳定结果形状，也扛不住崩了接着跑。你需要的不是更会聊天的模型，是一份**写下来的编排**。

## 解决方案

```text
  你的对话 ──► Workflow(...) ──► 一条结果回来
                    │
                    ▼
            脚本：agent / pipeline / parallel
                    │
                    ▼
              变量 + journal（半成品放这儿，不塞群聊）
```

帮手（子 agent）仍负责想；**脚本**管循环、分发、合并。中间结果进变量和 journal，不进主对话。

一句话：**编排从「智力」挪到「结构」。**

![静态 harness vs 动态 workflow](images/dynamic-vs-static.png)

*左：通吃的固定流水线。右：为这次任务现裁的编排。*

Claude Code 里有两扇门：**动态**——模型为这次任务写 JS（`script` / `scriptPath`）；**已保存**——好脚本用 `name` + `args` 再跑。门外还有用 SDK 事先写死的静态编排。本章是 **Python 教学 runtime**（不嵌 JS）：思想对齐，演示走「已保存」门。模型在产品里本来就能交脚本——我们只是不在这里跑 JS。

## 工作原理

**1. 三个动词**

```text
  agent      一个帮手，一件事（可带 schema，拿到能往下传的 JSON）
  pipeline   每个 item 自己走完各阶段（默认，不等齐）
  parallel   等所有结果齐了再往下（屏障，少用）
```

谁失手：`parallel` 那个槽变成 `null`；`pipeline` 丢掉那个 item。舰队不整船沉。合并前先过滤。

**2. 续跑靠本子，不靠聊天记忆**

journal 按 `agent()` **召唤顺序**记账。续跑回放最长未改前缀；碰到第一处改动，后面全实跑。真 JS 运行时禁 `Date.now()` / `Math.random()`，免得本子对不齐——教学脚本也请写成确定性的。

```text
  journal  [A] [B] [C] [D]
  续跑      命中 命中 ✂ 实跑
```

**3. 一个样本：分发 + 对抗**

`review-changes` 不是「一种模式」，是 **Fanout** 里嵌 **Adversarial**：多维度 `pipeline(audit, verify)`，验证里再 `parallel` 挑刺，只留站得住的 finding。

```text
  correctness ── 审计 ── 验证 ──┐
  security    ── 审计 ── 验证 ──┤── confirmed
  performance ── 审计 ── 验证 ──┤
  style       ── 审计 ── 验证 ──┘
```

```python
# code.py 节选 — 形状就这些
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    return {"confirmed": confirmed}
```

舰队不能早停，作者不当裁判，拓扑也不靠 chat 每轮改写。

<details>
<summary>六种常见形状（模式库）</summary>

![六种 Workflow 模式](images/six-workflow-patterns.png)

| 模式 | 人话 | 原语速写 |
|------|------|----------|
| Classify-And-Act | 先分拣再交给对的人 | `agent` → 分支 → `agent` |
| Fanout-And-Synthesize | 拆开干，再合并 | `pipeline` / `parallel` → 汇总 |
| Adversarial Verification | 别让狐狸评鸡窝 | 产出 → `parallel(verify)` → 过滤 |
| Generate-And-Filter | 先多产再筛 | `parallel(gens)` → 过滤 |
| Tournament | 两两比出冠军 | 裁判 `agent` |
| Loop Until Done | 「还有新发现？」就继续 | `while` + 停止 + `budget` |

`review-changes` ≈ Fanout + Adversarial。研究类常叠：分发 → 过滤 → 验证 → 汇总。

</details>

<details>
<summary>动态 / 已保存 / 静态 & 官方原语图</summary>

```python
# 教学示意
Workflow({ "name": "review-changes", "args": { "changes": "..." } })
# Claude Code 还接受：script | scriptPath | resumeFromRunId
```

![Workflow 原语](images/workflow-primitives.png)

</details>

<details>
<summary>不可信输入时：隔离读写</summary>

读工单的人，不该同时握着开 PR 的钥匙。读者只读 → 摘要；受信任的一侧只看摘要行动。

```text
  积压 → [隔离区: 读 / 去重 / 摘要] → [受信任: 行动]
```

![隔离分流](images/quarantine-triage.png)

</details>

谁握计划？s06 一次性派工，s13 邮箱同伴，s15 单循环聊天，**s16 是脚本 + journal**，s17 在门口问整件事做完没有。普通改几个文件：s15 或一个 s06 往往够。Workflow 贵在 token 和协调——**结构必须比单次对话活得更久**时再用。

## 试一试

```bash
python s16_workflow_runtime/code.py demo
python s16_workflow_runtime/code.py resume
```

第一次看 Review → Verify；第二次同一 run，agent 应大量 `cached`（理想情况 `agents=0 tokens=0`）。想挂进完整宿主：不加参数直接跑 `code.py`。

s15 还是那个循环；这里只是多了一个 `Workflow` 工具。[s17](../s17_goal_loop/) 问另一个问题：该停了吗？

<!-- translation-sync: zh@v19, en@v19, ja@v19 -->
