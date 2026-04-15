# brainstorm: consolidate project docs into trellis

## Goal

将项目内分散的规范文件、代码结构说明、项目要求与相关入口统一整理到 `.trellis/` 体系中，使 Trellis 成为后续协作的唯一主入口；同时删除被收编后的重复文档，以及不再需要的相关 skill 或 skill 引用。

## What I already know

* 用户希望以后“都以 trellis 为主”。
* 用户明确澄清：当前工作的主线项目是 `coding-deepgent/`。
* 仓库外层“教程层”包括 `web/`、`skills/`、`docs/`、教学/参考测试、`agents/`、`agents_deepagents/` 等，当前都不是工作主线，默认按参考内容处理。
* 用户已明确要求：首批清理范围包含根 `skills/` 与根目录教程测试。
* 当前 `.trellis/spec/` 中只有少量后端契约文档处于 `Active`，大量 frontend/backend index 仍是占位内容。
* 仓库中还存在大量非 `.trellis/` 文档来源：
  * 根目录 `README*.md`
  * `docs/{en,ja,zh}/`
  * `coding-deepgent/docs/`
  * `agents_deepagents/cc_alignment/`
* 仓库中还存在项目级技能目录 `skills/`，包含至少：
  * `skills/code-review/SKILL.md`
  * `skills/agent-builder/SKILL.md`
  * `skills/mcp-builder/SKILL.md`
  * `skills/pdf/SKILL.md`
* 代码与文档中已有多处对 `skills/`、`docs/`、`AGENTS.md`、workflow/spec/guideline 的引用，删除前需要先处理引用和入口。
* `AGENTS.md` 已经把 Trellis 设为会话起点，但 `.trellis/spec/` 里的多数规范仍未承接仓库现有知识。
* `coding-deepgent/docs/` 中包含大量真正影响当前产品开发的阶段说明、评审清单、cc 对齐路线图，当前不在 `.trellis/spec/` 主入口内。
* `.trellis/spec/backend/runtime-context-compaction-contracts.md` 与 `task-workflow-contracts.md` 已经证明：Trellis 适合承接“可执行契约 / 项目规范”。
* `.trellis/spec/backend/*`、`.trellis/spec/frontend/*` 的很多文件仍是模板或占位文案。
* `docs/{en,ja,zh}/` 与根 `README*.md` 更像教学主线与阅读入口，而不是单纯的项目协作规范。
* `skills/` 不只是历史遗留目录；它们仍被以下区域引用：
  * `agents/s05_skill_loading.py`
  * `agents_deepagents/s05_skill_loading.py`
  * `docs/*/s05-skill-loading.md`
  * `coding-deepgent` 的 skills/plugin 测试与说明
  * `web/src/data/*` 的教学可视化数据

## Assumptions (temporary)

* 这次工作应先完成“规范迁移与入口收敛”的设计和落盘，再做受控删除，避免先删后断链。
* `docs/` 下的教程型内容不应默认搬入 `.trellis/spec/`；需要明确区分“`coding-deepgent` 产品协作规范”与“仓库教程/参考文档”。
* 需要删除的 “相关 skill” 指的是那些原本承担项目规范入口职责、但在 Trellis 主导后会重复或过时的 skill，而不是所有技能都要移除。

## Open Questions

* None after scope confirmation.

## Requirements (evolving)

* Trellis 规范必须明确写出：当前工作主线是 `coding-deepgent/`，教程层默认不是实现目标。
* 盘点当前项目中所有实际承担“规范 / 结构 / 要求 / 协作入口”职责的文档。
* 区分 `coding-deepgent` 主线规范与教程/参考资产，不再把两者混成一个开发目标。
* 明确哪些内容应迁移到 `.trellis/spec/`、`.trellis/workflow.md`、`.trellis/workspace/` 或其他 Trellis 位置。
* 明确哪些现有文件在迁移后应删除，哪些应保留为产品文档。
* 清理多余入口，避免未来同时维护 Trellis 与非 Trellis 版本。
* 清理或改造与旧入口耦合的 skill / skill 引用。
* 首批清理范围包含：
  * `coding-deepgent/docs/` 下与 Trellis 重复的主线规范文件
  * 根 `skills/`
  * 根目录教程测试

