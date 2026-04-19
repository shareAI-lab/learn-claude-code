# L4-c Findings: Result Persistence And Microcompact Eligibility Audit

Date: 2026-04-18
Task: `04-17-l4c-h01-result-persistence-microcompact-eligibility-audit`

## Scope

Reviewed current `ToolCapability` opt-ins for:

- `persist_large_output`
- `max_inline_result_chars`
- `microcompact_eligible`

Reviewed against:

- `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
- `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
- `coding-deepgent/src/coding_deepgent/compact/tool_results.py`
- `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
- `coding-deepgent/tests/tool_system/test_tool_result_storage.py`
- `coding-deepgent/tests/tool_system/test_tool_system_registry.py`

## Current Opt-In Set

Current tools with `persist_large_output=True`:

- `bash`
- `read_file`
- `glob`
- `grep`

Current tools with `microcompact_eligible=True`:

- `bash`
- `read_file`
- `glob`
- `grep`

No other tool currently opts in.

## Audit Conclusion

### 1. No invalid microcompact opt-ins found

All current `microcompact_eligible` tools also opt into large-output
persistence, which is required by the current local contract.

That means old outputs can be hidden while preserving a model-visible persisted
path for later recovery.

### 2. No invalid large-output persistence opt-ins found

All current `persist_large_output` tools return string-heavy outputs that can be
meaningfully rewritten as preview + persisted file path:

- `read_file`: directly recoverable by re-reading the file or opening persisted
  output
- `glob` / `grep`: search results are path/text listings and are safe to persist
- `bash`: command output may be non-repeatable, but persisted-output storage
  still preserves the full original output behind a stable workspace path, so
  recoverability is satisfied without replaying the command

### 3. No capability metadata changes required

The existing opt-in set already matches the current contract and tests.

Recommendation:

- keep the current capability metadata unchanged
- keep `L5-a` dormant
- rely on current registry tests plus tool-result storage tests as the proof
  surface

## Follow-Up Rule

Reopen this area only when a new tool wants either:

- `persist_large_output=True`, or
- `microcompact_eligible=True`

At that point, require explicit proof that:

1. large results can be rewritten into preview + persisted path safely
2. old output can be hidden without losing critical state
3. the tool still behaves correctly through runtime pressure and recovery paths
