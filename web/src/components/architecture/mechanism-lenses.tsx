import type { VersionId } from "@/lib/constants";

type LocaleText = {
  zh: string;
  en: string;
  ja: string;
};

interface VersionMechanismLensesProps {
  version: string;
  locale: string;
}

const SECTION_TEXT = {
  label: {
    zh: "关键机制镜头",
    en: "Mechanism Lens",
    ja: "重要メカニズムの見取り図",
  },
  title: {
    zh: "把本章最容易打结的一层单独拆开",
    en: "Pull out the one mechanism most likely to tangle in this chapter",
    ja: "この章で最も混線しやすい層を単独でほどく",
  },
  body: {
    zh: "这不是重复正文，而是把真正关键的运行规则、状态边界和回流方向压成一张能反复回看的教学图。先看这里，再回正文，会更容易守住主线。",
    en: "This does not replace the chapter body. It compresses the most important runtime rule, state boundary, and write-back path into one reusable teaching view.",
    ja: "本文の繰り返しではなく、重要な runtime rule・state boundary・write-back path を一枚に圧縮した補助図です。ここを先に見ると本文の主線を保ちやすくなります。",
  },
} as const;

const TOOL_RUNTIME_VERSION_ANGLE: Partial<Record<VersionId, LocaleText>> = {
  s02: {
    zh: "这一章第一次把 model 的 tool intent 接进统一执行面，所以重点不是“多了几个工具”，而是“调用如何进入稳定 runtime”。",
    en: "This is the first chapter where model tool intent enters one execution plane. The point is not just more tools, but a stable runtime entry path.",
    ja: "この章では model の tool intent が初めて 1 つの execution plane に入ります。増えた tool よりも、安定した runtime 入口を作ることが主題です。",
  },
  s07: {
    zh: "权限系统不是独立岛屿，它是插在真正执行之前的一道 runtime 闸门。",
    en: "The permission system is not an isolated island. It is a runtime gate inserted before real execution.",
    ja: "権限層は独立した島ではなく、実行直前に差し込まれる安全ゲートです。",
  },
  s13: {
    zh: "后台任务会让结果不再总是当前 turn 立即回写，所以你必须开始把执行槽位和回流顺序分开看。",
    en: "Background tasks mean results do not always write back in the same turn, so execution slots and write-back order must become separate ideas.",
    ja: "バックグラウンド実行が入ると、結果は同じ turn に即時回写されるとは限りません。だから実行スロットと回写順序を分けて見る必要があります。",
  },
  s19: {
    zh: "到了 MCP 与 Plugin，这一层的重点是：本地工具、插件和外部 server 虽然来源不同，但最终都要回到同一执行面。",
    en: "With MCP and plugins, the key is that native tools, plugins, and external servers may come from different places but still return to one execution plane.",
    ja: "MCP と plugin の段階では、native tool・plugin・外部 server が出自は違っても最終的には同じ execution plane へ戻ることが重要です。",
  },
};

const QUERY_TRANSITION_VERSION_ANGLE: Partial<Record<VersionId, LocaleText>> = {
  s06: {
    zh: "压缩刚出现时，读者很容易还把 query 想成一个 while loop。这一章开始就该意识到：状态已经会影响下一轮为什么继续。",
    en: "When compaction first appears, readers still tend to picture a plain while-loop. This is where state starts changing why the next turn exists.",
    ja: "compact が出た直後は query を単なる while loop と見がちです。しかしこの章から、state が次の turn の存在理由を変え始めます。",
  },
  s11: {
    zh: "错误恢复真正提升系统完成度的地方，不是 try/except，而是系统能明确写出这次继续、重试或结束的原因。",
    en: "What really raises completion in recovery is not `try/except`, but the system knowing exactly why it continues, retries, or stops.",
    ja: "error recovery で完成度を押し上げるのは try/except そのものではなく、なぜ continue・retry・stop するのかを明示できる点です。",
  },
  s17: {
    zh: "自治车道会自己认领和恢复任务，所以 transition reason 不再只是单 agent 的内部细节，而是自治行为的稳定器。",
    en: "Autonomous lanes claim and resume work on their own, so transition reasons stop being an internal detail and become part of the system stabilizer.",
    ja: "自治レーンは自分で task を claim・resume するため、transition reason は単 agent の内部 detail ではなく、自治動作を安定化する要素になります。",
  },
};

const TASK_RUNTIME_VERSION_ANGLE: Partial<Record<VersionId, LocaleText>> = {
  s12: {
    zh: "这一章只建立 durable work graph。现在最重要的护栏是：先把“目标任务”讲干净，不要提前把后台执行槽位塞进来。",
    en: "This chapter only establishes the durable work graph. The main guardrail is to keep goal tasks clean before you push runtime execution slots into the same model.",
    ja: "この章では durable work graph だけを作ります。最大のガードレールは、バックグラウンド実行スロットを混ぜる前に作業目標タスクをきれいに保つことです。",
  },
  s13: {
    zh: "后台任务真正新增的不是“又一种任务”，而是“任务目标之外，还要单独管理一层活着的执行槽位”。",
    en: "Background tasks do not add just another task. They add a second layer of live execution slots outside the task goal itself.",
    ja: "バックグラウンド実行が増やすのは task の別名ではなく、作業目標の外にある live execution slot という別層です。",
  },
  s14: {
    zh: "到了定时调度，读者最容易把 schedule、task、runtime slot 混成一团，所以必须把“谁定义目标、谁负责触发、谁真正执行”拆开看。",
    en: "Cron scheduling is where schedule, task, and runtime slot start to blur together. The safe mental model is to separate who defines the goal, who triggers it, and who actually executes.",
    ja: "cron に入ると schedule・task・runtime slot が混ざりやすくなります。goal を定義する層、発火させる層、実行する層を分けて見る必要があります。",
  },
};

