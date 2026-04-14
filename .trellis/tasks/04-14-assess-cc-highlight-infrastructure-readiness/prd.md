# brainstorm: assess infrastructure readiness for cc highlights

## Goal

Determine whether the current `coding-deepgent` infrastructure is ready to support the planned cc-haha core highlight upgrades. If the foundation is not ready, define the infrastructure-first stage that should happen before advanced highlight work.

## What I already know

* The product goal is to implement cc-haha Agent Harness essence in a LangChain-native, professional-grade product track.
* The user wants source reading and target design to happen now, before implementation work.
* The core highlight roadmap exists at `.omx/plans/coding-deepgent-cc-core-highlights-roadmap.md`.
* The source-backed H01-H10 target design exists at `.omx/plans/coding-deepgent-h01-h10-target-design.md`.
* H01/H02/H03 are directionally strong locally:
  - tool-first runtime has `ToolCapability`, `CapabilityRegistry`, `ToolPolicy`, and `ToolGuardMiddleware`
  - permission runtime has deterministic modes/rules/hard safety through `PermissionManager`
  - prompt contract has `PromptContext` and tests guarding prompt wording drift
* H08 TodoWrite is strong locally:
  - public tool name `TodoWrite`
  - strict `todos` schema
  - required `content/status/activeForm`
  - `Command(update=...)`
  - stale reminders and parallel-call rejection
* H04/H05 are weaker infrastructure:
  - no general typed dynamic context payload protocol
  - no context lifecycle taxonomy
  - no message/context projection layer
  - only basic tool-result budget truncation exists
  - no compact boundary / microcompact / autocompact / reactive compact
  - no invariant tests around tool-use/tool-result pairing through projection/compaction
* H06/H07 have useful foundations but need integration hardening:
  - session JSONL, state snapshots, evidence, and loaded session models exist
  - memory store/save/recall and memory context middleware exist
  - memory quality policy, bounded recall tests, and session/recovery integration still need strengthening
* H09/H10/H11+ should not be the immediate next focus until context/recovery/subagent foundations are clearer.

## Assumptions (temporary)

* Infrastructure readiness should be judged against the first ten highlights, not all 22 at once.
* A foundation stage is preferable to starting advanced multi-agent/team/plugin marketplace work too early.
* The next implementation stage should stay small enough to verify with deterministic tests and not require live model calls.

## Open Questions

* None for the current readiness decision.

## Requirements (evolving)

* Decide if current infrastructure is sufficient for later highlight upgrades.
* If not sufficient, define the infrastructure-first stage.
* Keep the decision source-backed against cc-haha and current `coding-deepgent` code.
* Keep LangChain-native boundaries: do not replace `create_agent` / LangGraph runtime with a custom query loop.
* Preserve benefit-gated complexity: no work proceeds only because it is "closer to cc".

## Acceptance Criteria (evolving)

* [x] H01-H10 are audited against current local implementation.
* [x] A source-backed target design exists for H01-H10.
* [x] Infrastructure gaps are identified.
* [x] A recommended next stage is named.
* [ ] User confirms or adjusts the recommended next stage before implementation planning.

## Definition of Done (team quality bar)

* No implementation code is changed in this brainstorm task.
* Planning docs are updated with evidence and a concrete next-stage recommendation.
* Future implementation work still requires task workflow, spec context, tests, and quality checks.

## Out of Scope (explicit)

* Implementing Stage 12 code now
* Starting advanced coordinator/team/mailbox work
* Implementing auto classifier or rich permission UI
* Implementing full LLM autocompact now
* Plugin marketplace/install/update parity

## Technical Notes

* Created task: `.trellis/tasks/04-14-assess-cc-highlight-infrastructure-readiness`
* Planning docs:
  - `.omx/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.omx/plans/coding-deepgent-h01-h10-target-design.md`
* Current recommendation from source-backed target design:
  - next stage should be `Stage 12: Context and Recovery Hardening`
  - implement it iteratively as 12A-12D rather than as one large infrastructure push
* Candidate Stage 12 scope:
  - typed dynamic context payload protocol
  - deterministic message/context projection helpers with tool-result invariants
  - session resume path / recovery brief audit
  - memory quality rules and bounded recall tests
  - docs/status update
* Stage 12 sub-stage plan:
  - `12A Context Payload Foundation`: typed/bounded context payload protocol and tests
  - `12B Message Projection / Tool Result Invariants`: deterministic projection before LLM compaction
  - `12C Recovery Brief / Session Resume Audit`: harden session resume and evidence use
  - `12D Memory Quality Policy`: prevent low-value/derivable memory pollution
* Immediate implementation recommendation:
  - start with `Stage 12A: Context Payload Foundation`
* Stage 12 out of scope:
  - full auto-compact LLM summarization
  - coordinator/team runtime
  - mailbox/send-message
  - plugin marketplace
  - permission classifier / rich approval UI

## Decision (ADR-lite)

**Context**: The highlight roadmap includes many valuable upgrades, but later multi-agent, task, plugin, and automation features depend on context, session, memory, and recovery foundations.

**Decision**: Do not start advanced highlight implementation yet. Treat current infrastructure as partially ready, with a foundation gap around H04/H05/H06/H07. The next recommended stage is `Stage 12: Context and Recovery Hardening`, implemented iteratively as 12A-12D. Start with `Stage 12A: Context Payload Foundation`.

**Consequences**:
- H01/H02/H03/H08 should be preserved and hardened, not heavily redesigned.
- H04/H05 become the main infrastructure work because context projection and pressure handling affect most later systems.
- H06/H07 should be integrated into that foundation because recovery and memory quality influence long-running agent correctness.
- H09/H10/H11+ should wait until context/recovery boundaries are explicit enough to support them.
- 12A creates the shared dynamic context boundary that 12B/12C/12D can build on without ad hoc prompt injection.
