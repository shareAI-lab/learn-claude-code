"use client";

import { motion } from "framer-motion";
import { useLocale, useTranslations } from "@/lib/i18n";
import { VERSION_META, type VersionId } from "@/lib/constants";
import { getChapterGuide } from "@/lib/chapter-guides";
import { getVersionContent } from "@/lib/version-content";
import { LayerBadge } from "@/components/ui/badge";
import {
  LateStageTeachingMap,
  hasLateStageTeachingMap,
} from "./late-stage-teaching-map";

interface OverviewSection {
  title: string;
  body: string;
}

interface OverviewCopy {
  eyebrow: string;
  summary: string;
  sections: OverviewSection[];
  flowLabel: string;
  flow: string[];
  cautionLabel: string;
  caution: string;
  outcomeLabel: string;
  outcome: string;
}

const SURFACE_CLASSES: Record<string, string> = {
  core: "from-blue-500/10 via-blue-500/5 to-transparent",
  hardening: "from-emerald-500/10 via-emerald-500/5 to-transparent",
  runtime: "from-amber-500/10 via-amber-500/5 to-transparent",
  platform: "from-red-500/10 via-red-500/5 to-transparent",
};

const RING_CLASSES: Record<string, string> = {
  core: "ring-blue-500/20",
  hardening: "ring-emerald-500/20",
  runtime: "ring-amber-500/20",
  platform: "ring-red-500/20",
};

