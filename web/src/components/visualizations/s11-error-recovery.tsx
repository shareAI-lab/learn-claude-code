"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, AlertTriangle, Gauge, History, Repeat2, RotateCcw, ShieldCheck, TimerReset, Workflow } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Normal Call Still Comes First",
    desc: "The runtime starts with a regular LLM call and only enters recovery when a specific failure appears.",
    mode: "normal",
  },
  {
    title: "max_tokens Means Output Was Cut Off",
    desc: "First recovery is to retry with a larger budget before adding any synthetic continuation message.",
    mode: "max-tokens",
  },
  {
    title: "prompt_too_long Means Context Must Shrink",
    desc: "The runtime performs reactive compact once, then retries the same task with a smaller message list.",
    mode: "prompt-too-long",
  },
  {
    title: "429 Means Wait, Then Retry",
    desc: "Rate limits use exponential backoff with jitter so retries do not stampede the provider.",
    mode: "rate-limit",
  },
  {
    title: "Repeated 529 Can Switch Models",
    desc: "Provider overload increments RecoveryState and can move to a fallback model after repeated failures.",
    mode: "overloaded",
  },
  {
    title: "Recovered Calls Return to the Loop",
    desc: "Each recovery path is bounded, inspectable, and eventually returns to the normal tool loop or exits cleanly.",
    mode: "summary",
  },
] as const;

const CASES = [
  {
    id: "max-tokens",
    label: "max_tokens",
    symptom: "model stopped mid-answer",
    action: "8K -> 64K, retry same request",
    state: "token escalated once",
    tone: "amber",
  },
  {
    id: "prompt-too-long",
    label: "prompt_too_long",
    symptom: "context too large",
    action: "reactive_compact(messages), retry once",
    state: "compact retry used",
    tone: "orange",
  },
  {
    id: "rate-limit",
    label: "429",
    symptom: "rate limited",
    action: "backoff + jitter, max 10 retries",
    state: "retry attempt counted",
    tone: "blue",
  },
  {
    id: "overloaded",
    label: "529",
    symptom: "provider overloaded",
    action: "backoff; 3 consecutive -> fallback model",
    state: "consecutive_529 tracked",
    tone: "red",
  },
] as const;

type StepMode = (typeof STEPS)[number]["mode"];
type CaseId = (typeof CASES)[number]["id"];
type Tone = "amber" | "orange" | "blue" | "red" | "emerald" | "zinc";

function toneClass(tone: Tone, active = true) {
  if (!active) return "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200";
  if (tone === "orange") return "border-orange-200 bg-orange-50 text-orange-800 dark:border-orange-900 dark:bg-orange-950/40 dark:text-orange-200";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200";
  if (tone === "red") return "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200";
  if (tone === "emerald") return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200";
  return "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200";
}

function activeCase(mode: StepMode): CaseId | null {
  if (mode === "max-tokens") return "max-tokens";
  if (mode === "prompt-too-long") return "prompt-too-long";
  if (mode === "rate-limit") return "rate-limit";
  if (mode === "overloaded") return "overloaded";
  return null;
}

function Surface({
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
        "min-w-0 rounded-lg border p-4 transition-colors",
        active
          ? "border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-4 flex min-w-0 items-center gap-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            active ? "bg-red-500 text-white" : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
          )}
        >
          {icon}
        </span>
        <span className="min-w-0 text-wrap">{title}</span>
      </div>
      {children}
    </div>
  );
}

function CaseCard({
  item,
  active,
  muted,
}: {
  item: (typeof CASES)[number];
  active: boolean;
  muted: boolean;
}) {
  return (
    <motion.div
      layout
      animate={active ? { y: -1 } : { y: 0 }}
      className={cn(
        "min-w-0 rounded-lg border p-3",
        active ? toneClass(item.tone as Tone) : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900",
        muted && "opacity-45"
      )}
    >
      <div className="mb-2 flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0 font-mono text-sm font-semibold">{item.label}</div>
        {active && <AlertTriangle size={15} className="shrink-0" />}
      </div>
      <div className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">{item.symptom}</div>
      <div className="mt-2 rounded bg-white/70 px-2 py-1 text-xs leading-relaxed dark:bg-zinc-950/30">{item.action}</div>
    </motion.div>
  );
}

