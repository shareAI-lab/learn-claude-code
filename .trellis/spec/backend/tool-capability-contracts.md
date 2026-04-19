# Tool Capability Contracts

> Executable H01 contracts for the `coding-deepgent` tool capability protocol.

This document captures the cc-aligned "five-factor" tool protocol for the
current LangChain/LangGraph-native product mainline. It intentionally does not
copy the cc-haha TypeScript `Tool<Input, Output, Progress>` interface, React
rendering surface, or custom `StreamingToolExecutor`. The local contract is:
use LangChain tools for execution, and use `ToolCapability` plus middleware for
the harness semantics LangChain does not encode directly.

## Scenario: Five-Factor Tool Capability Protocol

### 1. Scope / Trigger

Read this document before changing:

- `coding_deepgent.tool_system`
- any domain `tools.py`
- tool `args_schema`
- tool permission/trust/exposure metadata
- tool output/result rendering behavior
- large-output persistence eligibility
- runtime-pressure/microcompact tool eligibility
- MCP/plugin/skill/subagent/task tool registration

This is an infra/cross-layer contract because model-visible schema, permission
policy, runtime execution, result projection, compact pressure, and tests must
agree for every tool.

### 2. Signatures

Canonical local capability surface:

```python
@dataclass(frozen=True)
class ToolCapability:
    name: str
    tool: BaseTool
    domain: str
    read_only: bool
    destructive: bool
    concurrency_safe: bool
    source: str
    trusted: bool
    family: str
    mutation: str
    execution: str
    exposure: str
    rendering_result: str
    enabled: bool = True
    tags: tuple[str, ...] = ()
    persist_large_output: bool = False
    max_inline_result_chars: int | None = None
    microcompact_eligible: bool = False

KNOWN_TOOL_EXPOSURES = frozenset({"main", "child_only", "extension", "deferred"})
TOOL_PROJECTION_EXPOSURES = {
    "main": ("main", "extension"),
    "child": ("child_only",),
    "extension": ("extension",),
    "deferred": ("deferred",),
}

@dataclass(frozen=True)
class ToolPoolProjection:
    name: str
    capabilities: tuple[ToolCapability, ...]

    def names(self) -> list[str]: ...
    def tools(self) -> list[BaseTool]: ...
    def metadata(self) -> dict[str, ToolCapability]: ...

class ToolSearchInput(BaseModel):
    query: str
    max_results: int = 5

def ToolSearch(query: str, runtime: ToolRuntime, max_results: int = 5) -> str: ...

class InvokeDeferredToolInput(BaseModel):
    tool_name: str
    arguments: dict[str, Any]

def invoke_deferred_tool(
    tool_name: str,
    arguments: dict[str, Any],
    runtime: ToolRuntime,
) -> ToolMessage | Command[Any]: ...
```

Required five-factor protocol for every registered tool:

```text
name
schema
permission
execution
rendering_result
```

Where:

- `name` is the model-visible and registry identity.
- `schema` is the strict Pydantic `args_schema` and any hidden injected runtime
  fields that must not appear in `tool_call_schema`.
- `permission` is the declared policy/trust surface:
  `read_only`, `destructive`, `source`, `trusted`, `domain`, `mutation`.
- `execution` is how the tool runs:
  `plain_tool`, `command_update`, `child_agent_bridge`, `local_loader`,
  adapter-backed MCP/plugin tool, or a documented future value.
- `rendering_result` is the result contract:
  `ToolMessage`, `Command(update=...)`, persisted-output preview,
  session evidence, CLI renderer, or other documented bounded result.

### 3. Contracts

#### Five-Factor Ownership

- Every model-facing tool must have one `ToolCapability` entry.
- The registry `name` must match the actual LangChain tool name.
- The tool schema must be strict and model-visible fields must be intentional.
- Hidden injected runtime fields such as `ToolRuntime` or injected tool-call IDs
  must not appear in model-visible schema.
- Registry construction must fail when a capability has a mismatched name,
  missing `args_schema` / `tool_call_schema`, blank/`unknown` required
  metadata, invalid exposure, or inconsistent large-output/microcompact opt-in.
- Permission metadata must describe the tool's real behavior, not the current
  permission mode.
- Execution metadata must describe the runtime boundary, not the business
  domain. For example:
  - `plain_tool`: returns a plain string/value or `ToolMessage`
  - `command_update`: returns `Command(update=...)`
  - `child_agent_bridge`: starts a bounded child-agent path
  - `local_loader`: loads local non-model code/data into the current run
- Rendering/result behavior must be bounded and testable. UI-specific React
  rendering from cc-haha is not a local product surface.

#### Safe Defaults

- New capability booleans must default to the conservative value.
- A tool is not `read_only` unless explicitly proven and tested.
- A tool is not `concurrency_safe` unless it is read-only or otherwise proven
  free of shared-state/race side effects.
