# OpenRouter Integration Plan (Implementation-Ready)

## 0) Workflow Progress Report

### Step 1 — README analysis ✅
- Reviewed architecture and loop invariants in `README.md`.
- Core invariant to preserve: **`messages -> model call -> if tool_use then execute tools -> append tool_result -> repeat`** (`README.md:53-80`).
- Repo is intentionally stage-progressive from s01 to s12 (`README.md:24-50`), so migration should be incremental.

### Step 2 — Stage docs + code analysis in strict s01 → s12 order ✅
- Read docs in strict order:
  - `docs/en/s01-the-agent-loop.md` ... `docs/en/s12-worktree-task-isolation.md`
- Mapped each to Python stage implementation:
  - `agents/s01_agent_loop.py` ... `agents/s12_worktree_task_isolation.py`
- Extracted Claude usage shape and exact call sites with line references (Appendix A).

### Step 3 — Design for Claude + OpenRouter pluggable providers ✅
- Proposed a provider abstraction with:
  - Common interface + normalized response types
  - Claude adapter
  - OpenRouter adapter
  - Provider factory + env switch
  - Retry/error taxonomy
  - Tool schema translation (Anthropic tools ↔ OpenRouter/OpenAI-style tools)

### Step 4 — Deliverable generation ✅
- This document is implementation-ready and saved to:
  - `outputs/open-router-implementation-plan.md`

---

## 1) Coverage Proof (All files analyzed, in order)

### Project-level
1. `README.md`
2. `.env.example`
3. `requirements.txt`

### Stage docs and mapped code (strict order)
1. `docs/en/s01-the-agent-loop.md` → `agents/s01_agent_loop.py`
2. `docs/en/s02-tool-use.md` → `agents/s02_tool_use.py`
3. `docs/en/s03-todo-write.md` → `agents/s03_todo_write.py`
4. `docs/en/s04-subagent.md` → `agents/s04_subagent.py`
5. `docs/en/s05-skill-loading.md` → `agents/s05_skill_loading.py`
6. `docs/en/s06-context-compact.md` → `agents/s06_context_compact.py`
7. `docs/en/s07-task-system.md` → `agents/s07_task_system.py`
8. `docs/en/s08-background-tasks.md` → `agents/s08_background_tasks.py`
9. `docs/en/s09-agent-teams.md` → `agents/s09_agent_teams.py`
10. `docs/en/s10-team-protocols.md` → `agents/s10_team_protocols.py`
11. `docs/en/s11-autonomous-agents.md` → `agents/s11_autonomous_agents.py`
12. `docs/en/s12-worktree-task-isolation.md` → `agents/s12_worktree_task_isolation.py`

### Naming mismatch note
- No functional mismatch found.
- Only naming style differs:
  - docs: hyphenated (`s03-todo-write.md`)
  - code: underscored (`s03_todo_write.py`)

---

## 2) Current Architecture and Claude Integration (Evidence-based)

## 2.1 Architecture summary
- The course keeps one stable loop and layers mechanisms around it (`README.md:53-80`):
  - tool expansion (s02), planning (s03), context isolation (s04), knowledge loading (s05), compaction (s06), persistent task graph (s07), background execution (s08), teams/protocols/autonomy (s09-s11), worktree isolation (s12).

## 2.2 Claude integration pattern (cross-stage)
Across s01-s12 code, the same provider pattern appears:
1. `from anthropic import Anthropic` (e.g., `agents/s01_agent_loop.py:29`)
2. `client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))` (e.g., `agents/s01_agent_loop.py:37`)
3. `response = client.messages.create(...)` (e.g., `agents/s01_agent_loop.py:69-72`)
4. `if response.stop_reason != "tool_use": return` (e.g., `agents/s01_agent_loop.py:76-77`)
5. Iterate `response.content` blocks with `if block.type == "tool_use"` (e.g., `agents/s01_agent_loop.py:80-81`)
6. Append tool results as:
   - `{"type":"tool_result","tool_use_id":block.id,"content":...}` (e.g., `agents/s01_agent_loop.py:85-87`)

