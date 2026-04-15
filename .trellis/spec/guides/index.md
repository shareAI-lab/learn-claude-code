# 思考指南索引

> **Purpose**: 帮助 AI agent 在写代码前先想清楚边界、复用、对齐、阶段执行和文档落点。

---

## 这个目录负责什么

`guides/` 放的是“怎么思考”的指南，不是具体实现 contract。

- 具体模块规则、schema、测试要求 -> 写到 `.trellis/spec/backend/*.md`
- 方向、roadmap、里程碑 -> 写到 `.trellis/plans/*.md`
- 工作流程 -> 写到 `.trellis/workflow.md`
- 思考触发器、采访流程、文档地图 -> 写到这里

---

## 可用指南

| Guide | Purpose | When to Use |
|---|---|---|
| [Trellis Doc Map Guide](./trellis-doc-map-guide.md) | 说明高价值 Trellis 文档职责、阅读顺序和写入落点 | 不确定该读哪份 Trellis 文档或把新知识写到哪里 |
| [Interview-Driven Spec Expansion Guide](./interview-driven-spec-expansion-guide.md) | 通过聚焦采访补充 Trellis specs | 缺失信息依赖维护者判断或项目偏好 |
| [Mainline Scope Guide](./mainline-scope-guide.md) | 保持当前工作聚焦 `coding-deepgent` 主线 | 教程/reference 资产可能干扰主线判断 |
| [CC Alignment Guide](./cc-alignment-guide.md) | 让 `cc-haha` 对齐保持 source-backed 和 effect-driven | 功能需要对齐 Claude Code / `cc-haha` 行为 |
| [Staged Execution Guide](./staged-execution-guide.md) | 用 checkpoint 和验证预算推进多阶段任务 | 一个任务族需要跨 sub-stage 推进 |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | 思考跨层数据流和边界 | 功能跨多个层或 payload 会变化 |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | 发现已有模式，避免重复实现 | 写新 helper、改常量、看到重复模式时 |

---

## 快速触发器

### 需要理解 Trellis 文档体系时

- [ ] 不确定 `.trellis/` 哪份文档负责某条规则
- [ ] 需要 `coding-deepgent` 的推荐阅读顺序
- [ ] 准备通过采访补充 Trellis docs

→ 读 [Trellis Doc Map Guide](./trellis-doc-map-guide.md)

### 需要采访补 spec 时

- [ ] 代码和现有文档推导不出项目约定
- [ ] 答案依赖维护者偏好或产品方向
- [ ] 已经知道答案要写进哪份 Trellis 文档

→ 读 [Interview-Driven Spec Expansion Guide](./interview-driven-spec-expansion-guide.md)

### 需要确认主线范围时

- [ ] repo 同时存在 product code 和 tutorial/reference assets
- [ ] 需求提到 `docs/`、`web/`、`skills/`、教程测试等非主线资产
- [ ] 不确定是否需要追求教程 parity

→ 读 [Mainline Scope Guide](./mainline-scope-guide.md)

### 需要做 `cc-haha` 对齐时

- [ ] 任务要对齐 `cc-haha` 或 Claude Code 行为
- [ ] 名称相似，但本地效果还不明确
- [ ] 需要判断 `align / partial / defer / do-not-copy`

→ 读 [CC Alignment Guide](./cc-alignment-guide.md)

### 需要多阶段执行时

- [ ] 工作跨多个 sub-stage 或 checkpoint
- [ ] 需要 checkpoint 后自动 `continue / adjust / split / stop`
- [ ] 需要控制 `lean` / `deep` 验证预算

→ 读 [Staged Execution Guide](./staged-execution-guide.md)

### 需要思考跨层问题时

- [ ] 功能触及 3 层以上
- [ ] 数据格式或 payload 会变化
- [ ] 多个消费者依赖同一份数据
- [ ] 不确定逻辑该放在哪层

→ 读 [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### 需要复用检查时

- [ ] 正在写类似已有代码的实现
- [ ] 看到重复模式
- [ ] 正在改常量或配置
- [ ] 正在新增 utility/helper

→ 读 [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

---

## Pre-Modification Rule

改任何值之前先搜索。

```bash
rg -n "value_to_change" .
```

这不是形式主义。它能避免“只改了一处，忘了别的调用点”的问题。

---

## 贡献规则

发现新的可复用思考规则时：

- 如果是“要思考什么” -> 更新 `guides/`
- 如果是“代码必须怎么写” -> 更新 `spec/backend/`
- 如果是“当前任务的临时判断” -> 先写 active task `prd.md`
