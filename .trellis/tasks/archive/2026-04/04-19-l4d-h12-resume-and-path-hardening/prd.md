# L4-d: H12 resume and path hardening

## Goal

让 H12 在恢复、路径变化、worktree 漂移这些长任务场景下更可靠。

## Requirements

* fork/subagent resume 要对 path/worktree drift 更稳
* 恢复时保持单一显式 fork surface
* 不为旧 resume state 做桥接兼容

## Acceptance Criteria

* [ ] 路径/工作区变化下 resume 行为更稳
* [ ] resume 失败有明确错误，不静默 fallback
* [ ] 新恢复 contract 不依赖旧数据兼容层
