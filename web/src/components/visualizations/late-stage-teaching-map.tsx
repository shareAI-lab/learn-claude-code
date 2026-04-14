"use client";

import { motion } from "framer-motion";
import { VERSION_META, type VersionId } from "@/lib/constants";
import { useLocale } from "@/lib/i18n";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";

type LateStageVersion =
  | "s07"
  | "s08"
  | "s09"
  | "s10"
  | "s11"
  | "s12"
  | "s13"
  | "s14"
  | "s15"
  | "s16"
  | "s17"
  | "s18"
  | "s19";

type LocaleText = {
  zh: string;
  en: string;
  ja?: string;
};

interface ScenarioLane {
  id: string;
  label: LocaleText;
  note: LocaleText;
}

interface ScenarioNode {
  id: string;
  lane: string;
  label: LocaleText;
  detail: LocaleText;
}

interface ScenarioRecord {
  id: string;
  label: LocaleText;
  note: LocaleText;
}

interface ScenarioStep {
  title: LocaleText;
  description: LocaleText;
  activeNodes: string[];
  activeRecords: string[];
  boundary: LocaleText;
  writeBack: LocaleText;
}

interface ChapterScenario {
  lanes: ScenarioLane[];
  nodes: ScenarioNode[];
  records: ScenarioRecord[];
  steps: ScenarioStep[];
}

const UI_TEXT = {
  label: {
    zh: "机制演示",
    en: "Mechanism Walkthrough",
    ja: "メカニズムの実演",
  },
  title: {
    zh: "把这一章真正新增的车道、记录和回流顺序分开看",
    en: "Separate the new lanes, records, and write-back order introduced by this chapter",
    ja: "この章で増えたレーン、レコード、回流順を切り分けて見る",
  },
  body: {
    zh: "中后段最容易拧巴的点，不是名词多，而是多个层同时动起来。先看这张演示图，再进正文，能更快守住“谁在决策、谁在执行、谁在记录、最后怎么回到主循环”。",
    en: "The middle and late chapters become confusing not because they use more terms, but because several layers move at once. Read this walkthrough first to keep straight who decides, who executes, who records state, and how control returns to the main loop.",
    ja: "中盤以降が難しくなるのは用語が増えるからではなく、複数の層が同時に動き始めるからです。先にこの図を見ると、誰が判断し、誰が実行し、誰が記録し、どう主ループへ戻るかを保ちやすくなります。",
  },
  systemLanes: {
    zh: "系统车道",
    en: "System Lanes",
    ja: "システムレーン",
  },
  activePath: {
    zh: "当前主线",
    en: "Current Mainline",
    ja: "現在の主線",
  },
  activeRecords: {
    zh: "这一步真正活跃的记录",
    en: "Records Active in This Step",
    ja: "この段階で本当に動くレコード",
  },
  boundary: {
    zh: "这一步要守住的边界",
    en: "Boundary to Protect Here",
    ja: "この段階で守るべき境界",
  },
  writeBack: {
    zh: "最后怎么回到主线",
    en: "How Control Returns to the Mainline",
    ja: "最後にどう主線へ戻るか",
  },
  inactiveRecord: {
    zh: "当前未激活",
    en: "Not active in this step",
    ja: "この段階では未使用",
  },
} as const;

const ACCENT_CLASSES: Record<
  "core" | "hardening" | "runtime" | "platform",
  {
    tint: string;
    ring: string;
    soft: string;
    pill: string;
    border: string;
  }
> = {
  core: {
    tint: "from-blue-500/18 via-blue-500/8 to-transparent",
    ring: "ring-blue-500/20",
    soft: "bg-blue-500/10 text-blue-700 dark:text-blue-200",
    pill: "border-blue-300/80 bg-blue-50/90 text-blue-700 dark:border-blue-900/70 dark:bg-blue-950/30 dark:text-blue-200",
    border: "border-blue-200/80 dark:border-blue-900/60",
  },
  hardening: {
    tint: "from-emerald-500/18 via-emerald-500/8 to-transparent",
    ring: "ring-emerald-500/20",
    soft: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-200",
    pill: "border-emerald-300/80 bg-emerald-50/90 text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/30 dark:text-emerald-200",
    border: "border-emerald-200/80 dark:border-emerald-900/60",
  },
  runtime: {
    tint: "from-amber-500/18 via-amber-500/8 to-transparent",
    ring: "ring-amber-500/20",
    soft: "bg-amber-500/10 text-amber-700 dark:text-amber-200",
    pill: "border-amber-300/80 bg-amber-50/90 text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200",
    border: "border-amber-200/80 dark:border-amber-900/60",
  },
  platform: {
    tint: "from-rose-500/18 via-rose-500/8 to-transparent",
    ring: "ring-rose-500/20",
    soft: "bg-rose-500/10 text-rose-700 dark:text-rose-200",
    pill: "border-rose-300/80 bg-rose-50/90 text-rose-700 dark:border-rose-900/70 dark:bg-rose-950/30 dark:text-rose-200",
    border: "border-rose-200/80 dark:border-rose-900/60",
  },
};

function pick(locale: string, text: LocaleText): string {
  if (locale === "zh") return text.zh;
  if (locale === "ja") return text.ja ?? text.en;
  return text.en;
}

function l(zh: string, en: string, ja?: string): LocaleText {
  return { zh, en, ja };
}

