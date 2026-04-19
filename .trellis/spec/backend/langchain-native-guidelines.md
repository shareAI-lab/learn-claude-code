# LangChain-Native Implementation Guidelines

> Practical structure and schema rules for `coding-deepgent` LangChain/LangGraph work.

---

## Scope

Use this document when a task touches:

- LangChain
- LangGraph
- middleware
- tool schemas
- prompt assembly
- runtime state
- model integration seams

This is the canonical Trellis guidance for LangChain/LangGraph implementation
shape.

---

## Operating Posture

- Prefer the smallest official LangChain/LangGraph abstraction that solves the problem.
- Keep code simple before modularizing.
- Do not add wrapper layers, fallback parsers, or framework-shaped indirection without a real boundary.
- If multiple surfaces are involved, keep tool, middleware, state, prompt, and rendering responsibilities separate.
- For project infrastructure changes, prove the mutation belongs to one of the
  official runtime surfaces: tool, middleware, typed state, context schema,
  checkpointer, store, or graph/subgraph. If it does not, document the explicit
  non-LangChain boundary before implementing.

Before editing, identify:

1. **Surface**
2. **Primary boundary**
3. **Smallest viable change**
4. **Durability boundary** for any session, memory, task, or transcript change

---

## Tool Schema Rules

- Use Pydantic `BaseModel` with strict schemas for structured tool input.
- Prefer `ConfigDict(extra="forbid")` unless loose input is explicitly required.
- Put model-visible guidance in `Field(description=...)` and the tool description.
- Put invariants in validators, not in ad hoc parsing helpers.
- Do not parse raw `dict[str, Any]` as fallback for model mistakes.
- Do not accept alias guessing such as `task -> content`, `done -> completed`,
  or `doing -> in_progress` unless explicitly requested.
- Avoid `normalize_*` helpers for structured tool input when schema validation
  can express the rule directly.

Preferred outcome:

- strict schema
- direct field access
- predictable `Command(update=...)` or typed return value
- matching `ToolCapability` metadata for the five-factor tool protocol:
  `name`, `schema`, `permission`, `execution`, and `rendering_result`

For tool capability ownership, safe defaults, exposure projection, large-output
eligibility, and runtime-pressure metadata, read
[Tool Capability Contracts](./tool-capability-contracts.md).

---

## State Rules

- Define explicit typed state for custom short-term state.
- Keep one default-state factory when app/session code owns initialization.
- Use middleware backfill only as defensive, idempotent state setup.
- Use reducers or explicit rejection when parallel tool calls can race on the
  same state key.
- Do not introduce persistence/store/task graph just for ephemeral session state.
- Do not use a generic "session state" dictionary to mix transcript facts,
  evidence, durable tasks, long-term memory, and live projection artifacts. Use
  the owning surface for each concern.

---

## Middleware Rules

- Middleware is for cross-cutting behavior:
  - validation
  - routing
  - guards
  - logging
  - usage tracking
  - state injection
- For HITL approval flows, prefer official LangGraph `interrupt()` plus
  `Command(resume=...)` with a checkpointer and stable `thread_id` instead of a
  custom waiting loop.
- Keep business-specific tool rules in tool schema/description, not middleware.
- Use `before_agent` / `after_agent` for once-per-invocation behavior.
- Use `wrap_model_call` / `wrap_tool_call` when logic must run around each call.
- Do not let middleware secretly own a feature that should be a tool, state
  schema, or prompt section.

---

## Prompt Placement Rules

System prompts should stay short and general:

- identity / role
- workspace / environment
- general tool-use behavior
- safety / honesty constraints

Tool-specific behavior belongs in:

- tool description
- field descriptions
- validators
- tests

Do not place a full tool manual in the system prompt unless it truly applies
globally.

---

## Modularity Rules

Extract modules only for real stable responsibilities, for example:

- `state.py` -> state schemas / default factories
- `tools/*.py` -> tool definitions and tool-local execution
- `middleware/*.py` -> middleware hooks
- `renderers/*.py` -> display formatting
- `app.py` -> agent wiring

Avoid:

- one-function modules
- speculative abstraction layers
- pass-through wrappers that only make code look architectural

Prefer local code until reuse or a boundary is real.

---

## Verification Rules

For LangChain tool/state changes, prove:

- the public tool name is correct
- `tool_call_schema.model_json_schema()` exposes only intended model-visible fields
- hidden injected fields are not model-visible
- invalid aliases / extra fields fail
- state update returns the expected shape
- middleware injects or guards only what it owns
- no stale public prompt/tool wording remains
- transcript/session/store mutations have an explicit durability boundary
- live projection middleware does not rewrite persisted session records

Useful review checks:

```bash
rg -n "dict\\[str, Any\\]|normalize_.*\\(|fallback|alias|ToolRuntime|InjectedToolCallId" <paths>
rg -n "system_prompt|SYSTEM_PROMPT|description=|Field\\(" <paths>
rg -n "record_type|message_index|thread_id|checkpointer|store|session_memory" <paths>
```

Treat matches as review prompts, not automatic failures.

---

## Relationship To Other Trellis Docs

- Use [Directory Structure](./directory-structure.md) for product-domain ownership.
- Use [Quality Guidelines](./quality-guidelines.md) for review/testing expectations.
- Use [Tool Capability Contracts](./tool-capability-contracts.md) for H01
  tool protocol and capability metadata.
- Use `guides/cc-alignment-guide.md` when the task also targets `cc-haha` alignment.
