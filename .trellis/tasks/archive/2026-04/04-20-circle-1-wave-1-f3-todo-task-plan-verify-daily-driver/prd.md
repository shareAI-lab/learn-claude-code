# Circle 1 Wave 1 F3 Todo-Task-Plan-Verify Daily-Driver

## Goal

Turn the existing todo/task/plan/verify surfaces into a practical personal
workflow amplifier for complex coding tasks.

## Acceptance Targets

* Workflow C improves materially: todo/task/plan/verify is useful in real
  complex development work, not just contract-correct.
* The family has a clear parity judgment against Claude Code public behavior
  and `cc-haha` workflow references.
* The next implementation slice is chosen based on real throughput gains.

## Planned Features

* Re-audit current todo/task/plan/verify surfaces against daily-driver personal
  workflow expectations.
* Identify where workflow friction remains despite current MVP contracts.
* Define a concrete follow-up slice for this family.

## Planned Extensions

* Coordinator / team-runtime planning
* Mailbox-driven collaboration
* Richer multi-agent workflow orchestration

## Technical Notes

* Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Parent decomposition: `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`

## Implementation Summary

* Frontend event flow now emits durable `task_snapshot` data alongside
  `todo_snapshot`, so the local UI/bridge protocol can surface active task
  graph state rather than only short-term todos.
* The snapshot is fail-soft: if no runtime store is available, it emits an
  empty task list instead of breaking the run flow.

## Verification

* `pytest -q coding-deepgent/tests/frontend/test_frontend_event_mapping.py coding-deepgent/tests/frontend/test_frontend_bridge.py coding-deepgent/tests/frontend/test_frontend_client.py coding-deepgent/tests/frontend/test_frontend_runs.py coding-deepgent/tests/frontend/test_frontend_gateway.py -q`
* `ruff check coding-deepgent/src/coding_deepgent/frontend/event_mapping.py coding-deepgent/src/coding_deepgent/frontend/producer.py coding-deepgent/tests/frontend/test_frontend_event_mapping.py coding-deepgent/tests/frontend/test_frontend_bridge.py coding-deepgent/tests/frontend/test_frontend_client.py`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/frontend/event_mapping.py coding-deepgent/src/coding_deepgent/frontend/producer.py coding-deepgent/tests/frontend/test_frontend_event_mapping.py coding-deepgent/tests/frontend/test_frontend_bridge.py coding-deepgent/tests/frontend/test_frontend_client.py`
