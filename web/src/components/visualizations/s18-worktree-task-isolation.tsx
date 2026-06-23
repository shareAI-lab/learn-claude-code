"use client";

import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";

type TaskStatus = "pending" | "in_progress" | "completed";

interface TaskRow {
  id: number;
  subject: string;
  status: TaskStatus;
  worktree: string;
}

interface WorktreeRow {
  name: string;
  branch: string;
  task: string;
  state: "none" | "active" | "kept" | "removed";
}

interface Lane {
  name: string;
  files: string[];
  highlight?: boolean;
}

interface StepState {
  title: string;
  desc: string;
  tasks: TaskRow[];
  worktrees: WorktreeRow[];
  lanes: Lane[];
  op: string;
}

const STEPS: StepState[] = [
  {
    title: "Single Workspace Pain",
    desc: "Two tasks are active, but both edits would hit one directory and collide.",
    op: "task_create x2",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "in_progress", worktree: "" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "" },
    ],
    worktrees: [],
    lanes: [
      { name: "main", files: ["auth/service.py", "ui/Login.tsx"], highlight: true },
      { name: "wt/auth-refactor", files: [] },
      { name: "wt/ui-login", files: [] },
    ],
  },
  {
    title: "Allocate Lane for Task 1",
    desc: "Create a worktree lane and associate it with task 1 for clear ownership.",
    op: "worktree_create(name='auth-refactor', task_id=1)",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "in_progress", worktree: "auth-refactor" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "" },
    ],
    worktrees: [
      { name: "auth-refactor", branch: "wt/auth-refactor", task: "#1", state: "active" },
    ],
    lanes: [
      { name: "main", files: ["ui/Login.tsx"] },
      { name: "wt/auth-refactor", files: ["auth/service.py"], highlight: true },
      { name: "wt/ui-login", files: [] },
    ],
  },
  {
    title: "Allocate Lane for Task 2",
    desc: "Lane creation and task association can be separate. Here task 2 binds after lane creation.",
    op: "worktree_create(name='ui-login')\ntask_bind_worktree(task_id=2, worktree='ui-login')",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "in_progress", worktree: "auth-refactor" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "ui-login" },
    ],
    worktrees: [
      { name: "auth-refactor", branch: "wt/auth-refactor", task: "#1", state: "active" },
      { name: "ui-login", branch: "wt/ui-login", task: "#2", state: "active" },
    ],
    lanes: [
      { name: "main", files: [] },
      { name: "wt/auth-refactor", files: ["auth/service.py"] },
      { name: "wt/ui-login", files: ["ui/Login.tsx"], highlight: true },
    ],
  },
  {
    title: "Run Commands in Isolated Lanes",
    desc: "Each command routes by selected lane directory, not by the shared root.",
    op: "worktree_run('auth-refactor', 'pytest tests/auth -q')",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "in_progress", worktree: "auth-refactor" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "ui-login" },
    ],
    worktrees: [
      { name: "auth-refactor", branch: "wt/auth-refactor", task: "#1", state: "active" },
      { name: "ui-login", branch: "wt/ui-login", task: "#2", state: "active" },
    ],
    lanes: [
      { name: "main", files: [] },
      { name: "wt/auth-refactor", files: ["auth/service.py", "tests/auth/test_login.py"], highlight: true },
      { name: "wt/ui-login", files: ["ui/Login.tsx", "ui/Login.css"] },
    ],
  },
  {
    title: "Keep One Lane, Close Another",
    desc: "Closeout can mix decisions: keep ui-login active for follow-up, remove auth-refactor and complete task 1.",
    op: "worktree_keep('ui-login')\nworktree_remove('auth-refactor', complete_task=true)\nworktree_events(limit=10)",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "completed", worktree: "" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "ui-login" },
    ],
    worktrees: [
      { name: "auth-refactor", branch: "wt/auth-refactor", task: "#1", state: "removed" },
      { name: "ui-login", branch: "wt/ui-login", task: "#2", state: "kept" },
    ],
    lanes: [
      { name: "main", files: [] },
      { name: "wt/auth-refactor", files: [] },
      { name: "wt/ui-login", files: ["ui/Login.tsx"], highlight: true },
    ],
  },
  {
    title: "Isolation + Coordination + Events",
    desc: "The board tracks shared truth, worktree lanes isolate execution, and events provide auditable side-channel traces.",
    op: "task_list + worktree_list + worktree_events",
    tasks: [
      { id: 1, subject: "Auth refactor", status: "completed", worktree: "" },
      { id: 2, subject: "UI login polish", status: "in_progress", worktree: "ui-login" },
    ],
    worktrees: [
      { name: "auth-refactor", branch: "wt/auth-refactor", task: "#1", state: "removed" },
      { name: "ui-login", branch: "wt/ui-login", task: "#2", state: "kept" },
    ],
    lanes: [
      { name: "main", files: [] },
      { name: "wt/auth-refactor", files: [] },
      { name: "wt/ui-login", files: ["ui/Login.tsx"], highlight: true },
    ],
  },
];

