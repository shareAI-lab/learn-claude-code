# 跨层思考指南

> **Purpose**: 在实现前梳理数据如何跨层流动，避免边界 bug。

---

## 问题

大多数复杂 bug 出现在层与层之间，而不是单个函数内部。

常见问题：

- API 返回格式 A，调用方期待格式 B
- service 写入 X，resume 读取时变成 Y
- 多个模块各自实现同一段 validation
- model-visible payload 和 persisted record 不一致

---

## 实现前检查

### 1. 画出数据流

```text
Source -> Transform -> Store -> Retrieve -> Transform -> Display/Model
```

每个箭头都问：

- 当前格式是什么？
- 谁负责 validation？
- 出错时在哪里转换 error？
- 是否需要写入 spec contract？

### 2. 找出边界

| Boundary | Common Issues |
|---|---|
| tool schema -> domain service | 字段名、必填项、默认值不一致 |
| domain service -> store/session | record shape 漂移 |
| runtime state -> prompt/context | payload 过大或格式不稳定 |
| CLI -> service | 用户错误没有转成 `ClickException` |
| middleware -> tool result | 破坏 tool_call/tool_result invariant |

### 3. 定义 contract

每个边界至少明确：

- input shape
- output shape
- validation rule
- error behavior
- tests required

---

## 什么时候必须更新 spec

如果跨层行为改变了：

- command/API/tool schema
- runtime state fields
- persisted record fields
- model-visible payload
- validation/error matrix

就更新对应 `.trellis/spec/backend/*.md`。

---

## 常见错误

### 1. 隐式格式假设

Bad:

- “这个 field 应该一直存在”

Good:

- 在 schema 或 loader 中显式验证，并写 tests。

### 2. 分散 validation

Bad:

- schema、service、middleware 各校验一遍且规则不同。

Good:

- 入口 schema / owning domain 负责主校验，其他层只保护自己的边界。

### 3. 把 display 当 contract

Bad:

- 根据 Rich/CLI 文本反推数据状态。

Good:

- contract 写在 typed record / JSON metadata / state schema 中。

---

## Checklist

实现前：

- [ ] 数据流已画出
- [ ] 边界已列出
- [ ] 每个边界的 input/output shape 明确
- [ ] validation ownership 明确
- [ ] error behavior 明确

实现后：

- [ ] 有 focused tests 覆盖边界
- [ ] invalid/empty/missing cases 有测试
- [ ] 数据 round-trip 后仍保持 contract
- [ ] 必要时更新 `.trellis/spec/backend/*`