const TEAM_BOUNDARY_VERSION_ANGLE: Partial<Record<VersionId, LocaleText>> = {
  s15: {
    zh: "这章的重点不是“多开几个 agent”，而是让系统第一次拥有长期存在、可重复协作的 teammate 身份层。",
    en: "The point of this chapter is not merely more agents. It is the first time the system gains persistent teammate identities that can collaborate repeatedly.",
    ja: "この章の要点は agent を増やすことではなく、反復して協調できる persistent teammate identity を初めて持つことです。",
  },
  s16: {
    zh: "团队协议真正新增的是“可追踪的协调请求层”，不是普通聊天消息的花样变体。",
    en: "Team protocols introduce a traceable coordination-request layer, not just another style of chat message.",
    ja: "team protocol が増やすのは追跡可能な協調要求レイヤーであり、普通の chat message の変種ではありません。",
  },
  s17: {
    zh: "自治行为最容易讲糊的地方，是 teammate、task、runtime slot 三层同时动起来。所以这一章必须盯紧“谁在认领、谁在执行、谁在记录目标”。",
    en: "Autonomy becomes confusing when teammate, task, and runtime slot all move at once. This chapter must keep clear who is claiming, who is executing, and who records the goal.",
    ja: "autonomy で混線しやすいのは teammate・task・runtime slot が同時に動き出す点です。誰が claim し、誰が execute し、誰が goal を記録しているかを保つ必要があります。",
  },
  s18: {
    zh: "worktree 最容易被误解成另一种任务，其实它只是执行目录车道。任务管目标，runtime slot 管执行，worktree 管在哪做。",
    en: "Worktrees are easy to misread as another kind of task, but they are execution-directory lanes. Tasks manage goals, runtime slots manage execution, and worktrees manage where execution happens.",
    ja: "worktree は別種の task と誤解されがちですが、実際は実行ディレクトリのレーンです。task は goal、runtime slot は execution、worktree はどこで実行するかを管理します。",
  },
};

const CAPABILITY_LAYER_VERSION_ANGLE: Partial<Record<VersionId, LocaleText>> = {
  s19: {
    zh: "这一章正文仍应坚持 tools-first，但页面必须额外提醒读者：MCP 平台真正长出来后，tools 只是 capability stack 里最先进入主线的那一层。",
    en: "The chapter body should still stay tools-first, but the page should also remind readers that once the MCP platform grows up, tools are only the first layer of the capability stack to enter the mainline.",
    ja: "本文は引き続き tools-first でよい一方、ページ上では tools が capability stack の最初の層にすぎないことも明示すべきです。",
  },
};

