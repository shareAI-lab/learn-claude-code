# Stage 23: Context Pressure And Session Continuity Closeout

## Goal

Close the highest-value remaining H05/H06 MVP gaps by auditing and tightening context pressure management, compact/projection behavior, session transcript continuity, and resume-facing session evidence seams.

## Function Summary

This stage should identify and implement the smallest concrete changes that make context pressure handling and session continuity count as MVP-complete for Approach A, without introducing automatic summarization middleware or a new persistence runtime.

## Expected Benefit

* Context-efficiency: compact/projection behavior remains deterministic and bounded.
* Recoverability: resume/session continuity behavior is easier to trust and audit.
* Testability: compact/session seams have clearer end-to-end regression coverage.

## Corresponding Highlights

* `H05 Progressive context pressure management`
* `H06 Session transcript, evidence, and resume`

## Corresponding Modules

* `coding_deepgent.compact`
* `coding_deepgent.sessions`
* `coding_deepgent.cli_service`
* `coding_deepgent.rendering`
* `coding_deepgent.runtime`

## Out Of Scope

* automatic summarization middleware
* new persistence backend
* background/session daemon
* remote transcript browser
* coordinator / mailbox / background runtime

## Acceptance Criteria

* [x] cc-haha source mapping for H05/H06 is recorded in this stage PRD.
* [x] local H05/H06 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H05/H06 become implemented or remain partial with an explicit minimal residual.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve context-efficiency, recoverability, and testability. The local runtime effect is: projection/compaction remains deterministic under pressure, and resumed session continuity remains stable across compact/evidence combinations.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Progressive context pressure gate | autocompact/compaction paths are gated by deterministic suppression and threshold rules | keep local projection/compact path predictable and regression-resistant | projection/compact contract tests and fallback safety | partial | Align deterministic contract now; defer richer auto-compact runtime |
| Session transcript / resume continuity | transcript + sidechain + resume chain must survive reload | keep local compact/evidence/resume ordering trustworthy | combined continuity regression and existing session-store contracts | partial | Align continuity now; defer evidence CLI surface |
| Richer remote/session runtime | upstream has broader hydration, sidechain, and remote resume machinery | useful later but not required for current MVP | none | defer | Keep out of Stage 23 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/commands/compact/compact.ts`
* `/root/claude-code-haha/src/services/compact/autoCompact.ts`
* `/root/claude-code-haha/src/services/compact/compact.ts`
* `/root/claude-code-haha/src/services/compact/microCompact.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
* `/root/claude-code-haha/src/services/compact/postCompactCleanup.ts`
* `/root/claude-code-haha/src/services/compact/prompt.ts`
* `/root/claude-code-haha/src/services/compact/apiMicrocompact.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`
* `/root/claude-code-haha/src/utils/sessionRestore.ts`
* `/root/claude-code-haha/src/utils/messages.ts`
* `/root/claude-code-haha/src/utils/sessionFileAccessHooks.ts`
* `/root/claude-code-haha/src/commands/resume/index.ts`

## Technical Approach

* Close H05 with regression coverage over the full projection chain:
  * plain same-role text merges
  * structured content does not merge
  * metadata blocks merging
  * truncation behavior remains stable
* Close H06 with a combined continuity regression proving that:
  * recovery brief appears once
  * compact boundary and summary survive in order
  * evidence provenance remains visible in the resume brief
  * resumed history does not duplicate the resume context message

## Checkpoint: Stage 23

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added an H05 projection regression covering mixed plain/structured/metadata message normalization behavior.
- Added an H06 combined continuity regression covering resume brief, compact boundary/summary order, evidence provenance, and no-duplication behavior in selected continuation history.

Corresponding highlights:
- `H05 Progressive context pressure management`
- `H06 Session transcript, evidence, and resume`

Corresponding modules:
- `coding_deepgent.compact.projection`
- `coding_deepgent.rendering`
- `coding_deepgent.sessions`
- `coding_deepgent.cli_service`

Tradeoff / complexity:
- Chosen: contract closeout through focused regression coverage.
- Deferred: richer auto-compact runtime, evidence CLI surface, remote/session hydration breadth.
- Why this complexity is worth it now: H05/H06 already had strong behavior; the MVP risk was regression at composition/reload boundaries, not missing large subsystems.

Verification:
- `pytest -q coding-deepgent/tests/test_rendering.py coding-deepgent/tests/test_message_projection.py coding-deepgent/tests/test_compact_artifacts.py coding-deepgent/tests/test_compact_budget.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py::test_selected_continuation_history_uses_loaded_compacted_history coding-deepgent/tests/test_cli.py::test_selected_continuation_history_preserves_resume_compact_and_evidence_without_duplication`
- `ruff check coding-deepgent/tests/test_rendering.py coding-deepgent/tests/test_cli.py`
- `mypy coding-deepgent/src/coding_deepgent/rendering.py coding-deepgent/src/coding_deepgent/compact/projection.py coding-deepgent/src/coding_deepgent/compact/artifacts.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/tests/test_rendering.py coding-deepgent/tests/test_cli.py`

Boundary findings:
- H05 is best treated as a deterministic projection/compact contract in the current MVP, not as a commitment to full upstream autocompact breadth.
- H06 is strong enough for MVP without adding an evidence inspection command; that remains an optional later enhancement under H19/H06.

Decision:
- continue

Reason:
- Stage 23 is complete and Stage 24 (H07 scoped memory closeout) remains the next direct milestone from the canonical dashboard.
