# context engineering roadmap and task decomposition

## Goal

建立一个高层 Trellis epic，用于统一规划上下文工程剩余 10 个方向，并反思已有 planning tasks 之间的耦合关系。后续再把这些方向拆成更小、可顺序执行的 implementation tasks。

当前只做规划，不实现。

## Communication Requirement

后续讨论上下文工程时，优先用具体 coding-session 场景表达功能价值，再映射到模块或术语。

## Context

当前已讨论并创建的上下文相关 planning tasks：

* `04-15-cc-style-snip-message-pruning`
* `04-15-opencode-style-auto-tool-output-prune`
* `04-15-cc-level-2-microcompact-alignment`
* `04-16-cc-style-time-based-local-microcompact`
* `04-16-cc-level-3-collapse-alignment`
* `04-16-cc-style-collapse-store-pressure-guard`
* `04-16-cc-level-4-autocompact-alignment`
* `04-16-cc-style-autocompact-hardening`
* `04-16-context-compression-visualization-readiness`
* `04-16-context-engineering-remaining-alignment`

Observation:

这些任务不是彼此独立的功能点。它们共享底层前提：

* stable message IDs,
* raw transcript vs model-facing projection separation,
* compression timeline records,
* runtime pressure evidence,
* model/context-window pressure estimation,
* post-compact context restoration,
* subagent/fork context boundaries.

因此后续不能按“Level 2/3/4”机械并行实现；应该先打基础，再做高级能力。

## The 10 Context Engineering Directions

### 1. Context Visibility And Timeline

Scenario:

用户问：“为什么模型没看到之前那段测试日志？” 系统应能展示 raw transcript 里存在，但 model-facing context 被 compact/collapse/microcompact 隐藏。

Depends on:

* stable message IDs
* compression timeline records
* affected IDs in events

### 2. Stable Message Identity

Scenario:

未来 SnipTool 或 UI 需要引用 `msg-0012`。没有稳定 ID，就无法安全说“剪掉这几条”或“这条被 collapse 覆盖”。

Depends on:

* session record schema
* backward-compatible session loading

### 3. Rich Session Memory Runtime

Scenario:

用户隔天回来，agent 仍应记得项目偏好、当前状态、关键错误教训，而不只是看 raw transcript。

Depends on:

* memory quality policy
* compact/session summary quality
* session state contributions

### 4. Post-Compact State Restoration

Scenario:

AutoCompact 后模型忘了 active todos、plan、verifier failure、skill、关键文件路径，继续工作偏航。

Depends on:

* structured compaction result
* contribution registry
* evidence and task/plan contracts

### 5. Fork/Subagent Context Hygiene

Scenario:

主上下文很大时直接开子 agent，子 agent 继承一堆无用历史或一启动就超上下文。

Depends on:

* pressure estimation
* subagent context propagation contract
* optional spawn guard

### 6. Provider Cost / Cache Observability

Scenario:

压缩后成本反而更高，用户需要知道是 summary call 贵、cache miss、还是 rewrite 造成。

Depends on:

* local token accounting
* provider usage capture when available
* runtime event/evidence schema

### 7. Context Source Attribution

Scenario:

模型看到一段规则，但开发者不知道它来自 memory、resume brief、skill、hook、todo 还是 compact summary。

Depends on:

* typed context contributions
* model-facing projection debug view

### 8. Context Quality Gates

Scenario:

summary 太泛，memory 保存临时状态，compact 丢掉关键约束，导致后续工作偏航。

Depends on:

* summary schema/quality checks
* memory policy
* optional verifier-like review later

### 9. Manual Context Controls

Scenario:

用户想主动说“这段旧探索不用了”或“compact 时特别保留数据库相关内容”。

Depends on:

* stable message IDs
* snip boundary/replay
* PreCompact custom instructions

### 10. Context Pressure Policy Configuration

Scenario:

不同模型上下文窗口不同；固定 token 阈值可能过早/过晚触发压缩。

Depends on:

* model context-window source
* deterministic local estimate
* settings-backed policy

## Coupling Reflection

