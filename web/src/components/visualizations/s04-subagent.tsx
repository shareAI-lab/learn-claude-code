"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useLocale } from "@/lib/i18n";

interface MessageBlock {
  id: string;
  label: string;
  color: string;
}

type SupportedLocale = "zh" | "en" | "ja";

interface LocaleCopy {
  title: string;
  parentProcess: string;
  childProcess: string;
  notSpawned: string;
  isolationLabel: string;
  cleanContext: string;
  compressing: string;
  discarded: string;
  taskPromptChip: string;
  summaryChip: string;
  parentBaseMessages: [string, string, string];
  taskPrompt: string;
  childWorkMessages: [string, string];
  summaryBlock: string;
  stepInfo: Array<{ title: string; description: string }>;
}

const COPY: Record<SupportedLocale, LocaleCopy> = {
  zh: {
    title: "子代理上下文隔离",
    parentProcess: "父进程",
    childProcess: "子进程",
    notSpawned: "尚未创建子代理",
    isolationLabel: "隔离边界",
    cleanContext: "3 条原始消息 + 1 条摘要 = 干净上下文",
    compressing: "正在将完整上下文压缩为摘要...",
    discarded: "子代理上下文已回收",
    taskPromptChip: "task prompt（任务提示）",
    summaryChip: "summary（摘要）",
    parentBaseMessages: [
      "user: 构建登录 + 测试",
      "assistant: 规划执行路径...",
      "tool_result: 项目结构",
    ],
    taskPrompt: "task: 为鉴权模块编写单元测试",
    childWorkMessages: [
      "tool_use: read auth.ts",
      "tool_use: write test.ts",
    ],
    summaryBlock: "summary: 已写 3 个测试并全部通过",
    stepInfo: [
      {
        title: "父流程上下文",
        description: "父代理已累积当前会话消息。",
      },
      {
        title: "创建子代理",
        description: "Task（任务委托）创建全新 messages[] 的子代理，只传任务描述。",
      },
      {
        title: "独立执行",
        description: "子代理拥有独立上下文，不继承父流程历史。",
      },
      {
        title: "压缩结果",
        description: "子代理完整对话被压缩成一条摘要结果。",
      },
      {
        title: "回传摘要",
        description: "回到父流程的只有摘要，子代理完整上下文被丢弃。",
      },
      {
        title: "保持主线清洁",
        description: "父代理拿到精简摘要而不引入上下文膨胀，这就是 fresh-context（新鲜上下文）隔离。",
      },
    ],
  },
  en: {
    title: "Subagent Context Isolation",
    parentProcess: "Parent Process",
    childProcess: "Child Process",
    notSpawned: "not yet spawned",
    isolationLabel: "ISOLATION",
    cleanContext: "3 original + 1 summary = clean context",
    compressing: "Compressing full context into summary...",
    discarded: "context discarded",
    taskPromptChip: "task prompt",
    summaryChip: "summary",
    parentBaseMessages: [
      "user: Build login + tests",
      "assistant: Planning approach...",
      "tool_result: project structure",
    ],
    taskPrompt: "task: Write unit tests for auth",
    childWorkMessages: [
      "tool_use: read auth.ts",
      "tool_use: write test.ts",
    ],
    summaryBlock: "summary: 3 tests written, all passing",
    stepInfo: [
      {
        title: "Parent Context",
        description:
          "The parent agent has accumulated messages from the conversation.",
      },
      {
        title: "Spawn Subagent",
        description:
          "Task tool creates a child with fresh messages[]. Only the task description is passed.",
      },
      {
        title: "Independent Work",
        description:
          "The child has its own context. It doesn't see the parent's history.",
      },
      {
        title: "Compress Result",
        description:
          "The child's full conversation compresses into one summary.",
      },
      {
        title: "Return Summary",
        description:
          "Only the summary returns. The child's full context is discarded.",
      },
      {
        title: "Clean Context",
        description:
          "The parent gets a clean summary without context bloat. This is fresh-context isolation via messages[].",
      },
    ],
  },
  ja: {
    title: "サブエージェントの文脈隔離",
    parentProcess: "親プロセス",
    childProcess: "子プロセス",
    notSpawned: "まだ生成されていません",
    isolationLabel: "隔離境界",
    cleanContext: "元メッセージ 3 件 + 要約 1 件 = クリーンな文脈",
    compressing: "完全な文脈を要約へ圧縮中...",
    discarded: "子プロセス文脈を破棄",
    taskPromptChip: "task prompt",
    summaryChip: "summary",
    parentBaseMessages: [
      "user: ログイン + テストを構築",
      "assistant: 方針を計画中...",
      "tool_result: プロジェクト構造",
    ],
    taskPrompt: "task: 認証の単体テストを書く",
    childWorkMessages: [
      "tool_use: read auth.ts",
      "tool_use: write test.ts",
    ],
    summaryBlock: "summary: テスト 3 件を作成し、すべて成功",
    stepInfo: [
      {
        title: "親文脈",
        description: "親エージェントは会話からメッセージを蓄積しています。",
      },
      {
        title: "サブエージェント生成",
        description: "Task ツールが fresh messages[] の子を作り、タスク説明だけを渡します。",
      },
      {
        title: "独立作業",
        description: "子は独自文脈を持ち、親の履歴は見えません。",
      },
      {
        title: "結果圧縮",
        description: "子の会話全体は 1 つの要約へ圧縮されます。",
      },
      {
        title: "要約返却",
        description: "返るのは要約のみで、子の完全文脈は破棄されます。",
      },
      {
        title: "クリーン文脈",
        description: "親は文脈肥大を起こさず要約だけを受け取り、fresh-context 分離を保てます。",
      },
    ],
  },
};

