# L4-c: H12 abort cleanup and kill semantics

## Goal

补齐后台 fork / subagent 的停止、失败收尾、worker cleanup 语义。

## Requirements

* 运行中的 fork/subagent 可以被显式停止
* 结束后 worker 句柄、挂起状态、通知状态都要正确收尾
* 失败路径不能留下半死状态

## Acceptance Criteria

* [ ] stop/kill 行为有明确 contract
* [ ] cleanup 不遗漏活跃 worker 句柄
* [ ] 失败/终止状态可恢复、可观察
