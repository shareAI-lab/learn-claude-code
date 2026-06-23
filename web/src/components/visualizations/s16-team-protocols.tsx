"use client";

import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, CheckCircle2, ClipboardCheck, FileText, LockKeyhole, UserCheck } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type Protocol = "shutdown" | "plan";

const REQUEST_ID = "req_abc";

const SHUTDOWN_STEPS = [
  {
    title: "Agree on a Small Form",
    desc: "A protocol is just a shared card shape: request type, request_id, and the expected answer.",
  },
  {
    title: "Leader Files a Request",
    desc: "The leader writes a shutdown request card instead of force-stopping the teammate.",
  },
  {
    title: "Teammate Chooses",
    desc: "The teammate can approve or reject, and the request_id keeps the answer attached to the right request.",
  },
  {
    title: "Clean Exit",
    desc: "The approved response returns to the leader, and the teammate exits cleanly.",
  },
];

const PLAN_STEPS = [
  {
    title: "Work Is Locked",
    desc: "In plan mode, implementation stays locked until a plan card is approved.",
  },
  {
    title: "Submit the Plan Card",
    desc: "The teammate sends a concrete plan with the same request-response shape.",
  },
  {
    title: "Approval Unlocks Action",
    desc: "The leader approves the card, then implementation can begin.",
  },
];

const PROTOCOL_STATES: Record<Protocol, { label: string; detail: string }[]> = {
  shutdown: [
    { label: "drafted", detail: "Lead creates request_id" },
    { label: "pending", detail: "card waits in inbox" },
    { label: "deciding", detail: "teammate replies" },
    { label: "closed", detail: "Lead matches response" },
  ],
  plan: [
    { label: "locked", detail: "work cannot start" },
    { label: "submitted", detail: "plan card is sent" },
    { label: "approved", detail: "implementation unlocks" },
  ],
};

function ToggleButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-xs font-medium transition-colors active:scale-95",
        active
          ? "bg-blue-500 text-white"
          : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
      )}
    >
      {children}
    </button>
  );
}

