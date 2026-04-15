# 主线范围指南

> **Purpose**: 避免当前工作被教程/reference 层带偏，始终优先服务真实产品主线。

---

## Current Mainline

当前工作主线是：

```text
coding-deepgent/
```

Trellis tasks、plans、spec updates 和 implementation decisions 默认都服务
`coding-deepgent/`。

---

## Reference-only Layer

除非任务明确指定，下列区域默认是 reference-only：

- `agents/`
- `agents_deepagents/`
- `docs/`
- `web/`
- tutorial/demo-oriented tests and teaching artifacts

这些内容可以用来：

- 教学说明
- source mapping / parity research
- 提炼思路或 examples

但它们不是当前默认实现目标。

---

## Decision Rule

任务模糊时按顺序判断：

1. 任务是否明确要求修改 tutorial/reference assets？
   - 是：按要求处理。
2. 否则，任务是否影响当前 product mainline？
   - 是：修改 `coding-deepgent/` 和 `.trellis/`。
3. 如果 tutorial/reference material 与 product direction 冲突：
   - tutorial 层只作为 evidence 或 examples
   - 以 `coding-deepgent` product boundaries 和 Trellis norms 为准

---

## 先读什么

当前主线实现前优先读：

- `AGENTS.md`
- `.trellis/workflow.md`
- `.trellis/project-handoff.md`
- `.trellis/spec/backend/*.md`
- `.trellis/spec/guides/*.md`
- `coding-deepgent/README.md`
- `coding-deepgent/PROJECT_PROGRESS.md`

教程/reference docs 只在主线来源不够时再读。

---

## Common Mistakes

- 把 tutorial chapter parity 当成 shipping goal
- 花时间修 `web/`、教程 `docs/` 或 teaching tests，但没有增强 `coding-deepgent`
- 没有 source-backed product justification 就把教程结构复制进产品代码
- Trellis 已记录规则后，还继续维护重复规范入口

---

## Practical Consequence

当前协作中：

- `.trellis/` 是 canonical coordination and norm layer
- `coding-deepgent/` 是 canonical product codebase
- tutorial/reference assets 只有在明确要求或避免误导未来工作时才更新
