"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations, useLocale } from "@/lib/i18n";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  isGenericAnnotationVersion,
  resolveLegacySessionAssetVersion,
} from "@/lib/session-assets";

import s01Annotations from "@/data/annotations/s01.json";
import s02Annotations from "@/data/annotations/s02.json";
import s03Annotations from "@/data/annotations/s03.json";
import s04Annotations from "@/data/annotations/s04.json";
import s05Annotations from "@/data/annotations/s05.json";
import s06Annotations from "@/data/annotations/s06.json";
import s07Annotations from "@/data/annotations/s07.json";
import s08Annotations from "@/data/annotations/s08.json";
import s09Annotations from "@/data/annotations/s09.json";
import s10Annotations from "@/data/annotations/s10.json";
import s11Annotations from "@/data/annotations/s11.json";
import s12Annotations from "@/data/annotations/s12.json";

interface DecisionLocaleCopy {
  title?: string;
  description?: string;
  alternatives?: string;
}

interface Decision {
  id: string;
  title: string;
  description: string;
  alternatives: string;
  zh?: DecisionLocaleCopy;
  ja?: DecisionLocaleCopy;
}

interface AnnotationFile {
  version: string;
  decisions: Decision[];
}

const ANNOTATIONS: Record<string, AnnotationFile> = {
  s01: s01Annotations as AnnotationFile,
  s02: s02Annotations as AnnotationFile,
  s03: s03Annotations as AnnotationFile,
  s04: s04Annotations as AnnotationFile,
  s05: s05Annotations as AnnotationFile,
  s06: s06Annotations as AnnotationFile,
  s07: s07Annotations as AnnotationFile,
  s08: s08Annotations as AnnotationFile,
  s09: s09Annotations as AnnotationFile,
  s10: s10Annotations as AnnotationFile,
  s11: s11Annotations as AnnotationFile,
  s12: s12Annotations as AnnotationFile,
};

