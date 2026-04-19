# brainstorm: full cc parity roadmap

## Goal

把 `coding-deepgent/` 的产品目标从当前 `Approach A MVP` 扩展为面向 Claude Code / `cc-haha` 的全功能对照路线图，并建立一套后续长期升级规则：优先对照可见源码；若对应功能没有公开源码，则必须检索高质量同类开源项目，提炼可验证实现模式，再写入 Trellis 规划/规范后实施。

## What I already know

* 用户明确要求：不再局限于当前上下文系统 MVP，要“全面往 cc 进军”，目标是功能上完全对照。
* 用户新增了一条过程约束：如果对应功能没有源代码，先搜索类似的高质量开源项目，研究别人怎么实现，再把这条做法写进文档，后续升级都按这个规则执行。
* 当前 canonical 目标仍然是 `Approach A MVP`，不是 full cc parity。
* 当前主线是 `coding-deepgent/`，Trellis 是 canonical coordination/documentation layer。
* 当前 canonical handoff、roadmap、release/next-step 口径都默认围绕 `Approach A MVP` 收口，而不是继续向 full parity 推进。
* 2026-04 的多个上下文/Collapse 相关任务已经明确区分了两层口径：
  - `MVP local boundary`
  - `richer cc-style follow-up`
* 现有 full-goal 定义其实已经存在一个“长线目标”：`cc-haha` essence alignment through LangChain/LangGraph-native primitives；但后续执行被收窄到了 MVP closeout。
* 公开 `cc-haha` 对很多 feature band 有源码，但并不是所有内部能力都公开可见；例如 `contextCollapse` 关键实现就是 feature-gated/缺失态。
* 用户已确认新的顶层对齐口径：
  - 真实 Claude Code 公开行为是最高目标
  - `cc-haha` 是最重要的开源实现参照
* 用户已确认第一圈 roadmap 范围：
  - 先做本地 agent 全带宽
  - 先不把 remote / IDE / daemon 作为第一优先圈
* 用户已确认第一圈本地 parity 口径：
  - 不是只做 backend/runtime
  - CLI/TUI/交互体验也纳入第一圈目标
* 用户已确认新的默认裁决规则：
  - 对 `模型可见行为 / runtime 语义 / CLI-TUI 交互`，优先贴近真实 Claude Code
  - 对隐藏内部实现、provider-specific plumbing、非必要底层机制，继续保持 LangChain-native 优先
* 用户已确认第一圈不纳入完整本地多智能体协作层：
  - `mailbox / coordinator / richer background team runtime` 先不进第一圈
  - 第一圈先做单 agent、本地 subagent/fork、context/session/memory/plugin/CLI 全带宽
* 用户已确认第一圈对本地扩展生态的深度：
  - 技能 / MCP / 插件 / 钩子以“本地可用、可加载、可调用、可调试”为目标
  - 不把完整安装 / 启停 / 分发 / marketplace-like 体验放入第一圈
* 用户已确认第一圈内部排期：
  - 采用 `runtime-first`
  - 先补 runtime/context/session/memory/task/subagent/fork/permission/prompt 等核心
  - CLI/TUI 先补与 runtime 核心直接相关的高价值面，而不是先做整套体验翻新
* 用户已确认第一圈完成判断：
  - 以代表性真实工作流达到本地 `daily-driver parity` 为主
  - 不是先以 feature-band checklist 收工
* 用户已确认第一圈代表性工作流采用 `Lean 3-workflow`：
  - 代码库接手与持续编码
  - 长会话连续性
  - 复杂任务分解（todo/task/plan + subagent/fork）
* 用户已明确降低对扩展生态的要求：
  - `skill / MCP / hook / plugin` 不作为第一圈高要求验收面
  - 第一圈对这些能力保持“可用即可、非高优先收口”
