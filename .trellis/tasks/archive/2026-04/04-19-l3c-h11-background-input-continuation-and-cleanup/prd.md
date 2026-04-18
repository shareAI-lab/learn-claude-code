# L3-c: H11 background input continuation and cleanup

## Goal

支持对后台子 agent 追加输入，并在结束后释放 worker 句柄。

## Requirements

* follow-up input 必须保留同一个 `run_id`
* running 状态下可以排队后续输入
* finished run 也可以被重新激活继续同一 child thread
* worker 结束后自动 cleanup 内存句柄

## Acceptance Criteria

* [x] `subagent_send_input` 保留同一个 `run_id`
* [x] follow-up input 会进入同一 background run
* [x] worker 结束后不会保留活跃句柄
