# brainstorm: subagent multi-agent ch09 gap review

## Goal

回看已经完成的 cc-highlight alignment 讨论，判断我们在子智能体 / 多智能体方面到底具体讨论到了什么程度，并对照《御舆》Chapter 9（必要时补充 Chapter 10 的多智能体编排要求）判断是否已经满足这些要求。

## What I already know

* 当前 canonical roadmap 用 H11/H12 表示 subagent / fork 相关亮点，用 H13/H14 表示 mailbox / coordinator 多智能体亮点。
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/prd.md` 已经记录了 H11/H12 的 source-backed 讨论结论。
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md` 已经列出 cc 子智能体运行时、fork/cache、resume、lifecycle 的 gap matrix。
* 当前 topology 里 H11/H12 相关任务包括 `L2-a`（AgentDefinition + general runtime）和 `L3-a`（sidechain transcript），H13/H14 仍 deferred。
* `lintsinghua/claude-code-book` README 把第 9 章定义为“子智能体与 Fork 模式”，第 10 章定义为“协调器模式 — 多智能体编排”。
* 实时 task ledger 显示：
  * `L2-a H11/H12 AgentDefinition + general runtime` 已完成
  * `L2-c H01 role-based tool projection` 已完成
  * `L3-a H11/H12 subagent sidechain transcript` 仍是下一条未完成的 H11/H12 主线任务

## Assumptions (temporary)

* 用户说“子agent多agent方面”，严格来说至少需要同时看 Ch09 子智能体 / Fork 和 Ch10 Coordinator / multi-agent orchestration。
* 本次目标是 requirements review，不是立刻新增实现任务。

## Open Questions

* `placeholder_tool_result_layout` 第一版是否只需要固定空壳布局，还是要同时定义 tool-use pairing / replacement-state hooks？

## Requirements (evolving)

* 明确区分“已经具体讨论过”与“只是高层提过/明确 deferred”。
* 明确区分“满足 Ch09 子智能体要求”与“满足 Ch10 多智能体协调要求”。
* 输出应包含章节要求、已有讨论、当前状态、缺口判断。
* 给出“继续讨论 vs 先做前提条件”的推荐顺序。
* 用户已选择继续做 Ch09 深水区讨论，而不是先实现 `L3-a`，也不是跳到 Ch10 coordinator。
* 优先级按“收益最大”排，不按最小改动排。
* 采用长远架构视角，优先边界清晰、后续可扩展的方案。
* 不为了兼容旧方案、旧数据额外加桥接层或 fallback。
* 如果新结构更合理，可以直接替换旧抽象。

## Acceptance Criteria (evolving)

* [ ] 能指出 H11/H12/H13/H14 哪些已经被 source-backed 讨论覆盖。
* [ ] 能指出 Ch09 哪些要求已讨论、哪些未讨论或未满足。
* [ ] 能指出如果把“多 agent”扩大到 Ch10，目前哪些仍明显不满足。

## Definition of Done (team quality bar)

* 结论基于 Trellis 任务/PRD/roadmap 与外部章节内容，而不是凭记忆。
* 明确列出满足 / 不满足 / 已 deferred 的边界。
* 如果发现现有计划仍缺一个讨论维度，要明确指出下一步应补哪一块。

## Out of Scope (explicit)

* 不修改 `coding-deepgent` 产品代码。
* 不重开 H13/H14 实现。
* 不对整本书做逐章审计，只聚焦 Ch09/Ch10 与子智能体、多智能体相关部分。

## Technical Notes

* Local docs inspected:
  * `.trellis/tasks/04-16-cc-highlight-alignment-discussion/prd.md`
  * `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
  * `.trellis/tasks/04-17-cc-core-topology-closeout-plan/prd.md`
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  * `.trellis/project-handoff.md`
* External docs inspected:
  * `https://lintsinghua.github.io/#ch09`
  * GitHub mirror chapter pages:
    * Chapter 9: `09-子智能体与Fork模式.md`
    * Chapter 10: `10-协调器模式-多智能体编排.md`

## Research Notes

### External chapter requirements

**Ch09 子智能体 / Fork**

* 子智能体生成机制与完整生命周期管理
* Fork 模式缓存共享与字节级继承
* 自定义 / 内置智能体定义与加载
* 对抗性验证 Agent 的设计哲学

