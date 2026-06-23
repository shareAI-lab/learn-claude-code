# s00a: Query Control Plane

> **Status: Planned** — This chapter is under design.

## 概念

控制平面（Control Plane）负责 Agent 运行时的调度、路由与资源分配。区别于数据平面（执行工具、读写文件），控制平面决定"下一步做什么"。

## 规划内容

- 请求路由：用户输入 → Agent Loop → Tool Dispatch
- 资源调度：上下文预算、并发限制、超时控制
- 状态管理：会话状态、任务依赖、团队协调

## 与其他章节的关系

| 章节 | 层级 | 关系 |
|------|------|------|
| s01 Agent Loop | 数据平面 | 控制平面调度其执行 |
| s07 Task System | 控制平面 | 任务 DAG 是调度核心 |
| s09 Agent Teams | 控制平面 | 团队协调属于控制平面 |
| s12 Worktree Isolation | 控制平面 | 并行执行资源隔离 |

---

本章正在设计中，欢迎在 [Issue #266](https://github.com/shareAI-lab/learn-claude-code/issues/266) 讨论方向。
