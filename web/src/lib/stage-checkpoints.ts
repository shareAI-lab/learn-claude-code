import type { LearningLayer, VersionId } from "@/lib/constants";

type SupportedLocale = "zh" | "en" | "ja";

export interface StageCheckpoint {
  layer: LearningLayer;
  entryVersion: VersionId;
  endVersion: VersionId;
  title: Record<SupportedLocale, string>;
  body: Record<SupportedLocale, string>;
  rebuild: Record<SupportedLocale, string>;
}

export const STAGE_CHECKPOINTS: readonly StageCheckpoint[] = [
  {
    layer: "core",
    entryVersion: "s01",
    endVersion: "s06",
    title: {
      zh: "先停在这里，自己重做一遍单 agent 主骨架",
      en: "Pause here and rebuild the single-agent system from scratch",
      ja: "ここで一度止まり、単一 agent の背骨を自分で作り直す",
    },
    body: {
      zh: "读完 `s01-s06` 后，最有价值的动作不是立刻跳去权限或团队，而是从空目录里重新做出主循环、工具分发、会话计划、子任务隔离、技能加载和上下文压缩。",
      en: "You now have a complete single-agent system. The most valuable thing you can do right now is not rush ahead -- it's to open an empty directory and rebuild the loop, tool dispatch, session planning, subtask isolation, skill loading, and context compaction from memory.",
      ja: "`s01-s06` の後で最も価値が高いのは、そのまま permission や team へ進むことではありません。空のディレクトリから、loop・tool dispatch・session planning・subtask isolation・skill loading・context compaction を作り直すことです。",
    },
    rebuild: {
      zh: "一个能连续工作多轮、能调用工具、能写 todo、能委派子任务、能按需加载技能并且能做最小压缩的单 agent harness。",
      en: "A single-agent harness that can survive multiple turns, call tools, keep a todo plan, delegate one-shot subtasks, load skills on demand, and compact context at the minimum useful level.",
      ja: "複数ターン継続でき、tool を呼び、todo plan を持ち、単発 subtask を委譲し、skill を必要時だけ読み込み、最小限の compact を行える単一 agent harness。",
    },
  },
  {
    layer: "hardening",
    entryVersion: "s07",
    endVersion: "s11",
    title: {
      zh: "到这里先把控制面补稳，再进入任务系统",
      en: "Stabilize the control plane before moving to the task runtime",
      ja: "ここで制御面を安定させてからタスク実行層へ入る",
    },
    body: {
      zh: "读完 `s07-s11` 后，应该先自己补出一条完整的控制面：执行前权限闸门、固定生命周期 Hook、跨会话记忆、输入装配和恢复续行分支。",
      en: "Your agent now has real safety. Rebuild it with a permission gate before every tool call, lifecycle hooks for extension, cross-session memory, a prompt assembly pipeline, and structured recovery branches.",
      ja: "`s07-s11` の後は、自分の制御面を一度まとめて作り直すべきです。実行前の permission gate、固定ライフサイクル hook、cross-session memory、入力組み立て、recovery 分岐を 1 本に戻します。",
    },
    rebuild: {
      zh: "一个不只是会跑，而是已经补齐执行闸门、扩展插口、长期记忆、输入装配与恢复续行的稳固单 agent。",
      en: "A single agent with a real control plane: execution gating, extension hooks, durable memory, input assembly, and recovery branches.",
      ja: "ただ動くだけでなく、実行前 gate、拡張 hook、長期 memory、入力組み立て、recovery 分岐までそろった安定した single agent。",
    },
  },
  {
    layer: "runtime",
    entryVersion: "s12",
    endVersion: "s14",
    title: {
      zh: "到这里先把“工作系统”手搓出来，再看团队层",
      en: "Build the work runtime before moving into teams",
      ja: "ここで work runtime を作り切ってから team 層へ進む",
    },
    body: {
      zh: "读完 `s12-s14` 后，读者最该做的是把 `task goal`、`runtime slot`、`notification` 和 `schedule trigger` 四层对象真的分开写出来，而不是只记住它们的名字。",
      en: "Now build separate structures for task goals, runtime slots, notifications, and schedule triggers. Don't just remember the names -- implement each as a distinct piece.",
      ja: "`s12-s14` の後で大事なのは、task goal・runtime slot・notification・schedule trigger を名前だけで覚えることではなく、別々の構造として実装し分けることです。",
    },
    rebuild: {
      zh: "一套能记录持久任务、后台运行慢工作、用通知带回结果，并且允许时间触发开工的最小 runtime 系统。",
      en: "A minimal runtime that can persist task goals, run slow work in the background, return results through notifications, and let time trigger new work.",
      ja: "永続 task goal を持ち、遅い仕事を background で回し、notification で結果を戻し、時間で新しい仕事を起動できる最小 runtime system。",
    },
  },
  {
    layer: "platform",
    entryVersion: "s15",
    endVersion: "s19",
    title: {
      zh: "最后这一段要做的是平台边界，而不是只加很多功能",
      en: "The final stage: building the platform boundary",
      ja: "最後の段階で作るのは機能の山ではなくプラットフォーム境界です",
    },
    body: {
      zh: "读完 `s15-s19` 后，最应该回头确认的是五层边界有没有彻底分清：teammate、protocol request、task、worktree lane、external capability。",
      en: "You've completed the entire course. The key test: can you cleanly separate teammate, protocol request, task, worktree lane, and external capability? If yes, you understand the full design backbone.",
      ja: "`s15-s19` の後で最も確認すべきなのは、teammate・protocol request・task・worktree lane・external capability の 5 層を本当に分けて保てるかどうかです。",
    },
    rebuild: {
      zh: "一个拥有长期队友、共享协议、自治认领、隔离执行车道，并把原生工具与外部能力接回同一控制面的平台雏形。",
      en: "An agent platform with persistent teammates, shared protocols, autonomous claiming, isolated execution lanes, and one control plane for native and external capabilities.",
      ja: "永続 teammate、共有 protocol、自律 claim、分離 execution lane、そして native/external capability を 1 つの control plane へ戻したプラットフォームの骨格。",
    },
  },
] as const;

export function getStageCheckpoint(
  layer: LearningLayer | null | undefined
): StageCheckpoint | null {
  if (!layer) return null;
  return STAGE_CHECKPOINTS.find((checkpoint) => checkpoint.layer === layer) ?? null;
}
