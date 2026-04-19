# brainstorm: cc highlight alignment discussion

## Goal

逐一讨论 `coding-deepgent` 与 cc-haha / Claude Code 的核心亮点对齐情况，优先识别当前实现里“名字看似对齐但功能/架构/长期规范没对上”的高价值差距，并形成后续可执行的讨论与实施顺序。

## What I already know

* 用户已经讨论过上下文压缩模块，并发现存在不少未对齐亮点。
* 用户当前不希望先抽象讨论“底层设施需要哪些功能”，因为这会变成凭空设计。
* 用户希望先对齐 cc 具体有哪些亮点，再从亮点反推 `coding-deepgent` 需要哪些底层设施。
* 用户提供了工具系统五要素协议、dead-code elimination、concurrency partitioning、StreamingToolExecutor、类型契约/渐进式扩展等关键亮点。
* 用户倾向先把后续亮点计划细节定清楚，再做一次高耦合集成实现，而不是边讨论边零碎实现。
* 用户计划后续实现并发分区 / 工具编排引擎。
* 用户判断 Streaming stage 太难，近期不做，只写入文档作为 deferred future capability。
* 补充扫描 cc docs/source 后，工具模块仍有动态 tool pool、deferred ToolSearch、tool_use/tool_result pairing、结果映射/持久化/渲染分离、agent 工具池过滤等亮点需要纳入计划。
* 当前 canonical roadmap 在 `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`，包含 H01-H22。
* 当前 MVP boundary 包含 H01-H11、H15-H19、H12 minimal、H20 minimal。
* H13 Mailbox / SendMessage、H14 Coordinator、H21 Bridge / remote / IDE、H22 Daemon / cron 被明确 deferred 出 MVP。
* 最新基础设施复盘已新增 `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`，要求后续围绕 transcript/session/compact/collapse/runtime pressure/task/subagent/hooks/memory 做项目级 gate。
* 用户确认下一步讨论 H15/H16/H17 Skills / MCP / Plugin extension platform，并要求先基于 cc 文档和源码抽取具体亮点，再对比本地完成/未完成。
* 用户判断 H15/H16/H17 extension platform 不是重点，甚至可以不做完整平台；目标是保底，不影响其他 cc 亮点继续推进。
* 用户确认 H15/H16/H17 收束为 baseline only，下一组进入 H11/H12 Agent-as-tool / Subagent。

## Assumptions (temporary)

* 本轮不是立即实现代码，而是先确定 cc 亮点讨论顺序与每个亮点的对齐审计切入点。
* “亮点没对上”主要指功能效果、运行时边界、LangChain/LangGraph-native 表达、持久化/恢复语义、模型可见面或测试合同没对齐，而不只是代码名字不同。
* 讨论顺序应从用户可感知/cc 可观察的具体亮点出发，而不是从本地 infra taxonomy 出发。

## Open Questions

* MVP agent 催化剂最小集:仅 general + verifier,还是必须预置 explore / plan 占位?
* subagent transcript 持久化边界:同 parent session JSONL(sidechain with parent_id)还是 per-agent 目录?
* subagent result envelope 是否暴露完整 token usage breakdown (cache creation/read 分列) 还是只给 total?
* general subagent 的 max_turns 上限取多少?

## Requirements (evolving)

* 先按 cc 具体亮点聚合 H01-H22，而不是先讨论抽象基础设施。
* 每个亮点先说明“cc 中这个亮点解决什么问题、用户/agent 看到什么效果”，再判断本地需要什么底层设施。
* 每个亮点讨论都需要关注 expected effect、cc source evidence、local target、LangChain primitive、当前差距、是否值得现在做。
* 已讨论过的 context compression 相关内容应作为已知风险，不再只围绕单一 bug。
* 第一轮深入讨论选择 H01/H02：Tool-first capability runtime 与 Permission runtime / hard safety。
* H01/H02 第一轮子主题选择 Shell safety / Bash 权限。
* Shell safety / Bash 权限不作为近期高优先级模块。
* 权限模块目标调整为：简单可用、保留后续 cc 功能扩展边界，不阻塞后续 tool/task/subagent/MCP 亮点。
* 第一阶段不做 classifier、sandbox、interactive permission dialog、复杂 Bash parser 移植。
* 第一阶段应保持 LangChain-native middleware/policy 边界，不引入自定义 query loop。
* H01 后续优先讨论工具控制面，而不是继续深挖低优先级权限模块。
* H01 工具控制面方向确定：把本地 `ToolCapability` / tool metadata 作为五要素协议承载层。
* 五要素协议包括：name、schema、permission、execution、rendering/result。
* 协议扩展维度包括：concurrency、exposure、trust/source、large-output policy、runtime-pressure policy。
* H01 五要素协议已固化到 `.trellis/spec/backend/tool-capability-contracts.md`。
* H01 后续计划加入并发分区 / 工具编排引擎，但应作为独立高级执行层能力，不能破坏 LangChain-native runtime 边界。
* Streaming tool-use execution 不进入近期实现范围，只保留文档约束和未来扩展点。
* H01 工具讨论收尾前应补齐 remaining highlights 清单，避免后续 H15/H16/H11 讨论时遗漏。
* 执行方式：先完成亮点对齐计划、依赖关系和实施切片，再进入实现；高耦合能力优先按集成批次完成。
* H01 工具模块总计划已写入 `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`。
* 推荐下一个讨论模块：H15/H16/H17 Skills / MCP / Plugin extension platform。
* H15/H16/H17 讨论方式：先做 source-backed highlight extraction，再做 local completion/gap matrix。
* H15/H16/H17 策略调整为：只保留 LangChain-native 保底能力，不追求 cc marketplace/install/enable/auth/operation-plane parity。
* H11/H12 讨论方式：先读 cc AgentTool/subagent/runtime source，再对照本地 run_subagent/task/session/runtime 实现。
* H11/H12 source-backed 对齐调研已固化到 `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`,识别 15 组对齐亮点与 gap matrix。
* H11/H12 候选讨论顺序:(1) 真 general-purpose child runtime → (2) AgentDefinition + 催化剂目录 → (3) subagent transcript/metadata 持久化 → (4) 结构化 result envelope → (5) deferred ADR。
* H11/H12 第一步讨论选择 (1) real general-purpose child runtime。
* general-purpose 子 agent 能力边界:**只读研究型**(read_file / glob / grep / task_get / task_list / plan_get),不含 write_file / edit_file / bash / TodoWrite / plan_save 等写工具。理由:与 cc explore/plan 对齐;避免把 H02 permission 投影复杂度拉进当前切片;契合 subagent_spawn_pressure_guard "缓解 parent context 压力" 的定位。未来 write-capable 子 agent 走独立 coder 类型加入目录。
* MVP built-in agent 催化剂最小集:**general + verifier**。理由:cc 的 explore/plan 本身在 feature flag 背后;AgentDefinition 结构就位后加 explore/plan/coder 是"填表"而非"改架构";避免占位驱动实现。statusline-setup / claude-code-guide 是 cc-TUI 专属场景,LangChain-native mainline 判 do-not-copy。
* subagent transcript 持久化:**sidechain 写回 parent session JSONL**,增加 `parent_message_id` / `subagent_thread_id` 字段,与 cc recordSidechainTranscript 语义一致;不单独开 per-agent 目录。理由:与 H06 JsonlSessionStore thread-keyed 结构一致;H05 compact / H19 evidence 查询只需扫单份 JSONL;subagent resume 目前 deferred,暂无需 per-agent 指针优化。
* subagent result envelope usage 粒度:**minimal**(input_tokens / output_tokens / total_tokens / total_duration_ms / total_tool_use_count)。不含 cache_creation / cache_read / service_tier / server_tool_use。理由:与 H20 minimal 边界一致;LangChain UsageMetadata 对 provider-specific cache 字段覆盖不完整,强拉会引入 adapter 层;未来扩展只加字段不改消费者。
* subagent max_turns:**general=25 / verifier=5**,通过 AgentDefinition 字段声明,不硬编码。理由:研究型任务典型 5-15 轮 tool call,25 给 2x 余量;verifier 只做读计划+读证据+verdict 三步,5 轮够;远低于 cc FORK_AGENT 200 是有意的——subagent_spawn_pressure_guard 已控制 parent 侧压力,无需让子 agent 消耗同规模上下文,天然约束任务粒度保持细。未来 coder 类型可声明更高上限。
* H19 source-backed 调研已固化到 `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`,识别 6 大类对齐亮点与 gap matrix。
* H19 dashboard 状态从 `implemented` 降级为 `implemented-minimal`,需 Stage 28 closeout(本就预留给 H19/H20 的 stage)。
* H19 closeout 必做项:**A1** queued-until-sink event sink / **B2** auto_compact 拆 attempted+succeeded / **B3** post_autocompact_turn canary(四指标全记:pre_compact_total, post_compact_total, new_turn_input, new_turn_output)/ **B4** orphan_tombstoned 事件 / **B6** 结构化 query_error runtime event / **B8** per-turn token_budget 事件 / **C1** dev-mode API dump(env-only,`CODING_DEEPGENT_DUMP_PROMPTS=1`)/ **E1** agent-scoped debug logger 约定。
* H19 明确 deferred(进 ADR):analytics backend 系(A2-A6)、Perfetto 层级追踪(D1-D6)、SDK progress + TTFT(E2-E3)、cache_eviction_hint(B10)、streaming 事件(B9)、attachment 边界(B1)。
* H19 deferred ADR 一次性与 H11/H12 deferred ADR 合并为 Stage 29 产出物,不单独拆文件。

