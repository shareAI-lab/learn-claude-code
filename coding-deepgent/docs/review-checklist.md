# s03 Review Checklist

Use this checklist when reviewing or integrating `coding-deepgent/` changes.

## 1. Independence from `agents_deepagents`

- [ ] No runtime imports from `agents_deepagents`
- [ ] No test imports from `agents_deepagents`
- [ ] No project-local helper script depends on `agents_deepagents`
- [ ] Behavioral parity is documented as reference knowledge, not shared code

## 2. Cumulative app shape

- [ ] The directory reads as one standalone project/package
- [ ] The public surface is one integrated `s03` app/CLI
- [ ] The implementation does not expose stage-mirror entrypoints as the main
      interface
- [ ] The current app includes `s01` loop behavior, `s02` tool growth, and
      `s03` planning behavior together

## 3. Responsibility boundaries

- [ ] `config` owns environment/config loading
- [ ] `state` owns runtime state definitions
- [ ] `tools/filesystem` owns workspace tool behavior
- [ ] `tools/planning` owns planning-tool updates
- [ ] `middleware/planning` owns prompt/state mediation
- [ ] `app` owns agent wiring
- [ ] `cli` owns the command-line boundary
- [ ] `tests` verify the project locally instead of reaching outward

## 4. Planning-state quality guardrails

- [ ] Planning state is explicit, reviewable, and bounded
- [ ] The plan keeps at most one `in_progress` item
- [ ] Planning updates happen through the intended tool/update path
- [ ] Reminder or rendering behavior stays in middleware, not scattered across
      unrelated modules

## 5. Documentation + milestone consistency

- [ ] `README.md` says the project is cumulative through `s03`
- [ ] `PROJECT_PROGRESS.md` records the same milestone and upgrade gate
- [ ] Docs explain that later upgrades are user-confirmed, not automatic
- [ ] Docs clearly state that `agents_deepagents/` is reference-only

## 6. Verification handoff

The implementation/test lanes should be able to show evidence for:

- [ ] standalone import/build health
- [ ] focused tests for tools, app wiring, and planning behavior
- [ ] absence of forbidden `agents_deepagents` dependencies
- [ ] one integrated `s03` entrypoint instead of parallel public stages
