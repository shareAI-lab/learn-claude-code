# Runtime Architecture Reshape Integrated Delivery Plan

## Goal

一次性集成交付 `coding-deepgent` backend runtime 架构重构计划，明确 main agent / child agent / fork / background run / future coordinator-worker runtime 的边界，避免继续把 H13/H14 多智能体编排堆到当前 subagent/fork/background surfaces 上，形成后续难以升级的屎山。

## What I already know

* 用户明确担心：前面一直强调架构边界，但 AI 仍可能把功能堆成屎山。
* 当前目标是先做重构整理计划，不是立刻实现多智能体编排。
* 当前主线是 `coding-deepgent/`，教程/reference 层默认只作参考。
* 现有 Trellis spec 已经要求：`run_subagent` 不能被拉伸成 mailbox/coordinator/team lifecycle semantics。
* 初步代码阅读显示：`RuntimeContext` 已经承担过多横切职责，subagent/fork/background runtime 构造散落在 `subagents/tools.py` 和 `subagents/background.py`。
* 用户现在进一步明确：代码重构计划希望后续一次性集成交付完成；智能体编排功能作为第二个大计划，后续再单独定集成交付目标。

## Assumptions (temporary)

* 这轮应优先把重构任务写到足够详细，使后续可以一口气实施，而不是立即开始改代码。
* 重构目标不是“为了好看重命名”，而是降低 H13/H14 mailbox/coordinator 落地时的边界风险。
* 可以接受先做少量架构 prep，再进入 H13 mailbox foundation。
* 后续实施可以是一个 integrated delivery pass，但必须保留内部 checkpoint 和 stop/split 条件。

## Open Questions

* （resolved）本轮只创建 R1-R4 子任务并完成计划拓扑，暂不改产品代码。

## Requirements (evolving)

* 明确指出当前 backend runtime 的真实混乱点，不泛泛而谈。
* 区分“必须先重构的 blocker”和“可以随 H13/H14 顺手整理的非 blocker”。
* 明确未来 H13/H14 需要的新 runtime surfaces，避免继续污染 `run_subagent`。
* 给出 staged refactor plan，每一阶段都要有验收标准和风险控制。
* 计划必须遵循 LangChain/LangGraph-native 原则，不引入自定义大 runtime 绕开 `create_agent` / middleware / store / checkpointer。
* 用户已选择 **Approach C: Broad runtime reshape before H13**。
* 本轮允许接受较大重构范围，目标是在 H13/H14 前把 runtime 底座整理干净。
* 重构仍必须 staged，不允许一次性无验收的大爆炸修改。
* 用户已选择：R1 不保留旧 monkeypatch/调用兼容桥接，直接迁移测试和调用点到新 factory seam。
* 用户已选择：brainstorm 收敛后先创建 R1-R4 子任务，暂不进入 implementation。
* 用户已选择：后续希望一次性完成这个代码重构大计划，因此父任务需要写成 integrated delivery contract，而不是松散 backlog。
* 后续还会单独定义“智能体编排功能”的 integrated delivery target；当前父任务只负责把 runtime 底座整理到可承载 H13/H14 的状态。

## Acceptance Criteria (evolving)

* [x] 有一份 runtime architecture assessment，列出具体文件/边界/风险。
* [x] 有 2-3 个可选重构路线，并说明 trade-off。
* [x] 有推荐路线，且能解释为什么它能降低 H13/H14 升级风险。
* [x] 有小 PR 拆分，每个 PR 都可独立验证。
* [x] 明确 out of scope：不在本轮直接实现完整 Coordinator。
* [x] Broad reshape 每个阶段都有 checkpoint gate、focused tests、rollback/split 条件。
* [x] R1-R4 子任务已创建并链接到父任务。
* [x] 父任务包含集成交付目标、阶段顺序、验证矩阵、stop/split 条件和 H13/H14 handoff contract。
* [x] R1-R4 子任务包含足够详细的实施顺序、文件范围、测试范围和非目标。

## Definition of Done (team quality bar)

* Tests added/updated if implementation is included.
* Lint / typecheck / CI green if code changes are included.
* Docs/notes updated if behavior or architecture contracts change.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* 不直接实现完整 H14 Coordinator runtime。
* 不直接实现 H13 Mailbox / SendMessage / Scratchpad。
* 不把 mailbox/coordinator/team semantics 加到 `run_subagent` 或 `run_fork` 字符串 payload 里。
* 不做 line-by-line cc-haha clone。
* 不为旧局部设计增加兼容桥接层，除非存在真实外部兼容要求。

