# L4-a Findings: LangChain Parallel Tool-Call Research

Date: 2026-04-18
Task: `04-17-l4a-h01-langchain-parallel-tool-call-research`
Scope: determine whether current LangChain/LangGraph behavior is sufficient for
non-streaming parallel tool calls in `coding-deepgent`.

## Sources

Official LangChain docs:

- `https://docs.langchain.com/oss/python/langchain/models` (`Tool calling`,
  `Parallel tool calls`)
- `https://docs.langchain.com/oss/python/langchain/tools` (`ToolNode`)

Local installed source:

- `langchain 1.2.12`
- `langgraph.prebuilt.tool_node.ToolNode`
- `langchain.agents.factory.create_agent`
- `langchain_core.runnables.config.get_executor_for_config`

Local product code:

- `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
- `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
- `coding-deepgent/src/coding_deepgent/todo/middleware.py`
- `coding-deepgent/tests/test_planning.py`

## What LangChain Already Guarantees

### 1. Models may emit multiple tool calls in one turn

Official docs state that many models support multiple parallel tool calls and
that the model may generate multiple tool calls in one response. Docs also note
that providers such as OpenAI/Anthropic can disable this with
`parallel_tool_calls=False` at bind time.

Implication for `coding-deepgent`:

- multiple tool calls in one model turn are already part of the standard
  LangChain tool-calling model surface
- we should treat this as a real possible runtime shape, not a future edge case

### 2. `create_agent()` uses `ToolNode` internally

Local installed `langchain.agents.factory.create_agent` constructs a
`ToolNode(...)` for client-side tools. There is no separate `coding-deepgent`
tool executor bypassing this path.

Implication:

- current `coding-deepgent` agent runtime inherits `ToolNode` behavior directly
- if `ToolNode` is sufficient, no custom executor should be added

### 3. `ToolNode` executes multiple tool calls in parallel

Observed in local installed source:

- sync path uses `get_executor_for_config(config)` plus
  `executor.map(self._run_one, ...)`
- async path uses `asyncio.gather(...)`
- `get_executor_for_config()` builds a thread-pool executor using
  `max_workers=config.get("max_concurrency")`

Implication:

- LangGraph already parallelizes multiple client-side tool calls in the same
  step
- there is no need for a local adapter just to get basic non-streaming
  parallelism

### 4. Output order is preserved

`ToolNode._combine_tool_outputs(outputs, ...)` consumes the `outputs` list in
the same order it was produced from `executor.map(...)` / `asyncio.gather(...)`.
Both preserve input ordering.

Local experiment:

- two tools each slept `0.4s`
- total elapsed wall-clock was `~0.405s`
- output order remained `call_a`, then `call_b`

Implication:

- current LangChain behavior already satisfies the baseline requirement
  "parallel execution with original tool-call order preserved"

## What LangChain Does Not Guarantee For Us

### 1. No capability-aware partitioning

`ToolNode` parallelizes the tool calls it is given. It does not know anything
about local metadata like:

- `ToolCapability.concurrency_safe`
- `mutation`
- `destructive`
- local trust/source semantics

Implication:

- if we need "read-only tools may run concurrently, unsafe tools must be
  serialized/exclusive", LangChain does not provide that policy out of the box
- implementing that policy would require a local adapter/tool-node wrapper or
  a stronger model-side restriction

### 2. No built-in protection against parallel state-replacement semantics

Local repo already contains one explicit safeguard:

- `PlanContextMiddleware.after_model()` rejects multiple `TodoWrite` tool calls
  in the same response, because session todo replacement is not safe in
  parallel

Implication:

- the repo already assumes LangChain may hand us parallel tool calls
- local invariants for stateful tools must be protected explicitly

## Recommendation For Local Work

### Recommendation

Do **not** implement `L5-a` as a runtime partition adapter now.

Instead:

1. treat LangChain/ToolNode parallelism as sufficient for the current
   non-streaming baseline
2. keep local protections as targeted invariants/tests for known unsafe tools
3. only reopen an execution adapter if `L4-b` / `L4-c` or a concrete runtime
   failure shows that capability-aware partitioning is required

### Why

- basic parallel execution already exists upstream
- result ordering is already stable
- current repo has no demonstrated failure for parallel read-only tools
- adding a local partition executor now would introduce a heavier runtime seam
  before we have a concrete source-backed failure

### Concrete L5-a Decision

`L5-a` should be **downgraded from implementation work to conditional/spec-only
follow-up**.

Keep it dormant unless one of these becomes true:

- local tests show unsafe multi-tool execution can occur and break state/tool
  invariants
- LangChain ordering/middleware behavior fails a concrete repo test
- the product requires capability-aware serialization for mutating tools beyond
  today's targeted guards

## What Local Tests Should Prove Before Any Adapter

Before reviving `L5-a`, local tests should prove all of:

1. a single model turn can contain multiple tool calls in our agent path
2. `ToolGuardMiddleware`, hooks, large-output persistence, and runtime events
   all still apply under multi-tool execution
3. output order remains aligned with original tool-call order
4. known unsafe/stateful tools are either:
   - explicitly prevented from parallel use, or
   - shown to remain correct under parallel execution

Concrete follow-up targets:

- `L4-b`: tool-use/result pairing and protocol-correct failure tests
- `L4-c`: result persistence / microcompact eligibility audit

If those pass without exposing a real safety gap, `L5-a` should remain
deferred.
