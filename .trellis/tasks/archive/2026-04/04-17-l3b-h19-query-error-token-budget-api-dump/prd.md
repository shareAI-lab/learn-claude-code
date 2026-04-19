# L3-b: H19 query error, token budget, and API dump

## Goal

Implement H19-C: structured `query_error`, per-turn `token_budget`, and env-gated API/prompt dump.

## Requirements

* Emit structured `query_error` runtime event with bounded fields such as error class, phase, and retry count.
* Emit `token_budget` for each assistant response turn, not only compact boundaries.
* Add env-gated prompt/API dump controlled by `CODING_DEEPGENT_DUMP_PROMPTS=1`.
* Keep dumps out of normal production paths and avoid leaking secrets into model-visible context.

## Acceptance Criteria

* [x] Runtime query failures produce structured evidence without depending on stderr logs.
* [x] Every assistant response can emit bounded token-budget metadata.
* [x] API dump is disabled by default and enabled only by environment gate.
* [x] Existing runtime/CLI tests stay deterministic when dump is disabled.

## Dependencies

* Depends on `L1-b`.
* Depends on `L2-b`.

## Context Sources

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`
* `.trellis/spec/backend/logging-guidelines.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`

## Out of Scope

* CLI flag for dumps.
* Provider-specific cache/cost breakdown.
* Perfetto or external analytics.
