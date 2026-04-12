# Session foundation cc-haha alignment note

## Expected effect

Aligning this behavior should improve reliability and product parity. The local
effect is a small, testable session substrate: transcript records, same-workdir
listing, resume-ready state snapshots, and a direct LangGraph `thread_id`
mapping without pulling in cc-haha's broader resume UI or sidechain runtime.

## Reference points inspected

- `/root/claude-code-haha/src/types/logs.ts`
- `/root/claude-code-haha/src/utils/sessionStorage.ts`
- `/root/claude-code-haha/src/commands/resume/resume.tsx`
- `/root/claude-code-haha/src/tools/AgentTool/resumeAgent.ts`
- `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`

## Alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Transcript identity | Serialized messages carry `cwd`, `sessionId`, `timestamp`, `version` | Stable local transcript records and deterministic lookup | `coding_deepgent.sessions.records` / `store_jsonl` | align | Keep the core identity fields in JSONL records |
| Same-workdir resume filter | Resume starts from same-repo/session-filtered logs | Avoid cross-workdir leakage in product resume/listing | `JsonlSessionStore.list_sessions()` | align | Filter by resolved workdir and ignore unrelated transcripts |
| LangGraph thread binding | Resume path depends on stable session identity | Future runtime wiring can map session id to `thread_id` directly | `coding_deepgent.sessions.langgraph` | partial | Provide the mapping helper now; full runtime injection is separate work |
| State restore | cc-haha resume reconstructs richer runtime state from logs | Product resume keeps TodoWrite state instead of replaying messages only | `state_snapshot` handling in `store_jsonl` / `resume` | align | Last valid same-session snapshot wins; missing snapshots fall back to default state |
| Lite/full logs, sidechains, cross-project flows | cc-haha supports richer resume UX and storage variants | Avoid speculative complexity before product runtime and CLI slices land | not implemented in this task | defer | Keep the domain transcript/resume-only for now |
| SessionMemory and subagent resume | cc-haha layers later memory/subagent behavior on top of session logs | Preserve boundaries so sessions do not become memory/task/subagent storage | not implemented in this task | defer | Revisit only after those product stages exist |

## What aligned now

- Versioned JSONL `message` and `state_snapshot` records.
- Same-workdir session lookup.
- Resume-ready state restoration helper.
- Session id to LangGraph `thread_id` mapping helper.

## Intentionally not copied yet

- Cross-project resume flows.
- Lite/full transcript variants.
- Sidechain/subagent transcript grouping.
- SessionMemory extraction and richer resume reconstruction.
