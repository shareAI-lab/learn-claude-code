# token budget tool output prune

## Goal

把普通 MicroCompact 的 count-based keep policy 升级为可选 token-budget protected policy：保留最近一段可压缩工具输出 token budget 内的结果，清理更旧的 eligible tool results，并复用前两个 sub-stage 的 bounded savings evidence。

## Expected Effect

当工具输出大小差异很大时，单纯保留最近 N 个结果并不稳定。token-budget policy 应让模型保留“最近约 N tokens 的工具输出上下文”，更接近 opencode `SessionCompaction.prune()` 的本地价值，同时保持当前 transcript 非破坏性。

## Requirements

- Add settings-backed optional `microcompact_protect_recent_tokens: int | None`.
- Add settings-backed `microcompact_min_prune_saved_tokens: int`.
- When `microcompact_protect_recent_tokens is None`, preserve existing count-based MicroCompact behavior.
- When configured, walk compactable successful tool results from newest to oldest:
  - keep recent compactable outputs while the protected token budget allows,
  - always keep at least one most-recent compactable tool result,
  - clear older eligible results outside the protected budget.
- Do not clear protected/ineligible semantic tools such as memory, task, plan, skill, verifier, subagent.
- Skip pruning when estimated savings are below `microcompact_min_prune_saved_tokens`.
- Preserve tool-call/tool-result pairing, ordering, `tool_call_id`, `status`, `artifact`, and persisted output path markers.
- Continue to emit bounded runtime event/evidence metadata from `MicrocompactStats`.

## Acceptance Criteria

- [ ] Default settings keep existing count-based behavior.
- [ ] Token-budget mode keeps recent compactable tool results under/around the protected budget.
- [ ] Token-budget mode always keeps at least one compactable result.
- [ ] Ineligible and error tool results are not rewritten.
- [ ] Savings threshold can skip low-value pruning without emitting an event.
- [ ] Persisted output paths remain model-visible after pruning.
- [ ] Runtime event/evidence uses bounded `tools_cleared`, `tools_kept`, `tokens_saved_estimate`, and `keep_recent`.
- [ ] `.trellis/spec/backend/runtime-pressure-contracts.md` is updated.
- [ ] Focused runtime pressure/app tests, ruff, and targeted mypy pass.

## Source Evidence

- `/root/claude-code-haha/src/services/compact/microCompact.ts`
- `sst/opencode` reference in source PRD remains planning evidence; local implementation must stay LangChain-native and deterministic.

## Out of Scope

- No provider exact tokenizer.
- No provider cache-edit/cache-reference payloads.
- No physical transcript deletion.
- No cc-style semantic SnipTool.

## Status

Checkpoint complete.

State: checkpoint

Verdict: APPROVE

Implemented:

- Added optional settings-backed `microcompact_protect_recent_tokens`.
- Added `microcompact_min_prune_saved_tokens`.
- Preserved default count-based MicroCompact behavior when token budget is not configured.
- Added token-budget suffix protection for ordinary MicroCompact.
- Kept at least one newest compactable tool result even when it exceeds budget.
- Added savings-threshold skip without event emission.
- Added bounded `protected_recent_tokens` runtime event/evidence metadata.
- Updated runtime pressure contracts.

Verification:

- `pytest -q tests/test_runtime_pressure.py` -> 30 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

Alignment:

- source files inspected:
  - `/root/claude-code-haha/src/services/compact/microCompact.ts`
  - `/root/claude-code-haha/src/services/compact/timeBasedMCConfig.ts`
- aligned:
  - compactable-tool allowlist via local `ToolCapability.microcompact_eligible`
  - newest-to-oldest protection policy
  - minimum-savings guard
- deferred:
  - exact opencode constants
  - provider exact tokenizer
  - persisted compacted marker/state
- do-not-copy:
  - provider cache editing
  - physical transcript deletion

Architecture:

- primitive used: existing deterministic live model-call projection helper.
- why no heavier abstraction: token-budget pruning is a policy variant inside
  the existing MicroCompact boundary.

Boundary findings:

- No session schema migration needed.
- No new tool/system prompt surface.
- Time-based MicroCompact remains first when its trigger fires.

Decision: continue

Reason:

- Stage 1 is complete and verified.
- Parent plan next stage remains valid: AutoCompact reliability can build on the
  same runtime pressure event/evidence seams without changing MicroCompact
  semantics further.