const TOOL_RUNTIME_TEXT = {
  label: {
    zh: "工具执行运行时",
    en: "Tool Execution Runtime",
    ja: "ツール実行の流れ",
  },
  title: {
    zh: "不要把工具调用压扁成“handler 一跑就完”",
    en: "Do not flatten tool calls into one handler invocation",
    ja: "tool call を単なる handler 呼び出しに潰さない",
  },
  note: {
    zh: "更完整的系统，会先判断这些 tool block 应该怎么分批、怎么执行、怎么稳定回写，而不是一股脑直接跑。",
    en: "A more complete system first decides how tool blocks should be batched, executed, and written back instead of running everything immediately.",
    ja: "より構造の整った system は、tool block を即座に全部走らせるのではなく、どう batch 化し、どう実行し、どう安定回写するかを先に決めます。",
  },
  angleLabel: {
    zh: "本章为什么要盯这层",
    en: "Why This Lens Matters Here",
    ja: "この章でこの層を見る理由",
  },
  rulesLabel: {
    zh: "运行规则",
    en: "Runtime Rules",
    ja: "実行ルール",
  },
  recordsLabel: {
    zh: "核心记录",
    en: "Core Records",
    ja: "主要レコード",
  },
  safeLane: {
    title: {
      zh: "Safe 批次",
      en: "Safe Batch",
      ja: "安全バッチ",
    },
    body: {
      zh: "读多写少、共享状态风险低的工具可以并发执行，但 progress 和 context modifier 仍然要被跟踪。",
      en: "Read-heavy, low-risk tools can execute concurrently, but progress and context modifiers still need tracking.",
      ja: "読み取り中心で共有 state リスクの低い tool は並列実行できますが、progress と context modifier の追跡は必要です。",
    },
  },
  exclusiveLane: {
    title: {
      zh: "Exclusive 批次",
      en: "Exclusive Batch",
      ja: "直列バッチ",
    },
    body: {
      zh: "会改文件、会改共享状态、会影响顺序的工具要留在串行车道，避免把 runtime 变成非确定性。",
      en: "File writes, shared-state mutation, and order-sensitive tools stay in a serial lane to keep the runtime deterministic.",
      ja: "file write・共有 state mutation・順序依存の tool は直列 lane に残し、runtime を非決定化させません。",
    },
  },
  stages: [
    {
      eyebrow: {
        zh: "Step 1",
        en: "Step 1",
        ja: "ステップ 1",
      },
      title: {
        zh: "接住 tool blocks",
        en: "Capture tool blocks",
        ja: "tool blocks を受け止める",
      },
      body: {
        zh: "先把 model 产出的 tool_use block 视为一批待调度对象，而不是一出现就立刻执行。",
        en: "Treat model-emitted tool_use blocks as a schedulable set before executing them immediately.",
        ja: "model が出した tool_use block を、即実行する前にまず schedulable set として扱います。",
      },
    },
    {
      eyebrow: {
        zh: "Step 2",
        en: "Step 2",
        ja: "ステップ 2",
      },
      title: {
        zh: "按并发安全性分批",
        en: "Partition by concurrency safety",
        ja: "concurrency safety で分割する",
      },
      body: {
        zh: "先决定哪些工具能并发，哪些必须串行，这一步本质上是在保护共享状态。",
        en: "Decide which tools can run together and which must stay serial. This step protects shared state.",
        ja: "どの tool が同時実行でき、どれが直列であるべきかを先に決めます。これは共有 state を守る工程です。",
      },
    },
    {
      eyebrow: {
        zh: "Step 3",
        en: "Step 3",
        ja: "ステップ 3",
      },
      title: {
        zh: "稳定回写结果",
        en: "Write back in stable order",
        ja: "安定順で回写する",
      },
      body: {
        zh: "并发并不代表回写乱序。更完整的运行时会先排队 progress、结果和 context modifier，再按稳定顺序落地。",
        en: "Concurrency does not imply chaotic write-back. A more complete runtime queues progress, results, and modifiers before landing them in stable order.",
        ja: "並列実行は乱れた回写を意味しません。より整った runtime は progress・result・modifier をいったん整列させてから安定順で反映します。",
      },
    },
  ],
  rules: [
    {
      title: {
        zh: "progress 可以先走",
        en: "progress can surface early",
        ja: "progress は先に出してよい",
      },
      body: {
        zh: "慢工具不必一直沉默，先让上层知道它在做什么。",
        en: "Slow tools do not need to stay silent. Let the upper layer see what they are doing.",
        ja: "遅い tool を黙らせ続ける必要はありません。上位層へ今何をしているかを先に知らせます。",
      },
    },
    {
      title: {
        zh: "modifier 先排队再合并",
        en: "queue modifiers before merge",
        ja: "modifier は queue してから merge する",
      },
      body: {
        zh: "共享 context 的修改最好不要按完成先后直接落地。",
        en: "Shared context changes should not land directly in completion order.",
        ja: "共有 context 変更を完了順でそのまま反映しない方が安全です。",
      },
    },
  ],
  records: [
    {
      name: "ToolExecutionBatch",
      note: {
        zh: "表示一批可一起调度的 tool block。",
        en: "Represents one schedulable batch of tool blocks.",
        ja: "一緒に調度できる tool block の batch。",
      },
    },
    {
      name: "TrackedTool",
      note: {
        zh: "跟踪每个工具的排队、执行、完成、产出进度。",
        en: "Tracks queued, executing, completed, and yielded progress states per tool.",
        ja: "各 tool の queued・executing・completed・yielded progress を追跡します。",
      },
    },
    {
      name: "queued_context_modifiers",
      note: {
        zh: "把并发工具的共享状态修改先存起来，再稳定合并。",
        en: "Stores shared-state mutations until they can be merged in stable order.",
        ja: "並列 tool の共有 state 変更を一時保存し、後で安定順に merge します。",
      },
    },
  ],
} as const;

