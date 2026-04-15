# Frontend Development Guidelines

> Frontend guidance status for this repository.

---

## Current Status

The current working mainline is `coding-deepgent/`, which is a Python
LangChain/LangGraph product surface.

Frontend/web assets are reference-only by default unless a task explicitly
targets them. Do not treat `web/` or tutorial UI code as the current product
implementation target.

This directory is retained as a placeholder for future frontend-mainline work.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | App, page, component, and hook organization | Deferred |
| [Component Guidelines](./component-guidelines.md) | Component patterns, props, and composition | Deferred |
| [Hook Guidelines](./hook-guidelines.md) | Custom hook naming, dependencies, and side effects | Deferred |
| [State Management](./state-management.md) | Local, shared, server, and derived state patterns | Deferred |
| [Type Safety](./type-safety.md) | TypeScript conventions and type organization | Deferred |
| [Quality Guidelines](./quality-guidelines.md) | Testing, accessibility, linting, and review expectations | Deferred |

---

## Reactivation Rule

Only fill these frontend specs when:

1. a task explicitly targets frontend/web product work, and
2. the target is no longer reference-only, and
3. the spec can be filled from actual code conventions rather than ideals.

---

## Language Convention

- Narrative prose may be written in **Simplified Chinese**.
- Keep commands, file paths, file names, task slugs, branch names, code identifiers, and JSON/YAML keys in **English**.
- Keep checklist keywords and structured status values in **English** when they are used for search, automation, or coordination.
- When introducing project-specific terms, prefer Chinese explanations with the original English term kept where precision matters.