## Acceptance Criteria (evolving)

* [x] 给出当前几大对齐亮点分组。
* [x] 给出推荐优先讨论顺序和理由。
* [x] 用户选择第一组后，进入一组一组的 source-backed 对齐讨论。
* [x] H01 工具模块总计划已固化为 Trellis plan。

## Definition of Done (team quality bar)

* 形成明确讨论顺序。
* 每组讨论结论能落到 PRD/plan/spec，而不是停留在口头判断。
* 若后续进入实现，必须按 Trellis task workflow 配置相关 spec context。

## Out of Scope (explicit)

* 本轮不直接修改 `coding-deepgent` 代码。
* 不做 H01-H22 的逐项完整源代码审计，除非用户选定具体亮点组。
* 不重新打开已 deferred 的远程/daemon 类能力，除非用户明确调整产品边界。
* 不在每个亮点刚讨论完时立即实现零散 patch。

## Technical Notes

* Canonical roadmap: `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* H01 tool plan: `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* Infra gate: `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* 当前建议优先围绕高耦合基础设施组讨论，而不是按 roadmap 编号线性推进。
* 2026-04-16 用户选择从工具与权限体验开始讨论。
* 2026-04-17 用户确认下一组讨论 H15/H16/H17 extension platform。
* 2026-04-17 用户确认 H15/H16/H17 baseline only，下一组讨论 H11/H12 Agent-as-tool / Subagent。

## Research Notes: H01/H02 Tool And Permission

### cc-haha source points inspected

* `/root/claude-code-haha/src/Tool.ts`
  * `ToolPermissionContext`
  * `ToolUseContext`
  * `Tool`
  * `ToolDef`
  * `buildTool`
* `/root/claude-code-haha/src/services/tools/toolOrchestration.ts`
  * `runTools`
  * `partitionToolCalls`
  * `runToolsSerially`
  * `runToolsConcurrently`
* `/root/claude-code-haha/src/services/tools/toolExecution.ts`
  * `runToolUse`
  * `checkPermissionsAndCallTool`
  * schema validation, tool validation, progress, hooks, result mapping
* `/root/claude-code-haha/src/hooks/useCanUseTool.tsx`
  * `CanUseToolFn`
  * permission decision routing: allow / deny / ask / classifier / interactive / coordinator / swarm worker
* `/root/claude-code-haha/src/types/permissions.ts`
  * `PermissionMode`
  * `PermissionBehavior`
  * `PermissionRule`
  * `PermissionResult`
  * `PermissionUpdate`
* `/root/claude-code-haha/src/utils/permissions/permissions.ts`
  * rule loading/matching
  * permission request message
  * permission update/persistence
* `/root/claude-code-haha/src/tools/BashTool/bashPermissions.ts`
* `/root/claude-code-haha/src/tools/BashTool/bashSecurity.ts`
* `/root/claude-code-haha/src/tools/BashTool/readOnlyValidation.ts`
* `/root/claude-code-haha/src/tools/ToolSearchTool/ToolSearchTool.ts`
* `/root/claude-code-haha/src/tools/ToolSearchTool/prompt.ts`

### Local source points inspected

* `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `coding-deepgent/src/coding_deepgent/tool_system/policy.py`
* `coding-deepgent/src/coding_deepgent/permissions/manager.py`
* `coding-deepgent/src/coding_deepgent/permissions/rules.py`
* `coding-deepgent/src/coding_deepgent/filesystem/policy.py`
* `coding-deepgent/src/coding_deepgent/filesystem/service.py`
* `coding-deepgent/src/coding_deepgent/filesystem/tools.py`

### First-pass cc亮点拆分