function StateRail({
  states,
  currentStep,
}: {
  states: { label: string; detail: string }[];
  currentStep: number;
}) {
  return (
    <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
          Protocol state
        </div>
        <div className="break-words font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
          request_id: {REQUEST_ID}
        </div>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        {states.map((state, index) => {
          const active = index === currentStep;
          const done = index < currentStep;
          return (
            <div key={state.label} className="flex min-w-0 flex-1 items-stretch gap-2">
              <motion.div
                layout
                animate={active ? { y: [0, -2, 0] } : { y: 0 }}
                transition={{ duration: 0.8, repeat: active ? Infinity : 0 }}
                className={cn(
                  "min-w-0 flex-1 rounded-md border px-3 py-2 transition-colors",
                  active
                    ? "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/35 dark:text-blue-200"
                    : done
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200"
                      : "border-zinc-200 bg-white text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
                )}
              >
                <div className="break-words text-sm font-semibold">{state.label}</div>
                <div className="mt-1 break-words text-[11px] leading-snug opacity-80">
                  {state.detail}
                </div>
              </motion.div>
              {index < states.length - 1 && (
                <div className="hidden items-center text-zinc-300 dark:text-zinc-600 sm:flex">
                  <ArrowRight size={15} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Desk({
  title,
  icon,
  active,
  children,
}: {
  title: string;
  icon: ReactNode;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "min-h-[260px] rounded-lg border p-3 transition-colors",
        active
          ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-3 flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
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
        <span className="min-w-0 break-words">{title}</span>
      </div>
      {children}
    </div>
  );
}

function ProtocolCard({
  title,
  rows,
  tone = "blue",
}: {
  title: string;
  rows: string[];
  tone?: "blue" | "amber" | "emerald" | "zinc";
}) {
  const toneClass = {
    blue: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200",
    amber: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200",
    emerald:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200",
    zinc: "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200",
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
      <div className="break-words font-mono text-xs font-semibold">{title}</div>
      <div className="mt-2 space-y-1 font-mono text-[11px] opacity-85">
        {rows.map((row) => (
          <div key={row} className="break-words">
            {row}
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function EmptyTray({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-dashed border-zinc-300 px-3 py-5 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
      {label}
    </div>
  );
}

export default function TeamProtocols({ title }: { title?: string }) {
  const [protocol, setProtocol] = useState<Protocol>("shutdown");
  const steps = protocol === "shutdown" ? SHUTDOWN_STEPS : PLAN_STEPS;
  const vis = useSteppedVisualization({ totalSteps: steps.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;

  const switchProtocol = (value: Protocol) => {
    setProtocol(value);
    vis.reset();
  };

  const isPlan = protocol === "plan";

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Team Protocol Cards"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 flex justify-center gap-2">
          <ToggleButton active={!isPlan} onClick={() => switchProtocol("shutdown")}>
            Shutdown
          </ToggleButton>
          <ToggleButton active={isPlan} onClick={() => switchProtocol("plan")}>
            Plan Approval
          </ToggleButton>
        </div>

        <StateRail states={PROTOCOL_STATES[protocol]} currentStep={step} />

        <div className="grid gap-3 lg:grid-cols-3">
          <Desk
            title="Leader desk"
            icon={<UserCheck size={15} />}
            active={(!isPlan && (step === 1 || step === 3)) || (isPlan && step === 2)}
          >
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {!isPlan && step >= 1 && (
                  <ProtocolCard
                    key="shutdown-request"
                    title="shutdown_request"
                    rows={[`request_id: ${REQUEST_ID}`, "target: teammate", "mode: polite"]}
                    tone={step >= 3 ? "zinc" : "blue"}
                  />
                )}
                {!isPlan && step >= 3 && (
                  <ProtocolCard
                    key="shutdown-response"
                    title="shutdown_response"
                    rows={[`request_id: ${REQUEST_ID}`, "approve: true", "status: closed"]}
                    tone="emerald"
                  />
                )}
                {isPlan && step >= 2 && (
                  <ProtocolCard
                    key="plan-approved"
                    title="plan_approval_response"
                    rows={[`request_id: ${REQUEST_ID}`, "approve: true", "unlock: implementation"]}
                    tone="emerald"
                  />
                )}
              </AnimatePresence>
              {((!isPlan && step === 0) || (isPlan && step < 2)) && (
                <EmptyTray label="waiting for a protocol card" />
              )}
            </div>
          </Desk>

          <Desk
            title="Shared card shape"
            icon={<ClipboardCheck size={15} />}
            active={(!isPlan && step === 0) || (isPlan && step === 0)}
          >
            <div className="space-y-3">
              <ProtocolCard
                title="protocol fields"
                rows={["type", "request_id", "payload", "response"]}
                tone="amber"
              />
              <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                The key idea is correlation, not ceremony.
              </div>
              {isPlan && (
                <div className="flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                  <LockKeyhole size={14} />
                  implementation locked until approval
                </div>
              )}
            </div>
          </Desk>

          <Desk
            title="Teammate desk"
            icon={isPlan ? <FileText size={15} /> : <CheckCircle2 size={15} />}
            active={(!isPlan && step === 2) || (isPlan && step === 1)}
          >
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {!isPlan && step >= 2 && (
                  <ProtocolCard
                    key="teammate-decision"
                    title="decision card"
                    rows={[`request_id: ${REQUEST_ID}`, "choice: approve", step >= 3 ? "state: exited" : "state: deciding"]}
                    tone={step >= 3 ? "emerald" : "amber"}
                  />
                )}
                {isPlan && step >= 1 && (
                  <ProtocolCard
                    key="plan-card"
                    title="exit_plan_mode"
                    rows={[`request_id: ${REQUEST_ID}`, "1. edit module", "2. run tests", "3. report diff"]}
                    tone={step >= 2 ? "emerald" : "blue"}
                  />
                )}
              </AnimatePresence>
              {((!isPlan && step < 2) || (isPlan && step === 0)) && (
                <EmptyTray label={isPlan ? "draft plan not submitted" : "no request received"} />
              )}
            </div>
          </Desk>
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
          stepTitle={steps[step].title}
          stepDescription={steps[step].desc}
        />
      </div>
    </section>
  );
}
