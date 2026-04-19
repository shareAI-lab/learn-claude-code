# Circle 2 Expanded Parity Baseline

## Goal

一口气完成 Circle 2 本地 expanded parity baseline：实现 substrate-first 计划里的 durable worker/event substrate、mailbox、local team orchestration、remote-control records、extension lifecycle、cross-day continuity、Circle 2 acceptance harness。

## Requirements

- Implement durable local event stream and worker records.
- Implement mailbox send/list/ack with idempotent delivery key support.
- Implement local team run records with coordinator/worker assignments and progress synthesis.
- Implement local remote-control record/event replay surface without pretending to have hosted SaaS.
- Implement extension lifecycle state: install/register, enable/disable, update metadata, rollback.
- Implement continuity artifacts for cross-day resume/memory notes.
- Add CLI command groups and tests.
- Update Trellis docs and project status.

## Acceptance Criteria

- [x] `workers` / `events` CLI commands work over durable local store.
- [x] `mailbox` CLI commands support send/list/ack and duplicate delivery protection.
- [x] `teams` CLI commands support create/assign/progress/status.
- [x] `remote` CLI commands support session registration, control, and event replay records.
- [x] `extension-lifecycle` CLI commands support register/enable/disable/update/rollback.
- [x] `continuity` CLI commands support save/list/show continuity artifacts.
- [x] `acceptance circle2` passes.
- [x] Full Python/TS validation passes.

## Out of Scope

- Hosted SaaS session ingress.
- Multi-user auth/billing.
- Real IDE plugin implementation.
- Public marketplace backend.
- Cross-machine worker process supervision.

## Technical Notes

- Canonical plan: `.trellis/plans/coding-deepgent-circle-2-expanded-parity-plan.md`
- Use local `runtime.store` file backend as durable substrate.
- Keep new domains out of `sessions/`, `subagents/tools.py`, `tool_system/`, and `frontend/producer.py`.
