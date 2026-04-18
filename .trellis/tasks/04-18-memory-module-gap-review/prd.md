# brainstorm: memory module gap review

## Goal

基于当前 `coding-deepgent` 的记忆实现和 cc/Claude Code 的记忆相关源码，明确“记忆模块”目前已经覆盖的功能、还缺的具体功能，以及下一轮应该优先补哪一类功能。

## What I already know

* 当前 `coding-deepgent` 已经完成一轮 integrated memory closeout：
  * 四类型长期记忆 `user / feedback / project / reference`
  * `save_memory / list_memory / delete_memory`
  * bounded recall / render
  * `feedback` 对少量高价值动作直接生效
  * recovery/resume 可见面里已经分开显示 `Long-term memory` 和 `Current-session memory`
* 当前 `coding-deepgent` 的长期记忆仍然是 store-backed 的运行时能力，不是持久落盘 backend。
* 当前 `coding-deepgent` 仍没有自动提取长期记忆、子 agent 私有记忆、向量检索、后台维护。
* cc 侧长期记忆主线来自：
  * `src/memdir/*`
  * `src/services/SessionMemory/*`
  * `src/tools/AgentTool/agentMemory.ts`
  * `src/tools/AgentTool/agentMemorySnapshot.ts`
* cc 的长期记忆核心是：
  * 闭合四类型
  * 只保存不可推导信息
  * frontmatter + MEMORY.md 索引
  * 记忆老化/信任提醒
  * user/project/local 以及 agent memory scope
  * session memory 周期性提取与 agent memory snapshot

## Assumptions (temporary)

* 用户现在要的不是立即继续编码，而是先把“当前实现相对 cc 还差哪些功能”讲清楚。
* 本轮主要输出 gap review 和下一步目标选择，不一定直接进入实现。
* 评价标准以“用户能得到什么功能”为主，而不是是否逐字照搬 cc 源码。

## Open Questions

* 下一轮记忆模块目标，优先补哪一类差距：
  * 更可靠的长期保留与管理，
  * 更聪明的记忆读取与过时判断，
  * 还是子 agent / agent 私有记忆？

## Requirements (evolving)

* 必须 source-backed，对照当前本地代码和 cc 相关源码/文档。
* 输出要按“具体功能差距”分组，不要只给术语。
* 需要明确：
  * 已对齐功能
  * 部分对齐功能
  * 明确缺失功能
* 最后要给出 2–3 个可选的下一轮目标包络，并推荐一个。

## Acceptance Criteria (evolving)

* [ ] 给出当前记忆模块相对 cc 的功能差距清单
* [ ] 功能差距按具体用户收益分组，而不是抽象层次
* [ ] 给出下一轮目标的 2–3 个选项
* [ ] 给出推荐选项和理由

## Definition of Done (team quality bar)

* 结论写入 PRD
* 差距描述可直接转为后续任务范围
* 推荐方向清晰，不依赖口头记忆

## Out of Scope (explicit)

* 本轮不直接进入实现
* 本轮不重新做已经完成的 memory closeout
* 本轮不讨论 tutorial/reference 层 UI

## Technical Notes

* `.trellis/project-handoff.md`
* `.trellis/plans/coding-deepgent-h01-h10-target-design.md`
* `/tmp/claude-code-book/第二部分-核心系统篇/06-记忆系统-Agent的长期记忆.md`
* `/root/claude-code-haha/src/memdir/*`
* `/root/claude-code-haha/src/services/SessionMemory/*`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemory.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
* `coding-deepgent/src/coding_deepgent/memory/*`
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`
* `coding-deepgent/src/coding_deepgent/sessions/long_term_memory.py`

## Research Notes

### Current local strengths

* Long-term memory types are already aligned to `user / feedback / project / reference`.
* Long-term memory has structured save/list/delete and bounded render.
* Feedback memories can already affect a few concrete actions, not only prompt text.
* Recovery/resume already shows long-term memory separately from current-session memory.

### Current local gaps vs cc

* No durable memory survives restart yet.
* No file-based memory entries or human-readable memory index.
* No explicit stale-memory trust/verification workflow at recall time.
* No smarter relevance selection beyond bounded deterministic recall.
* No automatic suggestion/extraction of durable memories from conversation.
* No per-agent memory scope and no agent snapshot/sync path.
* Current-session memory exists, but not the richer background extraction/update behavior cc has.
