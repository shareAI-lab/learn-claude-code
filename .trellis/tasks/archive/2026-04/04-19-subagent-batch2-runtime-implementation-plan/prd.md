# subagent batch2 runtime implementation plan

## Goal

完成第二批子 agent 能力：后台运行、进度、完成通知、追加输入、worker cleanup、插件提供的 agent definitions。

## Requirements

* 保持当前 H11/H12 主线，不引入 mailbox / coordinator / team runtime。
* 后台运行必须走现有 `subagents/runtime/sessions/store` seam。
* 进度与通知必须是 bounded local runtime facts，不引入外部队列系统或 daemon。
* 插件 agent 只提供 definitions source，不新增第二套执行平面。

## Task Breakdown

* `L3-a`: background subagent runtime surface
* `L3-b`: progress + notification contract
* `L3-c`: queued follow-up input + cleanup
* `L3-d`: plugin-provided subagent definitions

## Execution Order

1. `L3-d` can land independently but must join the same agent-definition merge path.
2. `L3-a` first for runtime surface.
3. `L3-b` and `L3-c` on top of `L3-a`.

## Out of Scope

* mailbox / SendMessage
* coordinator runtime
* background fork workers
* remote/daemon execution
