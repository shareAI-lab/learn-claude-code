# brainstorm: compare subagent vs cc gap

## Goal

基于当前 `coding-deepgent/` 主线实现，重新判断“子 agent 相比 Claude Code / 《御舆》Chapter 9 还差多少”。本次目标是做 source-backed 差距评估与范围确认，不直接改代码。

## What I already know

* 用户给出的主要参考是《御舆》在线阅读页 Chapter 9：`https://lintsinghua.github.io/#ch09`。
* `coding-deepgent` 当前 roadmap 已将：
  * `H11 Agent as tool and runtime object` 标为 `implemented`
  * `H12 Fork/cache-aware subagent execution` 标为 `implemented-minimal`
* 旧的 `.trellis/tasks/04-17-subagent-multiagent-ch09-review/prd.md` 和
  `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
  已经过时，原因是之后又完成了：
  * `L3-a H11/H12 subagent sidechain transcript`
  * `L5-b deferred boundary ADR refresh`
  * roadmap/dashboard 对 H11/H12 状态的刷新
* 当前代码里已经存在真实的子 agent / fork 运行时，而不是只有规划：
  * `run_subagent(task, agent_type="general" | "verifier", ...)`
  * `run_fork(intent, ...)`
  * `AgentDefinition` with `description`, `when_to_use`, `tool_allowlist`,
    `disallowed_tools`, `max_turns`, `model_profile`
* 当前已经落地的关键 H11/H12 能力：
  * `general` / `verifier` 都走真实 child `create_agent` 路径
  * child tool surface 仍是只读边界：`read_file`, `glob`, `grep`, `task_get`,
    `task_list`, `plan_get`
  * `verifier` 绑定 durable `plan_id`，并把 verdict 以 evidence 写回 session ledger
  * parent session JSONL 已持久化 sidechain transcript，包含
    `parent_message_id` / `parent_thread_id` / `subagent_thread_id`
  * `run_fork` 已经是独立入口，不混入普通 `run_subagent`
  * `run_fork` 直接继承 parent `rendered_system_prompt` 与
    `visible_tool_projection`
  * `run_fork` 输出已包含 `rendered_prompt_fingerprint`、
    `tool_pool_identity`、`placeholder_layout`
  * fork 已有递归防护：runtime entry guard + marker scan
* 当前仍然明显不具备的 cc / Ch09 深水区能力：
  * 三种 agent 来源完整体系（built-in / custom / plugin）尚未落地
  * 丰富内置 agent catalog 尚未落地，目前只有 `general` / `verifier`
  * per-agent hooks / skills / MCP additive / permission mode override 尚未落地
  * async/background child lifecycle、cleanup inventory、kill / notification /
    progress tracker 尚未落地
  * full fork/cache parity 尚未落地：placeholder tool-result 重建、replacement
    state continuity、resume continuity、真正 cache-safe prefix contract 仍未完成
* 当前实现里还有一个重要“表面 contract > 实际执行”的差距：
  * `run_subagent_task` 计算了 `effective_max_turns` 后直接丢弃
  * `run_fork_task` 直接 `del max_turns`
  * 也就是 schema/definition 有 `max_turns`，但运行时没有真正使用

## Assumptions (temporary)

* 用户口中的 “cc” 大概率是指 Claude Code / 《御舆》Chapter 9 所描述的子智能体与 Fork 体系，而不是 Ch10 coordinator 多智能体编排。
* 本轮更像 parity audit / brainstorming，而不是进入实现阶段。
* “差多少” 需要同时区分两种口径：
  * `MVP local slice`：是否已经达到本地最小可用边界
  * `full cc parity`：距离 Claude Code Chapter 9 完整体系还有多远

## Open Questions

* 这次比较的口径是否只看 Chapter 9 子智能体 / Fork，还是也要顺带把真实 Claude Code 的完整子 agent runtime（超出 Ch09 摘要的部分）一起算进去？

## Requirements (evolving)

* 用当前代码与当前 roadmap，而不是用旧 brainstorm 结论，重新判断差距。
* 明确区分：
  * 已实现
  * 已实现但只是 minimal slice
  * 明确 deferred
  * 仍然缺失 / contract 未兑现
* 输出里要把 “已经不差太多” 和 “其实还差很远” 放在不同口径下说明，避免一句话混淆。
* 如果给百分比，只能给近似量级，并解释估算口径。
* 要指出最影响判断的 1-3 个关键缺口。

## Acceptance Criteria (evolving)

* [ ] 能基于当前代码说明 H11/H12 已经落地到什么程度。
* [ ] 能指出旧调研中哪些 gap 已经不再成立。
* [ ] 能指出当前仍然缺失的 cc / Ch09 关键能力。
* [ ] 能给出至少两种口径下的差距判断：local MVP vs full cc parity。

## Definition of Done (team quality bar)

* 结论必须同时有本地代码/任务证据和外部章节证据。
* 不把 roadmap 的 `implemented` 直接当成 full parity 结论。
* 不把明确 deferred 的能力误判为“实现漏掉了”。
* 如果发现 contract 与实现不一致，要明确单独指出。

## Out of Scope (explicit)

* 不直接修改 `coding-deepgent` 代码。
* 不扩展到 Ch10 coordinator / mailbox / SendMessage，除非用户明确要求。
* 不对全书逐章审计。

## Technical Notes

* External sources inspected:
  * `https://lintsinghua.github.io/#ch09`
  * `https://github.com/lintsinghua/claude-code-book`
  * `第三部分-高级模式篇/09-子智能体与Fork模式.md`