const ZH_COPY: Record<string, OverviewCopy> = {
  s07: {
    eyebrow: "执行前先过权限闸门",
    summary:
      "权限系统的核心不是把工具藏起来，而是把“模型想做什么”先翻译成结构化意图，再按策略决定允许、拒绝还是询问用户。",
    sections: [
      {
        title: "输入要先规范化",
        body:
          "不要直接拿原始 tool call 执行。先抽出动作类型、目标路径、风险级别，变成权限层能判断的统一结构。",
      },
      {
        title: "策略是独立控制面",
        body:
          "允许名单、只读模式、危险命令拦截、需要确认的模式，都应该在权限层统一判断，而不是散在每个工具里。",
      },
      {
        title: "结果必须可回写",
        body:
          "无论是 allow、deny 还是 ask，最终都要回到主循环，成为模型下一步推理可以看到的上下文。",
      },
    ],
    flowLabel: "Permission Pipeline",
    flow: ["模型产生命令", "提取意图", "策略判定", "执行或回写拒绝"],
    cautionLabel: "最容易讲错",
    caution:
      "权限系统不是一个 if 语句集合。它是主循环前的独立闸门，负责把不安全执行拦在工具层之前。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能手写一个统一 permission check，让所有工具共享同一套 allow / deny / ask 语义。",
  },
  s08: {
    eyebrow: "在循环外加扩展点",
    summary:
      "Hook 的价值是把日志、审计、追踪、策略注入这些旁路能力挂到生命周期事件上，而不是反复改主循环核心代码。",
    sections: [
      {
        title: "核心循环保持最小",
        body:
          "主循环只负责推进状态。pre_tool、post_tool、on_error 这类附加动作，应该通过 hook 注册进来。",
      },
      {
        title: "事件边界要稳定",
        body:
          "Hook 接收到的不是随意拼出来的文本，而是统一事件对象，例如 toolName、input、result、error、duration。",
      },
      {
        title: "副作用与主流程解耦",
        body:
          "这样新增审计、埋点、自动修复建议时，不会反复打断主线心智，也不会污染每个工具处理函数。",
      },
    ],
    flowLabel: "Lifecycle Events",
    flow: ["主循环推进", "发出事件", "Hook 观察", "副作用回写"],
    cautionLabel: "最容易讲错",
    caution:
      "Hook 不是另一个主循环。它应该观察和补充，而不是偷偷接管核心状态机。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能定义一套生命周期事件，并用注册表把多个 hook 稳定挂接到同一个循环上。",
  },
  s09: {
    eyebrow: "把跨会话知识单独存放",
    summary:
      "Memory 系统只保存那些跨轮次、跨会话、无法从当前工作目录重新推导出来的事实，而不是把所有历史都塞进长期记忆。",
    sections: [
      {
        title: "记忆要有类型",
        body:
          "用户偏好、项目约束、稳定环境信息应该分类型存，不要把随手观察到的临时输出和真实长期知识混在一起。",
      },
      {
        title: "读取与写入分两段",
        body:
          "模型调用前加载相关记忆，任务结束后再提炼新增记忆。这样主循环里每次读写点都清晰可控。",
      },
      {
        title: "记忆不能替代上下文",
        body:
          "短期上下文负责当前过程，长期记忆只保留压缩后仍然重要的事实。两者职责必须明确分层。",
      },
    ],
    flowLabel: "Memory Lifecycle",
    flow: ["加载记忆", "组装输入", "完成工作", "提炼并落盘"],
    cautionLabel: "最容易讲错",
    caution:
      "Memory 不是无限对话历史仓库。真正要教清楚的是“什么值得记”和“什么时候写回”。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能区分短期 messages[]、压缩摘要、长期 memory 三种状态容器各自的职责。",
  },
  s10: {
    eyebrow: "把提示词拆成装配流水线",
    summary:
      "系统提示词不应该被讲成一大段神秘文本。真正关键的是：哪些信息先拼、哪些后拼、哪些属于稳定规则、哪些属于运行时状态。",
    sections: [
      {
        title: "稳定规则单独存放",
        body:
          "角色、底线、安全策略这些长期稳定内容，与任务说明、目录信息、临时记忆不该写在同一段字符串里。",
      },
      {
        title: "运行时片段按顺序装配",
        body:
          "工作目录、可用工具、记忆、待办、错误恢复提示等都应该有明确的拼接顺序，避免提示词结构漂移。",
      },
      {
        title: "输入其实是控制平面",
        body:
          "Prompt pipeline 决定了模型在每一轮能看到什么、看见的顺序是什么，这本质上就是控制系统行为。",
      },
    ],
    flowLabel: "Prompt Assembly",
    flow: ["稳定规则", "运行时状态", "工具/记忆注入", "形成最终输入"],
    cautionLabel: "最容易讲错",
    caution:
      "不要把“提示词工程”讲成玄学调参。这里真正需要讲清的是数据来源、拼接顺序和信息边界。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能把 system prompt 改写成一条显式的构建流水线，而不是一段越来越长的大字符串。",
  },
  s11: {
    eyebrow: "失败后仍能继续推进",
    summary:
      "结构更完整的 Agent 关键不是永不出错，而是每次出错后都知道当前处于什么恢复分支，以及应该怎样把失败转成下一步可继续的状态。",
    sections: [
      {
        title: "错误先分类",
        body:
          "权限拒绝、工具异常、环境缺失、超时、冲突写入，不应该都走同一条 retry 逻辑。先分类，恢复才会稳定。",
      },
      {
        title: "恢复原因要显式",
        body:
          "继续执行前，要把“为什么继续”写回上下文，例如 retry、fallback、user confirmation required，而不是静默吞错。",
      },
      {
        title: "恢复分支有上限",
        body:
          "重试次数、降级路径、终止条件都要清楚。否则系统只是把失败隐藏成无限循环。",
      },
    ],
    flowLabel: "Recovery Branches",
    flow: ["发现错误", "分类原因", "选择恢复分支", "带着原因继续"],
    cautionLabel: "最容易讲错",
    caution:
      "错误恢复不是 try/except 包一下。真正重要的是恢复状态也要进入消息历史，成为模型可见事实。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能设计 continuation reason，并把 retry / fallback / stop 变成可解释的状态迁移。",
  },
  s12: {
    eyebrow: "把会话步骤升级成持久工作图",
    summary:
      "任务系统不是把 todo 列表存盘那么简单，而是把工作拆成可追踪、可解锁、可跨轮次继续推进的 durable task graph。",
    sections: [
      {
        title: "任务先是记录，不是线程",
        body:
          "TaskRecord 记录目标、状态、依赖和解锁关系。它表达的是“还有什么工作要推进”，不是“现在谁正在跑”。",
      },
      {
        title: "依赖关系必须显式",
        body:
          "blockedBy、blocks、status 这类字段要写清楚，不然后续任务何时能开始、为什么还不能开始都会变得模糊。",
      },
      {
        title: "任务板负责推进顺序",
        body:
          "真正要教清楚的是：完成一个节点以后，系统如何检查依赖、解锁后继任务，并把状态变化回写到任务板。",
      },
    ],
    flowLabel: "Durable Task Graph",
    flow: ["创建任务记录", "写入依赖关系", "完成当前节点", "解锁后续任务"],
    cautionLabel: "最容易讲错",
    caution:
      "Task 不是后台线程，也不是模型的一轮计划文本。它是系统里一条可持久推进的工作记录。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能实现带依赖和解锁逻辑的最小任务板，而不是只会维护会话级 todo 列表。",
  },
  s13: {
    eyebrow: "把目标记录和运行槽位分开",
    summary:
      "后台任务这一章真正要教的是：任务目标依然留在 task board，正在执行的那一份工作则进入独立的 runtime record，并用通知把结果带回主循环。",
    sections: [
      {
        title: "运行记录必须独立",
        body:
          "RuntimeTaskRecord 应该有自己的 id、status、started_at、result_preview、output_file。它描述的是“这次执行本身”，不是任务目标本体。",
      },
      {
        title: "预览和全文要分层",
        body:
          "完整输出写文件，通知里只放 preview。这样模型先知道“有结果了、结果大概是什么”，真要看细节再去读文件。",
      },
      {
        title: "通知是回到主循环的桥",
        body:
          "后台线程并不直接改模型状态。它只写 runtime record 和 notification，等下一轮前再统一注入上下文。",
      },
    ],
    flowLabel: "Runtime Task Return Path",
    flow: ["创建 runtime record", "后台执行", "写入 preview / output", "下一轮通知回写"],
    cautionLabel: "最容易讲错",
    caution:
      "后台任务不是另一个会思考的 agent。并行的是等待和执行，不是主循环本身。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能把慢命令放到后台执行，并用 runtime record + notification 把结果稳稳接回主循环。",
  },
  s14: {
    eyebrow: "让时间成为启动源",
    summary:
      "当任务系统和后台执行已经成立后，Cron 章节要讲清的是：时间只负责触发，不负责执行。这样调度器和运行时边界才不会混乱。",
    sections: [
      {
        title: "调度器只管命中规则",
        body:
          "Cron 负责判断“什么时候该触发”，例如每小时、每天、工作日；它不直接承担具体任务执行逻辑。",
      },
      {
        title: "命中后仍生成运行任务",
        body:
          "时间触发到来时，应该像用户请求一样生成 runtime task，再交给后台执行层处理。",
      },
      {
        title: "时间与执行要解耦",
        body:
          "这样你才能分别解释：一个任务为什么被触发，以及它被触发后如何进入执行、重试、通知和完成流程。",
      },
    ],
    flowLabel: "Scheduled Trigger",
    flow: ["Cron tick", "规则匹配", "创建 runtime task", "交给后台执行"],
    cautionLabel: "最容易讲错",
    caution:
      "不要把 Cron 讲成“后台线程每分钟跑一下”。真正的关键是时间触发面和执行运行时是两套职责。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能把 schedule 记录和 runtime task 记录分开，并说明它们如何衔接。",
  },
  s15: {
    eyebrow: "让队友成为长期存在的角色",
    summary:
      "Agent Teams 的重点不是多开几个模型调用，而是给系统引入一组长期存在、能反复接活、能被点名协作的 persistent specialists。",
    sections: [
      {
        title: "身份先于单次任务",
        body:
          "Teammate 需要名字、角色、状态和 inbox。它的价值来自持续存在，而不是像一次性 subagent 那样跑完就消失。",
      },
      {
        title: "邮箱是协作边界",
        body:
          "团队协作不应该靠共享 messages[]。更清晰的做法是每个队友有自己的收件箱和独立执行线，再通过消息互相联系。",
      },
      {
        title: "负责人仍然掌控编排",
        body:
          "Lead 不只是转发消息，它负责生成 roster、分配职责、观察状态，让团队协作保持可理解。",
      },
    ],
    flowLabel: "Persistent Team Loop",
    flow: ["生成队友身份", "投递消息", "队友独立执行", "回信或继续协作"],
    cautionLabel: "最容易讲错",
    caution:
      "teammate 不是换了名字的 subagent。核心差别是长期身份、独立 inbox 和可重复协作。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能搭出一个最小 team roster，让多个长期存在的执行者通过邮箱协作。",
  },
  s16: {
    eyebrow: "把协作从自由文本升级成协议",
    summary:
      "团队协议这一章的关键不是多几种消息类型，而是让重要协作拥有统一 envelope、request_id 和 durable request record，从而做到可追踪、可审批、可收尾。",
    sections: [
      {
        title: "协议消息要有固定外壳",
        body:
          "type、from、to、request_id、payload 这些字段必须成套出现。这样同一类协作才能稳定匹配、稳定处理。",
      },
      {
        title: "请求记录必须落盘",
        body:
          "真正需要追踪的是 RequestRecord，而不是临时内存字典。审批、关机、交接都应该能在记录里看到当前状态和响应结果。",
      },
      {
        title: "状态流要比文本更重要",
        body:
          "pending、approved、rejected、expired 这些状态迁移，才是协议章节真正的教学主线，文本只是承载说明。",
      },
    ],
    flowLabel: "Protocol Request Lifecycle",
    flow: ["发协议请求", "登记 request record", "收到明确响应", "更新状态继续协作"],
    cautionLabel: "最容易讲错",
    caution:
      "协议不是更正式的聊天文案。它是带 request_id 和状态机的结构化协作通道。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能实现一套最小 request / response protocol，并用 durable request record 跟踪其状态。",
  },
  s17: {
    eyebrow: "让队友会自己接活和恢复",
    summary:
      "自治并不意味着神秘智能爆发，而是系统开始允许队友在空闲时主动寻找可认领工作、恢复自己的执行上下文，并按规则继续推进。",
    sections: [
      {
        title: "空闲轮询是自治入口",
        body:
          "Teammate 在 idle cycle 中轮询 inbox、共享任务板或待处理请求，这一步决定它能否在没有新指令时继续前进。",
      },
      {
        title: "认领规则必须清楚",
        body:
          "什么工作可以自领、如何避免重复认领、何时应该放弃，这些边界决定自治是稳定推进还是混乱抢活。",
      },
      {
        title: "恢复上下文要有依据",
        body:
          "队友不是凭空继续工作，而是根据 task state、request state、mailbox 和自身状态恢复到正确分支。",
      },
    ],
    flowLabel: "Autonomy Loop",
    flow: ["进入空闲轮询", "发现可认领工作", "恢复上下文执行", "回写状态后继续"],
    cautionLabel: "最容易讲错",
    caution:
      "自治不是让 agent 随便乱动。真正关键的是 self-claim 规则和 resume 所依赖的状态边界。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能解释 agent 怎样在没有新用户输入时，自主发现、认领并恢复工作。",
  },
  s18: {
    eyebrow: "把任务绑定到独立执行车道",
    summary:
      "Worktree Isolation 章节的核心不是 git 命令细节，而是把任务和执行车道绑定，让不同工作在各自目录里推进，并拥有清晰的 enter / run / closeout 生命周期。",
    sections: [
      {
        title: "任务和车道要分层",
        body:
          "Task 管目标，worktree 管隔离执行环境。只有把两者分开，系统才知道“做什么”和“在哪做”分别由谁负责。",
      },
      {
        title: "生命周期要完整",
        body:
          "分配 worktree、进入目录、执行任务、closeout 保留或删除，这几步都应该显式存在，而不是做完命令就算结束。",
      },
      {
        title: "事件流帮助观察执行面",
        body:
          "create、enter、closeout 这些 worktree event 让主系统能看到执行车道发生了什么，而不是只看到最后结果。",
      },
    ],
    flowLabel: "Isolated Execution Lane",
    flow: ["分配 worktree", "进入隔离目录", "执行任务", "closeout / 保留事件"],
    cautionLabel: "最容易讲错",
    caution:
      "Worktree 不是任务系统本身。它只是给任务提供一条独立、可回收、可观察的执行车道。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能把 task record 和 worktree lifecycle 连接起来，并讲清 keep / remove 何时发生。",
  },
  s19: {
    eyebrow: "把外部能力挂回同一控制面",
    summary:
      "MCP 与 Plugin 章节的重点不是罗列外部生态，而是说明：外部能力进入系统后，如何像本地工具一样被发现、路由、授权、调用和回写。",
    sections: [
      {
        title: "能力先做统一抽象",
        body:
          "无论是本地工具、插件能力还是 MCP server 提供的远程能力，都应该被整理到同一种 capability 视图里。",
      },
      {
        title: "路由前仍要过策略层",
        body:
          "外部能力不是例外。发现、选择、权限控制、错误恢复这些控制面流程都应该保持一致。",
      },
      {
        title: "结果回到同一消息总线",
        body:
          "调用远程能力后，返回结果仍然要标准化成主循环能消费的 tool_result 或结构化事件。",
      },
    ],
    flowLabel: "Capability Bus",
    flow: ["发现能力", "选择路由", "远程调用", "标准化回写"],
    cautionLabel: "最容易讲错",
    caution:
      "不要把 MCP 讲成一个孤立外挂。教学上真正要强调的是“它如何接回原本的 agent 控制平面”。",
    outcomeLabel: "学完应掌握",
    outcome:
      "你应该能解释本地工具、插件和 MCP server 为何可以共享同一套 capability routing 模型。",
  },
};