## Technical Notes

* Initial local evidence:
  * `coding-deepgent/src/coding_deepgent/runtime/context.py`
  * `coding-deepgent/src/coding_deepgent/runtime/invocation.py`
  * `coding-deepgent/src/coding_deepgent/containers/app.py`
  * `coding-deepgent/src/coding_deepgent/subagents/tools.py`
  * `coding-deepgent/src/coding_deepgent/subagents/background.py`
  * `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
  * `.trellis/spec/backend/task-workflow-contracts.md`

## Research Notes

### Relevant project rules

* `.trellis/spec/guides/architecture-posture-guide.md`
  * 优先长期清晰边界，不以最小 diff 为第一目标。
  * 如果新结构明显更正确，可以直接替换旧局部抽象，不为了旧方案保留 bridge/fallback。
* `.trellis/spec/guides/planning-targets-guide.md`
  * 非平凡 feature family 必须先写清 `Acceptance Targets` / `Planned Features` / `Planned Extensions`。
  * 这次计划必须防止“重构 runtime”这种模糊目标漂移。
* `.trellis/spec/backend/langchain-native-guidelines.md`
  * 任何 runtime 整理都必须落在官方 surfaces：tool、middleware、typed state、context schema、checkpointer、store、graph/subgraph。
  * 禁止引入无真实边界的 wrapper/fallback/框架形态间接层。
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
  * `run_subagent` 不得被拉伸为 mailbox/coordinator/background daemon/team lifecycle semantics。
  * 当前 subagent/fork/background 是 local slices，不是 team runtime。
  * H13/H14 需要新的 task/subagent specs，而不是继续扩展字符串 payload 或 deferred lifecycle bridge。

### Current code signals

* `RuntimeContext` 是一个轻量 dataclass，但已经聚合了 identity、session、transcript projection、context pressure、fork prompt/tool projection、tool policy、memory service、plugin dir 等横切信息。
* `subagents/tools.py` 约 1883 行，直接负责 AgentDefinition、child/fork invocation 派生、prompt 构造、tool projection、resume、sidechain persistence、structured envelopes 和 tool wrappers。
* `subagents/background.py` 约 561 行，管理 background run store、线程生命周期、queued input、stop、notification、subagent/fork resume 分流。
* `subagents/tools.py` 内部直接 `create_agent(...)` 构造 child/fork agent，和 `containers/app.py` 的主 agent composition seam 并不统一。
* `BackgroundSubagentManager` 把 live `ToolRuntime` 传入线程，当前 local bounded run 可接受，但不适合作为 mailbox/coordinator/跨进程恢复的基础。
* 代码中大量通过 `getattr(runtime, "context"...)`、`runtime.store`、`runtime.state` 读取隐式能力；这对当前 tool runtime 快速演进有用，但对 team/coordinator ownership 不够硬。
* `coding-deepgent/tests/subagents/test_subagents.py` 对 `subagents.tools.create_agent` 有大量 monkeypatch；如果直接拆文件/迁移 symbol，测试和调用点会大面积震荡。
* `agent_service.py` 已经有主 agent 的 `create_compiled_agent(...)` seam，但 child/fork runtime 没复用这个 seam。
* `agent_runtime_service.py` 只有 `invoke_agent(...)` / session payload wiring，没有负责 agent construction。它可以作为轻量 invocation helper 保留，不应被扩成新 god module。

### Why AI keeps risking "屎山"

* AI 默认会沿着最近可用的 surface 继续扩展：已有 `run_subagent_background` 和 `subagent_send_input`，就很容易把 mailbox 做成“send_input 的增强版”。
* 如果没有先定义 role/tool projection，Coordinator 很容易仍拿到执行工具，Worker 也容易拿到管理工具，最后只能靠 prompt 约束。
* 如果没有 runtime factory/context boundary，child/fork/worker/coordinator 会继续各自 `create_agent(...)`，middleware/store/checkpointer/policy 很难保持一致。
* 如果没有 serializable background run context，未来 worker resume/notification/mailbox 会被当前进程内 `ToolRuntime` 绑住。

### Feasible approaches here

**Approach A: Architecture plan only**

* How it works:
  * 本轮只产出 assessment、ADR、task decomposition，不改产品代码。
* Pros:
  * 风险最低，能快速把方向锁住。
* Cons:
  * 不会立刻减少代码里的耦合，下一位 AI 仍可能绕开计划。

**Approach B: Runtime architecture prep MVP** (Recommended)

* How it works:
  * 先做一个小而硬的架构准备包：
    * 定义 runtime role / invocation / agent factory contract。
    * 把 main/subagent/fork 的 agent construction 收敛到统一 factory seam。
    * 把 H13/H14 禁止污染 `run_subagent` 的规则写成 tests/spec review gate。
  * 不实现 mailbox/coordinator。
* Pros:
  * 直接降低后续 H13/H14 的屎山概率。
  * 范围仍可控，和当前 pain 点强相关。
* Cons:
  * 会触碰核心 runtime/subagent tests，需要认真验证。

**Approach C: Broad runtime reshape before H13**

* How it works:
  * 同时拆 `RuntimeContext`、重构 background manager、拆分 `subagents/tools.py`、定义 future team package。
* Pros:
  * 长期最干净。
* Cons:
  * 范围太大，容易变成另一个失控重构。
  * 在没有 H13 concrete consumer 前可能引入 speculative abstraction。

### Broad reshape staged plan candidate

**Stage R1: Runtime role and agent factory seam**

* Acceptance Targets:
  * main/subagent/fork agent construction 都能通过一个明确的 runtime factory/agent builder seam 表达。
  * child/fork 不再直接依赖散落在 `subagents/tools.py` 的裸 `create_agent(...)` 调用作为主要构造入口。
  * 现有 H11/H12 behavior 不变。
* Planned Features:
  * 新增或重整 `runtime/agent_factory.py` / `runtime/roles.py` 之类的低层 seam。
  * 定义 runtime roles：`main`、`subagent`、`fork`，并为 future `coordinator`、`worker` 预留枚举/contract，不实现行为。
  * 将 child/fork construction 调整为调用 factory seam。
* Planned Extensions:
  * future `coordinator` / `worker` role projection。
  * mailbox/scratchpad/team runtime。

**Stage R2: Split subagent domain by responsibility**

* Acceptance Targets:
  * `subagents/tools.py` 不再同时承载 definition/catalog、execution、fork payload、resume/sidechain、background lifecycle、tool wrappers。
  * Public tool surfaces 保持原名和 schema。
* Planned Features:
  * 拆分为职责模块，例如 `definitions.py`、`execution.py`、`forking.py`、`resume.py`、`sidechain.py`、`tool_wrappers.py`。
  * 保持 `subagents/__init__.py` public exports 稳定。
* Planned Extensions:
  * future `teams/` 或 `orchestration/` package 不依赖 `subagents/tools.py` 内部细节。

**Stage R3: Background run service hardening**

* Acceptance Targets:
  * background manager 不再把 live `ToolRuntime` 当作长期执行上下文的唯一来源。
  * run record 明确区分 serializable context、runtime-owned store、process-local worker handle。
* Planned Features:
  * 引入 `BackgroundRunContext` / `BackgroundRuntimeSnapshot` 等可序列化执行参数。
  * 线程 worker 通过 factory/context snapshot 重建 invocation，而不是长期闭包持有完整 live runtime。
* Planned Extensions:
  * H13 mailbox message delivery。
  * stopped-worker resume / notification protocol。

**Stage R4: H13/H14 readiness gate**

* Acceptance Targets:
  * tests/spec 明确阻止 `run_subagent` / `run_fork` 获得 mailbox/coordinator/team lifecycle 字段或语义。
  * future `coordinator` 和 `worker` 的 tool projection contract 已有占位测试或 spec 条目。
* Planned Features:
  * 更新 Trellis backend contracts。
  * 增加 regression tests 覆盖 schema 不污染、role projection 不混淆、factory seam 被使用。
* Planned Extensions:
  * H13 mailbox foundation。
  * H14 coordinator prompt/tool projection/runtime。

### Expansion sweep

1. Future evolution
* 1-3 个月内，runtime reshape 应直接支撑 H13 mailbox、H14 coordinator、future worktree/team worker，而不是只让当前 H12 更整洁。
* 需要保留 LangChain-native construction path，避免未来为了 coordinator 写自定义 query loop。

2. Related scenarios
* Runtime pressure、memory、tool guard、session evidence 都依赖 `RuntimeContext`，拆分时不能破坏现有 middleware。
* Existing tests monkeypatch `subagents.tools.create_agent`，第一阶段应先建立新 seam 和适配测试，再拆 public module。

3. Failure / edge cases
* 最大风险是 broad reshape 变成一次性大爆炸，导致行为回归难定位。
* 第二风险是过早引入 future coordinator abstractions，但没有 H13/H14 consumer，形成新的 speculative layer。

### Current implementation posture

* Recommended execution mode: `staged-execution` in `deep` planning, then `lean` implementation per stage.
* Do not activate implementation until final requirements include:
  * `Acceptance Targets`
  * `Planned Features`
  * `Planned Extensions`
  * Stage checkpoints
  * Focused test list

### Initial recommendation

采用 **Approach B: Runtime architecture prep MVP**。它不是为了“重构而重构”，而是为 H13/H14 建立最小硬边界：

* 让 agent construction 不再散落。
* 让 role/tool projection 成为显式 contract。
* 让 background execution 不继续绑定 live `ToolRuntime` 作为未来 team runtime 基础。
* 让 tests 阻止 `run_subagent` 被继续污染成 mailbox/coordinator。

## Decision (ADR-lite)

**Context**: 当前 `coding-deepgent` 的 H11/H12 local runtime 已经足够丰富，但 main/subagent/fork/background 的 agent construction、runtime context、tool projection、background lifecycle 分散在多个局部实现里。若继续直接做 H13/H14，多智能体编排很容易被实现成 `run_subagent_background` / `subagent_send_input` 的增强版，而不是真正的 coordinator-worker runtime。

**Decision**: 采用 **Approach C: Broad runtime reshape before H13**。先接受较大 runtime 架构整理，在进入 H13 mailbox / H14 coordinator 前重建更清晰的 runtime surfaces。

**Consequences**:

* 本轮规划优先级高于直接实现 H13/H14。
* 允许替换旧的局部 runtime 抽象，不为了旧局部设计增加兼容桥接层。
* 重构必须 staged，每个阶段都要有明确 acceptance targets 和 tests。
* 不允许把 broad reshape 变成无边界的大爆炸；每个阶段必须能解释它如何降低 H13/H14 屎山风险。
* H13/H14 继续保持 out of scope，直到 runtime reshape 的必要关口完成。
* R1 不保留旧 `subagents.tools.create_agent` 兼容桥接。现有测试和调用点应直接迁移到新的 runtime factory seam。
* R1 diff 会更大，但避免留下临时 bridge/fallback，符合 architecture posture guide。

## Decision (ADR-lite): R1 No Compatibility Bridge

**Context**: `coding-deepgent/tests/subagents/test_subagents.py` 目前大量 monkeypatch `subagents.tools.create_agent`，这是当前 child/fork construction 散落的测试信号。如果 R1 保留旧入口作为过渡，会降低 diff 风险，但会继续鼓励后续代码依赖旧局部抽象。

**Decision**: R1 不保留旧 monkeypatch/调用兼容桥接。直接建立新的 runtime factory seam，并迁移测试和调用点。

**Consequences**:

* 第一阶段修改范围更大。
* 测试应从 monkeypatch `subagents.tools.create_agent` 转向 monkeypatch/inject 新 factory seam。
* 不新增只为保护旧局部设计存在的 fallback 或 bridge。
* 如果 R1 迁移中发现范围超过可控边界，应 split 出前置子任务，而不是保留旧兼容入口。

## Decision (ADR-lite): Planning Topology Before Implementation

**Context**: Broad reshape 风险高，且 R1 明确不保留兼容桥接。若直接实现，很容易把 R1 范围和 R2/R3 混在一起。

**Decision**: 本轮先创建 R1-R4 子任务并暂停，不改产品代码。

**Consequences**:

* 后续可以从 R1 单独进入 Task Workflow。
* 父任务保留为 architecture reshape plan ledger。
* R2-R4 不应提前实现，除非 R1 checkpoint 明确通过或调整。

## Decision (ADR-lite): Integrated Delivery Mode For Refactor

**Context**: 用户希望后续“一口气”完成代码重构大计划，并在重构完成后再单独定智能体编排功能的集成交付目标。若 R1-R4 只是松散 backlog，后续执行容易在阶段间重新漂移，或者某个阶段做到一半就顺手实现 H13/H14。

**Decision**: 本父任务作为 runtime reshape integrated delivery contract。后续实现可以在一个连续执行 pass 内完成 R1-R4，但必须按顺序经过内部 checkpoint：R1 -> R2 -> R3 -> R4。每个 checkpoint 都要记录验证结果和 `continue | adjust | split | stop` 决策。

**Consequences**:

* 后续执行不需要每个阶段都重新 brainstorm，只要 PRD 仍然成立即可继续。
* 如果某阶段 focused tests 通过且 checkpoint 为 `continue`，可以立即进入下一阶段。
* 如果某阶段发现范围膨胀、架构前提错误、测试失败且非局部可修，就必须 `split` 或 `stop`。
* H13/H14 功能目标仍作为后续第二个大计划，不在本 integrated delivery 中实现。

## Integrated Delivery Contract

### Acceptance Targets

* `coding-deepgent` 的 main/subagent/fork/background runtime construction 有清晰统一的 factory/role seam。
* `subagents` domain 内部职责拆分清楚，future `teams/` or `orchestration/` 不需要依赖 `subagents/tools.py` 的内部细节。
* Background run service 明确区分 durable run record、serializable runtime snapshot、process-local worker handle。
* Trellis spec/tests 明确禁止 `run_subagent` / `run_fork` 污染 mailbox/coordinator/team lifecycle semantics。
* 完成后可以单独开启 H13/H14 integrated delivery planning，且不需要先回头修 runtime 底座。

### Planned Features

* R1: Runtime role and agent factory seam.
* R2: Split subagent domain responsibilities.
* R3: Background run service hardening.
* R4: H13/H14 readiness gate.

### Planned Extensions

* H13 mailbox / SendMessage / Scratchpad foundation.
* H14 Coordinator mode and coordinator-worker workflow.
* Worktree-aware worker lanes.
* Cross-process/remote team runtime if product goal later requires.

### Execution Order

1. R1 must run first because it changes the core construction seam that R2/R3 should depend on.
2. R2 should run second because it stabilizes internal subagent APIs before background hardening.
3. R3 should run third because background execution should depend on R1 factory and preferably R2 execution/resume modules.
4. R4 must run last because readiness tests/specs should reflect the final reshaped runtime surfaces.

### Checkpoint Gate

At the end of each R stage, write a checkpoint note into that child PRD:

```md
## Checkpoint: R<n>