* Local sources inspected:
  * `coding-deepgent/src/coding_deepgent/subagents/tools.py`
  * `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
  * `coding-deepgent/tests/test_subagents.py`
  * `.trellis/spec/backend/task-workflow-contracts.md`
  * `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
  * `.trellis/tasks/04-17-subagent-multiagent-ch09-review/prd.md`
  * `.trellis/tasks/04-17-l5b-deferred-boundary-adr-refresh/prd.md`
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

## Research Notes

### Chapter 9 expected effect summary

Chapter 9 关注的不是“有没有一个叫 subagent 的工具”，而是四类效果：

* 子智能体作为独立 runtime object 的生成与生命周期管理
* Fork 作为 same-config sibling branch 的缓存友好继承
* agent definition / 来源体系（built-in / custom / plugin）
* verifier / adversarial verification 这类专业 agent 的工程角色

### Current local evaluation snapshot

**已经对上的最小核心**

* bounded read-only `general` / `verifier` child runtime
* verifier-plan boundary + evidence persistence
* sidechain transcript audit
* explicit `run_fork` entry with rendered-prompt/tool snapshot lineage
* fork recursion guard

**已经有形，但还是 partial**

* `AgentDefinition` 结构已经有，但 catalog 仍极小
* fork continuity metadata 已有，但 full cache-safe execution contract 尚未完成
* roadmap 认为 H12 `implemented-minimal`，不是 full parity

**仍明显缺失**

* custom/plugin agents
* async/background agent lifecycle
* richer cleanup / notification / progress / resume
* full fork placeholder replacement-state and resume continuity
* actual enforcement of `max_turns`

### Priority proposal

**P0: must-fix inside the already-claimed local surface**

* `max_turns` contract debt:
  * `run_subagent_task()` computes `effective_max_turns` and drops it
  * `run_fork_task()` drops `max_turns` entirely
  * This is the clearest “schema says yes, runtime does nothing” gap
* `model_profile` contract debt:
  * `AgentDefinition.model_profile` exists, but child runtime still always uses
    `build_openai_model()` without per-agent routing
  * Either wire it, or explicitly narrow the contract

**P1: highest-value parity work if we want to get closer to cc Ch09**

* expand agent catalog and source model:
  * richer built-in catalog
  * custom agent definitions
  * plugin-provided agents
* deepen fork/cache continuity:
  * real placeholder tool-result reconstruction
  * replacement-state continuity
  * resume-safe fork prefix continuity
* add runtime-object lifecycle beyond synchronous MVP:
  * background/async child lifecycle
  * cancellation / cleanup / notification / progress

**P2: explicitly deferred under current product boundary**

* mailbox / SendMessage / coordinator team runtime
* full team orchestration and worker collaboration plane
* UI-heavy task panel / progress UX details
* provider-specific cache/cost instrumentation polish
