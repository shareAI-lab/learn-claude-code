# coding-deepgent

Independent cumulative LangChain cc product surface.

## Current product stage

- `current_product_stage`: `stage-5-memory-context-compact-foundation`
- `compatibility_anchor`: `memory-context-compact-foundation`
- Upgrade policy: advance by explicit product-stage plan approval, not tutorial chapter completion.

## Current architecture

- LangChain remains the runtime boundary: `RuntimeState`, `RuntimeContext`, `context=`, and LangGraph `thread_id` config own runtime invocation.
- Dependency-injector containers compose settings, runtime seams, domain tools, middleware, session storage, and agent creation; domain packages do not import containers.
- The public planning contract remains cc-aligned `TodoWrite(todos=[...])` with required `activeForm` on every todo item.
- Stage 3 creates a professional runtime foundation without full cc parity; subagents, hooks, permissions, compact, memory, MCP, and durable tasks remain future domains.

## CLI surface

The stage-3 runtime-foundation CLI keeps the legacy `--prompt` path while adding grouped commands:

- `coding-deepgent --prompt "..."` — run one prompt and exit
- `coding-deepgent run "..."` — explicit one-shot command
- `coding-deepgent config show` — render the resolved local configuration without exposing secrets
- `coding-deepgent sessions list` — render the current session index view
- `coding-deepgent sessions resume <session-id> --prompt "..."` — continue a recorded session when a session provider is wired
- `coding-deepgent doctor` — verify CLI/rendering/logging dependencies locally

Rich table renderers live in `coding_deepgent.renderers.text`, and local structured logging setup lives in `coding_deepgent.logging_config`.

## Stage 4 control-plane foundation

Stage 4 adds deterministic permission/safety decisions, local lifecycle hooks, and structured prompt/context assembly as LangChain-native seams over the existing `create_agent` runtime. Interactive UI approval, auto classifiers, memory, durable tasks, subagents, and MCP/plugin loading remain future stages.

## Stage 5 memory/context/compact foundation

Stage 5 adds a store-backed long-term memory foundation seam, the model-visible `save_memory` tool, bounded memory context injection, and deterministic tool-result budget helpers. Message-history projection/pruning, LLM autocompact, session-memory side-agent writing, subagents, durable tasks, and MCP/plugin memory sync remain future work.