const QUERY_TRANSITION_TEXT = {
  label: {
    zh: "Query 转移模型",
    en: "Query Transition Model",
    ja: "クエリ継続モデル",
  },
  title: {
    zh: "不要把所有继续都看成同一个 `continue`",
    en: "Do not treat every continuation as the same `continue`",
    ja: "すべての継続を同じ `continue` と見なさない",
  },
  note: {
    zh: "只要系统开始长出恢复、压缩和自治行为，就必须知道：这一轮为什么结束、下一轮为什么存在、继续之前改了哪块状态。只有这样，这几层才不会搅成一团。",
    en: "Once a system grows recovery, compaction, and autonomy, it must know why this turn ended, why the next turn exists, and what state changed before the jump.",
    ja: "system に recovery・compact・autonomy が入り始めたら、この turn がなぜ終わり、次の turn がなぜ存在し、移行前にどの state を変えたかを知る必要があります。",
  },
  angleLabel: {
    zh: "本章为什么要盯这层",
    en: "Why This Lens Matters Here",
    ja: "この章でこの層を見る理由",
  },
  chainLabel: {
    zh: "转移链",
    en: "Transition Chain",
    ja: "遷移チェーン",
  },
  reasonsLabel: {
    zh: "常见继续原因",
    en: "Common Continuation Reasons",
    ja: "よくある継続理由",
  },
  guardrailLabel: {
    zh: "实现护栏",
    en: "Implementation Guardrails",
    ja: "実装ガードレール",
  },
  chain: [
    {
      title: {
        zh: "当前轮撞到边界",
        en: "The current turn hits a boundary",
        ja: "現在の turn が境界に当たる",
      },
      body: {
        zh: "可能是 tool 结束、输出截断、compact 触发、transport 出错，或者外部 hook 改写了结束条件。",
        en: "A tool may have finished, output may be truncated, compaction may have fired, transport may have failed, or a hook may have changed the ending condition.",
        ja: "tool 完了、出力切断、compact 発火、transport error、hook による終了条件変更などが起こります。",
      },
    },
    {
      title: {
        zh: "写入 reason + state patch",
        en: "Write the reason and the state patch",
        ja: "reason と state patch を書く",
      },
      body: {
        zh: "在真正继续前，把 transition、重试计数、compact 标志或补充消息写进状态。",
        en: "Before continuing, record the transition, retry counters, compaction flags, or supplemental messages in state.",
        ja: "続行前に transition、retry count、compact flag、補助 message などを state へ書き込みます。",
      },
    },
    {
      title: {
        zh: "下一轮带着原因进入",
        en: "The next turn enters with a reason",
        ja: "次の turn は理由を持って入る",
      },
      body: {
        zh: "下一轮不再是盲目出现，它知道自己是正常回流、恢复重试还是预算延续。",
        en: "The next turn is no longer blind. It knows whether it exists because of normal write-back, recovery, or budgeted continuation.",
        ja: "次の turn は盲目的に現れるのではなく、通常回流・recovery retry・budget continuation のどれなのかを知っています。",
      },
    },
  ],
  reasons: [
    {
      name: "tool_result_continuation",
      note: {
        zh: "工具完成后的正常回流。",
        en: "Normal write-back after a tool finishes.",
        ja: "tool 完了後の通常回流。",
      },
    },
    {
      name: "max_tokens_recovery",
      note: {
        zh: "输出被截断后的续写恢复。",
        en: "Recovery after truncated model output.",
        ja: "出力切断後の継続回復。",
      },
    },
    {
      name: "compact_retry",
      note: {
        zh: "上下文重排后的重试。",
        en: "Retry after context reshaping.",
        ja: "context 再構成後の retry。",
      },
    },
    {
      name: "transport_retry",
      note: {
        zh: "基础设施抖动后的再试一次。",
        en: "Retry after infrastructure failure.",
        ja: "基盤失敗後の再試行。",
      },
    },
  ],
  guardrails: [
    {
      title: {
        zh: "每个 continue site 都写 reason",
        en: "every continue site writes a reason",
        ja: "すべての continue site が reason を書く",
      },
    },
    {
      title: {
        zh: "继续前先写 state patch",
        en: "patch state before continuing",
        ja: "続行前に state patch を書く",
      },
    },
    {
      title: {
        zh: "重试和续写都要有 budget",
        en: "retries and continuations need budgets",
        ja: "retry と continuation には budget が必要",
      },
    },
  ],
} as const;

const TASK_RUNTIME_TEXT = {
  label: {
    zh: "任务运行时边界",
    en: "Task Runtime Boundaries",
    ja: "タスク実行の境界",
  },
  title: {
    zh: "把目标任务、执行槽位、调度触发拆成三层",
    en: "Separate goal tasks, execution slots, and schedule triggers",
    ja: "goal task・execution slot・schedule trigger を三層に分ける",
  },
  note: {
    zh: "从 `s12` 开始，读者最容易把所有“任务”混成一个词。更完整的系统会把 durable goal、live runtime slot 和 optional schedule trigger 分层管理。",
    en: "From `s12` onward, readers start collapsing every kind of work into the word 'task'. More complete systems keep durable goals, live runtime slots, and optional schedule triggers on separate layers.",
    ja: "`s12` 以降は、あらゆる仕事を task という一語へ潰しがちです。より構造の整った system は durable goal・live runtime slot・optional schedule trigger を分離して管理します。",
  },
  angleLabel: {
    zh: "本章为什么要盯这层",
    en: "Why This Lens Matters Here",
    ja: "この章でこの層を見る理由",
  },
  layersLabel: {
    zh: "三层对象",
    en: "Three Layers",
    ja: "三層の対象",
  },
  flowLabel: {
    zh: "真实推进关系",
    en: "Actual Progression",
    ja: "実際の進み方",
  },
  recordsLabel: {
    zh: "关键记录",
    en: "Key Records",
    ja: "主要レコード",
  },
  layers: [
    {
      title: {
        zh: "Work-Graph Task",
        en: "Work-Graph Task",
        ja: "ワークグラフ・タスク",
      },
      body: {
        zh: "表示要做什么、谁依赖谁、谁负责。它关心目标和工作关系，不直接代表某个后台进程。",
        en: "Represents what should be done, who depends on whom, and who owns the work. It is goal-oriented, not a live background process.",
        ja: "何をやるか、誰が依存し、誰が owner かを表します。goal 指向であり、live background process そのものではありません。",
      },
    },
    {
      title: {
        zh: "Runtime Slot",
        en: "Runtime Slot",
        ja: "ランタイムスロット",
      },
      body: {
        zh: "表示现在有什么执行单元活着：shell、teammate、monitor、workflow。它关心 status、output 和 notified。",
        en: "Represents the live execution unit: shell, teammate, monitor, or workflow. It cares about status, output, and notification state.",
        ja: "いま生きている execution unit を表します。shell・teammate・monitor・workflow などがここに入り、status・output・notified を持ちます。",
      },
    },
    {
      title: {
        zh: "Schedule Trigger",
        en: "Schedule Trigger",
        ja: "スケジュールトリガー",
      },
      body: {
        zh: "表示什么时候要启动一次工作。它不是任务目标，也不是正在运行的槽位，而是触发规则。",
        en: "Represents when work should start. It is neither the durable goal nor the live execution slot. It is the trigger rule.",
        ja: "いつ仕事を起動するかを表します。durable goal でも live slot でもなく、trigger rule です。",
      },
    },
  ],
  flow: [
    {
      title: {
        zh: "目标先存在",
        en: "The goal exists first",
        ja: "goal が先に存在する",
      },
      body: {
        zh: "任务板先定义工作目标和依赖，不必立刻对应到某个后台执行体。",
        en: "The task board defines goals and dependencies before any specific background execution exists.",
        ja: "task board はまず goal と dependency を定義し、まだ特定の background execution を必要としません。",
      },
    },
    {
      title: {
        zh: "执行时生成 runtime slot",
        en: "Execution creates runtime slots",
        ja: "実行時に runtime slot が生まれる",
      },
      body: {
        zh: "当系统真的开跑一个 shell、worker 或 monitor 时，再生成独立 runtime record。",
        en: "Only when the system actually starts a shell, worker, or monitor does it create a separate runtime record.",
        ja: "shell・worker・monitor を本当に起動した時点で、独立した runtime record を作ります。",
      },
    },
    {
      title: {
        zh: "调度只是触发器",
        en: "Scheduling is only the trigger",
        ja: "schedule は trigger にすぎない",
      },
      body: {
        zh: "cron 负责到点触发，不负责代替任务目标，也不直接等同于执行槽位。",
        en: "Cron decides when to fire. It does not replace the task goal and it is not the execution slot itself.",
        ja: "cron は発火時刻を決める層であり、task goal を置き換えず、execution slot そのものでもありません。",
      },
    },
  ],
  records: [
    {
      name: "TaskRecord",
      note: {
        zh: "durable goal 节点。",
        en: "The durable goal node.",
        ja: "durable goal node。",
      },
    },
    {
      name: "RuntimeTaskState",
      note: {
        zh: "活着的执行槽位记录。",
        en: "The live execution-slot record.",
        ja: "live execution-slot record。",
      },
    },
    {
      name: "ScheduleRecord",
      note: {
        zh: "描述何时触发工作的规则。",
        en: "Describes when work should be triggered.",
        ja: "いつ仕事を発火するかを記述する rule。",
      },
    },
    {
      name: "Notification",
      note: {
        zh: "把 runtime 结果重新带回主线。",
        en: "Brings runtime results back into the mainline.",
        ja: "runtime result を主線へ戻す record。",
      },
    },
  ],
} as const;

