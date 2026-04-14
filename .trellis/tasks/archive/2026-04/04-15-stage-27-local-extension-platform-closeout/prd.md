# Stage 27: Local Extension Platform Closeout

## Goal

Close H15-H18 MVP gaps by tightening local skills, MCP, plugin manifests, and hooks as safe extension surfaces without adding marketplace/install/update, remote trust, or remote hook platforms.

## Function Summary

This stage should verify and minimally harden local extension packaging and loading so extensions remain typed, local, and policy-bound through the same tool/permission/runtime boundaries.

## Expected Benefit

* Extensibility: local extension surfaces are usable and predictable.
* Safety: plugins, MCP, skills, and hooks do not bypass tool/permission boundaries.
* Maintainability: extension manifests and lifecycle hooks have explicit contracts.

## Corresponding Highlights

* `H15 Skill system as capability packaging`
* `H16 MCP as external capability protocol`
* `H17 Plugin states: source / install / enable`
* `H18 Hooks as programmable middleware`

## Corresponding Modules

* `coding_deepgent.skills`
* `coding_deepgent.mcp`
* `coding_deepgent.plugins`
* `coding_deepgent.hooks`
* `coding_deepgent.tool_system`
* `coding_deepgent.extensions_service`

## Out Of Scope

* marketplace install/update flows
* remote plugin trust/auth UX
* remote hook platform
* executing plugin code
* replacing LangChain runtime with extension runtime

## Acceptance Criteria

* [x] cc-haha source mapping for H15-H18 is recorded in this stage PRD.
* [x] local H15-H18 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H15-H18 become implemented or remain partial/deferred with explicit minimal residuals.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve extensibility, safety, and maintainability. The local runtime effect is: skills, MCP, plugins, and hooks remain typed local extension seams that still flow through the same tool/permission/runtime boundaries.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Skills | skill frontmatter becomes model-visible command/tool packaging | local skills stay strict, deterministic, and explicitly loaded | skill loader/render/runtime context tests | partial | Close local MVP skill packaging now |
| MCP | typed external capability protocol with transport/config validation | local MCP stays config-validated and adapter-backed without replacing runtime | transport alias/http/sse config tests; tool/resource separation | partial | Close local MVP MCP protocol now |
| Plugins | source/install/enable are distinct upstream states | local MVP only supports manifest/source validation, not install/enable lifecycle | registry uniqueness/resource validation tests; lifecycle deferred | partial/defer | Close local manifest MVP; defer lifecycle state machine |
| Hooks | hooks are programmable middleware around runtime/tool events | local hooks stay sync, typed, event-emitting middleware, not backdoors | dispatcher event envelope tests | partial | Close local MVP hook middleware now |

### Source files inspected

Explorer A inspected cc-haha sources including:

* `/root/claude-code-haha/src/skills/loadSkillsDir.ts`
* `/root/claude-code-haha/src/tools/SkillTool/SkillTool.ts`
* `/root/claude-code-haha/src/services/mcp/types.ts`
* `/root/claude-code-haha/src/services/mcp/client.ts`
* `/root/claude-code-haha/src/services/mcp/config.ts`
* `/root/claude-code-haha/src/utils/plugins/installedPluginsManager.ts`
* `/root/claude-code-haha/src/services/plugins/pluginOperations.ts`
* `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`
* `/root/claude-code-haha/src/utils/hooks.ts`
* `/root/claude-code-haha/src/services/tools/toolHooks.ts`
* `/root/claude-code-haha/src/utils/hooks/sessionHooks.ts`
* `/root/claude-code-haha/src/utils/hooks/registerSkillHooks.ts`
* `/root/claude-code-haha/src/utils/plugins/loadPluginHooks.ts`

## Technical Approach

* Close H15 with skill malformed/mismatch/render truncation tests.
* Close H16 with MCP `type` alias and http/sse transport contract tests.
* Close H17 with plugin registry uniqueness and explicit known-resource validation tests, while deferring full install/enable lifecycle.
* Close H18 with direct runtime/context hook event-envelope tests.

## Checkpoint: Stage 27

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added skill loader malformed/mismatch and render truncation regressions.
- Added MCP transport alias/http/sse contract regressions.
- Added plugin registry duplicate-name and known-resource validation regressions.
- Added hook runtime/context dispatcher event-envelope regressions.

Corresponding highlights:
- `H15 Skill system as capability packaging`
- `H16 MCP as external capability protocol`
- `H17 Plugin states: source / install / enable`
- `H18 Hooks as programmable middleware`

Corresponding modules:
- `coding_deepgent.skills`
- `coding_deepgent.mcp`
- `coding_deepgent.plugins`
- `coding_deepgent.hooks`
- `coding_deepgent.tool_system`
- `coding_deepgent.extensions_service`

Tradeoff / complexity:
- Chosen: local-only extension platform closeout through strict schemas, manifest validation, adapter boundaries, and hook envelopes.
- Deferred: marketplace install/update, remote trust/auth UX, full plugin enable state machine, remote hook platform, plugin code execution.
- Why this complexity is worth it now: these extension seams already existed; the MVP risk was contract drift and unclear plugin lifecycle scope.

Verification:
- `pytest -q coding-deepgent/tests/test_skills.py coding-deepgent/tests/test_mcp.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py`
- `ruff check coding-deepgent/tests/test_skills.py coding-deepgent/tests/test_mcp.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_hooks.py`
- `mypy coding-deepgent/src/coding_deepgent/skills/loader.py coding-deepgent/src/coding_deepgent/skills/schemas.py coding-deepgent/src/coding_deepgent/mcp/loader.py coding-deepgent/src/coding_deepgent/mcp/adapters.py coding-deepgent/src/coding_deepgent/plugins/registry.py coding-deepgent/src/coding_deepgent/hooks/dispatcher.py coding-deepgent/tests/test_skills.py coding-deepgent/tests/test_mcp.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_hooks.py`

Boundary findings:
- H17 is implemented for MVP as local manifest/source validation only; full install/enable lifecycle is deferred.
- MCP resources remain metadata/read surfaces and are not promoted to executable tools in this MVP.

Decision:
- continue

Reason:
- Stage 27 is complete and Stage 28 (H19 observability/evidence closeout with minimal H20 decision) remains the next milestone from the canonical dashboard.