This pattern is repeated in all stages (detailed line citations in Appendix A).

## 2.3 Why OpenRouter needs an adapter
- Stage logic is coupled to Anthropic response structure (`block.type`, `block.id`, `block.name`, `block.input`, text blocks with `.text`).
- Therefore safest design is:
  - **Normalize provider responses into Anthropic-like internal objects**
  - Keep stage loops unchanged except replacing direct SDK call with provider abstraction.

---

## 3) Per-Stage Architecture and Claude Usage Mapping

| Stage | Architecture (from doc + code) | Claude usage evidence |
|---|---|---|
| s01 | Minimal agent loop with one `bash` tool; stop on non-tool (`docs/en/s01-the-agent-loop.md:13-25`, `:66-93`) | import/client/call/stop/tool loop in `agents/s01_agent_loop.py:29`, `:37`, `:69-72`, `:76-77`, `:80-87` |
| s02 | Dispatch map pattern; loop unchanged; adds read/write/edit tools (`docs/en/s02-tool-use.md:15-28`, `:49-76`) | `agents/s02_tool_use.py:25`, `:34`, `:115-118`, `:120-121`, `:123-129` |
| s03 | Todo manager + nag reminder; same loop contract (`docs/en/s03-todo-write.md:13-31`, `:53-74`) | `agents/s03_todo_write.py:33`, `:42`, `:167-170`, `:172-173`, `:176-190` |
| s04 | Parent/child context isolation via subagent with fresh messages (`docs/en/s04-subagent.md:13-25`, `:43-72`) | child loop: `agents/s04_subagent.py:118-131`; parent loop: `:145-164`; import/client: `:29`, `:38` |
| s05 | Two-layer skill loading via `load_skill` tool result injection (`docs/en/s05-skill-loading.md:13-33`, `:72-85`) | `agents/s05_skill_loading.py:42`, `:51`, `:189-192`, `:194-206` |
| s06 | 3-layer compaction; includes separate summarize call (`docs/en/s06-context-compact.md:15-41`, `:63-100`) | summarize call: `agents/s06_context_compact.py:107-114`; main loop call: `:202-205`; stop/tool: `:207-224` |
| s07 | Persistent task graph (`blockedBy`, `blocks`) with task CRUD tools (`docs/en/s07-task-system.md:15-46`, `:49-103`) | `agents/s07_task_system.py:29`, `:38`, `:211-214`, `:216-217`, `:219-228` |
| s08 | Background manager + notification injection before LLM call (`docs/en/s08-background-tasks.md:13-29`, `:70-87`) | `agents/s08_background_tasks.py:33`, `:42`, `:197-200`, `:202-203`, `:205-214` |
| s09 | Persistent teammates + JSONL inboxes + threaded teammate loops (`docs/en/s09-agent-teams.md:15-34`, `:64-101`) | teammate call: `agents/s09_agent_teams.py:177-183`; lead call: `:356-362`; stop/tool loops: `:187-199`, `:364-380` |
| s10 | Request/response protocols (shutdown, plan approval) over same message bus (`docs/en/s10-team-protocols.md:19-39`, `:43-82`) | teammate call: `agents/s10_team_protocols.py:191-197`; lead call: `:437-443`; tool loops: `:201-215`, `:445-461` |
| s11 | Autonomous work/idle loop + auto-claim + identity re-injection (`docs/en/s11-autonomous-agents.md:18-44`, `:48-116`) | teammate call: `agents/s11_autonomous_agents.py:226-232`; lead call: `:521-527`; tool loops: `:237-255`, `:529-545` |
| s12 | Task/worktree binding + lifecycle events + isolated execution dirs (`docs/en/s12-worktree-task-isolation.md:15-33`, `:44-97`) | `agents/s12_worktree_task_isolation.py:39`, `:48`, `:730-736`, `:738-739`, `:743-757` |

---

## 4) Implementation-Ready Design for Pluggable LLM Providers

## 4.1 Goals
1. Support `claude` and `openrouter` under one internal contract.
2. Preserve current stage behavior and tool loop semantics.
3. Keep migration low-risk via staged refactor.

