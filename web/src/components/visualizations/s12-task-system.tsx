"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ClipboardList, FileJson, LockKeyhole, PlayCircle } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type Status = "blocked" | "ready" | "active" | "done";

interface TaskCard {
  id: string;
  title: string;
  blockers: string[];
  status: Status;
}

const STEPS = [
  {
    title: "Tasks Become Files",
    desc: "The agent writes work as task cards on disk, so the plan survives compaction and restarts.",
  },
  {
    title: "Find the First Ready Card",
    desc: "A task with no blockers is ready immediately. Everything else waits visibly.",
  },
  {
    title: "Work One Card",
    desc: "The active task is not just text in the model's head; it has a durable status.",
  },
  {
    title: "Completion Unlocks Dependents",
    desc: "When T1 is done, the cards that depended on T1 become ready.",
  },
  {
    title: "Parallel Ready Work",
    desc: "T2 and T3 can run independently, while T4 still waits for both.",
  },
  {
    title: "All Blockers Cleared",
    desc: "Once T2 and T3 are done, T4 moves from waiting to active.",
  },
  {
    title: "Board Resolved",
    desc: "Every card reaches done. The dependency idea is visible without drawing a graph.",
  },
] as const;

const BASE_TASKS = [
  { id: "T1", title: "Set up database", blockers: [] },
  { id: "T2", title: "Add API routes", blockers: ["T1"] },
  { id: "T3", title: "Build auth module", blockers: ["T1"] },
  { id: "T4", title: "Integration pass", blockers: ["T2", "T3"] },
  { id: "T5", title: "Deploy", blockers: ["T4"] },
];

function taskStatus(id: string, step: number): Status {
  const table: Record<string, Status[]> = {
    T1: ["ready", "ready", "active", "done", "done", "done", "done"],
    T2: ["blocked", "blocked", "blocked", "ready", "active", "done", "done"],
    T3: ["blocked", "blocked", "blocked", "ready", "active", "done", "done"],
    T4: ["blocked", "blocked", "blocked", "blocked", "blocked", "active", "done"],
    T5: ["blocked", "blocked", "blocked", "blocked", "blocked", "blocked", "done"],
  };
  return table[id]?.[step] ?? "blocked";
}

function getTasks(step: number): TaskCard[] {
  return BASE_TASKS.map((task) => ({ ...task, status: taskStatus(task.id, step) }));
}

function statusClass(status: Status): string {
  if (status === "done") return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200";
  if (status === "active") return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200";
  if (status === "ready") return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200";
  return "border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
}

function statusIcon(status: Status) {
  if (status === "done") return <CheckCircle2 size={15} />;
  if (status === "active") return <PlayCircle size={15} />;
  if (status === "ready") return <ClipboardList size={15} />;
  return <LockKeyhole size={15} />;
}

function TaskCardView({ task }: { task: TaskCard }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.22 }}
      className={cn("rounded-md border p-3 shadow-sm", statusClass(task.status))}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="font-mono text-xs font-semibold">{task.id}</div>
        <div className="flex items-center gap-1 text-[11px] font-semibold">
          {statusIcon(task.status)}
          {task.status}
        </div>
      </div>
      <div className="text-sm font-semibold leading-snug">{task.title}</div>
      <div className="mt-2 flex flex-wrap gap-1">
        {task.blockers.length === 0 ? (
          <span className="rounded bg-white/70 px-1.5 py-0.5 text-[10px] dark:bg-zinc-950/30">
            no blockers
          </span>
        ) : (
          task.blockers.map((blocker) => (
            <span key={blocker} className="rounded bg-white/70 px-1.5 py-0.5 font-mono text-[10px] dark:bg-zinc-950/30">
              waits for {blocker}
            </span>
          ))
        )}
      </div>
    </motion.div>
  );
}

function Lane({
  title,
  subtitle,
  tasks,
}: {
  title: string;
  subtitle: string;
  tasks: TaskCard[];
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-3">
        <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">{title}</div>
        <div className="text-[11px] text-zinc-500 dark:text-zinc-400">{subtitle}</div>
      </div>
      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {tasks.length > 0 ? (
            tasks.map((task) => <TaskCardView key={`${task.id}-${task.status}`} task={task} />)
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="rounded-md border border-dashed border-zinc-300 px-3 py-6 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400"
            >
              empty
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function TaskSystem({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const tasks = getTasks(step);
  const current = STEPS[step];

  const blocked = tasks.filter((task) => task.status === "blocked");
  const ready = tasks.filter((task) => task.status === "ready");
  const active = tasks.filter((task) => task.status === "active");
  const done = tasks.filter((task) => task.status === "done");

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Task Board Dependencies"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 flex flex-col gap-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
            <FileJson size={16} />
            .tasks board
          </div>
          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            <div className="rounded bg-zinc-100 px-2 py-1 dark:bg-zinc-900">{blocked.length} blocked</div>
            <div className="rounded bg-amber-100 px-2 py-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">{ready.length} ready</div>
            <div className="rounded bg-blue-100 px-2 py-1 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{active.length} active</div>
            <div className="rounded bg-emerald-100 px-2 py-1 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">{done.length} done</div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-4">
          <Lane title="Waiting" subtitle="blocked by another card" tasks={blocked} />
          <Lane title="Ready" subtitle="can be claimed now" tasks={ready} />
          <Lane title="Working" subtitle="currently in progress" tasks={active} />
          <Lane title="Done" subtitle="unlocks dependents" tasks={done} />
        </div>

        <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-relaxed text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
          A dependency is not an arrow students must trace. It is a visible blocker badge on the card.
        </div>

        <StepControls
          className="mt-4"
          currentStep={vis.currentStep}
          totalSteps={vis.totalSteps}
          onPrev={vis.prev}
          onNext={vis.next}
          onReset={vis.reset}
          isPlaying={vis.isPlaying}
          onToggleAutoPlay={vis.toggleAutoPlay}
          stepTitle={current.title}
          stepDescription={current.desc}
        />
      </div>
    </section>
  );
}
