# 采访式补充 Spec 指南

> **Purpose**: 通过聚焦采访补齐 Trellis docs，同时避免产生重复、散乱或聊天记录式文档。

---

## Scope

当 Trellis docs 缺少真实项目知识，而这些知识依赖维护者判断、项目偏好或隐性约定时，使用这份 guide。

这份 guide 服务 `coding-deepgent` 主线文档，不服务教程/reference 层。

---

## 核心原则

采访不是聊天记录。

每个回答都应该写入拥有该规则、contract、decision 或 checklist 的最窄 Trellis 文档。

采访前先读 [Trellis 文档地图指南](./trellis-doc-map-guide.md)，确认目标文档。

---

## 什么时候采访

适合采访：

- 真实项目偏好，代码推导不出来
- 未来 agent 必须遵守的规则
- 多种可行方案之间的产品/维护取舍
- 尚未写入 spec 的 review expectation
- 维护者反复解释过的模糊点

不适合采访：

- 代码、测试、PRD、现有 specs 已经能推导出的事实
- 让用户替 agent 枚举代码结构
- 没有明确写入目标的宽泛问题

先推导，再只问剩下的高价值问题。

---

## 工作流程

### 1. 选择一个窄主题

好主题：

- module ownership
- testing expectation
- roadmap vs spec 的边界
- `cc-haha` 对齐边界
- LangChain schema 严格程度

坏问题：

```text
把所有项目规则都告诉我。
```

### 2. 先确定目标文档

| Answer type | Target |
|---|---|
| work process | `.trellis/workflow.md` |
| current mainline status | `.trellis/project-handoff.md` |
| roadmap / product direction | `.trellis/plans/*.md` |
| implementation rule | `.trellis/spec/backend/*.md` |
| thinking trigger | `.trellis/spec/guides/*.md` |
| completed-session record | `.trellis/workspace/<developer>/journal-N.md` via `record-session` |

如果目标文档不清楚，先提一个短 proposal，不要直接问宽泛问题。

快捷判断：

- `plans/` 写 goals、roadmap、sequencing、strategic tradeoffs
- `spec/` 写 implementation contracts、boundaries、schemas、tests
- plan decision 变成实现强约束时，要抽取到 owning spec

### 3. 一次问一个问题

推荐格式：

```text
对于 <specific topic>，未来 agent 应该遵循 A 还是 B？

1. A - <tradeoff>
2. B - <tradeoff>
3. Other - describe your preference
```

### 4. 立即写回 owning doc

用户回答后：

- 把 decision 写入目标 Trellis doc
- 必要时增加 example / anti-pattern
- 只有新增高价值文档或章节时才更新 index
- 不把 decision 只留在对话里

### 5. 在 active PRD 记录 interview trail

记录：

- question
- answer summary
- target document
- change made

这样可审计，但不会把 spec 变成聊天记录。

---

## Question Gate

提问前检查：

- 能否从 code/tests/docs 推导？
- 这是 preference 或 blocking decision 吗？
- 目标 Trellis doc 是否明确？
- 能否压成一个具体问题？

任一答案为否，就继续检查或缩窄主题。

---

## 本 repo 的高价值采访主题

- `coding-deepgent` module ownership boundaries
- LangChain/LangGraph abstraction tolerance
- `cc-haha` 行为何时 `align / partial / defer / do-not-copy`
- staged work 的验证强度
- `plans/` vs `spec/backend/` 的写入边界
- `project-handoff.md` vs workspace journal 的记录边界

低价值主题：

- 问代码里已经可见的内容
- 让用户口述目录结构
- 一次性填所有 placeholder specs
- 没有写入目标的哲学问题

---

## Interview Note 格式

写在 active task PRD：

```md
## Interview Note: <topic>

Question:
- <exact question or summary>

Answer:
- <maintainer decision>

Target doc:
- `<path>`

Change made:
- <section updated / rule added>
```

---

## MVP Interview Loop

第一次补 Trellis docs 时：

1. 建立当前 doc map。
2. 找 top 3 gaps。
3. 选最高价值 gap。
4. 问一个问题。
5. 更新 owning doc。
6. 重新判断下一个 gap 是否仍成立。

不要进行开放式采访马拉松。

---

## Stop Conditions

停止采访：

- 下一个问题太宽泛
- 目标文档不清楚
- 用户给出的决定应该变成新的 PRD
- 更新目标文档会冲突现有 Trellis guidance
- 本轮已经产生足够一个 reviewable slice 的改动

---

## Maintenance Rule

这份 guide 只负责采访流程。

采访产生的项目规则必须写入具体 owning docs。
