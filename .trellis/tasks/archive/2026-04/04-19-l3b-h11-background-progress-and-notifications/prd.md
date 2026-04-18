# L3-b: H11 background progress and notifications

## Goal

让后台子 agent 具备最小可用进度与完成通知。

## Requirements

* 状态里要有 progress summary
* 状态里要有 recent activities
* 完成或失败要写一条 bounded notification evidence

## Acceptance Criteria

* [x] 状态记录包含进度摘要
* [x] 状态记录包含 recent activities
* [x] 完成/失败会追加 `subagent_notification` evidence