const TEAM_BOUNDARY_TEXT = {
  label: {
    zh: "团队边界模型",
    en: "Team Boundary Model",
    ja: "チーム境界モデル",
  },
  title: {
    zh: "把 teammate、协议请求、任务、执行槽位、worktree 车道分开",
    en: "Separate teammates, protocol requests, tasks, runtime slots, and worktree lanes",
    ja: "teammate・protocol request・task・runtime slot・worktree lane を分ける",
  },
  note: {
    zh: "到了 `s15-s18`，最容易让读者打结的不是某个函数，而是这五层对象一起动起来时，到底谁表示身份、谁表示目标、谁表示执行、谁表示目录车道。",
    en: "From `s15` to `s18`, the hardest thing is not one function. It is keeping identity, coordination, goals, execution, and directory lanes distinct while all five move together.",
    ja: "`s15-s18` で難しいのは個別の関数ではなく、identity・coordination・goal・execution・directory lane を同時に分けて保つことです。",
  },
  angleLabel: {
    zh: "本章为什么要盯这层",
    en: "Why This Lens Matters Here",
    ja: "この章でこの層を見る理由",
  },
  layersLabel: {
    zh: "五层对象",
    en: "Five Layers",
    ja: "五層の対象",
  },
  rulesLabel: {
    zh: "读的时候先守住",
    en: "Read With These Guardrails",
    ja: "読むときのガードレール",
  },
  layers: [
    {
      title: {
        zh: "Teammate",
        en: "Teammate",
        ja: "Teammate",
      },
      body: {
        zh: "长期存在、可重复协作的身份层。",
        en: "The persistent identity layer that can collaborate repeatedly.",
        ja: "反復して協調できる persistent identity layer。",
      },
    },
    {
      title: {
        zh: "Protocol Request",
        en: "Protocol Request",
        ja: "Protocol Request",
      },
      body: {
        zh: "团队内部一次可追踪的协调请求，带 `request_id`、kind 和状态。",
        en: "A trackable coordination request inside the team, carrying a `request_id`, kind, and status.",
        ja: "team 内の追跡可能な coordination request。`request_id`・kind・status を持ちます。",
      },
    },
    {
      title: {
        zh: "Task",
        en: "Task",
        ja: "Task",
      },
      body: {
        zh: "表示要做什么的目标层。",
        en: "The goal layer that records what should be done.",
        ja: "何をやるかを表す goal layer。",
      },
    },
    {
      title: {
        zh: "Runtime Slot",
        en: "Runtime Slot",
        ja: "ランタイムスロット",
      },
      body: {
        zh: "表示谁正在执行、执行到什么状态。",
        en: "Represents who is actively executing and what execution state they are in.",
        ja: "誰が実行中で、どの execution state にいるかを表します。",
      },
    },
    {
      title: {
        zh: "Worktree Lane",
        en: "Worktree Lane",
        ja: "Worktree Lane",
      },
      body: {
        zh: "表示在哪个隔离目录里推进工作。",
        en: "Represents the isolated directory lane where execution happens.",
        ja: "どの分離ディレクトリ lane で仕事を進めるかを表します。",
      },
    },
  ],
  rules: [
    {
      title: {
        zh: "身份不是目标",
        en: "identity is not the goal",
        ja: "identity は goal ではない",
      },
      body: {
        zh: "teammate 表示谁长期存在，不表示这件工作本身。",
        en: "A teammate tells you who persists in the system, not what the work item itself is.",
        ja: "teammate は誰が system に長く存在するかを表し、仕事そのものではありません。",
      },
    },
    {
      title: {
        zh: "`request_id` 不等于 `task_id`",
        en: "`request_id` is not `task_id`",
        ja: "`request_id` は `task_id` ではない",
      },
      body: {
        zh: "协议请求记录协调过程，任务记录工作目标，两者都可长期存在但职责不同。",
        en: "Protocol requests record coordination, while tasks record work goals. Both can persist, but they serve different purposes.",
        ja: "protocol request は coordination を記録し、task は work goal を記録します。どちらも残り得ますが役割は別です。",
      },
    },
    {
      title: {
        zh: "worktree 不是另一种任务",
        en: "a worktree is not another kind of task",
        ja: "worktree は別種の task ではない",
      },
      body: {
        zh: "它只负责目录隔离和 closeout，不负责定义目标。",
        en: "It manages directory isolation and closeout, not the work goal itself.",
        ja: "directory isolation と closeout を管理する層であり、goal を定義する層ではありません。",
      },
    },
  ],
} as const;