## 4.2 Proposed modules/classes

```text
agents/
  llm/
    __init__.py
    types.py
    provider.py
    factory.py
    errors.py
    retry.py
    tool_schema.py
    providers/
      anthropic_provider.py
      openrouter_provider.py
```

### `agents/llm/types.py`
- `NormalizedBlock`
  - `type: Literal["text","tool_use"]`
  - `id, name, input, text`
- `NormalizedResponse`
  - `content: list[NormalizedBlock]`
  - `stop_reason: str | None`
  - `raw: Any`

### `agents/llm/provider.py`
- Protocol:
  - `create_message(model, system, messages, tools, max_tokens, temperature=None, stream=False) -> NormalizedResponse`

### `agents/llm/providers/anthropic_provider.py`
- Wrap current anthropic SDK call.
- Convert SDK content blocks to normalized blocks.
- Preserve current stop reason semantics.

### `agents/llm/providers/openrouter_provider.py`
- Use OpenRouter endpoint/client.
- Convert outgoing tools using `tool_schema.py`.
- Map incoming tool calls + text to normalized blocks.
- Map finish reasons:
  - tool calls present => `stop_reason="tool_use"`
  - otherwise `stop_reason="end_turn"` (or mapped finish reason).

### `agents/llm/factory.py`
- `create_provider_from_env()` returns adapter by `LLM_PROVIDER`.

### `agents/llm/retry.py`
- Exponential backoff with jitter for transient errors only.

### `agents/llm/errors.py`
- `LLMProviderError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMTimeoutError`, `LLMValidationError`

### `agents/llm/tool_schema.py`
- `anthropic_tool_to_openrouter_tool(tool: dict) -> dict`
- argument parsing/validation helpers

---

## 4.3 Config switch and compatibility

### Proposed env vars (add/update `.env.example`)
- `LLM_PROVIDER=claude`  (`claude` default, `openrouter` optional)
- `MODEL_ID=...` (keep existing)
- `ANTHROPIC_API_KEY=...` (existing)
- `ANTHROPIC_BASE_URL=...` (existing, keep for compatibility)
- `OPENROUTER_API_KEY=...`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `OPENROUTER_HTTP_REFERER=...` (optional)
- `OPENROUTER_X_TITLE=...` (optional)
- `LLM_MAX_RETRIES=3`
- `LLM_RETRY_BASE_DELAY_MS=500`
- `LLM_TIMEOUT_SECONDS=120`

### Backward compatibility policy
1. If `LLM_PROVIDER` is unset, default to Claude behavior.
2. Keep `ANTHROPIC_BASE_URL` behavior unchanged for existing users (`.env.example:8-10`, `:12-25`).
3. Keep `MODEL_ID` env key unchanged to avoid stage script breakage.

---

## 4.4 Factory wiring pattern

```python
# agents/llm/factory.py
def create_provider_from_env() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "claude").lower()
    if provider == "claude":
        return AnthropicProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )
    if provider == "openrouter":
        return OpenRouterProvider(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            http_referer=os.getenv("OPENROUTER_HTTP_REFERER"),
            x_title=os.getenv("OPENROUTER_X_TITLE"),
        )
    raise ValueError(f"Unsupported LLM_PROVIDER={provider}")
```

---

## 4.5 Retry/error handling strategy

### Retryable
- network timeout / connection reset
- HTTP 429
- HTTP 5xx

### Non-retryable
- 400 invalid schema/request
- 401/403 auth
- model-not-found

### Behavior
- backoff: `base_delay * 2^attempt + jitter`
- fail with typed exceptions from `errors.py`
- log provider/model/attempt/latency/stop_reason (no secrets)

---

## 4.6 Streaming compatibility

- Current stages are synchronous request/response (non-streaming).
- Implement `stream` argument in provider interface now but keep default `False`.
- Phase 1 acceptance: streaming not required for parity.
- Later: add stream event normalization to same `NormalizedBlock` shape.

---

## 4.7 Tool-use compatibility design

