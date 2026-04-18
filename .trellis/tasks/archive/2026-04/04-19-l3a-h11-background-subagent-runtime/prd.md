# L3-a: H11 background subagent runtime

## Goal

增加后台子 agent 运行 surface，让子 agent 可以异步启动并通过稳定 run id 被查询。

## Requirements

* 新增后台启动工具。
* 背景 run 要有持久化状态记录。
* 状态查询必须返回结构化记录。

## Acceptance Criteria

* [x] 后台启动返回稳定 `run_id`
* [x] 状态查询能看到 queued/running/completed/failed
* [x] 后台 run 不依赖新 daemon/remote process

## Out of Scope

* team runtime
* mailbox
