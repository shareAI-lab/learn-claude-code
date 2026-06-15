"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Boxes, Brain, CheckCircle2, FileText, KeyRound, Library, Rocket, Wrench } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Runtime State Arrives",
    desc: "The prompt is not a fixed paragraph; it starts from workspace, tools, memory, and skills.",
    mode: "state",
  },
  {
    title: "Section Shelf Selects Owners",
    desc: "Each subsystem owns one prompt section, so a bad rule has a place to debug.",
    mode: "sections",
  },
  {
    title: "Context Key Checks the Cache",
    desc: "The same runtime state produces the same deterministic cache key.",
    mode: "cache-miss",
  },
  {
    title: "Prompt Is Assembled",
    desc: "Selected sections are joined into one system prompt that the LLM can read.",
    mode: "assemble",
  },
  {
    title: "Same Key Reuses the Prompt",
    desc: "If nothing changed, the runtime skips assembly and reuses the cached prompt.",
    mode: "cache-hit",
  },
  {
    title: "LLM Sees the Built Prompt",
    desc: "The model receives a traceable product of runtime state, not a stale hardcoded string.",
    mode: "llm",
  },
] as const;

const SOURCES = [
  { id: "workspace", label: "workspace", value: "/repo", icon: <Boxes size={16} />, tone: "blue" },
  { id: "tools", label: "tools", value: "bash, read_file", icon: <Wrench size={16} />, tone: "emerald" },
  { id: "memory", label: "memory", value: "enabled", icon: <Brain size={16} />, tone: "amber" },
  { id: "skills", label: "skills", value: "code-review", icon: <Library size={16} />, tone: "violet" },
] as const;

const SECTIONS = [
  { id: "identity", title: "identity", body: "You are a helpful coding agent.", owner: "core" },
  { id: "tools", title: "tools", body: "Available tools: bash, read_file.", owner: "tool registry" },
  { id: "workspace", title: "workspace", body: "Current workspace: /repo.", owner: "runtime" },
  { id: "memory", title: "memory + skills", body: "Load memory index and code-review skill.", owner: "context loader" },
] as const;

type StepMode = (typeof STEPS)[number]["mode"];
type Tone = "blue" | "emerald" | "amber" | "violet" | "zinc";

function toneClass(tone: Tone, active = true) {
  if (!active) return "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200";
  if (tone === "emerald") return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200";
  if (tone === "violet") return "border-violet-200 bg-violet-50 text-violet-800 dark:border-violet-900 dark:bg-violet-950/40 dark:text-violet-200";
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
          ? "border-blue-300 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-4 flex min-w-0 items-center gap-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            active ? "bg-blue-500 text-white" : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
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

function SourceCard({
  source,
  active,
}: {
  source: (typeof SOURCES)[number];
  active: boolean;
}) {
  return (
    <motion.div layout animate={active ? { y: -1 } : { y: 0 }} className={cn("rounded-lg border p-3", toneClass(source.tone as Tone, active))}>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
        {source.icon}
        {source.label}
      </div>
      <code className="block min-w-0 whitespace-pre-wrap break-words rounded bg-white/70 px-2 py-1 font-mono text-xs dark:bg-zinc-950/30">
        {source.value}
      </code>
    </motion.div>
  );
}

function SectionCard({
  section,
  active,
  assembled,
}: {
  section: (typeof SECTIONS)[number];
  active: boolean;
  assembled: boolean;
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "min-w-0 rounded-lg border p-3",
        active || assembled ? toneClass("emerald") : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-1 flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0 break-words font-mono text-sm font-semibold leading-snug">{section.title}</div>
        {(active || assembled) && <CheckCircle2 size={15} className="shrink-0" />}
      </div>
      <div className="mb-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">owner: {section.owner}</div>
      <div className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">{section.body}</div>
    </motion.div>
  );
}

function CachePanel({ mode }: { mode: StepMode }) {
  const isHit = mode === "cache-hit";
  const isActive = mode === "cache-miss" || mode === "cache-hit";

  return (
    <div className={cn("rounded-lg border p-3", toneClass(isHit ? "emerald" : "amber", isActive))}>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
        <KeyRound size={16} />
        context key
      </div>
      <code className="block min-w-0 whitespace-pre-wrap break-words rounded bg-white/70 p-2 font-mono text-xs dark:bg-zinc-950/30">
        json.dumps(context, sort_keys=True)
      </code>
      <div className="mt-2 text-sm font-semibold">{isHit ? "cache hit: reuse prompt" : isActive ? "cache miss: assemble sections" : "waiting for state"}</div>
    </div>
  );
}

function PromptPreview({ mode }: { mode: StepMode }) {
  const assembled = mode === "assemble" || mode === "cache-hit" || mode === "llm";

  if (!assembled) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-4 py-8 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
        prompt not built yet
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
      {SECTIONS.map((section) => (
        <div key={section.id} className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <div className="mb-1 font-mono text-xs font-semibold text-blue-700 dark:text-blue-300">[{section.title}]</div>
          <div className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">{section.body}</div>
        </div>
      ))}
      <div className={cn("rounded-xl border p-4", toneClass(mode === "llm" ? "blue" : "zinc"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
          <Rocket size={17} />
          {mode === "llm" ? "sent to LLM" : "system prompt ready"}
        </div>
        <div className="text-sm leading-relaxed">Traceable prompt text, assembled from named runtime owners.</div>
      </div>
    </motion.div>
  );
}

export default function SystemPromptVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2600 });
  const current = STEPS[vis.currentStep];
  const mode = current.mode;
  const sourceActive = mode === "state" || mode === "sections" || mode === "cache-miss";
  const sectionsActive = mode === "sections" || mode === "assemble";
  const promptActive = mode === "assemble" || mode === "cache-hit" || mode === "llm";

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{title || "Runtime Prompt Assembly"}</h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 xl:grid-cols-[0.95fr_1.1fr_0.95fr]">
          <Surface title="Runtime context" icon={<Boxes size={20} />} active={sourceActive}>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
              {SOURCES.map((source) => (
                <SourceCard key={source.id} source={source} active={sourceActive} />
              ))}
            </div>
          </Surface>

          <Surface title="Section shelf + cache" icon={<FileText size={20} />} active={sectionsActive || mode === "cache-miss" || mode === "cache-hit"}>
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                {SECTIONS.map((section) => (
                  <SectionCard key={section.id} section={section} active={sectionsActive} assembled={promptActive} />
                ))}
              </div>
              <CachePanel mode={mode} />
            </div>
          </Surface>

          <Surface title="System prompt" icon={<Rocket size={20} />} active={promptActive}>
            <AnimatePresence mode="wait">
              <PromptPreview key={mode} mode={mode} />
            </AnimatePresence>
          </Surface>
        </div>

        <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300">
          Beginner rule: system prompts should be assembled from named runtime facts, then cached only when those facts are unchanged.
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