**Ch10 多智能体 / Coordinator**

* Coordinator-Worker 架构
* 协调者只编排不执行
* SendMessage / mailbox / worker addressing
* Scratchpad 协作空间
* 多智能体完整工作流与故障恢复

### Local discussion coverage

**已经具体讨论过**

* H11/H12：Agent-as-tool、general/verifier catalog、AgentDefinition、result envelope、sidechain transcript、fork/cache 差距、resume/lifecycle/deferred 边界
* verifier 作为对抗性验证 agent 的角色与最小边界

**只做了高层边界判断**

* H13 Mailbox / SendMessage：明确 deferred
* H14 Coordinator：明确 deferred
* Fork/cache 深度 parity：明确 deferred，不做当前 MVP

### Current repo state that matters for the decision

Already done:

* `L2-a`: `AgentDefinition` catalog for `general` / `verifier`
* real read-only `general` child runtime
* minimal structured subagent result envelope
* fallback final-text extraction
* `L2-c`: role-based tool projection through capability metadata

Still missing on the current H11/H12 path:

* `L3-a`: sidechain transcript persistence into parent JSONL
* transcript/audit visibility for what child agents actually saw/did

Still explicitly deferred:

* mailbox / SendMessage
* coordinator runtime
* background/async agents
* full fork/cache parity

### Fork/cache parity research notes

**Ch09 fork expectations from the book**

* Fork is a distinct execution path triggered when agent type is omitted and fork mode is enabled.
* Fork children inherit byte-identical request prefixes from the parent so Anthropic prompt cache can hit.
* Cache safety depends on five dimensions staying identical:
  * rendered system prompt bytes
  * user context
  * system context
  * tool/model context
  * message-prefix context
* Fork uses exact parent tools instead of re-resolving tool pools.
* `buildForkedMessages` preserves the full assistant tool-use block and injects fixed placeholder tool results so sibling children share the same prefix.
* Recursive fork must be blocked by runtime markers plus a fallback scan.
* Resume continuity matters: forked children should preserve prompt bytes and replacement state across resume.

**Current local state against those expectations**

* No implicit fork mode exists today.
* No cache-safe parameter object exists.
* No rendered-system-prompt byte threading exists for subagents.
* No `useExactTools`-style exact parent tool inheritance exists for a fork path.
* No placeholder tool-result construction exists for cache-sharing siblings.
* No dedicated recursive-fork guard exists because there is no fork path yet.
* No fork-specific resume path exists.
* The current subagent path is still synchronous and bounded; it is not a background parallel worker model.

**Local seams we can realistically build on later**

* `RuntimeInvocation` already gives a typed child `thread_id` seam.
* `AgentDefinition` already gives child identity, tool pool, and max-turn metadata.
* `PromptContext.system_prompt` exists, but only as freshly joined strings; there is no persisted rendered-byte contract yet.
* `SessionSidechainMessage` already models `subagent_thread_id` and `parent_message_id`.
* The subagent path already records child thread lineage and can append sidechain-style transcript entries.
* There is still no fork-specific marker equivalent to cc `querySource`, and no exact-parent-tools or placeholder tool-result payload builder.

### Expansion sweep

1. Future evolution
* If fork is reopened later, it should not fight the current `AgentDefinition`/role-projection contract.
* If H13/H14 are ever reopened, fork should remain the lightweight sibling of coordinator mode, not become a second coordinator.

2. Related scenarios
* `L3-a` sidechain transcript is the nearest adjacent seam because fork children still need auditability and parent/child linkage.
* Resume continuity matters because fork without restart-safe lineage becomes hard to trust in long sessions.

3. Failure / edge cases
* Prompt-cache miss from rebuilt system prompt or re-resolved tools.
* Recursive fork explosion.
* Worktree/path drift when a child runs in an isolated workspace.
* Broken resume if tool-use/tool-result replacement state is not reconstructed.

### Feasible approaches here

**Approach A: Finish the current Ch09-local MVP before new discussion** (Recommended)

* How it works:
  * Treat `L3-a` sidechain transcript as the last must-have local prerequisite.
  * After `L3-a`, do one focused review of what remains missing from Ch09 and what stays deferred.
