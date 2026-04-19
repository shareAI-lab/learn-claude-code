# brainstorm: extract coding agent repo

## Goal

将当前主线产品 `coding-deepgent/` 连同必要的 Trellis 协作、规范、计划和高价值历史决策移植到一个新的独立 git repository，形成可以独立开发、测试、记录任务和后续发布的 `coding-agent` 产品仓库。

本任务先制定一次性迁移计划；在用户确认后，按计划一次性执行迁移、文档修正、验证和提交。

## What I already know

* 用户希望把 coding-agent 移植出去，并且把相关 Trellis 文档一起移植。
* 用户倾向一次性做完，而不是多轮零散迁移。
* 当前 repo 的产品主线是 `coding-deepgent/`。
* 当前 repo 的 tutorial/reference 层包括 `agents/`, `agents_deepagents/`, `docs/`, `web/`, `skills/`，默认不属于本次产品移植范围。
* 当前工作区 clean；当前分支是 `codex/stage-12-14-context-compact-foundation`，比 origin ahead 107 commits。
* 当前没有 active Trellis task；本 brainstorm task 是 `.trellis/tasks/04-20-extract-coding-agent-repo/`。
* `coding-deepgent/pyproject.toml` 当前项目名是 `coding-deepgent`，console scripts 是 `coding-deepgent` 和 `coding-deepgent-ui`。
* Python package 当前是 `src/coding_deepgent`。
* React/Ink CLI frontend 在 `frontend/cli`，package name 是 `@coding-deepgent/cli-frontend`，bin 是 `coding-deepgent-ui`。
* `coding-deepgent/README.md` 当前使用 `../AGENTS.md` 和 `../.trellis/...` 作为 canonical docs 路径；移植后需要改为 repo-root 路径。
* `.trellis/` 是当前产品线的 canonical coordination layer，不是普通附属笔记。
* `.trellis/spec/` 内大量规则仍以 `coding-deepgent/` 作为实现根路径；移植后需要将语义改为 repo root 下的 `src/`, `tests/`, `frontend/`。
* `.trellis/tasks/archive/2026-04/` 有大量与产品演进相关的历史 PRD，但也包含旧分支名、旧 PR、旧 monorepo 路径和操作日志式上下文。

## Assumptions (temporary)

* 新仓库路径使用 `/root/coding-agent`，除非用户指定其他路径。
* 新仓库初始阶段保留 Python package 名 `coding_deepgent` 和 CLI 命令 `coding-deepgent`，先确保迁移后行为不变；重命名为 `coding_agent` / `coding-agent` 放入后续独立任务。
* 本次迁移使用 clean snapshot import，不强保旧仓库 git history。
* 不复制 secrets、runtime state、cache、local memory database、node_modules。
* 迁移结果需要在新 repo 内独立通过 Python 后端测试、lint/typecheck、Trellis 链接检查，以及 frontend CLI typecheck/test。

## Open Questions

* 用户是否接受推荐方案：新建独立 repo `/root/coding-agent`，先保留现有 package/CLI 名称，后续再做产品重命名？

## Requirements (evolving)

* 新建独立 git repo，作为迁移后的 source of truth。
* 将 `coding-deepgent/` 的产品代码提升到新 repo 根目录。
* Curated migrate Trellis：保留 workflow/scripts/spec/plans/project-handoff/config，以及高价值历史任务归档；剔除本地身份、当前任务指针、运行态和普通会话 journal。
* 将新 repo 文档改成 repo-root product mainline，不再说当前主线是 `coding-deepgent/` 子目录。
* 保留可验证、可回滚的迁移证据：source commit、复制清单、排除清单、验证命令和结果。
* 一次性完成迁移、Trellis 修正、验证、初始 commit。

## Acceptance Criteria (evolving)

