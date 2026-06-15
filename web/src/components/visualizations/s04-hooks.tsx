"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ClipboardList, FileSearch, LogOut, PlugZap, RadioTower, ScrollText, Wrench } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type HookId = "UserPromptSubmit" | "PreToolUse" | "PostToolUse" | "Stop";

const HOOKS: {
  id: HookId;
  when: string;
  callbacks: string[];
  color: "blue" | "amber" | "emerald" | "zinc";
}[] = [
  {
    id: "UserPromptSubmit",
    when: "after input, before LLM",
    callbacks: ["context_inject_hook"],
    color: "blue",
  },
  {
    id: "PreToolUse",
    when: "after tool_use, before handler",
    callbacks: ["permission_hook", "log_hook"],
    color: "amber",
  },
  {
    id: "PostToolUse",
    when: "after handler, before next turn",
    callbacks: ["large_output_hook"],
    color: "emerald",
  },
  {
    id: "Stop",
    when: "before final output",
    callbacks: ["summary_hook"],
    color: "zinc",
  },
];

const STEPS = [
  {
    title: "Hooks Are Registered Outside the Loop",
    desc: "The loop only knows event names; callback behavior lives in the registry.",
    active: null,
  },
  {
    title: "UserPromptSubmit",
    desc: "Input hooks can log, validate, or inject context before the model sees the prompt.",
    active: "UserPromptSubmit" as HookId,
  },
  {
    title: "The Core Loop Still Chooses a Tool",
    desc: "Calling the model and receiving tool_use remains the same as before.",
    active: null,
  },
  {
    title: "PreToolUse",
    desc: "Permission and logging hooks run before the handler touches the workspace.",
    active: "PreToolUse" as HookId,
  },
  {
    title: "PostToolUse",
    desc: "Result hooks inspect output or trigger side effects after execution.",
    active: "PostToolUse" as HookId,
  },
  {
    title: "Stop",
    desc: "Cleanup and summary hooks run when the model stops asking for tools.",
    active: "Stop" as HookId,
  },
] as const;

function toneClass(tone: "blue" | "amber" | "emerald" | "zinc", active = true) {
  if (!active) return "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200";
  if (tone === "emerald") return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200";
  return "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200";
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
          ? "border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-4 flex items-center gap-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            active
              ? "bg-emerald-500 text-white"
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

function HookCard({
  hook,
  active,
}: {
  hook: (typeof HOOKS)[number];
  active: boolean;
}) {
  return (
    <motion.div
      layout
      animate={active ? { y: [0, -2, 0] } : { y: 0 }}
      transition={{ duration: 0.8, repeat: active ? Infinity : 0 }}
      className={cn("rounded-lg border p-3", toneClass(hook.color, active))}
    >
      <div className="mb-1 flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0 truncate font-mono text-sm font-semibold">{hook.id}</div>
        {active && <PlugZap size={16} className="shrink-0" />}
      </div>
      <div className="mb-3 text-xs leading-relaxed opacity-80">{hook.when}</div>
      <div className="flex flex-wrap gap-1.5">
        {hook.callbacks.map((callback) => (
          <span key={callback} className="rounded bg-white/70 px-2 py-1 font-mono text-[11px] dark:bg-zinc-950/30">
            {callback}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

function TurnCard({ step }: { step: number }) {
  const state =
    step <= 1
      ? { title: "User input", body: "Read README.md and summarize it.", icon: <ScrollText size={18} /> }
      : step === 2
        ? { title: "LLM chooses tool", body: "tool_use: read_file({ path: 'README.md' })", icon: <Wrench size={18} /> }
        : step === 3
          ? { title: "Tool waits at pre-hook", body: "permission_hook + log_hook inspect the call.", icon: <FileSearch size={18} /> }
          : step === 4
            ? { title: "Handler returned output", body: "large_output_hook checks result size.", icon: <ClipboardList size={18} /> }
            : { title: "No more tool_use", body: "summary_hook records final session stats.", icon: <LogOut size={18} /> };

  return (
    <motion.div
      key={state.title}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900"
    >
      <div className="mb-2 flex items-center gap-2 text-base font-semibold text-zinc-900 dark:text-zinc-100">
        {state.icon}
        {state.title}
      </div>
      <div className="rounded-lg bg-zinc-50 p-3 font-mono text-xs leading-relaxed text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
        {state.body}
      </div>
    </motion.div>
  );
}

function AuditLog({ step }: { step: number }) {
  const items = [
    "[registry] four hook slots registered",
    "[UserPromptSubmit] working directory logged",
    "[loop] model returned read_file tool_use",
    "[PreToolUse] permission allowed; tool call logged",
    "[PostToolUse] output size checked",
    "[Stop] session used 1 tool call",
  ].slice(0, step + 1);

  return (
    <div className="space-y-2">
      <AnimatePresence mode="popLayout">
        {items.map((item) => (
          <motion.div
            key={item}
            layout
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.2 }}
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
          >
            {item}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

export default function HooksVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const current = STEPS[step];
  const activeHook = current.active;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Hook Workbench"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
          The loop stays boring on purpose: it calls <span className="font-mono">trigger_hooks(event)</span>, and the registry decides what extra logic runs.
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <Surface title="Hook registry" icon={<RadioTower size={20} />} active={step === 0 || activeHook !== null}>
            <div className="grid gap-2 sm:grid-cols-2">
              {HOOKS.map((hook) => (
                <HookCard key={hook.id} hook={hook} active={activeHook === hook.id} />
              ))}
            </div>
          </Surface>

          <Surface title="This turn" icon={<ScrollText size={20} />} active={step >= 1}>
            <div className="space-y-3">
              <TurnCard step={step} />
              <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
                <div className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">Audit log</div>
                <AuditLog step={step} />
              </div>
            </div>
          </Surface>
        </div>

        <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
          Beginner rule: adding behavior means registering a callback, not editing the core model-tool-result loop.
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