Because stages rely on Anthropic-style tool blocks:
- Keep Anthropic-style internal shape as canonical.
- For OpenRouter:
  1. Convert tool schemas to OpenRouter/OpenAI function format.
  2. Parse tool calls (JSON args) back into normalized `tool_use` blocks.
  3. Preserve `tool_use_id` correlation in normalized block `id`.

Edge behavior:
- Invalid JSON args => return safe tool-result error string (do not crash loop).
- Missing tool name/id => raise `LLMValidationError`.

---

## 4.8 OpenRouter SDK-style API/config guidance (concrete)

To align with common OpenRouter Python usage patterns (OpenAI-compatible client style), implement `OpenRouterProvider` with:

1. **Client initialization**
   - `base_url="https://openrouter.ai/api/v1"` (configurable via `OPENROUTER_BASE_URL`)
   - API key from `OPENROUTER_API_KEY`
   - Optional headers:
     - `HTTP-Referer` from `OPENROUTER_HTTP_REFERER`
     - `X-Title` from `OPENROUTER_X_TITLE`

2. **Model naming**
   - Keep model configurable through existing `MODEL_ID`
   - Accept OpenRouter-style model IDs (e.g., `anthropic/claude-3.7-sonnet`, `openai/gpt-4.1`)

3. **Chat completion/tool-call shape**
   - Send tools using OpenAI/OpenRouter function tool schema:
     - `{"type":"function","function":{"name":..., "description":..., "parameters":...}}`
   - Parse returned `tool_calls[*].id`, `tool_calls[*].function.name`, `tool_calls[*].function.arguments`
   - Convert to normalized internal `tool_use` blocks

4. **Dependency choices**
   - Preferred minimal path: rely on OpenAI-compatible client already in ecosystem (`openai` package) for OpenRouter calls
   - Alternative: dedicated OpenRouter SDK if team prefers stricter vendor coupling
   - Add explicit dependency decision to `requirements.txt` and document rationale

This keeps provider code aligned with real OpenRouter API conventions while preserving Anthropic-like internal stage contracts.

---

## 5) Stage-by-Stage Refactor Plan (s01..s12)

> Rule: keep stage business logic unchanged; only replace direct SDK calls with provider calls.

### Common migration action for every stage
1. Replace:
   - `from anthropic import Anthropic`
   - `client = Anthropic(...)`
2. Add:
   - `from agents.llm.factory import create_provider_from_env`
   - `provider = create_provider_from_env()`
3. Replace `client.messages.create(...)` with `provider.create_message(...)`
4. Continue using existing loop checks (`stop_reason`, `tool_use`, `tool_result`) against normalized response.

### Stage-specific notes
- **s04**: migrate both parent and subagent loops.
- **s06**: migrate both main loop and `auto_compact()` summarization call.
- **s09/s10/s11**: decide provider lifecycle in threads:
  - safest: create provider per thread (avoid hidden SDK thread-safety issues).
- **s12**: no changes to TaskManager/WorktreeManager/EventBus; only model-call path.

---

## 5.1 Concrete Implementation Steps (with expected outcomes + test plan)