* Pros:
  * Lowest context switching.
  * Closes the biggest remaining auditability gap in subagent runtime.
  * Gives a more honest baseline before revisiting Fork/multi-agent aspirations.
* Cons:
  * Does not advance coordinator/mailbox discussions yet.

**Approach B: Continue discussing Ch09 deep parity now**

* How it works:
  * Keep discussing full fork/cache parity, resume, async lifecycle, agent memory, summaries, and background agents before implementing `L3-a`.
* Pros:
  * Better long-range conceptual clarity.
* Cons:
  * Likely premature because current local MVP still lacks transcript/audit plumbing.
  * Risks discussing around a missing concrete runtime seam.

**Approach C: Jump to Ch10 multi-agent discussion now**

* How it works:
  * Start discussing coordinator, mailbox, Scratchpad, SendMessage, and worker orchestration despite H13/H14 being deferred.
* Pros:
  * Surfaces future architecture early.
* Cons:
  * Mismatched with current MVP boundary.
  * Most likely becomes speculative because coordinator/mailbox are explicitly out of scope today.

### Fork-specific approaches for the current discussion

**Approach F1: Minimal cache-safe fork contract** (Recommended)

* How it works:
  * Discuss only the reusable fork contract:
    * what must be byte-identical
    * what metadata must be persisted
    * how recursion should be blocked
    * how fork stays distinct from coordinator
  * Do not discuss background task lifecycle or mailbox.
* Pros:
  * Stays tightly inside Ch09.
  * Produces a clean contract that can later sit on top of `L3-a`.
  * Lowest speculation.
* Cons:
  * Will not answer all “full fork UX” questions.

**Approach F2: Resume-first fork continuity**

* How it works:
  * Center the discussion on what transcript, metadata, rendered-prompt bytes, and replacement state would be needed so a future fork can resume safely.
* Pros:
  * Closest to the current missing runtime seam (`L3-a`).
  * Connects fork discussion to durable session architecture.
* Cons:
  * More about continuity than about actual parallel fork execution.

**Approach F3: Full Ch09 fork parity target**

* How it works:
  * Discuss the whole fork story now: implicit fork entry, exact-tool inheritance, placeholder tool results, background worker execution, recursion guard, worktree notice, resume, summary.
* Pros:
  * Maximally complete.
* Cons:
  * Highest speculation.
  * Risks bleeding into H13/H14-style lifecycle/orchestration concerns.

### Decision candidate inside F1

The key unresolved boundary is how strict the minimal fork contract should be.

**Option 1: Metadata-first contract**

* Define only:
  * fork lineage ids
  * parent/child thread linkage
  * recursion-guard marker
  * worktree/isolation metadata
* Treat byte-identical cache sharing as a future optimization.
* Best when we want the smallest non-speculative local contract.

**Option 2: Cache-contract-first**

* Define byte-identity as a hard contract now:
  * rendered system prompt bytes
  * exact tool pool identity
  * fork context message prefix
  * placeholder tool-result layout
  * recursion-guard marker
* Even if implementation is deferred, future fork work must honor this exact cache-safe shape.
* Best when we want Ch09 fork semantics to stay central.

**Option 3: Hybrid**

* Define:
  * lineage / recursion / worktree metadata as hard requirements now
  * rendered prompt bytes + exact tools + placeholder layout as "reserved fields with normative comments"
* Best when we want to preserve the seam without claiming byte-identical behavior is fully settled.

## Decision (ADR-lite)

**Context**: 在 `L2-a` / `L2-c` 已完成后，当前可以选择继续补本地 H11/H12 前置（`L3-a`），也可以先继续讨论 Ch09 深水区，或者跳去 Ch10 多智能体编排。

**Decision**: 用户选择继续做 Ch09 深水区讨论，不先实现 `L3-a`，也不进入 Ch10 coordinator / mailbox 讨论。

**Consequences**:

* 讨论范围先收敛在 Ch09 余下的大缺口：Fork/cache parity、resume/metadata continuity、async/background lifecycle / summary。
* H13/H14 多智能体编排仍保持 deferred，不作为本轮讨论重点。
* 后续需要在 Ch09 深水区内部再选一个优先主题，以避免讨论过散。

## Decision (ADR-lite): Fork Discussion Boundary

