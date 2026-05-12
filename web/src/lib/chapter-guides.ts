import type { VersionId } from "@/lib/constants";

type SupportedLocale = "zh" | "en" | "ja";

export interface ChapterGuide {
  focus: string;
  confusion: string;
  goal: string;
}

export const CHAPTER_GUIDES: Record<VersionId, Record<SupportedLocale, ChapterGuide>> = {
  s01: {
    zh: {
      focus: "先盯住 `messages`、`tool_use` 和 `tool_result` 如何闭环回流。",
      confusion: "不要把“模型会思考”和“系统能行动”混成一回事，真正让它能行动的是 loop。",
      goal: "手写一个最小但真实可运行的 agent loop。",
    },
    en: {
      focus: "Focus first on how `messages`, `tool_use`, and `tool_result` close the loop.",
      confusion: "Do not confuse model reasoning with system action. The loop is what turns thought into work.",
      goal: "Be able to write a minimal but real agent loop by hand.",
    },
    ja: {
      focus: "まず `messages`、`tool_use`、`tool_result` がどう閉ループを作るかを見る。",
      confusion: "モデルが考えられることと、システムが行動できることを混同しない。行動を成立させるのは loop です。",
      goal: "最小でも実際に動く agent loop を自力で書けるようになる。",
    },
  },
  s02: {
    zh: {
      focus: "先盯住 `ToolSpec`、`dispatch map` 和 `tool_result` 的对应关系。",
      confusion: "工具 schema 不是执行函数本身；一个是给模型看的说明，一个是代码里的处理器。",
      goal: "在不改主循环的前提下，自己加一个新工具。",
    },
    en: {
      focus: "Focus on the relationship between `ToolSpec`, the dispatch map, and `tool_result`.",
      confusion: "A tool schema is not the handler itself. One describes the tool to the model; the other executes it.",
      goal: "Add a new tool without changing the main loop.",
    },
    ja: {
      focus: "`ToolSpec`、dispatch map、`tool_result` の対応関係を先に見る。",
      confusion: "schema は実行関数そのものではありません。片方はモデル向けの説明、もう片方は実装側の handler です。",
      goal: "主ループを変えずに新しいツールを追加できるようになる。",
    },
  },
  s03: {
    zh: {
      focus: "先盯住 `TodoItem` / `PlanState` 这类最小计划状态。",
      confusion: "todo 只是当前会话里的步骤提醒，不是后面那种持久化任务图。",
      goal: "让 agent 能把一个大目标拆成可跟踪的小步骤。",
    },
    en: {
      focus: "Focus on the smallest planning state, such as `TodoItem` and `PlanState`.",
      confusion: "A todo here is a session-level reminder, not the later durable task graph.",
      goal: "Make the agent break a large goal into trackable steps.",
    },
    ja: {
      focus: "`TodoItem` や `PlanState` のような最小の計画状態を見る。",
      confusion: "ここでの todo は会話内の手順メモであり、後の永続 task graph とは別物です。",
      goal: "大きな目標を追跡できる小さな手順へ分解できるようにする。",
    },
  },
  s04: {
    zh: {
      focus: "先盯住父 `messages` 和子 `messages` 如何隔离。",
      confusion: "subagent 的关键不是“又开一次模型调用”，而是“给子任务一个干净上下文”。",
      goal: "做出一个一次性委派、返回摘要的子 agent。",
    },
    en: {
      focus: "Focus on how parent `messages` and child `messages` stay isolated.",
      confusion: "The key value of a subagent is not another model call. It is a clean context for the subtask.",
      goal: "Build a one-shot delegated child agent that returns a summary.",
    },
    ja: {
      focus: "親 `messages` と子 `messages` がどう分離されるかを見る。",
      confusion: "subagent の本質はモデル呼び出しを増やすことではなく、子タスクへきれいな文脈を与えることです。",
      goal: "一回限りの委譲を行い、要約を返す子 agent を作れるようになる。",
    },
  },
  s05: {
    zh: {
      focus: "先盯住技能的“发现层”和“加载层”是怎么分开的。",
      confusion: "skill 不是一开始全部塞进 prompt 的大说明书，而是按需加载的知识块。",
      goal: "做出一个低成本发现、高成本按需读取的技能系统。",
    },
    en: {
      focus: "Focus on how skill discovery and skill loading are kept separate.",
      confusion: "A skill is not a giant prompt blob loaded upfront. It is knowledge loaded only when needed.",
      goal: "Build a skill system with cheap discovery and on-demand deep loading.",
    },
    ja: {
      focus: "skill の発見層と読み込み層がどう分かれているかを見る。",
      confusion: "skill は最初から全部 prompt に入れる巨大説明ではなく、必要時だけ読む知識ブロックです。",
      goal: "軽い発見と必要時だけの深い読み込みを持つ skill system を作る。",
    },
  },
  s06: {
    zh: {
      focus: "先盯住 `persisted output`、`micro compact`、`summary compact` 这三层。",
      confusion: "压缩不是为了删历史，而是把细节移出活跃上下文，同时保住主线。",
      goal: "做出一个能长期工作、不被上下文撑爆的最小压缩系统。",
    },
    en: {
      focus: "Focus on the three layers: persisted output, micro compact, and summary compact.",
      confusion: "Compaction is not about deleting history. It is about moving detail out of the active window while keeping continuity.",
      goal: "Build a minimal compaction system that keeps long sessions usable.",
    },
    ja: {
      focus: "persisted output、micro compact、summary compact の3層を見る。",
      confusion: "compact は履歴削除ではなく、細部をアクティブ文脈の外へ移しながら主線を保つことです。",
      goal: "長い作業でも文脈が破綻しない最小 compact system を作る。",
    },
  },
  s07: {
    zh: {
      focus: "先盯住 `PermissionRule`、`PermissionDecision` 和整条 allow / ask / deny 管道。",
      confusion: "权限系统不是单个 if 判断，而是一条在执行前拦截意图的决策链。",
      goal: "让危险动作先经过清晰的权限决策，再决定是否执行。",
    },
    en: {
      focus: "Focus on `PermissionRule`, `PermissionDecision`, and the full allow / ask / deny pipeline.",
      confusion: "A permission system is not one `if` statement. It is a decision chain that intercepts intent before execution.",
      goal: "Put risky actions behind a clear permission pipeline.",
    },
    ja: {
      focus: "`PermissionRule`、`PermissionDecision`、allow / ask / deny の流れを見る。",
      confusion: "permission system は単一の if ではなく、実行前に意図を止める判断パイプラインです。",
      goal: "危険な操作を明確な permission pipeline の後ろに置けるようにする。",
    },
  },
  s08: {
    zh: {
      focus: "先盯住 `HookEvent`、`HookResult` 和固定触发时机。",
      confusion: "hook 不是把逻辑塞回主循环，而是让主循环在固定时机对外发出插口。",
      goal: "不重写主循环，也能在关键时机扩展行为。",
    },
    en: {
      focus: "Focus on `HookEvent`, `HookResult`, and the fixed trigger points.",
      confusion: "A hook is not random logic stuffed back into the loop. It is an extension point exposed at a fixed moment.",
      goal: "Extend behavior at key moments without rewriting the loop.",
    },
    ja: {
      focus: "`HookEvent`、`HookResult`、固定の発火タイミングを見る。",
      confusion: "hook は主ループへ場当たり的にロジックを戻すことではなく、固定時点の拡張口です。",
      goal: "主ループを書き換えずに重要なタイミングへ拡張を差し込めるようにする。",
    },
  },
  s09: {
    zh: {
      focus: "先盯住 `MemoryEntry` 到底保存哪类信息、为什么不是所有上下文都进 memory。",
      confusion: "memory 不是万能笔记本，它只保存跨会话仍然有价值、又不容易重新推导的信息。",
      goal: "做出一个小而准的长期记忆层，而不是把上下文原样倾倒进去。",
    },
    en: {
      focus: "Focus on what belongs in `MemoryEntry`, and why not all context should become memory.",
      confusion: "Memory is not a universal notebook. It only stores knowledge that still matters across sessions and is not cheap to re-derive.",
      goal: "Build a small, precise long-term memory layer instead of dumping raw context into storage.",
    },
    ja: {
      focus: "`MemoryEntry` に何を入れるべきか、なぜ全部の文脈を memory にしないのかを見る。",
      confusion: "memory は万能ノートではなく、会話をまたいで意味があり再導出しにくい情報だけを残します。",
      goal: "文脈を丸ごと捨て込まない、小さく正確な長期記憶層を作る。",
    },
  },
  s10: {
    zh: {
      focus: "先盯住 `PromptParts` 和输入组装顺序，而不是只盯一段大 prompt 字符串。",
      confusion: "模型真正看到的是一条输入管道，不是单个神秘 system prompt 大文本。",
      goal: "把系统规则、工具说明、动态上下文拆成可管理的输入片段。",
    },
    en: {
      focus: "Focus on `PromptParts` and assembly order rather than one giant prompt string.",
      confusion: "The model really sees an input pipeline, not one magical system prompt blob.",
      goal: "Split system rules, tool descriptions, and dynamic context into manageable input parts.",
    },
    ja: {
      focus: "`PromptParts` と組み立て順を見る。巨大な prompt 文字列だけを見ない。",
      confusion: "モデルが実際に見るのは入力パイプラインであり、魔法の system prompt 1本ではありません。",
      goal: "ルール、ツール説明、動的文脈を管理しやすい入力片へ分解する。",
    },
  },
  s11: {
    zh: {
      focus: "先盯住 `RecoveryState` 和 `TransitionReason`，搞清“为什么继续”。",
      confusion: "错误恢复不只是 try/except，而是系统知道自己该重试、压缩后重来，还是结束。",
      goal: "让 agent 在可恢复错误后还能有条理地继续前进。",
    },
    en: {
      focus: "Focus on `RecoveryState` and `TransitionReason`, especially why the system is continuing.",
      confusion: "Recovery is not just `try/except`. The system must know whether to retry, compact and retry, or stop.",
      goal: "Make the agent continue coherently after recoverable failures.",
    },
    ja: {
      focus: "`RecoveryState` と `TransitionReason`、特に「なぜ続行するのか」を見る。",
      confusion: "error recovery は単なる try/except ではなく、再試行・compact 後再試行・終了を区別することです。",
      goal: "回復可能な失敗の後でも、agent が筋道立てて進めるようにする。",
    },
  },
  s12: {
    zh: {
      focus: "先盯住 `TaskRecord`、`blockedBy`、`blocks` 这几项关系字段。",
      confusion: "task 不再是会话里的步骤提醒，而是一张持久化工作图上的节点。",
      goal: "做出一个会解锁后续任务的最小任务系统。",
    },
    en: {
      focus: "Focus on `TaskRecord`, `blockedBy`, and `blocks`.",
      confusion: "A task here is no longer a session reminder. It is a durable node in a work graph.",
      goal: "Build a minimal task system that can unlock downstream work.",
    },
    ja: {
      focus: "`TaskRecord`、`blockedBy`、`blocks` の関係を見る。",
      confusion: "ここでの task は会話内メモではなく、永続 work graph のノードです。",
      goal: "後続タスクを解放できる最小 task system を作る。",
    },
  },
  s13: {
    zh: {
      focus: "先盯住 `RuntimeTaskState` 和 `Notification` 的分工。",
      confusion: "后台任务不是任务板节点，而是当前正在跑的一条执行槽位。",
      goal: "让慢命令后台运行，并在下一轮把结果带回模型。",
    },
    en: {
      focus: "Focus on the split between `RuntimeTaskState` and `Notification`.",
      confusion: "A background task is not a task-board node. It is a running execution slot.",
      goal: "Run slow work in the background and bring the result back on a later turn.",
    },
    ja: {
      focus: "`RuntimeTaskState` と `Notification` が何を分担しているかを見る。",
      confusion: "バックグラウンドタスクはタスクボード上のノードではなく、いま走っている実行スロットです。",
      goal: "遅い処理をバックグラウンドへ逃がし、次のターンで結果を主ループへ戻せるようにする。",
    },
  },
  s14: {
    zh: {
      focus: "先盯住 `ScheduleRecord`、触发条件和实际执行任务之间的关系。",
      confusion: "cron 不是任务本身，它只是“何时启动一份工作”的规则。",
      goal: "让系统在未来某个时间自动触发工作，而不是只能等当前用户发话。",
    },
    en: {
      focus: "Focus on the relationship between `ScheduleRecord`, trigger conditions, and the work that is actually launched.",
      confusion: "Cron is not the task itself. It is a rule about when work should start.",
      goal: "Trigger work at future times instead of waiting for the current user turn.",
    },
    ja: {
      focus: "`ScheduleRecord`、発火条件、実際に起動される仕事の関係を見る。",
      confusion: "cron は task そのものではなく、いつ仕事を始めるかのルールです。",
      goal: "現在のユーザー発話だけでなく、将来時刻で自動的に仕事を起動できるようにする。",
    },
  },
  s15: {
    zh: {
      focus: "先盯住 `TeamMember`、`MessageEnvelope` 和独立 inbox。",
      confusion: "teammate 不是换了名字的 subagent，关键区别在“是否长期存在、能反复接活”。",
      goal: "做出一个长期存在、能通过邮箱协作的多 agent 团队雏形。",
    },
    en: {
      focus: "Focus on `TeamMember`, `MessageEnvelope`, and independent inboxes.",
      confusion: "A teammate is not a renamed subagent. The difference is long-lived identity and repeatable responsibility.",
      goal: "Build the first version of a long-lived multi-agent team that collaborates through mailboxes.",
    },
    ja: {
      focus: "`TeamMember`、`MessageEnvelope`、独立 inbox を見る。",
      confusion: "teammate は名前を変えた subagent ではなく、長寿命で繰り返し責務を持つ存在です。",
      goal: "メールボックス経由で協力する長寿命マルチエージェントチームの雛形を作る。",
    },
  },
  s16: {
    zh: {
      focus: "先盯住 `ProtocolEnvelope`、`request_id` 和 `RequestRecord`。",
      confusion: "协议消息不是普通聊天消息，它必须能被系统追踪和更新状态。",
      goal: "让团队协作从自由聊天升级成可批准、可拒绝、可跟踪的流程。",
    },
    en: {
      focus: "Focus on `ProtocolEnvelope`, `request_id`, and `RequestRecord`.",
      confusion: "A protocol message is not ordinary chat. The system must be able to track it and update its state.",
      goal: "Turn team coordination from free-form chat into an approvable, rejectable, trackable flow.",
    },
    ja: {
      focus: "`ProtocolEnvelope`、`request_id`、`RequestRecord` を見る。",
      confusion: "protocol message は普通の会話ではなく、システムが追跡して状態更新できる必要があります。",
      goal: "チーム協調を自由会話から、承認・拒否・追跡可能なフローへ上げる。",
    },
  },
  s17: {
    zh: {
      focus: "先盯住 idle 恢复顺序、角色化 claim policy、claim event 和身份重注入这四件事。",
      confusion: "自治的关键不是“它会不会自己想”，而是系统有没有定义清楚：空闲时先看谁、能认领什么、恢复时补回哪些上下文。",
      goal: "让长期队友在不靠持续点名的情况下，也能按规则自己接住下一份工作。",
    },
    en: {
      focus: "Focus on idle resume order, role-aware claim policy, claim events, and identity re-injection.",
      confusion: "Autonomy is not the agent 'thinking on its own'. It is a defined rule for what an idle worker checks, what it may claim, and how it resumes safely.",
      goal: "Let a long-lived teammate pick up the next piece of work without constant manual delegation.",
    },
    ja: {
      focus: "特定製品らしさより、idle 復帰順序・役割付き claim policy・claim event・identity 再注入を見る。",
      confusion: "自律性の核心は魔法の知能ではなく、空いた worker が何を先に確認し、何を claim でき、どう安全に再開するかの規則です。",
      goal: "継続的に指名されなくても、長寿命 teammate が次の仕事を拾えるようにする。",
    },
  },
  s18: {
    zh: {
      focus: "先盯住 `worktree_state`、`last_worktree`、`closeout`，再看 `worktree_enter` 和统一 closeout。",
      confusion: "worktree 不是任务目标，也不是后台任务；它只是任务的独立执行车道，而且车道状态和任务状态不是一回事。",
      goal: "让多个执行者并行改代码时，任务目标、执行目录和收尾动作都能被显式记录。",
    },
    en: {
      focus: "Focus on `worktree_state`, `last_worktree`, `closeout`, then on explicit `worktree_enter` and unified closeout.",
      confusion: "A worktree is neither the task goal nor the runtime task. It is the isolated execution lane, and lane state is not the same as task state.",
      goal: "Make task goals, execution directories, and closeout decisions explicit when multiple workers edit in parallel.",
    },
    ja: {
      focus: "`worktree_state`、`last_worktree`、`closeout` を先に見て、その後 `worktree_enter` と統一 closeout を見る。",
      confusion: "worktree は task 目標でも runtime task でもなく、独立した実行レーンです。レーン状態と task 状態は別物です。",
      goal: "複数 worker が並列でコードを触るとき、task 目標・実行ディレクトリ・収束動作を明示的に記録できるようにする。",
    },
  },
  s19: {
    zh: {
      focus: "先盯住外部能力如何重新接回统一 router，而不是先掉进 transport 或认证细节。",
      confusion: "MCP 不只是外部工具目录，但主线入口仍然应该先从 tools-first 去理解。",
      goal: "把外部能力接进主系统，同时保持权限、路由和结果回流的一致性。",
    },
    en: {
      focus: "Focus on how external capabilities rejoin the same router before diving into transport or auth detail.",
      confusion: "MCP is more than an external tool catalog, but the cleanest mainline still starts with tools first.",
      goal: "Connect external capabilities to the main system while keeping routing, permissions, and result flow consistent.",
    },
    ja: {
      focus: "transport や auth の前に、外部 capability が同じ router へどう戻るかを見る。",
      confusion: "MCP は単なる外部 tool 一覧ではないが、主線理解の入口は tools-first のままでよいです。",
      goal: "外部 capability を主システムへ接続しつつ、routing・permission・結果回流の一貫性を保つ。",
    },
  },
};

export function getChapterGuide(version: string, locale: string): ChapterGuide | null {
  const versionGuide = CHAPTER_GUIDES[version as VersionId];
  if (!versionGuide) return null;
  if (locale === "zh" || locale === "en" || locale === "ja") {
    return versionGuide[locale];
  }
  return versionGuide.en;
}
