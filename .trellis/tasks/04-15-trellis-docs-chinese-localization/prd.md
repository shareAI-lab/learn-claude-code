# brainstorm: localize trellis docs to chinese

## Goal

制定一个把 `.trellis/` 文档逐步中文化的迁移 PRD，使后续 Trellis 文档主要用简体中文叙述，同时保留英文术语、文件路径、命令、代码标识、task slug、结构化字段和值，避免破坏搜索、自动化和代码契约。

## What I already know

* 用户希望把 Trellis 文档中文化。
* 用户明确要求保留：
  * 英文术语
  * 引用
  * 文件路径
  * 命令
  * 结构字段
* 用户要求先制定迁移 PRD。
* 官方 Trellis `ch07-writing-specs` 指南允许中文项目使用中文，并强调：
  * `index.md` 作为入口
  * 每个 spec 文件专注一个主题
  * 从实际代码/约定提炼
  * spec 持续演进
* 本地 `AGENTS.md` 已写明：
  * Trellis narrative docs may be written in Simplified Chinese
  * commands, file paths, file names, task slugs, branch names, code identifiers, structured fields keep English
* 本地 `.trellis/workflow.md` 已有一致的语言约定。
* 当前 `.trellis/` 里已有多份主线文档：
  * `workflow.md`
  * `project-handoff.md`
  * `plans/`
  * `spec/backend/`
  * `spec/guides/`
  * `spec/frontend/`
  * `workspace/`

## Assumptions (temporary)

* 中文化应该优先处理当前主线高价值文档，而不是一次性翻译所有历史 plan/task。
* `spec/guides/*` 最适合第一批，因为叙述性强、结构清晰、风险低。
* `spec/backend/*` 中的 signatures、test names、code snippets、status values 必须保留英文。
* `plans/*` 有大量历史和 roadmap 状态，应暂缓或单独处理。

## Open Questions

* None for initial PRD draft; default recommendation is phased localization.

## Requirements (evolving)

* 明确中文化范围和排除范围。
* 建立术语/结构保留规则。
* 分批迁移，避免一次性大改导致 review 困难。
* 每批迁移后运行 Trellis link check。
* 迁移后文档不能丢失原有 contract、路径、命令、test references、status vocabulary。

## Acceptance Criteria (evolving)

* [x] PRD 明确哪些 Trellis 文档优先中文化。
* [x] PRD 明确保留英文的内容类型。
* [x] PRD 明确每一批迁移的文件范围。
* [x] PRD 明确验证方式。
* [x] PRD 明确 out-of-scope，避免误改历史/自动化敏感内容。

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Trellis link check passes after each implementation batch
* No path/command/status/code contract is accidentally translated

## Out of Scope (explicit)

* 当前任务不直接批量翻译全部 `.trellis/`
* 不翻译代码块中的命令、签名、路径、测试名
* 不翻译 JSON/YAML keys 或结构化 status values
* 不优先翻译历史任务归档、workspace journal、旧 provenance plan
* 不服务教程/reference 层

## Technical Notes

* New child task:
  * `.trellis/tasks/04-15-trellis-docs-chinese-localization`
* Parent task:
  * `.trellis/tasks/04-15-trellis-spec-consolidation`
* Existing language convention sources:
  * `AGENTS.md`
  * `.trellis/workflow.md`
  * `.trellis/spec/backend/index.md`
  * `.trellis/spec/frontend/index.md`
* Suggested verification:
  * `python3 ./.trellis/scripts/check_trellis_links.py`
  * targeted grep for accidentally translated path/status markers where useful

## Research Notes

### Official / local guidance

Official Trellis guidance permits Chinese for Chinese projects and recommends
topic-focused, concrete, continuously evolving specs.

Local repo guidance already permits Simplified Chinese narrative while keeping
commands, paths, slugs, identifiers, structured fields, and automation keywords
in English.

### Feasible approaches

**Approach A: Phased mainline localization** (Recommended)

How:

* Phase 1: localize `spec/guides/*`
* Phase 2: localize `spec/backend/index.md` and narrative sections in active backend specs
* Phase 3: localize `workflow.md` and `project-handoff.md`
* Phase 4: selectively localize `plans/index.md` and current canonical roadmap summaries
* Leave historical plans/tasks mostly as-is unless actively maintained.

Pros:

* Reviewable.
* Low risk to contracts and automation.
* Aligns with current mainline.

Cons:

* Mixed-language state remains during migration.

**Approach B: Full `.trellis/` localization**

How:

* Translate nearly all Trellis markdown docs in one large pass.

Pros:

* Fast apparent completion.

Cons:

* High risk of corrupting paths, commands, contract examples, and historical provenance.
* Hard to review.

**Approach C: Only future docs in Chinese**

How:

* Leave existing docs as-is; write only new docs in Chinese.

Pros:

* Lowest risk.

Cons:

* Does not satisfy the desire to improve current Trellis readability.

## Decision (ADR-lite)

**Context**: The project is Chinese-led, and local conventions already allow Simplified Chinese narrative. However, many Trellis docs contain code contracts, paths, commands, and status vocabulary that must remain stable.

**Decision**: Prefer Approach A: phased mainline localization.

**Consequences**:

* First implementation batch should target `spec/guides/*`.
* Plans and historical task docs should not be batch-translated until there is a concrete need.
* Every batch must preserve English technical tokens and run link checks.

## Checkpoint: Phase 1 Guides Localization

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Localized `.trellis/spec/guides/*.md` narrative content to Simplified Chinese.
* Preserved English technical tokens, paths, commands, status values, code identifiers, and structured field names.
* Kept guide purposes and routing semantics intact.

Files changed:

* `.trellis/spec/guides/index.md`
* `.trellis/spec/guides/trellis-doc-map-guide.md`
* `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`
* `.trellis/spec/guides/mainline-scope-guide.md`
* `.trellis/spec/guides/cc-alignment-guide.md`
* `.trellis/spec/guides/staged-execution-guide.md`
* `.trellis/spec/guides/cross-layer-thinking-guide.md`
* `.trellis/spec/guides/code-reuse-thinking-guide.md`

Verification:

* `python3 ./.trellis/scripts/check_trellis_links.py` passed.
* Scanned localized guides for old placeholder/template markers and removed-skill references.

Decision:

* terminal for the initial PRD + Phase 1 implementation slice.
