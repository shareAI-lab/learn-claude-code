<!-- Created on 2026-04-14 after restoring removed OMX planning artifacts. -->
# Runtime Foundation Recovery Notes

Recovered artifacts:
- `.omx/plans/prd-coding-deepgent-runtime-foundation.md`
- `.omx/plans/test-spec-coding-deepgent-runtime-foundation.md`
- `.omx/context/coding-deepgent-runtime-foundation-20260412T213209Z.md`

Evidence sources:
- Direct session output from `/root/.codex/sessions/2026/04/13/...jsonl`
- `/root/.codex/history.jsonl`
- Session records showing the original `.omx/plans/` and `.omx/context/` paths existed before uninstall

Confidence:
- `test-spec-coding-deepgent-runtime-foundation.md`: high
  Reason: recovered from direct `sed` output of the original file in session logs.
- `coding-deepgent-runtime-foundation-20260412T213209Z.md`: high
  Reason: recovered from direct `sed` output of the original file in session logs.
- `prd-coding-deepgent-runtime-foundation.md`: medium-high
  Reason: reconstructed from multiple corroborating session fragments, including direct file reads and a logged heredoc write command, but not guaranteed byte-identical to the original final file.

Notable naming caveat:
- Earlier session logs show an older/narrower variant titled `# PRD — coding-deepgent Runtime Foundation`.
- The restored PRD uses the later professional-domain title:
  `# PRD — coding-deepgent Professional Domain Runtime Foundation`
- This appears to reflect a genuine same-day evolution of the plan rather than a contradiction.

Practical guidance:
- Treat the restored `test-spec` and `context` files as strong historical references.
- Treat the restored `PRD` as the best available working recovery for future planning/execution.
- If stricter provenance is needed later, use these files together with the referenced session logs.
