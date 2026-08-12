# s16: Workflow Runtime — 把菜谱写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> Workflow = 写进代码的编排。脚本管拓扑，模型管每一步判断。
>
> **Harness 层**: 编排 — 单 agent 循环之上再跑多 agent 脚本。
>
> 信任模型，工程化 harness。Workflow 把这句话往上提一层。

---

## 问题

长任务里，计划和动手挤在同一段 chat：做到一半就宣布完工、自己批改自己偏甜、压缩几轮后约束悄悄丢了。并行、稳定结果形状、崩了续跑——软对话记忆扛不住。

一轮轮催进度，像每隔十秒给厨师发短信。**Workflow** 是厨房能照着做的菜谱。

## 想法

帮手（子 agent）仍负责想；**脚本**管循环、分发、合并。中间结果进变量和 journal，不进对话。

**编排从「智力」挪到「结构」。**

```text
  messages[] ──► Workflow(...) ──► tool_result
                      │
                      ▼
              脚本管拓扑：agent / parallel / pipeline
                      │
                      ▼
                 变量 + journal
```

一次 `Workflow` 工具调用开跑；菜谱做完，一条结果回来。

<details>
<summary>运行时总览图</summary>

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

</details>

## 两扇门

- **动态**：模型为*这次*任务写 JS 编排（`script` / `scriptPath`）。
- **已保存**：好脚本进 `.claude/workflows/`，用 `name` + `args` 再调。
- **静态**（门外表亲）：SDK / `claude -p` 事先写好，偏通用。

![静态 vs 动态](images/dynamic-vs-static.png)

*左：固定流水线 → 泛报告。右：按你的代码现裁 → 具体建议。*

本章是 **Python 教学 runtime**（不嵌 JS VM）。概念对齐 Claude Code；演示走「已保存」门。模型在产品里本来就能交可执行脚本——我们只是不在这里跑 JS。

```python
# 教学示意 — 不是完整 schema
Workflow({ "name": "review-changes", "args": { "changes": "..." } })
# Claude Code 还接受：script | scriptPath | resumeFromRunId
```

## 三个动词

```text
  agent      一个帮手，一件事（可带 schema → 校验 JSON）
  pipeline   每个 item 自己走阶段（默认，不等齐）
  parallel   等齐再往下（屏障，少用）
```

失败时舰队继续：`parallel` 槽位变 `null`；`pipeline` 丢掉那个 item 及其后续 stage。合并前先过滤。

续跑：journal 按召唤顺序记；回放**最长未改前缀**，第一个改动之后全实跑。真 JS 运行时禁 `Date.now()` / `Math.random()`；本 demo 不完整沙箱——脚本仍写成确定性的。

```text
  journal  [A] [B] [C] [D]
  续跑      命中 命中 ✂ 实跑
```

<details>
<summary>官方原语卡片 + 更轻的动词</summary>

![Workflow 原语](images/workflow-primitives.png)

*`agent`；`parallel`（屏障）vs `pipeline`（流式阶段）。Claude Code 还有 `model` / `isolation` / `agentType`；教学面更小。*

更轻：`phase`、`log`、嵌一层 `workflow`、`args`、`budget`。

</details>

## 两种形状 + 一个样本

先摸两种（完整六模式见下方折叠）：

```text
  Fanout          task ──► ● ● ● ● ══屏障══► synthesize
  Adversarial     worker ──► verifier×N  → 只留站得住的
```

样本 `review-changes` = **Fanout** 里嵌 **Adversarial**：多维度 `pipeline(audit, verify)`，`verify` 里 `parallel` 挑刺，过滤后只留 `isReal`。

```text
  correctness ── 审计 ── 验证 ──┐
  security    ── 审计 ── 验证 ──┤── confirmed
  performance ── 审计 ── 验证 ──┤
  style       ── 审计 ── 验证 ──┘
```

```python
# 来自 code.py（节选）
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    return {"confirmed": confirmed}
```

舰队不能早停、作者不当裁判、拓扑不靠 chat 每轮改写。

<details>
<summary>六种模式网格 + 原语对照</summary>

![六种 Workflow 模式](images/six-workflow-patterns.png)

| 模式 | 原语速写 | 什么时候别用 |
|------|----------|--------------|
| Classify-And-Act | `agent` → 分支 → `agent` | 每件都该同样处理 |
| Fanout-And-Synthesize | `pipeline` / `parallel` → 合并 | 一趟已装得下 |
| Adversarial Verification | 产出 → `parallel(verify)` → 过滤 | 答错很便宜 |
| Generate-And-Filter | `parallel(gens)` → 过滤 | 答案空间本来就小 |
| Tournament | 两两裁判 `agent` | 清晰量尺一趟能选 |
| Loop Until Done | `while` + 停止 + `budget` | 工作量已知 |

```python
# 教学示意
kind = await ctx.agent("给工单分类", schema=KIND)
if kind["type"] == "billing":
    return await ctx.agent("处理账单…")
```

</details>

<details>
<summary>不可信输入：隔离分流（quarantine）</summary>

读工单的 agent 不该同时握开 PR 的钥匙。读者只读 → 结构化摘要；受信任 actor 只看摘要行动。

```text
  积压（不可信）→ [隔离区: readers → 去重 → 摘要] → [受信任: actor]
```

![隔离分流](images/quarantine-triage.png)

*高权限工具住在受信任一侧。积压睡不着时可配 `/loop`。*

</details>

<details>
<summary>怎样挂在 s15 上</summary>

s15 仍是宿主循环；s16 只多一个 `Workflow` 工具。产品里可后台跑；教学 CLI 用前台 `demo` / `resume` 看阶段和缓存。

</details>

## 邻居 & 何时别用

谁握计划？s06 一次性委派、s13 邮箱同伴、s15 单循环、**s16 脚本 + journal**、s17 门口问「整目标做完了吗」。

普通改代码：s15 一轮或一个 s06 往往够。Workflow 要 token 和协调——结构必须比单个上下文活得更久时再用。

## 试一下

```bash
python s16_workflow_runtime/code.py          # s15 宿主 + Workflow（真实 API）
python s16_workflow_runtime/code.py demo     # 固定数据；看阶段
python s16_workflow_runtime/code.py resume   # 同一 runId；期待缓存命中
```

完整续跑应看到 `agents=0 tokens=0`。

## 接下来

s16 讲一批活怎么跑。[s17 Goal Loop](../s17_goal_loop/) 问：该停，还是再来一轮？

<!-- translation-sync: zh@v18, en@v18, ja@v18 -->
