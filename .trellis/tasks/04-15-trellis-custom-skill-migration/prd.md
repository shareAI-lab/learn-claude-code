# brainstorm: migrate custom project skills into trellis and remove them

## Goal

将当前 `coding-deepgent` 主线工作所依赖的“项目定制 skill”能力迁移到 `.trellis/` 的正式规范与工作流文档中，使后续协作默认依赖 Trellis 文档而不是额外 skill；迁移完成后删除这些已被吸收的 skill 文件与入口，保留 Trellis 官方工作流 skill。

## What I already know

* 用户希望以后以 Trellis 能力为主，而不是继续依赖额外 skill。
* 用户明确要求：
  * 最终目标是把这些 skill 的能力迁移进对应 Trellis 文档
  * 迁移完成后删除相关 skill
  * `record-session` 不要动
* 当前候选目标 skill 是：
  * `/root/.codex/skills/cc-haha-alignment/SKILL.md`
  * `/root/.codex/skills/langchain-architecture-guard/SKILL.md`
  * `.agents/skills/stage-iterate/SKILL.md`
  * `.agents/skills/project-handoff/SKILL.md`
* 这些 skill 当前承担的高价值能力分别是：
  * `cc-haha-alignment`
    * expected effect 先行
    * source-backed alignment matrix
    * `align / partial / defer / do-not-copy` 决策记录
  * `langchain-architecture-guard`
    * 最小 LangChain/LangGraph 抽象
    * strict schema / middleware / state / prompt / tool 边界
    * 避免 fallback parser / 伪架构包装
  * `stage-iterate`
    * staged run / checkpoint gate
    * `continue / adjust / split / stop`
    * `lean / deep` 验证预算
  * `project-handoff`
    * 新会话最小 resume 读取顺序
    * 当前主线 handoff 入口
* 当前 Trellis 已经部分覆盖这些能力：
  * `.trellis/project-handoff.md`
  * `.trellis/workflow.md`
  * `.trellis/spec/backend/index.md`
  * `.trellis/spec/backend/directory-structure.md`
  * `.trellis/spec/backend/quality-guidelines.md`
  * `.trellis/spec/guides/mainline-scope-guide.md`
  * 多个主线任务 PRD 已经直接内联 `cc-haha alignment` / `LangChain guard` / checkpoint 结构

## Assumptions (temporary)

* 这次迁移只处理“项目定制增强 skill”，不处理 Trellis 官方工作流 skill。
* `.agents/skills/record-session/SKILL.md` 明确排除在删除范围外。
* 如果某个 skill 的能力已经被 Trellis 原生文档或脚本完全承接，就应优先删除 skill 壳而不是继续双维护。
* 如果某个 skill 仍有独特硬约束，则先迁规则，再删 skill。

## Open Questions

* None after current scope confirmation, unless迁移过程中发现 `project-handoff` 中仍有无法自然落进 Trellis 文档的特殊步骤。

## Requirements (evolving)

* 明确哪些 skill 属于“项目定制 skill”，哪些属于 Trellis 官方工作流 skill。
* 只迁移并删除项目定制 skill，不动 Trellis 官方工作流 skill。
* 为每个目标 skill 建立 Trellis 落点映射：
  * 哪些规则进 `.trellis/workflow.md`
  * 哪些规则进 `.trellis/spec/backend/*.md`
  * 哪些规则进 `.trellis/spec/guides/*.md`
  * 哪些规则进 `.trellis/project-handoff.md`
* 迁移后，Trellis 文档应能独立承担这些 skill 原先提供的关键约束。
* 删除已迁移的目标 skill 文件与相关入口引用。
* 显式保留：
  * `.agents/skills/record-session/SKILL.md`
  * 其他 Trellis 官方工作流骨架 skill，除非后续另有明确指令

## Acceptance Criteria (evolving)

* [ ] 有一份 source-backed 映射，说明每个目标 skill 的规则迁移到了哪些 Trellis 文档。
* [ ] `cc-haha-alignment` 的关键护栏已写入 Trellis，而不是仅存在 skill 中。
* [ ] `langchain-architecture-guard` 的关键护栏已写入 Trellis backend 规范。
* [ ] `stage-iterate` 的 checkpoint / validation-budget 规则已写入 Trellis workflow 或 guide。
* [ ] `project-handoff` 的最小 resume 读取规则已由 Trellis 文档承接。
* [ ] 目标 skill 文件已删除。
* [ ] `record-session` 未被修改或删除。

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky
* Any path or prompt references to removed skills are updated
* Remaining Trellis workflow still reads coherently for a new session

## Out of Scope (explicit)

* 删除 `record-session`
* 删除 Trellis 官方工作流骨架 skill 的整套体系
* 重写 `coding-deepgent` 产品功能代码，除非为修复 skill 删除后的引用断链所必需
* 处理根 `skills/` 教学资产之外的其他教程层重构工作

## Technical Notes

* New child task:
  * `.trellis/tasks/04-15-trellis-custom-skill-migration`
* Parent task:
  * `.trellis/tasks/04-15-trellis-spec-consolidation`
* Candidate target docs:
  * `.trellis/workflow.md`
  * `.trellis/project-handoff.md`
  * `.trellis/spec/backend/index.md`
  * `.trellis/spec/backend/directory-structure.md`
  * `.trellis/spec/backend/quality-guidelines.md`
  * `.trellis/spec/guides/index.md`
  * new Trellis guide(s) if existing docs are not a clean fit

## Research Notes

### Feasible Trellis landing map

**`cc-haha-alignment`**

Recommended landing:

* new `.trellis/spec/guides/cc-alignment-guide.md`
* references from `.trellis/workflow.md`
* optional cross-link from backend index

Why:

* this is mostly a pre-implementation reasoning/decision discipline
* it includes expected effect, source mapping, matrix, and do-not-copy rules

**`langchain-architecture-guard`**

Recommended landing:

* `.trellis/spec/backend/directory-structure.md`
* `.trellis/spec/backend/quality-guidelines.md`
* optional new backend guideline if strict tool/schema guidance becomes too dense

Why:

* most rules are implementation constraints, not session workflow
* they directly govern tool schemas, middleware, state, prompt placement, and modularity

**`stage-iterate`**

Recommended landing:

* `.trellis/workflow.md`
* optional new `.trellis/spec/guides/staged-execution-guide.md`

Why:

* it is a work-execution protocol: sub-stage progression, checkpoint gate, lean/deep validation budget

**`project-handoff`**

Recommended landing:

* `.trellis/project-handoff.md`
* `.trellis/workflow.md`

Why:

* it is already close to Trellis-native behavior
* most of its value is canonical resume order and minimal refresh commands

### Deletion boundary

Delete after migration:

* `/root/.codex/skills/cc-haha-alignment/SKILL.md`
* `/root/.codex/skills/langchain-architecture-guard/SKILL.md`
* `.agents/skills/stage-iterate/SKILL.md`
* `.agents/skills/project-handoff/SKILL.md`

Do not delete:

* `.agents/skills/record-session/SKILL.md`

### Implementation posture

Recommended execution order:

1. migrate `project-handoff`
2. migrate `stage-iterate`
3. migrate `cc-haha-alignment`
4. migrate `langchain-architecture-guard`
5. remove target skill files
6. update references and re-read Trellis entry docs for coherence