| Sub-highlight | cc expected effect | Local current shape | First-pass status |
|---|---|---|---|
| Tool definition as rich capability object | 每个工具不仅有 schema，还有 read-only/destructive/concurrency/search/defer/result/render/permission hooks 等运行时语义 | `ToolCapability` 保存 read_only/destructive/concurrency/source/trust/exposure/persist_large_output 等元数据 | partial |
| Strict schema and tool-local validation | schema parse fail、tool-local validate fail 都回到模型可理解的 tool_result error | Pydantic `args_schema` 严格，部分 tool 有 service-level validation | partial |
| Tool execution lifecycle | unknown tool、schema validation、permission、pre/post hooks、progress、call、result mapping、storage、telemetry 串成生命周期 | `ToolGuardMiddleware.wrap_tool_call` 覆盖 permission/hook/result storage/event；LangChain owns schema/call path | partial / LangChain-native |
| Concurrency partitioning | read/concurrency-safe 工具可并发，非安全工具串行，context modifiers 之后合并 | 本地 capability 有 `concurrency_safe`，但未发现主 agent 显式 partition tool calls；依赖 LangChain runtime | possible gap |
| Deferred tool discovery | 大量/MCP/低频工具可 deferred，模型先用 ToolSearch 拉 schema | 本地有 exposure `main`/`child_only`，MCP local loading；未发现 ToolSearch-style deferred schema discovery | likely gap / maybe deferred |
| Permission modes | default/plan/acceptEdits/bypassPermissions/dontAsk/auto/bubble 等模式影响工具行为 | 本地有 default/plan/acceptEdits/bypassPermissions/dontAsk，无 auto/bubble | partial |
| Permission rule model | allow/deny/ask rules 有来源、持久化目标、tool/content 匹配、MCP server/tool 粒度 | 本地有 `PermissionRuleSpec` 和 allow/ask/deny settings rules，source/domain/trust matching 较小 | partial |
| Tool-specific permission | 通用权限后还有 tool.checkPermissions，例如 Bash/PowerShell 的命令级解析、安全、suggestions | 本地 permission 主要由 capability + generic manager + simple filesystem command/path policy 处理 | major gap for shell |
| Interactive/worker/coordinator permission resolution | ask 不只是返回错误；可走 interactive prompt、worker auto-deny、coordinator automated check/classifier | 本地 `ask` 在 middleware 中转为 error ToolMessage，没有交互批准状态机 | gap by current MVP boundary |
| Hard shell safety | Bash/PowerShell 有复杂解析、危险模式、read-only allowlist、path/sed/git/sandbox/classifier | 本地 `command_policy` 是字符串黑名单，read-only bash 是简单 shlex + token check | major gap |
| Hook integration | PreToolUse/PostToolUse/PermissionDenied 可以 block、add context、modify MCP output、record attachments | 本地支持 PreToolUse/PostToolUse/PermissionDenied block 和 evidence，context/update 能力较小 | partial |
| Tool result persistence / projection | 大输出落盘、返回 preview/path，参与后续 compact/restoration | 本地已实现 large output persistence contract | aligned for local slice |

### Discussion implication

H01/H02 不应该被讨论成“我们是否有工具 registry 和 permission manager”。更准确的问题是：

* cc 里的工具控制面哪些效果对 `coding-deepgent` 是核心？
* 哪些属于 LangChain 已经替我们托管的 runtime 行为？
* 哪些必须产品本地补齐，例如 shell safety、ToolSearch/deferred tools、permission ask state machine、concurrency partitioning？
* 哪些是 UI/remote/coordinator 相关，当前应继续 deferred？

## User-provided H01 Key Points

用户提供的 cc 工具系统亮点：

* 五要素协议是工具系统的 DNA：名称、Schema、权限、执行、渲染。
* `buildTool` 默认值机制让简单工具只关注核心逻辑，设计哲学是“显式声明，安全默认”。
* dead-code elimination 通过环境变量和功能开关条件导入，避免内部工具泄漏到外部构建。
* `isConcurrencySafe` 决定工具能否并发执行；正确标记只读工具可减少响应时间，错误标记会引入数据竞争。
* `StreamingToolExecutor` 在模型生成 `tool_use` 块时就开始执行工具，通过状态机和顺序保证兼顾并行性与一致性。
* `Tool<Input, Output, Progress>` 泛型和 `ToolUseContext` 让工具具备独立类型空间和统一执行环境，添加新工具无需修改编排引擎。

### Fit Assessment

| Key point | Fits cc highlight? | Local adoption judgment |
|---|---|---|
| 五要素协议：名称/Schema/权限/执行/渲染 | Yes, H01 core | Should adopt as design vocabulary, but map rendering to local CLI/model-visible result boundaries rather than React UI. |
| `buildTool` 默认值 / 显式声明 / 安全默认 | Yes, H01 core | Should adopt conceptually. In LangChain, use strict `@tool` schemas plus `ToolCapability` defaults that are safe unless explicitly marked read-only/concurrency-safe/etc. |
| Dead-code elimination | Yes for cc multi-product builds | Do not copy Bun/DCE mechanics now. Adopt feature-gated registration/source validation for plugins/MCP/internal tools when product needs it. |
| Concurrency partitioning | Yes, H01 performance/safety | Important future gap. Local metadata exists, but execution is currently delegated to LangChain; need research before adding custom orchestration. |
| StreamingToolExecutor | Yes, cc runtime highlight | Do not copy directly unless LangChain cannot provide equivalent streaming hooks. Current product should preserve LangChain runtime and only add an adapter if concrete latency need appears. |
| Generic Tool type / ToolUseContext | Yes, H01 extensibility | Adopt via local typed domain schemas, `RuntimeContext`, `ToolCapability`, and middleware seams rather than recreating cc TS `Tool` interface. |

### Current local mapping

* Name: LangChain tool name + `ToolCapability.name`
* Schema: Pydantic `args_schema` + `tool_call_schema` tests
* Permission: `ToolGuardMiddleware` + `ToolPolicy` + `PermissionManager`
* Execution: LangChain `create_agent` / tool node, domain `tools.py`, `Command(update=...)`
* Rendering/result: `ToolMessage`, `Command(update={"messages": [...]})`, CLI renderers, large-output preview persistence

### First-principles conclusion

这些点符合 cc 的亮点，但不能逐字照搬。`coding-deepgent` 应该模仿的是协议和边界：

* 每个工具显式声明五要素。
* 默认不假设工具安全、只读、可并发、可压缩、可暴露。
* 编排层只读取工具声明，不写死具体工具。
* LangChain 负责基础 tool execution；本地只补 cc 需要但 LangChain 没表达的 metadata、policy、projection、evidence、rendering。

不应模仿的是：

* React UI rendering surface。
* Bun feature/DCE 细节。
* 自建 query/tool streaming loop，除非证明 LangChain runtime 无法满足 latency/order/cancellation 需求。