| Step | Scope | Expected outcome | Testing plan |
|---|---|---|---|
| 1 | Add provider abstraction modules (`agents/llm/*`) | New common interface, normalized response types, provider factory compile/import cleanly | Unit: import tests + type-shape tests in `tests/llm/test_types.py` |
| 2 | Implement `AnthropicProvider` adapter | Existing Claude behavior preserved via normalized output | Unit: golden mock of Anthropic response -> normalized blocks equality |
| 3 | Implement `OpenRouterProvider` adapter + tool schema conversion | OpenRouter responses map to same `tool_use`/`text` semantics | Unit: mocked OpenRouter tool-call and plain text responses; invalid tool-call negative tests |
| 4 | Add retry/error taxonomy (`errors.py`, `retry.py`) | Transient failures retried consistently; typed exceptions for terminal errors | Unit: 429/5xx retry success, 401 no-retry, timeout exception mapping |
| 5 | Add config/env wiring (`.env.example`, docs) | `LLM_PROVIDER` switch works; backward-compatible defaults maintained | Unit: factory behavior with env permutations; missing key validation tests |
| 6 | Migrate s01 | s01 runs with both providers without loop logic changes | Stage tests: Claude positive, OpenRouter positive, provider failure negative |
| 7 | Migrate s02-s03 | Tool dispatch + todo flows run identically cross-provider | Stage tests for each: positive Claude/OpenRouter + malformed tool args negative |
| 8 | Migrate s04 | Parent/subagent both use same provider contract | Stage tests: child/parent interaction for both providers + child provider failure isolation |
| 9 | Migrate s05-s06 | Skill loading and compaction summary call are provider-agnostic | Stage tests: skill `tool_result` injection parity + s06 summarize-call cross-provider |
| 10 | Migrate s07-s08 | Task system/background notifications unaffected by provider swap | Stage tests: task graph mutation + background completion notice injection cross-provider |
| 11 | Migrate s09-s11 | Team protocols/autonomy stable under threaded execution | Stage tests: threaded teammate loops, protocol request-response, idle/auto-claim cross-provider |
| 12 | Migrate s12 | Worktree isolation workflow remains unchanged except LLM adapter call path | Stage tests: task/worktree lifecycle + tool-use roundtrip with mocked providers |
| 13 | Regression + compatibility sweep | No behavior regressions when `LLM_PROVIDER` unset (`claude` default) | Integration smoke: run s01/s06/s12 demo flows in both provider modes |
| 14 | CI/docs hardening | Actionable docs + reliable test automation | CI: matrix on `LLM_PROVIDER` with mocked network tests; optional gated live test job |

---

## 6) Unit Testing Plan (Positive, Negative, Cross-Provider)

## 6.1 Test setup
- Add `pytest` (+ `pytest-mock`) to test dependencies.
- Keep unit tests mostly mocked for deterministic CI.

## 6.2 Provider-layer tests (`tests/llm/`)
- `test_factory_default_returns_anthropic_provider`
- `test_factory_openrouter_returns_openrouter_provider`
- `test_factory_invalid_provider_raises_value_error`
- `test_anthropic_provider_normalizes_tool_use_block`
- `test_openrouter_provider_normalizes_tool_call_to_tool_use`
- `test_openrouter_provider_maps_finish_reason_to_stop_reason`
- `test_retry_retries_on_429_then_succeeds`
- `test_retry_does_not_retry_on_401`
- `test_timeout_raises_llm_timeout_error`
- `test_tool_schema_conversion_anthropic_to_openrouter_success`
- `test_tool_schema_conversion_invalid_schema_raises_validation_error`

## 6.3 Per-stage tests (`tests/agents/`)

For each stage `s01..s12`, create **three tests minimum**:
1. Claude positive path
2. OpenRouter positive path
3. Negative/error path

Suggested naming pattern (example s01):
- `test_s01_tool_loop_claude_provider`
- `test_s01_tool_loop_openrouter_provider`
- `test_s01_provider_error_is_handled`

Repeat same naming template for `s02`...`s12`.

### Special mandatory tests
- `test_s04_subagent_parent_and_child_use_same_provider_contract`
- `test_s06_auto_compact_summary_call_works_cross_provider`
- `test_s09_threaded_teammate_loop_openrouter`
- `test_s10_protocol_request_id_roundtrip_openrouter`
- `test_s11_idle_poll_and_auto_claim_cross_provider`
- `test_s12_worktree_task_flow_openrouter_provider_mock`

## 6.4 Cross-provider normalization fixtures
- `tests/fixtures/anthropic_tool_use.json`
- `tests/fixtures/openrouter_tool_call.json`

Test:
- `test_cross_provider_fixture_normalization_equivalence`

---

## 6.5 Per-stage detailed test matrix (s01-s12)

- **s01_agent_loop**
  - Positive-Claude: single tool call then final text.
  - Positive-OpenRouter: equivalent tool call normalized to `tool_use`.
  - Negative: invalid provider config or LLM timeout surfaces typed error.
- **s02_tool_use**
  - Positive-Claude: dispatch map calls expected tool and appends `tool_result`.
  - Positive-OpenRouter: same dispatch behavior via normalized tool call.
  - Negative: unknown tool name returns safe error content (loop continues).
