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

模型既当厨师又当记事本时，感觉就是这样：计划与动手挤在同一段对话里。**Workflow** 则是写好的菜谱。厨房（一个小 runtime）按谱做，帮手（子 agent）负责尝和判断，半成品放在台面上的碗里——变量和 journal——而不是塞进群聊。

## 为什么还要另一层 harness？

默认的 Claude Code harness 已经很擅长“写代码那种形状”的活：改一点、跑一下、看报错、再试。一个循环。一颗脑袋。能做出不少工艺。

可有些活需要**叠一层定制 harness**——深度调研、安全排查、agent teams、要铺开审查一整片改动。你可以事先用 SDK 手写那一层；也可以——这才是有意思的地方——让 Claude **为这次任务**起草一个 harness，跑起来，好用的再留下来。

Claude Code 的设计者说得很直白：dynamic workflow 让模型当场为自己写下多 agent 的 harness。课程那句口号往上提一层：每一步里信任模型；步骤怎么排，由你来定结构。

## 长对话里你会看见的走偏

从 s01 到 s15，计划与执行共享同一个上下文。下一步取决于刚才的发现时，这很舒服。

可一旦任务变长、要大规模并行、结构又死板，或需要一个挑剔的第二意见，它就会发脆。你若耐心看一段很长的聊天，会在学会术语之前，先撞见熟面孔。

做到五十项里的三十五就宣布完工。让它批改自己的作业，分数总是偏甜——狐狸给鸡窝打分。多轮对话和压缩过后，那句轻轻的“别动 X”渐渐听不见了。

这些就是 agentic laziness、self-preferential bias、goal drift。名字不如感觉重要：同一个窗口既要干活，又要记住计划。对话历史太软，扛不住并行、稳定的结果形状，以及崩了还能续上。审查很多文件、先调研再验证、按同一方式迁移 N 个模块——这些活的形状事先就清楚。软记忆不够用。

## 点子落下的那一下

假如计划住在代码里呢？

帮手仍然负责想——每人一张干净桌子，一件专注的事。**脚本**掌管循环、分发和合并。中间结果待在变量和 journal 里，不进对话。想偷懒提前收工的习惯，更难叫停整支队伍；自我检查的偏心，会撞上一个不是作者本人的第二帮手；漂移也难下手，因为拓扑不再由一个疲倦的叙述者每轮改写。

一句话：**workflow 把编排从「智力」挪到「结构」。** 模型仍在每次 `agent()` 里做判断；地图归脚本管。

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

一次 `Workflow` 工具调用启动这次运行。进度在旁边轻轻响；最后一条工具结果带回启动信息、结果和任务状态。

## 两扇门——门外还有个表亲

Claude Code 对入口说得很直白。

有时模型为*这次*任务写一段编排用的 JavaScript，以 `script` 交出来（或之后改 `scriptPath`）。这是**动态**那扇门——问题还热着，就裁出一件合身的 harness。

有时好脚本已经进了例如 `.claude/workflows/`。你用 `name` 和 `args` 再请它出来。这是**已保存**那扇门——一次值得留下的运行，沉淀成可复用的卡片。

门外还有表亲：**静态** harness，用 Agent SDK 或 `claude -p` 事先写好。它们得扛住所有边角，所以往往更泛。动态的是为这块布现裁的；合身了再存。

![静态 harness 与动态 workflow](images/dynamic-vs-static.png)

*来自 Claude Code 设计文：同一个问题，两套 harness。左边——固定的搜索→验证→摘要，终点是一份泛泛的研究报告。右边——读你的 billing 代码、分叉、再请来魔鬼代言人，最后给出具体建议。*

**这一章是 Python 教学运行时。** 同样的想法，每行都能读。演示按名字挂了一个已保存的 workflow；概念和 Claude Code 的脚本世界一一对应。我们不会再说“模型不能提交可执行代码”——那从来不是 Claude Code 的真相。这里只是不嵌入完整的 JS 解释器。

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

## 脚本会说的三个动词

想象学校义卖要烤许多蛋糕。每张桌子都是搅拌 → 烘烤 → 装箱。帮手负责尝；菜谱决定先后。

![Workflow 原语：agent、parallel、pipeline](images/workflow-primitives.png)

*官方原语卡片：一个 `agent`，以及两种“跑很多”的方式——`parallel`（等齐屏障）与 `pipeline`（每个 item 自己流过各阶段）。*

`agent(prompt, opts?)` 是请一个帮手做一件事。带上 `schema`，答案会变成校验过的 JSON——下一阶段接得住的接口——第一次不对还给一次重试。真正的 Claude Code 还可以选 `model`、`isolation`（worktree / remote）和 `agentType`；本课教学运行时把表面收小一点，好让每一行都读得完。