State:
* verifying

Verdict:
* APPROVE | ITERATE | REJECT

Implemented:
* ...

Verification:
* ...

Architecture:
* primitive used:
* why no heavier abstraction:

Boundary findings:
* ...

Decision:
* continue | adjust | split | stop

Reason:
* ...
```

### Stop / Split Conditions

* Stop if a required change would replace LangChain/LangGraph `create_agent` / middleware / store / checkpointer seams rather than reorganizing around them.
* Split if R1 cannot remove `subagents.tools.create_agent` monkeypatch dependence without a separate test harness cleanup task.
* Split if R2 module extraction reveals a behavior change that should be fixed before further file moves.
* Split if R3 requires durable cross-process worker execution; that is not part of this refactor.
* Stop if H13/H14 feature behavior starts leaking into implementation.
* Stop if working tree changes conflict with user-owned edits.

### Verification Matrix

Focused checks expected during integrated implementation:

* R1:
  * `pytest -q coding-deepgent/tests/subagents/test_subagents.py`
  * `pytest -q coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/runtime/test_app.py`
  * `ruff check` / `mypy` on touched runtime/subagent/test files.
* R2:
  * `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/tool_system/test_tool_system_registry.py`
  * import/export smoke checks through `subagents/__init__.py`.
  * `ruff check` / `mypy` on touched subagent files.
* R3:
  * background-specific subset in `coding-deepgent/tests/subagents/test_subagents.py` covering background start/status/send_input/stop/fork reuse.
  * session evidence checks if notification code changes.
  * `ruff check` / `mypy` on touched background/schema files.
* R4:
  * schema non-contamination tests for `run_subagent` / `run_fork`.
  * registry/projection tests if role projection contracts are added.
  * Trellis spec review against project infrastructure contracts.

Broader validation should run after R4 if all stages changed runtime/subagent surfaces:

* `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/runtime/test_app.py coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`

### H13/H14 Handoff Contract

This refactor is complete only when the next multi-agent orchestration plan can start from these assumptions:

* `coordinator` and `worker` can be represented as runtime roles without overloading `subagent` or `fork`.
* Coordinator tool projection can be restricted to orchestration tools without prompt-only enforcement.
* Worker tool projection can expose execution tools without team-management tools.
* Background workers can eventually receive mailbox messages through a service boundary, not through ad hoc `subagent_send_input` semantics.
* Scratchpad/team state can land in a future `teams/` or `orchestration/` domain without being hidden inside `sessions/`, `tool_system/`, or `subagents/tools.py`.

## Checkpoint: Integrated Runtime Reshape

State:
* terminal

Verdict:
* APPROVE

Implemented:
* R1 completed: runtime roles and runtime agent factory seam now own main/subagent/fork construction.
* R2 completed: subagent definitions/catalog, result dataclasses, and fork payload/fingerprint helpers moved out of `subagents/tools.py`.
* R3 completed: background runs now persist bounded runtime snapshots and separate process-local worker handles from durable run records.
* R4 completed: H13/H14 readiness contracts and schema regression tests prevent mailbox/coordinator/team semantics from creeping into existing subagent/fork/background tools.

Verification:
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/runtime/test_app.py coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Result: `77 passed`
* `ruff check coding-deepgent/src/coding_deepgent/runtime coding-deepgent/src/coding_deepgent/agent_service.py coding-deepgent/src/coding_deepgent/subagents coding-deepgent/src/coding_deepgent/tool_system/middleware.py coding-deepgent/tests/subagents/test_subagents.py`
* Result: `All checks passed`
* `mypy coding-deepgent/src/coding_deepgent/runtime coding-deepgent/src/coding_deepgent/agent_service.py coding-deepgent/src/coding_deepgent/subagents coding-deepgent/src/coding_deepgent/tool_system/middleware.py coding-deepgent/tests/subagents/test_subagents.py`
* Result: `Success: no issues found in 20 source files`

Architecture:
* primitive used: LangChain `create_agent` remains the execution primitive, wrapped by a project-local runtime factory seam.
* why no heavier abstraction: this reshaped construction and domain boundaries without introducing a custom query loop, daemon, team runtime, or coordinator mode.

Boundary findings:
* `subagents/tools.py` is still a large module because execution/resume/sidechain/tool wrappers remain there. Definitions/catalog, result dataclasses, and fork payload/fingerprint ownership are no longer there.
* Background workers still use live `ToolRuntime` for the current in-process invoke; durable snapshot and process-local handle boundaries are explicit. Full cross-process reconstruction remains future work.
* H13/H14 behavior is not implemented. The next plan can now define mailbox/SendMessage/Scratchpad and Coordinator/Worker as separate surfaces.

Decision:
* terminal

Reason:
* Integrated runtime reshape acceptance targets are met and focused validation passed.

## Final Plan Summary

**Goal**: 在进入 H13 mailbox / H14 coordinator 前，先完成 backend runtime broad reshape，避免多智能体编排被堆到现有 subagent/fork/background surfaces 上。

**Chosen route**: Approach C, broad runtime reshape before H13.

**Implementation topology**:

* R1: `04-19-r1-runtime-role-agent-factory-seam`
  * 建立 runtime role + agent factory seam。
  * 不保留旧 `subagents.tools.create_agent` 兼容桥接。
* R2: `04-19-r2-split-subagent-domain-responsibilities`
  * 拆分 `subagents` domain 内部职责。
* R3: `04-19-r3-background-run-service-hardening`
  * 整理 background run service，分离 durable record、serializable context、process-local worker handle。
* R4: `04-19-r4-h13-h14-readiness-gate`
  * 建立 H13/H14 readiness gate，防止 `run_subagent` / `run_fork` 污染 team semantics。

**Out of scope for this planning task**:

* 不改产品代码。
* 不实现 H13 mailbox / SendMessage。
* 不实现 H14 Coordinator。
