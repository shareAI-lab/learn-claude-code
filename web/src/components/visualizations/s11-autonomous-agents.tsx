"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ClipboardList, Hourglass, UserRoundCog } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type AgentPhase = "idle" | "polling" | "claiming" | "working" | "done";
type TaskStatus = "open" | "claimed" | "complete";

interface AgentState {
  id: string;
  phase: AgentPhase;
  timer: number;
  task?: string;
}

interface TaskState {
  id: string;
  title: string;
  status: TaskStatus;
  owner?: string;
}

const STEPS = [
  {
    title: "Quiet Agents",
    desc: "Autonomous agents start by waiting. The important mental model is a work board, not a central dispatcher.",
  },
  {
    title: "Idle Timer Fills",
    desc: "An agent watches its own idle timer. When it waits long enough, it decides to look for work.",
  },
  {
    title: "Read the Board",
    desc: "The agent polls the shared task board and looks for an open card.",
  },
  {
    title: "Claim One Card",
    desc: "Claiming writes the agent name onto one task, making ownership visible.",
  },
  {
    title: "Work Independently",
    desc: "The claimed task moves into the agent workspace. No coordinator has to babysit it.",
  },
  {
    title: "Others Join In",
    desc: "A second agent can claim a different card through the same simple habit.",
  },
  {
    title: "Finish and Free Up",
    desc: "Completed work goes back to the board as done, and the agent returns to waiting.",
  },
  {
    title: "Self Organization",
    desc: "Timers plus visible ownership let a small group organize itself without a manager loop.",
  },
] as const;

const TASKS = [
  { id: "T1", title: "Fix auth bug" },
  { id: "T2", title: "Add rate limiter" },
  { id: "T3", title: "Write docs" },
  { id: "T4", title: "Clean tests" },
];

function getAgents(step: number): AgentState[] {
  if (step === 0) {
    return [
      { id: "A", phase: "idle", timer: 0.1 },
      { id: "B", phase: "idle", timer: 0 },
      { id: "C", phase: "idle", timer: 0 },
    ];
  }
  if (step === 1) {
    return [
      { id: "A", phase: "idle", timer: 0.85 },
      { id: "B", phase: "idle", timer: 0.25 },
      { id: "C", phase: "idle", timer: 0 },
    ];
  }
  if (step === 2) {
    return [
      { id: "A", phase: "polling", timer: 1 },
      { id: "B", phase: "idle", timer: 0.25 },
      { id: "C", phase: "idle", timer: 0 },
    ];
  }
  if (step === 3) {
    return [
      { id: "A", phase: "claiming", timer: 0, task: "T1" },
      { id: "B", phase: "idle", timer: 0.45 },
      { id: "C", phase: "idle", timer: 0.1 },
    ];
  }
  if (step === 4) {
    return [
      { id: "A", phase: "working", timer: 0, task: "T1" },
      { id: "B", phase: "idle", timer: 0.65 },
      { id: "C", phase: "idle", timer: 0.2 },
    ];
  }
  if (step === 5) {
    return [
      { id: "A", phase: "working", timer: 0, task: "T1" },
      { id: "B", phase: "claiming", timer: 0, task: "T2" },
      { id: "C", phase: "idle", timer: 0.35 },
    ];
  }
  if (step === 6) {
    return [
      { id: "A", phase: "done", timer: 0, task: "T1" },
      { id: "B", phase: "working", timer: 0, task: "T2" },
      { id: "C", phase: "idle", timer: 0.6 },
    ];
  }
  return [
    { id: "A", phase: "idle", timer: 0.15 },
    { id: "B", phase: "working", timer: 0, task: "T2" },
    { id: "C", phase: "claiming", timer: 0, task: "T3" },
  ];
}

function getTasks(step: number): TaskState[] {
  return TASKS.map((task) => {
    if (task.id === "T1" && step >= 6) {
      return { ...task, status: "complete", owner: "A" };
    }
    if (task.id === "T1" && step >= 3) {
      return { ...task, status: "claimed", owner: "A" };
    }
    if (task.id === "T2" && step >= 5) {
      return { ...task, status: "claimed", owner: "B" };
    }
    if (task.id === "T3" && step >= 7) {
      return { ...task, status: "claimed", owner: "C" };
    }
    return { ...task, status: "open" };
  });
}

function phaseClass(phase: AgentPhase): string {
  if (phase === "working") return "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30";
  if (phase === "claiming" || phase === "polling") return "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30";
  if (phase === "done") return "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30";
  return "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900";
}

function statusClass(status: TaskStatus): string {
  if (status === "complete") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (status === "claimed") return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300";
}

function AgentCard({ agent }: { agent: AgentState }) {
  const timerPercent = Math.round(agent.timer * 100);

  return (
    <motion.div
      layout
      animate={agent.phase !== "idle" ? { y: [0, -2, 0] } : { y: 0 }}
      transition={{ duration: 0.9, repeat: agent.phase !== "idle" ? Infinity : 0 }}
      className={cn("rounded-lg border p-3 transition-colors", phaseClass(agent.phase))}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-zinc-900 text-sm font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
            {agent.id}
          </span>
          <div>
            <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">Agent {agent.id}</div>
            <div className="text-[11px] capitalize text-zinc-500 dark:text-zinc-400">{agent.phase}</div>
          </div>
        </div>
        {agent.phase === "done" ? (
          <CheckCircle2 size={18} className="text-emerald-500" />
        ) : (
          <UserRoundCog size={18} className="text-zinc-400" />
        )}
      </div>

      <div className="mb-2 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <motion.div
          className="h-full rounded-full bg-amber-400"
          initial={{ width: 0 }}
          animate={{ width: `${timerPercent}%` }}
          transition={{ duration: 0.35 }}
        />
      </div>
      <div className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
        {agent.task ? `task: ${agent.task}` : `idle timer: ${timerPercent}%`}
      </div>
    </motion.div>
  );
}

export default function AutonomousAgents({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const agents = getAgents(step);
  const tasks = getTasks(step);
  const current = STEPS[step];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Autonomous Work Board"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr]">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              <Hourglass size={16} />
              Agents watch their own idle timer
            </div>
            <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
              {agents.map((agent) => (
                <AgentCard key={`${agent.id}-${agent.phase}-${agent.task ?? "none"}-${step}`} agent={agent} />
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              <ClipboardList size={16} />
              Shared task board
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <AnimatePresence mode="popLayout">
                {tasks.map((task) => (
                  <motion.div
                    layout
                    key={`${task.id}-${task.status}-${task.owner ?? "open"}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.96 }}
                    transition={{ duration: 0.2 }}
                    className="rounded-md border border-zinc-200 bg-white p-3 text-xs shadow-sm dark:border-zinc-700 dark:bg-zinc-900"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="font-mono font-semibold text-zinc-500 dark:text-zinc-400">{task.id}</span>
                      <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", statusClass(task.status))}>
                        {task.status}
                      </span>
                    </div>
                    <div className="font-medium text-zinc-800 dark:text-zinc-100">{task.title}</div>
                    <div className="mt-2 font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
                      owner: {task.owner ?? "-"}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            <div className="mt-3 rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
              Nobody assigns tasks directly; agents claim visible open cards when their timers wake them.
            </div>
          </div>
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