## Decision (ADR-lite): H01 Tool Capability Protocol

**Context**: cc 的 `Tool<Input, Output, Progress>` 和 `buildTool` 体现的是工具五要素协议与安全默认，而 `coding-deepgent` 当前已有 `ToolCapability`、strict Pydantic tools、middleware、large-output policy 和 runtime-pressure metadata，但协议还没有被明确命名为后续工具扩展的统一 contract。

**Decision**: H01 后续按“五要素协议”讨论和收敛：每个工具都必须能被描述为 name、schema、permission、execution、rendering/result 五个维度；额外 capability metadata 用于 concurrency、exposure、trust/source、large-output、runtime-pressure 等 cross-cutting 行为。实现上不复制 cc TS `Tool` 接口，不复制 React rendering，不自建 streaming tool executor，优先通过 LangChain tool + middleware + `ToolCapability` 表达。

**Consequences**:

* 后续新增 skill/MCP/plugin/subagent/task tools 时，必须先声明五要素和扩展 metadata。
* 默认值必须保守：未显式声明 read-only/concurrency-safe/trusted/persist/microcompact 的工具不得默认获得这些能力。
* 若需要 streaming/concurrency optimization，应先证明 LangChain runtime 不足，再增加 adapter；不得直接引入 custom query loop。
* H01 的下一步讨论重点应是协议字段、默认值、测试合同和 spec 固化，而不是权限深挖。

## Decision (ADR-lite): Planning Before Integrated Implementation

**Context**: cc 亮点之间高度耦合。工具协议会影响 task/subagent/MCP/skills，session/context 会影响 memory/subagent/verification。如果边讨论边零碎实现，容易在后续亮点出现时推翻前面的局部设计。

**Decision**: 先完成亮点级计划细节：每个亮点的 expected effect、local target、依赖、是否立即实现、是否 deferred、对应 spec/test contract。计划收敛后，再按高耦合能力包做集成实现，而不是每个亮点单独小修。

**Consequences**:

* 可以一次性处理互相依赖的底层 seam，减少返工。
* 不要求一次实现 H01-H22 全部；应按能力包拆分，例如 H01/H15/H16/H11 可能共享 tool capability protocol。
* 每个集成批次开始前仍需要明确 PRD、spec context、验证范围和 stop/split 条件。

## Planned Capability: Concurrent Tool Partitioning / Tool Orchestration Engine

### Expected Effect

当模型在同一轮产生多个 tool call 时，系统能够根据 `ToolCapability.concurrency_safe` 和 mutation/trust metadata 做确定性调度：

* read/search 类安全工具可以并发执行
* workspace/store/state mutation 工具必须串行或独占执行
* 结果输出顺序保持与 tool call 顺序一致
* sibling tool 失败、用户中断、streaming fallback 等情况有明确取消/错误传播规则
* 编排层不写死具体工具名，只消费 capability metadata

### cc Source Anchor

* `/root/claude-code-haha/src/services/tools/toolOrchestration.ts`
  * `partitionToolCalls`
  * `runTools`
  * `runToolsSerially`
  * `runToolsConcurrently`
* `/root/claude-code-haha/src/services/tools/StreamingToolExecutor.ts`
  * queued/executing/completed/yielded 状态
  * safe tools parallel, unsafe tools exclusive
  * buffered ordered result emission
  * sibling error / user interrupt / streaming fallback cancellation

### Local Target

近期目标不是复制 cc 的完整 `StreamingToolExecutor`，而是先设计一个 LangChain-native compatible orchestration boundary：

* 保留 `create_agent` / middleware / `ToolRuntime` 作为主 runtime。
* 先确认 LangChain 当前 tool execution 是否已有并发和顺序保证；不能重复造轮子。
* 如果 LangChain runtime 不暴露足够控制点，再设计薄 adapter。
* adapter 必须继续走 `ToolGuardMiddleware`、permission、hooks、large-output persistence、evidence。

### Difficulty

Difficulty: High

原因：

* 它不是普通工具函数，而是会影响 tool execution ordering、middleware 调用时机、state mutation、error propagation、streaming output、tool result message pairing。
* 如果绕开 LangChain tool node，很容易变成 custom query loop，违反项目长期规范。
* 并发安全需要依赖准确 metadata；metadata 错误会导致真实数据竞争。
* 测试必须覆盖顺序、并发、失败、取消、state mutation、Command(update)、large-output、hooks/evidence 等组合。

### Suggested Staging

1. Spec stage:
   * 定义并发分区合同、状态机、顺序保证、失败/取消语义。
   * 明确哪些能力依赖 LangChain runtime，哪些能力需要本地 adapter。
2. Research spike:
   * 验证 LangChain `create_agent` / tool node 对 parallel tool calls 的现有行为。
   * 判断是否能通过 middleware/config 实现，而不是自建 executor。
3. Minimal adapter stage:
   * 只支持非 streaming 的 batch partition：safe 并发、unsafe 串行、结果按原顺序返回。
   * 不先做模型边生成边执行。
4. Deferred documentation stage:
   * Streaming tool-use execution 只写入文档，不进入近期实现。
   * 文档保留未来约束：并发分区设计不得封死边生成 tool call 边执行、progress、cancellation、ordered yield 的可能性。
   * 只有在未来出现明确低延迟需求、并证明 LangChain 无法满足时，才重新打开 streaming tool-use execution。

### Out of Scope For First Implementation

* 不复制 cc React/UI progress rendering。
* 不实现 streaming tool-use execution。
* 不支持完整 streaming fallback。
* 不先支持 background shell task lifecycle。
* 不绕过 `ToolGuardMiddleware`、permission、hooks、large-output persistence。

### Deferred Streaming Note

cc 的 `StreamingToolExecutor` 是真实亮点，但当前不进入 `coding-deepgent`
近期实现。原因：

* 需要接管模型流式输出中的 partial `tool_use` lifecycle。
* 会影响 tool result ordering、progress、interrupt、sibling cancellation、
  fallback discard 和 error synthesis。
* 如果实现不慎，极易绕过 LangChain 官方 tool runtime 和 middleware。

近期只要求：

* spec 中记录 streaming 是 future capability。
* batch/concurrency adapter 不得写死成无法扩展到 streaming。
* 不因 deferred streaming 而阻塞五要素协议、capability metadata、非
  streaming 并发分区的计划。

## Remaining H01 Tool Highlights From cc Source/Docs

### Source / docs reviewed