* 用户已确认“代码库接手与持续编码”工作流的成功标准：
  - 以 **PR 级任务独立完成** 为标准
  - agent 应能在中大型仓库中读代码、形成短计划、改代码、跑验证、处理中断并继续推进
  - 不要求一开始就达到长时间近乎无人值守的超长链路主力级
* 用户已确认“长会话连续性”工作流的成功标准：
  - 以 **单日长任务级** 为标准
  - 在一次较长本地开发任务中，经历多轮 context pressure、compact/collapse、resume、继续编辑后，仍能稳定保留主线并推进任务
  - 不把跨日连续工作级作为第一圈默认完成线
* 用户已确认“复杂任务分解（todo/task/plan + subagent/fork）”工作流的成功标准：
  - 以 **个人效率增强级** 为标准
  - todo/task/plan + subagent/fork 应能稳定帮助单人完成复杂开发任务，明显提升效率
  - 不把 mailbox、coordinator、完整 team-runtime 语义纳入第一圈完成线

## Assumptions (temporary)

* 这次任务先做 roadmap / planning / documentation boundary reset，不直接进入大规模实现。
* 新方向会覆盖现有 `Approach A MVP` 边界，因此需要更新 canonical planning docs，而不是只新增一个孤立任务 PRD。
* “功能上完全对照”优先指真实 Claude Code 公开可观察行为与产品能力对照；`cc-haha` 作为最重要的开源实现参照，而不是最高裁决源。
* 不要求对 provider-specific 或 closed-source 细节做盲目复刻，但要求尽可能逼近真实行为。

## Open Questions

* None for the roadmap-definition pass.

## Requirements (evolving)

* 梳理当前 canonical 文档中所有把目标限定为 `Approach A MVP` / “not full parity” 的边界。
* 输出新的 full-cc-parity planning shape，至少包含 `Acceptance Targets`、`Planned Features`、`Planned Extensions`。
* 定义 feature-band 级别的对齐方法：有源码时直接 source-backed 对齐；无源码时进入高质量 OSS research-first 流程。
* 把“无源码时转向高质量 OSS 对标”的规则写进 Trellis canonical docs。
* 给出后续实施顺序、优先级、阶段切分、风险边界。
* 输出一份可复用的证据等级规则，避免未来把“可见源码”“公开行为”“三方分析”“类比 OSS”混成同一可信度。
* 新 roadmap 的第一圈必须覆盖本地 agent 全带宽，而不是只做 backend/runtime 局部。
* 新 roadmap 的第一圈必须同时覆盖本地 CLI/TUI/交互体验，而不是把使用感完全后置。
* roadmap 必须明确裁决规则：哪些层要求行为优先，哪些层保持 LangChain-native 优先。
* roadmap 第一圈必须明确排除完整本地多智能体协作层，以免单 agent 本地 parity 被 team-runtime 需求稀释。
* 第一圈本地扩展生态以“可用即可”为边界，不把完整插件分发/安装体验纳入第一圈。
* roadmap 第一圈的实施顺序以 `runtime-first` 为默认，不以先做表层 CLI/TUI 相似度为导向。
* roadmap 第一圈的完成判断以代表性真实工作流达到本地 `daily-driver parity` 为主，而不是仅以 feature checklist 作为主验收。
* 第一圈主验收工作流固定为 `Lean 3-workflow`，扩展生态不作为第一圈高要求验收面。
* “代码库接手与持续编码”工作流以 **PR 级任务独立完成** 为第一圈成功标准。
* “长会话连续性”工作流以 **单日长任务级** 为第一圈成功标准，而不是跨日连续工作级。
* “复杂任务分解（todo/task/plan + subagent/fork）”工作流以 **个人效率增强级** 为第一圈成功标准，而不是完整 team-runtime 协作级。

## Acceptance Criteria (evolving)

