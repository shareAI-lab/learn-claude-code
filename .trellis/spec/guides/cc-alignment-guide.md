# CC Alignment 指南

> **Purpose**: 让 `cc-haha` / Claude Code 对齐保持 source-backed、effect-driven，并且用 LangChain-native 方式落地。

---

## Scope

当 `coding-deepgent` 的功能需要对齐 `NanmiCoder/cc-haha` 或 Claude Code runtime 行为时，使用这份 guide。

适用场景：

- implementation
- review
- planning
- alignment documentation

不要因为名字相似就复制行为。

---

## Core Rule

改代码前，先说明 **expected effect**，再写 source-backed alignment matrix。

如果说不清具体本地效果，默认不要对齐。标记为 `defer` 或 `do-not-copy`。

---

## Pre-code Workflow

1. **Name the feature band**
   - 例如 `TodoWrite`、`Skill loading`、`Runtime pressure`、`Verifier execution`
2. **State expected effect**
   - 本地用户/runtime/safety/reliability/maintainability 会得到什么具体改善？
3. **Identify cc-haha reference points**
   - 列 exact source files，必要时列 symbol/function。
4. **Extract functional essence**
   - 这个 cc 行为解决什么问题？
   - 拥有什么 state？
   - 改变什么 model-visible surface？
5. **Separate essence from product detail**
   - essence 需要对齐
   - product detail 只有当前有本地收益才复制
6. **Write alignment matrix before implementation**

---

## Required Alignment Matrix

写在 task PRD 或 planning note：

```md
## Expected effect

Aligning this behavior should improve: <category>. The local user/runtime effect
is: <specific outcome>. If this effect does not appear, the change is not worth
shipping.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Tool/schema | `TodoWrite(todos=...)` | fewer model JSON mistakes | strict tool schema | align | Match model-visible contract |
| Runtime state | `appState.todos[...]` | correct isolation semantics | local state domain | defer | Requires later stage |
```

Status vocabulary 保留英文：

- `align`
- `partial`
- `defer`
- `do-not-copy`
- `unknown/inferred`

---

## Decision Rules

### Align when

- expected effect 具体且当前有价值
- 属于 model-visible contract 或 essential state semantics
- 能防止已知 agent failure
- 能自然表达为官方 LangChain/LangGraph primitive

### Defer when

- 效果依赖后续 capability/stage
- 会引入 speculative abstractions
- 是真实 cc 行为，但不是当前主线优先级

### Do-not-copy when

- 只是 UI/TUI detail
- 是 provider-specific plumbing，LangChain 已有更合适抽象
- 与本地更简单抽象冲突
- 会模糊当前 product boundary

---

## Mandatory Boundary Checks

实现前必须回答：

1. Expected effect 是什么？
2. Scope 是什么？
3. Non-goals 是什么？
4. 哪些 state 是 short-term / persistent / shared / model-visible？
5. 哪些 tool/prompt/schema surface 会被模型看到？
6. 用哪个 LangChain/LangGraph primitive？

常见 primitive：

- strict tool + Pydantic schema
- `Command(update=...)`
- middleware hook
- typed state schema / reducer
- store / memory seam
- graph node / edge

---

## Documentation Rule

当前 `coding-deepgent` 主线中：

- cc alignment 先写 active task PRD
- 只有稳定的 roadmap/product-direction 结果才提升到 `.trellis/plans/`
- 只有 executable implementation constraints 才提升到 `.trellis/spec/`
- 不默认写到 tutorial-track `agents_deepagents/cc_alignment/`

探索性 source notes 不要默认变成 canonical plans/specs。

---

## Verification Requirements

需要证明两侧：

1. **cc-haha mapping evidence**
   - source files/symbols cited
   - matrix decisions recorded
   - intentional gaps documented
2. **local behavior evidence**
   - model-visible schema tests
   - state/update shape tests
   - boundary guard tests
   - 必要时 grep/review stale public names

---

## Anti-patterns

- 不看 source，凭记忆实现
- 复制文件名但没复制 functional intent
- LangChain 有简单 primitive 时还 line-for-line clone
- 把 secondary analysis 当成比 source behavior 更强的证据
- alignment status 不写明

---

## Final Output Checklist

报告时包含：

- expected effect
- source files/symbols inspected
- alignment matrix summary
- what aligned now
- deferred / do-not-copy
- files changed
- verification evidence