* `/root/claude-code-haha/docs/must-read/01-execution-engine.md`
* `/root/claude-code-haha/docs/modules/01-execution-engine-deep-dive.md`
* `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`
* `/root/claude-code-haha/docs/modules/03-prompt-context-memory-deep-dive.md`
* `/root/claude-code-haha/src/tools.ts`
* `/root/claude-code-haha/src/constants/tools.ts`
* `/root/claude-code-haha/src/utils/embeddedTools.ts`
* `/root/claude-code-haha/src/utils/groupToolUses.ts`
* `/root/claude-code-haha/src/utils/toolResultStorage.ts`
* `/root/claude-code-haha/src/services/api/claude.ts`
* `/root/claude-code-haha/src/services/api/errors.ts`

### Remaining highlights

| Highlight | cc expected effect | Local planning judgment |
|---|---|---|
| Dynamic tool pool | 可见工具不是常量；会随 permission、plan/agent mode、MCP connect、deferred discovery 改变 | Important. Should be discussed before H15/H16/H11. |
| ToolSearch / deferred schema loading | 大量/MCP/低频工具先只暴露名字，按需加载完整 schema，降低 prompt/cache 压力 | Important but can stage after five-factor protocol. |
| Tool pool filtering by agent role | async agent/coordinator/teammate 有不同 allowed/disallowed tool sets，防递归和越权 | Important for H11/H13/H14. |
| Tool use/result pairing invariant | `tool_result.tool_use_id` 必须严格对应 `tool_use.id`；resume/compact/API error recovery 都要维护 | Already partially covered by compact specs; should be made H01 invariant too. |
| Pairing repair / synthetic errors | orphaned tool_use/tool_result、duplicate IDs、streaming fallback 需要协议正确的 synthetic result | Future execution-engine hardening; not first H01 implementation. |
| Tool result mapping vs UI rendering | model-facing `mapToolResult...`、transcript rendering、search text、group rendering 是不同 surface | Local should map this to ToolMessage/CLI/evidence, not React UI. |
| Grouped tool rendering | 同一 assistant message 中多个同类 tool use 可分组显示，减少 UI 噪音 | UI/renderer enhancement; not blocking infra. |
| Result persistence / preview | 大输出持久化、preview、path restoration、threshold opt-in | Already has local contract; keep tied to ToolCapability. |
| Cache-aware tool schema layout | deferred tools、MCP tools、tool sections 会影响 prompt cache key | Important for future ToolSearch/context work; not immediate implementation. |
| Embedded/replaced search tools | 环境具备 embedded search 时，移除 Glob/Grep 专用工具，避免重复能力 | Product-specific optimization; probably do-not-copy until needed. |
| Dead-code / feature-gated tool registration | ant-only/internal/proactive/cron/remote tools 条件装载，防泄漏 | Keep as extension/source validation principle; do not copy Bun DCE. |
| Tool failure remains protocol-correct | validation/permission/MCP auth/abort/fallback failures都转成模型可消费 tool_result | Important. Local middleware/errors should continue improving around this. |

### H01 closeout recommendation

H01 工具模块可以在计划层收束为四个 buckets：

1. Tool capability protocol:
   * five-factor protocol
   * safe defaults
   * metadata-driven middleware/projection
2. Tool visibility and discovery:
   * dynamic tool pool
   * role-based tool filtering
   * future ToolSearch/deferred schema
3. Tool execution correctness:
   * non-streaming concurrency partition
   * strict tool_use/tool_result pairing
   * protocol-correct errors/synthetic results
   * streaming executor deferred
4. Tool result/context pressure:
   * result mapping/rendering separation
   * large-output persistence
   * microcompact eligibility
   * cache-aware schema/layout as future context work

## Research Notes: H15/H16/H17 Extension Platform

### cc-haha source/docs inspected

* `/root/claude-code-haha/docs/must-read/06-extension-platform.md`
* `/root/claude-code-haha/docs/modules/06-extension-platform-deep-dive.md`
* `/root/claude-code-haha/src/tools/SkillTool/SkillTool.ts`
* `/root/claude-code-haha/src/skills/loadSkillsDir.ts`
* `/root/claude-code-haha/src/skills/bundledSkills.ts`
* `/root/claude-code-haha/src/skills/mcpSkillBuilders.ts`
* `/root/claude-code-haha/src/services/mcp/config.ts`
* `/root/claude-code-haha/src/services/mcp/client.ts`
* `/root/claude-code-haha/src/services/mcp/types.ts`
* `/root/claude-code-haha/src/services/mcp/normalization.ts`
* `/root/claude-code-haha/src/utils/plugins/schemas.ts`
* `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`
* `/root/claude-code-haha/src/utils/plugins/installedPluginsManager.ts`
* `/root/claude-code-haha/src/utils/plugins/validatePlugin.ts`
* `/root/claude-code-haha/src/utils/hooks/AsyncHookRegistry.ts`
* `/root/claude-code-haha/src/utils/hooks/hookEvents.ts`
* `/root/claude-code-haha/src/utils/hooks/sessionHooks.ts`
* `/root/claude-code-haha/src/utils/hooks/ssrfGuard.ts`

### Local source inspected

