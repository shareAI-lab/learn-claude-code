# s06：Context Compact — CC 对齐进度

## 范围

`s06_context_compact.py` 是教程轨道里的上下文压缩章节。它负责在保留足够的
canonical history（规范历史记录）和恢复元数据的同时，缩小模型每轮真正看到的
active context（活跃上下文）。

当前实现是一个 **受 cc-haha 启发的 LangChain 教学版压缩流水线**，不是 Claude
Code 生产级 compact runtime 的完整克隆。

## CC 参考点

主要参考：`NanmiCoder/cc-haha` commit
`5fa3247f9fa3ddde462185218f7e73b2dccfc956`。

本章使用到的公开源码参考点：

- `src/query.ts` — 模型调用前的压缩顺序：
  `applyToolResultBudget -> snipCompactIfNeeded -> microcompactMessages -> contextCollapse.applyCollapsesIfNeeded -> autoCompactIfNeeded`。
- `src/utils/toolResultStorage.ts` — 大型 tool result 持久化、`<persisted-output>` 标记、单轮 message 预算、replacement decision。
- `src/services/compact/microCompact.ts` — 可压缩工具集合、旧结果清理、time-based / cached microcompact 概念，以及 microcompact boundary。
- `src/services/compact/autoCompact.ts` — 阈值计算、summary 预算、auto compact 触发、失败 circuit breaker。
- `src/services/compact/compact.ts` 与 `src/commands/compact/compact.ts` — 手动 compact、summary prompt、compact boundary、prompt-too-long retry、compact 后 hook / attachment 恢复。
- cc-haha 文档把高层压缩策略描述为四层：**snip**、**micro**、**context collapse**、**auto compact**。

公开源码限制：

- `snipCompact` 与 `contextCollapse` 在公开 tree 中是 feature-gated 引用；本次能看到集成点和行为目标，但看不到完整内部实现。因此本章里的 `snip_projection` 与 `context_collapse` 是教学等价实现，不声称逐行复刻。

## 已对齐

这些部分有意对齐 CC / cc-haha 公开可见的结构或行为。

### 1. 压缩阶段顺序是显式的

当前 s06 暴露同样的教学顺序：

```python
PIPELINE_STAGE_ORDER = (
    "apply_tool_result_budget",
    "snip_projection",
    "microcompact_messages",
    "context_collapse",
    "auto_compact_if_needed",
    "reactive_compact_on_overflow",
)
```

这对齐了 cc-haha 的核心思想：压缩不是一次“神奇总结”，而是模型调用前的一组分阶段 context preparation pipeline。

### 2. 大型 tool output 不直接污染 active context

当前 s06 实现：

```python
apply_tool_result_budget()
```

已对齐行为：

- 超预算的 tool output 会被持久化到 active context 之外；
- 模型可见内容变成 `<persisted-output>` preview marker；
- replacement decision 按 tool call id 记录；
- 重复 pipeline pass 会复用之前的 replacement decision。

这对齐 cc-haha 的大型输出持久化与单轮 message budget 策略；区别是我们使用小型本地教学存储路径，而不是生产级 session storage infrastructure。

### 3. 旧 tool result 可以 microcompact

当前 s06 实现：

```python
microcompact_messages()
```

已对齐行为：

- 只处理 compactable tools；
- 保留最近的 tool results；
- 更旧的 tool results 被替换成 placeholder；
- microcompact boundary 记录发生了什么。

这对齐 cc-haha microcompact 的核心目标：避免旧工具输出持续占用模型上下文。

### 4. Auto compact 由阈值触发

当前 s06 实现：

```python
auto_compact_if_needed()
```

已对齐行为：

- 估算 model-facing context size；
- 超过阈值后 compact；
- 生成 summary；
- 保留 recent context；
- 记录 compact boundary。

这对齐 cc-haha auto compact 的目的。测试中使用 deterministic summarizer 代替 live model call。

### 5. Overflow recovery 先尝试 collapse，再 full compact

当前 s06 实现：

```python
reactive_compact_on_overflow()
```

已对齐行为：

```text
prompt/context overflow
  -> 先尝试 drain staged collapse
  -> 如果仍然太大，再 reactive full compact
```

这对齐 cc-haha prompt-too-long recovery 的恢复形状：优先 drain staged collapse，再 fallback 到 reactive compact。

### 6. 压缩状态保留可恢复元数据

当前 s06 使用 typed state：

- `ContextCompressionState`
- `ContextMessage`
- `PersistedOutput`
- `CompactBoundary`
- summaries
- transitions

这对齐 CC 的重要原则：压缩不能只是静默删除历史，而要留下可恢复、可解释的元数据。

## 部分对齐 / 教学等价

### 1. Snip projection

当前 s06 实现：

```python
snip_projection()
```

它建模的是：

- canonical history 保留在 `state.messages`；
- `state.model_messages` 变成更小的 model-facing view；
- snip boundary 记录这次 projection。

为什么只是部分对齐：

- 公开 cc-haha 源码能看到 snip 的集成点，但看不到完整 `snipCompact` 实现；
- 我们的版本是根据可见目标做出的 LangChain-native 教学等价实现。

### 2. Context collapse

当前 s06 实现：

```python
context_collapse()
```

