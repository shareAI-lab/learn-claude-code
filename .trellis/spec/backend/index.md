# Backend Development Guidelines

> Canonical backend norms for the current `coding-deepgent` mainline.

---

## Current Scope

- Current working mainline: `coding-deepgent/`
- Canonical coordination layer: `.trellis/`
- Default non-mainline reference layer:
  - `agents/`
  - `agents_deepagents/`
  - `docs/`
  - `web/`

Use tutorial/reference material as evidence or examples only unless a task
explicitly targets it.

---

## Canonical Reading Order

Before changing backend code in the current mainline, read in this order:

1. `AGENTS.md`
2. `.trellis/workflow.md`
3. `.trellis/project-handoff.md`
4. `.trellis/spec/guides/mainline-scope-guide.md`
5. This index
6. The specific backend docs relevant to the task

Product-level status summaries may still exist in `coding-deepgent/README.md`
and `coding-deepgent/PROJECT_PROGRESS.md`, but live development norms and
contracts should be captured here in Trellis.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Actual `coding-deepgent` module layout and boundary rules | Active |
| [Database Guidelines](./database-guidelines.md) | Current persistence guidance; no SQL/ORM in mainline yet | Active |
| [Error Handling](./error-handling.md) | Mixed-but-strict error boundary conventions | Active |
| [LangChain-Native Implementation Guidelines](./langchain-native-guidelines.md) | Strict tool/schema/middleware/state rules for LangChain/LangGraph work | Active |
| [Quality Guidelines](./quality-guidelines.md) | Mainline code-review, testing, and boundary rules | Active |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging and evidence-vs-log boundary | Active |
| [Runtime Context And Compaction Contracts](./runtime-context-compaction-contracts.md) | Overview index for runtime/compact contract files | Active |
| [Project Infrastructure Foundation Contracts](./project-infrastructure-foundation-contracts.md) | Project-level review gate for transcript/session/compact/collapse/runtime pressure/task/subagent/hooks/memory | Active |
| [Tool Capability Contracts](./tool-capability-contracts.md) | H01 five-factor tool protocol, safe defaults, capability metadata, and tool projection rules | Active |
| [Tool Result Storage Contracts](./tool-result-storage-contracts.md) | Executable contracts for large-output persistence and preview references | Active |
| [Session Compact Contracts](./session-compact-contracts.md) | Executable contracts for resume, compact records, session memory, and memory quality | Active |
| [Runtime Pressure Contracts](./runtime-pressure-contracts.md) | Executable contracts for live microcompact, auto/reactive compact, restoration, and runtime pressure evidence | Active |
| [Task Workflow Contracts](./task-workflow-contracts.md) | Executable contracts for durable task graph readiness, transitions, and verification boundary | Active |

---

## Current High-Signal Docs

For most current `coding-deepgent` work, the high-signal Trellis docs are:

- [Directory Structure](./directory-structure.md)
- [LangChain-Native Implementation Guidelines](./langchain-native-guidelines.md)
- [Quality Guidelines](./quality-guidelines.md)
- [Runtime Context And Compaction Contracts](./runtime-context-compaction-contracts.md)
- [Project Infrastructure Foundation Contracts](./project-infrastructure-foundation-contracts.md)
- [Tool Capability Contracts](./tool-capability-contracts.md)
- [Tool Result Storage Contracts](./tool-result-storage-contracts.md)
- [Session Compact Contracts](./session-compact-contracts.md)
- [Runtime Pressure Contracts](./runtime-pressure-contracts.md)
- [Task Workflow Contracts](./task-workflow-contracts.md)

If a task changes runtime/session/compact/task boundaries, these Trellis docs
should be updated rather than creating or reviving parallel docs under
`coding-deepgent/docs/`.

---

## Language Convention

- Narrative prose may be written in **Simplified Chinese**.
- Keep commands, file paths, file names, task slugs, branch names, code identifiers, and JSON/YAML keys in **English**.
- Keep checklist keywords and structured status values in **English** when they are used for search, automation, or coordination.
- When introducing project-specific terms, prefer Chinese explanations with the original English term kept where precision matters.