* `coding-deepgent/src/coding_deepgent/skills/*`
* `coding-deepgent/src/coding_deepgent/mcp/*`
* `coding-deepgent/src/coding_deepgent/plugins/*`
* `coding-deepgent/src/coding_deepgent/hooks/*`
* `coding-deepgent/src/coding_deepgent/extensions_service.py`
* `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
* `coding-deepgent/src/coding_deepgent/containers/app.py`
* `coding-deepgent/src/coding_deepgent/containers/tool_system.py`
* `coding-deepgent/tests/extensions/test_skills.py`
* `coding-deepgent/tests/extensions/test_mcp.py`
* `coding-deepgent/tests/extensions/test_plugins.py`
* `coding-deepgent/tests/extensions/test_hooks.py`
* `coding-deepgent/tests/tool_system/test_tool_system_registry.py`

### Highlight completion matrix

| ID | Concrete cc highlight | Current local state | Status |
|---|---|---|---|
| H15 | Skill as capability bridge between command system and agent runtime | Local `load_skill` tool reads `skills/<name>/SKILL.md` with strict frontmatter and bounded render | partial |
| H15 | Multi-source skills: bundled, directory, plugin, MCP, remote | Local only supports local directory skills via `load_skill`; no bundled/plugin/MCP/remote skill unification | missing/deferred |
| H15 | Skill metadata: allowed tools, when-to-use, model/effort, hooks, fork/inline context | Local schema only has `name` and `description`; body is text | missing |
| H15 | Forked skill execution | Local `load_skill` only returns content to current model; no forked skill agent | missing/deferred |
| H15 | Bundled skill reference files extracted safely on demand | Not present | missing/deferred |
| H16 | MCP config strict loading | Local `.mcp.json` strict schema supports stdio/http/sse and `type` alias | partial/aligned local slice |
| H16 | Official LangChain MCP adapter seam | Local probes `langchain_mcp_adapters` and loads tools through `MultiServerMCPClient` when available | partial/aligned local slice |
| H16 | MCP tools become capability entries with source/trust metadata | Local maps MCP descriptors to `ToolCapability(source="mcp:<server>", trusted=False, exposure="extension")` | aligned local slice |
| H16 | MCP resources separate from executable tools | Local `MCPResourceRegistry` keeps resources out of tool capabilities | aligned local slice |
| H16 | MCP multi-transport breadth: stdio, sse, http, ws, sdk, proxy | Local supports stdio/http/sse only | partial |
| H16 | MCP auth/OAuth/XAA/channel permissions/elicitation/notifications | Not present | missing/deferred |
| H16 | MCP connection manager and status lifecycle | Local load is synchronous/one-shot at startup; no connection manager/status lifecycle | missing/deferred |
| H16 | MCP name normalization/dedup with plugin/manual precedence | Local has no deep normalization/dedup beyond strict config and duplicate registry names | missing |
| H17 | Local plugin manifest schema | Local `plugin.json` is strict metadata-only with name/description/version/skills/tools/resources | aligned local minimal |
| H17 | Plugin declaration validation against known local tools/skills/resources | Local registry validates declared tools/skills/resources; startup blocks unknown entries | aligned local minimal |
| H17 | Plugin runtime execution/components | Local plugin does not execute code and does not load commands/agents/hooks/output styles | intentionally deferred |
| H17 | Marketplace/source/install/enable three-state model | Not present; local plugin dir only | missing/deferred |
| H17 | installed_plugins.json, versioned cache, cache-only vs full load | Not present | missing/deferred |
| H17 | Plugin trust policy, blocklist, source validation, dependency resolver | Local has strict local identifiers and no runtime code execution; no marketplace/dependency/trust lifecycle | partial/deferred |
| H18 adjacent | Local lifecycle hooks | Local sync `LocalHookRegistry` supports SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/PermissionDenied/PreCompact/PostCompact | partial/aligned local slice |
| H18 adjacent | Async hooks, HTTP hooks, prompt/post-sampling/frontmatter/skill hooks | Not present | missing/deferred |
| H18 adjacent | Hook SSRF guard and timeout/progress events | Not present | missing/deferred |
| Platform ops | `/plugin`, `/mcp`, `/skills` management commands | Not present in current local CLI | missing/deferred |

### First-pass judgment

本地 H15/H16/H17 是 local MVP extension foundation，不是完整 cc extension platform。

完成较好的 local slice:

* Local skill loading as explicit tool.
* Local plugin manifest validation as metadata-only declaration.
* Plugin declarations validated against known local tool/skill/resource surfaces.
* MCP local config loading and official LangChain adapter seam.
* MCP tool -> `ToolCapability` mapping with source/trust/exposure metadata.
* MCP resources kept separate from executable tool capabilities.
* Basic local sync hooks.

主要未完成:

* Plugin platform lifecycle: marketplace/source/install/enable/cache/update.
* MCP connection/auth lifecycle: connection manager, status, OAuth/XAA, channel permissions, notifications.
* Multi-source skill unification and forked skill execution.
* Async/HTTP/frontmatter/skill hooks as programmable middleware.
* User-facing operation plane commands.

### Recommended next discussion focus

建议不要一口气讨论完整 extension platform。下一步应先讨论：

1. **H16 MCP external capability protocol**:
   * 因为它直接消费 H01 `ToolCapability`。
   * 本地已有基础实现，容易判断 near-term 是否补 connection/auth/transport/dedup。
2. 然后讨论 **H15 Skills**:
   * Skill 是否只是 `load_skill` 文本加载，还是要成为多来源/可 fork capability。
3. 最后讨论 **H17 Plugin lifecycle**:
   * 当前 local manifest 已够 MVP；marketplace/install/enable/cache 是更大产品边界。

### Provisional near-term/deferred split

Near-term baseline:

* Keep current local `load_skill` tool as a bounded local skill loader.
* Keep current `.mcp.json` strict config and optional official LangChain MCP adapter seam.
* Keep MCP tool conversion into `ToolCapability` with source/trust/exposure metadata.
* Keep MCP resources separate from executable tools.
* Keep local plugin manifest metadata-only and validate declarations against known tools/skills/resources.
* Keep hooks as local deterministic middleware events; do not expand them into a plugin/runtime platform.
* Use H01 `ToolCapability` contracts as the shared guardrail for all extension-provided tools.

Deferred:

* Marketplace/install/update/cache lifecycle.
* Full MCP auth/OAuth/XAA/channel permissions.
* Remote/HTTP/WebSocket/sdk transports beyond current local slice unless needed.
* Forked skill execution.
* Async/HTTP/frontmatter/skill hooks.
* `/plugin`, `/mcp`, `/skills` operation plane.

## Decision (ADR-lite): Extension Platform Baseline

**Context**: cc 的 H15/H16/H17 extension platform 很大，包含 MCP 多 transport/auth、plugin marketplace/install/cache/enable、multi-source/forked skills、async/HTTP/frontmatter hooks 和操作面命令。用户当前目标不是复制完整平台，而是保证后续工具、subagent、task、context 等 cc 亮点不被扩展层卡住。

**Decision**: H15/H16/H17 近期只做保底。沿用 LangChain/LangGraph-native 工具、中间件、`ToolCapability`、本地 strict schemas 和 source/trust/exposure metadata。完整 plugin marketplace、MCP auth/connection lifecycle、forked skills、async hooks 和操作面命令全部 deferred，除非后续亮点提出具体依赖。

**Consequences**:

* 当前本地实现基本够作为保底 extension layer。
* 后续重点应回到 H11/H12 subagent 或 H08-H10 workflow，而不是继续深挖 extension platform。
* 对 extension-provided capability 的最低要求是：严格 schema、source/trust metadata、permission 经过 `ToolGuardMiddleware`、不绕过 H01 tool capability protocol。
* 如果未来 MCP/plugin 数量或外部能力风险上升，再单独开启 H15/H16/H17 扩展平台任务。

## Research Notes: H11/H12 Agent-as-tool / Subagent

### cc-haha source/docs inspected

* `/root/claude-code-haha/docs/must-read/02-agent-runtime.md`
* `/root/claude-code-haha/docs/modules/02-agent-runtime-deep-dive.md`
* `/root/claude-code-haha/src/tools/AgentTool/AgentTool.tsx`
* `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/forkSubagent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/resumeAgent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemory.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
* `/root/claude-code-haha/src/tasks/LocalAgentTask/LocalAgentTask.tsx`
* `/root/claude-code-haha/src/tools/SendMessageTool/SendMessageTool.ts`
* `/root/claude-code-haha/src/services/AgentSummary/agentSummary.ts`