function RecoveryStatePanel({ mode }: { mode: StepMode }) {
  const values = {
    token: mode === "max-tokens" || mode === "summary" ? "64K used" : "8K",
    compact: mode === "prompt-too-long" || mode === "summary" ? "used once" : "unused",
    retry: mode === "rate-limit" || mode === "overloaded" || mode === "summary" ? "counting" : "0",
    model: mode === "overloaded" ? "fallback ready" : "primary",
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
      {[
        ["max_tokens", values.token],
        ["reactive_compact", values.compact],
        ["retry_attempt", values.retry],
        ["current_model", values.model],
      ].map(([label, value]) => (
        <div key={label} className="min-w-0 rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <div className="mb-1 font-mono text-xs text-zinc-500 dark:text-zinc-400">{label}</div>
          <div className="break-words text-sm font-semibold text-zinc-900 dark:text-zinc-100">{value}</div>
        </div>
      ))}
    </div>
  );
}

function ActionPanel({ mode }: { mode: StepMode }) {
  if (mode === "normal") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-xl border p-4", toneClass("emerald"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
          <ShieldCheck size={17} />
          normal tool loop
        </div>
        <div className="text-sm leading-relaxed">LLM succeeds, tool_use continues as usual.</div>
      </motion.div>
    );
  }

  if (mode === "max-tokens") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("amber"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <Gauge size={17} />
          escalate output budget
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <CodePill label="before" value="max_tokens=8000" />
          <CodePill label="retry" value="max_tokens=64000" />
        </div>
        <div className="text-sm leading-relaxed">No fake "continue" user message on the first escalation.</div>
      </motion.div>
    );
  }

  if (mode === "prompt-too-long") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("orange"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <History size={17} />
          shrink context, retry once
        </div>
        <CodePill label="recovery" value="messages = reactive_compact(messages)" />
        <div className="text-sm leading-relaxed">If it is still too long after compact, exit cleanly instead of looping forever.</div>
      </motion.div>
    );
  }

  if (mode === "rate-limit") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("blue"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <TimerReset size={17} />
          exponential backoff
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs font-semibold">
          {["0.5s", "1s", "2s"].map((delay) => (
            <div key={delay} className="rounded bg-white/70 px-2 py-2 dark:bg-zinc-950/30">{delay} + jitter</div>
          ))}
        </div>
        <div className="text-sm leading-relaxed">Wait before retrying so the provider has time to recover.</div>
      </motion.div>
    );
  }

  if (mode === "overloaded") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("red"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <RotateCcw size={17} />
          fallback model path
        </div>
        <CodePill label="state" value="consecutive_529 >= 3" />
        <CodePill label="action" value="current_model = FALLBACK_MODEL_ID" />
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
      {CASES.map((item) => (
        <div key={item.id} className={cn("rounded-lg border p-3", toneClass(item.tone as Tone))}>
          <div className="mb-1 text-sm font-semibold">{item.label}</div>
          <div className="text-xs leading-relaxed opacity-80">{item.state}</div>
        </div>
      ))}
      <div className={cn("rounded-xl border p-4", toneClass("emerald"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
          <Repeat2 size={17} />
          continue or exit cleanly
        </div>
        <div className="text-sm leading-relaxed">Every path has a limit, then returns to the normal loop or stops with an explicit error.</div>
      </div>
    </motion.div>
  );
}

function CodePill({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-white/70 p-2 dark:bg-zinc-950/30">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide opacity-70">{label}</div>
      <code className="block min-w-0 whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">{value}</code>
    </div>
  );
}

export default function ErrorRecoveryVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2600 });
  const current = STEPS[vis.currentStep];
  const mode = current.mode;
  const active = activeCase(mode);
  const isSummary = mode === "summary";

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{title || "Error Recovery Paths"}</h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 xl:grid-cols-[1fr_0.9fr_1fr]">
          <Surface title="Failure inbox" icon={<Activity size={20} />} active={mode !== "normal"}>
            <div className="space-y-2">
              <div className={cn("rounded-lg border p-3", toneClass("emerald", mode === "normal"))}>
                <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
                  <ShieldCheck size={15} />
                  success
                </div>
                <div className="text-sm leading-relaxed">No recovery needed; continue to tool loop.</div>
              </div>
              {CASES.map((item) => (
                <CaseCard key={item.id} item={item} active={active === item.id || isSummary} muted={active !== null && active !== item.id && !isSummary} />
              ))}
            </div>
          </Surface>

          <Surface title="RecoveryState" icon={<Workflow size={20} />} active={mode !== "normal"}>
            <RecoveryStatePanel mode={mode} />
          </Surface>

          <Surface title="Recovery action" icon={<Repeat2 size={20} />} active>
            <AnimatePresence mode="wait">
              <ActionPanel key={mode} mode={mode} />
            </AnimatePresence>
          </Surface>
        </div>

        <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300">
          Beginner rule: do not blindly retry; classify the failure, run the smallest recovery, and track whether that recovery was already used.
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
