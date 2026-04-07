import type { VersionId } from "@/lib/constants";

type LocalizedText = {
  zh: string;
  en: string;
  ja?: string;
};

export type ArchitectureSliceId =
  | "mainline"
  | "control"
  | "state"
  | "lanes";

export interface ArchitectureItem {
  name: LocalizedText;
  detail: LocalizedText;
  fresh?: boolean;
}

export interface ArchitectureBlueprint {
  summary: LocalizedText;
  slices: Partial<Record<ArchitectureSliceId, ArchitectureItem[]>>;
  records: ArchitectureItem[];
  handoff: LocalizedText[];
}

const l = (zh: string, en: string): LocalizedText => ({ zh, en });

export const ARCHITECTURE_BLUEPRINTS: Record<VersionId, ArchitectureBlueprint> = {
  s01: {
    summary: l(
      "第一章先建立最小闭环：用户输入进入 messages[]，模型决定要不要调工具，结果再回写到同一条循环里。",
      "The first chapter establishes the smallest closed loop: user input enters messages[], the model decides whether to call a tool, and the result flows back into the same loop."
    ),
    slices: {
      mainline: [
        { name: l("Agent Loop", "Agent Loop"), detail: l("每轮都走一次调用模型 -> 处理输出 -> 再决定是否继续。", "Each turn calls the model, handles the output, then decides whether to continue."), fresh: true },
      ],
      state: [
        { name: l("messages[]", "messages[]"), detail: l("所有用户、助手和工具结果都累积在这里。", "User, assistant, and tool result history accumulates here."), fresh: true },
        { name: l("tool_result 回流", "tool_result write-back"), detail: l("真正让 agent 能行动的是工具结果会回到下一轮推理。", "The agent becomes real when tool results return into the next reasoning step."), fresh: true },
      ],
    },
    records: [
      { name: l("LoopState", "LoopState"), detail: l("最小可运行会话状态。", "The smallest runnable session state."), fresh: true },
      { name: l("Assistant Content", "Assistant Content"), detail: l("模型本轮输出。", "The model output for the current turn."), fresh: true },
    ],
    handoff: [
      l("用户消息进入 messages[]", "User message enters messages[]"),
      l("模型产出 tool_use 或文本", "Model emits tool_use or text"),
      l("工具结果回写到下一轮", "Tool result writes back into the next turn"),
    ],
  },
  s02: {
    summary: l(
      "这一章把“会调一个工具”升级成“能稳定路由很多工具”，主循环不变，工具层长出来。",
      "This chapter upgrades one tool call into a stable multi-tool routing layer while keeping the main loop unchanged."
    ),
    slices: {
      mainline: [
        { name: l("稳定主循环", "Stable Main Loop"), detail: l("主循环继续只管模型调用与结果回写。", "The main loop still only owns model calls and write-back."), },
      ],
      control: [
        { name: l("ToolSpec 目录", "ToolSpec Catalog"), detail: l("把工具能力描述给模型看。", "Describes tool capabilities to the model."), fresh: true },
        { name: l("Dispatch Map", "Dispatch Map"), detail: l("按工具名把调用路由到对应 handler。", "Routes a tool call to the correct handler by name."), fresh: true },
      ],
      state: [
        { name: l("tool_input", "tool_input"), detail: l("模型传入的结构化工具参数。", "Structured tool arguments emitted by the model."), fresh: true },
      ],
    },
    records: [
      { name: l("ToolSpec", "ToolSpec"), detail: l("schema + 描述。", "Schema plus description."), fresh: true },
      { name: l("Dispatch Entry", "Dispatch Entry"), detail: l("工具名到函数的映射。", "Mapping from tool name to function."), fresh: true },
    ],
    handoff: [
      l("模型说要调哪个工具", "The model selects a tool"),
      l("dispatch map 找到 handler", "The dispatch map resolves the handler"),
      l("handler 输出 tool_result", "The handler returns a tool_result"),
    ],
  },
  s03: {
    summary: l(
      "第三章把会话内的工作拆解显式化，agent 开始有一块自己的 session planning 状态。",
      "The third chapter makes session planning explicit so the agent gains a dedicated session-planning state."
    ),
    slices: {
      mainline: [
        { name: l("计划先行", "Plan Before Execution"), detail: l("先把大目标拆成当前轮可追踪步骤，再去行动。", "Break the larger goal into trackable steps before acting."), fresh: true },
      ],
      control: [
        { name: l("提醒回路", "Reminder Loop"), detail: l("每轮重新看到当前 todo，避免中途漂移。", "Each turn revisits the current todo list to avoid drift."), fresh: true },
      ],
      state: [
        { name: l("TodoItem", "TodoItem"), detail: l("当前会话里的最小计划单位。", "The smallest planning unit inside one session."), fresh: true },
        { name: l("PlanState", "PlanState"), detail: l("记录有哪些步骤、做到了哪一步。", "Tracks what steps exist and which one is active."), fresh: true },
      ],
    },
    records: [
      { name: l("Todo List", "Todo List"), detail: l("会话级，不持久。", "Session-scoped, not durable."), fresh: true },
    ],
    handoff: [
      l("目标先变成步骤", "The goal becomes steps first"),
      l("当前步骤指导工具选择", "The current step guides tool choice"),
      l("进展再回写计划状态", "Progress writes back into planning state"),
    ],
  },
  s04: {
    summary: l(
      "这里开始把子任务从父上下文中隔离出来，系统第一次有了显式的多循环结构。",
      "This chapter isolates subtasks from the parent context and introduces the first explicit multi-loop structure."
    ),
    slices: {
      mainline: [
        { name: l("父循环", "Parent Loop"), detail: l("保持主线目标和最终整合责任。", "Keeps the main goal and the integration responsibility."), },
        { name: l("子循环", "Child Loop"), detail: l("为子任务提供一份干净上下文。", "Provides a clean context for the subtask."), fresh: true },
      ],
      control: [
        { name: l("委派边界", "Delegation Boundary"), detail: l("什么时候把工作交给子 agent，什么时候留在父循环。", "Defines when work is delegated versus kept in the parent loop."), fresh: true },
      ],
      state: [
        { name: l("Parent messages", "Parent messages"), detail: l("父 agent 的长期上下文。", "The parent agent's long-lived context."), },
        { name: l("Child messages", "Child messages"), detail: l("子任务一次性的独立上下文。", "An isolated one-shot context for the delegated subtask."), fresh: true },
      ],
      lanes: [
        { name: l("一次性 Subagent", "One-shot Subagent"), detail: l("做完摘要后就退出，不承担长期身份。", "Exits after returning a summary and does not keep long-lived identity."), fresh: true },
      ],
    },
    records: [
      { name: l("Subtask Request", "Subtask Request"), detail: l("父循环交给子循环的边界对象。", "The boundary object handed from parent to child."), fresh: true },
    ],
    handoff: [
      l("父循环定义子任务", "The parent loop defines a subtask"),
      l("子循环在独立 messages 里执行", "The child loop runs in isolated messages"),
      l("摘要回到父循环继续主线", "A summary returns to the parent loop"),
    ],
  },
  s05: {
    summary: l(
      "技能系统把知识获取拆成发现层和按需加载层，避免把所有说明一开始全塞进 prompt。",
      "The skill system splits knowledge into a discovery layer and an on-demand loading layer so the prompt does not start bloated."
    ),
    slices: {
      control: [
        { name: l("Skill Discovery", "Skill Discovery"), detail: l("先用便宜方式知道有哪些技能可用。", "Learns which skills exist through a cheap discovery pass."), fresh: true },
        { name: l("Skill Load", "Skill Load"), detail: l("真正需要时再把深说明注入。", "Loads deep instructions only when they are actually needed."), fresh: true },
      ],
      state: [
        { name: l("Skill Registry", "Skill Registry"), detail: l("保存技能名字、简介和路径。", "Stores skill names, summaries, and paths."), fresh: true },
      ],
      mainline: [
        { name: l("主循环保持轻量", "Keep the Loop Lightweight"), detail: l("技能不是固定写进系统 prompt，而是按需补进当前轮。", "Skills are injected on demand instead of being permanently fused into the system prompt."), },
      ],
    },
    records: [
      { name: l("SKILL.md", "SKILL.md"), detail: l("技能的深说明载体。", "The deep instruction source for a skill."), fresh: true },
    ],
    handoff: [
      l("先发现技能入口", "Discover the skill entry first"),
      l("需要时读取 SKILL.md", "Read SKILL.md when needed"),
      l("再把结果回注给主循环", "Feed the loaded result back into the main loop"),
    ],
  },
  s06: {
    summary: l(
      "上下文压缩让系统第一次区分活跃窗口和被转移出去的细节，长会话开始变得可持续。",
      "Context compaction is where the system first separates the active window from offloaded detail so long sessions stay usable."
    ),
    slices: {
      control: [
        { name: l("压缩触发器", "Compaction Trigger"), detail: l("接近 token 上限时决定何时压缩。", "Decides when to compact as the token budget grows."), fresh: true },
        { name: l("微压缩与摘要压缩", "Micro and Summary Compaction"), detail: l("按损失程度分两层压缩。", "Compacts in layers with different levels of loss."), fresh: true },
      ],
      state: [
        { name: l("活跃上下文", "Active Context"), detail: l("当前轮必须直接看到的内容。", "What the current turn must see directly."), },
        { name: l("Persisted Output", "Persisted Output"), detail: l("被移出活跃窗口但仍可再读的细节。", "Detail moved out of the active window but still readable later."), fresh: true },
        { name: l("Summary State", "Summary State"), detail: l("压缩后保留下来的主线。", "The retained storyline after compaction."), fresh: true },
      ],
    },
    records: [
      { name: l("Micro Compact Record", "Micro Compact Record"), detail: l("短期挪走细节。", "Moves recent detail out of the hot window."), fresh: true },
      { name: l("Summary Compact", "Summary Compact"), detail: l("保住主线连续性。", "Preserves continuity of the mainline."), fresh: true },
    ],
    handoff: [
      l("细节先移出活跃窗口", "Detail leaves the active window first"),
      l("主线被压成摘要", "The mainline is preserved as a summary"),
      l("后续真需要时再读回原文", "Raw detail is read back only when needed"),
    ],
  },
  s07: {
    summary: l(
      "从这一章开始，执行前出现了真正的控制面闸门：模型意图必须先变成可判断的权限请求。",
      "From this chapter onward, execution gets a real control-plane gate: model intent must become a permission request before it runs."
    ),
    slices: {
      control: [
        { name: l("Permission Gate", "Permission Gate"), detail: l("deny / ask / allow 决策发生在执行之前。", "deny / ask / allow happens before execution."), fresh: true },
        { name: l("模式控制", "Mode Control"), detail: l("default、plan、auto 等模式影响整条权限路径。", "Modes such as default, plan, and auto affect the whole permission path."), fresh: true },
      ],
      state: [
        { name: l("PermissionRule", "PermissionRule"), detail: l("定义哪些工具或路径直接允许、拒绝或询问。", "Defines which tools or paths are allowed, denied, or sent for confirmation."), fresh: true },
        { name: l("PermissionDecision", "PermissionDecision"), detail: l("把 allow / ask / deny 结构化回写。", "Writes allow / ask / deny back in structured form."), fresh: true },
      ],
      mainline: [
        { name: l("主循环不再直达工具", "The Loop No Longer Reaches Tools Directly"), detail: l("tool call 先过权限层，再决定是否真正执行。", "A tool call passes through the permission layer before actual execution."), },
      ],
    },
    records: [
      { name: l("Normalized Intent", "Normalized Intent"), detail: l("把原始工具调用翻译成可判断对象。", "Translates raw tool calls into a policy-checkable object."), fresh: true },
    ],
    handoff: [
      l("模型提出动作", "The model proposes an action"),
      l("权限层做出 allow / ask / deny", "The permission layer returns allow / ask / deny"),
      l("结果回写给主循环继续推理", "That result writes back into the main loop"),
    ],
  },
  s08: {
    summary: l(
      "Hook 让主循环第一次拥有稳定的旁路扩展点，日志、审计、追踪开始从核心逻辑中分离。",
      "Hooks give the loop stable sidecar extension points so logging, audit, and tracing separate from the core path."
    ),
    slices: {
      control: [
        { name: l("Lifecycle Events", "Lifecycle Events"), detail: l("主循环在 pre_tool / post_tool / on_error 等边界发出事件。", "The loop emits events at boundaries like pre_tool, post_tool, and on_error."), fresh: true },
        { name: l("Hook Registry", "Hook Registry"), detail: l("多个 hook 共享同一事件契约。", "Multiple hooks share one event contract."), fresh: true },
      ],
      state: [
        { name: l("HookEvent", "HookEvent"), detail: l("tool、input、result、error 等结构化事件包。", "A structured event envelope carrying tool, input, result, error, and more."), fresh: true },
      ],
      mainline: [
        { name: l("主线保持最小", "Keep the Mainline Small"), detail: l("副作用通过 hook 附着，不侵入每个工具 handler。", "Side effects attach through hooks instead of invading every handler."), },
      ],
    },
    records: [
      { name: l("Audit Sink", "Audit Sink"), detail: l("一个具体副作用落点。", "A concrete side-effect sink."), fresh: true },
    ],
    handoff: [
      l("主循环发事件", "The loop emits an event"),
      l("Hook 观察并产出副作用", "Hooks observe and produce side effects"),
      l("主线继续推进不被重写", "The mainline continues without being rewritten"),
    ],
  },
  s09: {
    summary: l(
      "长期记忆把跨会话事实从即时上下文里分层出来，系统第一次有了真正的 durable knowledge 容器。",
      "Long-term memory layers cross-session facts away from immediate context and introduces a real durable knowledge container."
    ),
    slices: {
      control: [
        { name: l("Memory Load/Write", "Memory Load/Write"), detail: l("模型调用前读取，任务结束后提炼并写回。", "Load before the model call, then extract and write after the work turn."), fresh: true },
      ],
      state: [
        { name: l("messages[]", "messages[]"), detail: l("承载当前过程，不负责跨会话长期知识。", "Carries the live process, not long-term cross-session knowledge."), },
        { name: l("Memory Store", "Memory Store"), detail: l("只保存跨会话仍然有价值的事实。", "Stores only durable facts that still matter across sessions."), fresh: true },
      ],
    },
    records: [
      { name: l("MemoryEntry", "MemoryEntry"), detail: l("用户偏好、项目约束等长期事实。", "Long-lived facts such as preferences and project constraints."), fresh: true },
    ],
    handoff: [
      l("先读取相关 memory", "Relevant memory is loaded first"),
      l("主循环完成本轮工作", "The main loop completes the current turn"),
      l("再把新事实提炼写回", "New durable facts are extracted and written back"),
    ],
  },
  s10: {
    summary: l(
      "系统输入在这里变成装配流水线，模型看到的不再是一段神秘大 prompt，而是一组有边界的输入片段。",
      "System input becomes an assembly pipeline here: the model no longer sees one giant mysterious prompt, but a bounded set of input sections."
    ),
    slices: {
      control: [
        { name: l("Prompt Builder", "Prompt Builder"), detail: l("按顺序装配稳定规则、运行时状态、工具和记忆。", "Assembles stable policy, runtime state, tools, and memory in a visible order."), fresh: true },
      ],
      state: [
        { name: l("Prompt Parts", "Prompt Parts"), detail: l("每一段输入都有单独边界。", "Each input fragment has its own explicit boundary."), fresh: true },
        { name: l("Runtime Context", "Runtime Context"), detail: l("工作目录、任务状态、记忆等运行时片段。", "Runtime fragments such as workspace state, task state, and memory."), fresh: true },
      ],
      mainline: [
        { name: l("模型输入构建", "Model Input Construction"), detail: l("主循环在调用模型前先构建完整输入。", "The loop constructs the full input before calling the model."), },
      ],
    },
    records: [
      { name: l("Section Order", "Section Order"), detail: l("哪一段先拼、哪一段后拼。", "Which fragment is assembled first versus later."), fresh: true },
    ],
    handoff: [
      l("稳定策略先装配", "Stable policy is assembled first"),
      l("运行时片段再注入", "Runtime fragments are injected next"),
      l("最终输入才交给模型", "Only then does the final input reach the model"),
    ],
  },
  s11: {
    summary: l(
      "错误恢复把失败正式纳入状态机，系统开始显式记录为什么继续、为什么重试、为什么停止。",
      "Error recovery formally brings failure into the state machine so the system records why it continues, retries, or stops."
    ),
    slices: {
      control: [
        { name: l("Recovery Manager", "Recovery Manager"), detail: l("按失败类型选择 retry、fallback、ask 或 stop。", "Chooses retry, fallback, ask, or stop by failure type."), fresh: true },
      ],
      state: [
        { name: l("Continuation Reason", "Continuation Reason"), detail: l("把“为什么继续”写成可见状态。", "Makes the reason for continuation visible state."), fresh: true },
        { name: l("Retry Bounds", "Retry Bounds"), detail: l("限制恢复分支不会无限循环。", "Prevents recovery branches from looping forever."), fresh: true },
      ],
      mainline: [
        { name: l("失败仍回到主循环", "Failures Still Return to the Loop"), detail: l("失败不是丢掉，而是带着恢复语义回写。", "Failures are not discarded; they write back with recovery semantics."), },
      ],
    },
    records: [
      { name: l("RecoveryState", "RecoveryState"), detail: l("错误分类和恢复分支状态。", "The error classification and branch state."), fresh: true },
    ],
    handoff: [
      l("工具失败先分类", "A tool failure is classified first"),
      l("恢复层选择分支", "The recovery layer chooses a branch"),
      l("继续原因写回主循环", "The continuation reason returns to the main loop"),
    ],
  },
  s12: {
    summary: l(
      "任务系统第一次把会话步骤提升成 durable work graph，系统开始能跨轮次推进一组真正的工作节点。",
      "The task system is where session steps become a durable work graph that can progress real work nodes across turns."
    ),
    slices: {
      control: [
        { name: l("Unlock Rules", "Unlock Rules"), detail: l("完成一个任务后检查哪些后继节点可以开始。", "Checks which downstream nodes can start once one task completes."), fresh: true },
      ],
      state: [
        { name: l("Task Board", "Task Board"), detail: l("所有工作节点的持久记录面。", "The durable record surface for all work nodes."), fresh: true },
        { name: l("Dependency Edges", "Dependency Edges"), detail: l("blockedBy / blocks 记录谁依赖谁。", "blockedBy / blocks record who depends on whom."), fresh: true },
      ],
      mainline: [
        { name: l("任务与会话分层", "Tasks Layer Away From the Session"), detail: l("会话内的 todo 退到次要位置，durable task 进入主设计。", "Session-local todo becomes secondary while durable tasks enter the main architecture."), fresh: true },
      ],
    },
    records: [
      { name: l("TaskRecord", "TaskRecord"), detail: l("目标、状态、依赖、owner 等持久字段。", "Durable fields for goal, status, dependencies, owner, and more."), fresh: true },
    ],
    handoff: [
      l("任务节点被创建", "A task node is created"),
      l("依赖边决定何时 ready", "Dependency edges decide when work becomes ready"),
      l("完成后解锁后继节点", "Completion unlocks downstream nodes"),
    ],
  },
  s13: {
    summary: l(
      "后台任务把“这项工作存在”和“这次执行正在跑”两层彻底分开，runtime record 正式成立。",
      "Background tasks fully separate the existence of work from one live execution attempt, which is where runtime records become first-class."
    ),
    slices: {
      control: [
        { name: l("Notification Drain", "Notification Drain"), detail: l("下一轮调用模型前先把后台摘要带回。", "Drains background notifications before the next model call."), fresh: true },
      ],
      state: [
        { name: l("Task Goal", "Task Goal"), detail: l("durable task 仍在任务板上。", "The durable task goal still lives on the task board."), },
        { name: l("RuntimeTaskRecord", "RuntimeTaskRecord"), detail: l("描述一条正在跑或跑完的执行槽位。", "Describes one running or completed execution slot."), fresh: true },
        { name: l("output_file", "output_file"), detail: l("完整产物落盘，通知只带 preview。", "The full artifact goes to disk while notifications carry only a preview."), fresh: true },
      ],
      lanes: [
        { name: l("后台执行线", "Background Execution Slot"), detail: l("慢命令在旁路执行，主循环继续前进。", "Slow commands execute on a side path while the main loop keeps moving."), fresh: true },
      ],
    },
    records: [
      { name: l("Notification", "Notification"), detail: l("结果回流桥梁。", "The bridge back into the main loop."), fresh: true },
    ],
    handoff: [
      l("主循环创建 runtime record", "The loop creates a runtime record"),
      l("后台槽位执行慢命令", "A background slot runs the slow command"),
      l("notification + output_file 回到主系统", "notification plus output_file returns to the main system"),
    ],
  },
  s14: {
    summary: l(
      "Cron 调度把时间从“外部条件”变成系统内正式的触发源，但执行权仍然交给 runtime 层。",
      "The cron scheduler makes time a first-class trigger source while still handing execution off to the runtime layer."
    ),
    slices: {
      control: [
        { name: l("Schedule Matcher", "Schedule Matcher"), detail: l("只负责判断规则是否命中。", "Only decides whether a rule matches."), fresh: true },
      ],
      state: [
        { name: l("ScheduleRecord", "ScheduleRecord"), detail: l("记录何时触发什么。", "Records what should trigger and when."), fresh: true },
        { name: l("RuntimeTaskRecord", "RuntimeTaskRecord"), detail: l("命中后生成的具体执行实例。", "The concrete runtime instance created after a match."), },
      ],
      lanes: [
        { name: l("时间触发面", "Time Trigger Surface"), detail: l("cron tick 只是触发面，不直接执行业务。", "A cron tick is only a trigger surface, not the business execution itself."), fresh: true },
      ],
    },
    records: [
      { name: l("Trigger Event", "Trigger Event"), detail: l("一次规则命中。", "One rule-match occurrence."), fresh: true },
    ],
    handoff: [
      l("cron 规则命中", "A cron rule matches"),
      l("生成 runtime task", "A runtime task is created"),
      l("后台运行时接管执行", "The background runtime takes over execution"),
    ],
  },
  s15: {
    summary: l(
      "这里开始从单执行者迈向长期团队，persistent teammate、roster 和 inbox 成为新的平台骨架。",
      "This is where the system moves from one executor toward a long-lived team with persistent teammates, a roster, and inboxes."
    ),
    slices: {
      control: [
        { name: l("Lead Orchestrator", "Lead Orchestrator"), detail: l("维护 roster、分配职责、观察团队状态。", "Maintains the roster, assigns work, and watches team state."), fresh: true },
      ],
      state: [
        { name: l("Team Roster", "Team Roster"), detail: l("记录每个队友的名字、角色和状态。", "Stores each teammate's name, role, and status."), fresh: true },
        { name: l("Inbox", "Inbox"), detail: l("每个队友独立的消息边界。", "A separate message boundary for each teammate."), fresh: true },
      ],
      lanes: [
        { name: l("Persistent Teammate", "Persistent Teammate"), detail: l("长期存在、可反复接活的执行者。", "A long-lived worker that can take repeated assignments."), fresh: true },
      ],
    },
    records: [
      { name: l("TeamMember", "TeamMember"), detail: l("长期身份，不是一次性委派结果。", "A long-lived identity, not a one-shot delegation result."), fresh: true },
      { name: l("MessageEnvelope", "MessageEnvelope"), detail: l("邮箱里的结构化消息。", "A structured message carried through inboxes."), fresh: true },
    ],
    handoff: [
      l("lead 指定职责", "The lead defines responsibility"),
      l("消息进入队友 inbox", "Messages enter the teammate inbox"),
      l("队友独立执行并回信", "The teammate runs independently and replies"),
    ],
  },
  s16: {
    summary: l(
      "团队协议把协作从自由文本升级成结构化请求流，request_id 和 durable request record 成为新主线。",
      "Team protocols upgrade collaboration from free-form text into structured request flows centered on request_id and durable request records."
    ),
    slices: {
      control: [
        { name: l("Protocol Envelope", "Protocol Envelope"), detail: l("type、from、to、request_id、payload 这类固定外壳。", "A fixed envelope with type, from, to, request_id, and payload."), fresh: true },
        { name: l("Protocol State Machine", "Protocol State Machine"), detail: l("pending / approved / rejected / expired。", "pending / approved / rejected / expired."), fresh: true },
      ],
      state: [
        { name: l("Request Store", "Request Store"), detail: l("把协议请求变成 durable request record。", "Turns protocol requests into durable request records."), fresh: true },
      ],
      lanes: [
        { name: l("协议协作通道", "Protocol Collaboration Channel"), detail: l("审批、关机、交接这类协作都走同一种 request/response 模型。", "Approvals, shutdowns, and handoffs all use the same request/response model."), fresh: true },
      ],
    },
    records: [
      { name: l("RequestRecord", "RequestRecord"), detail: l("协议工作的真正状态中心。", "The real state center of a protocol workflow."), fresh: true },
    ],
    handoff: [
      l("发出协议请求", "A protocol request is sent"),
      l("request_id 绑定状态记录", "request_id binds the durable state record"),
      l("明确响应回写状态机", "An explicit response writes back into the state machine"),
    ],
  },
  s17: {
    summary: l(
      "自治章节把队友从“等待派活”推进到“按 claim policy 自己找活并恢复上下文”，平台开始真正自己运转。",
      "The autonomy chapter moves teammates from waiting for assignments to self-claiming eligible work under a claim policy and resuming with context."
    ),
    slices: {
      control: [
        { name: l("Idle Poll Loop", "Idle Poll Loop"), detail: l("空闲时按节奏检查 inbox 和 task board。", "Checks inboxes and the task board on a cadence during idle time."), fresh: true },
        { name: l("Claim Policy", "Claim Policy"), detail: l("只有满足角色与状态条件的任务才允许 auto-claim。", "Only tasks that satisfy role and state conditions may be auto-claimed."), fresh: true },
      ],
      state: [
        { name: l("Claim Events", "Claim Events"), detail: l("记录是谁因什么来源认领了任务。", "Records who claimed a task and from which source."), fresh: true },
        { name: l("Durable Requests", "Durable Requests"), detail: l("自治队友继续继承上一章的协议请求状态。", "Autonomous teammates still inherit durable protocol request state from the previous chapter."), },
      ],
      lanes: [
        { name: l("Autonomous Worker", "Autonomous Worker"), detail: l("空闲时自己发现可做工作，再恢复执行。", "Discovers eligible work while idle, then resumes execution."), fresh: true },
      ],
    },
    records: [
      { name: l("Claimable Predicate", "Claimable Predicate"), detail: l("判定任务是否可由当前角色认领。", "Decides whether the current role may claim a task."), fresh: true },
    ],
    handoff: [
      l("队友进入 idle poll", "The teammate enters idle polling"),
      l("claim policy 选出可认领工作", "The claim policy selects eligible work"),
      l("身份块重注入后恢复执行", "Identity is re-injected and execution resumes"),
    ],
  },
  s18: {
    summary: l(
      "Worktree 章节把执行环境从主目录里拆开，任务继续表达目标，而 worktree 成为独立、可观察、可 closeout 的执行车道。",
      "The worktree chapter pulls execution environments out of the main directory: tasks still express goals while worktrees become isolated, observable, closeout-capable lanes."
    ),
    slices: {
      control: [
        { name: l("Task-to-Lane Binding", "Task-to-Lane Binding"), detail: l("系统明确记录哪条任务用哪条执行车道。", "The system records which task is using which execution lane."), fresh: true },
        { name: l("Closeout Semantics", "Closeout Semantics"), detail: l("收尾时显式决定 keep 还是 remove。", "Closeout explicitly decides whether to keep or remove the lane."), fresh: true },
      ],
      state: [
        { name: l("Worktree Index", "Worktree Index"), detail: l("注册每条隔离车道的路径、分支和 task_id。", "Registers each isolated lane's path, branch, and task_id."), fresh: true },
        { name: l("TaskRecord.worktree", "TaskRecord.worktree"), detail: l("任务记录里也能直接看到它当前在哪条 lane 上。", "The task record shows which lane it is currently using."), fresh: true },
        { name: l("Event Log", "Event Log"), detail: l("create / enter / run / closeout 等生命周期事件。", "Lifecycle events such as create, enter, run, and closeout."), fresh: true },
      ],
      lanes: [
        { name: l("Isolated Directory Lane", "Isolated Directory Lane"), detail: l("不同任务默认不共享未提交改动。", "Different tasks do not share uncommitted changes by default."), fresh: true },
      ],
    },
    records: [
      { name: l("WorktreeRecord", "WorktreeRecord"), detail: l("车道级执行记录。", "The execution record for one lane."), fresh: true },
      { name: l("Closeout Record", "Closeout Record"), detail: l("保留或回收的显式结果。", "The explicit result of keep versus reclaim."), fresh: true },
    ],
    handoff: [
      l("任务绑定到 worktree lane", "A task binds to a worktree lane"),
      l("命令在隔离目录里执行", "Commands run inside the isolated directory"),
      l("closeout 决定 lane 的最终去向", "Closeout decides the lane's final fate"),
    ],
  },
  s19: {
    summary: l(
      "最后一章把本地工具、插件和 MCP server 重新统一到同一 capability bus 下，外部能力终于回到原有控制面里。",
      "The final chapter reunifies native tools, plugins, and MCP servers on one capability bus so external capability returns to the same control plane."
    ),
    slices: {
      control: [
        { name: l("Capability Router", "Capability Router"), detail: l("先发现能力，再决定本地、插件还是 MCP 路由。", "Discovers capability first, then routes to native, plugin, or MCP."), fresh: true },
        { name: l("Shared Permission Gate", "Shared Permission Gate"), detail: l("外部能力和本地工具共用同一权限语义。", "External capabilities and native tools share one permission contract."), fresh: true },
        { name: l("Result Normalizer", "Result Normalizer"), detail: l("远程结果也要转成主循环看得懂的标准 payload。", "Remote results are normalized into a payload the main loop already understands."), fresh: true },
      ],
      state: [
        { name: l("Plugin Manifest", "Plugin Manifest"), detail: l("告诉系统有哪些外部 server 可用。", "Tells the system which external servers are available."), fresh: true },
        { name: l("Capability View", "Capability View"), detail: l("把 native / plugin / mcp 整理成一个可比较的能力面。", "Collects native, plugin, and MCP capability into one comparable view."), fresh: true },
      ],
      lanes: [
        { name: l("Native Tool", "Native Tool"), detail: l("本地 handler。", "A local handler."), },
        { name: l("MCP / Plugin Lane", "MCP / Plugin Lane"), detail: l("外部 server 或插件提供的远程能力。", "Remote capability provided by an external server or plugin."), fresh: true },
      ],
    },
    records: [
      { name: l("Scoped Capability", "Scoped Capability"), detail: l("带 server / source / risk 信息的能力对象。", "A capability object carrying server, source, and risk information."), fresh: true },
    ],
    handoff: [
      l("先做 capability discovery", "Capability discovery happens first"),
      l("统一 permission + routing", "Routing and permission stay unified"),
      l("标准化结果再回写主循环", "A normalized result writes back into the main loop"),
    ],
  },
};