它建模的是：

- 先总结更旧的 groups；
- 保留最近 groups 的原文；
- 保留 summary metadata；
- recovery 可以在 reactive compact 前 drain staged collapse。

为什么只是部分对齐：

- 公开 cc-haha 源码能看到 `contextCollapse.applyCollapsesIfNeeded()` 与 `recoverFromOverflow()` 集成点，但看不到完整内部实现；
- 我们的版本是 staged-summary 教学等价实现。

### 3. LangChain-native message/state 边界

当前 s06 使用 typed Python dataclasses 和小型 `build_agent()` surface。它比 cc-haha TypeScript runtime 小很多，但保留了最重要的 LangChain 侧边界：

```text
canonical history != model-facing projection
```

## 未对齐 / 有意不复制

以下是 s06 当前没有实现的生产级 CC 细节。

### 1. 真实 provider cache edits

未复制：

- Anthropic cache edit APIs；
- `cache_deleted_input_tokens` accounting；
- prompt-cache-preserving delete operations。

原因：

- provider cache edits 属于生产/runtime 基础设施；
- 本章只需要教学核心行为：旧 tool result 可以变轻，同时保留可恢复性。

### 2. 完整 `snipCompact` 内部算法

未复制：

- 精确 snip algorithm；
- hidden feature-gated implementation details。

原因：

- 公开 cc-haha 源码中没有完整实现；
- 当前使用诚实的教学等价实现。

### 3. 完整 `contextCollapse` 内部算法

未复制：

- 精确 collapse store；
- 完整 staged collapse commit log；
- 生产级 collapse projection rules。

原因：

- 公开 cc-haha 源码中没有完整实现；
- 当前实现的是可观察行为等价。

### 4. Session memory compaction

未复制：

- session memory extraction；
- `lastSummarizedMessageId`；
- memory file truncation；
- resumed-session compact path。

原因：

- 这属于后续 memory / product-runtime stage，不应该提前塞进 s06 教学版。

### 5. Pre/Post compact hooks

未复制：

- PreCompact hooks；
- PostCompact hooks；
- SessionStart hook replay；
- hook-provided summary instructions。

原因：

- hooks 是独立子系统；在 hook 章节/阶段前，不应提前拉进 s06。

### 6. Prompt-cache-sharing fork

未复制：

- forked compact agent；
- prompt-cache-sharing parameters；
- streaming fallback retry loop。

原因：

- 这是生产优化，不是 deterministic teaching version 的必要条件。

### 7. GrowthBook / telemetry / feature flags

未复制：

- remote config；
- analytics events；
- experiment gates；
- circuit-break telemetry。

原因：

- 本地教学轨道不需要这些生产运营设施。

### 8. 完整 token accounting 与 media recovery

未复制：

- 精确 tokenizer budgets；
- image / document token handling；
- media-size recovery；
- model-specific context window logic。

原因：

- s06 使用 deterministic character-count budgets，使测试保持 no-network 且稳定。

### 9. 完整 UI / transcript restore 系统

未复制：

- compact boundary UI components；
- transcript segment storage；
- recent file restore attachments；
- plan / skills / background-agent rehydration attachments。

原因：

- 这些属于 product UI / runtime persistence 关注点。s06 只记录 compact boundaries、persisted outputs、summaries、transitions 作为教学底座。

## 测试 / 证据

当前 deterministic verification：

```sh
PYTHON_DOTENV_DISABLED=1 python -m pytest \
  tests/test_s06_context_compact_baseline.py \
  tests/test_deepagents_track_smoke.py \
  tests/test_stage_track_capability_contract.py -q
```

期望结果：

```text
23 passed
```

完成时也使用过这些检查：

```sh
PYTHON_DOTENV_DISABLED=1 python -m py_compile agents_deepagents/*.py
git diff --check
git diff --name-only -- coding-deepgent
```

s06 baseline tests 断言：

- source-backed / inferred / simplification metadata 存在；
- oversized tool output 会被持久化并替换成 marker；
- replacement decisions 会被复用；
- snip projection 会缩小 model-facing context，同时保留 canonical history；
- microcompact 会保留最近 tool results 并清理更旧结果；
- context collapse 会总结 older groups 并保留 recent groups；
- auto compact 会生成 summary + recent context；
- reactive compact 会记录 collapse-before-reactive transition order；
- s06 是 stage gating 中第一个暴露 `compact` capability 的章节。

## 下一步对齐候选

未来不要随意往 s06 增加细节。最有价值的下一步，是把 context compression 接到其他 runtime state。

1. **TodoWrite preservation**
   - product compact 应该保留当前 `todos`、active todo、最近 completed/pending context。
2. **Subagent boundaries**
   - 决定 child agent 是继承 parent compression state，还是拥有自己的 isolated context。
3. **Skill state**
   - compact 时保留 invoked skill metadata / content。
4. **Session memory**
   - 只有 memory chapter / product stage 进入范围后，再加入真实 memory extraction / resumed-session compact。
5. **Hooks**
   - 只有 hook system 进入范围后，再加入 PreCompact / PostCompact 行为。
6. **Product migration**
   - 如果要迁入 `coding-deepgent/`，必须另写 product-stage plan；不要把教程模块直接复制成 production runtime。
