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
| `coding-deepgent-h01-h10-target-design.md` | Source-backed target design for the first highlight band | When implementing or reviewing H01-H10-related behavior |
| `master-plan-coding-deepgent-reconstructed.md` | Reconstructed product identity, architecture baseline, and stage model | When re-orienting after plan loss or checking long-term direction |
| `prd-coding-deepgent-runtime-foundation.md` | Runtime foundation PRD and architecture constraints | When touching runtime/container/domain skeleton boundaries |
| `test-spec-coding-deepgent-runtime-foundation.md` | Runtime foundation verification plan | When auditing or rebuilding foundation validation |

## Supporting Planning Files

| File | Role | Notes |
|---|---|---|
| `coding-deepgent-runtime-foundation-20260412T213209Z.md` | Recovered context snapshot | Provenance/supporting context, not the primary roadmap |
| `runtime-foundation-recovery-notes-2026-04-14.md` | Recovery notes from plan migration | Historical recovery context |

## Maintenance Rules

- Keep this index short and navigational.
- Update the roadmap/dashboard before creating new stage plans.
- Promote reusable implementation constraints into `.trellis/spec/`.
- Do not make plans the only place a future agent can find mandatory coding rules.
