# s16: Workflow Runtime — 把菜谱写进代码

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *“一轮轮聊天，像每隔十秒给厨师发一条短信。Workflow 是厨房能照着做的菜谱。”*
>
> **Harness 层**: 编排 — 单 agent 循环之上，再跑一套多 agent 脚本。
>
> 信任模型，工程化 harness。Workflow，就是把这句话落到编排层。

---

想象你跟朋友用微信一起做饭。“先切洋葱。”等回音。“切好了吗？”然后热锅、放盐。一道菜还能撑住这种节奏；二十桌宴席就不行了——步骤会丢，话会重复，手机一死还得从头来。

模型既当厨师又当记事本时，感觉就是这样：计划与动手挤在同一段对话里。**Workflow** 则是写好的菜谱。厨房（runtime）按谱做，帮手（子 agent）负责尝和判断，半成品放在台面上的碗里，而不是塞进群聊记录。

## 为什么还要另一层 harness？

默认的 Claude Code harness 已经很擅长“写代码那种形状”的活：改一点、跑一下、看报错、再试。一个循环、一颗脑袋，能做出不少工艺。

可有些活是另一种形状——深度调研、安全排查、agent teams、要铺开审查一整片改动。这类事，人们早就习惯在上面再搭一层定制 harness。你当然可以事先用 SDK 手写；也可以——这才是有意思的地方——让 Claude **为这次任务**起草一个 harness，跑起来，好用的再留下来。

课程那句口号往上提一层：每一步里信任模型；步骤怎么排，由你来定结构。

## 长对话里你会看见的走偏

从 s01 到 s15，计划与执行共享同一个上下文。下一步取决于刚才的发现时，这很舒服。

可一旦任务变长、要大规模并行、结构又死板，或需要一个挑剔的第二意见，它就会发脆。你若耐心看一段很长的聊天，会撞见熟面孔：做到五十项里的三十五就宣布完工；让它批改自己的作业，分数总是偏甜——狐狸给鸡窝打分；多轮对话和压缩过后，那句轻轻的“别动 X”渐渐听不见了。

Claude Code 的设计者把这些叫做 agentic laziness、self-preferential bias、goal drift。名字不如感觉重要：同一个窗口既要干活，又要记住计划。对话历史太软，扛不住并行、稳定的结果形状，以及崩了还能续上。审查很多文件、先调研再验证、按同一方式迁移 N 个模块——这些活的形状事先就清楚。软记忆不够用。

## 点子落下的那一下

假如计划住在代码里呢？

帮手仍然负责想——每人一张干净桌子，一件专注的事。**脚本**掌管循环、分发和合并。中间结果待在变量和 journal 里，不进对话。想偷懒提前收工的习惯，更难叫停整支队伍；自我检查的偏心，会撞上一个不是作者本人的第二帮手；漂移也难下手，因为拓扑不再由一个疲倦的叙述者每轮改写。

一句话：workflow 把编排从“靠聪明”挪到“靠结构”。模型仍在每次 `agent()` 里做判断；地图归脚本管。

![Workflow Runtime 总览](images/workflow-runtime-overview.svg)

一次 `Workflow` 工具调用启动这次运行。进度在旁边轻轻响；最后一条工具结果带回启动信息、结果和任务状态。

## 同一间厨房，两扇门

Claude Code 对入口说得很直白。

有时模型为*这次*任务写一段编排用的 JavaScript，以 `script` 交出来（或之后改 `scriptPath`）。这是**动态**那扇门——问题还热着，就裁出一件合身的 harness。

有时好脚本已经进了例如 `.claude/workflows/`。你用 `name` 和 `args` 再请它出来。这是**已保存**那扇门——一次值得留下的运行，沉淀成可复用的卡片。

本课之外还有表亲：**静态** harness，用 Agent SDK 或 `claude -p` 事先写好。它们得扛住所有边角，所以往往更泛。动态的是为这块布现裁的；合身了再存。

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

## 厨房里的几个动词

想象学校义卖要烤许多蛋糕。每张桌子都是搅拌 → 烘烤 → 装箱。帮手负责尝；菜谱决定先后。

`agent(...)` 是请一个帮手做一件事。`pipeline(items, *stages)` 是默认：每块蛋糕自己走完各阶段，所以一块在装箱时，另一块可能还在搅拌。`parallel(...)` 是等齐——所有托盘都回来才往下——只有下一步真的需要全部结果时才值得，比如尝完再写评分表。

