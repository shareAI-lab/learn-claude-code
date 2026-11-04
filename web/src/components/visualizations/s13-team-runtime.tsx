"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  ClipboardList,
  GitBranch,
  Inbox,
  LockKeyhole,
  Search,
  Terminal,
  UsersRound,
} from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Confirm a Small Team",
    desc: "The Lead proposes focused roles and waits for the user before starting persistent teammates.",
    event: "lead proposes: backend + tests",
  },
  {
    title: "Claim Atomically",
    desc: "A ready task moves to one owner while the task-store file lock protects the persisted transition.",
    event: "task_store_lock: task_1a2b3c4d -> backend",
  },
  {
    title: "Require and Review a Plan",
    desc: "The gate is active before the teammate starts; the Lead reviews the typed request for this task and work version.",
    event: "review_plan(req_000007, approve=true)",
  },
  {
    title: "Route Tools to the Task Directory",
    desc: "The claimed task carries its worktree binding; bash, read, and write derive their cwd from that record.",
    event: "cwd -> .worktrees/auth-refactor",
  },
  {
    title: "Execute the Approved Work",
    desc: "Mutating tools run only after the current assignment's plan is approved.",
    event: "bash / write: allowed",
  },
  {
    title: "Return the Result, Keep the Teammate",
    desc: "Completion keeps the task cwd through the turn; IDLE releases the assignment and keeps the teammate available.",
    event: "complete -> result -> IDLE",
  },
] as const;

const EVENTS = STEPS.map((step) => step.event);

function StateBadge({
  label,
  tone,
}: {
  label: string;
  tone: "zinc" | "blue" | "amber" | "emerald";
}) {
  const classes = {
    zinc: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
    blue: "bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-200",
    amber: "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-200",
    emerald:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-200",
  }[tone];

  return (
    <span className={cn("shrink-0 whitespace-nowrap rounded px-2 py-1 text-[11px] font-semibold", classes)}>
      {label}
    </span>
  );
}

function RuntimePanel({ step }: { step: number }) {
  const state =
    step === 0 ? "awaiting confirmation" : step === 1 ? "working" : step === 5 ? "idle" : "active";
  const tone = step === 0 ? "zinc" : step === 5 ? "emerald" : "blue";

  return (
    <div className="min-h-[250px] rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <UsersRound size={16} className="shrink-0 text-blue-500" />
          <span className="break-words">Team runtime</span>
        </div>
        <StateBadge label={state} tone={tone} />
      </div>

      <div className="mt-4 grid grid-cols-[88px_minmax(0,1fr)] gap-x-2 gap-y-3 text-xs">
        <span className="text-zinc-500 dark:text-zinc-400">Lead</span>
        <span className="break-words font-medium text-zinc-800 dark:text-zinc-200">
          {step === 0 ? "proposes roles" : step === 5 ? "receives result" : "coordinates"}
        </span>
        <span className="text-zinc-500 dark:text-zinc-400">Teammate</span>
        <span className="break-words font-medium text-zinc-800 dark:text-zinc-200">
          backend
        </span>
        <span className="text-zinc-500 dark:text-zinc-400">Protocol</span>
        <span className="break-all font-mono text-zinc-700 dark:text-zinc-300">
          {step < 2 ? "-" : "request_id=req_000007"}
        </span>
      </div>

      <div className="mt-4 flex min-h-[72px] items-start gap-2 rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
        <Inbox size={15} className="mt-0.5 shrink-0" />
        <span className="break-words leading-relaxed">
          {step === 0
            ? "No mailbox is created before confirmation."
            : step === 2
              ? "The approval is tied to the claimed task and work version."
              : step === 5
                ? "The result wakes the Lead; IDLE releases the cwd lease."
                : "The runtime owns delivery while the teammate works."}
        </span>
      </div>
    </div>
  );
}