## Acceptance Criteria (evolving)

* [x] 有一份 source-backed 清单，列出当前所有规范类文档、其用途、保留/迁移/删除决策。
* [x] Trellis 明确记录 `coding-deepgent` 是当前主线，教程层默认 reference-only。
* [x] `.trellis/` 内形成项目规范的主入口与清晰索引。
* [x] 迁移后的 Trellis 内容能覆盖当前实际开发所需的项目要求与代码结构说明。
* [x] 被判定为重复或废弃的文档已删除，且相关引用已更新。
* [x] 被判定为重复或废弃的相关 skill 已删除或改造，且不再误导后续协作。
* [x] 根目录教程测试已按首批清理范围删除。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 直接重写产品功能代码，除非为修复文档/skill 引用断链所必需
* 把教程层默认当作当前实现目标
* 无差别删除所有 `docs/`、`skills/`、`README` 内容
* 在没有完成映射清单前直接进行大规模删除

## Technical Notes

* New task: `.trellis/tasks/04-15-trellis-spec-consolidation`
* 初步发现的文档承载区：
  * `AGENTS.md`
  * `README.md`, `README-zh.md`, `README-ja.md`
  * `docs/`
  * `coding-deepgent/docs/`
  * `agents_deepagents/cc_alignment/`
  * `.trellis/spec/`
* 初步发现的 skill 承载区：
  * `skills/`
  * `.agents/skills/`

## Research Notes

### What different document areas are doing now

* `AGENTS.md`
  * 已经是“如何进入 Trellis 工作流”的顶层入口。
* `.trellis/workflow.md`
  * 已经定义开发工作流、任务机制、workspace/journal 约束。
* `.trellis/spec/`
  * 已有少量高价值可执行规范，但大部分结构/质量/前端规范仍为空模板。
* `coding-deepgent/docs/`
  * 承载当前产品开发的真实阶段语义、cc 对齐决策、review checklist。
* `docs/` + `README*.md`
  * 承载教学主线、章节阅读顺序、多语言教材内容。
* `skills/`
  * 承载教程和示例 agent 的按需知识加载样本，不只是“团队规范”。
* `.trellis/project-handoff.md`
  * 已经明确 `coding-deepgent` 是 product track / current mainline。

### Constraints from our repo/project

* 如果删除 `docs/`，将破坏教学仓库主入口和 web 生成内容，不是单纯的“规范整理”。
* 如果删除 `skills/`，将影响 `s05` 教学、相关测试、Deep Agents 轨道、以及部分产品说明。
* 如果不把 `coding-deepgent/docs/` 中的产品级开发要求迁入 Trellis，未来仍会出现“双入口”。
* 当前 `.trellis/spec/` 需要从“模板集合”升级为“真实规范入口”，否则 Trellis 无法成为主入口。
* 未来规范首先要服务 `coding-deepgent`，而不是继续为整个教学外壳提供等权主入口。

### Current classification draft

**Mainline / should stay first-class**

* `.trellis/`
* `coding-deepgent/`
* `coding-deepgent/tests/`

**Reference-only by default**

* `agents/`
* `agents_deepagents/`
* `docs/`
* `web/`
* root tutorial/reference tests under `tests/`, especially:
  * `test_agents_*`
  * `test_deepagents_*`
  * `test_s02_*`
  * `test_s03_*`
  * `test_s04_*`
  * `test_s06_*`
  * `test_stage_track_*`
  * `test_s_full_background.py`

**High-priority duplicate / misleading candidates**

