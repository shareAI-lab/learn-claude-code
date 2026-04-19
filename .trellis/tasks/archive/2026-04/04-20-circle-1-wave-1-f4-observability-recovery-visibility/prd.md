# Circle 1 Wave 1 F4 Observability-Recovery Visibility

## Goal

Improve observability, evidence, and recovery visibility so long-task and
runtime-core parity work is understandable enough to trust and debug.

## Acceptance Targets

* Workflows A and B gain clearer runtime/recovery visibility during real use.
* This family supports Wave 1 runtime-core work rather than drifting into broad
  analytics/platform work.
* The next implementation slice is chosen based on daily-driver visibility
  value.

## Planned Features

* Re-audit observability/evidence/recovery surfaces against Circle 1 workflow
  needs.
* Identify the highest-value visibility gap still blocking daily-driver trust.
* Define the next implementation slice for this family.

## Planned Extensions

* External analytics backends
* Perfetto / provider-specific telemetry
* Remote/daemon observability surfaces

## Technical Notes

* Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Parent decomposition: `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`

## Implementation Summary

* Added a dedicated `Subagent activity:` recovery brief contribution that
  summarizes recent background subagent/fork notifications separately from the
  generic recent-evidence list.
* This improves recovery visibility for complex task decomposition and
  background child-agent work without expanding into full team-runtime parity.

## Verification

* `pytest -q coding-deepgent/tests/sessions/test_session_contributions.py coding-deepgent/tests/sessions/test_sessions.py coding-deepgent/tests/cli/test_cli.py -q`
* `ruff check coding-deepgent/src/coding_deepgent/sessions/subagent_activity.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/tests/sessions/test_session_contributions.py`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/sessions/subagent_activity.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/tests/sessions/test_session_contributions.py`