### Local source/spec inspected

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `coding-deepgent/tests/subagents/test_subagents.py`
* `coding-deepgent/src/coding_deepgent/runtime/context.py`
* `coding-deepgent/src/coding_deepgent/runtime/invocation.py`
* `coding-deepgent/src/coding_deepgent/tasks/*`
* `.trellis/spec/backend/task-workflow-contracts.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`

### Highlight completion matrix

| ID | Concrete cc highlight | Current local state | Status |
|---|---|---|---|
| H11 | Agent is first a tool, so it inherits permission/tool/runtime protocols | Local has `run_subagent` LangChain tool with strict schema and `ToolCapability(execution="child_agent_bridge")` | partial/aligned local slice |
| H11 | AgentTool can launch specialized subagents by agent definition/type | Local supports only `agent_type="general"|"verifier"`; no custom/built-in agent definition loading | partial |
| H11 | Verifier as specialized child agent | Local verifier resolves `PlanArtifact`, uses read-only allowlist, runs a real `create_agent`, returns structured JSON, persists verdict evidence | aligned strong local slice |
| H11 | General subagent as real child runtime | Local general subagent returns synchronous accepted text unless fake factory provided; no real general child `create_agent` path | missing |
| H11 | Role-based child tool allowlists | Local has exact verifier/general allowlists and excludes mutating tools | aligned local slice |
| H11 | Agent has its own runtime invocation/thread identity | Local verifier uses child `thread_id = parent:verifier:<plan_id>` and `entrypoint="run_subagent:verifier"` | partial/aligned |
| H11 | Agent progress/task lifecycle object | cc has `LocalAgentTask` with running/completed/failed/killed/progress/output/notifications; local has no agent task object for subagent lifecycle | missing/deferred |
| H11 | Agent transcript/metadata persistence and resume | cc persists sidechain transcript + metadata and resumes agent; local only persists verifier evidence in parent session, not child transcript/resume | missing/deferred |
| H11 | Background/async agent | cc supports background agent lifecycle; local `max_turns=1` synchronous only | missing/deferred |
| H11/H13 | Mailbox / SendMessage | cc has `SendMessageTool` and pending message queues; local has no mailbox/send-message | deferred out of MVP |
| H12 | Fork subagent inherits parent context/cache-safe prefix | cc fork preserves parent tool_use structure and cache-identical prefix; local has no forked context execution | missing/deferred |
| H12 | Minimal context/thread propagation | Local passes runtime context/config/store into verifier child and records lineage evidence | aligned minimal slice |
| H12 | Spawn guard under runtime pressure | Local has subagent spawn pressure guard using `RuntimeContext.model_context_window_tokens` and evidence | aligned local hardening |
| H12 | Agent memory and snapshots | cc has per-agent memory scopes and snapshot sync; local has no agent-scoped memory beyond global memory/session memory | missing/deferred |
| H12/H20 | Agent summary side-agent | cc periodically forks summarizer for progress; local has no agent summary side-agent | missing/deferred |
| H14 | Coordinator synthesis ownership | cc docs emphasize coordinator must keep synthesis; local coordinator runtime deferred | deferred |

### First-pass judgment

本地 H11/H12 当前不是完整 Agent Runtime，而是：

```text
bounded verifier-as-tool MVP + minimal child runtime propagation
```

完成得较好的部分：

* `run_subagent` 是模型可见工具，符合 Agent-as-tool 的入口原则。
* verifier 是真实 child agent，而不是纯 prompt wrapper。
* verifier 有 durable plan boundary、read-only tool allowlist、child thread id、structured result、session evidence lineage。
* 有 subagent spawn pressure guard，避免在上下文压力过高时继续派生子 agent。

主要缺口：

* general subagent 不是真实 child agent。
* 没有 agent definition registry / built-in agents / custom agents。
* 没有 LocalAgentTask 生命周期对象。
* 没有 child transcript/metadata/resume。
* 没有 background/async execution。
* 没有 mailbox/SendMessage。
* 没有 fork/cache-aware context execution。
* 没有 agent memory/snapshot/summary。

### Near-term vs deferred

Near-term candidates:

* Make `general` subagent a real bounded child agent only if it has a concrete local effect beyond verifier.
* Formalize child runtime contract in spec:
  * child thread id
  * parent lineage
  * tool allowlist
  * evidence boundary
  * spawn guard
* Decide whether `run_subagent` should remain verifier-first or become general-purpose.
* Keep H01 role-based tool projection aligned with subagent needs.

Deferred:

* LocalAgentTask lifecycle.
* Background/async agents.
* Mailbox/SendMessage.
* Coordinator runtime.
* Fork/cache-aware full context cloning.
* Agent memory/snapshot/summary.
* Worktree/remote isolation.

### Key design question

下一步不是“要不要复制 AgentTool”，而是：

```text
coding-deepgent 的近期 subagent 是否只需要 verifier-backed workflow，
还是需要把 general subagent 升级成真实 child agent runtime？
```

如果近期重点是 H08-H10 workflow，那么 verifier-first 足够。
如果近期要支持 H11 product parity，就需要 general child agent + minimal
agent definition/tool projection contract。

## Research Notes: Shell Safety / Bash Permission

### cc-haha shell safety source points inspected

* `/root/claude-code-haha/src/tools/BashTool/BashTool.tsx`
  * strict input schema includes `command`, `description`, timeout/background/sandbox-related fields
  * `isReadOnly(input)` delegates to `checkReadOnlyConstraints`
  * `checkPermissions(input, context)` delegates to `bashToolHasPermission`
  * command execution handles progress, backgrounding, sandbox annotation, persisted output, code indexing hints
* `/root/claude-code-haha/src/tools/BashTool/bashPermissions.ts`
  * `bashToolCheckExactMatchPermission`
  * `bashToolCheckPermission`
  * `checkCommandAndSuggestRules`
  * `filterRulesByContentsMatchingInput`
  * `matchingRulesForInput`
  * `commandHasAnyCd`
  * `isNormalizedGitCommand`
* `/root/claude-code-haha/src/tools/BashTool/bashSecurity.ts`
  * dangerous shell pattern detection including command substitution, zsh expansion, heredoc substitution, dangerous variables, shell metacharacters, jq `system`, git commit substitution, malformed tokens
* `/root/claude-code-haha/src/tools/BashTool/readOnlyValidation.ts`
  * command allowlist with safe flags
  * `isCommandSafeViaFlagParsing`
  * `checkReadOnlyConstraints`
  * git internal path and cwd-change protections
* `/root/claude-code-haha/src/tools/BashTool/pathValidation.ts`
  * per-command path extractors
  * output redirection validation
  * dangerous removal path detection
  * workspace/additional-working-dir checks
  * path-based permission suggestions