`pipeline(items, *stages)` 是多阶段工作的默认：每块蛋糕自己走完各阶段，一块在装箱时，另一块可能还在搅拌。阶段之间没有等齐屏障。

`parallel(thunks)` 是等齐——所有托盘都回来才往下。只有下一步真的需要全部结果时才值得，比如尝完再写评分表。

旁边还有更轻的词：`phase` 报站，`log` 喊一句，嵌一层 `workflow`，`args` 是食材清单，`budget` 是烤箱分钟（token）。

```python
# 每个审查维度自己走完 审计 → 验证。
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

帮手失手时，舰队仍然温和。`parallel` 里失败的 thunk 在该槽位变成 `null`，gather 本身不会拒绝；`pipeline` 里某个 stage 失败会把**那个 item** 置空并跳过后续 stage，别的 item 继续往前。合并前小心过滤。

厨房暂停了呢？每次运行都有 `runId` 和磁盘上的 journal——按你**召唤**帮手的顺序记的笔记本。续跑从脚本开头走，回放**最长未改前缀**；碰到第一个改过或未完成的调用，之后全部实跑。所以真正的 JS 运行时禁止 `Date.now()` 和 `Math.random()`：时钟和骰子会让笔记本对不齐。这个 Python 演示不会完整沙箱那些——脚本仍写成确定性的吧。

```text
journal:  [A 好] [B 好] [C 好] [D 好]
续跑:     A 命中 → B 命中 → C 改过 → D 实跑
```

## 会写菜谱之后——模式工具箱

动词是面粉和火候。人们反复发明的，是少数几种*形状*。把它们想成工具箱，不是必点菜单。

![六种 Workflow 模式](images/six-workflow-patterns.png)

*官方六模式网格——工具箱，不是必点菜单。脚本掌管拓扑；本课用 `agent` / `parallel` / `pipeline` / `phase` / journal 把每种形状说出来。*

**Classify-And-Act（分类再行动）。** 痛点：一个万金油帮手样样稀松。形状：分类器看一眼，再路由到专家 A、B 或 C。本课：一次带 `schema` 的 `agent` 返回标签，脚本分支到对的后续 `agent`（或嵌一层 `workflow`）。每件东西其实都该同样处理时，就别用。

**Fanout-And-Synthesize（分发再汇总）。** 痛点：五十个文件塞不进一个疲倦的上下文，挤在一起还会串味。形状：拆开、多跑、等齐、再合并。本课：每件有自己阶段用 `pipeline`；下一步必须凑齐全部结果用 `parallel`；合并写在 gather 之后的普通 Python。三五个相关文件一趟就能看完时，就别用。

**Adversarial Verification（对抗验证）。** 痛点：狐狸给鸡窝打分。形状：工人产出；独立验证者来反驳；只留下幸存者。本课：一次生产 `agent`，再 `parallel` 一组验证 `agent`（最好带 schema），然后过滤。`phase` 标出 Review 再 Verify。答错代价很低时就别用。

**Generate-And-Filter（生成再过滤）。** 痛点：你要的是选项，不是第一个听起来机灵的念头。形状：许多生成器把想法倒进“量尺 + 去重”。本课：`parallel` 生成，再在脚本里过滤（或一个裁判 `agent`）。生成很贵时 journal 特别有用。好答案空间本来就很小，就别用。

**Tournament（锦标赛）。** 痛点：品味和排序上，绝对分数糊成一团。形状：两两比较、淘汰支架、冠军——相对判断胜过孤独打分。本课：脚本里多轮 pairwise 裁判 `agent`，直到剩一个。清晰量尺一趟就能选出赢家时，就别用。

**Loop Until Done（接到完为止）。** 痛点：你不知道矿里还要挖几轮。形状：只要“还有新发现？”为是就继续派工；连续空轮就停。本课：`while` 包着 `agent`/`parallel`，带 schema 的停止检查，再加硬性 `budget`。长挖可能暂停时配上 journal。工作量已知时，固定 `pipeline` 更简单。

几种有了面孔之后，工具箱一眼就能看清：

| 模式 | 原语速写 | 什么时候伸手 |
|------|----------|--------------|
| Classify-And-Act | `agent` → 分支 → `agent` | 条目需要不同专家 |
| Fanout-And-Synthesize | `pipeline` / `parallel` → 合并 | 许多干净桌子，再一份摘要 |
| Adversarial Verification | 产出 → `parallel(verify)` → 过滤 | 答错很贵 |
| Generate-And-Filter | `parallel(gens)` → 量尺过滤 | 先要选项，再要品味 |
| Tournament | 两两裁判 `agent` | 排序/品味却没有锋利刻度 |
| Loop Until Done | `while` + 停止 + `budget` | 埋着不知多少活 |

组合是常态。深度调研常常叠成：分发 → 过滤 → 验证 → 汇总。我们的示例，是两个音符的一小段和弦。

### 当 workflow 碰上不可信输入

工具箱旁边还值得留一个形状：**quarantine triage（隔离分流）**。工单、bug 报告、用户反馈都是不可信的。你不会希望*读*它们的 agent，同时也握着能开 PR 的钥匙。

![隔离分流](images/quarantine-triage.png)

*读者留在只读的隔离区里，分类、去重，只把结构化摘要递过去。高权限工具住在受信任一侧——它们只根据摘要行动，从不碰原始正文。积压永远睡不着时，可以和 `/loop` 配对。*

落到本课原语，仍是脚本和 agent：一串低权限 reader `agent` 的 `pipeline` 或 `parallel`，摘要进变量，再交给另一个 actor `agent`（或嵌一层 `workflow`）去写。真正值钱的是气闸——谁被允许看见原始文本。

## 跟着 `review-changes` 走一圈——一种组合

示例不是“一种模式”。它是 **Fanout-And-Synthesize**，里面嵌着 **Adversarial Verification**——结尾再轻轻做一层 generate-and-filter：只留下 `isReal` 的 finding。

```text
correctness ── 审计 ── 验证 ──┐
security    ── 审计 ── 验证 ──┤── 确认过的问题
performance ── 审计 ── 验证 ──┤
style       ── 审计 ── 验证 ──┘
         分发（fanout）                    汇总（synthesize）
              └── 每条 finding：怀疑式验证 ──┘