function TaskPanel({ step }: { step: number }) {
  const status = step < 1 ? "pending" : step < 5 ? "in_progress" : "completed";
  const owner = step < 1 ? "-" : "backend";
  const tone = status === "pending" ? "zinc" : status === "in_progress" ? "amber" : "emerald";

  return (
    <div className="min-h-[250px] rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <ClipboardList size={16} className="shrink-0 text-amber-500" />
          <span>Task board</span>
        </div>
        <StateBadge label={status} tone={tone} />
      </div>

      <div className="mt-4 rounded-md border border-zinc-200 p-3 dark:border-zinc-700">
        <div className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
          task_1a2b3c4d
        </div>
        <div className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          Refactor authentication
        </div>
        <div className="mt-3 grid grid-cols-[76px_minmax(0,1fr)] gap-2 text-xs">
          <span className="text-zinc-500 dark:text-zinc-400">owner</span>
          <span className="font-mono text-zinc-700 dark:text-zinc-300">{owner}</span>
          <span className="text-zinc-500 dark:text-zinc-400">blockedBy</span>
          <span className="font-mono text-zinc-700 dark:text-zinc-300">[]</span>
        </div>
      </div>

      <div
        className={cn(
          "mt-3 flex min-h-[56px] items-center gap-2 rounded-md border px-3 py-2 text-xs",
          step === 1
            ? "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
            : "border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
        )}
      >
        {step < 1 ? <Search size={15} className="shrink-0" /> : <LockKeyhole size={15} className="shrink-0" />}
        <span className="break-words">
          {step < 1
            ? "Waiting for the teammate loop."
            : step === 1
              ? "The claim check and update share one lock."
              : "The claimed task remains owned through the work turn."}
        </span>
      </div>
    </div>
  );
}

function WorkspacePanel({ step }: { step: number }) {
  const routed = step >= 3 && step < 5;
  const retained = step >= 5;

  return (
    <div className="min-h-[250px] rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <GitBranch size={16} className="shrink-0 text-emerald-500" />
          <span>Task directory</span>
        </div>
        <StateBadge
          label={routed ? "active cwd" : retained ? "binding retained" : "reserved"}
          tone={routed ? "emerald" : "zinc"}
        />
      </div>

      <div className="mt-4 space-y-2">
        <div
          className={cn(
            "rounded-md border p-3 transition-colors",
            !routed
              ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30"
              : "border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800"
          )}
        >
          <div className="font-mono text-xs font-semibold text-zinc-800 dark:text-zinc-200">
            repository root
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
            coordination state
          </div>
        </div>
        <motion.div
          animate={routed ? { y: [0, -2, 0] } : { y: 0 }}
          transition={{ duration: 0.8, repeat: routed ? Infinity : 0 }}
          className={cn(
            "rounded-md border p-3 transition-colors",
            routed
              ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30"
              : "border-dashed border-zinc-300 bg-white dark:border-zinc-700 dark:bg-zinc-900"
          )}
        >
          <div className="break-all font-mono text-xs font-semibold text-zinc-800 dark:text-zinc-200">
            .worktrees/auth-refactor
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
            {routed
              ? "bash / read / write cwd"
              : retained
                ? "task binding remains after IDLE"
                : "task.worktree binding"}
          </div>
        </motion.div>
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-300">
        {routed ? <Terminal size={15} /> : <GitBranch size={15} />}
        <span>
          {routed
            ? "Tools follow the claimed task."
            : retained
              ? "IDLE released active tool routing."
              : "No implicit directory switching."}
        </span>
      </div>
    </div>
  );
}

export default function TeamRuntime({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2800 });
  const step = vis.currentStep;
  const current = STEPS[step];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Agent Team Runtime"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-950">
        <div className="grid gap-3 lg:grid-cols-3">
          <RuntimePanel step={step} />
          <TaskPanel step={step} />
          <WorkspacePanel step={step} />
        </div>

        <div className="mt-3 rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            <CheckCircle2 size={14} />
            Runtime events
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {EVENTS.map((event, index) => {
              const visible = index <= step;
              return (
                <motion.div
                  key={event}
                  initial={false}
                  animate={{ opacity: visible ? 1 : 0.18, y: 0 }}
                  aria-hidden={!visible}
                  className={cn(
                    "break-all rounded-md border px-2 py-1.5 font-mono text-[10px]",
                    index === step
                      ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200"
                      : "border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                  )}
                >
                  {event}
                </motion.div>
              );
            })}
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