function statusClass(status: TaskStatus): string {
  if (status === "completed") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (status === "in_progress") return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
}

function worktreeClass(state: WorktreeRow["state"]): string {
  if (state === "active") return "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20";
  if (state === "kept") return "border-sky-300 bg-sky-50 dark:border-sky-800 dark:bg-sky-900/20";
  if (state === "removed") return "border-zinc-200 bg-zinc-100 opacity-70 dark:border-zinc-700 dark:bg-zinc-800";
  return "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900";
}

export default function WorktreeTaskIsolation({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2600 });
  const step = STEPS[vis.currentStep];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Worktree Task Isolation"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-3 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 font-mono text-xs text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">
          {step.op}
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-zinc-200 dark:border-zinc-700">
            <div className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              Task Board (.tasks)
            </div>
            <div className="space-y-2 p-2">
              {step.tasks.map((task) => (
                <motion.div
                  key={`${task.id}-${task.status}-${task.worktree}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="rounded border border-zinc-200 p-2 text-xs dark:border-zinc-700"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-zinc-500 dark:text-zinc-400">#{task.id}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${statusClass(task.status)}`}>
                      {task.status}
                    </span>
                  </div>
                  <div className="mt-1 font-medium text-zinc-800 dark:text-zinc-100">{task.subject}</div>
                  <div className="mt-1 font-mono text-[10px] text-zinc-500 dark:text-zinc-400">
                    worktree: {task.worktree || "-"}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-zinc-200 dark:border-zinc-700">
            <div className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              Worktree Index (.worktrees/index.json)
            </div>
            <div className="space-y-2 p-2">
              {step.worktrees.length === 0 && (
                <div className="rounded border border-dashed border-zinc-300 px-3 py-4 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
                  no worktrees yet
                </div>
              )}
              {step.worktrees.map((wt) => (
                <motion.div
                  key={`${wt.name}-${wt.state}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`rounded border p-2 text-xs ${worktreeClass(wt.state)}`}
                >
                  <div className="font-mono text-[11px] font-semibold text-zinc-800 dark:text-zinc-100">{wt.name}</div>
                  <div className="font-mono text-[10px] text-zinc-500 dark:text-zinc-400">{wt.branch}</div>
                  <div className="mt-1 text-[10px] text-zinc-600 dark:text-zinc-300">task: {wt.task}</div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-zinc-200 dark:border-zinc-700">
            <div className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              Execution Lanes
            </div>
            <div className="space-y-2 p-2">
              {step.lanes.map((lane) => (
                <motion.div
                  key={`${lane.name}-${lane.files.join(",")}`}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`rounded border p-2 text-xs ${
                    lane.highlight
                      ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
                      : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
                  }`}
                >
                  <div className="font-mono text-[11px] font-semibold text-zinc-800 dark:text-zinc-100">{lane.name}</div>
                  <div className="mt-1 space-y-1 font-mono text-[10px] text-zinc-500 dark:text-zinc-400">
                    {lane.files.length === 0 ? (
                      <div>(no changes)</div>
                    ) : (
                      lane.files.map((f) => <div key={f}>{f}</div>)
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800/60">
          <div className="font-medium text-zinc-800 dark:text-zinc-100">{step.title}</div>
          <div className="text-zinc-600 dark:text-zinc-300">{step.desc}</div>
        </div>
      </div>

      <StepControls
        currentStep={vis.currentStep}
        totalSteps={vis.totalSteps}
        onPrev={vis.prev}
        onNext={vis.next}
        onReset={vis.reset}
        isPlaying={vis.isPlaying}
        onToggleAutoPlay={vis.toggleAutoPlay}
        stepTitle={step.title}
        stepDescription={step.desc}
      />
    </section>
  );
}
