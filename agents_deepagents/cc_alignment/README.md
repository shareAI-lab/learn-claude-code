# CC Alignment Progress Documents

Every implemented `agents_deepagents/sNN_*.py` chapter must have a matching CC
alignment progress document in this directory.

## Project rule

For each `sNN` chapter, maintain one document named:

```text
agents_deepagents/cc_alignment/sNN-<topic>.md
```

The document must explicitly list:

1. **Chapter scope** — what this `sNN` is responsible for in the LangChain / Deep Agents track.
2. **CC / cc-haha reference points** — source files, docs, or observed behavior used as the alignment target.
3. **Aligned** — behavior or structure we intentionally match.
4. **Partially aligned / teaching equivalent** — behavior we model in a smaller LangChain-native way.
5. **Not aligned / intentionally not copied** — production details we do not implement yet, with reasons.
6. **Tests / evidence** — deterministic verification proving the current state.
7. **Next alignment candidates** — what should be considered in a later product-stage or chapter pass.

If a chapter has no meaningful CC equivalent yet, the document should still exist
and say so explicitly rather than leaving alignment status implicit.

## Current documents

| Chapter | Document | Status |
|---|---|---|
| s06 Context Compact | [`s06-context-compact.md`](./s06-context-compact.md) | Teaching-level structural parity with explicit production gaps |

## Template

```md
# sNN: <Title> — CC Alignment Progress

## Scope

## CC reference points

## Aligned

## Partially aligned / teaching equivalent

## Not aligned / intentionally not copied

## Tests / evidence

## Next alignment candidates
```