- A tool is not trusted when it comes from MCP/plugin/external sources unless
  validation explicitly marks it trusted.
- `source`, `trusted`, `family`, `mutation`, `execution`, `exposure`, and
  `rendering_result` must be explicit at construction time. Do not rely on
  implicit trusted/builtin defaults for extension tools.
- A tool is not eligible for large-output persistence unless it can safely
  return a preview/path reference and later be restored/read.
- A tool is not `microcompact_eligible` unless old results can be safely hidden
  without losing critical state.
- A `microcompact_eligible` tool must also opt into large-output persistence in
  the current local contract.
- `destructive=False` does not mean "safe to run without policy"; it only means
  the tool is not classified as destructive. Permission mode and trust still
  apply.

#### Capability-Driven Composition

- Middleware and projection code must consume `ToolCapability` metadata instead
  of hard-coding tool names when the behavior is cross-cutting.
- Domain-specific validation belongs in the domain tool/schema/service, not in
  `tool_system`.
- `tool_system` may own capability projection, permission/trust routing,
  result persistence, and runtime events.
- Common tool failure classes such as unknown tool, permission denial, hook
  block, and tool exception should surface as bounded model-consumable
  `ToolMessage(status="error")` results rather than broken protocol state.
- `containers/*` may wire tool groups, but must not decide business semantics.

#### LangChain-Native Boundary

- Use LangChain `@tool`, strict Pydantic schemas, `ToolRuntime`, middleware,
  `ToolMessage`, and `Command(update=...)` first.
- Do not recreate cc-haha's TypeScript `Tool` interface as a parallel Python
  runtime object.
- Do not introduce a custom query loop or custom `StreamingToolExecutor` unless
  a source-backed PRD proves LangChain's runtime cannot satisfy a concrete local
  latency/order/cancellation need.
- If streaming/concurrency optimization becomes necessary, introduce a narrow
  LangChain adapter contract first and preserve middleware, policy, state, and
  evidence boundaries.

#### Exposure And Extension Sources

- `exposure="main"` and `exposure="extension"` are model-facing main tools.
- `exposure="child_only"` is allowed only for bounded child-agent or verifier
  surfaces.
- `exposure="deferred"` is the local deferred-discovery surface. Deferred tools
  must not enter the initial main/child projections directly.
- `ToolSearch` and `invoke_deferred_tool` are the main-surface bridge tools for
  deferred discovery/execution.
- Runtime surfaces should call registry projection helpers such as
  `project("main")`, `names_for_projection("main")`,
  `tools_for_projection("child")`, or `tools_for_names(...)` instead of
  duplicating exposure filtering.
- `ToolPoolProjection` is the explicit projection seam for follow-up work. It
  may be tested independently from agent startup and runtime wiring.
- `declarable_names()` must include enabled `main`, `extension`, and
  `deferred` names, while excluding `child_only` and disabled tools.
- `ToolSearch` must return the matched deferred tool's exact name plus the full
  `tool_call_schema` JSON schema needed for later execution.
- `invoke_deferred_tool` must execute the actual deferred capability through the
  shared `ToolGuardMiddleware` path so permission policy, hook dispatch,
  bounded failure shaping, and large-output persistence still apply to the real
  target tool.
- Deferred execution may preserve the real bounded result contract of the
  target capability, including `ToolMessage` and `Command(update=...)`, rather
  than degrading all deferred tools to plain string results.
- Do not overload `child_only` or `extension` to mean deferred schema loading.
- MCP/plugin tools must preserve source/trust metadata so permission and
  observability can distinguish builtin from extension behavior.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| duplicate capability names | registry construction raises `ValueError` |
| capability name differs from LangChain tool name | test failure; do not register |
| tool has extra public schema aliases | schema validation rejects unless explicitly documented |
| hidden runtime field appears in public schema | test failure |
| new tool omits capability metadata | test failure or review block |
| tool marked `read_only=True` but mutates workspace/store/state | reject metadata or change tool behavior |
| tool marked `concurrency_safe=True` but writes shared state | reject metadata |
| untrusted destructive extension in accept/bypass modes | permission remains ask/deny; not auto-allowed |
| tool handler raises exception | bounded `ToolMessage(status=\"error\")` is returned with the original `tool_call_id` |
| large-output eligible tool returns oversized result | middleware may persist full output and return preview/path |
| ineligible tool returns oversized result | result remains inline unless tool-local policy handles it |
| `microcompact_eligible=True` for non-restorable stateful output | reject metadata |
| child-only tool appears in main projection | projection test fails |
| extension tool lacks source/trust identity | startup/registration validation rejects it |
| deferred tool is registered | excluded from initial main and child projections; visible through `deferred` projection and bridge tools |
| `ToolSearch` query matches deferred tools | result returns exact names plus full JSON parameter schemas |
| `invoke_deferred_tool` targets unknown or non-deferred tool | bounded error result; no direct execution |
| `invoke_deferred_tool` targets a denied deferred capability | shared policy path still returns bounded `ToolMessage(status="error")` |
| deferred capability returns `Command(update=...)` | deferred bridge preserves the `Command` result instead of throwing a runtime error |

