# Directory Structure

> Actual backend structure rules for the current `coding-deepgent` mainline.

---

## Scope

This document describes how backend/product code is organized under:

```text
coding-deepgent/src/coding_deepgent/
```

It is not a tutorial chapter map. Do not mirror `agents/`, `agents_deepagents/`,
or `docs/` structure into product code.

---

## Directory Layout

```text
coding-deepgent/src/coding_deepgent/
├── app.py                    # public app/runtime entry helpers
├── bootstrap.py              # startup validation + top-level build helpers
├── agent_loop_service.py     # app invocation orchestration
├── agent_runtime_service.py  # runtime payload/session state wiring
├── agent_service.py          # create_agent-facing assembly seam
├── config.py                 # typed settings
├── containers/               # dependency-injector composition only
├── runtime/                  # invocation, state, context, session payload seams
├── tool_system/              # capability registry, projection, guard middleware
├── tools/                    # builtin workspace-facing tools
├── filesystem/               # filesystem/domain-level helpers
├── prompting/                # layered prompt + dynamic context assembly
├── compact/                  # projection, summaries, runtime pressure, artifacts
├── rules/                    # project-level rules entrypoint and file loading
├── sessions/                 # transcript/evidence/resume/record stores
├── memory/                   # save/recall/policy/context integration
├── todo/                     # short-term planning contract
├── tasks/                    # durable task graph + plan artifacts
├── subagents/                # bounded run_subagent runtime
├── permissions/              # deterministic permission policy
├── hooks/                    # lifecycle/event hook seam
├── mcp/                      # MCP config/load/resource seams
├── plugins/                  # local plugin manifest schemas/registry/loader
└── renderers/                # terminal/rendering helpers
```

---

## Core Organization Rules

### 1. Domain package first

New behavior should land in the domain package that owns the product concept:

- session persistence or resume -> `sessions/`
- project-level persistent behavior rules -> `rules/`
- dynamic runtime state or invocation shaping -> `runtime/`
- tool exposure or tool guard behavior -> `tool_system/`
- task graph or plan artifacts -> `tasks/`
- model-facing context pressure behavior -> `compact/`

Do not add unrelated behavior to `app.py`, `cli.py`, or `bootstrap.py` just
because those files are easy to find.

### 2. Containers compose, domains decide

`containers/` exists for dependency-injector wiring only.

Rules:

- domain packages do not import `coding_deepgent.containers`
- `containers/*` does not own business rules
- container modules may assemble providers, but product decisions belong in the
  corresponding domain

### 3. Runtime is a real boundary

`runtime/` owns invocation-specific state and context seams.

Put code there when it is about:

- runtime state shape
- session payload wiring
- invocation context propagation
- LangGraph/LangChain runtime attachment points

Do not use `sessions/` as a generic place for any long-lived product state.

### 4. Sessions stay transcript/resume scoped

`sessions/` is for:

- JSONL transcript records
- evidence
- recovery brief rendering
- compact records
- resume loading/selection

It should not silently absorb:

- durable task graph ownership
- generic plugin state
- arbitrary runtime-only caches

### 5. Tool system stays generic

`tool_system/` owns cross-cutting capability mechanics:

- capability metadata
- projection into the model-visible tool surface
- permission/trust metadata
- guard middleware

It should not become a god module for task logic, session policy, or prompt
assembly.

### 6. LangChain-native adapters stay explicit

Keep LangChain/LangGraph-specific adapters in clearly named files or packages,
for example:

- `tools.py`
- `middleware.py`
- `state.py`
- `app.py`

Do not spread model/schema/prompt/runtime wiring across unrelated modules.
For implementation-specific rules, read
`langchain-native-guidelines.md`.

---

## Naming And Placement Conventions

- Keep package names noun-based and product-domain oriented:
  - `sessions`, `tasks`, `compact`, `memory`, `rules`
- Prefer small modules with one strong responsibility over giant mixed files.
- Put public exports in each domain `__init__.py` only when that improves the
  main product surface; do not re-export everything automatically.
- Tests should mirror domain responsibilities under `coding-deepgent/tests/`
  instead of reaching through app entrypoints for everything.

---

## Real Examples

- `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
  shows a cross-cutting runtime concern implemented as a domain seam rather
  than inside app wiring.
- `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  is the source of truth for transcript/evidence persistence.
- `coding-deepgent/src/coding_deepgent/tasks/tools.py`
  keeps durable task and plan artifact tool behavior in the `tasks` domain
  instead of scattering it across runtime/app modules.
- `coding-deepgent/src/coding_deepgent/containers/app.py`
  composes the runtime without owning product rules.

---

## Anti-Patterns

- importing `coding_deepgent.containers` from domain packages
- adding domain decisions directly into `app.py`, `cli.py`, or `bootstrap.py`
- treating tutorial directory structure as a template for product layout
- merging unrelated concepts into `sessions/` because they are "stateful"
- using `tool_system/` as a dumping ground for product logic