const SCENARIOS: Record<LateStageVersion, ChapterScenario> = {
  s07: {
    lanes: [
      { id: "input", label: l("模型入口", "Model Entry", "モデル入口"), note: l("模型先提出动作意图。", "The model proposes an action first.", "モデルが先に行動意図を出します。") },
      { id: "control", label: l("权限控制面", "Permission Plane", "権限制御面"), note: l("这里决定 allow / ask / deny。", "This is where allow / ask / deny is decided.", "ここで allow / ask / deny を決めます。") },
      { id: "runtime", label: l("执行面", "Execution Plane", "実行面"), note: l("只有放行后才真正触发工具。", "Tools run only after approval.", "許可されたあとで初めて tool が動きます。") },
      { id: "history", label: l("消息回流", "Message Write-back", "メッセージ回流"), note: l("所有结果都要回写给主循环。", "Every result must write back to the main loop.", "すべての結果は主ループへ回流します。") },
    ],
    nodes: [
      { id: "intent", lane: "input", label: l("工具意图", "Tool Intent", "tool 意図"), detail: l("模型想执行某个动作。", "The model wants to perform an action.", "モデルが何かを実行したがっています。") },
      { id: "normalize", lane: "control", label: l("意图规范化", "Normalize Intent", "意図正規化"), detail: l("先抽出动作、目标和风险。", "Extract action, target, and risk first.", "行動・対象・危険度を先に抽出します。") },
      { id: "policy", lane: "control", label: l("规则与模式", "Rules + Mode", "ルールとモード"), detail: l("deny / mode / allow 顺序判断。", "Evaluate deny / mode / allow in order.", "deny / mode / allow を順番に判定します。") },
      { id: "decision", lane: "control", label: l("权限决策", "Permission Decision", "権限判断"), detail: l("输出 allow / ask / deny。", "Return allow / ask / deny.", "allow / ask / deny を返します。") },
      { id: "tool", lane: "runtime", label: l("实际执行", "Tool Execution", "実行"), detail: l("只有 allow 时才落到工具。", "Execution happens only after allow.", "allow のときだけ tool 実行へ進みます。") },
      { id: "writeback", lane: "history", label: l("结构化回写", "Structured Write-back", "構造化回写"), detail: l("拒绝、询问、执行结果都回到主循环。", "Deny, ask, or execute results all return to the loop.", "拒否・確認・実行結果はすべて主ループへ戻ります。") },
    ],
    records: [
      { id: "normalized-intent", label: l("NormalizedIntent", "NormalizedIntent", "NormalizedIntent"), note: l("供权限层统一判断的对象。", "A normalized object the policy layer can inspect.", "policy 層が統一的に見られる正規化オブジェクトです。") },
      { id: "permission-rule", label: l("PermissionRule", "PermissionRule", "PermissionRule"), note: l("定义匹配条件和行为。", "Defines match conditions and behavior.", "一致条件と挙動を定義します。") },
      { id: "permission-decision", label: l("PermissionDecision", "PermissionDecision", "PermissionDecision"), note: l("把 allow / ask / deny 带着原因写回。", "Writes allow / ask / deny back with a reason.", "理由付きで allow / ask / deny を回写します。") },
    ],
    steps: [
      {
        title: l("先把动作变成可判断对象", "Turn the action into a policy object", "行動を policy 判定可能な形へ変える"),
        description: l("权限章第一步不是拦截命令字符串，而是把模型意图翻译成规则层看得懂的统一对象。", "The first step is not blocking raw command strings. It is translating model intent into a uniform object the policy layer can understand.", "最初にやるのは生の文字列ブロックではなく、モデル意図を policy 層が分かる統一オブジェクトへ翻訳することです。"),
        activeNodes: ["intent", "normalize"],
        activeRecords: ["normalized-intent"],
        boundary: l("不要直接拿原始 tool call 执行。先规范化，后决策。", "Do not execute raw tool calls directly. Normalize first, decide second.", "生の tool call をそのまま実行しない。先に正規化し、その後で判断します。"),
        writeBack: l("规范化结果继续送进权限链，不直接落到工具。", "The normalized intent continues into the permission chain, not straight into execution.", "正規化結果はそのまま実行へ行かず、permission chain へ進みます。"),
      },
      {
        title: l("规则和模式一起决定权限", "Rules and mode decide together", "ルールとモードが一緒に権限を決める"),
        description: l("deny 规则、模式限制和 allow 规则构成完整权限管道，重点是顺序，不是零散 if。", "Deny rules, mode restrictions, and allow rules form one pipeline. The important part is their order, not scattered if statements.", "deny rule・mode 制限・allow rule が 1 本の pipeline を作ります。大事なのは零散な if ではなく順序です。"),
        activeNodes: ["normalize", "policy", "decision"],
        activeRecords: ["permission-rule", "permission-decision"],
        boundary: l("权限系统是独立控制面，不要把判断逻辑拆散到每个工具里。", "The permission system is its own control plane. Do not scatter this logic into every tool.", "permission system は独立した control plane です。各 tool に散らさないでください。"),
        writeBack: l("决策结果先形成 PermissionDecision，再决定是否往执行面流动。", "PermissionDecision is produced before anything flows to execution.", "実行面へ進む前に、まず PermissionDecision が作られます。"),
      },
      {
        title: l("只有 allow 才触发工具", "Only allow reaches execution", "allow のときだけ実行へ進む"),
        description: l("执行面只处理被允许的动作。ask 和 deny 同样是结果，但它们不会落到工具处理器。", "The execution plane only handles allowed actions. Ask and deny are also outcomes, but they do not enter the tool handler.", "実行面は許可された行動だけを処理します。ask と deny も結果ですが、tool handler へは入りません。"),
        activeNodes: ["decision", "tool"],
        activeRecords: ["permission-decision"],
        boundary: l("权限层和执行层是两层，不要把询问用户和真正运行工具混成一条路。", "Permission and execution are two layers. Do not mix user confirmation with real tool execution.", "permission と execution は別層です。ユーザー確認と実行を同じ道にしないでください。"),
        writeBack: l("allow 通过后才进入工具处理器，工具输出仍要再回写。", "Only after allow does execution begin, and tool output still writes back afterward.", "allow のあとで初めて tool が動き、その結果もさらに回写されます。"),
      },
      {
        title: l("所有权限结果都回到主循环", "Every permission outcome returns to the loop", "あらゆる権限結果が主ループへ戻る"),
        description: l("教学上最重要的是：拒绝、询问、执行成功，都必须变成模型下一步能看见的事实。", "The critical teaching point is that deny, ask, and successful execution all become facts the model can see on the next turn.", "拒否・確認・成功のすべてが、次のターンでモデルが見られる事実になることが重要です。"),
        activeNodes: ["decision", "tool", "writeback"],
        activeRecords: ["permission-decision"],
        boundary: l("不要让权限判断静默消失，否则模型不会知道为什么没执行。", "Do not let permission outcomes disappear silently, or the model will not know why something did not run.", "permission の結果を黙って消さないこと。そうしないとモデルはなぜ実行されなかったか分かりません。"),
        writeBack: l("最终回流的是结构化 permission result 或 tool result，它们一起维持下一轮推理。", "The loop receives either a structured permission result or a tool result, and both support the next reasoning step.", "最終的に戻るのは構造化 permission result か tool result であり、どちらも次の推論を支えます。"),
      },
    ],
  },
  s08: {
    lanes: [
      { id: "loop", label: l("主循环", "Main Loop", "主ループ"), note: l("核心状态推进仍留在这里。", "Core state progression stays here.", "中核の状態遷移はここに残ります。") },
      { id: "events", label: l("生命周期事件", "Lifecycle Events", "ライフサイクルイベント"), note: l("固定时机发出结构化事件。", "Structured events are emitted at fixed moments.", "固定タイミングで構造化イベントが出ます。") },
      { id: "hooks", label: l("Hook 侧车", "Hook Sidecars", "Hook サイドカー"), note: l("审计、追踪、策略副作用挂在这里。", "Audit, tracing, and policy side effects live here.", "監査・追跡・副作用はここに乗ります。") },
      { id: "history", label: l("结果回流", "Result Write-back", "結果回流"), note: l("副作用和主线结果都可回写。", "Both side effects and mainline results can write back.", "副作用も主線結果も回写できます。") },
    ],
    nodes: [
      { id: "advance", lane: "loop", label: l("推进主线", "Advance Loop", "主線を進める"), detail: l("循环继续负责主状态。", "The loop still owns the main state.", "主状態は引き続きループが持ちます。") },
      { id: "emit", lane: "events", label: l("发事件", "Emit Event", "イベント送出"), detail: l("在 pre_tool / post_tool / on_error 发事件。", "Emit events at pre_tool / post_tool / on_error.", "pre_tool / post_tool / on_error でイベントを出します。") },
      { id: "registry", lane: "hooks", label: l("Hook 注册表", "Hook Registry", "Hook レジストリ"), detail: l("统一管理谁来观察。", "One registry decides who observes.", "誰が観測するかを一元管理します。") },
      { id: "audit", lane: "hooks", label: l("日志/审计", "Audit / Trace", "監査 / 追跡"), detail: l("旁路能力不侵入主逻辑。", "Side effects stay out of the core loop.", "副作用は主ロジックへ侵入しません。") },
      { id: "tool-path", lane: "loop", label: l("核心执行", "Core Execution", "コア実行"), detail: l("主循环照常执行本轮工作。", "The main loop still runs the actual work.", "主ループは通常どおり本輪の仕事を実行します。") },
      { id: "writeback", lane: "history", label: l("统一回写", "Unified Write-back", "統一回写"), detail: l("结果与旁路观察都能进入历史。", "Results and observations can both enter history.", "結果も観測も履歴へ入れます。") },
    ],
    records: [
      { id: "hook-event", label: l("HookEvent", "HookEvent", "HookEvent"), note: l("固定字段的事件对象。", "A structured event object with stable fields.", "安定したフィールドを持つイベントオブジェクトです。") },
      { id: "hook-result", label: l("HookResult", "HookResult", "HookResult"), note: l("Hook 处理后的副作用结果。", "The side-effect result from a hook.", "Hook が返す副作用結果です。") },
      { id: "hook-registry", label: l("HookRegistry", "HookRegistry", "HookRegistry"), note: l("统一登记和分发 Hook。", "Registers and dispatches hooks centrally.", "Hook を一元的に登録・配布します。") },
    ],
    steps: [
      {
        title: l("先确定事件边界", "Define the event boundary first", "先にイベント境界を定義する"),
        description: l("主循环不是随便让外部逻辑插进来，而是在固定时机主动发出 HookEvent。", "The loop does not allow random code to jump in. It emits HookEvent at stable moments.", "主ループは場当たり的に外部ロジックを差し込むのではなく、固定時点で HookEvent を出します。"),
        activeNodes: ["advance", "emit"],
        activeRecords: ["hook-event"],
        boundary: l("先定义什么时候能观察，再定义谁来观察。", "Define when the loop is observable before deciding who observes it.", "誰が観測するかの前に、いつ観測可能かを定義します。"),
        writeBack: l("事件不是终点，它会把本轮状态送到 Hook 侧车继续处理。", "The event is not the endpoint. It hands the current state to sidecar hooks.", "イベントは終点ではなく、このターンの状態を sidecar hook へ渡します。"),
      },
      {
        title: l("Hook 通过注册表挂上去", "Hooks attach through a registry", "Hook は registry 経由で接続する"),
        description: l("多个 Hook 可以共享同一事件契约，主循环不需要知道每个 Hook 的内部细节。", "Multiple hooks can share the same contract, and the loop does not need to know their internal details.", "複数 Hook が同じ契約を共有でき、主ループは各 Hook の中身を知る必要がありません。"),
        activeNodes: ["emit", "registry", "audit"],
        activeRecords: ["hook-event", "hook-registry"],
        boundary: l("不要把 Hook 写成另一套主循环。它应该观察和补充，而不是接管。", "Do not turn hooks into a second main loop. They should observe and extend, not take over.", "Hook を第2の主ループにしないでください。観測と補助が役目です。"),
        writeBack: l("Hook 产出的副作用结果仍然经统一入口回到系统。", "Hook side effects still return through a unified entry path.", "Hook の副作用結果も統一入口からシステムへ戻ります。"),
      },
      {
        title: l("主线继续执行，Hook 在旁边观察", "The mainline keeps running while hooks observe", "主線は進み、Hook は横で観測する"),
        description: l("Hook 的价值不是阻止主线，而是把审计、追踪、策略副作用和核心执行拆成两条心智线。", "Hooks are valuable because they separate auditing, tracing, and policy side effects from the core execution path.", "Hook の価値は主線を止めることではなく、監査や追跡をコア実行から分離することです。"),
        activeNodes: ["registry", "audit", "tool-path"],
        activeRecords: ["hook-result"],
        boundary: l("副作用和主流程必须解耦，否则每个工具都会被日志逻辑污染。", "Side effects must stay decoupled from the main flow or every tool gets polluted by observability logic.", "副作用と主処理を分離しないと、全 tool が観測ロジックで汚れてしまいます。"),
        writeBack: l("核心执行结果和 Hook 副作用都汇到统一回写层。", "Core execution and hook side effects both converge in one write-back layer.", "コア実行結果と Hook 副作用は統一回写層へ集まります。"),
      },
      {
        title: l("副作用结果也能被下一轮看见", "Side effects can be visible to later turns", "副作用結果も次のターンで見える"),
        description: l("一旦需要审计、追踪或修复提示，Hook 产物也应该像主线结果那样成为下一轮可见事实。", "When auditing, tracing, or repair hints matter, hook output should become visible facts for later turns just like core results.", "監査・追跡・修復ヒントが重要なら、Hook 出力も主線結果と同じく後続ターンで見える事実にすべきです。"),
        activeNodes: ["tool-path", "audit", "writeback"],
        activeRecords: ["hook-result"],
        boundary: l("Hook 不是只给人类看日志，它也可以给系统留下可消费的旁路信息。", "Hooks are not just for human-readable logs. They can also leave machine-consumable side information.", "Hook は人間向けログだけではなく、システムが消費できる側路情報も残せます。"),
        writeBack: l("统一回写后，下一轮既知道主线结果，也知道旁路观察到了什么。", "After unified write-back, the next turn can see both the mainline result and what the sidecars observed.", "統一回写のあと、次のターンは主線結果と sidecar の観測結果の両方を見られます。"),
      },
    ],
  },
  s09: {
    lanes: [
      { id: "turn", label: l("新一轮", "New Turn", "新しいターン"), note: l("当前请求进入系统。", "The current request enters the system.", "現在のリクエストがシステムへ入ります。") },
      { id: "memory", label: l("记忆层", "Memory Layer", "記憶層"), note: l("跨会话事实只在这里保存。", "Cross-session facts live here.", "会話をまたぐ事実はここに残ります。") },
      { id: "prompt", label: l("输入装配", "Prompt Assembly", "入力組み立て"), note: l("相关记忆在这里重新进入当前轮。", "Relevant memory re-enters the current turn here.", "関連記憶はここで今のターンへ戻ります。") },
      { id: "writeback", label: l("提炼回写", "Extraction + Persist", "抽出と保存"), note: l("只有 durable fact 才会写回。", "Only durable facts are written back.", "durable fact だけが書き戻されます。") },
    ],
    nodes: [
      { id: "request", lane: "turn", label: l("当前请求", "Current Request", "現在の要求"), detail: l("新任务开始。", "A new task begins.", "新しい仕事が始まります。") },
      { id: "load", lane: "memory", label: l("载入相关记忆", "Load Relevant Memory", "関連記憶を読む"), detail: l("只挑和当前任务相关的事实。", "Load only the facts relevant to this task.", "この仕事に関係する事実だけを読みます。") },
      { id: "assemble", lane: "prompt", label: l("组装输入", "Assemble Prompt", "入力を組み立てる"), detail: l("把记忆和当前上下文并列放进去。", "Place memory beside the live context.", "記憶を現在の文脈と並べて入れます。") },
      { id: "work", lane: "prompt", label: l("完成当前工作", "Do the Work", "現在の仕事を進める"), detail: l("模型和工具继续本轮工作。", "The model and tools continue the current work.", "モデルと tool がこのターンの仕事を進めます。") },
      { id: "extract", lane: "writeback", label: l("提炼 durable fact", "Extract Durable Facts", "durable fact を抽出"), detail: l("不是所有内容都值得记。", "Not everything deserves to be remembered.", "すべてを覚えるわけではありません。") },
      { id: "persist", lane: "writeback", label: l("写回记忆库", "Persist Memory", "記憶へ保存"), detail: l("跨会话仍重要的内容才进入 store。", "Only facts that still matter across sessions enter the store.", "会話をまたいでも重要な内容だけが store に入ります。") },
    ],
    records: [
      { id: "memory-entry", label: l("MemoryEntry", "MemoryEntry", "MemoryEntry"), note: l("长期保存的事实条目。", "A durable fact entry.", "長期保存される事実エントリです。") },
      { id: "memory-query", label: l("MemoryQuery", "MemoryQuery", "MemoryQuery"), note: l("决定本轮要读哪些记忆。", "Determines which memory to load for this turn.", "このターンで読む記憶を決めます。") },
      { id: "memory-candidate", label: l("MemoryCandidate", "MemoryCandidate", "MemoryCandidate"), note: l("本轮结束后候选写回事实。", "A candidate fact extracted after the turn.", "ターン終了後に候補として抽出された事実です。") },
    ],
    steps: [
      {
        title: l("先读和当前任务有关的记忆", "Load only memory relevant to the current task", "現在の仕事に関係する記憶だけ読む"),
        description: l("记忆系统的第一护栏是少而准。不是每次都把整个长期记忆塞回 prompt。", "The first guardrail of memory is being selective. You do not dump the entire memory store back into every prompt.", "記憶システムの第一ガードレールは少なく正確であることです。毎回すべてを prompt に戻しません。"),
        activeNodes: ["request", "load"],
        activeRecords: ["memory-query", "memory-entry"],
        boundary: l("长期记忆不是上下文备份，它是本轮按需取回的知识层。", "Long-term memory is not a context backup. It is a knowledge layer loaded on demand.", "長期記憶は文脈バックアップではなく、必要時だけ戻す知識層です。"),
        writeBack: l("读到的记忆随后进入输入装配，而不是直接覆盖当前上下文。", "Loaded memory proceeds into prompt assembly instead of replacing the live context.", "読み込んだ記憶は現在文脈を置き換えず、入力組み立てへ進みます。"),
      },
      {
        title: l("记忆和当前上下文并列进入输入", "Memory and live context enter the prompt side by side", "記憶と現在文脈を並列で入力へ入れる"),
        description: l("messages[] 负责当前过程，memory 负责跨会话事实。真正关键是两者分层，不是谁取代谁。", "messages[] carries the live process while memory carries cross-session facts. The key is layering them, not replacing one with the other.", "messages[] は現在の過程、memory は会話をまたぐ事実を持ちます。重要なのは置き換えではなく分層です。"),
        activeNodes: ["load", "assemble", "work"],
        activeRecords: ["memory-entry"],
        boundary: l("记忆不能取代当前上下文，否则模型会失去正在做什么的连贯性。", "Memory cannot replace live context, or the model loses continuity about what it is currently doing.", "memory が現在文脈を置き換えると、モデルは今何をしているかの連続性を失います。"),
        writeBack: l("模型完成工作后，才会进入下一步提炼哪些内容值得留下。", "Only after the work turn finishes do you ask what deserves to persist.", "仕事ターンが終わってから、何を残すべきかを考えます。"),
      },
      {
        title: l("完成工作后再提炼 durable fact", "Extract durable facts only after the work turn", "仕事後に durable fact を抽出する"),
        description: l("写记忆最稳的时机是任务阶段性结束后。这样你才看得见什么是稳定事实，什么只是临时输出。", "The safest moment to write memory is after a meaningful work segment completes, when you can tell durable facts from temporary output.", "記憶を書き出す最も安定したタイミングは、意味のある仕事区間が終わったあとです。"),
        activeNodes: ["work", "extract"],
        activeRecords: ["memory-candidate"],
        boundary: l("不是所有模型输出都值得长期保留。先过滤，再决定要不要写入。", "Not every model output deserves long-term storage. Filter first, then decide whether to persist.", "すべての出力を長期保存しない。先に絞り込みます。"),
        writeBack: l("提炼出的 candidate 会进入记忆库，而当前轮上下文继续留在 messages[]。", "Extracted candidates go to the memory store while the live process stays in messages[].", "抽出候補は memory store へ、現在の過程は messages[] に残ります。"),
      },
      {
        title: l("只有值得跨会话保留的事实才入库", "Only cross-session facts enter the memory store", "会話をまたいで残す価値のある事実だけ入庫する"),
        description: l("记忆系统真正教的是取舍。什么值得留下，决定了后续 agent 是更稳还是更乱。", "The deepest lesson of memory is selection. What you keep determines whether later sessions become steadier or noisier.", "記憶システムの本質は選別です。何を残すかで、次回以降が安定するか騒がしくなるかが決まります。"),
        activeNodes: ["extract", "persist"],
        activeRecords: ["memory-candidate", "memory-entry"],
        boundary: l("长期记忆只收 durable fact，不收一整段对话流水账。", "Long-term memory should store durable facts, not full chat transcripts.", "長期記憶は durable fact を保存し、会話の逐語録は保存しません。"),
        writeBack: l("保存后的 MemoryEntry 会在未来相关任务中被重新装配进输入。", "Persisted MemoryEntry can be reloaded into future relevant turns.", "保存された MemoryEntry は将来の関連ターンで再び入力へ組み込まれます。"),
      },
    ],
  },
  s10: {
    lanes: [
      { id: "policy", label: l("稳定规则", "Stable Policy", "安定ルール"), note: l("长期不变的系统约束。", "Long-lived system rules.", "長期的に変わらない制約です。") },
      { id: "runtime", label: l("运行时状态", "Runtime State", "ランタイム状態"), note: l("当前目录、工具、待办、任务等。", "Current workspace, tools, todos, tasks, and more.", "現在の workspace、tool、todo、task などです。") },
      { id: "assembly", label: l("装配流水线", "Assembly Pipeline", "組み立てパイプライン"), note: l("决定按什么顺序拼输入。", "Decides the assembly order.", "どんな順番で入力を組むかを決めます。") },
      { id: "loop", label: l("模型可见输入", "Model-Visible Input", "モデル可視入力"), note: l("真正给模型看的只有最后产物。", "The model only sees the final assembled input.", "モデルが見るのは最終的に組み上がった入力だけです。") },
    ],
    nodes: [
      { id: "stable-policy", lane: "policy", label: l("角色/底线", "Role + Hard Rules", "役割 / ハードルール"), detail: l("稳定内容单独存在。", "Stable content lives in its own layer.", "安定内容は独立して置きます。") },
      { id: "tools", lane: "runtime", label: l("工具信息", "Tool Catalog", "ツール情報"), detail: l("本轮可用工具集。", "The tool set available for this turn.", "このターンで使える tool 集です。") },
      { id: "memory", lane: "runtime", label: l("记忆与任务", "Memory + Task State", "記憶と task 状態"), detail: l("动态上下文分块进入。", "Dynamic context enters in distinct blocks.", "動的文脈が分割された状態で入ります。") },
      { id: "assemble", lane: "assembly", label: l("PromptBuilder", "PromptBuilder", "PromptBuilder"), detail: l("显式拼装顺序。", "Explicit assembly order.", "明示的な組み立て順です。") },
      { id: "final-input", lane: "loop", label: l("最终输入", "Final Input", "最終入力"), detail: l("模型真正看到的单一入口。", "The single input the model really sees.", "モデルが実際に見る単一の入口です。") },
      { id: "response", lane: "loop", label: l("模型响应", "Model Response", "モデル応答"), detail: l("下一轮又会回到这条装配链。", "The next turn returns to this pipeline again.", "次のターンでもこの組み立て列に戻ります。") },
    ],
    records: [
      { id: "prompt-parts", label: l("PromptParts", "PromptParts", "PromptParts"), note: l("系统输入的分块容器。", "Structured prompt fragments.", "system 入力の断片コンテナです。") },
      { id: "prompt-builder", label: l("PromptBuilder", "PromptBuilder", "PromptBuilder"), note: l("定义装配顺序。", "Defines the prompt assembly order.", "組み立て順を定義します。") },
      { id: "runtime-context", label: l("RuntimeContext", "RuntimeContext", "RuntimeContext"), note: l("本轮动态注入的上下文。", "Dynamic runtime context for the current turn.", "このターンで動的注入される文脈です。") },
    ],
    steps: [
      {
        title: l("先把稳定规则单独拿出来", "Pull stable policy into its own layer first", "安定ルールを独立層へ出す"),
        description: l("系统提示词最容易讲糊的地方，是把所有内容揉成一大段字符串。教学上要先拆出稳定规则。", "The biggest prompt-teaching mistake is flattening everything into one giant string. Start by separating stable policy.", "prompt 教学で最も混乱しやすいのは、全部を巨大な文字列へ潰すことです。まず安定ルールを分離します。"),
        activeNodes: ["stable-policy"],
        activeRecords: ["prompt-parts"],
        boundary: l("稳定规则和当前任务状态不是一回事，必须分层。", "Stable policy and current task state are not the same thing and must stay separate.", "安定ルールと現在の task 状態は別物です。"),
        writeBack: l("稳定规则不会直接被模型消费，它会进入 PromptBuilder 参与最终装配。", "Stable policy is not consumed alone; it enters the PromptBuilder for final assembly.", "安定ルールは単独消費されず、PromptBuilder で最終組み立てへ入ります。"),
      },
      {
        title: l("动态状态按块进入 PromptBuilder", "Dynamic state enters the PromptBuilder in blocks", "動的状態をブロック単位で PromptBuilder へ入れる"),
        description: l("工具、记忆、待办、错误恢复提示都属于动态片段。重要的是它们要有清楚来源和顺序。", "Tools, memory, todos, and recovery hints are dynamic fragments. What matters is that they have clear sources and order.", "tool・memory・todo・recovery hint は動的断片です。重要なのは出所と順序が明確であることです。"),
        activeNodes: ["tools", "memory", "assemble"],
        activeRecords: ["runtime-context", "prompt-builder"],
        boundary: l("不要把动态状态硬拼到稳定规则里，否则后续很难解释清楚哪些东西是临时的。", "Do not hardcode dynamic state into stable policy, or you lose the ability to explain what is temporary.", "動的状態を安定ルールへ埋め込むと、一時情報がどれか説明しづらくなります。"),
        writeBack: l("所有动态块按顺序进入 PromptBuilder，形成最终模型输入。", "All dynamic blocks flow into the PromptBuilder in order to create the final input.", "すべての動的ブロックが順番に PromptBuilder へ入り、最終入力になります。"),
      },
      {
        title: l("模型真正看到的是最终装配产物", "The model sees the assembled product, not the parts", "モデルが見るのは最終組み立て結果"),
        description: l("教学上要让读者意识到：模型不是直接读取工具系统或记忆库，它只看到最终输入。", "Readers should understand that the model does not directly inspect the tool system or memory store. It only sees the assembled input.", "モデルは tool system や memory store を直接見るのではなく、組み上がった最終入力だけを見ます。"),
        activeNodes: ["assemble", "final-input"],
        activeRecords: ["prompt-builder", "prompt-parts"],
        boundary: l("输入装配本身就是控制面，因为它决定模型这一轮能看到什么。", "Prompt assembly is itself a control plane because it decides what the model can see this turn.", "入力組み立て自体が control plane です。モデルがこのターンで何を見られるかを決めるからです。"),
        writeBack: l("最终输入喂给模型后，系统才得到下一步动作或文本响应。", "Only after the final input is built does the system get the model's next action or text response.", "最終入力を渡したあとで、モデルの次の行動や応答が返ります。"),
      },
      {
        title: l("下一轮又回到同一装配管道", "The next turn re-enters the same assembly pipeline", "次のターンも同じ組み立て経路へ戻る"),
        description: l("这章真正建立的是输入控制面。每一轮都在重复“取规则、取动态状态、装配、调用模型”这条主线。", "This chapter really establishes an input control plane. Every turn repeats the same mainline: gather rules, gather runtime state, assemble, call the model.", "この章が作るのは入力 control plane です。毎ターン、ルール収集・動的状態収集・組み立て・モデル呼び出しを繰り返します。"),
        activeNodes: ["final-input", "response", "stable-policy"],
        activeRecords: ["prompt-builder"],
        boundary: l("Prompt pipeline 不是一次性的字符串拼接，而是会在每轮反复运行的系统流程。", "The prompt pipeline is not one-off string concatenation. It is a system flow that runs every turn.", "prompt pipeline は一回限りの文字列連結ではなく、毎ターン動くシステム流程です。"),
        writeBack: l("模型响应会更新当前状态，然后再次进入 PromptBuilder 所在的装配链。", "The model response updates the live state and then re-enters the same prompt-building chain.", "モデル応答は現在状態を更新し、その後また同じ prompt-building chain に戻ります。"),
      },
    ],
  },
  s11: {
    lanes: [
      { id: "runtime", label: l("执行结果", "Execution Result", "実行結果"), note: l("本轮执行到了成功或失败。", "The current execution finishes in success or failure.", "この実行は成功か失敗で一区切りします。") },
      { id: "recovery", label: l("恢复分支", "Recovery Branch", "回復分岐"), note: l("失败后要分类再处理。", "Failures must be classified before recovery.", "失敗は分類してから回復します。") },
      { id: "state", label: l("续行状态", "Continuation State", "続行状態"), note: l("继续的原因要写清。", "The reason for continuing must be explicit.", "なぜ続行するかを明示します。") },
      { id: "loop", label: l("主循环", "Main Loop", "主ループ"), note: l("恢复后才能决定继续还是结束。", "Only after recovery can the loop continue or stop.", "回復後に続行か終了かを決めます。") },
    ],
    nodes: [
      { id: "result", lane: "runtime", label: l("工具结果", "Tool Result", "tool 結果"), detail: l("成功与失败都从这里开始。", "Both success and failure start here.", "成功も失敗もここから始まります。") },
      { id: "detect", lane: "recovery", label: l("发现异常", "Detect Failure", "失敗検知"), detail: l("先看这是不是恢复分支。", "First decide whether this is a recovery path.", "まず回復分岐かどうかを見ます。") },
      { id: "classify", lane: "recovery", label: l("分类原因", "Classify Reason", "理由分類"), detail: l("权限、超时、环境缺失等不能混成一类。", "Permission, timeout, and missing environment errors should not be one bucket.", "権限・タイムアウト・環境欠如を一括りにしません。") },
      { id: "branch", lane: "recovery", label: l("选择恢复分支", "Choose Recovery Branch", "回復分岐選択"), detail: l("retry / fallback / ask / stop。", "retry / fallback / ask / stop.", "retry / fallback / ask / stop を選びます。") },
      { id: "reason", lane: "state", label: l("写明续行原因", "Write Continuation Reason", "続行理由を書く"), detail: l("下一轮必须知道为什么继续。", "The next turn must know why it is continuing.", "次のターンはなぜ続行するかを知る必要があります。") },
      { id: "continue", lane: "loop", label: l("继续或结束", "Continue or Stop", "続行か終了"), detail: l("恢复分支完成后才决定下一步。", "Only after recovery do you choose the next step.", "回復後に次の一歩を決めます。") },
    ],
    records: [
      { id: "error-event", label: l("ErrorEvent", "ErrorEvent", "ErrorEvent"), note: l("记录本次失败发生了什么。", "Captures what failed this time.", "今回何が失敗したかを記録します。") },
      { id: "recovery-state", label: l("RecoveryState", "RecoveryState", "RecoveryState"), note: l("当前处于哪条恢复分支。", "Tracks the current recovery branch.", "どの回復分岐にいるかを追跡します。") },
      { id: "transition-reason", label: l("TransitionReason", "TransitionReason", "TransitionReason"), note: l("为什么继续、重试或停止。", "Explains why the system continues, retries, or stops.", "なぜ続行・再試行・停止するかを示します。") },
    ],
    steps: [
      {
        title: l("先确认这是不是恢复分支", "First confirm whether this is a recovery path", "まず回復分岐か確認する"),
        description: l("错误恢复不是永远存在，它只在失败发生时接管。第一步是把失败从普通结果里分出来。", "Recovery is not always active. It only takes over when failure happens, so first separate failures from ordinary results.", "回復は常時動くわけではありません。失敗時だけ主導するので、まず通常結果と分けます。"),
        activeNodes: ["result", "detect"],
        activeRecords: ["error-event"],
        boundary: l("不要把所有工具结果都扔进统一 retry 逻辑。先确认是不是错误。", "Do not dump every tool result into one retry branch. First confirm whether it is actually a failure.", "すべての tool 結果を一律 retry に入れないでください。まず失敗か確認します。"),
        writeBack: l("一旦确认失败，控制流转向恢复层而不是继续假装成功。", "Once failure is confirmed, control moves into recovery instead of pretending the turn succeeded.", "失敗が確認されたら、成功したふりをせず recovery 層へ移ります。"),
      },
      {
        title: l("错误要先分类再恢复", "Classify failures before recovering", "失敗は分類してから回復する"),
        description: l("权限拒绝、超时、环境缺失、写冲突的恢复策略不同，所以恢复前一定先分类。", "Permission denials, timeouts, missing dependencies, and write conflicts recover differently, so classification must come first.", "権限拒否・タイムアウト・依存欠如・書き込み競合は回復方法が違うため、まず分類します。"),
        activeNodes: ["detect", "classify", "branch"],
        activeRecords: ["error-event", "recovery-state"],
        boundary: l("恢复稳定性的来源不是多重 try/except，而是分类足够清楚。", "Recovery becomes stable not through more try/except blocks, but through clear classification.", "回復が安定するのは try/except の数ではなく、分類が明確だからです。"),
        writeBack: l("分类后的 RecoveryState 决定接下来走 retry、fallback、ask 还是 stop。", "RecoveryState determines whether the next branch is retry, fallback, ask, or stop.", "分類後の RecoveryState が retry / fallback / ask / stop を決めます。"),
      },
      {
        title: l("恢复动作要带着理由继续", "Recovery continues with an explicit reason", "回復後は理由付きで続行する"),
        description: l("真正关键的点在于：系统不只是继续了，而是知道自己为什么继续。", "The key point is not that the system continues, but that it knows why it is continuing.", "本当に重要なのは、system がただ続くことではなく、なぜ続くのかを自分で分かっていることです。"),
        activeNodes: ["branch", "reason"],
        activeRecords: ["recovery-state", "transition-reason"],
        boundary: l("retry、fallback、ask 都应该显式写成 TransitionReason，而不是静默吞掉。", "retry, fallback, and ask should all be written as TransitionReason instead of silently swallowed.", "retry・fallback・ask は黙って飲み込まず、TransitionReason として明示します。"),
        writeBack: l("恢复原因进入续行状态，供下一轮推理理解当前分支。", "The recovery reason becomes visible state for the next reasoning step.", "回復理由は見える状態となり、次の推論が今の分岐を理解できるようにします。"),
      },
      {
        title: l("只有写明原因后，主循环才能稳定继续", "The main loop resumes safely only after the reason is written", "理由を書いてから主ループが安全に再開する"),
        description: l("恢复系统的终点不是“又试一次”，而是把恢复后的当前状态重新变成主循环可消费的事实。", "The endpoint of recovery is not “try again.” It is turning the recovered branch into visible state the main loop can consume.", "回復の終点は『もう一度試す』ではなく、回復後の状態を主ループが消費できる事実へ戻すことです。"),
        activeNodes: ["reason", "continue"],
        activeRecords: ["transition-reason"],
        boundary: l("没有续行原因，下一轮会不知道自己为什么还在这条分支上。", "Without a continuation reason, the next turn will not know why it is still on this branch.", "続行理由がないと、次のターンはなぜこの分岐にいるのか分かりません。"),
        writeBack: l("主循环看到 TransitionReason 后，才能按当前恢复状态继续、降级或结束。", "Once the main loop sees TransitionReason, it can continue, degrade, or stop coherently.", "主ループが TransitionReason を見ることで、続行・降格・終了を筋道立てて選べます。"),
      },
    ],
  },
  s12: {
    lanes: [
      { id: "input", label: l("目标入口", "Goal Entry", "目標入口"), note: l("一个更大的目标进入系统。", "A larger goal enters the system.", "より大きな目標がシステムへ入ります。") },
      { id: "board", label: l("任务板", "Task Board", "タスクボード"), note: l("这里保存 durable work graph。", "The durable work graph lives here.", "durable work graph はここにあります。") },
      { id: "records", label: l("记录层", "Record Layer", "レコード層"), note: l("任务、依赖和状态都必须显式。", "Tasks, dependencies, and status must be explicit.", "task・依存・状態を明示します。") },
      { id: "return", label: l("回流顺序", "Return Order", "回流順"), note: l("完成一个节点后如何解锁后继。", "How finishing one node unlocks the next.", "1 つ完了したあとでどう次を解放するかです。") },
    ],
    nodes: [
      { id: "goal", lane: "input", label: l("目标拆分", "Split Goal", "目標分解"), detail: l("把大任务拆成多个 durable node。", "Split a large goal into durable work nodes.", "大きな目標を durable node へ分解します。") },
      { id: "board", lane: "board", label: l("任务板登记", "Register on Board", "ボード登録"), detail: l("任务先成为记录，再考虑执行。", "A task becomes a record before it becomes execution.", "task はまず record になります。") },
      { id: "edges", lane: "records", label: l("依赖边", "Dependency Edges", "依存エッジ"), detail: l("blockedBy / blocks 决定谁先谁后。", "blockedBy / blocks decide ordering.", "blockedBy / blocks が順序を決めます。") },
      { id: "status", lane: "records", label: l("任务状态", "Task Status", "task 状態"), detail: l("pending / blocked / done 必须可见。", "pending / blocked / done must stay visible.", "pending / blocked / done を見える状態にします。") },
      { id: "complete", lane: "return", label: l("完成当前节点", "Complete Node", "現在ノード完了"), detail: l("一个节点完成后才检查后继。", "Only after completion do you inspect downstream work.", "完了後に後続を確認します。") },
      { id: "unlock", lane: "return", label: l("解锁后续任务", "Unlock Downstream", "後続解放"), detail: l("任务板根据依赖关系更新资格。", "The board updates eligibility from dependency state.", "ボードが依存状態から実行資格を更新します。") },
    ],
    records: [
      { id: "task-record", label: l("TaskRecord", "TaskRecord", "TaskRecord"), note: l("durable task 节点本体。", "The durable task node itself.", "durable task node 本体です。") },
      { id: "blocked-by", label: l("blockedBy", "blockedBy", "blockedBy"), note: l("当前节点还被谁卡住。", "Which upstream work still blocks this node.", "どの上流作業がこの node を止めているかです。") },
      { id: "blocks", label: l("blocks", "blocks", "blocks"), note: l("这个节点完成后会放行谁。", "Which downstream nodes this task unlocks.", "この node 完了後に誰を解放するかです。") },
      { id: "task-status", label: l("status", "status", "status"), note: l("任务板上的可见状态。", "The visible board state for a task.", "ボード上で見える task 状態です。") },
    ],
    steps: [
      {
        title: l("先把目标变成 durable task node", "Turn the goal into durable task nodes first", "目標を durable task node へ変える"),
        description: l("这一章真正新增的是任务记录本体，而不是后台线程。任务先是 durable work graph 上的节点。", "The real addition in this chapter is the task record itself, not a background thread. A task is first a node in a durable work graph.", "この章で増える本体は background thread ではなく task record です。task は durable work graph の node から始まります。"),
        activeNodes: ["goal", "board"],
        activeRecords: ["task-record"],
        boundary: l("现在讲的是目标记录，不是执行槽位。不要提前把后台执行混进来。", "This chapter is about goal records, not execution slots. Do not mix background execution in too early.", "ここで扱うのは goal record であり execution slot ではありません。"),
        writeBack: l("目标进入任务板后，系统才知道自己未来有哪些 durable work 要推进。", "Once the goal enters the board, the system knows what durable work exists to be advanced later.", "目標が task board に入ることで、将来進める durable work が見えるようになります。"),
      },
      {
        title: l("依赖边把任务排成工作图", "Dependency edges turn tasks into a work graph", "依存エッジが task を work graph にする"),
        description: l("blockedBy 和 blocks 是任务系统真正的骨架，它们决定为什么一个节点现在不能开始。", "blockedBy and blocks are the true skeleton of the task system. They explain why a node cannot start yet.", "blockedBy と blocks は task system の骨格であり、なぜまだ始められないかを説明します。"),
        activeNodes: ["board", "edges", "status"],
        activeRecords: ["task-record", "blocked-by", "blocks", "task-status"],
        boundary: l("没有显式依赖边，任务板就只是一份更大的 todo list。", "Without explicit dependency edges, the board is just a larger todo list.", "明示的な依存エッジがなければ、task board は大きい todo list にすぎません。"),
        writeBack: l("依赖关系和状态一起写在任务板里，为后续解锁逻辑做准备。", "Dependency state is written into the board alongside status so unlock logic can run later.", "依存状態と status を task board に書き込み、後続の unlock logic を準備します。"),
      },
      {
        title: l("完成一个节点后检查谁被放行", "After one node completes, check who becomes eligible", "1 つ完了したあとで誰が実行可能になるかを見る"),
        description: l("任务系统的运行感来自‘完成一个节点以后，后继节点为什么突然能开始’。这一步必须显式。", "The runtime feel of tasks comes from explicitly showing why a downstream node becomes eligible after one node completes.", "task system の実感は『1 つ終わるとなぜ次が始められるか』を明示することから生まれます。"),
        activeNodes: ["status", "complete", "unlock"],
        activeRecords: ["task-status", "blocked-by", "blocks"],
        boundary: l("不要把完成和解锁写成隐式副作用。读者必须看见状态是怎么变的。", "Do not hide completion and unlock as implicit side effects. Readers need to see how state changes.", "完了と解放を暗黙副作用にしないでください。状態変化を見せる必要があります。"),
        writeBack: l("任务板重新计算依赖后，新的 eligible task 会浮到下一步工作入口。", "After the board recomputes dependencies, newly eligible tasks rise into the next work entry point.", "依存再計算のあと、新しく eligible になった task が次の仕事入口に上がります。"),
      },
      {
        title: l("任务板把下一步工作重新送回主线", "The task board sends the next unit of work back to the mainline", "task board が次の仕事を主線へ戻す"),
        description: l("教学上最关键的是让读者看到：任务系统不是静态表格，它会持续把新的可做工作重新送回系统主线。", "The important teaching point is that the task board is not a static table. It continuously sends newly eligible work back into the mainline.", "重要なのは、task board が静的な表ではなく、新しく可能になった仕事を主線へ返し続けることです。"),
        activeNodes: ["board", "unlock", "goal"],
        activeRecords: ["task-record", "task-status"],
        boundary: l("任务板负责描述和解锁工作，不负责直接执行工作。", "The task board describes and unlocks work. It does not execute the work itself.", "task board は仕事を記述し解放しますが、直接実行はしません。"),
        writeBack: l("被解锁的任务重新变成系统下一段主线要推进的目标。", "Unlocked tasks become the next mainline goals the system should push forward.", "解放された task が次の主線目標になります。"),
      },
    ],
  },
  s13: {
    lanes: [
      { id: "board", label: l("任务板", "Task Board", "タスクボード"), note: l("目标任务仍留在这里。", "Goal tasks remain here.", "goal task はここに残ります。") },
      { id: "runtime", label: l("运行槽位", "Runtime Slot", "実行スロット"), note: l("正在跑的那一份工作独立存在。", "Live execution exists in its own slot.", "実行中の仕事は独立した slot にあります。") },
      { id: "output", label: l("输出分层", "Output Layer", "出力層"), note: l("preview 和全文分层保存。", "Preview and full output are saved separately.", "preview と全文を分けて保存します。") },
      { id: "notify", label: l("通知回流", "Notification Return", "通知回流"), note: l("结果在未来某轮再回到主循环。", "Results return on a later turn.", "結果は後続のターンで戻ります。") },
    ],
    nodes: [
      { id: "goal-task", lane: "board", label: l("目标任务", "Goal Task", "goal task"), detail: l("durable 目标仍在任务板。", "The durable goal stays on the board.", "durable な目標は board に残ります。") },
      { id: "spawn-runtime", lane: "runtime", label: l("生成运行记录", "Spawn Runtime Record", "runtime record 生成"), detail: l("为这次执行创建独立记录。", "Create a separate record for this execution attempt.", "今回の実行のために独立 record を作ります。") },
      { id: "background-run", lane: "runtime", label: l("后台执行", "Run in Background", "バックグラウンド実行"), detail: l("慢工作不再阻塞前台循环。", "Slow work stops blocking the foreground loop.", "遅い仕事が前景ループを塞がなくなります。") },
      { id: "preview", lane: "output", label: l("结果预览", "Result Preview", "結果 preview"), detail: l("通知里只放可读摘要。", "Only a readable summary goes into notifications.", "通知には読める要約だけを入れます。") },
      { id: "full-output", lane: "output", label: l("完整输出文件", "Full Output File", "完全出力ファイル"), detail: l("长输出写文件，不撑爆 prompt。", "Long output goes to disk instead of bloating the prompt.", "長い出力は disk へ書き、prompt を膨らませません。") },
      { id: "notification", lane: "notify", label: l("通知写回", "Write Notification", "通知回写"), detail: l("下一轮前再注入主循环。", "Inject it into the main loop on a later turn.", "後続ターンで主ループへ注入します。") },
    ],
    records: [
      { id: "runtime-task", label: l("RuntimeTaskRecord", "RuntimeTaskRecord", "RuntimeTaskRecord"), note: l("描述这次执行本身。", "Describes this specific execution.", "この実行そのものを表します。") },
      { id: "notification-record", label: l("Notification", "Notification", "Notification"), note: l("把结果带回前台循环的桥。", "The bridge that brings results back to the foreground loop.", "結果を前景ループへ戻す橋です。") },
      { id: "output-file", label: l("output_file", "output_file", "output_file"), note: l("存放完整输出内容。", "Stores the full output.", "完全な出力を保存します。") },
    ],
    steps: [
      {
        title: l("目标任务和运行记录先分开", "Separate the goal task from the runtime record first", "goal task と runtime record を先に分ける"),
        description: l("后台任务章真正新增的不是另一种 task，而是一层专门描述‘这次执行本身’的 runtime record。", "The chapter does not add a second kind of task. It adds a runtime record dedicated to this execution attempt.", "この章で増えるのは別種の task ではなく、『今回の実行そのもの』を記述する runtime record です。"),
        activeNodes: ["goal-task", "spawn-runtime"],
        activeRecords: ["runtime-task"],
        boundary: l("目标任务记录‘要做什么’，运行记录记录‘这次怎么跑’。两者不能混。", "The goal task records what should be done, while the runtime record records how this attempt is running. They should not be merged.", "goal task は『何をするか』、runtime record は『今回どう走るか』を持ちます。混ぜません。"),
        writeBack: l("生成 RuntimeTaskRecord 后，前台循环就可以先继续，慢任务进入后台车道。", "Once the RuntimeTaskRecord exists, the foreground loop can continue while the slow task enters a background lane.", "RuntimeTaskRecord ができたら、前景ループは先へ進み、遅い仕事は背景レーンへ移れます。"),
      },
      {
        title: l("慢工作在后台槽位执行", "Slow work runs inside the background slot", "遅い仕事は background slot で走る"),
        description: l("并行的不是第二个主循环，而是等待和执行这件事本身。主循环没有消失。", "What runs in parallel is the waiting/execution work itself, not a second main loop. The main loop still exists.", "並列になるのは待ち時間と実行そのものであり、第2の主ループではありません。"),
        activeNodes: ["spawn-runtime", "background-run"],
        activeRecords: ["runtime-task"],
        boundary: l("后台执行不等于后台思考。不要把它误讲成另一个完整 agent。", "Background execution does not mean a second background thinker. Do not teach it as another full agent.", "バックグラウンド実行は、別の思考 agent が生まれたことではありません。"),
        writeBack: l("后台槽位完成后，不直接改 messages[]，而是先生成输出和通知。", "When the background slot finishes, it does not edit messages[] directly. It writes output and notifications first.", "背景 slot は終わっても messages[] を直接触らず、まず出力と通知を作ります。"),
      },
      {
        title: l("预览和全文必须分层保存", "Preview and full output must be stored separately", "preview と全文を分層保存する"),
        description: l("真正稳的设计不是把大段后台输出塞回 prompt，而是只把 preview 带回前台，把全文落盘。", "The stable design is not to stuff huge background output back into the prompt, but to return only a preview while persisting the full output.", "安定した設計は巨大出力を prompt に戻すことではなく、preview だけ返して全文は保存することです。"),
        activeNodes: ["background-run", "preview", "full-output"],
        activeRecords: ["runtime-task", "output-file"],
        boundary: l("通知负责告诉主循环‘有结果了’，不负责承载全部结果内容。", "Notifications should tell the main loop that work finished, not carry the entire output payload.", "通知は『結果が出た』ことを伝え、全文を背負いません。"),
        writeBack: l("preview 进入 Notification，全文进入 output_file，二者在未来按需重连。", "The preview goes into Notification, the full text goes into output_file, and they reconnect later on demand.", "preview は Notification へ、全文は output_file へ入り、必要時だけ再接続します。"),
      },
      {
        title: l("通知在下一轮前把结果接回主循环", "Notifications reconnect the result on a later turn", "通知が後続ターンで結果を主ループへ戻す"),
        description: l("后台结果之所以不拧巴，是因为它通过 Notification 这座桥，重新以‘本轮可见事实’的形式返回。", "Background results stay understandable because they return through Notification as visible facts for a later turn.", "背景結果が分かりやすいのは、Notification という橋を通って後続ターンの可視事実として戻るからです。"),
        activeNodes: ["preview", "notification", "goal-task"],
        activeRecords: ["notification-record", "runtime-task"],
        boundary: l("后台线程不要直接篡改模型状态，统一回流时机要留在前台控制面。", "Background workers should not mutate model state directly. The write-back moment belongs to the foreground control plane.", "背景 worker がモデル状態を直接書き換えないこと。回流タイミングは前景 control plane に残します。"),
        writeBack: l("下一轮注入 Notification 后，主循环再决定要不要去读完整输出文件。", "After injecting Notification on a later turn, the main loop decides whether it needs to read the full output file.", "後続ターンで Notification を注入したあと、主ループが全文ファイルを読むかどうかを決めます。"),
      },
    ],
  },
  s14: {
    lanes: [
      { id: "clock", label: l("时间触发", "Time Trigger", "時間トリガ"), note: l("时间第一次成为启动源。", "Time becomes a trigger source.", "時間が起動源になります。") },
      { id: "schedule", label: l("调度规则", "Schedule Rules", "スケジュールルール"), note: l("这里只决定是否命中。", "This layer only decides whether a rule matched.", "ここはヒット判定だけを行います。") },
      { id: "runtime", label: l("运行时接力", "Runtime Handoff", "ランタイム受け渡し"), note: l("命中后仍然创建 runtime work。", "A match still creates runtime work.", "ヒット後も runtime work を作ります。") },
      { id: "return", label: l("事件回流", "Event Return", "イベント回流"), note: l("调度结果也要被系统看见。", "Schedule outcomes should also remain visible.", "スケジュール結果もシステムから見えるようにします。") },
    ],
    nodes: [
      { id: "tick", lane: "clock", label: l("Cron Tick", "Cron Tick", "Cron Tick"), detail: l("定期检查时间规则。", "Periodically check schedule rules.", "定期的にルールを確認します。") },
      { id: "match", lane: "schedule", label: l("规则命中?", "Rule Match?", "ルール一致?"), detail: l("时间只负责判断要不要启动。", "Time only decides whether work should start.", "時間は起動可否だけを決めます。") },
      { id: "schedule-record", lane: "schedule", label: l("调度记录", "Schedule Record", "schedule record"), detail: l("描述何时、按什么规则触发。", "Describes when and why work was triggered.", "いつどのルールで起動したかを表します。") },
      { id: "spawn", lane: "runtime", label: l("创建运行任务", "Create Runtime Task", "runtime task 作成"), detail: l("命中后仍生成 runtime task。", "A matching schedule still creates a runtime task.", "一致後も runtime task を作ります。") },
      { id: "background", lane: "runtime", label: l("交给后台运行时", "Hand Off to Background Runtime", "背景 runtime へ渡す"), detail: l("执行仍由后台任务层负责。", "Execution is still owned by the runtime layer.", "実行は引き続き runtime 層が担います。") },
      { id: "notify", lane: "return", label: l("调度事件回写", "Write Schedule Event", "schedule event 回写"), detail: l("系统要知道这次工作是被时间触发的。", "The system should know this work came from a schedule.", "この仕事が時間トリガで始まったと分かる必要があります。") },
    ],
    records: [
      { id: "schedule-rule", label: l("ScheduleRecord", "ScheduleRecord", "ScheduleRecord"), note: l("保存时间规则和触发目标。", "Stores the schedule rule and target work.", "時間ルールと起動対象を保存します。") },
      { id: "runtime-task", label: l("RuntimeTaskRecord", "RuntimeTaskRecord", "RuntimeTaskRecord"), note: l("真正执行的那一份工作。", "The runtime record for actual execution.", "実際に動く仕事の runtime record です。") },
      { id: "schedule-event", label: l("ScheduleEvent", "ScheduleEvent", "ScheduleEvent"), note: l("记录本次时间触发已经发生。", "Captures that a schedule trigger fired.", "今回 schedule trigger が起きたことを記録します。") },
    ],
    steps: [
      {
        title: l("时间先命中规则，不直接执行", "Time matches rules before anything executes", "時間はまずルール一致を判定し、直接実行しない"),
        description: l("Cron 章节真正想建立的是‘时间只是启动源’，所以第一步只判断规则有没有命中。", "The core idea of cron is that time is only a trigger source, so the first step is rule matching, not execution.", "cron の核心は『時間は起動源にすぎない』ことです。最初にやるのは実行ではなくルール一致判定です。"),
        activeNodes: ["tick", "match", "schedule-record"],
        activeRecords: ["schedule-rule"],
        boundary: l("不要把时间线程误讲成执行线程。调度层先只决定要不要启动。", "Do not confuse a timing loop with an execution loop. The schedule layer first decides only whether to trigger work.", "時間ループを実行ループと混同しないでください。schedule 層は起動可否だけを決めます。"),
        writeBack: l("一旦规则命中，控制流才会去创建真正的 runtime task。", "Only after a rule matches does control move toward creating real runtime work.", "ルール一致のあとで初めて runtime task 作成へ進みます。"),
      },
      {
        title: l("命中后生成 runtime work，而不是自己执行", "A match creates runtime work instead of executing by itself", "一致後は自分で実行せず runtime work を作る"),
        description: l("时间触发的工作和用户触发的工作，最终都应该收敛到同一 runtime task 模型。", "Work triggered by time should converge into the same runtime task model as user-triggered work.", "時間トリガ仕事もユーザートリガ仕事も、最終的には同じ runtime task model に収束すべきです。"),
        activeNodes: ["match", "spawn"],
        activeRecords: ["schedule-rule", "runtime-task"],
        boundary: l("调度器只管触发，不管执行细节。否则 schedule 和 runtime 会混成一团。", "The scheduler owns triggering, not runtime execution detail. Otherwise schedule and runtime blur together.", "scheduler は trigger を持ち、実行詳細は持ちません。そうしないと schedule と runtime が混ざります。"),
        writeBack: l("创建好的 RuntimeTaskRecord 会被交给后台运行时继续处理。", "The created RuntimeTaskRecord is handed to the background runtime for actual execution.", "作成された RuntimeTaskRecord は背景 runtime へ渡されます。"),
      },
      {
        title: l("执行仍由后台运行时负责", "Execution still belongs to the background runtime", "実行は引き続き背景 runtime が担う"),
        description: l("Cron 不需要重复发明执行模型。命中后的工作直接交给 s13 那层 runtime slot 去跑。", "Cron does not need a second execution model. Triggered work hands off to the same background runtime introduced in s13.", "cron は第2の実行モデルを発明しません。起動後の仕事は s13 の background runtime へ渡します。"),
        activeNodes: ["spawn", "background"],
        activeRecords: ["runtime-task"],
        boundary: l("Cron 不是后台槽位；后台槽位才真正持有执行生命周期。", "Cron is not the background slot. The slot owns the execution lifecycle.", "cron は background slot ではありません。実行ライフサイクルは slot が持ちます。"),
        writeBack: l("运行时完成后，再把‘这是一次时间触发工作’的事实回写给系统。", "After runtime execution completes, the system still writes back the fact that this work came from a schedule.", "runtime 実行後も『これは schedule 起動の仕事だった』という事実をシステムへ返します。"),
      },
      {
        title: l("系统要看见这次工作来自时间触发", "The system should see that this work came from a schedule", "この仕事が時間トリガ由来だと見えるようにする"),
        description: l("时间触发不是隐形来源。它应该形成可见的 ScheduleEvent，让系统理解为什么这个任务会在此时出现。", "A schedule trigger should not be invisible. It should become a visible ScheduleEvent so the system knows why this work appeared now.", "schedule trigger は見えない起源にしません。見える ScheduleEvent にして、なぜ今この仕事が現れたかを理解できるようにします。"),
        activeNodes: ["schedule-record", "notify"],
        activeRecords: ["schedule-event", "schedule-rule"],
        boundary: l("如果不写回触发来源，后面的 agent 很容易不知道任务为什么会突然出现。", "If the trigger source is not written back, later agents may not understand why the task suddenly appeared.", "起動源を書き戻さないと、後続 agent はなぜ突然 task が現れたか分からなくなります。"),
        writeBack: l("ScheduleEvent 把时间来源重新接回系统主线，供后续任务板和通知层继续理解。", "ScheduleEvent reconnects time as a visible source for later task-board and notification logic.", "ScheduleEvent が時間起源を主線へ戻し、後続の task board や通知層が理解できるようにします。"),
      },
    ],
  },
  s15: {
    lanes: [
      { id: "lead", label: l("Lead 编排者", "Lead Orchestrator", "Lead 編成者"), note: l("由它生成 roster 并分配工作。", "It creates the roster and assigns work.", "roster を作り、仕事を割り当てます。") },
      { id: "roster", label: l("团队身份层", "Team Identity Layer", "チーム identity 層"), note: l("长期存在的 teammate 从这里开始。", "Persistent teammates begin here.", "長寿命 teammate はここから始まります。") },
      { id: "mailbox", label: l("邮箱协作", "Mailbox Collaboration", "メールボックス協調"), note: l("不是共用一份 messages[]。", "The team does not share one messages[] buffer.", "1 つの messages[] を共有しません。") },
      { id: "workers", label: l("独立执行线", "Independent Worker Lines", "独立実行線"), note: l("每个队友沿自己的车道执行。", "Each teammate runs on its own line.", "各 teammate が自分の実行線を持ちます。") },
    ],
    nodes: [
      { id: "lead", lane: "lead", label: l("Lead", "Lead", "Lead"), detail: l("负责看全局并分配角色。", "Owns the global picture and assignment.", "全体像と割り当てを持ちます。") },
      { id: "roster", lane: "roster", label: l("TeamRoster", "TeamRoster", "TeamRoster"), detail: l("列出长期存在的 teammates。", "Lists persistent teammates.", "長寿命 teammate を列挙します。") },
      { id: "teammates", lane: "roster", label: l("Teammates", "Teammates", "Teammates"), detail: l("每个都有自己的身份和职责。", "Each has its own identity and responsibility.", "各自が固有の identity と責務を持ちます。") },
      { id: "mail", lane: "mailbox", label: l("投递信件", "Deliver Message", "メッセージ配送"), detail: l("通过 envelope 发任务，不靠共享上下文。", "Send work via envelopes instead of shared context.", "共有文脈ではなく envelope 経由で仕事を送ります。") },
      { id: "inbox", lane: "mailbox", label: l("独立 Inbox", "Independent Inbox", "独立 Inbox"), detail: l("每个队友只看自己的收件箱。", "Each teammate watches its own inbox.", "各 teammate は自分の inbox を見ます。") },
      { id: "worker-run", lane: "workers", label: l("队友执行", "Teammate Execution", "teammate 実行"), detail: l("不同执行线可以反复接活。", "Worker lines can receive repeat work over time.", "worker line は繰り返し仕事を受けられます。") },
      { id: "reply", lane: "workers", label: l("回信或继续协作", "Reply or Continue", "返信または継続協調"), detail: l("结果可以回给 Lead 或别的队友。", "Results can return to the Lead or other teammates.", "結果は Lead や他 teammate に戻せます。") },
    ],
    records: [
      { id: "team-member", label: l("TeamMember", "TeamMember", "TeamMember"), note: l("长期身份、角色和状态。", "Persistent identity, role, and status.", "長寿命の identity・role・status を持ちます。") },
      { id: "message-envelope", label: l("MessageEnvelope", "MessageEnvelope", "MessageEnvelope"), note: l("队友之间传递任务和回应的壳。", "The envelope used to pass work and replies.", "仕事や返信を渡す外殻です。") },
      { id: "inbox-record", label: l("Inbox", "Inbox", "Inbox"), note: l("每个 teammate 的独立消息入口。", "Each teammate's independent message entry.", "各 teammate の独立メッセージ入口です。") },
    ],
    steps: [
      {
        title: l("先让队友成为长期身份", "Make teammates persistent identities first", "まず teammate を長寿命 identity にする"),
        description: l("Agent Teams 这一章的关键不是‘多开几个模型调用’，而是先建立能长期存在的 teammate 身份层。", "The key lesson is not “more model calls,” but persistent teammate identities that survive beyond a single subtask.", "要点は『モデル呼び出しを増やすこと』ではなく、1 回きりで終わらない teammate identity を作ることです。"),
        activeNodes: ["lead", "roster", "teammates"],
        activeRecords: ["team-member"],
        boundary: l("teammate 不是换了名字的 subagent。它得能长期存在、重复接活。", "A teammate is not a renamed subagent. It must persist and take repeated work.", "teammate は名前を変えた subagent ではありません。継続存在し、繰り返し仕事を受けます。"),
        writeBack: l("Lead 生成 roster 后，系统才第一次拥有长期存在的多角色结构。", "Once the Lead builds the roster, the system gains its first persistent multi-role structure.", "Lead が roster を作ることで、システムは初めて長寿命の多役割構造を持ちます。"),
      },
      {
        title: l("协作通过邮箱而不是共享上下文", "Collaboration runs through mailboxes, not shared context", "協調は共有文脈ではなく mailbox で行う"),
        description: l("真正清晰的团队协作依赖独立 inbox 和结构化 envelope，而不是大家共用一份 messages[]。", "Clear team collaboration depends on independent inboxes and structured envelopes, not one shared messages[] buffer.", "明快なチーム協調は独立 inbox と構造化 envelope に依存し、共有 messages[] には依存しません。"),
        activeNodes: ["teammates", "mail", "inbox"],
        activeRecords: ["message-envelope", "inbox-record"],
        boundary: l("如果所有队友都看同一份上下文，协作边界会很快混乱。", "If every teammate reads the same context buffer, collaboration boundaries become blurry fast.", "全 teammate が同じ文脈を読むと、協調境界はすぐ曖昧になります。"),
        writeBack: l("任务通过 MessageEnvelope 投递进各自 Inbox，每个队友按自己的节奏取件。", "Work enters each Inbox via MessageEnvelope so teammates can process it independently.", "仕事は MessageEnvelope で各 Inbox に入り、各 teammate が独立に取り出します。"),
      },
      {
        title: l("队友沿各自执行线推进工作", "Teammates advance work along their own lines", "teammate は各自の実行線で仕事を進める"),
        description: l("团队价值来自长期分工。每个 teammate 都有自己的执行线，而不是每次都回到 Lead 重新推理一遍。", "Team value comes from durable specialization. Each teammate has its own execution line instead of bouncing all work back to the Lead.", "チーム価値は持続的な分業から生まれます。各 teammate は独自の実行線を持ちます。"),
        activeNodes: ["inbox", "worker-run"],
        activeRecords: ["team-member", "inbox-record"],
        boundary: l("Lead 负责编排，不等于 Lead 亲自执行所有细节。", "The Lead orchestrates, but that does not mean it executes every detail itself.", "Lead は編成を担いますが、細部をすべて自分で実行するわけではありません。"),
        writeBack: l("队友消费 inbox 后，在自己的执行线中推进工作，再产出回信或后续消息。", "After consuming inbox messages, teammates advance work on their own lines and then emit replies or follow-up messages.", "Inbox を消費した teammate は自分の実行線で仕事を進め、返信や次のメッセージを出します。"),
      },
      {
        title: l("结果可以回给 Lead，也可以继续队友协作", "Results can return to the Lead or continue peer collaboration", "結果は Lead に戻ることも、隊友間で続くこともある"),
        description: l("一旦团队身份和邮箱成立，协作就不再是单向的‘Lead 发任务，队友做完就结束’，而是可以持续往复。", "Once identity and mailboxes exist, collaboration stops being a single one-way delegation. It can continue as a durable exchange.", "identity と mailbox が成立すると、協調は一方向の委譲ではなく、継続的な往復になります。"),
        activeNodes: ["worker-run", "reply", "lead"],
        activeRecords: ["message-envelope", "team-member"],
        boundary: l("团队系统的结束条件不只是‘任务完成’，还包括‘结果该回给谁继续处理’。", "A team flow is not finished only when work is done, but also when the result is routed back to the right owner.", "チームフローは『仕事完了』だけで終わらず、『結果を誰へ戻すか』も含みます。"),
        writeBack: l("回信进入下一段编排，Lead 或别的 teammate 再根据结果决定后续协作。", "Replies enter the next orchestration step so the Lead or another teammate can decide what happens next.", "返信が次の編成段階に入り、Lead や別 teammate が次を決めます。"),
      },
    ],
  },
  s16: {
    lanes: [
      { id: "request", label: l("协议请求", "Protocol Request", "プロトコル要求"), note: l("重要协作先变成结构化请求。", "Important coordination becomes a structured request first.", "重要な協調はまず構造化要求になります。") },
      { id: "record", label: l("请求记录", "Request Record", "要求レコード"), note: l("状态要能被持续追踪。", "State must stay traceable over time.", "状態を継続追跡できるようにします。") },
      { id: "response", label: l("明确响应", "Explicit Response", "明示応答"), note: l("批准、拒绝、超时都要可见。", "Approve, reject, and timeout must stay visible.", "承認・拒否・タイムアウトを見えるようにします。") },
      { id: "team", label: l("团队继续协作", "Team Continues", "チーム継続"), note: l("有了协议后，协作才真正稳。", "Shared protocols stabilize the team.", "共有 protocol がチームを安定させます。") },
    ],
    nodes: [
      { id: "envelope", lane: "request", label: l("协议外壳", "Protocol Envelope", "protocol envelope"), detail: l("type / from / to / request_id / payload。", "type / from / to / request_id / payload.", "type / from / to / request_id / payload を持ちます。") },
      { id: "request-id", lane: "request", label: l("request_id", "request_id", "request_id"), detail: l("把同一次请求和响应串起来。", "Correlates a request with its response.", "要求と応答を結びつけます。") },
      { id: "request-record", lane: "record", label: l("落盘请求记录", "Persist Request Record", "request record 保存"), detail: l("状态必须 durable，不只在内存里。", "State must be durable, not just in memory.", "状態は memory だけでなく durable である必要があります。") },
      { id: "pending", lane: "record", label: l("Pending 状态", "Pending State", "Pending 状態"), detail: l("等待响应期间状态也清楚可见。", "The waiting state stays visible too.", "待機中の状態も見えるようにします。") },
      { id: "response", lane: "response", label: l("批准/拒绝/过期", "Approve / Reject / Expire", "承認 / 拒否 / 期限切れ"), detail: l("协议响应不是自由文本。", "Protocol responses are not free-form chat.", "protocol 応答は自由文ではありません。") },
      { id: "update", lane: "team", label: l("更新请求状态", "Update Request State", "request 状態更新"), detail: l("团队依据结构化状态继续。", "The team continues based on structured status.", "チームは構造化状態に基づいて続行します。") },
    ],
    records: [
      { id: "protocol-envelope", label: l("ProtocolEnvelope", "ProtocolEnvelope", "ProtocolEnvelope"), note: l("团队协议消息的统一壳。", "The shared envelope for protocol messages.", "protocol message の共通外殻です。") },
      { id: "request-record", label: l("RequestRecord", "RequestRecord", "RequestRecord"), note: l("保存一次协议请求的整个生命周期。", "Stores the lifecycle of a protocol request.", "protocol request のライフサイクルを保存します。") },
      { id: "request-id", label: l("request_id", "request_id", "request_id"), note: l("在请求和响应之间做关联。", "Correlates requests and responses.", "要求と応答を関連づけます。") },
    ],
    steps: [
      {
        title: l("重要协作先被包成协议请求", "Important coordination is wrapped into a protocol request first", "重要協調を先に protocol request に包む"),
        description: l("协议章的第一护栏是：重要协作不再只靠自由文本，而是先拥有固定 envelope。", "The first guardrail of protocols is that important coordination no longer relies on free-form text. It gets a fixed envelope first.", "protocol 章の第一ガードレールは、重要協調が自由文ではなく固定 envelope を持つことです。"),
        activeNodes: ["envelope", "request-id"],
        activeRecords: ["protocol-envelope", "request-id"],
        boundary: l("‘正式一点的聊天’还不是协议。协议要先有固定字段。", "“More formal chat” is still not a protocol. A protocol needs fixed fields first.", "『少し丁寧な会話』は protocol ではありません。固定フィールドが必要です。"),
        writeBack: l("结构化请求带着 request_id 进入 durable request record。", "The structured request, together with its request_id, enters a durable request record.", "構造化要求は request_id とともに durable request record へ入ります。"),
      },
      {
        title: l("请求状态必须落盘可追踪", "Request state must persist durably and remain traceable", "request 状態は durable に保存し追跡可能であるべき"),
        description: l("真正稳定的团队协议，不是临时内存里的标记，而是 durable RequestRecord。", "Stable team protocols depend on durable RequestRecord, not temporary in-memory flags.", "安定した team protocol は一時 memory flag ではなく durable RequestRecord に依存します。"),
        activeNodes: ["request-id", "request-record", "pending"],
        activeRecords: ["request-record", "request-id"],
        boundary: l("如果请求状态不 durable，审批、接力和恢复都会失去依据。", "If request state is not durable, approval, handoff, and recovery all lose their ground truth.", "request 状態が durable でないと、承認・引き継ぎ・回復の根拠が失われます。"),
        writeBack: l("一旦 RequestRecord 进入 pending，系统就能跨轮次继续等待、催促或恢复。", "Once a RequestRecord enters pending, the system can wait, remind, or recover across turns.", "RequestRecord が pending に入ると、ターンをまたいで待機・催促・回復できます。"),
      },
      {
        title: l("响应必须是显式状态，而不是自由聊天", "Responses must be explicit state transitions, not free chat", "応答は自由会話ではなく明示状態遷移にする"),
        description: l("批准、拒绝、过期的核心价值在于状态迁移可见，而不是语言本身多好看。", "Approve, reject, and expire matter because the state transition is visible, not because the language sounds more formal.", "承認・拒否・期限切れの価値は、状態遷移が見えることであって、文面が丁寧なことではありません。"),
        activeNodes: ["pending", "response"],
        activeRecords: ["request-record"],
        boundary: l("协议响应要优先表达状态，不要先沉迷于消息文案。", "Protocol responses must express state first; message wording comes second.", "protocol 応答はまず状態を表し、文面はその後です。"),
        writeBack: l("响应会更新 RequestRecord，团队后续协作都以这个状态为依据。", "Responses update the RequestRecord, and later coordination uses that state as truth.", "応答は RequestRecord を更新し、以後の協調はその状態を真実として使います。"),
      },
      {
        title: l("团队根据协议状态继续协作", "The team continues based on protocol state", "チームは protocol 状態に基づいて協調を続ける"),
        description: l("协议的终点不是发出一条消息，而是团队后续每一步都能基于同一个请求状态继续行动。", "The endpoint of protocol is not sending a message. It is enabling every later coordination step to use the same request state.", "protocol の終点はメッセージ送信ではなく、その後の各段階が同じ request state に基づいて動けることです。"),
        activeNodes: ["response", "update"],
        activeRecords: ["request-record", "protocol-envelope"],
        boundary: l("协议系统真正管理的是状态机，而不是聊天内容。", "The protocol system really manages a state machine, not the chat text itself.", "protocol system が本当に管理しているのは状態機械であり、会話文そのものではありません。"),
        writeBack: l("更新后的 RequestRecord 成为团队下一轮协作、恢复和审批的共同依据。", "The updated RequestRecord becomes shared ground truth for later coordination, recovery, and approval.", "更新後の RequestRecord が次の協調・回復・承認の共通根拠になります。"),
      },
    ],
  },
  s17: {
    lanes: [
      { id: "idle", label: l("空闲巡检", "Idle Scan", "アイドル巡回"), note: l("自治从空闲时还能找工作开始。", "Autonomy begins when idle workers keep looking for work.", "自律は idle worker が仕事を探し続けるところから始まります。") },
      { id: "claim", label: l("认领规则", "Claim Policy", "claim ルール"), note: l("不是任何工作都能自领。", "Not every task can be self-claimed.", "何でも self-claim できるわけではありません。") },
      { id: "resume", label: l("恢复上下文", "Resume Context", "再開文脈"), note: l("认领后还要恢复正确身份。", "After claiming, the worker must resume the right identity and context.", "claim 後に正しい identity と文脈へ戻る必要があります。") },
      { id: "return", label: l("状态回写", "State Write-back", "状態回写"), note: l("自治行为也要留下可见状态。", "Autonomous behavior still leaves visible state.", "自律動作も見える状態を残します。") },
    ],
    nodes: [
      { id: "idle-worker", lane: "idle", label: l("空闲队友", "Idle Teammate", "idle teammate"), detail: l("没有新指令时也会继续检查。", "Keeps checking even without new instructions.", "新しい指示がなくても確認を続けます。") },
      { id: "scan", lane: "idle", label: l("巡检 inbox / task board", "Scan Inbox / Task Board", "Inbox / Task Board を巡回"), detail: l("自治入口从这一步开始。", "Autonomy begins with this scan.", "自律の入口はこの巡回から始まります。") },
      { id: "policy", lane: "claim", label: l("claim policy", "Claim Policy", "claim policy"), detail: l("按角色、资格和占用状态判断能否接活。", "Role, eligibility, and occupancy decide whether work can be claimed.", "役割・資格・占有状態で claim 可否を決めます。") },
      { id: "claim", lane: "claim", label: l("认领工作", "Claim Work", "仕事を claim"), detail: l("自领工作时也要生成显式事件。", "Self-claiming should still generate explicit events.", "self-claim でも明示イベントを作ります。") },
      { id: "resume", lane: "resume", label: l("恢复身份与上下文", "Resume Identity + Context", "identity と文脈を再開"), detail: l("恢复 mailbox、task、role-aware context。", "Restore mailbox, task, and role-aware context.", "mailbox・task・role-aware context を戻します。") },
      { id: "execute", lane: "resume", label: l("继续执行", "Continue Execution", "実行継続"), detail: l("认领后沿正确车道继续工作。", "After claiming, work continues on the right lane.", "claim 後に正しい lane で仕事を続けます。") },
      { id: "writeback", lane: "return", label: l("回写 claim / resume 状态", "Write Back Claim / Resume State", "claim / resume 状態を回写"), detail: l("自治过程也必须可见。", "Autonomous progress must stay visible too.", "自律過程も見える必要があります。") },
    ],
    records: [
      { id: "claim-event", label: l("ClaimEvent", "ClaimEvent", "ClaimEvent"), note: l("记录谁认领了哪份工作。", "Records who claimed which work item.", "誰が何を claim したかを記録します。") },
      { id: "runtime-task", label: l("RuntimeTaskState", "RuntimeTaskState", "RuntimeTaskState"), note: l("执行槽位仍然独立存在。", "The execution slot still exists independently.", "execution slot は引き続き独立しています。") },
      { id: "identity-context", label: l("IdentityContext", "IdentityContext", "IdentityContext"), note: l("恢复时要重新注入角色化身份。", "Role identity must be re-injected when resuming.", "再開時に役割 identity を再注入します。") },
    ],
    steps: [
      {
        title: l("自治从空闲巡检开始", "Autonomy starts with idle scanning", "自律は idle scan から始まる"),
        description: l("自治不是神秘地‘自己会想’，而是空闲队友在没有新指令时，仍会去巡检 inbox 和 task board。", "Autonomy is not mysterious self-thinking. It begins when idle teammates keep scanning inboxes and task boards even without new instructions.", "自律は神秘的な『自分で考える』ことではなく、新しい指示がなくても inbox と task board を見に行くことから始まります。"),
        activeNodes: ["idle-worker", "scan"],
        activeRecords: [],
        boundary: l("没有 idle 巡检，自治就不会发生；系统只会在被点名时行动。", "Without idle scanning, autonomy never starts. The system acts only when explicitly called.", "idle scan がなければ自律は始まりません。"),
        writeBack: l("巡检发现可处理线索后，控制流才进入 claim policy。", "Only after the scan finds candidate work does control move into the claim policy.", "巡回で候補仕事が見つかってから、claim policy へ進みます。"),
      },
      {
        title: l("不是所有工作都能自领，先过 claim policy", "Not all work may be self-claimed; pass through claim policy first", "すべての仕事を self-claim できるわけではない"),
        description: l("真正让自治稳定的，不是‘敢不敢动’，而是系统有没有定义清楚谁能认领什么。", "What makes autonomy stable is not boldness but a clear definition of who may claim what.", "自律を安定させるのは大胆さではなく、誰が何を claim できるかが明確なことです。"),
        activeNodes: ["scan", "policy", "claim"],
        activeRecords: ["claim-event"],
        boundary: l("如果没有 claim policy，多 agent 很容易重复认领同一份工作。", "Without a claim policy, multiple agents may grab the same work repeatedly.", "claim policy がなければ複数 agent が同じ仕事を重複 claim しやすくなります。"),
        writeBack: l("一旦 claim 成功，就写下 ClaimEvent，避免自治动作变成黑箱。", "Once a claim succeeds, write a ClaimEvent so autonomy does not become a black box.", "claim 成功時には ClaimEvent を残し、自律動作をブラックボックスにしません。"),
      },
      {
        title: l("认领后先恢复正确身份，再继续执行", "After claiming, restore the right identity before execution", "claim 後に正しい identity を復元してから実行する"),
        description: l("自治难点不在于开始执行，而在于恢复正确上下文。谁在执行、为什么轮到它，都必须重新注入。", "The hard part of autonomy is not starting execution, but restoring the right context: who is acting and why it is their turn.", "自律で難しいのは実行開始ではなく、正しい文脈を復元することです。"),
        activeNodes: ["claim", "resume", "execute"],
        activeRecords: ["claim-event", "identity-context", "runtime-task"],
        boundary: l("自领工作不等于无上下文乱跑，resume context 才是自治可控的关键。", "Self-claiming does not mean acting without context. Resume context is what keeps autonomy under control.", "self-claim は文脈なし暴走ではありません。resume context が制御の鍵です。"),
        writeBack: l("恢复后的身份和任务状态进入 RuntimeTaskState，执行线才真正继续。", "Restored identity and task state enter RuntimeTaskState before the execution lane continues.", "復元された identity と task 状態が RuntimeTaskState に入り、その後で実行線が続きます。"),
      },
      {
        title: l("自治行为也必须留下可见状态", "Autonomous behavior must also leave visible state", "自律動作も見える状態を残す"),
        description: l("自治不是偷偷干活。系统必须看得见 claim 了什么、恢复到了哪里、目前执行到哪一步。", "Autonomy is not hidden activity. The system must still see what was claimed, what context was restored, and how far execution progressed.", "自律は隠れた作業ではありません。何を claim し、どこまで復元し、どこまで進んだかが見える必要があります。"),
        activeNodes: ["execute", "writeback", "idle-worker"],
        activeRecords: ["claim-event", "runtime-task"],
        boundary: l("如果自治过程没有状态回写，系统就很难调度、恢复和解释。", "Without write-back for autonomous progress, scheduling, recovery, and explanation all become harder.", "自律過程の回写がないと、調度・回復・説明が難しくなります。"),
        writeBack: l("回写后的自治状态会在下一次 idle 巡检或团队协作中继续被读取。", "Once written back, autonomous state becomes readable by the next idle scan or later collaboration.", "回写された自律状態は次の idle scan や後続協調で再び読まれます。"),
      },
    ],
  },
  s18: {
    lanes: [
      { id: "task", label: l("任务目标", "Task Goal", "task 目標"), note: l("任务板继续描述做什么。", "The task board still describes what to do.", "task board は引き続き何をするかを記述します。") },
      { id: "worktree", label: l("隔离车道", "Isolated Lane", "分離レーン"), note: l("worktree 管在哪做。", "The worktree decides where execution happens.", "worktree はどこで実行するかを管理します。") },
      { id: "runtime", label: l("执行生命周期", "Execution Lifecycle", "実行ライフサイクル"), note: l("enter / run / closeout 都要显式。", "enter / run / closeout must stay explicit.", "enter / run / closeout を明示します。") },
      { id: "return", label: l("收尾与事件", "Closeout + Events", "収束とイベント"), note: l("keep / remove 也是系统状态。", "keep / remove is also visible system state.", "keep / remove もシステム状態です。") },
    ],
    nodes: [
      { id: "task-goal", lane: "task", label: l("目标任务", "Task Goal", "task goal"), detail: l("任务记录仍是目标层。", "The task record still owns the goal.", "task record は引き続き goal を持ちます。") },
      { id: "assign", lane: "worktree", label: l("分配 worktree", "Assign Worktree", "worktree 割当"), detail: l("为任务分配隔离目录。", "Assign an isolated directory to the task.", "task に分離ディレクトリを割り当てます。") },
      { id: "enter", lane: "runtime", label: l("进入车道", "Enter Lane", "レーンに入る"), detail: l("显式进入隔离目录工作。", "Explicitly enter the isolated directory.", "明示的に分離ディレクトリへ入ります。") },
      { id: "run", lane: "runtime", label: l("隔离执行", "Run in Isolation", "分離実行"), detail: l("执行动作发生在独立车道。", "Execution happens inside the isolated lane.", "実行は独立レーンの中で起こります。") },
      { id: "closeout", lane: "return", label: l("closeout", "closeout", "closeout"), detail: l("决定 keep / remove / summarize。", "Decides keep / remove / summarize.", "keep / remove / summarize を決めます。") },
      { id: "event", lane: "return", label: l("车道事件", "Worktree Event", "worktree event"), detail: l("主系统要看见 create / enter / closeout。", "The main system should see create / enter / closeout.", "主システムは create / enter / closeout を見えるようにします。") },
    ],
    records: [
      { id: "worktree-state", label: l("worktree_state", "worktree_state", "worktree_state"), note: l("记录当前车道归属和状态。", "Tracks the worktree lane and its state.", "worktree lane と状態を記録します。") },
      { id: "last-worktree", label: l("last_worktree", "last_worktree", "last_worktree"), note: l("帮助系统知道任务最近在哪条车道上。", "Helps the system remember the last lane for a task.", "task が直近どの lane にいたかを覚えます。") },
      { id: "closeout-record", label: l("closeout", "closeout", "closeout"), note: l("描述车道最终怎么收尾。", "Describes how the lane is closed out.", "lane をどう収束させるかを表します。") },
    ],
    steps: [
      {
        title: l("任务目标和执行车道先分层", "Separate the task goal from the execution lane first", "task goal と execution lane を先に分ける"),
        description: l("这一章最重要的第一步是把‘做什么’和‘在哪做’拆开。任务板仍管目标，worktree 只管隔离执行环境。", "The first crucial step is to separate what should be done from where it runs. The task board still owns goals, while the worktree owns isolated execution space.", "最初の重要点は『何をするか』と『どこでやるか』を分けることです。"),
        activeNodes: ["task-goal", "assign"],
        activeRecords: ["worktree-state"],
        boundary: l("worktree 不是另一种 task，它只是任务的隔离执行车道。", "A worktree is not another kind of task. It is the task's isolated execution lane.", "worktree は別種の task ではなく、task の分離実行レーンです。"),
        writeBack: l("一旦分配了 worktree，任务就获得了明确的执行地点和 lane 状态。", "Once a worktree is assigned, the task gets a clear execution location and lane state.", "worktree が割り当てられると、task は明確な実行場所と lane 状態を持ちます。"),
      },
      {
        title: l("进入隔离目录后再执行", "Enter the isolated directory before executing", "分離ディレクトリへ入ってから実行する"),
        description: l("好的教学顺序要让读者看到：不是直接在目录里跑命令，而是先有 enter 动作，再有 run 动作。", "The right teaching order shows that you do not just run commands in a directory. You first enter the lane, then run inside it.", "正しい学習順序は『その場でコマンドを打つ』のではなく、『まず enter し、その後 run する』ことを見せます。"),
        activeNodes: ["assign", "enter", "run"],
        activeRecords: ["worktree-state", "last-worktree"],
        boundary: l("enter 是显式生命周期动作，不要把它写成隐含前提。", "enter is an explicit lifecycle action, not an implicit assumption.", "enter は明示的な lifecycle action であり、暗黙前提ではありません。"),
        writeBack: l("进入车道后，系统会更新 last_worktree，并在隔离目录里继续执行任务。", "After entering the lane, the system updates last_worktree and continues execution inside the isolated directory.", "lane へ入ったあと、last_worktree が更新され、その分離ディレクトリで実行が続きます。"),
      },
      {
        title: l("执行结束后必须走 closeout", "After execution, closeout is mandatory", "実行後は必ず closeout を通る"),
        description: l("Worktree 章节真正完整的地方不在 create，而在 closeout。keep、remove、summarize 都是显式收尾动作。", "What makes the worktree chapter complete is not creation but closeout. keep, remove, and summarize are all explicit end-of-lane actions.", "worktree 章が完全になるのは create ではなく closeout にあります。"),
        activeNodes: ["run", "closeout"],
        activeRecords: ["closeout-record", "worktree-state"],
        boundary: l("不要把 worktree 用完就静默丢掉；收尾策略本身就是系统机制。", "Do not silently discard a worktree after use. Closeout strategy is itself a system mechanism.", "使い終わった worktree を黙って捨てないでください。closeout 戦略そのものがシステム機構です。"),
        writeBack: l("closeout 决定这条 lane 是被保留、移除还是总结，并把结论写回主系统。", "closeout decides whether the lane is kept, removed, or summarized, and writes that conclusion back into the system.", "closeout は lane を keep / remove / summarize のどれにするかを決め、主システムへ書き戻します。"),
      },
      {
        title: l("车道事件让主系统看见执行面发生了什么", "Worktree events let the main system see what happened in the lane", "worktree event で主システムが lane 内の出来事を見えるようにする"),
        description: l("教学上要强调的是观察能力：主系统不仅看到结果，还看到 create、enter、closeout 等生命周期事件。", "The teaching emphasis here is observability. The main system should see not only the final result, but lifecycle events like create, enter, and closeout.", "ここで強調したいのは観測可能性です。主システムは最終結果だけでなく create・enter・closeout も見えるべきです。"),
        activeNodes: ["closeout", "event", "task-goal"],
        activeRecords: ["closeout-record", "worktree-state", "last-worktree"],
        boundary: l("没有 lane 事件，系统就只能看到‘做完了’，却不知道执行车道里发生过什么。", "Without lane events, the system only sees “done” and misses what happened inside the execution lane.", "lane event がないと、システムは『終わった』しか見えず、中で何が起きたか分かりません。"),
        writeBack: l("closeout 和 worktree event 一起把隔离车道的生命周期重新接回任务主线。", "closeout and worktree events reconnect the lane lifecycle back into the task mainline.", "closeout と worktree event がレーンのライフサイクルを task 主線へ戻します。"),
      },
    ],
  },
  s19: {
    lanes: [
      { id: "request", label: l("能力请求", "Capability Request", "capability 要求"), note: l("系统先提出‘需要什么能力’。", "The system first asks what capability it needs.", "システムはまず『どんな capability が必要か』を出します。") },
      { id: "router", label: l("统一路由", "Unified Router", "統一路由"), note: l("本地工具、插件和 MCP 在这里汇合。", "Native tools, plugins, and MCP converge here.", "native tool・plugin・MCP がここで合流します。") },
      { id: "execution", label: l("能力执行面", "Capability Execution", "capability 実行面"), note: l("本地与外部能力都能被调起。", "Both local and external capabilities can be invoked.", "ローカル能力も外部能力も呼び出せます。") },
      { id: "return", label: l("统一回流", "Unified Write-back", "統一回流"), note: l("结果最终要标准化回到主循环。", "Results must be normalized back into the main loop.", "結果は最終的に標準化され主ループへ戻ります。") },
    ],
    nodes: [
      { id: "capability-request", lane: "request", label: l("能力请求", "Capability Request", "capability request"), detail: l("不是先问它来自哪里，而是先问需要什么能力。", "Ask what capability is needed before asking where it comes from.", "どこから来たかより先に、何の capability が必要かを問います。") },
      { id: "catalog", lane: "router", label: l("能力目录", "Capability Catalog", "capability catalog"), detail: l("整理 native / plugin / MCP 能力视图。", "Unify native, plugin, and MCP capabilities in one catalog.", "native / plugin / MCP を 1 つの catalog にまとめます。") },
      { id: "policy", lane: "router", label: l("策略与授权", "Policy + Permission", "ポリシーと権限"), detail: l("外部能力也要过同一控制面。", "External capabilities still pass the same control plane.", "外部 capability も同じ control plane を通ります。") },
      { id: "native", lane: "execution", label: l("本地工具", "Native Tool", "native tool"), detail: l("本地能力是一种 capability。", "Native tools are one kind of capability.", "native tool も capability の一種です。") },
      { id: "plugin", lane: "execution", label: l("插件能力", "Plugin Capability", "plugin capability"), detail: l("插件把额外能力挂回系统。", "Plugins attach extra capability back into the system.", "plugin は追加 capability をシステムへ戻します。") },
      { id: "mcp", lane: "execution", label: l("MCP Server", "MCP Server", "MCP Server"), detail: l("远程 server 也能像 tool 一样被路由。", "Remote servers can be routed like tools.", "遠隔 server も tool のように route できます。") },
      { id: "normalize", lane: "return", label: l("标准化结果", "Normalize Result", "結果標準化"), detail: l("不同来源的结果都要转成统一格式。", "Results from different sources must become one common format.", "出所の違う結果を共通形式に変えます。") },
      { id: "tool-result", lane: "return", label: l("回写主循环", "Write Back to Loop", "主ループへ回写"), detail: l("最后回到统一 tool_result / event 通道。", "Everything returns through the same tool_result / event bus.", "最後は同じ tool_result / event bus に戻ります。") },
    ],
    records: [
      { id: "capability-spec", label: l("CapabilitySpec", "CapabilitySpec", "CapabilitySpec"), note: l("把本地与外部能力抽象到同一视图。", "Abstracts local and external capabilities into one view.", "ローカル能力と外部能力を同じ視点へ抽象化します。") },
      { id: "permission-decision", label: l("PermissionDecision", "PermissionDecision", "PermissionDecision"), note: l("外部能力仍然共享权限层。", "External capabilities still share the permission plane.", "外部 capability も permission plane を共有します。") },
      { id: "tool-result", label: l("tool_result / event", "tool_result / event", "tool_result / event"), note: l("最后统一回流的格式。", "The unified return format.", "最終的な統一回流形式です。") },
    ],
    steps: [
      {
        title: l("先从‘需要什么能力’而不是‘它来自哪里’开始", "Start from the needed capability, not its origin", "必要な capability から始め、出所から始めない"),
        description: l("MCP 与 Plugin 章节最重要的第一步，是把注意力放在 capability request，而不是 transport 细节。", "The first important move in the MCP and plugin chapter is to focus on capability requests, not transport details.", "MCP と plugin 章で最初に重要なのは transport 詳細ではなく capability request に注目することです。"),
        activeNodes: ["capability-request", "catalog"],
        activeRecords: ["capability-spec"],
        boundary: l("教学主线应先坚持 tools-first / capability-first，而不是先掉进协议细节。", "The teaching mainline should stay tools-first / capability-first before diving into protocol detail.", "学習主線は protocol 詳細より先に tools-first / capability-first を保つべきです。"),
        writeBack: l("能力请求进入统一 catalog，系统才知道有哪些 native / plugin / MCP 路由可选。", "The capability request enters a unified catalog so the system can see native, plugin, and MCP routes together.", "capability request が統一 catalog へ入り、native / plugin / MCP の選択肢が見えるようになります。"),
      },
      {
        title: l("所有能力都先过统一路由与策略层", "All capabilities pass through one router and policy layer first", "すべての capability を統一路由とポリシー層へ通す"),
        description: l("MCP 不是例外外挂。只要它是系统能力，就应该像本地工具一样被发现、选择、授权。", "MCP is not a special exception. If it is a system capability, it should be discovered, selected, and authorized like any native tool.", "MCP は特例ではありません。システム capability なら native tool と同じように発見・選択・認可されます。"),
        activeNodes: ["catalog", "policy"],
        activeRecords: ["capability-spec", "permission-decision"],
        boundary: l("外部能力不能绕过权限与路由层，否则整套控制面会断裂。", "External capabilities must not bypass routing and permissions or the control plane breaks apart.", "外部 capability が routing と permission を迂回すると control plane が壊れます。"),
        writeBack: l("通过策略后，路由器才决定是走 native tool、plugin 还是 MCP server。", "Only after policy approval does the router choose between native, plugin, or MCP execution.", "ポリシー通過後に router が native / plugin / MCP のどれへ行くか決めます。"),
      },
      {
        title: l("本地工具、插件、MCP 只是不同执行来源", "Native tools, plugins, and MCP are different execution sources", "native tool・plugin・MCP は実行元が違うだけ"),
        description: l("一旦进入能力执行面，教学重点就变成：来源不同，但都是被同一 capability bus 调起。", "Once you enter capability execution, the teaching focus becomes: the sources differ, but the same capability bus invokes them all.", "capability 実行面に入ると、重要なのは『出所は違っても同じ bus で呼ばれる』ことです。"),
        activeNodes: ["policy", "native", "plugin", "mcp"],
        activeRecords: ["capability-spec"],
        boundary: l("不要把 plugin 或 MCP 讲成孤立外挂；它们只是统一能力总线上的不同端点。", "Do not teach plugins or MCP as isolated add-ons. They are different endpoints on one shared capability bus.", "plugin や MCP を孤立した追加物として教えないでください。共有 capability bus 上の別 endpoint です。"),
        writeBack: l("无论走哪条执行来源，结果都还需要再标准化后才能回到主循环。", "No matter which execution source is used, the result still must be normalized before it re-enters the main loop.", "どの実行元を通っても、結果は標準化されてから主ループへ戻ります。"),
      },
      {
        title: l("最终仍回到统一结果总线", "Everything still returns through one result bus", "最終的には同じ結果 bus へ戻る"),
        description: l("这章真正让系统完整的地方，是外部能力虽然多源，但最后仍然回到统一 tool_result / event 总线。", "The chapter becomes complete when multi-source external capability still returns through one unified tool_result / event bus.", "この章が完成するのは、多元の外部 capability が最終的に同じ tool_result / event bus へ戻るときです。"),
        activeNodes: ["native", "plugin", "mcp", "normalize", "tool-result"],
        activeRecords: ["permission-decision", "tool-result"],
        boundary: l("如果不同来源的结果不能统一回流，主循环就会被迫理解很多套执行语义。", "If results from different sources cannot be normalized, the main loop must understand too many execution dialects.", "出所ごとに結果がバラバラだと、主ループが多くの実行方言を理解しなければなりません。"),
        writeBack: l("标准化后的 tool_result / event 把外部能力重新接回原有 agent 主线。", "Normalized tool_result / event reconnects external capability back into the existing agent mainline.", "標準化された tool_result / event が外部 capability を既存の agent 主線へ戻します。"),
      },
    ],
  },
};