const CAPABILITY_LAYER_TEXT = {
  label: {
    zh: "外部能力层地图",
    en: "External Capability Layers",
    ja: "外部 capability レイヤー",
  },
  title: {
    zh: "把 MCP 看成能力层，而不只是外部工具目录",
    en: "See MCP as layered capability, not just an external tool catalog",
    ja: "MCP を外部 tool catalog ではなく layered capability として見る",
  },
  note: {
    zh: "如果只把 MCP 当作远程工具列表，读者会在 resources、prompts、elicitation、auth 这些点上突然失去主线。更稳的办法是先守住 tools-first，再补整张能力层地图。",
    en: "If MCP is taught only as a remote tool list, readers lose the thread when resources, prompts, elicitation, and auth appear. The steadier approach is tools-first in the mainline, then the full capability map.",
    ja: "MCP を remote tool list だけで教えると、resources・prompts・elicitation・auth が出た瞬間に主線を失います。tools-first を守りつつ capability map を補う方が安定です。",
  },
  angleLabel: {
    zh: "本章为什么要盯这层",
    en: "Why This Lens Matters Here",
    ja: "この章でこの層を見る理由",
  },
  layersLabel: {
    zh: "六层能力面",
    en: "Six Capability Layers",
    ja: "六層の capability",
  },
  teachLabel: {
    zh: "教学顺序",
    en: "Teaching Order",
    ja: "教える順序",
  },
  layers: [
    { title: { zh: "Config", en: "Config", ja: "設定" }, body: { zh: "server 配置来自哪里、长什么样。", en: "Where server configuration comes from and what it looks like.", ja: "server config がどこから来て、どんな形か。" } },
    { title: { zh: "Transport", en: "Transport", ja: "接続方式" }, body: { zh: "stdio / http / sse / ws 这些连接通道。", en: "The connection channel such as stdio, HTTP, SSE, or WebSocket.", ja: "stdio / HTTP / SSE / WS などの接続通路。" } },
    { title: { zh: "Connection State", en: "Connection State", ja: "接続状態" }, body: { zh: "connected / pending / needs-auth / failed。", en: "States such as connected, pending, needs-auth, and failed.", ja: "connected / pending / needs-auth / failed などの状態。" } },
    { title: { zh: "Capabilities", en: "Capabilities", ja: "能力層" }, body: { zh: "tools 只是其中之一，旁边还有 resources、prompts、elicitation。", en: "Tools are only one member of the layer beside resources, prompts, and elicitation.", ja: "tools は一員にすぎず、resources・prompts・elicitation も並びます。" } },
    { title: { zh: "Auth", en: "Auth", ja: "認証" }, body: { zh: "决定 server 能不能真正进入 connected 可用态。", en: "Determines whether a server can actually enter the usable connected state.", ja: "server が実際に使える connected 状態へ入れるかを決めます。" } },
    { title: { zh: "Router Integration", en: "Router Integration", ja: "ルーター統合" }, body: { zh: "最后怎么回到 tool router、permission 和 notification。", en: "How the result finally routes back into tool routing, permissions, and notifications.", ja: "最後に tool router・permission・notification へどう戻るか。" } },
  ],
  teach: [
    {
      title: { zh: "先讲 tools-first", en: "Teach tools-first first", ja: "まず tools-first を教える" },
      body: { zh: "先让读者能把外部工具接回来，不要一开始就被平台细节拖走。", en: "Let readers wire external tools back into the agent before platform details take over.", ja: "最初から platform detail に引き込まず、まず外部 tool を agent へ戻せるようにします。" },
    },
    {
      title: { zh: "再补 capability map", en: "Then add the capability map", ja: "次に capability map を足す" },
      body: { zh: "告诉读者 tools 只是切面之一，平台还有别的面。", en: "Show readers that tools are only one slice of a broader platform.", ja: "tools が broader platform の一断面にすぎないことを見せます。" },
    },
    {
      title: { zh: "最后再展开 auth 等重层", en: "Expand auth and heavier layers last", ja: "auth など重い層は最後に展開する" },
      body: { zh: "只有当前两层站稳后，再深入认证和更复杂状态机。", en: "Only after the first two layers are stable should auth and heavier state machines become the focus.", ja: "最初の二層が安定してから、auth や重い state machine を扱います。" },
    },
  ],
} as const;

function pick(locale: string, value: LocaleText): string {
  if (locale === "zh") return value.zh;
  if (locale === "ja") return value.ja;
  return value.en;
}