const GENERIC_ANNOTATIONS: Record<string, AnnotationFile> = {
  s07: {
    version: "s07",
    decisions: [
      {
        id: "permission-before-execution",
        title: "Permission Is a Gate Before Execution",
        description:
          "The model should not call tools directly as if intent were already trusted execution. Normalize the requested action first, then run it through a shared policy gate that returns allow, deny, or ask. This keeps safety rules consistent across every tool.",
        alternatives:
          "Tool-local safety checks are simpler at first, but they scatter policy into every handler and make behavior inconsistent. A single permission plane adds one more layer, but it is the only place where global execution policy can stay coherent.",
        zh: {
          title: "权限必须是执行前闸门",
          description:
            "模型不应该把 tool call 直接当成可信执行。先把请求规范化成统一意图，再送进共享权限层，返回 allow / deny / ask。这样所有工具都遵循同一套安全语义。",
          alternatives:
            "把安全判断散落到每个工具里实现起来更快，但策略会碎片化。独立权限层虽然多一层，却能让全局执行规则保持一致。",
        },
        ja: {
          title: "権限は実行前のゲートでなければならない",
          description:
            "model は tool call をそのまま信頼済みの実行として扱ってはいけません。まず要求を統一された intent に正規化し、共有 permission layer に通して allow / deny / ask を返します。これで全 tool が同じ安全意味論に従います。",
          alternatives:
            "安全判定を各 tool に分散すると最初は速く作れますが、policy がばらけます。独立した permission layer は一段増えますが、全体の実行方針を一貫して保てます。",
        },
      },
      {
        id: "structured-permission-result",
        title: "Permission Results Must Be Structured and Visible",
        description:
          "A deny or ask outcome is not an implementation detail. The agent must append that result back into the loop so the model can re-plan from it. Otherwise the system silently blocks execution and the model loses the reason why.",
        alternatives:
          "Throwing an exception or returning a plain string is easy, but it hides the decision semantics. A structured permission result makes the next model step explainable and recoverable.",
        zh: {
          title: "权限结果必须结构化且可见",
          description:
            "deny 或 ask 不是内部细节。它们必须回写到主循环，让模型知道为什么没执行、接下来该怎么重规划。否则系统只是静默阻止执行，模型却看不到原因。",
          alternatives:
            "直接抛异常或回一段普通字符串最省事，但会把决策语义藏起来。结构化权限结果能让后续一步更可解释、更可恢复。",
        },
        ja: {
          title: "権限結果は構造化され、見える形で戻るべきだ",
          description:
            "deny や ask は内部実装の細部ではありません。main loop へ書き戻し、model が「なぜ実行されなかったか」「次にどう再計画するか」を見えるようにする必要があります。そうしないと system は黙って止め、model だけが理由を失います。",
          alternatives:
            "例外や単なる文字列で返す方が楽ですが、判断の意味が隠れます。構造化された permission result の方が、次の一手を説明可能で回復可能にします。",
        },
      },
    ],
  },
  s08: {
    version: "s08",
    decisions: [
      {
        id: "hooks-observe-lifecycle",
        title: "Hooks Extend Lifecycle, Not Core State Progression",
        description:
          "Hooks should attach around stable lifecycle boundaries such as pre_tool, post_tool, and on_error. The core loop still owns messages, tool execution, and stop conditions. That separation keeps the system teachable and prevents hidden control flow.",
        alternatives:
          "Letting hooks mutate core loop control directly feels flexible, but it makes execution order harder to reason about. Stable lifecycle boundaries keep extension power without dissolving the mainline.",
        zh: {
          title: "Hook 扩展生命周期，不接管主状态推进",
          description:
            "Hook 应该挂在 pre_tool、post_tool、on_error 这类稳定边界上。messages、工具执行和停止条件仍由主循环掌控。这样系统心智才清晰，不会出现隐藏控制流。",
          alternatives:
            "让 Hook 直接改主循环状态看似灵活，但执行顺序会越来越难推理。稳定生命周期边界能保留扩展力，又不破坏主线。",
        },
        ja: {
          title: "Hook はライフサイクルを拡張し、主状態の進行は奪わない",
          description:
            "Hook は pre_tool、post_tool、on_error のような安定境界に付けるべきです。messages、tool 実行、停止条件は main loop が持ち続けます。これで system の心智が崩れず、隠れた制御フローも生まれません。",
          alternatives:
            "Hook が main loop 制御を直接書き換えると柔軟そうに見えますが、実行順はどんどん読みにくくなります。安定した lifecycle 境界が、拡張力と主線の明瞭さを両立させます。",
        },
      },
      {
        id: "normalized-hook-event-shape",
        title: "Hooks Need a Normalized Event Shape",
        description:
          "Each hook should receive the same event envelope: tool name, input, result, error, timing, and session identifiers. This lets audit, tracing, metrics, and policy hooks share one mental model instead of inventing custom payloads.",
        alternatives:
          "Passing ad hoc strings to each hook is fast, but every new hook then needs custom parsing and drifts from the rest of the system. A normalized event contract costs a little upfront and pays for itself quickly.",
        zh: {
          title: "Hook 必须共享统一事件结构",
          description:
            "每个 Hook 都应该收到同样的事件封包，例如 tool name、input、result、error、耗时、session id。这样审计、追踪、指标和策略 Hook 才共享同一心智模型。",
          alternatives:
            "给每个 Hook 传临时拼接的字符串最省事，但新 Hook 都得自己解析，系统会越来越散。统一事件结构前期多一点设计，后面会省很多心智成本。",
        },
        ja: {
          title: "Hook は正規化されたイベント形を共有する必要がある",
          description:
            "各 Hook は tool name、input、result、error、所要時間、session id のような同じ event envelope を受け取るべきです。これで audit、trace、metrics、policy hook が同じ心智モデルを共有できます。",
          alternatives:
            "その場しのぎの文字列を各 Hook に渡すのは楽ですが、新しい Hook のたびに独自解析が必要になり、system は散らかります。統一イベント契約は最初に少し設計が必要でも、すぐ元が取れます。",
        },
      },
    ],
  },
  s09: {
    version: "s09",
    decisions: [
      {
        id: "memory-keeps-only-durable-facts",
        title: "Memory Stores Durable Facts, Not Full History",
        description:
          "Long-term memory should hold cross-session facts such as user preferences, durable project constraints, and other information that cannot be cheaply re-derived. That keeps memory small, legible, and useful.",
        alternatives:
          "Saving every conversation turn feels safe, but it turns memory into an unbounded log and makes retrieval noisy. Selective durable memory is harder to teach at first, but it is the right system boundary.",
        zh: {
          title: "Memory 只保存长期有效事实",
          description:
            "长期记忆应该保存跨会话事实，例如用户偏好、稳定项目约束、无法轻易重新推导的信息。这样 memory 才会小而清晰，真正有用。",
          alternatives:
            "把整段历史全存进去看起来更稳，但长期会变成无边界日志，检索也会很脏。选择性保存长期事实更符合正确边界。",
        },
        ja: {
          title: "Memory は長く有効な事実だけを保存する",
          description:
            "long-term memory には、ユーザー設定、安定した project 制約、簡単には再導出できない情報のような、会話をまたいで有効な事実だけを置くべきです。そうすると memory は小さく、読みやすく、役に立つ状態を保てます。",
          alternatives:
            "会話履歴を全部保存すると安全そうですが、やがて無制限ログになり、検索も濁ります。長期事実だけを選んで残す方が正しい境界です。",
        },
      },
      {
        id: "memory-read-write-phases",
        title: "Memory Needs Clear Read and Write Phases",
        description:
          "Load relevant memory before prompt assembly, then extract and persist new durable facts after the work turn completes. This keeps memory flow visible and prevents the loop from mutating long-term state at arbitrary moments.",
        alternatives:
          "Writing memory opportunistically at random tool boundaries is possible, but it makes memory updates hard to explain. Clear read and write phases keep the lifecycle teachable.",
        zh: {
          title: "Memory 需要明确读写阶段",
          description:
            "在 prompt 装配前读取相关 memory，在任务轮次结束后提炼并写回新的长期事实。这样读写边界清楚，也避免主循环在任意时刻偷偷修改长期状态。",
          alternatives:
            "在随机工具边界随手写 memory 虽然也能跑，但很难解释系统到底何时更新长期知识。清晰阶段更适合教学和实现。",
        },
        ja: {
          title: "Memory には明確な読取段階と書込段階が必要だ",
          description:
            "prompt 組み立て前に関連 memory を読み込み、作業ターンの後で新しい durable fact を抽出して書き戻します。こうすると読書き境界が見え、main loop が任意の瞬間に長期状態をこっそり変えることも防げます。",
          alternatives:
            "適当な tool 境界で memory を書くこともできますが、いつ長期知識が更新されたのか説明しにくくなります。明確な read/write phase の方が、学習にも実装にも向いています。",
        },
      },
    ],
  },
  s10: {
    version: "s10",
    decisions: [
      {
        id: "prompt-is-a-pipeline",
        title: "The System Prompt Should Be Built as a Pipeline",
        description:
          "Role policy, workspace state, tool catalog, memory, and task focus should be assembled as explicit prompt sections in a visible order. This makes model input auditable and keeps the control plane understandable.",
        alternatives:
          "A single giant string looks simpler in code, but no one can explain which part came from where or why its order matters. A pipeline adds structure where the system actually needs it.",
        zh: {
          title: "系统提示词应被实现成装配流水线",
          description:
            "角色策略、工作区状态、工具目录、memory、任务焦点都应该作为显式片段按顺序装配。这样模型输入才可审计，控制平面也才讲得清楚。",
          alternatives:
            "一整段大字符串在代码里看起来更省事，但没人能说清每部分从哪来、顺序为什么这样。Prompt pipeline 才符合真实系统结构。",
        },
        ja: {
          title: "System prompt は組み立てパイプラインとして作るべきだ",
          description:
            "role policy、workspace state、tool catalog、memory、task focus は、見える順序を持つ prompt section として明示的に組み立てるべきです。これで model input が監査可能になり、control plane も説明しやすくなります。",
          alternatives:
            "巨大な 1 本の文字列にすると実装は簡単に見えますが、どこから来た指示なのか、なぜその順番なのかを誰も説明できません。pipeline の方が実際の構造に合っています。",
        },
      },
      {
        id: "stable-policy-separated-from-runtime-state",
        title: "Stable Policy Must Stay Separate from Runtime State",
        description:
          "Instruction hierarchy becomes clearer when stable rules live separately from volatile runtime data. That separation reduces accidental prompt drift and makes each prompt section easier to test.",
        alternatives:
          "Mixing durable policy with per-turn runtime details works for tiny demos, but it breaks down quickly once memory, tasks, and recovery hints all need to join the input.",
        zh: {
          title: "稳定策略与运行时状态必须分开",
          description:
            "当稳定规则和每轮运行时数据分离后，指令层级会清晰很多，也更不容易出现提示词结构漂移。每一段输入都更容易单独测试。",
          alternatives:
            "小 demo 里把所有东西揉在一起还能跑，但一旦 memory、任务状态、恢复提示都要加入输入，混写方式很快就失控。",
        },
        ja: {
          title: "安定した policy と runtime state は分けて保つべきだ",
          description:
            "変わりにくい規則と毎ターン変わる runtime data を分けると、指示の階層がずっと明確になります。prompt drift も起きにくくなり、各 section を個別にテストしやすくなります。",
          alternatives:
            "小さな demo では全部混ぜても動きますが、memory、task state、recovery hint まで入れ始めるとすぐ破綻します。分離が必要です。",
        },
      },
    ],
  },
  s11: {
    version: "s11",
    decisions: [
      {
        id: "explicit-continuation-reasons",
        title: "Recovery Needs Explicit Continuation Reasons",
        description:
          "After a failure, the agent should record whether it is retrying, degrading, requesting confirmation, or stopping. That reason becomes part of the visible state and lets the next model step act intentionally.",
        alternatives:
          "A blind retry loop is easy to implement, but neither the user nor the model can explain what branch the system is on. Explicit continuation reasons make recovery legible.",
        zh: {
          title: "恢复分支必须显式写出继续原因",
          description:
            "失败后，系统应该明确记录当前是在 retry、fallback、请求确认还是停止。这个原因本身也是可见状态，让下一步模型推理更有依据。",
          alternatives:
            "盲重试最容易写，但用户和模型都不知道系统现在处在哪条恢复分支。显式 continuation reason 才能让恢复过程可解释。",
        },
        ja: {
          title: "回復分岐は継続理由を明示して残すべきだ",
          description:
            "失敗後、system は retry・fallback・確認要求・停止のどれにいるのかを明示して記録すべきです。この理由自体が visible state になり、次の model step の判断材料になります。",
          alternatives:
            "盲目的な retry loop は実装しやすいですが、user も model も今どの回復分岐にいるのか説明できません。explicit continuation reason が回復を読めるものにします。",
        },
      },
      {
        id: "bounded-retry-branches",
        title: "Retry Paths Must Be Bounded",
        description:
          "Recovery branches need caps, stop conditions, and alternative strategies. Otherwise the system only hides failure behind repetition instead of turning it into progress.",
        alternatives:
          "Infinite retries can appear robust in early demos, but they produce loops with no insight. Bounded branches force the design to define when the system should pivot or stop.",
        zh: {
          title: "重试分支必须有上限和转向条件",
          description:
            "恢复分支必须有次数上限、停止条件和降级路径。否则系统只是把失败藏进重复执行，并没有真正把失败转成进展。",
          alternatives:
            "无限重试在早期 demo 里看起来像“更稳”，但其实只是在制造无洞察的循环。明确边界能逼迫系统定义何时转向或停止。",
        },
        ja: {
          title: "Retry 分岐には上限と転向条件が必要だ",
          description:
            "回復分岐には試行回数の上限、停止条件、別戦略への切替経路が必要です。そうしないと system は失敗を繰り返しの中へ隠すだけで、進展に変えられません。",
          alternatives:
            "無限 retry は初期 demo では頑丈に見えますが、実際は洞察のないループを作るだけです。境界を定めることで、いつ pivot し、いつ止まるかを設計できます。",
        },
      },
    ],
  },
  s12: {
    version: "s12",
    decisions: [
      {
        id: "task-records-are-durable-work-nodes",
        title: "Task Records Should Describe Durable Work Nodes",
        description:
          "A task record should represent work that can survive across turns, not a temporary note for one model call. That means keeping explicit identifiers, states, and dependency edges on disk or in another durable store.",
        alternatives:
          "Session-local todo text is cheaper to explain at first, but it cannot coordinate larger work once the loop moves on. Durable records add structure where the runtime actually needs it.",
        zh: {
          title: "任务记录必须是可持久的工作节点",
          description:
            "Task record 应该表示一项能跨轮次继续推进的工作，而不是某一轮模型调用里的临时备注。这要求它拥有明确 id、status 和依赖边，并被持久化保存。",
          alternatives:
            "会话级 todo 文本一开始更容易讲，但主循环一旦继续往前，它就无法协调更大的工作。Durable record 才是正确的系统边界。",
        },
        ja: {
          title: "Task record は持続する作業ノードを表すべきだ",
          description:
            "task record は、複数ターンにまたがって進む work を表すべきで、1 回の model call のメモではありません。そのために明示的な id、status、dependency edge を持ち、永続化される必要があります。",
          alternatives:
            "session 内 todo text は最初は説明しやすいですが、loop が先へ進むと大きな仕事を調整できません。durable record の方が正しい境界です。",
        },
      },
      {
        id: "unlock-logic-belongs-to-the-board",
        title: "Dependency Unlock Logic Belongs to the Task Board",
        description:
          "Completing one task should update the board, check dependency satisfaction, and unlock the next nodes. That logic belongs to the task system, not to whatever worker happened to finish the task.",
        alternatives:
          "Letting each worker manually decide what becomes available next is flexible, but it scatters dependency semantics across the codebase. Central board logic keeps the graph teachable.",
        zh: {
          title: "依赖解锁逻辑必须属于任务板",
          description:
            "完成一个任务以后，应该由任务板统一更新状态、检查依赖是否满足，并解锁后续节点。这段逻辑属于 task system，而不该散落到各个执行者手里。",
          alternatives:
            "让每个执行者自己判断后续任务是否解锁看似灵活，但依赖语义会散落到整个代码库。集中在任务板里才讲得清楚。",
        },
        ja: {
          title: "依存の解放ロジックは task board が持つべきだ",
          description:
            "1 つの task が完了したら、board が状態更新、依存充足の確認、次ノードの解放をまとめて行うべきです。このロジックは task system に属し、たまたま作業した worker に散らしてはいけません。",
          alternatives:
            "各 worker が次に何を解放するかを個別判断すると柔軟そうですが、dependency semantics がコード全体へ散ります。board に集中させる方が教えやすく、壊れにくいです。",
        },
      },
    ],
  },
  s13: {
    version: "s13",
    decisions: [
      {
        id: "runtime-records-separate-goal-from-execution",
        title: "Runtime Records Should Separate Goal from One Execution Attempt",
        description:
          "Background execution needs a record that describes the current run itself: status, timestamps, preview, and output location. That keeps the durable task goal separate from one live execution slot.",
        alternatives:
          "Reusing the same task record for both goal state and execution state saves one structure, but it blurs what is planned versus what is actively running right now.",
        zh: {
          title: "运行记录必须把目标和单次执行分开",
          description:
            "后台执行需要一份专门描述这次运行本身的记录，例如 status、时间戳、preview、output 位置。这样 durable task goal 和 live execution slot 才不会混在一起。",
          alternatives:
            "把 goal state 和 execution state 强行塞进同一条 task record 虽然省结构，但会模糊“计划中的工作”和“当前正在跑的这一趟执行”之间的边界。",
        },
        ja: {
          title: "Runtime record は goal と単発実行を分けて持つべきだ",
          description:
            "background execution には、その実行自身を表す record が必要です。status、timestamp、preview、output location を持たせることで、durable task goal と live execution slot が混ざらなくなります。",
          alternatives:
            "goal state と execution state を 1 つの task record へ押し込むと構造は減りますが、「計画された仕事」と「今走っている 1 回の実行」の境界が曖昧になります。",
        },
      },
      {
        id: "notifications-carry-preview-not-full-output",
        title: "Notifications Should Carry a Preview, Not the Full Log",
        description:
          "Large command output should be written to durable storage, while the notification only carries a compact preview. That preserves the return path into the main loop without flooding the active context window.",
        alternatives:
          "Injecting the full background log back into prompt space looks convenient, but it burns context and hides the difference between alerting the loop and storing the artifact.",
        zh: {
          title: "通知只带摘要，不直接带全文日志",
          description:
            "大输出应该写入持久存储，notification 只带一段 compact preview。这样既保住回到主循环的 return path，又不会把活跃上下文塞满。",
          alternatives:
            "把整份后台日志直接塞回 prompt 看起来省事，但会快速吃掉上下文，还会模糊“提醒主循环”和“保存原始产物”这两层职责。",
        },
        ja: {
          title: "通知は全文ログではなく preview だけを運ぶべきだ",
          description:
            "大きな出力は durable storage に書き、notification には compact preview だけを載せるべきです。これで main loop へ戻る経路を保ちつつ、活性 context を膨らませずに済みます。",
          alternatives:
            "background log 全文を prompt へ戻すのは手軽ですが、context を急速に消費し、「loop への通知」と「artifact の保存」という 2 つの責務も混ざります。",
        },
      },
    ],
  },
  s14: {
    version: "s14",
    decisions: [
      {
        id: "cron-only-triggers-runtime-work",
        title: "Cron Should Trigger Runtime Work, Not Own Execution",
        description:
          "The scheduler's job is to decide when a rule matches. Once it does, it should create runtime work and hand execution off to the runtime layer. This preserves a clean boundary between time and work.",
        alternatives:
          "Letting cron directly execute task logic is tempting for small systems, but it mixes rule-matching with execution state and makes both harder to teach and debug.",
        zh: {
          title: "Cron 只负责触发，不直接承担执行",
          description:
            "调度器的职责是判断时间规则何时命中。命中后应创建 runtime work，再把执行交给运行时层。这样“时间”和“工作”两类职责边界才干净。",
          alternatives:
            "小系统里让 cron 直接执行业务逻辑很诱人，但会把规则匹配和执行状态搅在一起，教学和调试都会变难。",
        },
        ja: {
          title: "Cron は発火だけを担当し、実行を抱え込まない",
          description:
            "scheduler の役割は時間規則がいつ一致するかを判断することです。一致したら runtime work を生成し、実行は runtime layer へ渡すべきです。これで「時間」と「仕事」の境界がきれいに保てます。",
          alternatives:
            "小さな system では cron がそのまま仕事を実行したくなりますが、rule matching と execution state が混ざり、学習にもデバッグにも不利です。",
        },
      },
      {
        id: "schedule-records-separate-from-runtime-records",
        title: "Schedule Records Must Stay Separate from Runtime Records",
        description:
          "A schedule says what should trigger and when. A runtime record says what is currently running, queued, retried, or completed. Keeping them separate makes both time semantics and execution semantics clearer.",
        alternatives:
          "A single merged record reduces file count, but it blurs whether the system is reasoning about recurring policy or one concrete execution instance.",
        zh: {
          title: "调度记录与运行时记录必须分离",
          description:
            "schedule 记录的是“何时触发什么”，runtime record 记录的是“当前运行、排队、重试或完成到哪一步”。分开后，时间语义和执行语义都更清楚。",
          alternatives:
            "把两者合成一条记录看似省事，但会混淆系统此刻究竟在描述长期规则，还是某次具体执行实例。",
        },
        ja: {
          title: "Schedule record と runtime record は分離すべきだ",
          description:
            "schedule は「いつ何を起動するか」を記録し、runtime record は「今どの実行が走り、待ち、再試行し、完了したか」を記録します。分けることで時間意味論と実行意味論の両方が明確になります。",
          alternatives:
            "両者を 1 レコードにまとめると楽そうですが、system が長期ルールを語っているのか、単発の実行インスタンスを語っているのかが分からなくなります。",
        },
      },
    ],
  },
  s15: {
    version: "s15",
    decisions: [
      {
        id: "teammates-need-persistent-identity",
        title: "Teammates Need Persistent Identity, Not One-Shot Delegation",
        description:
          "A teammate should keep a name, role, inbox, and status across multiple rounds of work. That persistence is what lets the platform assign responsibility instead of recreating a fresh subagent every time.",
        alternatives:
          "Disposable delegated workers are easier to implement, but they cannot carry stable responsibility or mailbox-based coordination over time.",
        zh: {
          title: "队友必须拥有长期身份，而不是一次性委派",
          description:
            "Teammate 应该在多轮工作之间保留名字、角色、inbox 和状态。只有这样，平台才能分配长期责任，而不是每次都重新创建一个临时 subagent。",
          alternatives:
            "一次性委派更容易实现，但它承载不了长期职责，也无法自然地进入 mailbox-based 协作。",
        },
        ja: {
          title: "チームメイトには使い捨てではない継続的な身元が必要だ",
          description:
            "teammate は複数ラウンドにわたり、名前、役割、inbox、状態を保つべきです。そうして初めて platform は長期責任を割り当てられ、毎回新しい subagent を作り直さずに済みます。",
          alternatives:
            "使い捨ての委譲 worker は作りやすいですが、安定した責務も mailbox ベースの協調も持ち運べません。",
        },
      },
      {
        id: "mailboxes-keep-collaboration-bounded",
        title: "Independent Mailboxes Keep Collaboration Legible",
        description:
          "Each teammate should coordinate through an inbox boundary rather than sharing one giant message history. That keeps ownership, message flow, and wake-up conditions easier to explain.",
        alternatives:
          "A shared message buffer looks simpler, but it erases agent boundaries and makes it harder to see who is responsible for what.",
        zh: {
          title: "独立邮箱边界让协作保持清晰",
          description:
            "每个队友都应该通过 inbox 边界协作，而不是共用一段巨大的消息历史。这样 ownership、消息流和唤醒条件才更容易讲清楚。",
          alternatives:
            "共享消息缓冲区看起来更简单，但会抹平 agent 边界，也更难解释到底谁在负责什么。",
        },
        ja: {
          title: "独立 mailbox があると協調の境界が読みやすくなる",
          description:
            "各 teammate は巨大な共有 message history を使うのではなく、inbox 境界を通して協調すべきです。これで ownership、message flow、wake-up condition を説明しやすくなります。",
          alternatives:
            "共有 message buffer は単純そうですが、agent 境界を消してしまい、誰が何に責任を持つのかが見えにくくなります。",
        },
      },
    ],
  },
  s16: {
    version: "s16",
    decisions: [
      {
        id: "protocols-need-request-correlation",
        title: "Protocol Messages Need Request Correlation",
        description:
          "Structured workflows such as approvals or shutdowns need request_id correlation so every reply, timeout, or rejection can resolve against the right request.",
        alternatives:
          "Free-form reply text may work in a tiny demo, but it breaks as soon as several protocol flows exist at once.",
        zh: {
          title: "协议消息必须带请求关联 id",
          description:
            "审批、关机这类结构化工作流必须带 request_id，这样每条回复、超时或拒绝才能准确对应到正确请求。",
          alternatives:
            "自由文本回复在极小 demo 里还能凑合，但一旦同时存在多条协议流程，就很快会对不上号。",
        },
        ja: {
          title: "プロトコルメッセージには request 相関 id が必要だ",
          description:
            "approval や shutdown のような構造化 workflow では request_id が必要です。そうして初めて各 reply、timeout、reject を正しい request に結び付けられます。",
          alternatives:
            "自由文の返答は極小 demo では動いても、複数の protocol flow が同時に走るとすぐ対応関係が崩れます。",
        },
      },
      {
        id: "request-state-should-be-durable",
        title: "Request State Should Be Durable and Inspectable",
        description:
          "Pending, approved, rejected, or expired states belong in a durable request record, not only in memory. That makes protocol state recoverable, inspectable, and teachable.",
        alternatives:
          "In-memory trackers are quick to write, but they disappear too easily and hide the real object the system is coordinating around.",
        zh: {
          title: "请求状态必须可持久、可检查",
          description:
            "pending、approved、rejected、expired 这些状态应该写进 durable request record，而不是只存在内存里。这样协议状态才能恢复、检查，也更适合教学。",
          alternatives:
            "内存追踪表写起来很快，但太容易消失，也会把系统真正围绕的对象藏起来。",
        },
        ja: {
          title: "Request state は永続化され、検査できるべきだ",
          description:
            "pending、approved、rejected、expired のような状態は durable request record に書くべきで、memory の中だけに置いてはいけません。そうすることで protocol state が回復可能・可視化可能になります。",
          alternatives:
            "in-memory tracker はすぐ書けますが、消えやすく、system が本当に中心にしている object も隠してしまいます。",
        },
      },
    ],
  },
  s17: {
    version: "s17",
    decisions: [
      {
        id: "autonomy-starts-with-bounded-claim-rules",
        title: "Autonomy Starts with Bounded Claim Rules",
        description:
          "Workers should only self-claim work when clear policies say they may do so. That prevents autonomy from turning into race conditions or duplicate execution.",
        alternatives:
          "Letting every idle worker grab anything looks energetic, but it makes the platform unpredictable. Claim rules keep autonomy controlled.",
        zh: {
          title: "自治从有边界的认领规则开始",
          description:
            "只有在明确策略允许的情况下，worker 才应该 self-claim 工作。这样才能避免自治变成撞车或重复执行。",
          alternatives:
            "让所有空闲 worker 见活就抢看起来很积极，但平台会变得不可预测。Claim rule 才能让自治保持可控。",
        },
        ja: {
          title: "自律は境界のある claim rule から始まる",
          description:
            "worker が self-claim してよいのは、明確な policy が許すときだけにすべきです。そうしないと autonomy は race condition や重複実行へ変わります。",
          alternatives:
            "空いている worker が何でも取りに行く設計は勢いがあるように見えますが、platform は予測不能になります。claim rule があって初めて自律を制御できます。",
        },
      },
      {
        id: "resume-must-come-from-visible-state",
        title: "Resumption Must Come from Visible State",
        description:
          "A worker should resume from task state, protocol state, mailbox contents, and role state. That keeps autonomy explainable instead of making it look like spontaneous intuition.",
        alternatives:
          "Implicit resume logic hides too much. Visible state may feel verbose, but it is what makes autonomous behavior debuggable.",
        zh: {
          title: "恢复执行必须建立在可见状态上",
          description:
            "Worker 应该根据 task state、protocol state、mailbox 内容和角色状态恢复执行。这样自治才可解释，而不是看起来像神秘直觉。",
          alternatives:
            "隐式恢复逻辑会把太多关键条件藏起来。可见状态虽然更啰嗦，但能让自治行为真正可调试。",
        },
        ja: {
          title: "再開は見える state から始まるべきだ",
          description:
            "worker は task state、protocol state、mailbox 内容、role state をもとに実行を再開すべきです。そうすることで autonomy は説明可能になり、謎の直感のようには見えません。",
          alternatives:
            "暗黙の resume ロジックは重要条件を隠しすぎます。visible state は少し冗長でも、自律挙動を本当にデバッグ可能にします。",
        },
      },
    ],
  },
  s18: {
    version: "s18",
    decisions: [
      {
        id: "worktree-is-a-lane-not-the-task",
        title: "A Worktree Is an Execution Lane, Not the Task Itself",
        description:
          "Tasks describe goals and dependency state. Worktrees describe isolated directories where execution happens. Keeping those two objects separate prevents the runtime model from blurring.",
        alternatives:
          "Collapsing task and worktree into one object removes one layer, but it becomes harder to explain whether the system is talking about work intent or execution environment.",
        zh: {
          title: "Worktree 是执行车道，不是任务本身",
          description:
            "Task 描述目标和依赖状态，worktree 描述隔离执行发生在哪个目录里。把两者分开，运行时模型才不会糊成一团。",
          alternatives:
            "把 task 和 worktree 硬合成一个对象虽然少一层，但会让系统很难解释当前说的是工作意图还是执行环境。",
        },
        ja: {
          title: "Worktree は task そのものではなく execution lane だ",
          description:
            "task は goal と dependency state を表し、worktree は隔離された実行ディレクトリを表します。この 2 つを分けることで runtime model が曖昧になりません。",
          alternatives:
            "task と worktree を 1 つの object に潰すと層は減りますが、system が work intent を語っているのか execution environment を語っているのか分かりにくくなります。",
        },
      },
      {
        id: "closeout-needs-explicit-keep-remove-semantics",
        title: "Closeout Needs Explicit Keep / Remove Semantics",
        description:
          "After isolated work finishes, the system should explicitly decide whether that lane is kept for follow-up or reclaimed. That makes lifecycle state observable instead of accidental.",
        alternatives:
          "Implicit cleanup feels automatic, but it hides important execution-lane decisions. Explicit closeout semantics teach the lifecycle much more clearly.",
        zh: {
          title: "收尾阶段必须显式决定保留还是回收",
          description:
            "隔离工作结束后，系统应该显式决定这个 lane 是继续保留给后续工作，还是立即回收。这样生命周期状态才可见，而不是碰运气。",
          alternatives:
            "隐式清理看起来很自动，但会把很多关键执行车道决策藏起来。显式 closeout 语义更适合教学，也更利于调试。",
        },
        ja: {
          title: "Closeout では保持か回収かを明示的に決めるべきだ",
          description:
            "隔離作業が終わった後、その lane を次の作業のために保持するのか、すぐ回収するのかを system が明示的に決めるべきです。これで lifecycle state が運任せではなく見える状態になります。",
          alternatives:
            "暗黙 cleanup は自動に見えますが、重要な execution-lane 判断を隠してしまいます。explicit closeout semantics の方が、学習にもデバッグにも向いています。",
        },
      },
    ],
  },
  s19: {
    version: "s19",
    decisions: [
      {
        id: "external-capabilities-share-one-routing-model",
        title: "External Capabilities Should Share the Same Routing Model as Native Tools",
        description:
          "Plugins and MCP servers should enter through the same capability-routing surface as native tools. That means discovery, routing, permission, execution, and result normalization all stay conceptually aligned.",
        alternatives:
          "Building a parallel external-capability subsystem may feel cleaner at first, but it doubles the mental model. One routing model keeps the platform understandable.",
        zh: {
          title: "外部能力必须共享同一套路由模型",
          description:
            "Plugin 和 MCP server 都应该从与本地工具相同的 capability routing 入口进入系统。这样发现、路由、权限、执行、结果标准化才保持同一心智。",
          alternatives:
            "单独给外部能力再造一套系统看似整洁，实际会把平台心智翻倍。共享一套 routing model 才更可教、也更可维护。",
        },
        ja: {
          title: "外部 capability は native tool と同じ routing model を共有すべきだ",
          description:
            "plugin と MCP server は、native tool と同じ capability routing surface から system へ入るべきです。そうすることで discovery、routing、permission、execution、result normalization が 1 つの心智に揃います。",
          alternatives:
            "外部 capability 用に並列 subsystem を作ると最初は整って見えますが、学習モデルが二重になります。1 つの routing model の方が platform を理解しやすく保てます。",
        },
      },
      {
        id: "scope-external-capabilities",
        title: "External Capabilities Need Scope and Policy Boundaries",
        description:
          "Remote capability does not mean unrestricted capability. Servers, plugins, and credentials need explicit workspace or session scopes so the platform can explain who can call what and why.",
        alternatives:
          "Global capability exposure is easier to wire up, but it weakens permission reasoning. Scoped capability access adds a small amount of configuration and a large amount of clarity.",
        zh: {
          title: "外部能力必须带作用域和策略边界",
          description:
            "远程能力不代表无限能力。server、plugin、credential 都要有 workspace 或 session 级作用域，平台才解释得清楚“谁能调用什么，为什么能调”。",
          alternatives:
            "全局暴露所有外部能力接起来最简单，但会削弱权限推理。增加一点 scope 配置，却能换来大量清晰度。",
        },
        ja: {
          title: "外部 capability には scope と policy の境界が必要だ",
          description:
            "remote capability だからといって無制限 capability ではありません。server、plugin、credential には workspace あるいは session scope が必要で、誰が何を呼べるのか、なぜ呼べるのかを platform が説明できるようにする必要があります。",
          alternatives:
            "すべての外部 capability をグローバル公開するのが最も配線は簡単ですが、permission reasoning が弱くなります。少しの scope 設定で、大きな明瞭さが得られます。",
        },
      },
    ],
  },
};