export function hasLateStageTeachingMap(version: string): version is LateStageVersion {
  return version in SCENARIOS;
}

export function LateStageTeachingMap({ version }: { version: LateStageVersion }) {
  const locale = useLocale();
  const scenario = SCENARIOS[version];
  const meta = VERSION_META[version];

  if (!scenario || !meta) return null;

  const accent = ACCENT_CLASSES[meta.layer];
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({
    totalSteps: scenario.steps.length,
    autoPlayInterval: 2600,
  });

  const step = scenario.steps[currentStep];
  const nodeMap = new Map(scenario.nodes.map((node) => [node.id, node]));
  const activeNodes = new Set(step.activeNodes);
  const activeRecords = new Set(step.activeRecords);

  return (
    <div
      className={`overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[var(--color-bg)] shadow-sm ring-1 dark:border-zinc-800/80 ${accent.ring}`}
    >
      <div className={`relative overflow-hidden bg-gradient-to-br ${accent.tint} px-5 py-6 sm:px-6`}>
        <div className="absolute right-[-50px] top-[-46px] h-40 w-40 rounded-full bg-white/35 blur-3xl dark:bg-white/5" />
        <div className="relative space-y-3">
          <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${accent.pill}`}>
            {pick(locale, UI_TEXT.label)}
          </span>
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {pick(locale, UI_TEXT.title)}
            </h3>
            <p className="mt-2 max-w-4xl text-sm leading-7 text-zinc-700 dark:text-zinc-300">
              {pick(locale, UI_TEXT.body)}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6 px-5 py-5 sm:px-6">
        <StepControls
          currentStep={currentStep}
          totalSteps={totalSteps}
          onPrev={prev}
          onNext={next}
          onReset={reset}
          isPlaying={isPlaying}
          onToggleAutoPlay={toggleAutoPlay}
          stepTitle={pick(locale, step.title)}
          stepDescription={pick(locale, step.description)}
        />

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.95fr)]">
          <section className="rounded-[24px] border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800 dark:bg-zinc-950/60">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                  {pick(locale, UI_TEXT.systemLanes)}
                </p>
              </div>
              <div className={`rounded-full px-3 py-1 text-xs font-medium ${accent.soft}`}>
                {version.toUpperCase()}
              </div>
            </div>

            <div className="space-y-3">
              {scenario.lanes.map((lane, laneIndex) => {
                const laneNodes = scenario.nodes.filter((node) => node.lane === lane.id);
                return (
                  <motion.div
                    key={lane.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.28, delay: laneIndex * 0.05 }}
                    className={`rounded-[22px] border bg-zinc-50/80 p-3 dark:bg-zinc-900/80 ${accent.border}`}
                  >
                    <div className="grid gap-3 lg:grid-cols-[152px_minmax(0,1fr)]">
                      <div className="rounded-2xl border border-dashed border-zinc-300/80 bg-white/80 px-3 py-3 dark:border-zinc-700 dark:bg-zinc-950/60">
                        <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                          {pick(locale, lane.label)}
                        </div>
                        <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                          {pick(locale, lane.note)}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-3">
                        {laneNodes.map((node, nodeIndex) => {
                          const isActive = activeNodes.has(node.id);
                          return (
                            <motion.div
                              key={node.id}
                              initial={{ opacity: 0, scale: 0.96 }}
                              animate={{
                                opacity: 1,
                                scale: isActive ? 1.02 : 1,
                                y: isActive ? -1 : 0,
                              }}
                              transition={{ duration: 0.24, delay: nodeIndex * 0.04 }}
                              className={`min-w-[172px] flex-1 rounded-2xl border px-4 py-3 shadow-sm transition-colors ${
                                isActive
                                  ? `${accent.pill} ring-1 ${accent.ring}`
                                  : "border-zinc-200/80 bg-white text-zinc-700 dark:border-zinc-800 dark:bg-zinc-950/70 dark:text-zinc-300"
                              }`}
                            >
                              <div className="text-sm font-semibold">
                                {pick(locale, node.label)}
                              </div>
                              <p className="mt-1 text-xs leading-5 opacity-85">
                                {pick(locale, node.detail)}
                              </p>
                            </motion.div>
                          );
                        })}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <div className="rounded-[22px] border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800 dark:bg-zinc-950/60">
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                {pick(locale, UI_TEXT.activePath)}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {step.activeNodes.map((nodeId, index) => {
                  const node = nodeMap.get(nodeId);
                  if (!node) return null;
                  return (
                    <div key={nodeId} className="contents">
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.24, delay: index * 0.05 }}
                        className={`inline-flex items-center rounded-full border px-3 py-2 text-xs font-medium shadow-sm ${accent.pill}`}
                      >
                        {pick(locale, node.label)}
                      </motion.div>
                      {index < step.activeNodes.length - 1 && (
                        <span className="text-zinc-300 dark:text-zinc-600">-&gt;</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-[22px] border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800 dark:bg-zinc-950/60">
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                {pick(locale, UI_TEXT.activeRecords)}
              </p>
              <div className="mt-3 space-y-2">
                {scenario.records.map((record) => {
                  const isActive = activeRecords.has(record.id);
                  return (
                    <div
                      key={record.id}
                      className={`rounded-2xl border px-3 py-3 transition-colors ${
                        isActive
                          ? `${accent.pill} ring-1 ${accent.ring}`
                          : "border-zinc-200/80 bg-zinc-50/80 dark:border-zinc-800 dark:bg-zinc-900/70"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                          {pick(locale, record.label)}
                        </div>
                        {!isActive && (
                          <span className="text-[11px] text-zinc-400">
                            {pick(locale, UI_TEXT.inactiveRecord)}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                        {pick(locale, record.note)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className={`rounded-[22px] border bg-zinc-50/90 p-4 dark:bg-zinc-900/70 ${accent.border}`}>
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                {pick(locale, UI_TEXT.boundary)}
              </p>
              <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                {pick(locale, step.boundary)}
              </p>
            </div>

            <div className={`rounded-[22px] border bg-zinc-50/90 p-4 dark:bg-zinc-900/70 ${accent.border}`}>
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                {pick(locale, UI_TEXT.writeBack)}
              </p>
              <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                {pick(locale, step.writeBack)}
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