**Context**: 在 Ch09 深水区里，fork 可以只被当作 lineage/metadata 扩展，也可以被定义为 cache-safe execution contract。用户已明确选择后者。

**Decision**: 本轮 fork 讨论采用 cache-contract-first 边界。fork 的本质不是普通子 agent lineage，而是未来必须满足的 cache-safe contract。即使实现暂缓，这个 contract 也应该先明确：

* rendered system prompt bytes continuity
* exact tool-pool identity
* byte-identical fork message prefix
* placeholder tool-result layout for sibling cache sharing
* recursion guard marker

**Consequences**:

* 后续如果实现 fork，不能只靠 `AgentDefinition` + thread lineage 拼一个“类似 fork”的 path。
* sidechain transcript、resume、worktree metadata 仍重要，但它们是支撑件，不是 fork 的核心定义。
* 下一步最值得拍板的是 fork 的入口形态，因为它会影响 tool schema、prompt shape、cache contract ownership、以及是否和普通 subagent catalog 混在一起。

## Decision (ADR-lite): Fork Entry Shape

**Context**: 在 cache-contract-first 边界下，fork 的核心价值是 cache-safe sibling execution，而不是普通 agent catalog 的一个变体。如果继续复用 `run_subagent` / `agent_type` 体系，fork 很容易退化成“继承上下文的普通子 agent”，从而稀释 byte-identical prefix、exact tool pool、placeholder tool results 这些核心语义。

**Decision**: 未来 fork 采用独立显式模式，不复用普通 `run_subagent` / `agent_type` 入口。

**Consequences**:

* fork 可以单独拥有 cache-safe contract，而不和 `general` / `verifier` 的 `AgentDefinition` 语义混杂。
* `AgentDefinition` 继续服务普通 child runtime；fork 作为平行能力，服务“same-agent sibling execution”。
* 后续需要继续明确第一版 fork 的范围，尤其是是否只支持同配置 sibling fork，还是立即引入 worktree/isolation 变体。
* 范围判断应优先看长期边界是否清晰，而不是先选“改动最小”的方案。
* 如果 fork 需要独立抽象，就直接独立，不为兼容当前 `run_subagent` 入口增加桥接层。

## Technical Approach

Fork 最小 cache-safe contract 的推荐草案：

### 1. rendered_system_prompt_bytes

* Fork child 不重新动态构造 system prompt。
* Parent 在 fork 时必须传递一份已渲染完成的 system prompt bytes/string。
* Resume 时优先恢复这份 rendered prompt，而不是重新调用 prompt builder。

### 2. exact_tool_pool_identity

* Fork child 不重新按 role/projection 解析工具池。
* Fork child 直接继承 parent 当次调用实际可见的 tool identity 集合。
* 这个 identity 应可序列化并可恢复，用于 fork resume continuity。
* 推荐把 identity 定义为**稳定排序的可见工具描述快照**，而不是只有工具名列表。

### 3. fork_message_prefix_shape

* Fork child 的前缀必须定义为“parent 已有消息前缀 + 固定 fork directive block”。
* 该 prefix shape 必须是规范化 contract，而不是运行时临时拼接。
* sibling forks 之间除 fork-specific directive 外，prefix 必须保持 byte-identical。
* fork-specific directive block 采用**极薄固定指令**，不承载富任务描述，不让 fork 退化成普通 subagent prompt。

### 4. placeholder_tool_result_layout

* 如果 fork 发生时 parent 历史里存在相关 tool-use context，则 sibling forks 必须共享固定 placeholder tool-result layout。
* placeholder 是 cache contract 的一部分，不是纯显示层。
* 不要求当前就实现完整 provider cache 命中，但字段和布局必须先固定。

### 5. recursion_guard_marker

* Fork path 必须带显式 recursion marker。
* 该 marker 同时服务：
  * runtime fast-path guard
  * transcript scan fallback guard
  * future resume guard

### Recommended first-version boundary

* 第一版只定义 same-config sibling fork contract。
* 不在第一版引入：
  * isolated worktree execution
  * path remap notice
  * background lifecycle / summary agent
  * mailbox / coordinator semantics

### Why this boundary

* 最大化 Ch09 fork 语义纯度。
* 保住 future cache parity 的核心 seam。
* 不让 fork 过早滑向 H13/H14 的多智能体编排。

