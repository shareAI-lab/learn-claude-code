# s17: Secure Extension Harness (安全扩展总成)

`s02 > s13 > s14 | s15 | s16 > [ s17 ]`

> *"生产级 Harness 的核心不是功能多，而是各层职责清晰"*
>
> **Harness 层**: 安全管线 -- 将所有防御层组合为一条执行路径。

## 问题

s13-s16 各自是一个能独立运行的 Agent。真实系统需要所有层在一条执行管线中协同工作。问题在于：如何组合而不冲突？

## 解决方案

```
    LLM 调用工具
         |
         v
    +---------------------+
    | [1] Pre-tool Hook   | --block--> 返回错误
    +----------+----------+
               v
    +---------------------+
    | [2] 分类器          | --deny---> 返回错误
    +----------+----------+
               v
    +---------------------+
    | [3] 权限检查        | --deny---> 返回错误
    |                     | --ask---> 用户确认?
    +----------+----------+
               v
    +---------------------+
    | [4] 执行            |  内建 handler 或 MCP
    +----------+----------+
               v
    +---------------------+
    | [5] Post-tool Hook  |  观察 / 日志
    +----------+----------+
               |
               v
         返回结果
```

每一层只回答一个问题:

| 层 | 问题 | 来源 |
|----|------|------|
| Hook | "这个动作需要被拦截吗？" | s15 |
| 分类器 | "这个命令的意图是什么？" | s14 |
| 权限 | "这个意图被允许吗？" | s13 |
| 执行 | "执行并返回结果" | s02 + s16 |

## 工作原理

1. `execute_tool()` 对每次工具调用运行 5 层管线。

2. 每层独立 -- 移除任何一层，其他层不受影响。

3. REPL 命令: `/security`, `/hooks`, `/mcp`, `/audit`。

## 相对 s16 的变更

| 组件 | 之前 (s13-s16 独立) | 之后 (s17) |
|------|-------------------|-----------|
| 安全管线 | 各章独立运行 | 统一 `execute_tool` 管线 |
| 分类器 | 独立运行 | 嵌入 Hook -> Classify -> Permission 流程 |
| Hooks | 独立运行 | 作为管线第一层和最后一层 |
| MCP | 独立运行 | 作为管线执行层的一部分 |

## 试一试

```sh
cd learn-claude-code
python agents/s17_secure_extension_harness.py
```

1. `list all python files` (所有层通过 -> allow)
2. `run rm -rf /` (分类器拒绝 -> 被拦截)
3. `write a test file and show audit log` (PostToolUse hook 记录 -> `/audit`)
4. `search for 'PermissionGuard' via MCP` (MCP 工具通过管线调用)
5. `register a hook that blocks all pip commands` (动态 hook 注册)