### Foundational Couplings

* `Stable Message Identity` is a prerequisite for:
  * cc-style Snip,
  * compression timeline,
  * raw/projection diff,
  * affected-message metadata,
  * frontend display.
* `Structured CompactionResult` is a prerequisite for:
  * post-compact restoration,
  * hooks,
  * better AutoCompact telemetry,
  * future UI progress.
* `Pressure Estimation` is a prerequisite for:
  * ratio-based Collapse,
  * spawn guard,
  * MicroCompact time/budget policy,
  * cost/cache observability.
* `Contribution/Source Attribution` is a prerequisite for:
  * restoration,
  * debug views,
  * quality gates.

### Existing Task Couplings

* `04-16-context-compression-visualization-readiness` should not proceed before stable message IDs.
* `04-15-cc-style-snip-message-pruning` should not proceed before stable message IDs and projection replay.
* `04-16-cc-style-collapse-store-pressure-guard` should be split; collapse records and projection replay should come before spawn guard and overflow drain.
* `04-16-cc-style-autocompact-hardening` should be split; failure circuit breaker can be early, post-compact restoration should wait for structured result.
* `04-16-cc-style-time-based-local-microcompact` can be relatively independent, but richer event metadata should align with compression timeline schema.

## Proposed Execution Order

### Phase 0: Stabilize Current Work

* Commit current progressive runtime pressure pipeline work.
* Record session.
* Avoid adding more implementation until current diff is committed.

### Phase 1: Foundation For Context Explainability

1. Stable message IDs in session records.
2. Compression timeline record schema.
3. Raw history vs model-facing projection debug/query helper.

Why first:

These unlock frontend display, Snip, projection replay, and better evidence.

### Phase 2: Low-Risk Pressure Enhancements

4. Time-based local MicroCompact.
5. Token saved accounting and pressure event enrichment.
6. AutoCompact failure circuit breaker.

Why second:

These are mostly local, low-risk, and do not require major session projection changes.

### Phase 3: Structured Compaction Backbone

7. Structured CompactionResult.
8. Compact request prompt-too-long retry.
9. Post-compact state restoration contributions.

Why third:

This gives AutoCompact a stronger backbone before hooks or UI.

### Phase 4: Collapse Store And Replay

10. Collapse records.
11. Projection replay from collapse records.
12. Overflow drain before reactive compact.

Why fourth:

This depends on message IDs, timeline, and projection helper.

### Phase 5: Manual / Agent Context Control

13. Explicit SnipTool with reason and safety gates.
14. Optional `/history` or CLI selection UX.
15. PreCompact/PostCompact hooks.

Why fifth:

These expose control surfaces and should wait until records/replay are reliable.

### Phase 6: Advanced Runtime And Provider Optimization

16. Spawn guard / compact-before-spawn.
17. Rich session memory extraction.
18. Provider cache/cost instrumentation.
19. Cached microcompact API spike only if provider support is concrete.

Why last:

These are high-coupling and provider/runtime-specific.

## Suggested Small Task Breakdown

Future tasks should be small and testable:

* `stable-session-message-ids`
* `compression-timeline-records`
* `model-facing-projection-debug-view`
* `time-based-local-microcompact`
* `runtime-pressure-token-saved-evidence`
* `autocompact-failure-circuit-breaker`
* `structured-compaction-result`
* `compact-request-ptl-retry`
* `post-compact-restoration-contributions`
* `collapse-records`
* `collapse-projection-replay`
* `collapse-overflow-drain`
* `explicit-snip-tool`
* `pre-post-compact-hooks`
* `spawn-pressure-guard`

## Out of Scope

* No implementation in this task.
* No frontend UI work now.
* No provider-specific cache editing now.
* No line-by-line cc clone.

## Acceptance Criteria

* [x] 10 context engineering directions are captured.
* [x] Couplings with existing planning tasks are documented.
* [x] A phased execution order is proposed.
* [x] Future small task names are listed.

## Status

Planning-only epic. Use this task as the parent planning reference before splitting new implementation tasks.
