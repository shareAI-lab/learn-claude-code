# s16: Workflow Runtime — 把菜谱写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *“一轮轮聊天，像每隔十秒给厨师发一条短信。Workflow 是厨房能照着做的菜谱。”*
>
> **Harness 层**: 编排 — 单 agent 循环之上，再跑一套多 agent 脚本。
>
> 信任模型，工程化 harness。Workflow，就是把这句话往上提一层。

---

想象你跟朋友用微信一起做饭。“先切洋葱。”等回音。“切好了吗？”然后热锅、放盐。一道菜还能撑住这种节奏；二十桌宴席就不行了——步骤会丢，话会重复，手机一死还得从头来。

模型既当厨师又当记事本时，感觉就是这样：计划与动手挤在同一段对话里。**Workflow** 是写好的菜谱。厨房（一个小 runtime）按谱做，帮手（子 agent）负责尝和判断，半成品放在台面上的碗里——变量和 journal——而不是塞进群聊。

## 为什么还要另一层 harness？

默认的 Claude Code harness 已经很擅长“写代码那种形状”的活：改一点、跑一下、看报错、再试。一个循环。一颗脑袋。能做出不少工艺。

可有些活需要**叠一层定制 harness**——深度调研、安全排查、agent teams、要铺开审查一整片改动。你可以事先用 SDK 手写那一层；也可以——这才是有意思的地方——让 Claude **为这次任务**起草一个 harness，跑起来，好用的再留下来。

课程那句口号往上提一层：每一步里信任模型；步骤怎么排，由你来定结构。

## 长对话里你会看见的走偏

从 s01 到 s15，计划与执行共享同一个上下文。下一步取决于刚才的发现时，这很舒服。可一旦任务变长、要大规模并行、结构又死板，或需要一个挑剔的第二意见，它就会发脆。

耐心看一段很长的聊天，你会在学会术语之前先撞见熟面孔。做到五十项里的三十五就宣布完工。让它批改自己的作业，分数总是偏甜——狐狸给鸡窝打分。多轮对话和压缩过后，那句轻轻的“别动 X”渐渐听不见了。

这些就是 agentic laziness、self-preferential bias、goal drift。名字不如感觉重要：同一个窗口既要干活，又要记住计划。软软的对话记忆，很难扛住并行、稳定的结果形状，以及崩了还能续上。

## 点子落下的那一下

假如计划住在代码里呢？

帮手仍然负责想——每人一张干净桌子。**脚本**掌管循环、分发和合并。中间结果待在变量和 journal 里，不进对话。想偷懒提前收工的习惯，更难叫停整支队伍；自我检查的偏心，会撞上一个不是作者本人的第二帮手；漂移也难下手，因为拓扑不再由一个疲倦的叙述者每轮改写。

**Workflow 把编排从「智力」挪到「结构」。** 模型仍在每次 `agent()` 里做判断；地图归脚本管。

```text
  messages[] ──► Workflow(...) ──► tool_result { launched, result, task }
                      │
                      ▼
              ┌───────────────┐
              │  脚本掌管拓扑  │
              └───────┬───────┘
                      │ agent / parallel / pipeline
                      ▼
                 变量 + journal
```

一次 `Workflow` 工具调用启动这次运行。进度在旁边轻轻响；菜谱做完，一条工具结果回来。

<details>
<summary>运行时总览图（可选）</summary>

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

</details>

## 两扇门——门外还有个表亲

Claude Code 对入口说得很直白。

**动态**——模型为*这次*任务写一段编排用的 JavaScript（`script`，之后可改 `scriptPath`）。问题还热着，就裁出一件合身的 harness。

**已保存**——好脚本已经进了例如 `.claude/workflows/`。你用 `name` + `args` 再请它出来。一次值得留下的运行，沉淀成可复用的卡片。

门外还有表亲：**静态** harness，用 Agent SDK 或 `claude -p` 事先写好。它们得扛住所有边角，所以往往更泛。动态的是为这块布现裁的；合身了再存。

![静态 harness 与动态 workflow](images/dynamic-vs-static.png)

*同一个问题，两套 harness。左边：固定的搜索→验证→摘要，终点是泛泛的报告。右边：读你的 billing 代码、分叉、请来魔鬼代言人，最后给出具体建议。*

**这一章是 Python 教学运行时。** 同样的想法，每行都能读。演示按名字挂了一个已保存的 workflow；概念和 Claude Code 的脚本世界一一对应。我们不会再说“模型不能提交可执行代码”——那从来不是 Claude Code 的真相。这里只是不嵌入 JS 解释器。