### 5. Good / Base / Bad Cases

#### Good

```python
ToolCapability(
    name="read_file",
    tool=read_file,
    domain="filesystem",
    read_only=True,
    destructive=False,
    concurrency_safe=True,
    source="builtin",
    trusted=True,
    family="filesystem",
    mutation="read",
    execution="plain_tool",
    exposure="main",
    rendering_result="tool_message_or_persisted_output",
    tags=("read", "workspace"),
    persist_large_output=True,
    max_inline_result_chars=4000,
    microcompact_eligible=True,
)
```

Expected:

- schema is strict and model-visible
- permission can auto-allow in safe modes
- concurrent reads are allowed
- large results may be persisted and later restored
- old results may be microcompacted because the file can be read again

#### Base

```python
ToolCapability(
    name="task_update",
    tool=task_update,
    domain="tasks",
    read_only=False,
    destructive=False,
    concurrency_safe=False,
    source="builtin",
    trusted=True,
    family="tasks",
    mutation="durable_store",
    execution="plain_tool",
    exposure="main",
    rendering_result="tool_message",
)
```

Expected:

- not destructive, but still not read-only
- not concurrency-safe because it mutates store-backed workflow state
- permission/policy and verifier boundaries still apply

#### Bad

```python
ToolCapability(
    name="write_file",
    tool=write_file,
    domain="filesystem",
    read_only=True,
    destructive=False,
    concurrency_safe=True,
    source="builtin",
    trusted=True,
    family="filesystem",
    mutation="workspace_write",
    execution="plain_tool",
    exposure="main",
    rendering_result="tool_message",
)
```

Expected:

- reject; this lies to permission and concurrency policy
- write tools must declare workspace mutation and non-concurrency-safe behavior

### 6. Tests Required

Required focused test families:

- `coding-deepgent/tests/tool_system/test_tool_system_registry.py`
- `coding-deepgent/tests/tool_system/test_tool_system_middleware.py`
- `coding-deepgent/tests/tool_system/test_tool_search.py`
- domain-specific schema tests, for example:
  - `coding-deepgent/tests/filesystem/test_tools.py`
  - `coding-deepgent/tests/tasks/test_tasks.py`
  - `coding-deepgent/tests/subagents/test_subagents.py`
  - `coding-deepgent/tests/memory/test_memory.py`
  - `coding-deepgent/tests/extensions/test_skills.py`
  - `coding-deepgent/tests/extensions/test_mcp.py`

Required assertion points:

- public tool names match capability names
- duplicate names fail
- main/child/extension exposure projections are stable
- deferred projection and bridge-tool contracts are stable
- hidden injected runtime fields are absent from model-visible schema
- invalid extra/alias fields fail schema validation
- permission behavior uses capability metadata
- common tool failures remain bounded protocol-correct `ToolMessage` errors
- untrusted destructive extension tools are not auto-allowed
- large-output and microcompact eligibility are opt-in
- child-only tools do not enter the main tool surface
- deferred tools do not enter the initial main tool surface directly

### 7. Wrong vs Correct

#### Wrong

```python
# Cross-cutting behavior hard-coded by tool name.
if request.tool_call["name"] in {"read_file", "bash", "grep"}:
    persist_large_output(...)
```

Why wrong:

- extension/MCP tools cannot participate without editing middleware
- behavior drifts from source/trust/domain metadata
- future ToolSearch/deferred/plugin work becomes special-case heavy

#### Correct

```python
capability = registry.get(str(request.tool_call["name"]))
if capability is not None and capability.persist_large_output:
    persist_large_output(...)
```

Why correct:

- tools opt in through metadata
- middleware stays generic
- extension tools can be validated and composed consistently

#### Wrong

```python
# Recreate cc-haha's full Tool runtime interface locally.
class Tool:
    def render_react_ui(...): ...
    def streaming_executor_hook(...): ...
```

Why wrong:

- `coding-deepgent` is LangChain/LangGraph-native
- React rendering and custom streaming loop are not local runtime boundaries
- this bypasses official middleware/tool state seams

#### Correct

```python
@tool("read_file", args_schema=ReadFileInput)
def read_file(path: str, runtime: ToolRuntime, limit: int | None = None) -> str:
    ...

ToolCapability(
    name="read_file",
    tool=read_file,
    ...
)
```

Why correct:

- LangChain owns tool execution/schema exposure
- `ToolCapability` owns cc-harness metadata not encoded by LangChain
- middleware can compose permission, result persistence, evidence, and pressure
  behavior from metadata
