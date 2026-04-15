# Trellis 文档地图指南

> **Purpose**: 说明当前 `coding-deepgent` 主线中高价值 `.trellis/` 文档的职责、阅读顺序和写入落点。

---

## Scope

这份 guide 只覆盖当前主线高频使用的 Trellis 文档。

它不试图解释 `.trellis/scripts/`、配置文件、历史归档任务和所有内部细节。

用途：

- 给维护者看：理解 Trellis 文档职责分层
- 给 AI agent 看：知道先读什么、把新知识写到哪里

---

## 核心原则

Trellis 不应该变成一份巨型 handbook。

当前分工是：

- `workflow.md` 说明 **工作如何流转**
- `project-handoff.md` 说明 **当前主线状态**
- `plans/` 说明 **长期产品方向**
- `spec/backend/` 说明 **实现时必须遵守的规则**
- `spec/guides/` 说明 **改动前应该怎么思考**
- `workspace/` 记录 **完成后发生了什么**

新增知识时，写进“最窄且真正拥有它”的文档。

---

## 高价值文档层级

| Layer | Main paths | Owns | Does not own |
|---|---|---|---|
| Workflow | `.trellis/workflow.md` | session flow、task lifecycle、staged execution、finish/record expectations | product architecture details |
| Mainline handoff | `.trellis/project-handoff.md` | 当前 `coding-deepgent` 目标、latest verified state、minimal resume procedure | 详细 implementation contracts |
| Plans | `.trellis/plans/index.md`, `.trellis/plans/*.md` | roadmap、target design、stage sequencing、milestone boundaries | 日常 coding conventions |
| Backend specs | `.trellis/spec/backend/index.md`, `.trellis/spec/backend/*.md` | implementation contracts、module boundaries、quality rules、LangChain-native rules | 广泛 brainstorm notes |
| Thinking guides | `.trellis/spec/guides/index.md`, `.trellis/spec/guides/*.md` | pre-implementation thinking、source alignment、staged work、scope checks | 精确 code/API contracts |
| Deferred frontend specs | `.trellis/spec/frontend/index.md`, `.trellis/spec/frontend/*.md` | future frontend activation conditions | 当前 `coding-deepgent` product rules |
| Workspace records | `.trellis/workspace/index.md`, `.trellis/workspace/<developer>/journal-N.md` | completed session summaries、commit/session records | future requirements 或 canonical rules |

---

## 阅读顺序

### 维护者

想理解或调整项目方向时，按这个顺序：

1. `AGENTS.md`
2. `.trellis/workflow.md`
3. `.trellis/project-handoff.md`
4. `.trellis/plans/index.md`
5. `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
6. `.trellis/spec/backend/index.md`
7. `.trellis/spec/guides/index.md`

之后只打开当前决策需要的具体 topic docs。

### AI agent

实现前按这个顺序：

1. `AGENTS.md`
2. `.trellis/workflow.md`
3. `python3 ./.trellis/scripts/get_context.py`
4. 如果任务涉及当前主线状态，读 `.trellis/project-handoff.md`
5. backend/product work 读 `.trellis/spec/backend/index.md`
6. 需要思考触发器时读 `.trellis/spec/guides/index.md`
7. 读 active task `prd.md` 和注入的 `implement.jsonl` / `check.jsonl`

不要无差别读取整个 `.trellis/tasks/` 或 `.trellis/plans/` 树。

---

## 新知识写到哪里

| New knowledge type | Write it here | Example |
|---|---|---|
| 工作流程变化 | `.trellis/workflow.md` | staged validation budget changed |
| 当前主线状态变化 | `.trellis/project-handoff.md` | latest verified stage family updated |
| 普通完成会话 | `.trellis/workspace/<developer>/journal-N.md` via `record-session` | daily progress summary |
| 长期 roadmap 变化 | `.trellis/plans/*.md` | H-row status or MVP boundary changed |
| 模块职责或布局变化 | `.trellis/spec/backend/directory-structure.md` | new domain package added |
| LangChain/LangGraph 规则变化 | `.trellis/spec/backend/langchain-native-guidelines.md` | tool schema rule changed |
| review/testing 规则变化 | `.trellis/spec/backend/quality-guidelines.md` | new forbidden pattern |
| runtime/session/compact contract 变化 | `.trellis/spec/backend/*-contracts.md` | new compact invariant |
| task/plan/verifier contract 变化 | `.trellis/spec/backend/task-workflow-contracts.md` | new verifier evidence rule |
| thinking checklist 变化 | `.trellis/spec/guides/*.md` | new scope or alignment trigger |

---

## Plans vs Specs

`plans/` 写方向：

- product goals
- roadmap rows
- stage sequencing
- strategic tradeoffs
- deferred / do-not-copy decisions
- milestone boundaries

`spec/` 写可执行约束：

- implementation contracts
- schemas and signatures
- module boundaries
- validation/error matrices
- testing requirements
- concrete do/don't rules

如果 plan 里的决定变成未来每次实现都必须遵守的规则，要抽取到 owning spec。

---

## Task PRD vs Workspace Journal

工作进行中使用 active task PRD。

PRD 负责：

- requirements / acceptance criteria
- interview notes
- scope decisions
- implementation checkpoints
- verification evidence
- unresolved questions

工作完成并提交后使用 workspace journal。

Journal 负责：

- completed session summary
- commit list
- final testing notes
- next-step handoff

不要让未来 agent 必须翻 journal 才能恢复 active task 的需求。

---

## 什么时候必须更新 Specs

当改动创建或改变未来 agent 必须遵守的 implementation contract 时，更新 `.trellis/spec/*`。

触发条件：

- tool schema / command / API shape 改变
- runtime state fields 或 payload formats 改变
- module ownership 或 boundary 改变
- validation / error behavior 改变
- testing requirements 或 verification matrix 改变
- cross-layer transformation 改变
- repeated mistake 需要变成 rule / anti-pattern

普通实现细节不要写进 spec。

---

## CC Alignment 记录位置

`cc-haha` 对齐按这个顺序记录：

1. Active task PRD
   - expected effect
   - source files inspected
   - alignment matrix
   - `align / partial / defer / do-not-copy`
2. `.trellis/plans/`
   - 稳定的 roadmap / product-direction 结果
3. `.trellis/spec/`
   - 未来实现必须遵守的 executable constraints

不要把探索性 source notes 默认变成 canonical specs。

---

## Summary docs vs Atomic specs

地图/总结文档用于：

- orientation
- reading order
- responsibility boundaries
- “这条规则应该写到哪里？”

原子 spec 用于：

- concrete implementation rules
- signatures and contracts
- validation/error matrices
- examples and anti-patterns

不要把原子 spec 的细节复制到地图文档里。地图只负责指路。

---

## Interview-driven expansion

采访补文档时：

1. 识别缺失知识类别。
2. 从上面的表选择 owning Trellis document。
3. 一次只问一个问题。
4. 回答立即写入 owning doc。
5. 只有文档结构或路由规则变化时，才更新这份地图。

---

## Frontend 状态

frontend specs 当前是 future-activatable placeholders。

只有当任务明确把 frontend/web product work 纳入主线时，才激活这些 spec。

---

## Lightweight Path Checks

重组 Trellis docs 后运行：

```bash
python3 ./.trellis/scripts/check_trellis_links.py
```

这是 Markdown link smoke check，不替代人工 review。

---

## Maintenance Rules

- 保持这份 guide 可快速扫描。
- 只有当新文档成为高价值入口时，才加入地图。
- 优先更新 owning atomic doc，不要扩张这份地图。
- 如果两份文档看起来拥有同一条规则，在这里澄清 ownership。