* [x] 新 roadmap 明确取代“只到 MVP”为默认主目标。
* [x] roadmap 覆盖主要 feature bands，而不是只讨论上下文系统。
* [x] 文档明确规定：无公开源码时必须先做同类高质量 OSS 调研，再决定本地实现策略。
* [x] 计划中区分：有源码可直接对照、只有行为可对照、无源码需类比研究，这三类证据等级。
* [x] 输出后，后续 agent 能按该文档继续规划/实施，而不会回到“closer to cc 但 scope 不清”的状态。
* [x] 现有 canonical docs 中与新方向冲突的 MVP-only 表述被标记为 superseded/update targets。
* [x] 第一圈三条主工作流的成功标准被明确写入 roadmap。

## Acceptance Targets

* `coding-deepgent` 的默认产品目标从“Approach A MVP”切换为“持续推进 full cc parity roadmap”。
* 后续 feature-family planning 默认按 feature band 和证据等级推进，而不是按临时 closeout stage 漂移。
* 对于 `cc-haha` 未公开的能力，团队有一套固定 fallback 机制去借鉴高质量 OSS，而不是临时拍脑袋。
* 第一圈 roadmap 的完成判断聚焦本地 agent 全带宽，而非一开始就把 remote / IDE / daemon 纳入第一优先波次。
* 第一圈 roadmap 的完成判断以“真实工作流是否足够像 Claude Code 并能日常使用”为主。
* 第一圈 roadmap 的主要验收工作流是精简的 3 条，而不是覆盖所有次级能力面。
* 第一圈至少要让 agent 在真实仓库中独立完成典型 PR 级任务，达到可日常依赖的编码助手水平。
* 第一圈至少要让 agent 在单日长任务里跨多轮压缩/恢复后，仍能保持主线并继续工作。
* 第一圈至少要让 todo/task/plan + subagent/fork 成为个人复杂任务中的稳定效率放大器，而不是仅停留在演示级。

## Planned Features

* 盘点并标记当前所有 MVP-only canonical docs / handoff / ADR / roadmap 边界。
* 产出新的 full-parity canonical roadmap 结构，覆盖主要 feature bands 和实施顺序。
* 定义“evidence ladder + OSS fallback”方法论，并写进 Trellis 文档。
* 建立一份高质量 OSS 候选池，按 feature band 说明优先参考什么。
* 说明后续实施时的 planning gate、对齐矩阵、验证要求、文档更新要求。
* 为“本地 agent 全带宽第一圈”定义清晰 feature-band 范围。
* 为本地 CLI/TUI/交互体验建立和 runtime/backend 并行的 parity 目标，而不是只把它视为壳层。
* 为冲突 feature bands 写明：模型可见行为、runtime semantics、CLI/TUI interaction、hidden implementation、provider plumbing 分别怎么判。
* 为第一圈写清楚“不包含完整 mailbox/coordinator/team runtime”这一边界。
* 为第一圈写清楚“本地扩展生态只做到可用，不做到完整分发/安装产品化”这一边界。
* 为第一圈定义 runtime-first 波次：哪些 runtime/core bands 在 CLI/TUI polish 之前优先落地。
* 定义 3-5 条代表性本地工作流，并用它们作为第一圈 parity 验收面。
* 将 `skill / MCP / hook / plugin` 从第一圈高要求验收面中降级，保留为非阻塞配套能力。
* 为每条主工作流定义明确成功粒度；其中“代码库接手与持续编码”采用 PR 级任务独立完成标准。
* 为每条主工作流定义明确成功粒度；其中“长会话连续性”采用单日长任务级标准。
* 为每条主工作流定义明确成功粒度；其中“复杂任务分解”采用个人效率增强级标准。

## Planned Extensions

* 为每个 feature band 建独立的 parity matrix / decomposition PRD。
* 为无源码 feature band 建“候选 OSS 深入研究模板”。
* 建立更细的实现波次：backend/runtime first，再到 CLI/frontend/workflow/team runtime。
* 若后续需要，再引入“真实 Claude Code 公开行为验证”专门文档和测试协议。
* 第二圈再规划 remote / IDE / daemon / proactive automation 对照目标。