```

`pipeline(DIMENSIONS, audit, verify)` 给每个维度自己的桌子。`verify` 里对验证 agent 做 `parallel`，就是对抗那一和弦。普通的列表过滤是汇总。`phase` 标出 Review 再 Verify；journal 记住每次 `agent()`，暂停也不会重做审计。

那三种走偏，会感觉自己最爱的座位被撤了：舰队不能在两个维度后收工，作者不当裁判，拓扑也不会在中途漂移。

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"确认了 {len(confirmed)} 个真实问题")
    return {"confirmed": confirmed}
```

<details>
<summary>怎样挂在 s15 上，却不取代它</summary>

s15 仍是宿主循环。s16 只多了一个名叫 `Workflow` 的工具。你（或模型）报一个已保存的名字；适配器找到脚本再跑。

在真正的产品里，这次运行可以待在后台、带着通知，会话照样能应你。教学 CLI 把 `demo` / `resume` 放在前台，好让你看清阶段和缓存命中。想法相同；简化之处我们会明说。主循环多借一把工具，就像借 `bash` 或 `task`。

</details>

## 转一转这颗宝石：谁握着计划？

看看邻居，同一件东西会露出新的面。有用的问题不是“几个 agent？”，而是**谁拥有拓扑**，半成品的碗放在哪。

| 邻居 | 谁握着计划 | 中间结果住哪 | 最适合 |
|------|------------|--------------|--------|
| [s06 子 Agent](../s06_subagent/) | 模型，一次性 | 多半丢掉 | 隔离一个脏的子任务 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead 逐轮 + 邮箱 | 共享任务 / 消息 | 长跑的同伴 |
| [s15 Agent Harness 集成](../s15_integrated_harness/) | 模型在一个循环里 | 对话 `messages[]` | 累积型 coding agent |
| **s16 Workflow** | **脚本** | **变量 + journal** | 结构化分发与验证 |
| [s17 Goal Loop](../s17_goal_loop/) | 停止时的判断器 | 对话当证据 | “整个目标做完了吗？” |

更便宜的路经常就够：skill 当软计划、一小段多 agent 闲聊、手写静态编排，或更大的单轮模型调用。当结构必须比单个上下文活得更久，再伸手去拿 workflow——不是因为“专家团”听起来很酷。

## 什么时候先放回架子上

Workflow 要花 token，也有协调成本。大多数普通写代码，并不需要五人评审团。

动手前问一句：这活真的想要更多算力和一层定制 harness 吗？若普通的 s15 一轮——或一个老实的 s06 子 agent——就够，就停在那儿。克制也是思想的一部分：并行和分工得赚回自己的位置。

## 试一下

```bash
python s16_workflow_runtime/code.py          # s15 宿主 + Workflow（真实 API）
python s16_workflow_runtime/code.py demo     # 固定数据；看阶段
python s16_workflow_runtime/code.py resume   # 同一 runId；期待缓存命中
```

看 Review 让给 Verify；看完整续跑时 agent 从 `done` 翻成 `cached`。结尾是一份短短的确认列表——干净续跑会显示 `agents=0 tokens=0`，像笔记本在说：没有什么需要重新加热。

## 接下来

s16 讲一批活怎么跑。[s17 Goal Loop](../s17_goal_loop/) 在门口问另一个问题：该停，还是再来一轮？可重复的菜谱若还需要硬性的“做完”，可以和它一起用。

<!-- translation-sync: zh@v16, en@v16, ja@v16 -->
