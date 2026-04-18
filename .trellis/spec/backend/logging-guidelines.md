# Logging Guidelines

> Logging and runtime event conventions for the current `coding-deepgent` mainline.

---

## Overview

`coding-deepgent` uses `structlog` for local structured logging setup.

Current setup:

- `coding_deepgent.logging_config.configure_logging()`
- JSON rendering via `structlog.processors.JSONRenderer`
- ISO timestamps
- log level filtering from the configured level

Runtime facts that should survive resume/audit should usually be session
evidence, not just logs.

Default evidence posture: **high-value recoverable facts only**.

---

## Log Levels

- `debug`
  - local diagnostic detail that should not be required for normal operation
- `info`
  - successful startup/config/major lifecycle observations
- `warning`
  - recoverable unexpected behavior or degraded paths
- `error`
  - unrecoverable local failures before converting to CLI/user-facing errors

Use the configured level instead of ad hoc print debugging.

---

## Structured Logging

Prefer structured event fields over prose-only logs.

Recommended fields when applicable:

- `event`
- `session_id`
- `thread_id`
- `entrypoint`
- `tool_name`
- `capability_source`
- `decision`
- `status`

Do not log arbitrary model prompts, raw tool outputs, API keys, or secret-like
environment values.

---

## Runtime Evidence Vs Logs

Use session evidence when the fact should be recoverable across sessions or
visible in recovery briefs.

Do not use evidence as a general event log.

Examples that belong in evidence:

- verifier verdicts
- permission-denied events
- hook-blocked events
- compact/runtime pressure counters when they affect continuation

Examples that can stay as logs:

- hook start/complete events that do not block execution
- successful ordinary tool calls
- config/startup diagnostics
- startup diagnostics
- local configuration display plumbing
- non-contractual debug detail

Current whitelisted runtime evidence kinds:

- `hook_blocked`
- `permission_denied`
- `snip`
- `microcompact`
- `context_collapse`
- `auto_compact`
- `post_autocompact_turn`
- `reactive_compact`
- `subagent_spawn_guard`
- `orphan_tombstoned`
- `query_error`

`token_budget` is a bounded runtime event for local observability. It is not
persisted as session evidence by default because it can fire every assistant
response turn and would otherwise dominate recovery briefs.

Env-gated prompt/API dumps are allowed only when
`CODING_DEEPGENT_DUMP_PROMPTS=1`. Dumps must be local files, must keep secrets
out of dump metadata, and must never be injected back into model-visible
context.

Add a new evidence kind only when:

- it helps session recovery or audit
- it can be summarized concisely
- its metadata can be safely bounded
- it has focused tests

---

## What NOT To Log

- provider API keys or auth tokens
- raw full prompts
- raw large tool outputs
- sensitive local file contents
- arbitrary plugin/MCP payload dumps
- unbounded exception payloads that may include secrets

---

## Common Mistakes

- Using `print()` for runtime diagnostics that should be structured.
- Treating logs as durable product evidence.
- Logging raw model/tool payloads when a bounded evidence record would be safer.
- Recording every runtime event as evidence and making recovery briefs noisy.