const EN_COPY: Record<string, OverviewCopy> = {
  s07: {
    eyebrow: "Intent must pass a gate before execution",
    summary:
      "The permission chapter should teach a control gate, not scattered safety checks. Model intent becomes executable action only after policy classification.",
    sections: [
      {
        title: "Normalize the request first",
        body:
          "Convert raw tool calls into a structured intent with action type, target, and risk level before making any permission decision.",
      },
      {
        title: "Keep policy separate",
        body:
          "Read-only modes, allowlists, dangerous-command blocks, and ask-before-run rules should live in one permission plane.",
      },
      {
        title: "Always write back the outcome",
        body:
          "Allow, deny, and ask all need to flow back into the loop so the model can reason over what happened next.",
      },
    ],
    flowLabel: "Permission Pipeline",
    flow: ["Model proposes action", "Intent is classified", "Policy decides", "Execute or return denial"],
    cautionLabel: "Common mistake",
    caution:
      "Permission is not just a few if statements. It is a gate in front of execution with its own control-plane semantics.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A shared permission check that gives every tool the same allow / deny / ask contract.",
  },
  s08: {
    eyebrow: "Extend the loop without rewriting it",
    summary:
      "Hooks let you add audit trails, tracing, policy side effects, and instrumentation around the loop while keeping the loop itself small and legible.",
    sections: [
      {
        title: "The loop stays minimal",
        body:
          "Core state progression stays in the loop. Extra behavior hangs off lifecycle points like pre_tool, post_tool, and on_error.",
      },
      {
        title: "Events need a stable shape",
        body:
          "Hooks should receive normalized lifecycle events with tool name, input, result, error, and duration, not ad hoc strings.",
      },
      {
        title: "Side effects stay decoupled",
        body:
          "That keeps auditing, metrics, or repair hints from leaking into every tool implementation.",
      },
    ],
    flowLabel: "Lifecycle Events",
    flow: ["Loop advances", "Event emitted", "Hooks observe", "Side effects write back"],
    cautionLabel: "Common mistake",
    caution:
      "A hook system should observe and extend the loop, not secretly replace the loop's state machine.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A lifecycle event registry with multiple hooks attached to one stable execution loop.",
  },
  s09: {
    eyebrow: "Persist only what survives sessions",
    summary:
      "Memory is for cross-session facts that cannot be re-derived cheaply, not for storing every conversation turn forever.",
    sections: [
      {
        title: "Use typed memory buckets",
        body:
          "Preferences, project constraints, and durable environment facts should be separated from temporary observations.",
      },
      {
        title: "Read and write at clear moments",
        body:
          "Load relevant memory before prompt assembly. Extract and persist new memory after the work is done.",
      },
      {
        title: "Memory is not context",
        body:
          "Short-term messages carry the live process. Long-term memory keeps only compressed, durable facts.",
      },
    ],
    flowLabel: "Memory Lifecycle",
    flow: ["Load memory", "Assemble input", "Finish work", "Extract and persist"],
    cautionLabel: "Common mistake",
    caution:
      "Memory is not an infinite history log. The hard part is deciding what deserves to survive.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A clear separation between messages[], compacted summaries, and cross-session memory.",
  },
  s10: {
    eyebrow: "Prompting becomes an assembly pipeline",
    summary:
      "The system prompt should be taught as a pipeline that assembles stable policy, runtime state, tools, and memory in a predictable order.",
    sections: [
      {
        title: "Separate stable policy",
        body:
          "Role, safety rules, and non-negotiable constraints should not be tangled with temporary runtime details.",
      },
      {
        title: "Assemble runtime fragments explicitly",
        body:
          "Workspace state, available tools, memory, task state, and recovery hints need a visible assembly order.",
      },
      {
        title: "Input is a control plane",
        body:
          "The ordering and boundaries of prompt fragments control what the model sees and how it reasons.",
      },
    ],
    flowLabel: "Prompt Assembly",
    flow: ["Stable policy", "Runtime state", "Tool and memory injection", "Final model input"],
    cautionLabel: "Common mistake",
    caution:
      "Do not teach this as mystical prompt engineering. Teach data sources, assembly order, and information boundaries.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A prompt builder pipeline instead of a single giant prompt string.",
  },
  s11: {
    eyebrow: "Recovery keeps the system moving",
    summary:
      "A high-completion agent is not error-free. It is explicit about why it is retrying, degrading, or stopping after each failure.",
    sections: [
      {
        title: "Classify failures first",
        body:
          "Permission denials, tool crashes, missing dependencies, timeouts, and write conflicts should not all use the same retry branch.",
      },
      {
        title: "Continuation reasons stay explicit",
        body:
          "Before continuing, record whether this branch is a retry, fallback, or user-confirmation path.",
      },
      {
        title: "Recovery needs hard limits",
        body:
          "Caps on retries, fallback paths, and stop conditions prevent silent infinite loops.",
      },
    ],
    flowLabel: "Recovery Branches",
    flow: ["Failure detected", "Reason classified", "Recovery chosen", "Continue with context"],
    cautionLabel: "Common mistake",
    caution:
      "Recovery is not just a try/except wrapper. The recovery reason itself must become visible state.",
    outcomeLabel: "You should be able to build",
    outcome:
      "Explicit continuation reasons that make retry / fallback / stop into understandable state transitions.",
  },
  s12: {
    eyebrow: "Turn session steps into a durable work graph",
    summary:
      "The task system is not just a saved todo list. It turns work into durable records with dependency edges so progress can unlock later work across turns.",
    sections: [
      {
        title: "A task is a record before it is execution",
        body:
          "TaskRecord stores goal, state, and dependency edges. It answers what work exists and what is blocked, not what thread is currently running.",
      },
      {
        title: "Dependency edges must stay explicit",
        body:
          "Fields like blockedBy, blocks, and status make it clear why a task cannot start yet and which downstream work becomes eligible next.",
      },
      {
        title: "The board owns unlock logic",
        body:
          "The key runtime lesson is how completing one node updates the board, checks dependency satisfaction, and unlocks the next nodes.",
      },
    ],
    flowLabel: "Durable Task Graph",
    flow: ["Create task record", "Write dependency edges", "Complete current node", "Unlock downstream work"],
    cautionLabel: "Common mistake",
    caution:
      "A task is not a background thread and not a plan paragraph. It is a durable work record inside the system.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A minimal task board with dependency and unlock logic, not just a session-scoped todo list.",
  },
  s13: {
    eyebrow: "Separate goal records from running slots",
    summary:
      "The real lesson in background tasks is that the durable task goal stays on the board while each live execution gets its own runtime record and returns through notifications.",
    sections: [
      {
        title: "Running work needs its own record",
        body:
          "A RuntimeTaskRecord should carry id, status, started_at, result_preview, and output_file. It describes one execution attempt, not the task goal itself.",
      },
      {
        title: "Preview and full output should split",
        body:
          "Write the complete output to disk, then send only a preview back through notifications. The loop learns what happened without flooding prompt space.",
      },
      {
        title: "Notifications rejoin the main loop",
        body:
          "The background thread should not mutate model state directly. It writes runtime state and notifications, then the next turn injects them back into context.",
      },
    ],
    flowLabel: "Runtime Task Return Path",
    flow: ["Create runtime record", "Run in background", "Write preview and output", "Inject notification next turn"],
    cautionLabel: "Common mistake",
    caution:
      "A background task is not another thinking agent. What runs in parallel is waiting and execution, not the main loop itself.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A background execution path that returns through runtime records and notifications instead of blocking the foreground loop.",
  },
  s14: {
    eyebrow: "Time becomes another trigger source",
    summary:
      "Once tasks can run in the background, a scheduler should only decide when to trigger work. Execution still belongs to the runtime layer.",
    sections: [
      {
        title: "The scheduler only matches rules",
        body:
          "Cron owns time rules like hourly, daily, or weekdays. It should not directly own the runtime execution model.",
      },
      {
        title: "A trigger creates runtime work",
        body:
          "When a rule matches, generate the same kind of runtime task that other sources would create.",
      },
      {
        title: "Time and execution stay decoupled",
        body:
          "That lets you explain both why work started and how it moved through execution, retries, and completion.",
      },
    ],
    flowLabel: "Scheduled Trigger",
    flow: ["Cron tick", "Rule match", "Create runtime task", "Hand off to background runtime"],
    cautionLabel: "Common mistake",
    caution:
      "Do not reduce cron to a timer thread. The teaching value is the separation between trigger time and execution runtime.",
    outcomeLabel: "You should be able to build",
    outcome:
      "Separate schedule records from runtime task records and show how one hands off to the other.",
  },
  s15: {
    eyebrow: "Make teammates long-lived roles",
    summary:
      "Agent teams matter when specialists stop being disposable subtasks and become persistent identities with roles, inboxes, and repeatable responsibilities.",
    sections: [
      {
        title: "Identity comes before one task",
        body:
          "A teammate needs a name, role, status, and inbox. Its value comes from remaining available across multiple rounds of work.",
      },
      {
        title: "Mailbox boundaries keep coordination clear",
        body:
          "Teams should not share one giant messages[] buffer. Each worker has an inbox and its own execution line, then coordination travels through messages.",
      },
      {
        title: "The lead still owns orchestration",
        body:
          "The lead builds the roster, assigns work, and watches state. Team structure is what keeps persistence understandable instead of chaotic.",
      },
    ],
    flowLabel: "Persistent Team Loop",
    flow: ["Create teammate identity", "Deliver message", "Worker runs independently", "Reply or continue"],
    cautionLabel: "Common mistake",
    caution:
      "A teammate is not just a renamed subagent. The important difference is long-lived identity and repeatable collaboration.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A minimal team roster where persistent workers collaborate through mailboxes.",
  },
  s16: {
    eyebrow: "Upgrade coordination from chat to protocol",
    summary:
      "Team protocols matter because important coordination needs a fixed envelope, a request_id, and a durable request record, not just free-form text in a mailbox.",
    sections: [
      {
        title: "Protocol messages need a stable envelope",
        body:
          "type, from, to, request_id, and payload should travel together so one workflow can always be parsed and handled the same way.",
      },
      {
        title: "Requests should be durable records",
        body:
          "The real object to teach is the RequestRecord, not an in-memory tracker. Approval, shutdown, or handoff should survive long enough to inspect and resume.",
      },
      {
        title: "State transitions matter more than wording",
        body:
          "pending, approved, rejected, and expired are the actual teaching spine. The human-readable text is only the explanation layer around that state machine.",
      },
    ],
    flowLabel: "Protocol Request Lifecycle",
    flow: ["Send protocol request", "Persist request record", "Receive explicit response", "Update state and continue"],
    cautionLabel: "Common mistake",
    caution:
      "A protocol is not just more formal chat. It is a structured coordination path with request correlation and state transitions.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A small request / response protocol with durable request tracking.",
  },
  s17: {
    eyebrow: "Let workers self-claim and self-resume",
    summary:
      "Autonomy is not magic intelligence. It begins when a worker can poll for eligible work, restore the right context, and continue under clear claim rules.",
    sections: [
      {
        title: "Idle polling is the autonomy entry point",
        body:
          "During idle cycles, a worker checks inboxes, boards, or pending requests to discover whether something can now be claimed.",
      },
      {
        title: "Claim rules must stay explicit",
        body:
          "The system needs clear rules for what a worker may claim, how collisions are avoided, and when it should back off.",
      },
      {
        title: "Resume depends on visible state",
        body:
          "A worker does not continue from nowhere. It resumes from task state, protocol state, mailbox contents, and its own role state.",
      },
    ],
    flowLabel: "Autonomy Loop",
    flow: ["Enter idle poll", "Find claimable work", "Resume with context", "Write back state"],
    cautionLabel: "Common mistake",
    caution:
      "Autonomy does not mean uncontrolled motion. The important part is the claim policy and the state used to resume safely.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A worker loop that can discover, claim, and resume work without waiting for a new user turn.",
  },
  s18: {
    eyebrow: "Bind tasks to isolated execution lanes",
    summary:
      "Worktree isolation is not about git trivia. It is about giving each task a separate execution lane with explicit enter, run, and closeout lifecycle steps.",
    sections: [
      {
        title: "Tasks and lanes are different layers",
        body:
          "Tasks describe the goal. Worktrees describe where isolated execution happens. Keeping those layers separate prevents the runtime model from blurring.",
      },
      {
        title: "Lifecycle steps should stay explicit",
        body:
          "Allocate the worktree, enter the directory, run the work, then decide whether to keep or remove it during closeout.",
      },
      {
        title: "Lifecycle events make lanes observable",
        body:
          "Create, enter, and closeout events let the rest of the system observe execution-lane state instead of only seeing the final result.",
      },
    ],
    flowLabel: "Isolated Execution Lane",
    flow: ["Allocate worktree", "Enter isolated dir", "Run task", "Close out or keep"],
    cautionLabel: "Common mistake",
    caution:
      "A worktree is not the task system itself. It is an isolated, observable execution lane for a task.",
    outcomeLabel: "You should be able to build",
    outcome:
      "A task-to-worktree binding with explicit keep / remove closeout semantics.",
  },
  s19: {
    eyebrow: "External capability joins the same control plane",
    summary:
      "MCP and plugins matter because they extend the agent's capability bus without inventing a second execution universe.",
    sections: [
      {
        title: "Unify capability abstraction first",
        body:
          "Native tools, plugins, and MCP server actions should all enter the system through one capability view.",
      },
      {
        title: "External calls still pass policy",
        body:
          "Discovery, routing, permission checks, and recovery logic should apply to external capabilities too.",
      },
      {
        title: "Results return on the same bus",
        body:
          "Remote outputs should be normalized into the same tool_result or structured event format the loop already understands.",
      },
    ],
    flowLabel: "Capability Bus",
    flow: ["Discover capability", "Choose route", "Call external system", "Normalize and append"],
    cautionLabel: "Common mistake",
    caution:
      "Do not teach MCP as an isolated addon. The key is how it plugs back into the existing agent control plane.",
    outcomeLabel: "You should be able to build",
    outcome:
      "One capability-routing model that can explain native tools, plugins, and MCP servers together.",
  },
};