- **s03_todo_write**
  - Positive-Claude: todo CRUD + nag reminder message behavior.
  - Positive-OpenRouter: same todo update sequence.
  - Negative: malformed todo payload/tool args handled without crash.
- **s04_subagent**
  - Positive-Claude: parent delegates, child executes with isolated context.
  - Positive-OpenRouter: same delegation/return behavior.
  - Negative: child provider failure returns error to parent without corrupting parent loop.
- **s05_skill_loading**
  - Positive-Claude: `load_skill` injects skill content into conversation.
  - Positive-OpenRouter: identical injection and follow-up behavior.
  - Negative: missing skill path returns recoverable tool-result error.
- **s06_context_compact**
  - Positive-Claude: compaction triggers summary call and resumes task loop.
  - Positive-OpenRouter: summary + main calls both work through provider abstraction.
  - Negative: summarize call failure triggers fallback/error path without data loss.
- **s07_task_system**
  - Positive-Claude: `blockedBy/blocks` updates and task transitions.
  - Positive-OpenRouter: same graph updates.
  - Negative: invalid task reference/tool input yields validation error string.
- **s08_background_tasks**
  - Positive-Claude: background task completion notification injected before model call.
  - Positive-OpenRouter: same notification semantics.
  - Negative: background tool exception captured and reported safely.
- **s09_agent_teams**
  - Positive-Claude: lead + teammate loops exchange messages correctly.
  - Positive-OpenRouter: same inbox/outbox behavior in threaded mode.
  - Negative: teammate LLM error isolated; other teammates continue.
- **s10_team_protocols**
  - Positive-Claude: shutdown/approval protocol request-response with request IDs.
  - Positive-OpenRouter: same protocol flow and correlation IDs.
  - Negative: malformed protocol message rejected and logged.
- **s11_autonomous_agents**
  - Positive-Claude: idle poll -> claim work -> continue loop.
  - Positive-OpenRouter: equivalent autonomous behavior.
  - Negative: claim race/conflict handled deterministically without deadlock.
- **s12_worktree_task_isolation**
  - Positive-Claude: task-worktree binding lifecycle and isolated execution.
  - Positive-OpenRouter: same lifecycle invariants.
  - Negative: worktree/provisioning failure produces recoverable task error state.

---

## 7) Trade-offs and Decisions

1. **Adapter normalization vs stage-level branching**
   - Decision: normalization adapter.
   - Why: avoids duplicating provider-specific logic in 12 stage files.

2. **Big-bang migration vs staged rollout**
   - Decision: staged rollout.
   - Why: stage-based repo architecture naturally supports incremental validation.

3. **OpenRouter via Anthropic-compatible mode vs explicit adapter**
   - Decision: explicit OpenRouter adapter (recommended), while keeping Anthropic base URL compatibility.
   - Why: clearer tool-call handling + better testability and long-term maintainability.

4. **Streaming now vs later**
   - Decision: interface now, runtime behavior later.
   - Why: current loops are sync; parity can ship without stream rewrite.

---

## 8) Staged Rollout Plan

### Phase 1 — Provider infrastructure
- Add `agents/llm/*` modules and provider tests.
- No stage file changes yet.

### Phase 2 — Early stage migration
- Migrate s01-s03.
- Validate parity quickly on simplest loops.

### Phase 3 — Mid-stage migration
- Migrate s04-s08.
- Validate subagent + compaction + background behaviors.

### Phase 4 — Advanced stage migration
- Migrate s09-s12.
- Focus on thread behavior and long-lived flows.

### Phase 5 — Docs and CI
- Update README/.env docs.
- Add Python test workflow if missing.

---

## 9) Acceptance Criteria

1. `LLM_PROVIDER=claude` reproduces existing behavior across s01-s12.
2. `LLM_PROVIDER=openrouter` runs all stages without changing stage business logic.
3. Tool-use semantics preserved:
   - `stop_reason` handling equivalent
   - `tool_use_id` correlation preserved
   - unknown/malformed tool calls handled gracefully