```python
# 教学示意 — 已保存这扇门（不是完整 Claude Code schema）
Workflow({ "name": "review-changes", "args": { "changes": "..." } })

# Claude Code 还接受：script | scriptPath | resumeFromRunId
```

## 脚本会说的三个动词

学校义卖。每张桌子：搅拌 → 烘烤 → 装箱。帮手负责尝；菜谱决定先后。

```text
  agent      一个帮手，一件事
  pipeline   每块蛋糕自己走完各阶段   （默认 — 不等齐）
  parallel   等所有托盘都回来再往下   （屏障 — 少用）
```

`agent(prompt, opts?)` 请一个帮手。带上 `schema`，答案变成校验过的 JSON——下一阶段接得住的接口——第一次不对还给一次重试。

`pipeline` 让蛋糕 A 装箱时，蛋糕 B 还可以在搅拌。`parallel` 只在下一步真的需要全部结果时才值得——比如尝完所有托盘再写评分表。

```python
# 教学示意 — 只看形状（可运行样本在 code.py）
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

帮手失手时，舰队仍然温和：`parallel` 的失败在该槽位变成 `null`；`pipeline` 的失败会丢掉**那个 item** 并跳过后续 stage。合并前先过滤。

厨房暂停了呢？磁盘上的 journal 按**召唤顺序**记着每次调用。续跑回放**最长未改前缀**；碰到第一个改动，之后全部实跑。真正的 JS 运行时禁止 `Date.now()` / `Math.random()`，好让笔记本对得齐。这个 Python 演示不会完整沙箱那些——脚本仍写成确定性的吧。

```text
  journal   [A] [B] [C] [D]
  续跑       命中 命中 ✂ 实跑   ← 前缀在 C 断开
```

<details>
<summary>官方原语卡片 + 更轻的动词</summary>

![Workflow 原语](images/workflow-primitives.png)

*官方卡片：`agent`，以及 `parallel`（屏障）与 `pipeline`（流式阶段）。Claude Code 还有 `model` / `isolation` / `agentType`；教学运行时把表面收小一点。*

更轻的动词：`phase`、`log`、嵌一层 `workflow`、`args`、`budget`。

</details>

## 会写菜谱之后——模式工具箱

动词是面粉和火候。人们反复发明的，是少数几种*形状*——工具箱，不是必点菜单。

![六种 Workflow 模式](images/six-workflow-patterns.png)

*官方六模式网格。脚本掌管拓扑；本课用 `agent` / `parallel` / `pipeline` / journal 把每种形状说出来。*

对后面的示例，先摸清三种最要紧的形状——名字可以后到。

**Fanout-And-Synthesize（分发再汇总）**——五十个文件塞不进一个疲倦的上下文。拆开、多跑、在屏障处合并。

```text
  task ──► ● ● ● ● ══屏障══► synthesize
```

**Adversarial Verification（对抗验证）**——狐狸不该给鸡窝打分。工人产出；独立验证者来挑刺；只留下还站得住的。

```text
  worker ──► verifier
         ├──► verifier
         └──► verifier   → 留下仍然成立的
```

**Generate-And-Filter（生成再过滤）**——你要的是选项，不是第一个听起来机灵的念头。许多生成器，再加一把量尺（和去重）。

同一工具箱里还有 **Classify-And-Act**（路由到专家）、**Tournament**（两两比较出冠军）、**Loop Until Done**（“还有新发现？”为是就继续派，并加上硬性 `budget`）。只有额外成本能买到更清楚或更稳妥的结果时，才去借一种风格。

<details>
<summary>每种模式如何落到本课原语</summary>

| 模式 | 原语速写 | 什么时候别用 |
|------|----------|--------------|
| Classify-And-Act | `agent` → 分支 → `agent` | 每件东西其实都该同样处理 |
| Fanout-And-Synthesize | `pipeline` / `parallel` → 合并 | 一趟已经装得下 |
| Adversarial Verification | 产出 → `parallel(verify)` → 过滤 | 答错很便宜 |
| Generate-And-Filter | `parallel(gens)` → 过滤 | 好答案空间本来就很小 |
| Tournament | 两两裁判 `agent` | 清晰量尺一趟就能选出赢家 |
| Loop Until Done | `while` + 停止 + `budget` | 工作量已知 |

```python
# 教学示意 — 先分类再行动
kind = await ctx.agent("给这张工单分类", schema=KIND)
if kind["type"] == "billing":
    return await ctx.agent("处理账单…")
