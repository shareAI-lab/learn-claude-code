"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, CalendarDays, CheckCircle2, Clock3, Database, Inbox } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Make It Repeatable",
    desc: "The user turns one normal prompt into a reusable schedule card.",
    active: "composer",
  },
  {
    title: "Store the Card",
    desc: "The schedule lives in durable data, so it is not tied to the current chat turn.",
    active: "ledger",
  },
  {
    title: "Time Keeps Moving",
    desc: "A tiny scheduler watches the clock while the agent can do other work.",
    active: "clock",
  },
  {
    title: "Copy Goes to the Queue",
    desc: "When the cron expression matches, the scheduler puts a due copy in the queue.",
    active: "queue",
  },
  {
    title: "Run as a Normal Turn",
    desc: "The queue processor hands the due prompt to the same agent loop beginners already know.",
    active: "inbox",
  },
  {
    title: "Keep the Original",
    desc: "The result is recorded, and the schedule card remains ready for the next matching time.",
    active: "done",
  },
] as const;

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

function Panel({
  title,
  icon,
  active,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "min-h-[230px] rounded-lg border p-3 transition-colors",
        active
          ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-md",
            active
              ? "bg-blue-500 text-white"
              : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
          )}
        >
          {icon}
        </span>
        {title}
      </div>
      {children}
    </div>
  );
}

function ScheduleCard({
  title,
  subtitle,
  tone = "blue",
}: {
  title: string;
  subtitle: string;
  tone?: "blue" | "amber" | "emerald";
}) {
  const toneClass = {
    blue: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200",
    amber: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200",
    emerald:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200",
  }[tone];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.98 }}
      transition={{ duration: 0.25 }}
      className={cn("rounded-md border p-3 shadow-sm", toneClass)}
    >
      <div className="font-mono text-xs font-semibold">{title}</div>
      <div className="mt-1 text-xs opacity-80">{subtitle}</div>
    </motion.div>
  );
}

export default function CronSchedulerVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const current = STEPS[step];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Cron Scheduler"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              <CalendarDays size={16} />
              Weekly clock
            </div>
            <motion.div
              animate={step >= 2 ? { scale: [1, 1.08, 1] } : { scale: 1 }}
              transition={{ duration: 1.1, repeat: step >= 2 && step <= 4 ? Infinity : 0 }}
              className="rounded-md bg-white px-2 py-1 font-mono text-xs text-zinc-600 shadow-sm dark:bg-zinc-900 dark:text-zinc-300"
            >
              {step < 2 ? "08:59" : "09:00"}
            </motion.div>
          </div>
          <div className="grid grid-cols-5 gap-2">
            {DAYS.map((day, index) => (
              <div
                key={day}
                className={cn(
                  "rounded-md border px-2 py-2 text-center text-xs font-medium",
                  step >= 2 && index === 2
                    ? "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200"
                    : "border-zinc-200 bg-white text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
                )}
              >
                {day}
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <Panel
            title="Schedule book"
            icon={<Database size={15} />}
            active={current.active === "ledger" || current.active === "done"}
          >
            <div className="space-y-3">
              {step === 0 && (
                <ScheduleCard title="Draft prompt" subtitle="review open PR every weekday" />
              )}
              <AnimatePresence>
                {step >= 1 && (
                  <ScheduleCard
                    title="0 9 * * 1-5"
                    subtitle="review open PR every weekday"
                    tone={step === 5 ? "emerald" : "blue"}
                  />
                )}
              </AnimatePresence>
              <div className="rounded-md border border-dashed border-zinc-300 px-3 py-4 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
                {step >= 1 ? "stored schedules stay here" : "no saved schedule yet"}
              </div>
            </div>
          </Panel>

          <Panel
            title="Due queue"
            icon={<Clock3 size={15} />}
            active={current.active === "clock" || current.active === "queue"}
          >
            <div className="space-y-3">
              <div className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                watcher: {step >= 2 ? "running" : "waiting"}
              </div>
              <AnimatePresence>
                {step >= 3 && step <= 4 && (
                  <ScheduleCard
                    title="due copy"
                    subtitle="same prompt, current timestamp"
                    tone="amber"
                  />
                )}
              </AnimatePresence>
              {step < 3 && (
                <div className="rounded-md border border-dashed border-zinc-300 px-3 py-8 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
                  queue is empty
                </div>
              )}
              {step === 5 && (
                <ScheduleCard title="queue drained" subtitle="ready for next tick" tone="emerald" />
              )}
            </div>
          </Panel>

          <Panel
            title="Agent inbox"
            icon={<Inbox size={15} />}
            active={current.active === "inbox" || current.active === "done"}
          >
            <div className="space-y-3">
              <AnimatePresence>
                {step >= 4 && (
                  <ScheduleCard
                    title="agent turn"
                    subtitle={step >= 5 ? "result appended" : "runs like a normal prompt"}
                    tone={step >= 5 ? "emerald" : "blue"}
                  />
                )}
              </AnimatePresence>
              <div className="flex items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                {step >= 5 ? <CheckCircle2 size={14} /> : <Bot size={14} />}
                {step >= 5 ? "review summary saved" : "agent loop available"}
              </div>
            </div>
          </Panel>
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