4. Retry/error behavior deterministic and tested.
5. Threaded stages (s09-s11) pass cross-provider tests.
6. s06 summarization and s12 orchestration pass cross-provider tests.

---

## 10) Missing Critical Information + Clarifying Questions

### Missing info
1. Preferred OpenRouter integration mode:
   - Anthropic-compatible path vs explicit OpenRouter API/tool-calls mode?
2. Required OpenRouter model allowlist (single default vs configurable list)?
3. Is real streaming required in this milestone or interface-only?
4. Dependency policy:
   - okay to add OpenRouter SDK/OpenAI-compatible client, or keep minimal deps?
5. CI expectation:
   - should Python tests be added to GitHub Actions now?
6. OpenRouter SDK skill reference availability:
   - I did not find an in-repo `skills/openrouter-python-sdk` directory in this repository snapshot.
   - How to obtain: provide the intended skill doc path/content, or confirm the preferred canonical source (OpenRouter docs + openrouter/openai Python client examples) to lock request/response mappings.

### Clarifying questions
1. Should `agents/s_full.py` be included in migration scope now, or only s01-s12?
2. For s09-s11, do you prefer one provider instance per thread (safer) or shared singleton?
3. Is semantic parity sufficient, or do you require exact text parity between providers?
4. Do you want Anthropic-compatible fallback retained indefinitely or marked deprecated?

---

## Appendix A — Claude Usage Line References (Code)

- `agents/s01_agent_loop.py`: `29`, `37`, `69-72`, `76-77`, `80-87`
- `agents/s02_tool_use.py`: `25`, `34`, `115-118`, `120-121`, `123-129`
- `agents/s03_todo_write.py`: `33`, `42`, `167-170`, `172-173`, `176-190`
- `agents/s04_subagent.py`:
  - child: `118-131`
  - parent: `145-164`
  - import/client: `29`, `38`
- `agents/s05_skill_loading.py`: `42`, `51`, `189-192`, `194-195`, `197-206`
- `agents/s06_context_compact.py`:
  - summarize call: `107-114`
  - main call: `202-205`
  - stop/tool: `207-224`
- `agents/s07_task_system.py`: `29`, `38`, `211-214`, `216-217`, `219-228`
- `agents/s08_background_tasks.py`: `33`, `42`, `197-200`, `202-203`, `205-214`
- `agents/s09_agent_teams.py`:
  - teammate call/loop: `177-199`
  - lead call/loop: `356-380`
- `agents/s10_team_protocols.py`:
  - teammate call/loop: `191-215`
  - lead call/loop: `437-461`
- `agents/s11_autonomous_agents.py`:
  - teammate call/loop: `226-255`
  - lead call/loop: `521-545`
- `agents/s12_worktree_task_isolation.py`: `39`, `48`, `730-736`, `738-739`, `743-757`

## Appendix B — Documentation Evidence References

- `README.md:24-50`, `53-80`, `150-160`
- `docs/en/s01-the-agent-loop.md:13-25`, `34-49`, `53-64`, `66-93`
- `docs/en/s02-tool-use.md:15-28`, `49-59`, `61-74`
- `docs/en/s03-todo-write.md:13-31`, `35-51`, `53-74`
- `docs/en/s04-subagent.md:13-25`, `29-41`, `43-72`
- `docs/en/s05-skill-loading.md:13-33`, `46-70`, `72-85`
- `docs/en/s06-context-compact.md:15-41`, `45-61`, `63-84`, `90-100`
- `docs/en/s07-task-system.md:15-46`, `49-76`, `91-103`
- `docs/en/s08-background-tasks.md:13-29`, `33-41`, `43-53`, `55-68`, `70-87`
- `docs/en/s09-agent-teams.md:15-34`, `38-48`, `50-62`, `64-101`
- `docs/en/s10-team-protocols.md:19-39`, `43-54`, `56-67`, `68-82`
- `docs/en/s11-autonomous-agents.md:18-44`, `48-70`, `72-91`, `93-116`
- `docs/en/s12-worktree-task-isolation.md:15-33`, `35-62`, `63-81`, `83-97`
