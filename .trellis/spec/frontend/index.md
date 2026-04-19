# Frontend Development Guidelines

> Frontend guidance status for this repository.

---

## Current Status

The current working mainline is `coding-deepgent/`.

Product frontend work is now active only for:

- `coding-deepgent/frontend/cli` — TypeScript React/Ink CLI frontend
- `coding-deepgent/src/coding_deepgent/frontend` — Python JSONL bridge/protocol backend

The root `web/` app remains tutorial/reference-only unless a task explicitly
promotes it to product Web work.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | CLI app, protocol, component, and bridge organization | Active |
| [Component Guidelines](./component-guidelines.md) | Component patterns, props, and composition | Active |
| [Hook Guidelines](./hook-guidelines.md) | Custom hook naming, dependencies, and side effects | Deferred |
| [State Management](./state-management.md) | Local event reducer and bridge-driven state patterns | Active |
| [Type Safety](./type-safety.md) | TypeScript protocol and UI state conventions | Active |
| [Quality Guidelines](./quality-guidelines.md) | Testing, typecheck, and review expectations | Active |

---

## Reactivation Rule

Only expand these frontend specs when:

1. a task explicitly targets frontend/web product work, and
2. the target is no longer reference-only, and
3. the spec can be filled from actual code conventions rather than ideals.

---

## Language Convention

- Narrative prose may be written in **Simplified Chinese**.
- Keep commands, file paths, file names, task slugs, branch names, code identifiers, and JSON/YAML keys in **English**.
- Keep checklist keywords and structured status values in **English** when they are used for search, automation, or coordination.
- When introducing project-specific terms, prefer Chinese explanations with the original English term kept where precision matters.