interface DesignDecisionsProps {
  version: string;
}

function DecisionCard({
  decision,
  locale,
}: {
  decision: Decision;
  locale: string;
}) {
  const [open, setOpen] = useState(false);
  const t = useTranslations("version");

  const localized =
    locale !== "en"
      ? ((decision as unknown as Record<string, unknown>)[locale] as DecisionLocaleCopy | undefined)
      : undefined;

  const title = localized?.title || decision.title;
  const description = localized?.description || decision.description;
  const alternatives = localized?.alternatives || decision.alternatives;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="pr-4 text-sm font-semibold text-zinc-900 dark:text-white">
          {title}
        </span>
        <ChevronDown
          size={16}
          className={cn(
            "shrink-0 text-zinc-400 transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
              <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
                {description}
              </p>

              {alternatives && (
                <div className="mt-3">
                  <h4 className="text-xs font-medium uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                    {t("alternatives")}
                  </h4>
                  <p className="mt-1 text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
                    {alternatives}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function DesignDecisions({ version }: DesignDecisionsProps) {
  const t = useTranslations("version");
  const locale = useLocale();

  const annotations = isGenericAnnotationVersion(version)
    ? GENERIC_ANNOTATIONS[version]
    : ANNOTATIONS[resolveLegacySessionAssetVersion(version)];

  if (!annotations || annotations.decisions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("design_decisions")}</h2>
      <div className="space-y-2">
        {annotations.decisions.map((decision, i) => (
          <motion.div
            key={decision.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <DecisionCard decision={decision} locale={locale} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