```

组合是常态：深度调研常常叠成 分发 → 过滤 → 验证 → 汇总。

</details>

### 当 workflow 碰上不可信输入

工单和用户反馈是不可信的。*读*它们的 agent，不该同时握着能开 PR 的钥匙。留一道气闸：读者只读，只递结构化摘要；受信任的 actor 根据摘要行动——从不碰原始正文。

```text
  积压（不可信）
       │
       ▼
  ┌─ 隔离区（只读） ────────┐
  │  readers → 去重 → 摘要   │
  └────────────┬────────────┘
               ▼
  ┌─ 受信任（高权限） ──────┐
  │  actor → 修复 / 升级人工 │
  └─────────────────────────┘
```

<details>
<summary>官方隔离分流图</summary>

![隔离分流](images/quarantine-triage.png)

*读者在隔离区里分类、去重；高权限工具住在受信任一侧。积压永远睡不着时，可以和 `/loop` 配对。*

</details>

## 跟着 `review-changes` 走一圈——一种组合

示例不是“一种模式”。它是 **Fanout-And-Synthesize**，里面嵌着 **Adversarial Verification**——结尾再轻轻过滤，只留下 `isReal` 的 finding。

```text
  correctness ── 审计 ── 验证 ──┐
  security    ── 审计 ── 验证 ──┤── 确认列表
  performance ── 审计 ── 验证 ──┤
  style       ── 审计 ── 验证 ──┘
       分发           ▲              汇总
                      └── 每条 finding 的怀疑式验证
```

`pipeline(DIMENSIONS, audit, verify)` 给每个维度自己的桌子。`verify` 里对验证 agent 做 `parallel`，就是对抗那一和弦。列表过滤是汇总。`phase` 标出 Review → Verify；journal 记住每次 `agent()`，暂停也不会重做审计。

那三种走偏，会感觉自己最爱的座位被撤了：舰队不能在两个维度后收工，作者不当裁判，拓扑也不会在中途漂移。

```python
# 来自 code.py — 可运行样本（节选）
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"确认了 {len(confirmed)} 个真实问题")
    return {"confirmed": confirmed}
```

<details>
<summary>怎样挂在 s15 上（却不取代它）</summary>

s15 仍是宿主循环。s16 只多了一个 `Workflow` 工具。你（或模型）报一个已保存的名字；适配器跑脚本。

在产品里，这次运行可以待在后台、带着通知。教学 CLI 把 `demo` / `resume` 放在前台，好让阶段和缓存命中容易看见。想法相同；简化之处我们会明说。

</details>

## 转一转这颗宝石：谁握着计划？

有用的问题不是“几个 agent？”，而是**谁拥有拓扑**，半成品的碗放在哪。

| 邻居 | 谁握着计划 | 中间结果住哪 | 最适合 |
|------|------------|--------------|--------|
| [s06 子 Agent](../s06_subagent/) | 模型，一次性 | 多半丢掉 | 隔离一个脏的子任务 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead + 邮箱 | 共享任务 / 消息 | 长跑的同伴 |
| [s15 Agent Harness 集成](../s15_integrated_harness/) | 模型在一个循环里 | `messages[]` | 累积型 coding agent |
| **s16 Workflow** | **脚本** | **变量 + journal** | 结构化分发与验证 |
| [s17 Goal Loop](../s17_goal_loop/) | 停止时的判断器 | 对话当证据 | “整个目标做完了吗？” |

更便宜的路经常就够：skill 当软计划、一小段多 agent 闲聊、手写静态编排，或更大的单轮模型调用。当结构必须比单个上下文活得更久，再伸手去拿 workflow——不是因为“专家团”听起来很酷。

## 什么时候先放回架子上

Workflow 要花 token，也有协调成本。大多数普通写代码，并不需要五人评审团。

问问这活是否真的想要更多算力和一层定制 harness。若普通的 s15 一轮——或一个老实的 s06 子 agent——就够，就停在那儿。克制也是设计思想的一部分。

## 试一下

```bash
python s16_workflow_runtime/code.py          # s15 宿主 + Workflow（真实 API）
python s16_workflow_runtime/code.py demo     # 固定数据；看阶段
python s16_workflow_runtime/code.py resume   # 同一 runId；期待缓存命中
```

看 Review 让给 Verify。完整续跑时 agent 翻成 `cached`，并应看到 `agents=0 tokens=0`——笔记本在说：没有什么需要重新加热。

## 接下来

s16 讲一批活怎么跑。[s17 Goal Loop](../s17_goal_loop/) 在门口问另一个问题：该停，还是再来一轮？

<!-- translation-sync: zh@v17, en@v17, ja@v17 -->
