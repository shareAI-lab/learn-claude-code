# 代码复用思考指南

> **Purpose**: 在写新代码前先找已有模式，减少重复实现和配置漂移。

---

## 核心原则

新增 helper、常量、配置、schema 或流程前，先搜索。

```bash
rg -n "keyword_or_value" .
```

这能避免：

- 同一规则出现两份实现
- 只更新一个调用点
- 新旧配置并存
- 文档和代码 contract 不一致

---

## 什么时候必须先搜

- 新增 utility/helper
- 修改常量或配置值
- 新增 tool/schema/state field
- 新增文件路径规则
- 修改 command/API shape
- 看到相似逻辑第三次出现

---

## 搜索策略

### 1. 搜索名字

```bash
rg -n "function_or_field_name" coding-deepgent .trellis
```

### 2. 搜索值

```bash
rg -n "exact_value" .
```

### 3. 搜索概念

```bash
rg -n "compact|session_memory|permission_denied|plan_get" coding-deepgent .trellis
```

### 4. 搜索测试

```bash
rg -n "expected behavior" coding-deepgent/tests
```

---

## 复用决策

找到已有实现后：

- 如果职责相同，复用或扩展 existing seam
- 如果职责相近但边界不同，记录区别，避免硬合并
- 如果已有实现是错误抽象，先在 PRD 说明为什么不复用

不要为了“减少文件数量”把不同 product concept 合并。

---

## 常见反模式

### 1. 新增第二套配置

Bad:

- 新增一个阈值，但已有 settings/provider 已经有同类字段。

Good:

- 扩展 owning settings 或 domain policy。

### 2. 新增第二个 renderer

Bad:

- 为一个新场景复制已有 render 逻辑。

Good:

- 复用 existing renderer seam，或明确说明输出 contract 不同。

### 3. 新增第二个 store namespace

Bad:

- 同一 domain 的 record 分散到多个 namespace。

Good:

- 让 owning domain 决定 namespace 和 schema。

---

## Trellis 更新规则

如果你发现可复用模式已经稳定：

- 代码结构规则 -> `.trellis/spec/backend/directory-structure.md`
- LangChain/schema 规则 -> `.trellis/spec/backend/langchain-native-guidelines.md`
- review/testing 规则 -> `.trellis/spec/backend/quality-guidelines.md`
- 只是一条思考触发器 -> 留在本 guide

如果只是当前任务的一次判断，先写 active task PRD。