## Technical Approach

* 新建 full-parity canonical roadmap，作为默认 planning target。
* 将旧 MVP-only roadmap / deferred-boundary ADR 降级为 historical references。
* 更新 `project-handoff.md`，让默认 resume 入口转向 full-parity roadmap。
* 更新 `cc-alignment-guide.md`，把 evidence ladder 和 missing-source OSS fallback workflow 写成统一规则。
* 新建 Circle 1 / Wave 1 runtime-core decomposition plan，作为下一批具体 parity tasks 的直接来源。

## Implementation Checkpoint

State: terminal

Verdict: APPROVE

Implemented:

* Canonical full parity roadmap and evidence ladder.
* Circle 1 / Wave 1 runtime-core decomposition.
* Wave 1 implementation pack across F1/F2/F3/F4/F5:
  - deferred `Command(update=...)` preservation
  - collapse assistant-round tail preservation
  - session-memory freshness hardening
  - frontend durable `task_snapshot`
  - background `subagent_list`
  - recovery `Subagent activity:` section

Verification:

* `pytest -q coding-deepgent/tests` -> 415 passed
* `ruff check coding-deepgent/src/coding_deepgent coding-deepgent/tests .trellis/spec .trellis/plans` -> passed
* `python3 -m mypy coding-deepgent/src/coding_deepgent` -> passed

## Definition of Done (team quality bar)

* 规划文档更新到 canonical Trellis 位置
* 范围、优先级、升级方法、证据等级都写清楚
* 与现有 handoff/roadmap/goal docs 不冲突
* 如行为边界发生变化，相关 spec/ADR 更新目标已标明

## Out of Scope (explicit)

* 本任务不直接实现 full cc parity
* 本任务不承诺复制闭源 provider plumbing
* 本任务不因为“功能全对照”而忽略 LangChain/LangGraph-native 边界

## Technical Notes

* Current canonical handoff: `.trellis/project-handoff.md`
* Current product goal/backlog docs:
  * `.trellis/tasks/archive/2026-04/04-14-redefine-coding-deepgent-final-goal/prd.md`
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* Current planning rules:
  * `.trellis/spec/guides/cc-alignment-guide.md`
  * `.trellis/spec/guides/planning-targets-guide.md`
