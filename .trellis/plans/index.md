# Trellis Plans Index

> Long-lived product direction and planning memory for the current `coding-deepgent` mainline.

Use these through Trellis instead of the removed `.omx/` tree.

Plans own direction, sequencing, roadmap state, product tradeoffs, and milestone
boundaries. Executable implementation rules should be extracted into
`.trellis/spec/` when they become mandatory for future work.

## Canonical Planning Files

| File | Role | When to read |
|---|---|---|
| `coding-deepgent-cc-core-highlights-roadmap.md` | Canonical H01-H22 highlight dashboard and MVP/future boundary | Before choosing or changing mainline roadmap work |
| `coding-deepgent-h01-tool-module-alignment-plan.md` | H01 tool-module alignment plan: five-factor tool protocol, projection, non-streaming concurrency, and deferred ToolSearch/streaming boundaries | Before implementing or reviewing tool-system, MCP/plugin/skill tool registration, or subagent tool surfaces |
| `coding-deepgent-h01-h10-target-design.md` | Source-backed target design for the first highlight band | When implementing or reviewing H01-H10-related behavior |
| `master-plan-coding-deepgent-reconstructed.md` | Reconstructed product identity, architecture baseline, and stage model | When re-orienting after plan loss or checking long-term direction |
| `prd-coding-deepgent-runtime-foundation.md` | Runtime foundation PRD and architecture constraints | When touching runtime/container/domain skeleton boundaries |
| `test-spec-coding-deepgent-runtime-foundation.md` | Runtime foundation verification plan | When auditing or rebuilding foundation validation |

## Supporting Planning Files

| File | Role | Notes |
|---|---|---|
| `coding-deepgent-runtime-foundation-20260412T213209Z.md` | Recovered context snapshot | Provenance/supporting context, not the primary roadmap |
| `runtime-foundation-recovery-notes-2026-04-14.md` | Recovery notes from plan migration | Historical recovery context |

## Source-Backed Alignment Research

Research artifacts live in the brainstorm task directory, not in `plans/`, but
are referenced here so implementers can find them from the planning index:

| File | Covered highlights | Notes |
|---|---|---|
| `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md` | H11 Agent-as-tool / H12 Fork/cache subagent | Gap matrix + sub-task decomposition (A general runtime + catalog, B sidechain transcript, C deferred ADR) |
| `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md` | H19 Observability / evidence ledger | Gap matrix + Stage 28 closeout scope (A1 queued sink, B2/B3/B4 compact events, B6 query_error, B8 token_budget, C1 API dump, E1 logger) |

## Maintenance Rules

- Keep this index short and navigational.
- Update the roadmap/dashboard before creating new stage plans.
- Promote reusable implementation constraints into `.trellis/spec/`.
- Do not make plans the only place a future agent can find mandatory coding rules.