## Decision (ADR-lite): Thin Fork Directive

**Context**: 如果 fork directive block 过厚，包含大段任务描述、临时上下文摘要、工具说明或自由文本目标，sibling forks 的 prefix 会过早分叉，fork 很容易退化成“重新发一个普通 subagent 任务”。

**Decision**: `fork_message_prefix_shape` 采用极薄固定指令。该指令只承担 fork 身份声明、cache-safe 约束说明、最小 fork intent 标识，不承载富任务描述。

**Consequences**:

* sibling forks 更容易保持 byte-identical prefix。
* fork 与普通 `run_subagent(task=...)` 的语义边界更清晰。
* richer task framing 如果未来确有需要，应通过独立字段或后缀差异承载，而不是塞进固定 fork directive block。

## Decision (ADR-lite): Exact Tool Pool Identity

**Context**: 如果 `exact_tool_pool_identity` 只记录工具名列表，那么 fork 只能证明“名字一样”，却无法证明模型看到的工具表面完全一致。工具顺序、schema 摘要、暴露面变化都可能破坏 cache-safe 语义，但不会反映在 name-only identity 中。

**Decision**: `exact_tool_pool_identity` 采用**稳定排序的可见工具描述快照**。第一版至少应覆盖：

* tool name
* stable visible order
* schema fingerprint or stable schema summary
* exposure-visible descriptor needed by the model surface

而不是只保留工具名列表。

**Consequences**:

* fork cache-safe contract 更接近“模型实际看到的是同一组工具表面”，而不是仅仅“运行时注册了同名工具”。
* 未来即使底层 registry/projection 重构，只要可见工具描述快照不变，fork contract 仍然清晰。
* 如果工具 schema 或显示顺序变化，fork 应视为不同 tool-pool identity，而不是偷偷复用旧 fork contract。

## Final Convergence

### Goal

一次性定清 Ch09 这一轮真正要交付的功能边界，然后按一个高耦合集成包完成，不把 fork 继续拆成零碎 patch。

### In Scope

* 普通子 agent 能被当作真正的“分支执行者”，而不只是 verifier 特例
* 子 agent 的过程能被父会话审计和追踪
* fork 有独立显式入口，不混入普通 subagent
* fork 保证“同一个父上下文分出多个 sibling 分支”时，模型侧看到的关键前缀和工具表面保持稳定
* fork 第一版只支持 same-config sibling fork，不引入多工作区/多机器/协调器

### Out of Scope

* coordinator / mailbox / SendMessage / Scratchpad
* 多智能体编排
* isolated worktree/path remap
* background lifecycle / summary side-agent
* full fork resume implementation

### Locked Decisions

* fork 采用独立显式模式，不复用普通 `run_subagent`
* fork 的核心按 cache-safe contract 定义，而不是普通 lineage metadata
* fork directive 采用极薄固定指令，不承载富任务描述
* exact tool pool 采用稳定排序的可见工具描述快照，而不是 name-only list
* 长远边界优先于最小改动；不为旧抽象保留桥接层/fallback

### One-Pass Delivery Plan

**Package 1: child auditability foundation**

* 完成 `L3-a` sidechain transcript
* 让 parent session 能看见 child 的 user/assistant sidechain
* 保证 compact/collapse/resume 不把 sidechain 错暴露到主上下文

**Package 2: explicit fork contract**

* 新增独立 fork 入口
* 定义 same-config sibling fork 的最小输入/输出 contract
* 固定 fork lineage / recursion guard / exact tool pool snapshot / thin directive / prefix shape

**Package 3: placeholder + continuity seam**

* 定义 placeholder tool-result layout
* 同时定义 tool-use pairing / replacement-state hook 的 contract seam
* 即使完整 fork resume 暂不实现，也要保证未来 continuity 不会推翻 fork contract

### Acceptance Criteria

* [ ] 子 agent 过程可在 parent session 中被审计
* [ ] fork 与普通 subagent 是两条清晰分开的入口
* [ ] same-config sibling fork 的关键前缀 contract 已固定
* [ ] tool surface identity 不是 name-only，而是模型可见表面的稳定快照
* [ ] placeholder/result continuity seam 已固定，不需要未来靠桥接层补救
* [ ] H13/H14 多智能体编排仍明确保持 out of scope