* Current MVP-boundary docs to revisit:
  * `.trellis/project-handoff.md`
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  * `.trellis/plans/coding-deepgent-deferred-boundary-refresh-adr.md`
  * `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
  * `.trellis/tasks/archive/2026-04/04-19-backend-next-step-roadmap/prd.md`

## Research Notes

### Current canonical repo constraints

* The long-term product-goal doc already says `coding-deepgent` should implement the essential `cc-haha` / Claude Code runtime logic through LangChain/LangGraph-native primitives.
* The current active canonical roadmap later narrowed execution to `Approach A MVP`, with explicit non-MVP deferrals.
* Any new full-parity plan must therefore replace or supersede the MVP-only planning surface, not merely add another optional backlog note.

### Evidence ladder for future parity work

1. **Behavior-backed**
   - public Claude Code behavior, official docs, public product surfaces, or visible runtime artifacts
2. **Primary source-backed implementation reference**
   - exact `cc-haha` source files / symbols / docs
3. **Analogous OSS-backed**
   - high-quality open-source systems implementing a similar capability family
4. **Secondary analysis**
   - books, blogs, third-party explanations; useful but weaker

Rule:

* treat real Claude Code public behavior as the top-level parity target
* use `cc-haha` as the default open-source implementation reference when it matches or explains the public behavior
* use level 3 only after documenting why Claude Code public evidence and `cc-haha` source are insufficient
* never treat level 4 as stronger than available source

### Candidate high-quality OSS pool for fallback research

These are not automatic parity targets. They are candidate reference systems when
`cc-haha` lacks source for a capability family.

* `sst/opencode`
  - highly relevant for terminal coding-agent runtime and explicitly positions itself as very similar to Claude Code
  - useful bands: agent runtime, CLI/TUI, provider-agnostic architecture, remote/client-server split
* `Aider-AI/aider`
  - highly relevant for repo-map, edit loop, git/testing ergonomics, pragmatic coding-agent workflows
  - useful bands: codebase mapping, edit/commit/test loops, practical code editing UX
* `OpenHands/OpenHands`
  - highly relevant for software-agent SDK, CLI, local/cloud runtime split, multi-agent/system architecture
  - useful bands: agent runtime layering, SDK/CLI separation, permissions/collaboration surfaces
* `google-gemini/gemini-cli`
  - relevant for CLI agent features, context files, checkpointing, MCP, trusted-folder/security ergonomics
  - useful bands: CLI UX, checkpoint/resume, context-file conventions, MCP/tool integration
* `block/goose`
  - relevant for local agent runtime, desktop/CLI/API tri-surface, extensibility, provider-agnostic architecture, skills/extensions ecosystem
  - useful bands: extension/skills ecosystem, local-agent safety, distribution model, agent packaging

### Feasible planning approaches here

**Approach A: Replace MVP as canonical top-level target now** (Recommended)

* How it works:
  - full-cc-parity becomes the default canonical target
  - existing MVP docs become historical closeout records or bounded stage snapshots
  - future work plans from feature bands and evidence ladder
* Pros:
  - matches the user's new directive directly
  - stops future ambiguity around “MVP complete vs parity incomplete”
  - gives one clean upgrade rule for all subsequent work
* Cons:
  - requires updating multiple canonical docs and handoff assumptions

**Approach B: Keep MVP as shipping baseline, add full-parity as separate long-run track**

* How it works:
  - preserve current MVP docs as canonical shipping boundary
  - add a separate parity-track roadmap above it
* Pros:
  - less churn to current docs
  - easier to preserve “already verified MVP” language
* Cons:
  - high risk of future planning drift
  - likely repeats the same confusion about what “complete” means

**Approach C: Split by feature-band ownership, not by one new top-level target**

* How it works:
  - leave global goal mostly as-is
  - create one parity decomposition doc per feature family
* Pros:
  - less central-doc disruption
  - can move fast per subsystem
* Cons:
  - weak top-level coordination
  - likely reintroduces inconsistent evidence standards

## Decision (ADR-lite)

**Context**: The repo already has a long-term cc-aligned product goal, but the current canonical planning surface narrowed execution to an MVP closeout path. The user now wants the default direction to change: no longer “stop at MVP,” but systematically pursue full feature parity, with a documented fallback process for missing-source features.

**Decision**: Prefer Approach A: replace MVP as the canonical top-level target now, while preserving MVP documents as historical boundary evidence rather than the default planning destination. The top-level parity target is real Claude Code public behavior; `cc-haha` becomes the primary open-source implementation reference, and high-quality OSS research is required when both are insufficient.

**Consequences**:

* Canonical roadmap/handoff docs will need an explicit superseding update.
* Future feature planning should default to feature-band parity plus evidence ladder.
* Missing-source capabilities must trigger OSS research-first instead of ad-hoc design.
* Verification and documentation burden will increase, but planning drift should drop.
* Future feature PRDs will need an explicit layer-by-layer parity judgment instead of one coarse “align/defer” label.
* The first implementation circle should stay focused on local single-agent parity and bounded local subagent/fork parity, deferring broader team-runtime parity.
* The first implementation circle should treat skills/MCP/plugins/hooks as usable local extension seams, not as a full plugin distribution platform.
* The first implementation circle should prioritize runtime/core parity before broad CLI/TUI polish, except for CLI/TUI surfaces directly needed to expose or validate those runtime gains.
* The first implementation circle should be evaluated primarily through representative daily-driver workflows, with feature-band checklist serving as supporting structure rather than the main finish line.