function normalizeLocale(locale: string): SupportedLocale {
  if (locale === "zh" || locale === "ja") return locale;
  return "en";
}

export default function SubagentIsolation({ title }: { title?: string }) {
  const locale = normalizeLocale(useLocale());
  const copy = COPY[locale];
  const PARENT_BASE_MESSAGES: MessageBlock[] = [
    { id: "p1", label: copy.parentBaseMessages[0], color: "bg-blue-500" },
    { id: "p2", label: copy.parentBaseMessages[1], color: "bg-zinc-600" },
    { id: "p3", label: copy.parentBaseMessages[2], color: "bg-emerald-500" },
  ];
  const TASK_PROMPT: MessageBlock = {
    id: "task",
    label: copy.taskPrompt,
    color: "bg-purple-500",
  };
  const CHILD_WORK_MESSAGES: MessageBlock[] = [
    { id: "c1", label: copy.childWorkMessages[0], color: "bg-amber-500" },
    { id: "c2", label: copy.childWorkMessages[1], color: "bg-amber-500" },
  ];
  const SUMMARY_BLOCK: MessageBlock = {
    id: "summary",
    label: copy.summaryBlock,
    color: "bg-teal-500",
  };

  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: copy.stepInfo.length, autoPlayInterval: 2500 });

  // Derive what to show in each container based on step
  const parentMessages: MessageBlock[] = (() => {
    const base = [...PARENT_BASE_MESSAGES];
    if (currentStep >= 5) {
      base.push(SUMMARY_BLOCK);
    }
    return base;
  })();

  const childMessages: MessageBlock[] = (() => {
    if (currentStep < 1) return [];
    if (currentStep === 1) return [TASK_PROMPT];
    if (currentStep === 2) return [TASK_PROMPT, ...CHILD_WORK_MESSAGES];
    if (currentStep === 3) return [SUMMARY_BLOCK];
    return currentStep >= 4 ? [TASK_PROMPT, ...CHILD_WORK_MESSAGES] : [];
  })();

  const showChildEmpty = currentStep === 0;
  const showArcToChild = currentStep === 1;
  const showCompression = currentStep === 3;
  const showArcToParent = currentStep === 4;
  const childDiscarded = currentStep >= 4;
  const childFaded = currentStep >= 4;

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || copy.title}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900"
        style={{ minHeight: 500 }}
      >
        {/* Main layout: two containers side by side */}
        <div className="relative flex gap-4" style={{ minHeight: 340 }}>
          {/* Parent Process Container */}
          <div className="flex-1 rounded-xl border-2 border-blue-300 bg-blue-50/50 p-4 dark:border-blue-700 dark:bg-blue-950/20">
            <div className="mb-3 flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-blue-500" />
                <span className="text-sm font-bold text-blue-700 dark:text-blue-300">
                {copy.parentProcess}
              </span>
            </div>
            <div className="mb-2 font-mono text-xs text-zinc-400">
              messages[]
            </div>
            <div className="space-y-2">
              <AnimatePresence>
                {parentMessages.map((msg, i) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.4, delay: msg.id === "summary" ? 0.3 : 0 }}
                    className={`rounded-lg px-3 py-2 text-xs font-medium text-white shadow-sm ${msg.color}`}
                  >
                    {msg.label}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            {currentStep >= 5 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="mt-3 rounded border border-blue-200 bg-white/60 px-2 py-1 text-center text-xs text-blue-600 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-300"
              >
                {copy.cleanContext}
              </motion.div>
            )}
          </div>

          {/* Isolation Wall */}
          <div className="flex flex-col items-center justify-center gap-2">
            <div className="h-full w-px border-l-2 border-dashed border-zinc-300 dark:border-zinc-600" />
            <motion.div
              animate={{
                opacity: currentStep >= 1 && currentStep <= 4 ? 1 : 0.4,
              }}
              className="rounded bg-zinc-200 px-2 py-1 text-center font-mono text-[10px] text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400"
            >
              {copy.isolationLabel}
            </motion.div>
            <div className="h-full w-px border-l-2 border-dashed border-zinc-300 dark:border-zinc-600" />
          </div>

          {/* Child Process Container */}
          <div
            className={`flex-1 rounded-xl border-2 p-4 transition-colors duration-300 ${
              showChildEmpty
                ? "border-dashed border-zinc-300 bg-zinc-50/50 dark:border-zinc-600 dark:bg-zinc-800/30"
                : childDiscarded
                  ? "border-zinc-300 bg-zinc-100/50 dark:border-zinc-600 dark:bg-zinc-800/40"
                  : "border-purple-300 bg-purple-50/50 dark:border-purple-700 dark:bg-purple-950/20"
            }`}
          >
            <div className="mb-3 flex items-center gap-2">
              <div
                className={`h-3 w-3 rounded-full ${
                  showChildEmpty
                    ? "bg-zinc-300 dark:bg-zinc-600"
                    : childDiscarded
                      ? "bg-zinc-400 dark:bg-zinc-500"
                      : "bg-purple-500"
                }`}
              />
              <span
                className={`text-sm font-bold ${
                  showChildEmpty
                    ? "text-zinc-400 dark:text-zinc-500"
                    : childDiscarded
                      ? "text-zinc-400 dark:text-zinc-500"
                      : "text-purple-700 dark:text-purple-300"
                }`}
              >
                {copy.childProcess}
              </span>
            </div>
            <div className="mb-2 font-mono text-xs text-zinc-400">
              messages[] (fresh)
            </div>

            {showChildEmpty && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex h-24 items-center justify-center rounded-lg border border-dashed border-zinc-200 dark:border-zinc-700"
              >
                <span className="text-xs text-zinc-400">
                  {copy.notSpawned}
                </span>
              </motion.div>
            )}

            <div className="space-y-2">
              <AnimatePresence>
                {childMessages.map((msg) => (
                  <motion.div
                    key={msg.id + "-child"}
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: childFaded ? 0.3 : 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.4 }}
                    className={`rounded-lg px-3 py-2 text-xs font-medium text-white shadow-sm ${msg.color}`}
                  >
                    {msg.label}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {showCompression && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="mt-3 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-center text-xs text-amber-700 dark:border-amber-600 dark:bg-amber-900/20 dark:text-amber-300"
              >
                {copy.compressing}
              </motion.div>
            )}

            {childDiscarded && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 rounded border border-red-200 bg-red-50 px-2 py-1 text-center text-xs text-red-500 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
              >
                {copy.discarded}
              </motion.div>
            )}
          </div>

          {/* Animated arcs: task prompt going from parent to child */}
          <AnimatePresence>
            {showArcToChild && (
              <motion.div
                initial={{ opacity: 0, x: "20%", y: "-10%" }}
                animate={{ opacity: 1, x: "55%", y: "-10%" }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.0, ease: "easeInOut" }}
                className="pointer-events-none absolute left-0 top-0"
                style={{ zIndex: 10 }}
              >
                <div className="rounded-lg bg-purple-500 px-3 py-1.5 text-xs font-medium text-white shadow-lg">
                  {copy.taskPromptChip}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {showArcToParent && (
              <motion.div
                initial={{ opacity: 0, x: "75%", y: "60%" }}
                animate={{ opacity: 1, x: "15%", y: "60%" }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.0, ease: "easeInOut" }}
                className="pointer-events-none absolute left-0 top-0"
                style={{ zIndex: 10 }}
              >
                <div className="rounded-lg bg-teal-500 px-3 py-1.5 text-xs font-medium text-white shadow-lg">
                  {copy.summaryChip}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Step Controls */}
        <div className="mt-6">
          <StepControls
            currentStep={currentStep}
            totalSteps={totalSteps}
            onPrev={prev}
            onNext={next}
            onReset={reset}
            isPlaying={isPlaying}
            onToggleAutoPlay={toggleAutoPlay}
            stepTitle={copy.stepInfo[currentStep].title}
            stepDescription={copy.stepInfo[currentStep].description}
          />
        </div>
      </div>
    </section>
  );
}