* [x] `/root/coding-agent` 存在且是独立 git repository。
* [x] 新 repo 根目录包含产品文件：`pyproject.toml`, `README.md`, `PROJECT_PROGRESS.md`, `src/`, `tests/`, `frontend/`, `.trellis/`, `AGENTS.md`。
* [x] 新 repo 不包含 `.env`, `.coding-deepgent/memory.db`, `.omx/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `__pycache__/`。
* [x] 新 repo 的 `AGENTS.md`, `README.md`, `.trellis/project-handoff.md`, `.trellis/spec/*` 不再把 `coding-deepgent/` 子目录描述为当前实现根。
* [x] Trellis 脚本可运行：`python3 ./.trellis/scripts/get_context.py`。
* [x] Trellis 链接检查可运行：`python3 ./.trellis/scripts/check_trellis_links.py`。
* [x] Python 验证在新 repo 内通过或记录明确阻塞：`pytest -q`, `ruff check .`, `mypy src`。
* [x] Frontend 验证在新 repo 内通过或记录明确阻塞：`npm --prefix frontend/cli test`, `npm --prefix frontend/cli run typecheck`。
* [x] 新 repo 有 initial commit，commit message 说明这是迁移快照。

## Definition of Done

* 迁移清单、排除清单、路径语义修正和验证结果写入 active PRD。
* 新 repo 初始化完成并有清晰 initial commit。
* 原 repo 不被破坏；原 repo 只新增/更新本 planning task 相关 Trellis 记录。
* 若验证失败，失败原因和下一步修复范围明确记录，不做模糊完成。

## Research Notes

### What similar extraction workflows usually do

* Monorepo-to-repo extraction normally has two choices：history-preserving filter 或 clean snapshot import。
* History-preserving extraction is useful when blame/log continuity matters, but it is brittle when only part of `.trellis/` should move and paths need semantic rewriting.
* Clean snapshot import is simpler, easier to audit, and better when the new repo intentionally changes ownership boundaries.

### Constraints from this repo

* `coding-deepgent/` is currently nested under a larger tutorial/reference repo.
* `.trellis/` is shared at old repo root, but the high-value Trellis content now primarily serves `coding-deepgent`.
* `.trellis/tasks/archive` contains product-relevant decisions but also contains many historical file paths and branch references that should not become active executable context.
* `coding-deepgent` package and CLI names are currently used by tests, README, frontend scripts, and probably runtime env vars.

### Feasible approaches here

**Approach A: clean snapshot extraction with curated Trellis migration** (Recommended)

* How it works:
  * Create `/root/coding-agent`.
  * Copy tracked product files from `coding-deepgent/` to repo root.
  * Copy high-value `.trellis/` files and selected task archives.
  * Rewrite live Trellis/docs paths to repo-root semantics.
  * Keep package/CLI names unchanged for first migration commit.
* Pros:
  * Lowest risk for one-shot execution.
  * Avoids dragging tutorial repo history and old workspace noise into new product repo.
  * Makes the new repo boundary explicit and clean.
* Cons:
  * Loses git blame/history continuity unless old repo remains as archive reference.

**Approach B: history-preserving extraction with `git filter-repo`**

* How it works:
  * Clone old repo into temp dir.
  * Filter history for `coding-deepgent/`, `AGENTS.md`, and selected `.trellis/` paths.
  * Move `coding-deepgent/` contents to root.
  * Then repair Trellis/docs.
* Pros:
  * Preserves more file history.
* Cons:
  * Higher failure surface; curated `.trellis/` selection is hard across history.
  * More likely to preserve outdated monorepo context accidentally.
  * More expensive to verify.

**Approach C: keep as subtree/submodule**

* How it works:
  * Create a new wrapper repo that pulls `coding-deepgent/` as subtree or submodule.
* Pros:
  * Minimal extraction work.
* Cons:
  * Does not actually make the product repo clean.
  * Trellis remains awkward because canonical docs live outside product root.
  * Poor fit for user's goal of moving coding-agent out.

## Expansion Sweep

### Future evolution

* Package/CLI rename from `coding-deepgent` to `coding-agent` should be a second explicit migration, with compatibility decisions and deprecation strategy.
* New repo may later need GitHub remote, release packaging, CI workflow, and public/private distribution policy.

### Related scenarios

* Trellis task workflow must work from the new repo root.
* Frontend CLI scripts must work with root-relative `PYTHONPATH=src` after directory promotion.
* Runtime state directories such as `.coding-deepgent/` may later need rename policy, but should not be renamed in the extraction commit.

### Failure and edge cases

* Stale `coding-deepgent/` path references in live specs can cause future agents to edit nonexistent paths.
* Copying `.env`, memory DB, cache, or `node_modules` would leak local state and bloat the repo.
* Running tests from the promoted root may expose path assumptions previously hidden by the nested directory.

## Technical Approach

Recommended one-shot plan:

1. Capture source state:
   * current branch
   * current commit
   * `git status -sb`
   * tracked file inventory for `coding-deepgent`, `AGENTS.md`, and curated `.trellis`
2. Create target repo:
   * `/root/coding-agent`
   * initialize git
   * add a root `.gitignore` that excludes env files, caches, runtime state, databases, `node_modules`, and Python/TS build outputs
3. Promote product tree:
   * copy tracked `coding-deepgent/` files to target repo root
   * exclude runtime/local/cache files
4. Migrate Trellis:
   * copy `.trellis/workflow.md`
   * copy `.trellis/scripts/`
   * copy `.trellis/spec/`
   * copy `.trellis/plans/`
   * copy `.trellis/project-handoff.md`
   * copy `.trellis/config.yaml`
   * copy `.trellis/.gitignore`
   * copy selected `.trellis/tasks/archive/2026-04/` task PRDs and related plan/audit files, but treat them as historical reference
   * initialize fresh `.trellis/workspace/index.md`; do not copy personal journals by default
5. Rewrite live docs:
   * root `AGENTS.md`: current mainline is repo root
   * `README.md`: canonical docs are `.trellis/...`, not `../.trellis/...`
   * `.trellis/project-handoff.md`: remove old PR/branch as current live state; preserve old source commit as extraction provenance
   * `.trellis/spec/backend/index.md`: repo root is product mainline
   * `.trellis/spec/frontend/index.md`: frontend paths are `frontend/cli` and `src/coding_deepgent/frontend`
   * `.trellis/spec/guides/mainline-scope-guide.md`: tutorial/reference layer is no longer in repo by default
   * high-signal backend specs: replace executable path examples from `coding-deepgent/src/...` and `coding-deepgent/tests/...` to `src/...` and `tests/...`
6. Verify path hygiene:
   * `rg -n "coding-deepgent/|../.trellis|learn-claude-code|pull/220|codex/stage-12-14" .`
   * classify remaining hits as either package/CLI name, historical archive, or docs bug
7. Validate product:
   * Python install/dev validation
   * backend tests
   * backend lint/typecheck
   * frontend npm tests/typecheck
   * Trellis scripts/link check
8. Commit in new repo:
   * `chore: extract coding agent repository`
   * include migration summary in PRD / migration note

## Decision (ADR-lite)

**Context**: The product currently lives as `coding-deepgent/` inside a broader tutorial/reference repository, while Trellis lives at old repo root and already acts as the canonical workflow/spec layer for the product. A move to an independent `coding-agent` repo requires both file relocation and documentation ownership cleanup.

**Decision**: Recommend Approach A: clean snapshot extraction with curated Trellis migration, preserving package and CLI names for the first migration commit.

**Consequences**: The new repo starts with a clean boundary and a reproducible migration record, but old git blame/history remains in the source repo unless a separate archival/history-preserving extraction is later required.

## Out of Scope

* Full package rename from `coding_deepgent` to `coding_agent`.
* CLI rename from `coding-deepgent` to `coding-agent`.
* npm package/bin rename.
* Publishing to a GitHub remote or creating a PR.
* Copying local runtime state, memory database, `.env`, caches, or `node_modules`.
* Migrating tutorial/reference directories outside product scope.

## Technical Notes

* Inspected:
  * `AGENTS.md`
  * `.trellis/workflow.md`
  * `.trellis/project-handoff.md`
  * `.trellis/spec/backend/index.md`
  * `.trellis/spec/frontend/index.md`
  * `.trellis/spec/guides/index.md`
  * `.trellis/spec/guides/mainline-scope-guide.md`
  * `.trellis/spec/guides/architecture-posture-guide.md`
  * `.trellis/spec/guides/trellis-doc-map-guide.md`
  * `coding-deepgent/README.md`
  * `coding-deepgent/pyproject.toml`
  * `coding-deepgent/frontend/cli/package.json`
* Source inventory observations:
  * `git ls-files coding-deepgent .trellis AGENTS.md | wc -l` reported 798 tracked files including Trellis archives.
  * `find coding-deepgent ... | wc -l` excluding common caches/runtime directories reported 272 product files.
  * `find .trellis/tasks/archive/2026-04 -name prd.md | wc -l` reported 127 archived PRDs.
* High-risk old-context strings:
  * `coding-deepgent/`
  * `../.trellis`
  * `learn-claude-code`
  * `pull/220`
  * `codex/stage-12-14-context-compact-foundation`

## Migration Execution Results

### Source

* Source repo: `/root/learn-claude-code`
* Source commit: `d0463493055c48790a2a20a6c28fa386a1929e1e`
* Extraction strategy: clean snapshot extraction with curated Trellis migration
* Target repo: `/root/coding-agent`
* Target branch: `main`
* Initial commit: `808262479095f6c5df674e3c2b6a3ef0f7bf6761` (`chore: extract coding agent repository`)

### Migrated

* Product root files: `pyproject.toml`, `README.md`, `PROJECT_PROGRESS.md`, `project_status.json`, `.env.example`, `.flake8`
* Product code/tests/frontend: `src/`, `tests/`, `frontend/`
* Trellis live layer: `AGENTS.md`, `.trellis/workflow.md`, `.trellis/scripts/`, `.trellis/spec/`, `.trellis/plans/`, `.trellis/project-handoff.md`, `.trellis/config.yaml`, `.trellis/worktree.yaml`
* Trellis historical archive: `.trellis/tasks/archive/2026-04/` with 127 archived `prd.md` files
* Migration task record: `.trellis/tasks/04-20-extract-coding-agent-repo/`

### Intentionally excluded

* `.env`
* `.coding-deepgent/`
* `.omx/`
* `.mypy_cache/`
* `.pytest_cache/`
* `.ruff_cache/`
* `frontend/cli/node_modules/`
* `__pycache__/`
* old source workspace journals and `.trellis/.developer`

### Path hygiene

`rg -n "coding-deepgent/|../.trellis|learn-claude-code|pull/220|codex/stage-12-14" ...`
after live-doc rewrite returns only:

* historical extraction provenance in `README.md`, `AGENTS.md`, and `.trellis/project-handoff.md`
* this migration PRD's source-context notes
* preserved runtime-state paths such as `.coding-deepgent/tool-results/`

No live spec now describes `coding-deepgent/` as the current implementation
root.

### Verification

* `python3 ./.trellis/scripts/check_trellis_links.py` -> `Trellis markdown links OK`
* `python3 ./.trellis/scripts/get_context.py` -> ran successfully with a local gitignored `.trellis/.developer`
* `python3 -m pytest -q` -> `406 passed`
* `python3 -m ruff check .` -> `All checks passed!`
* `python3 -m mypy src` -> `Success: no issues found in 143 source files`
* `npm --prefix frontend/cli ci` -> installed frontend validation dependencies into ignored `node_modules`
* `npm --prefix frontend/cli test` -> `2 passed`, `8 passed`
* `npm --prefix frontend/cli run typecheck` -> passed
* validation artifacts cleaned with `git clean -fdX`
