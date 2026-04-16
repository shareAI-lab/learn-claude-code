# stable message ids for compression projection

## Goal

Add stable persisted message identifiers before implementing durable collapse projection replay, compression timeline, or cc-style selective snip records.

## Why This Split Exists

Stage 3 `collapse-projection-replay` needs deterministic references from collapse records back to raw transcript messages. The current session model has message indexes, but not stable `message_id` fields. Indexes are useful for existing compact tail math, but future UI/timeline/replay needs IDs that remain explicit in raw records.

## Requirements

- Add stable `message_id` to persisted session message records.
- Preserve existing `message_index` behavior for compatibility.
- Ensure resumed/loaded raw history can expose or derive message IDs without applying compression filters.
- Define how future collapse records reference covered messages or ranges.
- Keep raw transcript append-only.

## Acceptance Criteria

- [ ] New persisted message records include stable IDs.
- [ ] Existing sessions without IDs still load.
- [ ] Session tests cover ID roundtrip/backward compatibility.
- [ ] Runtime/session contracts are updated.
- [ ] Collapse record/projection work can reference message IDs without inventing ad hoc indexes.

## Status

Prerequisite split from `context-compression-staged-implementation-plan` Stage 3.