function ToolRuntimeLens({
  locale,
  angle,
}: {
  locale: string;
  angle: string;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(160deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(160deg,rgba(24,24,27,0.96),rgba(10,10,10,0.92))]">
      <div className="border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, TOOL_RUNTIME_TEXT.label)}
        </p>
        <h3 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, TOOL_RUNTIME_TEXT.title)}
        </h3>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, TOOL_RUNTIME_TEXT.note)}
        </p>
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        <div className="rounded-2xl border border-sky-200/70 bg-sky-50/80 p-4 dark:border-sky-900/50 dark:bg-sky-950/20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-sky-700/80 dark:text-sky-300/80">
            {pick(locale, TOOL_RUNTIME_TEXT.angleLabel)}
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
            {angle}
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              {TOOL_RUNTIME_TEXT.stages.map((stage) => (
                <div
                  key={stage.title.en}
                  className="rounded-2xl border border-zinc-200/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-400">
                    {pick(locale, stage.eyebrow)}
                  </p>
                  <h4 className="mt-2 text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                    {pick(locale, stage.title)}
                  </h4>
                  <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, stage.body)}
                  </p>
                </div>
              ))}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/20">
                <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                  {pick(locale, TOOL_RUNTIME_TEXT.safeLane.title)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                  {pick(locale, TOOL_RUNTIME_TEXT.safeLane.body)}
                </p>
              </div>
              <div className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                  {pick(locale, TOOL_RUNTIME_TEXT.exclusiveLane.title)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                  {pick(locale, TOOL_RUNTIME_TEXT.exclusiveLane.body)}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, TOOL_RUNTIME_TEXT.rulesLabel)}
              </p>
              <div className="mt-3 space-y-3">
                {TOOL_RUNTIME_TEXT.rules.map((rule) => (
                  <div
                    key={rule.title.en}
                    className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                  >
                    <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                      {pick(locale, rule.title)}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {pick(locale, rule.body)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, TOOL_RUNTIME_TEXT.recordsLabel)}
              </p>
              <div className="mt-3 space-y-3">
                {TOOL_RUNTIME_TEXT.records.map((record) => (
                  <div
                    key={record.name}
                    className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                  >
                    <code className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {record.name}
                    </code>
                    <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {pick(locale, record.note)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function QueryTransitionLens({
  locale,
  angle,
}: {
  locale: string;
  angle: string;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(160deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(160deg,rgba(24,24,27,0.96),rgba(10,10,10,0.92))]">
      <div className="border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, QUERY_TRANSITION_TEXT.label)}
        </p>
        <h3 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, QUERY_TRANSITION_TEXT.title)}
        </h3>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, QUERY_TRANSITION_TEXT.note)}
        </p>
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        <div className="rounded-2xl border border-rose-200/70 bg-rose-50/80 p-4 dark:border-rose-900/50 dark:bg-rose-950/20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-rose-700/80 dark:text-rose-300/80">
            {pick(locale, QUERY_TRANSITION_TEXT.angleLabel)}
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
            {angle}
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, QUERY_TRANSITION_TEXT.chainLabel)}
            </p>
            <div className="mt-3 space-y-3">
              {QUERY_TRANSITION_TEXT.chain.map((item, index) => (
                <div key={item.title.en}>
                  <div className="rounded-2xl border border-white/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70">
                    <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                      {pick(locale, item.title)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {pick(locale, item.body)}
                    </p>
                  </div>
                  {index < QUERY_TRANSITION_TEXT.chain.length - 1 && (
                    <div className="flex justify-center py-2 text-zinc-300 dark:text-zinc-600">
                      <div className="h-6 w-px bg-current" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, QUERY_TRANSITION_TEXT.reasonsLabel)}
              </p>
              <div className="mt-3 space-y-3">
                {QUERY_TRANSITION_TEXT.reasons.map((reason) => (
                  <div
                    key={reason.name}
                    className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                  >
                    <code className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {reason.name}
                    </code>
                    <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {pick(locale, reason.note)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, QUERY_TRANSITION_TEXT.guardrailLabel)}
              </p>
              <div className="mt-3 grid gap-3">
                {QUERY_TRANSITION_TEXT.guardrails.map((item) => (
                  <div
                    key={item.title.en}
                    className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                  >
                    <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                      {pick(locale, item.title)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function TaskRuntimeLens({
  locale,
  angle,
}: {
  locale: string;
  angle: string;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(160deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(160deg,rgba(24,24,27,0.96),rgba(10,10,10,0.92))]">
      <div className="border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, TASK_RUNTIME_TEXT.label)}
        </p>
        <h3 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, TASK_RUNTIME_TEXT.title)}
        </h3>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, TASK_RUNTIME_TEXT.note)}
        </p>
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        <div className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-700/80 dark:text-amber-300/80">
            {pick(locale, TASK_RUNTIME_TEXT.angleLabel)}
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
            {angle}
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, TASK_RUNTIME_TEXT.layersLabel)}
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {TASK_RUNTIME_TEXT.layers.map((layer) => (
                  <div
                    key={layer.title.en}
                    className="rounded-2xl border border-white/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                  >
                    <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                      {pick(locale, layer.title)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {pick(locale, layer.body)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
                {pick(locale, TASK_RUNTIME_TEXT.flowLabel)}
              </p>
              <div className="mt-3 space-y-3">
                {TASK_RUNTIME_TEXT.flow.map((item, index) => (
                  <div key={item.title.en}>
                    <div className="rounded-2xl border border-white/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70">
                      <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                        {pick(locale, item.title)}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                        {pick(locale, item.body)}
                      </p>
                    </div>
                    {index < TASK_RUNTIME_TEXT.flow.length - 1 && (
                      <div className="flex justify-center py-2 text-zinc-300 dark:text-zinc-600">
                        <div className="h-6 w-px bg-current" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, TASK_RUNTIME_TEXT.recordsLabel)}
            </p>
            <div className="mt-3 space-y-3">
              {TASK_RUNTIME_TEXT.records.map((record) => (
                <div
                  key={record.name}
                  className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <code className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    {record.name}
                  </code>
                  <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, record.note)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function TeamBoundaryLens({
  locale,
  angle,
}: {
  locale: string;
  angle: string;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(160deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(160deg,rgba(24,24,27,0.96),rgba(10,10,10,0.92))]">
      <div className="border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, TEAM_BOUNDARY_TEXT.label)}
        </p>
        <h3 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, TEAM_BOUNDARY_TEXT.title)}
        </h3>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, TEAM_BOUNDARY_TEXT.note)}
        </p>
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        <div className="rounded-2xl border border-red-200/70 bg-red-50/80 p-4 dark:border-red-900/50 dark:bg-red-950/20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-red-700/80 dark:text-red-300/80">
            {pick(locale, TEAM_BOUNDARY_TEXT.angleLabel)}
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
            {angle}
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, TEAM_BOUNDARY_TEXT.layersLabel)}
            </p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {TEAM_BOUNDARY_TEXT.layers.map((layer) => (
                <div
                  key={layer.title.en}
                  className="rounded-2xl border border-white/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                    {pick(locale, layer.title)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, layer.body)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, TEAM_BOUNDARY_TEXT.rulesLabel)}
            </p>
            <div className="mt-3 space-y-3">
              {TEAM_BOUNDARY_TEXT.rules.map((rule) => (
                <div
                  key={rule.title.en}
                  className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                    {pick(locale, rule.title)}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, rule.body)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function CapabilityLayerLens({
  locale,
  angle,
}: {
  locale: string;
  angle: string;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(160deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(160deg,rgba(24,24,27,0.96),rgba(10,10,10,0.92))]">
      <div className="border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, CAPABILITY_LAYER_TEXT.label)}
        </p>
        <h3 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, CAPABILITY_LAYER_TEXT.title)}
        </h3>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, CAPABILITY_LAYER_TEXT.note)}
        </p>
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        <div className="rounded-2xl border border-slate-300/70 bg-slate-100/80 p-4 dark:border-slate-700/60 dark:bg-slate-900/40">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-700/80 dark:text-slate-300/80">
            {pick(locale, CAPABILITY_LAYER_TEXT.angleLabel)}
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
            {angle}
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, CAPABILITY_LAYER_TEXT.layersLabel)}
            </p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {CAPABILITY_LAYER_TEXT.layers.map((layer) => (
                <div
                  key={layer.title.en}
                  className="rounded-2xl border border-white/80 bg-white/90 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                    {pick(locale, layer.title)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, layer.body)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
              {pick(locale, CAPABILITY_LAYER_TEXT.teachLabel)}
            </p>
            <div className="mt-3 space-y-3">
              {CAPABILITY_LAYER_TEXT.teach.map((step) => (
                <div
                  key={step.title.en}
                  className="rounded-2xl border border-white/80 bg-white/90 p-3 dark:border-zinc-800/80 dark:bg-zinc-950/70"
                >
                  <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                    {pick(locale, step.title)}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {pick(locale, step.body)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

export function VersionMechanismLenses({
  version,
  locale,
}: VersionMechanismLensesProps) {
  const toolAngle = TOOL_RUNTIME_VERSION_ANGLE[version as VersionId];
  const queryAngle = QUERY_TRANSITION_VERSION_ANGLE[version as VersionId];
  const taskAngle = TASK_RUNTIME_VERSION_ANGLE[version as VersionId];
  const teamAngle = TEAM_BOUNDARY_VERSION_ANGLE[version as VersionId];
  const capabilityAngle = CAPABILITY_LAYER_VERSION_ANGLE[version as VersionId];
  const lensCount =
    Number(Boolean(toolAngle)) +
    Number(Boolean(queryAngle)) +
    Number(Boolean(taskAngle)) +
    Number(Boolean(teamAngle)) +
    Number(Boolean(capabilityAngle));

  if (!lensCount) return null;

  return (
    <section className="space-y-5">
      <div className="max-w-3xl">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pick(locale, SECTION_TEXT.label)}
        </p>
        <h2 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {pick(locale, SECTION_TEXT.title)}
        </h2>
        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {pick(locale, SECTION_TEXT.body)}
        </p>
      </div>

      <div className={`grid gap-6 ${lensCount > 1 ? "2xl:grid-cols-2" : ""}`}>
        {toolAngle && <ToolRuntimeLens locale={locale} angle={pick(locale, toolAngle)} />}
        {queryAngle && <QueryTransitionLens locale={locale} angle={pick(locale, queryAngle)} />}
        {taskAngle && <TaskRuntimeLens locale={locale} angle={pick(locale, taskAngle)} />}
        {teamAngle && <TeamBoundaryLens locale={locale} angle={pick(locale, teamAngle)} />}
        {capabilityAngle && <CapabilityLayerLens locale={locale} angle={pick(locale, capabilityAngle)} />}
      </div>
    </section>
  );
}
