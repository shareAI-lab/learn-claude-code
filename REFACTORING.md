# 增量重构计划

本文件记录 learn-claude-code 仓库的增量重构计划。每个阶段独立可交付，避免大爆炸式重构。

## 阶段 1: 重复代码抽取

| 范围 | 问题 | 方案 |
|------|------|------|
| s01-s20 | `safe_path` / `_safe_path` 重复定义 20 次 | 抽取到 `agents/_common.py` |
| s01-s20 | `run_bash` / `_run_bash` 重复定义 | 抽取到 `agents/_common.py` |
| s01-s20 | TOOLS 列表重复定义 | 抽取到 `agents/_tools.py` |

## 阶段 2: 命名一致性

| 范围 | 问题 | 方案 |
|------|------|------|
| 目录名 | s06_subagent vs s08_context_compact（实际 s06 是 subagent，s08 是 compact） | 统一为 s{NN}_{topic} |
| 函数名 | `micro_compact` vs `snip_compact` vs `reactive_compact` | 统一术语表 |
| 变量名 | `WORKDIR` vs `workdir` vs `cwd` | 统一为 `WORKDIR` |

## 阶段 3: 测试补齐

| 范围 | 现状 | 目标 |
|------|------|------|
| s01-s05 | 无测试 | smoke test |
| s06-s10 | 部分测试 | 覆盖核心路径 |
| s11-s20 | 无测试 | smoke test |
| s_full | 部分测试 | 覆盖多 bug 修复点 |

## 原则

1. 每个阶段独立 PR，不混合多个阶段
2. 保持向后兼容，不改变公开 API
3. 重构与功能修复分开提交
4. 优先处理高频重复，低风险项

## 进度

- [ ] 阶段 1: 重复代码抽取
- [ ] 阶段 2: 命名一致性
- [ ] 阶段 3: 测试补齐

---

讨论请参与 [Issue #349](https://github.com/shareAI-lab/learn-claude-code/issues/349)
