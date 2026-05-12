import { VERSION_META, type VersionId } from "@/lib/constants";

export type LearningLocale = "zh" | "en" | "ja";

type VersionContent = {
  subtitle: string;
  coreAddition: string;
  keyInsight: string;
};

const VERSION_CONTENT: Record<LearningLocale, Record<VersionId, VersionContent>> = {
  zh: {
    s01: {
      subtitle: "最小闭环",
      coreAddition: "LoopState + tool_result 回流",
      keyInsight: "真正的 agent 起点，是把真实工具结果重新喂回模型，而不只是输出一段文本。",
    },
    s02: {
      subtitle: "把意图路由成动作",
      coreAddition: "工具规格 + 分发映射",
      keyInsight: "主循环本身不用变复杂；工具能力靠一层清晰的路由面增长。",
    },
    s03: {
      subtitle: "会话级计划",
      coreAddition: "PlanningState + reminder loop",
      keyInsight: "对多步骤任务来说，可见计划不是装饰，而是防止会话漂移的稳定器。",
    },
    s04: {
      subtitle: "子任务使用全新上下文",
      coreAddition: "带隔离消息历史的委派",
      keyInsight: "把探索性工作移进干净上下文后，父 agent 才能持续盯住主目标。",
    },
    s05: {
      subtitle: "先轻发现，再深加载",
      coreAddition: "技能注册表 + 按需注入",
      keyInsight: "专门知识不该一开始全部塞进上下文，而该在需要时被轻量发现、按需展开。",
    },
    s06: {
      subtitle: "保持活跃上下文小而稳",
      coreAddition: "持久标记 + 微压缩 + 总结压缩",
      keyInsight: "压缩的目标不是删历史，而是保住连续性和下一步所需的工作记忆。",
    },
    s07: {
      subtitle: "意图先过安全闸门",
      coreAddition: "deny / mode / allow / ask 管线",
      keyInsight: "模型产生的执行意图，必须先通过清晰的权限门，再变成真正动作。",
    },
    s08: {
      subtitle: "不改主循环也能扩展",
      coreAddition: "生命周期事件 + 副作用 Hook",
      keyInsight: "Hook 让系统围绕主循环生长，而不是不断重写主循环本身。",
    },
    s09: {
      subtitle: "只保存跨会话还成立的东西",
      coreAddition: "类型化记忆记录 + reload 路径",
      keyInsight: "只有跨会话、无法从当前工作重新推导的知识，才值得进入 memory。",
    },
    s10: {
      subtitle: "把输入组装成流水线",
      coreAddition: "Prompt 分段 + 动态装配",
      keyInsight: "模型看到的不是一坨固定 prompt，而是一条按阶段拼装的输入流水线。",
    },
    s11: {
      subtitle: "先恢复，再继续",
      coreAddition: "continuation reason + retry 分支",
      keyInsight: "系统必须清楚自己此刻是在继续、重试，还是处于恢复流程。",
    },
    s12: {
      subtitle: "持久化工作图",
      coreAddition: "Task 记录 + 依赖 + 解锁规则",
      keyInsight: "Todo 适合会话内规划，持久任务图才负责跨步骤、跨阶段协调工作。",
    },
    s13: {
      subtitle: "把任务目标和运行槽位分开",
      coreAddition: "RuntimeTaskState + 异步执行槽位",
      keyInsight: "持久任务描述要完成什么，运行槽位描述谁在跑、跑到哪里；两者相关但不是一回事。",
    },
    s14: {
      subtitle: "让时间也能触发工作",
      coreAddition: "基于 runtime task 的定时触发",
      keyInsight: "当任务能后台运行以后，时间本身也会变成另一种启动入口。",
    },
    s15: {
      subtitle: "长驻的专职队友",
      coreAddition: "团队 roster + teammate 生命周期",
      keyInsight: "系统一旦长期运行，就需要有名字、有身份、可持续存在的队友，而不只是一次性子任务。",
    },
    s16: {
      subtitle: "共享请求-响应规则",
      coreAddition: "协议信封 + 请求关联",
      keyInsight: "团队只有在协作遵守共同消息模式时，才会变得可理解、可调试、可扩展。",
    },
    s17: {
      subtitle: "自主认领，自主续跑",
      coreAddition: "空闲轮询 + 角色感知认领 + 恢复上下文",
      keyInsight: "自主性开始于：队友能安全找到可做的事、认领它，并带着正确身份继续执行。",
    },
    s18: {
      subtitle: "独立目录，独立车道",
      coreAddition: "task-worktree 状态 + 显式 enter / closeout 生命周期",
      keyInsight: "task 管目标，worktree 管隔离执行车道和收尾状态；两者不能混成一个概念。",
    },
    s19: {
      subtitle: "外部能力总线",
      coreAddition: "作用域服务器 + 能力路由",
      keyInsight: "外部能力系统不该是外挂；它们应和原生工具一起处在同一控制面上。",
    },
  },
  en: {
    s01: {
      subtitle: "Minimal Closed Loop",
      coreAddition: "LoopState + tool_result feedback",
      keyInsight: "An agent is just a loop: send messages, execute tools, feed results back, repeat.",
    },
    s02: {
      subtitle: "Route Intent into Action",
      coreAddition: "Tool specs + dispatch map",
      keyInsight: "Adding a tool means adding one handler. The loop never changes.",
    },
    s03: {
      subtitle: "Session Planning",
      coreAddition: "PlanningState + reminder loop",
      keyInsight: "A visible plan keeps the agent on track when tasks get complex.",
    },
    s04: {
      subtitle: "Fresh Context per Subtask",
      coreAddition: "Delegation with isolated message history",
      keyInsight: "A subagent is mainly a context boundary, not a process trick.",
    },
    s05: {
      subtitle: "Discover Cheaply, Load Deeply",
      coreAddition: "Skill registry + on-demand injection",
      keyInsight: "Discover cheaply, load deeply -- only when needed.",
    },
    s06: {
      subtitle: "Keep Active Context Small and Stable",
      coreAddition: "Persist markers + micro compact + summary compact",
      keyInsight: "Compaction isn't deleting history -- it's relocating detail so the agent can keep working.",
    },
    s07: {
      subtitle: "Intent Must Pass a Safety Gate",
      coreAddition: "deny / mode / allow / ask pipeline",
      keyInsight: "Safety is a pipeline, not a boolean: deny, check mode, allow, then ask.",
    },
    s08: {
      subtitle: "Extend Without Rewriting the Loop",
      coreAddition: "Lifecycle events + side-effect hooks",
      keyInsight: "The loop owns control flow; hooks only observe, block, or annotate at named moments.",
    },
    s09: {
      subtitle: "Keep Only What Survives Sessions",
      coreAddition: "Typed memory records + reload path",
      keyInsight: "Memory gives direction; current observation gives truth.",
    },
    s10: {
      subtitle: "Assemble Inputs as a Pipeline",
      coreAddition: "Prompt sections + dynamic assembly",
      keyInsight: "The model sees a constructed input pipeline, not one giant static string.",
    },
    s11: {
      subtitle: "Recover, Then Continue",
      coreAddition: "Continuation reasons + retry branches",
      keyInsight: "Most failures aren't true task failure -- they're signals to try a different path.",
    },
    s12: {
      subtitle: "Durable Work Graph",
      coreAddition: "Task records + dependencies + unlock rules",
      keyInsight: "Todo lists help a session; durable task graphs coordinate work that outlives it.",
    },
    s13: {
      subtitle: "Background Execution Lanes",
      coreAddition: "RuntimeTaskState + async execution slots",
      keyInsight: "Background execution is a runtime lane, not a second main loop.",
    },
    s14: {
      subtitle: "Let Time Trigger Work",
      coreAddition: "Scheduled triggers over runtime tasks",
      keyInsight: "Scheduling is not a separate system -- it just feeds the same agent loop from a timer.",
    },
    s15: {
      subtitle: "Persistent Specialist Teammates",
      coreAddition: "Team roster + teammate lifecycle",
      keyInsight: "Teammates persist beyond one prompt, have identity, and coordinate through durable channels.",
    },
    s16: {
      subtitle: "Shared Request-Response Rules",
      coreAddition: "Protocol envelopes + request correlation",
      keyInsight: "A protocol request is a structured message with an ID; the response must reference the same ID.",
    },
    s17: {
      subtitle: "Self-Claim, Self-Resume",
      coreAddition: "Idle polling + role-aware self-claim + resume context",
      keyInsight: "Autonomy is a bounded mechanism -- idle, scan, claim, resume -- not magic.",
    },
    s18: {
      subtitle: "Separate Directory, Separate Lane",
      coreAddition: "Task-worktree state + explicit enter / closeout lifecycle",
      keyInsight: "Tasks answer what; worktrees answer where. Keep them separate.",
    },
    s19: {
      subtitle: "External Capability Bus",
      coreAddition: "Scoped servers + capability routing",
      keyInsight: "External capabilities join the same routing, permission, and result-append path as native tools.",
    },
  },
  ja: {
    s01: {
      subtitle: "最小の閉ループ",
      coreAddition: "LoopState + tool_result の戻し込み",
      keyInsight: "本当の agent の始まりは、実際のツール結果をモデルへ戻すところにあり、単なる文章出力ではありません。",
    },
    s02: {
      subtitle: "意図を実行へルーティングする",
      coreAddition: "ツール仕様 + ディスパッチマップ",
      keyInsight: "主ループを複雑にしなくても、きれいなルーティング層を置けばツール能力は増やせます。",
    },
    s03: {
      subtitle: "セッション計画",
      coreAddition: "PlanningState + reminder loop",
      keyInsight: "多段作業では、見える計画は飾りではなく、会話の漂流を防ぐ安定器です。",
    },
    s04: {
      subtitle: "サブタスクごとに新しい文脈を使う",
      coreAddition: "分離されたメッセージ履歴を持つ委譲",
      keyInsight: "探索作業をきれいなサブコンテキストへ移して初めて、親 agent は主目標へ集中し続けられます。",
    },
    s05: {
      subtitle: "軽く見つけて、必要時に深く読む",
      coreAddition: "スキルレジストリ + オンデマンド注入",
      keyInsight: "専門知識は最初から全部を文脈へ詰め込まず、必要になった時だけ軽く見つけて深く展開するべきです。",
    },
    s06: {
      subtitle: "活性コンテキストを小さく安定させる",
      coreAddition: "永続マーカー + micro compact + summary compact",
      keyInsight: "圧縮の目的は履歴を消すことではなく、連続性と次の一歩に必要な作業記憶を守ることです。",
    },
    s07: {
      subtitle: "意図は先に安全ゲートを通る",
      coreAddition: "deny / mode / allow / ask パイプライン",
      keyInsight: "モデルが出した実行意図は、明確な権限ゲートを通った後で初めて実動作になるべきです。",
    },
    s08: {
      subtitle: "主ループを書き換えずに拡張する",
      coreAddition: "ライフサイクルイベント + 副作用 Hook",
      keyInsight: "Hook は主ループの周囲へ機能を育てるためのもので、主ループ自体を何度も書き換えるためのものではありません。",
    },
    s09: {
      subtitle: "セッションを越えて残るものだけ保存する",
      coreAddition: "型付き memory record + reload 経路",
      keyInsight: "現在の作業空間から再導出できない、セッションを越えて有効な知識だけが memory に入る価値があります。",
    },
    s10: {
      subtitle: "入力をパイプラインとして組み立てる",
      coreAddition: "Prompt セクション + 動的組み立て",
      keyInsight: "モデルが見るのは巨大な固定 prompt 文字列ではなく、実行時に組み上がる入力パイプラインです。",
    },
    s11: {
      subtitle: "回復してから続行する",
      coreAddition: "continuation reason + retry 分岐",
      keyInsight: "完成度の高い agent は、いま続行中なのか、再試行中なのか、回復処理中なのかを自分で区別できなければなりません。",
    },
    s12: {
      subtitle: "永続ワークグラフ",
      coreAddition: "Task record + 依存 + 解放ルール",
      keyInsight: "Todo はセッション内計画に向きますが、長い作業の調整を担うのは永続 task graph です。",
    },
    s13: {
      subtitle: "タスク目標と実行スロットを分ける",
      coreAddition: "RuntimeTaskState + 非同期実行スロット",
      keyInsight: "永続タスクは何を終えるべきかを表し、実行スロットは誰がどこまで走っているかを表します。両者は関連しますが同一ではありません。",
    },
    s14: {
      subtitle: "時間でも仕事を起動できるようにする",
      coreAddition: "runtime task 上の定時トリガー",
      keyInsight: "タスクがバックグラウンド実行できるようになると、時間そのものも起動入口の一つになります。",
    },
    s15: {
      subtitle: "常駐する専門チームメイト",
      coreAddition: "チーム roster + teammate lifecycle",
      keyInsight: "長く動くシステムには、その場限りのサブタスクではなく、名前と役割を持って居続けるチームメイトが必要です。",
    },
    s16: {
      subtitle: "共有された request-response 規則",
      coreAddition: "プロトコル封筒 + request の相関付け",
      keyInsight: "協調が共通メッセージ規則に従う時、チームは初めて理解しやすく、デバッグしやすく、拡張しやすくなります。",
    },
    s17: {
      subtitle: "自分で引き受け、自分で再開する",
      coreAddition: "アイドル polling + 役割認識 claim + resume context",
      keyInsight: "自律性は、チームメイトが実行可能な仕事を安全に見つけ、引き受け、正しい身元文脈で再開できるところから始まります。",
    },
    s18: {
      subtitle: "別ディレクトリ、別レーン",
      coreAddition: "task-worktree 状態 + 明示的な enter / closeout lifecycle",
      keyInsight: "task は目標を管理し、worktree は隔離された実行レーンと収束状態を管理します。この二つは混ぜてはいけません。",
    },
    s19: {
      subtitle: "外部 capability bus",
      coreAddition: "scope 付き server + capability routing",
      keyInsight: "外部 capability system は後付けの別物ではなく、ネイティブツールと同じ control plane に置くべきです。",
    },
  },
};

export function normalizeLearningLocale(locale: string): LearningLocale {
  if (locale === "zh" || locale === "ja") return locale;
  return "en";
}

export function getVersionContent(version: string, locale: string): VersionContent {
  const normalizedLocale = normalizeLearningLocale(locale);
  const content =
    VERSION_CONTENT[normalizedLocale][version as VersionId] ??
    VERSION_CONTENT.en[version as VersionId];

  if (content) return content;

  const fallback = VERSION_META[version];

  return {
    subtitle: fallback?.subtitle ?? "",
    coreAddition: fallback?.coreAddition ?? "",
    keyInsight: fallback?.keyInsight ?? "",
  };
}