* `/root/claude-code-haha/src/tools/BashTool/sedValidation.ts`
  * strict sed read/edit allowlist instead of generic shell allow
* `/root/claude-code-haha/src/tools/BashTool/modeValidation.ts`
  * acceptEdits auto-allow for a narrow filesystem command set
* `/root/claude-code-haha/src/tools/BashTool/shouldUseSandbox.ts`
  * sandbox selection and excluded-command matching

### Local shell safety source points inspected

* `coding-deepgent/src/coding_deepgent/filesystem/policy.py`
  * `DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")`
  * `command_policy(command)`
  * `safe_path(path_str, workdir, additional_workdirs)`
  * `path_policy(...)`
* `coding-deepgent/src/coding_deepgent/permissions/manager.py`
  * `is_read_only_bash(command)` uses `shlex.split`, rejects simple metacharacter tokens, allowlists first word
  * `_hard_safety_decision` calls `command_policy`
  * `_mode_decision` treats read-only bash as allow, write-like bash as ask/deny by mode
* `coding-deepgent/tests/permissions/test_permissions.py`
  * covers simple read-only bash, write-like bash, dangerous substring, mode behavior
* `coding-deepgent/tests/filesystem/test_tools.py`
  * covers runtime-owned workdir and blocking `rm -rf /`

### Shell safety gap map

| cc sub-capability | Local gap | Risk if ignored |
|---|---|---|
| Structured command parsing | local uses `shlex` and string tokens only | shell injection, quoted/operator edge cases, false allow/false ask |
| Read-only command validation | local allows by first word and rejects common operators | cannot distinguish safe flags from unsafe flags or read commands with dangerous forms |
| Path extraction from shell commands | local validates `path` args for path tools, not paths embedded in bash command | `cat ../x`, redirects, `rm -- path`, `find -- path`, `git` cwd cases are not modeled deeply |
| Output redirection handling | only coarse `> /dev/` substring block | file writes via redirection are not part of permission/path logic |
| Deny/ask/allow rule normalization | local content matching is simple substring across args | env/wrapper/compound command bypass or overmatching risk |
| Sed-specific handling | no local sed parser/allowlist | sed read vs edit cannot be safely distinguished |
| Git/cwd safety | no modeled cd+git / internal path protections | sandbox/workspace assumptions can be bypassed in future richer shell runtime |
| Sandbox decision | no sandbox backend in local `run_bash` | current safety must be permission-only; cannot rely on runtime containment |
| Permission suggestions | no rule suggestion output | ask flow cannot teach safe persistent rules |
| Classifier/auto mode | absent | acceptable to defer, but must not claim parity |

### First-pass judgment

本地 shell safety 是 MVP/minimal，不是 cc-aligned hard safety。它适合作为早期 demo guard，但如果后续要承接 subagent、MCP/plugin tools、agent tasks、background shell、workspace trust 或更高权限模式，必须把 Bash 权限单独升级成产品级 domain，而不是继续把逻辑塞进 generic `PermissionManager` 或 `filesystem.policy.command_policy`。

### Feasible approaches

**Approach A: Deterministic shell safety core** (Recommended)

* How it works:
  * 新增/扩展本地 shell safety module，先不做 classifier 和 sandbox。
  * 明确 pipeline：parse-ish tokenize -> deny/ask/allow rules -> dangerous pattern -> path/redirection -> sed/git/read-only -> mode decision。
  * 输出 `PermissionDecision` with reason/code/metadata/suggestions placeholder。
* Pros:
  * 最大化当前安全收益。
  * 不依赖 UI/远程/sandbox。
  * Fits LangChain middleware / local permission policy.
* Cons:
  * 需要复制/移植一部分 shell safety 思维，测试面较大。

**Approach B: Permission ask state machine first**

* How it works:
  * 先把 `ask` 从 error ToolMessage 升级成可恢复/可批准的状态，再逐步补 shell parser。
* Pros:
  * 更接近 cc 用户体验。
  * 后续可支持 session allow rule。
* Cons:
  * 如果 shell safety 仍薄，批准机制可能让危险命令更容易执行。

**Approach C: Keep shell safety minimal until subagent/MCP pressure appears**

* How it works:
  * 当前只记录差距，不实施。
  * 继续靠 permission modes + coarse dangerous command guard。
* Pros:
  * 成本最低。
  * 不会过早实现一套复杂 shell policy。
* Cons:
  * 后续任何工具/agent 扩展都会建立在弱 shell 安全上。
  * “H02 implemented” 的判断会继续偏乐观。

## Decision (ADR-lite): Shell Safety Direction

**Context**: H01/H02 的 cc source review 显示 Bash 权限是多层安全判定管线，而本地当前只有 coarse command blacklist、简单 read-only first-word 判定和 path tools 的 workspace policy。该差距会影响后续 subagent、MCP/plugin tools、task execution、permission mode 和 hooks 的安全基础。

**Decision**: 权限模块优先级下调。近期不追求完整 cc Bash safety parity，只保留简单安全底线和可扩展 policy/middleware seam。后续如 subagent/MCP/task execution 对 shell safety 提出真实压力，再单独启动 deterministic shell safety core。

**Consequences**:

* 本地 H02 不应按“已有 permission manager”乐观判断完全对齐；Shell safety 维持 partial/deferred。
* 当前必须保留 `filesystem` / `permissions` / `tool_system` 的 LangChain-native policy/middleware seam，避免未来重做入口。
* 不引入复杂 Bash parser、classifier、sandbox、ask approval UI、permission suggestion persistence。
* 若后续亮点需要更强 shell safety，按独立任务补 deterministic shell safety core，而不是把复杂逻辑临时塞进 generic `PermissionManager`。

## Final Closeout (2026-04-19)

This brainstorm is complete and should not stay active as a development task.
Its useful outputs have been absorbed into later canonical artifacts and
implementation tasks:

* H01/H02/H11/H12/H19 discussion produced source-backed gap maps and staged
  implementation direction.
* H01 closeout now includes five-factor `ToolCapability`, role projection,
  dynamic/deferred tool discovery, tool pairing/failure coverage, result
  persistence audit, and conditional/spec-only `L5-a`.
* H11/H12 closeout now includes `AgentDefinition`, read-only `general` /
  `verifier`, sidechain transcript audit, explicit fork/fork-resume surfaces,
  and deferred lifecycle tooling.
* H19 closeout now includes queued event sink/logger, compact observability,
  query_error/token_budget/API dump events, and roadmap/dashboard refresh.
* Remaining shell-hardening / coordinator / remote / daemon items are captured
  as deferred or future focused work in the canonical roadmap and deferred ADR.

Future work should open a new focused implementation PRD rather than continuing
this broad highlight-alignment discussion.