* `coding-deepgent/docs/cc-alignment-roadmap.md`
  * overlaps with canonical Trellis roadmap/dashboard
* `coding-deepgent/docs/review-checklist.md`
  * overlaps with Trellis quality/review norms
* `coding-deepgent/docs/session-foundation-cc-alignment.md`
  * overlaps with Trellis handoff / session contracts
* root `README*.md`
  * good as repo-level teaching entry, misleading as current product implementation entry
* tutorial chapter docs in `docs/*` that cover current product concepts:
  * `s05-skill-loading.md`
  * `s06-context-compact.md`
  * `s09-memory-system.md`
  * `s10-system-prompt.md`
  * `s12-task-system.md`
  * `s13-background-tasks.md`
  * `s19-mcp-plugin.md`
* generic root skills:
  * `skills/agent-builder/SKILL.md`
  * `skills/code-review/SKILL.md`
  * `skills/mcp-builder/SKILL.md`
  * `skills/pdf/SKILL.md`
  * user-selected for first-batch cleanup

### Feasible approaches here

**Approach A: Trellis-first for `coding-deepgent` governance/specs** (Chosen)

* How it works:
  * 只把 `coding-deepgent` 的“项目协作规范 / 开发要求 / 代码结构约定 / 产品开发契约”迁入 Trellis。
  * 保留 `docs/`、`web/`、`agents*` 作为教程/参考文档，不再承担当前主线开发规范职责。
  * 将 `coding-deepgent/docs/` 中真正属于开发规范的内容迁入 `.trellis/spec/` 或 `.trellis/plans/`。
  * 删除根 `skills/` 与根目录教程测试，避免它们继续伪装成当前主线协作资产。
* Pros:
  * 最符合“以后以 Trellis 为主”的协作目标。
  * 风险可控，不会误删教学主线。
  * 可以真正清理双入口。
* Cons:
  * 仍会保留一部分非 Trellis 文档，用于教学或产品说明。

**Approach B: Trellis as the only global doc center**

* How it works:
  * 将规范、产品说明、教学入口、阶段说明都尽量并入 `.trellis/`。
  * 大幅删除 `docs/`、`coding-deepgent/docs/`、根 README 中的重复内容。
  * 同步移除或重写依赖这些目录的 skill / 测试 / web 数据。
* Pros:
  * 单一入口最彻底。
* Cons:
  * 影响面极大，已经接近“重构整个仓库信息架构”。
  * 会动到教学仓库产品定位，而不只是开发协作规范。

**Approach C: Trellis as index only, old docs mostly retained**

* How it works:
  * 在 Trellis 中增加索引和映射，但不做大规模迁移。
  * 老文档大部分保留，只加“canonical source 在 Trellis”或“see also”。
* Pros:
  * 成本最低，断链风险最低。
* Cons:
  * 不能真正消除双入口和重复维护。
  * 不符合用户“以后都以 trellis 为主”的方向。

## Checkpoint: Trellis Spec Consolidation

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Established `coding-deepgent/` as current mainline and tutorial/reference layer as reference-only by default.
* Migrated mainline governance into Trellis docs.
* Removed duplicated `coding-deepgent/docs/*` governance docs.
* Removed root tutorial `skills/`, root tutorial tests, and `live_tests/` as first-batch cleanup.
* Added/updated Trellis guides and backend specs for mainline scope, doc map, interview expansion, cc alignment, staged execution, LangChain-native implementation, quality, persistence, error handling, and logging.
* Added Trellis link checker.
* Split oversized runtime/compact contract into focused backend contract files.

Verification:

* `python3 ./.trellis/scripts/check_trellis_links.py` passed.
* Focused `coding-deepgent` skill/plugin tests passed earlier after root `skills/` removal.
* Scanned current Trellis specs/plans for stale root tutorial paths and removed-skill references.

Decision:

* terminal for this consolidation task family. Archive after human review/commit according to Trellis workflow.