const JA_FALLBACK_TEXT = {
  sectionA: "この章で本当に増えるもの",
  sectionB: "最初に守る境界",
  sectionC: "実装で到達したい形",
  flowLabel: "読む順序",
  cautionLabel: "混同しやすい点",
  outcomeLabel: "学習後にできること",
  flow: [
    "まず増分を見る",
    "次に状態境界を分ける",
    "その後で回写経路を追う",
    "最後に自分で最小実装を作る",
  ],
} as const;

function buildJapaneseFallbackOverview(version: string): OverviewCopy | null {
  const versionId = version as VersionId;
  const content = getVersionContent(version, "ja");
  const guide = getChapterGuide(versionId, "ja") ?? getChapterGuide(versionId, "en");

  if (!guide) return null;

  return {
    eyebrow: content.subtitle,
    summary: `本章の中核増分は「${content.coreAddition}」です。${content.keyInsight}`,
    sections: [
      {
        title: JA_FALLBACK_TEXT.sectionA,
        body: `ここで本当に新しく成立するのは「${content.coreAddition}」です。読むときは実装の枝葉よりも、この構造が主線のどこへ差し込み、どの状態を増やし、どう主ループへ戻るかを先に押さえます。`,
      },
      {
        title: JA_FALLBACK_TEXT.sectionB,
        body: `${guide.focus} ${guide.confusion}`,
      },
      {
        title: JA_FALLBACK_TEXT.sectionC,
        body: `${guide.goal} 一度に全部を再現しようとするより、この章で増えた最小構造だけを独立に成立させてから次へ進む方が理解も実装も安定します。`,
      },
    ],
    flowLabel: JA_FALLBACK_TEXT.flowLabel,
    flow: [...JA_FALLBACK_TEXT.flow],
    cautionLabel: JA_FALLBACK_TEXT.cautionLabel,
    caution: guide.confusion,
    outcomeLabel: JA_FALLBACK_TEXT.outcomeLabel,
    outcome: guide.goal,
  };
}

