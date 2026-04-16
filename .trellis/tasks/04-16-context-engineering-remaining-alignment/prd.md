# brainstorm: context engineering remaining alignment

## Goal

反思四层压缩（Snip / MicroCompact / Collapse / AutoCompact）之外，`coding-deepgent` 的上下文工程还需要与 cc-haha / 类 cc 产品对齐或补充哪些能力，并形成后续 backlog。当前只做研究和规划，不实现。

## Communication Requirement

解释上下文工程时，必须优先使用具体 coding-session 场景，而不是只列术语。

Preferred style:

* 先描述用户/agent 遇到的实际问题。
* 再说明系统应该如何处理。
* 最后才映射到模块名、contract 或 task。

## What I already know

* 当前 `coding-deepgent` 已完成 Approach A MVP 的上下文核心：
  * prompt layering / dynamic context,
  * runtime pressure pipeline,
  * session transcript/evidence/resume,
  * compact records,
  * scoped memory MVP,
  * minimal subagent context propagation,
  * observability counters/events MVP.
* 已规划的上下文增强 tasks:
  * `04-15-cc-style-snip-message-pruning`
  * `04-16-cc-style-time-based-local-microcompact`
  * `04-16-cc-style-collapse-store-pressure-guard`
  * `04-16-cc-style-autocompact-hardening`
  * `04-16-context-compression-visualization-readiness`
  * `04-15-opencode-style-auto-tool-output-prune`
* Roadmap marks richer session/agent memory runtime, rich fork/cache parity, provider-specific cost/cache instrumentation as deferred beyond MVP.

## Remaining Context Engineering Themes

### 1. Context Visibility And Timeline

Scenario:

用户问：“为什么模型忘了之前的测试日志？” 或 “这段历史到底有没有给模型看？”

Needed behavior:

* Raw transcript remains complete.
* Model-facing projection is inspectable.
* Compression timeline shows compact/snip/microcompact/collapse events and affected IDs.

Existing task:

* `04-16-context-compression-visualization-readiness`

### 2. Stable Message Identity

Scenario:

未来做 SnipTool、前端 timeline、projection diff 时，必须能说“msg-0012 被 collapse-3 隐藏”。

Needed behavior:

* Persist stable `message_id` in session message records.
* Preserve mapping from model-facing projection back to raw transcript.

Related tasks:

* `04-15-cc-style-snip-message-pruning`
* `04-16-context-compression-visualization-readiness`

### 3. Rich Session Memory Runtime

Scenario:

用户隔天回来，希望 agent 还记得“项目偏好、当前状态、错误教训”，而不只是 compact summary。

Needed behavior:

* Background or explicit session-memory extraction.
* Session-memory compact path when memory is good enough.
* Staleness/quality gates stronger than current artifact refresh.

Roadmap link:

* H07 richer session/agent memory runtime deferred.

### 4. Post-Compact State Restoration

Scenario:

AutoCompact 后，模型只看到 summary，却忘了当前 plan、active todos、loaded skill、verifier failure、重要文件路径。

Needed behavior:

* Restore bounded plan/todo/verifier/skill/file/subagent context after compact.
* Keep raw payloads out of recovery context.

Existing task:

* `04-16-cc-style-autocompact-hardening`

### 5. Fork/Subagent Context Hygiene

Scenario:

主上下文已经很大，用户要求 “开一个子 agent 去审查”。如果直接 fork，子 agent 可能一开始就带着一堆无用历史。

Needed behavior:

* Decide what parent context child agents inherit.
* Add pressure-aware spawn guard or compact-before-spawn.
* Keep child context isolated from parent pressure state.

Roadmap link:

* H12 rich fork/cache parity deferred.
* Existing task: `04-16-cc-style-collapse-store-pressure-guard`.

### 6. Provider Cost / Cache Observability

Scenario:

压缩后成本为什么反而变高？是 cache miss、cache rewrite，还是 summary API 太贵？

Needed behavior:

* Track local estimated tokens and, when available, provider usage.
* Distinguish cache read/write/drop from intentional compact/microcompact.
* Keep provider-specific features behind capability gates.

Roadmap link:

* H20 rich provider-specific cost/cache instrumentation deferred.

### 7. Context Source Attribution

Scenario:

模型看到一段内容，但开发者不知道它来自 memory、resume brief、todo、compact summary、skill 还是 hook。

Needed behavior:

* Tag model-facing context sections with source.
* Preserve source metadata in projection/debug surfaces.
* Avoid dumping arbitrary metadata into model-visible recovery briefs.

Existing contracts:

* Runtime state/recovery/compact contribution seams.

### 8. Context Quality Gates

Scenario:

summary 写得太泛，memory 保存了临时状态，或 compact 丢了关键约束，导致下一轮工作偏航。

Needed behavior:

* Quality checks for generated summaries and session-memory artifacts.
* Rejection or warning when summary lacks goal/current state/next steps.
* Optional verifier-style review for high-risk compaction later.

### 9. Manual Context Controls

Scenario:

用户想主动说：“这段旧探索不用了” 或 “compact 时特别保留数据库相关内容”。

Needed behavior:

* Manual compact instructions already exist in CLI resume path.
* Future: explicit SnipTool or `/history`-style selection.
* Future: PreCompact custom instruction hook.

Existing tasks:

* `04-15-cc-style-snip-message-pruning`
* `04-16-cc-style-autocompact-hardening`

### 10. Context Pressure Policy Configuration

Scenario:

不同模型/供应商/任务类型上下文窗口不同，固定 token 阈值可能不合适。

Needed behavior:

* Ratio-based thresholds when context window is known.
* Conservative local estimates when provider limits are unavailable.
* Settings-backed policies with tests.

Existing tasks:

* `04-16-cc-style-collapse-store-pressure-guard`
* `04-16-cc-style-time-based-local-microcompact`

## Current Priority Recommendation

1. Finish already planned pressure closeouts only when needed:
   * time-based local MicroCompact,
   * AutoCompact hardening,
   * Collapse records/projection.
2. Then add visualization readiness:
   * stable message IDs,
   * compression timeline,
   * raw vs model-facing projection.
3. Defer expensive/provider-specific work:
   * cached microcompact API,
   * prompt-cache sharing,
   * provider exact token accounting.
4. Defer full cc-style Snip until message IDs and projection replay exist.

## Out of Scope

* No implementation in this turn.
* No frontend UI work now.
* No provider-specific cache editing now.
* No line-by-line cc clone.

## Status

Research captured / planning-only.