旁边还有更轻的词：`phase` 在进度板上报站，`log` 喊一句短话，`workflow` 嵌一份更小的菜谱，`args` 是食材清单，`budget` 是还能烧多少烤箱分钟（token）。

```python
# 每个审查维度自己走完 审计 → 验证。
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

## 模式：用得着才拿

不必背目录。看清示例在干什么，手里就有三种风格。

它把改动**分发**到各个审查维度，每人一张干净桌子，再**汇总**成一份确认列表——fan-out-and-synthesize。碎片若挤在同一个嘈杂上下文里会互相串味时，这一招值钱。

验证阶段里，第二个帮手专门来挑每条 finding 的刺——adversarial verification，结构上回答“别给自己的作业打高分”。

留下来的，是对生成物做过滤。Generate-and-filter：候选进来，过关的留下。

同一工具箱里还有 classify-and-act、tournament、loop-until-done，以后都会遇见。只有额外成本能买到更清楚或更稳妥的结果时，才去借一种风格。

## 让下一阶段接得住的答案

帮手若回来写散文，下一阶段很难把 finding 和 verdict 对齐。传入 `schema`。运行时要 JSON、做校验，并给**一次**重试。再不对，这次调用报错——而舰队在失败时怎样仍然温和，下一节就说到。

```python
out = await ctx.agent(
    f"检查这段变更里有没有{dimension}相关的问题：\n{changes}",
    schema=FINDINGS_SCHEMA,
    label=f"audit:{dimension}",
)
```

跟你聊天可以继续用自然语言。流水线需要接口对得上。

## 一个托盘糊了的时候

不能因为一个帮手烤箱失手，整支队伍停工。

在 `parallel` 里，失败的 thunk 在该槽位变成 `null` / `None`，gather 本身不会拒绝。在 `pipeline` 里，某个 stage 失败会把**那个 item** 置成空，并跳过它后面的 stage；别的 item 继续往前走。合并前小心过滤——`if r`，在 JS 里常见 `.filter(Boolean)`。

```python
verdicts = await ctx.parallel([...])  # 有些格子可能是 None
confirmed = [
    f for f, v in zip(findings, verdicts)
    if v and v.get("isReal")
]
```

## 一本可以重开的笔记本

每次运行都有一个 `runId`。每个 `agent()` 结束，磁盘上的 journal 就多一行——按你**召唤**帮手的顺序记，而不是按他们从烤箱回来的先后。

续跑（`resume_from_run_id` / `resumeFromRunId`）仍从脚本开头走，只是更客气：按调用顺序，与下一条 journal 比对；最长未改前缀直接从缓存回放；碰到第一个改过或未完成的调用，前缀断开——之后全部实跑，即便笔记本更后面还躺着旧 key，也不能跳过裂缝偷懒命中。

这也是真正的 JS workflow 运行时禁止 `Date.now()`、`Math.random()` 和裸 `new Date()` 的原因。时钟和骰子会让 prompt 或调用顺序晃一下，笔记本就对不齐了。这个 Python 演示不会完整沙箱那些东西。脚本仍写成确定性的吧。

```text
journal:  [A ✓] [B ✓] [C ✓] [D ✓]
续跑:     A 命中 → B 命中 → C 改过 → D 实跑
```

## 跟着 `review-changes` 走一圈

四个维度共用一条两阶段路径——先铺开，再对抗验证，留下活下来的：

```text
correctness ── 审计 ── 验证 ──┐
security    ── 审计 ── 验证 ──┤── 确认过的问题
performance ── 审计 ── 验证 ──┤
style       ── 审计 ── 验证 ──┘
```

Review 让每个审计员坐自己的桌子，正确性的闲聊不至于淌进安全性。Verify 把每条 finding 交给不是作者的怀疑者。只留下真的，再按严重程度排好。那三种走偏，会感觉自己最爱的座位被撤了。

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"确认了 {len(confirmed)} 个真实问题")
    return {"confirmed": confirmed}
```

## 挂在 s15 上，并不取代它

s15 仍是宿主循环。s16 只多了一个名叫 `Workflow` 的工具。你（或模型）报一个已保存的名字；适配器找到脚本再跑。

在真正的产品里，这次运行可以待在后台、带着通知，会话照样能应你。教学 CLI 把 `demo` / `resume` 放在前台，好让你看清阶段和缓存命中。想法相同；简化之处我们会明说。

主循环不会变成 workflow 引擎。它只是多借一把工具，就像借 `bash` 或 `task`。

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

<!-- translation-sync: zh@v13, en@v13, ja@v13 -->