export function GenericSessionOverview({
  version,
  title,
}: {
  version: string;
  title?: string;
}) {
  const locale = useLocale();
  const tLayer = useTranslations("layer_labels");
  const tSession = useTranslations("sessions");
  const meta = VERSION_META[version];
  const content = getVersionContent(version, locale);

  if (!meta) return null;

  const copy =
    locale === "zh"
      ? ZH_COPY[version] ?? EN_COPY[version]
      : locale === "ja"
        ? buildJapaneseFallbackOverview(version) ?? EN_COPY[version]
        : EN_COPY[version];
  const coreAdditionLabel =
    locale === "zh"
      ? "核心增量"
      : locale === "ja"
        ? "中核の追加"
        : "Core Addition";

  if (!copy) return null;

  return (
    <section className="min-h-[500px] space-y-4">
      <div
        className={`overflow-hidden rounded-[28px] border border-[var(--color-border)] bg-[var(--color-bg)] shadow-sm ring-1 ${RING_CLASSES[meta.layer]}`}
      >
        <div
          className={`relative overflow-hidden bg-gradient-to-br ${SURFACE_CLASSES[meta.layer]} px-5 py-6 sm:px-6`}
        >
          <div className="absolute right-[-40px] top-[-40px] h-36 w-36 rounded-full bg-white/40 blur-3xl dark:bg-white/5" />
          <div className="relative">
            <div className="flex flex-wrap items-center gap-2">
              <LayerBadge layer={meta.layer}>{tLayer(meta.layer)}</LayerBadge>
              <span className="rounded-full border border-white/50 bg-white/70 px-2.5 py-1 text-[11px] font-medium text-zinc-700 backdrop-blur dark:border-white/10 dark:bg-zinc-950/40 dark:text-zinc-300">
                {copy.eyebrow}
              </span>
            </div>
            <h2 className="mt-4 text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {title || tSession(version)}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-zinc-700 dark:text-zinc-300">
              {copy.summary}
            </p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-zinc-200/70 bg-white/85 px-3 py-2 text-xs text-zinc-600 backdrop-blur dark:border-zinc-700/70 dark:bg-zinc-950/50 dark:text-zinc-300">
              <span className="font-medium">{coreAdditionLabel}</span>
              <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
                {content.coreAddition}
              </span>
            </div>
          </div>
        </div>

        {hasLateStageTeachingMap(version) && (
          <div className="px-5 pt-5 sm:px-6">
            <LateStageTeachingMap version={version} />
          </div>
        )}

        <div className="grid gap-3 px-5 py-5 sm:grid-cols-3 sm:px-6">
          {copy.sections.map((section, index) => (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08, duration: 0.32 }}
              className="rounded-2xl border border-zinc-200/80 bg-white/90 p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/60"
            >
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400 dark:text-zinc-500">
                0{index + 1}
              </div>
              <h3 className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {section.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                {section.body}
              </p>
            </motion.div>
          ))}
        </div>

        <div className="grid gap-4 border-t border-[var(--color-border)] px-5 py-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)] sm:px-6">
          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
            <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              {copy.flowLabel}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {copy.flow.map((step, index) => (
                <div key={step} className="contents">
                  <motion.div
                    initial={{ opacity: 0, scale: 0.94 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.07, duration: 0.28 }}
                    className="inline-flex items-center rounded-full border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-700 shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
                  >
                    <span className="mr-2 font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
                      {index + 1}
                    </span>
                    {step}
                  </motion.div>
                  {index < copy.flow.length - 1 && (
                    <span className="text-zinc-300 dark:text-zinc-600">-&gt;</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-2xl border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800 dark:bg-zinc-950/60">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                {copy.cautionLabel}
              </div>
              <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                {copy.caution}
              </p>
            </div>
            <div className="rounded-2xl border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800 dark:bg-zinc-950/60">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                {copy.outcomeLabel}
              </div>
              <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                {copy.outcome}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
