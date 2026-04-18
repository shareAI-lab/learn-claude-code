# L4-a: H12 background fork runtime

## Goal

让显式 `run_fork` 真的进入后台 fork worker 形态，而不是继续停留在前台同步 fork。

## Requirements

* fork 能通过现有 background runtime 真正跑在后台
* 仍保持显式 `run_fork` 入口
* 不新增隐式 fork 入口

## Acceptance Criteria

* [ ] fork 可以后台启动并返回稳定 run id / thread lineage
* [ ] background fork 能被查询状态
* [ ] foreground/background fork 不会分裂成两套不一致 contract
