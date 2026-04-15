# Quality Guidelines

> Canonical code-review and quality rules for the `coding-deepgent` mainline.

---

## Scope

These rules apply to current product work in:

```text
coding-deepgent/
```

Tutorial/reference material is not the review baseline unless a task explicitly
targets it.

---

## Forbidden Patterns

### 1. Tutorial/runtime coupling

Do not introduce runtime or test dependencies on tutorial/reference layers:

- `agents/`
- `agents_deepagents/`
- `docs/`
- `web/`
- root `skills/`

Behavioral parity can be documented as reference knowledge, but product code
must not depend on those directories.

### 2. Business logic in composition shells

Do not hide product rules in:

- `containers/*`
- `app.py`
- `cli.py`
- `bootstrap.py`

These files may wire and expose behavior, but domain logic should live in the
owning package.

### 3. Boundary creep

Do not let these domains absorb unrelated responsibilities:

- `sessions/` -> transcript/resume/evidence only
- `tool_system/` -> capability/guard/projection only
- `containers/` -> composition only

If a change does not belong naturally to that domain, move it.

### 4. Runtime replacement drift

Do not bypass LangChain/LangGraph-native seams casually.

Avoid:

- ad hoc custom query loops
- hidden side executors that skip middleware/policy boundaries
- tutorial-shell stage mirroring as the public product surface

Use official `create_agent`, middleware, runtime context, and typed tool/schema
seams unless a task explicitly approves a stronger deviation.

### 5. Loose tool/schema fallbacks

Do not hide model or schema mistakes behind permissive parsing.

Avoid:

- raw `dict[str, Any]` fallback parsing for structured tools
- alias guessing such as `task -> content` or `doing -> in_progress`
- `normalize_*` helpers used only to compensate for weak public schemas

---

## Required Patterns

### 1. Keep the mainline explicit

- Treat `coding-deepgent/` as the implementation target.
- Treat `.trellis/` as the canonical norms/contracts layer.
- When norms change, update Trellis docs instead of creating new parallel
  product-local review/spec files.

### 2. Preserve product shape

The product should read as one cumulative app, not a parallel set of stage
entrypoints.

Required outcomes:

- one integrated product surface
- domain packages with clear ownership
- explicit runtime/middleware boundaries

### 3. Use bounded, typed contracts

Prefer:

- strict Pydantic schemas
- explicit JSON contracts
- bounded message/context payloads
- deterministic policy and middleware behavior

For LangChain/LangGraph implementation details, follow
[LangChain-Native Implementation Guidelines](./langchain-native-guidelines.md).

### 4. Keep review evidence focused

When a change affects a mainline contract, reviewers should be able to point to:

- the Trellis spec/plan that defines the boundary
- the implementation seam that enforces it
- the tests that prove it

---

## Testing Requirements

### Minimum expectation

For touched mainline files, run focused checks from `coding-deepgent/tests/`
plus relevant static checks.

Expected tools:

- `pytest` on affected product tests
- `ruff check` on touched files
- `mypy` on touched typed modules where applicable

### Test placement

- product tests belong under `coding-deepgent/tests/`
- tutorial/reference tests under root `tests/` should not be expanded as a
  substitute for product verification

### Preferred test style

- focused, deterministic, no-network
- assert boundary behavior, not only happy-path outputs
- add regression tests when changing contracts or middleware ordering

### Validation Scope Policy

Default to focused validation first.

Run:

- focused tests for the touched domain
- `ruff check` on touched Python files
- `mypy` on touched typed modules where relevant

Escalate to broader validation when:

- a cross-layer contract changes
- runtime/session/compact/task behavior changes
- middleware ordering changes
- focused tests fail in a way that suggests wider coupling
- the user explicitly asks for broader validation

Do not default to full-suite validation for every small change.

---

## Code Review Checklist

### Mainline scope

- [ ] The change serves `coding-deepgent`, not tutorial parity by default.
- [ ] No new dependency on `agents_deepagents` or other tutorial/reference code.

### Responsibility boundaries

- [ ] `containers/*` compose but do not own business rules.
- [ ] Domain logic lives in the owning package.
- [ ] `sessions/`, `tool_system/`, and `runtime/` boundaries remain coherent.

### Product shape

- [ ] The public surface still reads as one cumulative app.
- [ ] No new stage-mirror or tutorial-shaped main entrypoint was introduced.

### Contracts and invariants

- [ ] Cross-layer behavior changes are reflected in Trellis specs when needed.
- [ ] Structured payloads, bounded context behavior, and tool invariants remain valid.
- [ ] Task/plan/verifier/session boundaries are preserved when touched.
- [ ] LangChain tool/schema/middleware changes follow `langchain-native-guidelines.md`.

### Verification

- [ ] Focused product tests were updated or added.
- [ ] `ruff check` and `mypy` were run when relevant.
- [ ] Residual risks or deferred cleanup are stated explicitly.
