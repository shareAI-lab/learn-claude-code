"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useLocale } from "@/lib/i18n";

// -- Task definitions --

type TaskStatus = "pending" | "in_progress" | "done";
type SupportedLocale = "zh" | "en" | "ja";

interface Task {
  id: number;
  label: LocalizedText;
  status: TaskStatus;
}

interface LocalizedText {
  zh: string;
  en: string;
  ja: string;
}

interface StepInfo {
  title: string;
  desc: string;
}

type TaskSnapshot = Array<{ id: number; status: TaskStatus }>;

const TASK_LABELS: Record<number, LocalizedText> = {
  1: {
    zh: "编写认证测试",
    en: "Write auth tests",
    ja: "認証テストを作成",
  },
  2: {
    zh: "修复移动端布局",
    en: "Fix mobile layout",
    ja: "モバイルレイアウトを修正",
  },
  3: {
    zh: "补充错误处理",
    en: "Add error handling",
    ja: "エラーハンドリングを追加",
  },
  4: {
    zh: "更新配置加载器",
    en: "Update config loader",
    ja: "設定ローダーを更新",
  },
};

// Snapshot of all 4 tasks at each step
const TASK_STATES: TaskSnapshot[] = [
  // Step 0: all pending
  [
    { id: 1, status: "pending" },
    { id: 2, status: "pending" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 1: still all pending (idle round 1)
  [
    { id: 1, status: "pending" },
    { id: 2, status: "pending" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 2: still all pending (idle round 2)
  [
    { id: 1, status: "pending" },
    { id: 2, status: "pending" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 3: NAG fires, task 1 moves to in_progress
  [
    { id: 1, status: "in_progress" },
    { id: 2, status: "pending" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 4: task 1 done
  [
    { id: 1, status: "done" },
    { id: 2, status: "pending" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 5: task 2 self-directed to in_progress
  [
    { id: 1, status: "done" },
    { id: 2, status: "in_progress" },
    { id: 3, status: "pending" },
    { id: 4, status: "pending" },
  ],
  // Step 6: tasks 2,3 done, task 4 in_progress
  [
    { id: 1, status: "done" },
    { id: 2, status: "done" },
    { id: 3, status: "done" },
    { id: 4, status: "in_progress" },
  ],
];

// Nag timer value at each step (out of 3)
const NAG_TIMER_PER_STEP = [0, 1, 2, 3, 0, 0, 0];
const NAG_THRESHOLD = 3;

// Whether the nag fires at this step
const NAG_FIRES_PER_STEP = [false, false, false, true, false, false, false];

const STEP_INFO: Record<SupportedLocale, StepInfo[]> = {
  zh: [
    {
      title: "可见计划",
      desc: "TodoWrite（待办写入）先把计划显式写出来，所有任务初始都是 pending（待处理）。",
    },
    {
      title: "第 1 轮空转",
      desc: "模型开始工作但没有推进待办，催办计数器增加 1。",
    },
    {
      title: "第 2 轮空转",
      desc: "连续两轮没有推进任务，系统即将触发提醒。",
    },
    {
      title: "触发提醒",
      desc: "达到阈值后插入系统提醒：你有待办任务，请马上接手一项。",
    },
    {
      title: "完成一项",
      desc: "任务完成后计时器归零，说明“有推进”会清空催办压力。",
    },
    {
      title: "自主推进",
      desc: "模型学会节奏后，会主动领取下一项任务。",
    },
    {
      title: "稳定收敛",
      desc: "可见计划 + 轻度催办，让多步骤任务更稳定地完成。",
    },
  ],
  en: [
    {
      title: "The Plan",
      desc: "TodoWrite gives the model a visible plan. All tasks start as pending.",
    },
    {
      title: "Round 1 -- Idle",
      desc: "The model does work but doesn't touch its todos. The nag counter increments.",
    },
    {
      title: "Round 2 -- Still Idle",
      desc: "Two rounds without progress. Pressure builds.",
    },
    {
      title: "NAG!",
      desc: "Threshold reached! System message injected: 'You have pending tasks. Pick one up now!'",
    },
    {
      title: "Task Complete",
      desc: "The model completes the task. Timer stays at 0 -- working on todos resets the counter.",
    },
    {
      title: "Self-Directed",
      desc: "Once the model learns the pattern, it picks up tasks voluntarily.",
    },
    {
      title: "Mission Accomplished",
      desc: "Visible plan + nag pressure = reliable task completion.",
    },
  ],
  ja: [
    {
      title: "可視化された計画",
      desc: "TodoWrite によって計画が先に明示され、全タスクは pending から始まります。",
    },
    {
      title: "1 ラウンド目の停滞",
      desc: "作業は進んでいるように見えても todo は更新されず、催促カウンタが増加します。",
    },
    {
      title: "2 ラウンド目も停滞",
      desc: "進捗なしが続くと、催促圧力が高まります。",
    },
    {
      title: "催促発火",
      desc: "しきい値到達でシステムメッセージが注入されます。",
    },
    {
      title: "タスク完了",
      desc: "todo を進めるとタイマーは 0 に戻ります。",
    },
    {
      title: "自律的な着手",
      desc: "パターンを学習すると、モデルは自発的に次のタスクを拾います。",
    },
    {
      title: "安定完了",
      desc: "可視計画と催促圧力により、タスク完了率が安定します。",
    },
  ],
};

const UI_COPY: Record<
  SupportedLocale,
  {
    title: string;
    nagTimer: string;
    nagMessage: string;
    pending: string;
    inProgress: string;
    done: string;
    progress: (done: number, total: number) => string;
    statusLabel: Record<TaskStatus, string>;
  }
> = {
  zh: {
    title: "TodoWrite 待办督促系统",
    nagTimer: "催办计时器",
    nagMessage: '系统提示："你还有待办任务，请立即接手一项！"',
    pending: "待处理",
    inProgress: "进行中",
    done: "已完成",
    progress: (done, total) => `进度：${done}/${total} 已完成`,
    statusLabel: {
      pending: "待处理",
      in_progress: "进行中",
      done: "已完成",
    },
  },
  en: {
    title: "TodoWrite Nag System",
    nagTimer: "Nag Timer",
    nagMessage: 'SYSTEM: "You have pending tasks. Pick one up now!"',
    pending: "Pending",
    inProgress: "In Progress",
    done: "Done",
    progress: (done, total) => `Progress: ${done}/${total} complete`,
    statusLabel: {
      pending: "pending",
      in_progress: "in progress",
      done: "done",
    },
  },
  ja: {
    title: "TodoWrite 催促システム",
    nagTimer: "催促タイマー",
    nagMessage: 'SYSTEM: 「保留中のタスクがあります。今すぐ 1 つ着手してください」',
    pending: "保留",
    inProgress: "進行中",
    done: "完了",
    progress: (done, total) => `進捗: ${done}/${total} 完了`,
    statusLabel: {
      pending: "保留",
      in_progress: "進行中",
      done: "完了",
    },
  },
};

function normalizeLocale(locale: string): SupportedLocale {
  if (locale === "zh" || locale === "ja") return locale;
  return "en";
}

function pick(locale: SupportedLocale, text: LocalizedText): string {
  return text[locale];
}

function buildTasks(step: number): Task[] {
  return TASK_STATES[step].map((item) => ({
    id: item.id,
    status: item.status,
    label: TASK_LABELS[item.id],
  }));
}

// -- Column component --

function KanbanColumn({
  title,
  tasks,
  accentClass,
  headerBg,
}: {
  title: string;
  tasks: Task[];
  accentClass: string;
  headerBg: string;
}) {
  return (
    <div className="flex min-h-[280px] flex-1 flex-col rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900">
      <div
        className={`rounded-t-lg px-3 py-2 text-center text-xs font-bold uppercase tracking-wider ${headerBg}`}
      >
        {title}
        <span className={`ml-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${accentClass}`}>
          {tasks.length}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2">
        <AnimatePresence mode="popLayout">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </AnimatePresence>
        {tasks.length === 0 && (
          <div className="flex flex-1 items-center justify-center text-xs text-zinc-400 dark:text-zinc-600">
            --
          </div>
        )}
      </div>
    </div>
  );
}

// -- Task card --

function TaskCard({ task }: { task: Task }) {
  const locale = normalizeLocale(useLocale());
  const statusStyles: Record<TaskStatus, string> = {
    pending: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
    in_progress: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  };

  const borderStyles: Record<TaskStatus, string> = {
    pending: "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800",
    in_progress: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30",
    done: "border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/30",
  };

  return (
    <motion.div
      layout
      layoutId={`task-${task.id}`}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={`rounded-md border p-2.5 ${borderStyles[task.status]}`}
    >
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
          #{task.id}
        </span>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${statusStyles[task.status]}`}
        >
          {UI_COPY[locale].statusLabel[task.status]}
        </span>
      </div>
      <div className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
        {pick(locale, task.label)}
      </div>
    </motion.div>
  );
}

// -- Nag gauge --

function NagGauge({
  value,
  max,
  firing,
  label,
}: {
  value: number;
  max: number;
  firing: boolean;
  label: string;
}) {
  const pct = Math.min((value / max) * 100, 100);

  const barColor =
    value === 0
      ? "bg-zinc-300 dark:bg-zinc-600"
      : value === 1
        ? "bg-green-400 dark:bg-green-500"
        : value === 2
          ? "bg-yellow-400 dark:bg-yellow-500"
          : "bg-red-500 dark:bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
          {label}
        </span>
        <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">
          {value}/{max}
        </span>
      </div>
      <div className="relative h-4 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
        <motion.div
          className={`absolute inset-y-0 left-0 rounded-full ${barColor}`}
          initial={{ width: "0%" }}
          animate={{
            width: `${pct}%`,
            ...(firing ? { scale: [1, 1.05, 1] } : {}),
          }}
          transition={{
            width: { duration: 0.5, ease: "easeOut" },
            scale: { duration: 0.3, repeat: 2 },
          }}
        />
        {firing && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-red-500"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0, 1, 0] }}
            transition={{ duration: 1 }}
          />
        )}
      </div>
    </div>
  );
}

// -- Main component --

export default function TodoWrite({ title }: { title?: string }) {
  const locale = normalizeLocale(useLocale());
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: 7, autoPlayInterval: 2500 });

  const copy = UI_COPY[locale];
  const tasks = buildTasks(currentStep);
  const nagValue = NAG_TIMER_PER_STEP[currentStep];
  const nagFires = NAG_FIRES_PER_STEP[currentStep];
  const stepInfo = STEP_INFO[locale][currentStep];

  const pendingTasks = tasks.filter((t) => t.status === "pending");
  const inProgressTasks = tasks.filter((t) => t.status === "in_progress");
  const doneTasks = tasks.filter((t) => t.status === "done");

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || copy.title}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        {/* Nag gauge + nag message */}
        <div className="mb-4 space-y-2">
          <NagGauge
            value={nagValue}
            max={NAG_THRESHOLD}
            firing={nagFires}
            label={copy.nagTimer}
          />

          <AnimatePresence>
            {nagFires && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-center text-xs font-bold text-red-700 dark:border-red-700 dark:bg-red-950/30 dark:text-red-300"
              >
                {copy.nagMessage}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Kanban board */}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <KanbanColumn
            title={copy.pending}
            tasks={pendingTasks}
            accentClass="bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
            headerBg="bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
          />
          <KanbanColumn
            title={copy.inProgress}
            tasks={inProgressTasks}
            accentClass="bg-amber-200 text-amber-700 dark:bg-amber-800 dark:text-amber-200"
            headerBg="bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
          />
          <KanbanColumn
            title={copy.done}
            tasks={doneTasks}
            accentClass="bg-emerald-200 text-emerald-700 dark:bg-emerald-800 dark:text-emerald-200"
            headerBg="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
          />
        </div>

        {/* Progress summary */}
        <div className="mt-3 flex items-center justify-between rounded-md bg-zinc-100 px-3 py-2 dark:bg-zinc-800">
          <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
            {copy.progress(doneTasks.length, tasks.length)}
          </span>
          <div className="flex gap-0.5">
            {tasks.map((t) => (
              <div
                key={t.id}
                className={`h-2 w-6 rounded-sm ${
                  t.status === "done"
                    ? "bg-emerald-500"
                    : t.status === "in_progress"
                      ? "bg-amber-400"
                      : "bg-zinc-300 dark:bg-zinc-600"
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      <StepControls
        currentStep={currentStep}
        totalSteps={totalSteps}
        onPrev={prev}
        onNext={next}
        onReset={reset}
        isPlaying={isPlaying}
        onToggleAutoPlay={toggleAutoPlay}
        stepTitle={stepInfo.title}
        stepDescription={stepInfo.desc}
      />
    </section>
  );
}
