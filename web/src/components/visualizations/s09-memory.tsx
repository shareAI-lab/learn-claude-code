"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, CheckCircle2, FileText, Inbox, Search, Sparkles } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type MemoryType = "feedback" | "project" | "reference";

interface MemoryFile {
  id: string;
  type: MemoryType;
  title: string;
  filename: string;
  description: string;
  body: string;
  relevant?: boolean;
}

const MEMORY_FILES: MemoryFile[] = [
  {
    id: "visual-preference",
    type: "feedback",
    title: "Beginner visual preference",
    filename: "lcc_visual_preference.md",
    description: "Use concrete mental models for LCC web pages.",
    body: "Prefer cards, boards, shelves, and workbenches over abstract flowcharts.",
    relevant: true,
  },
  {
    id: "project-path",
    type: "project",
    title: "LCC web paths",
    filename: "lcc_web_paths.md",
    description: "Web app reads root lesson folders and generated JSON.",
    body: "Build from web/, extract content from s01-s20 lesson directories.",
  },
  {
    id: "test-command",
    type: "reference",
    title: "Verification commands",
    filename: "lcc_test_commands.md",
    description: "Useful smoke checks for the course website.",
    body: "Run npm run build, then browser-check /zh/s09 and /zh/s20.",
  },
];

const STEPS = [
  {
    title: "A Fact Worth Keeping",
    desc: "The user says something that should survive future sessions.",
  },
  {
    title: "Stamp It After the Turn",
    desc: "Memory extraction happens after useful work, so the main loop stays focused.",
  },
  {
    title: "Write One Memory File",
    desc: "The durable detail goes into a Markdown file with a readable title and metadata.",
  },
  {
    title: "Update the Catalog",
    desc: "MEMORY.md is the cheap catalog: short enough to keep nearby.",
  },
  {
    title: "A Future Request Arrives",
    desc: "Later, the agent sees a new request and the catalog, not the whole library.",
  },
  {
    title: "Catalog Picks One",
    desc: "Selection chooses the one memory file that is relevant now.",
  },
  {
    title: "Build the Reading Stack",
    desc: "Only the selected memory joins the current request before the model call.",
  },
  {
    title: "Continuity Without Clutter",
    desc: "The answer reflects old context while unrelated memories stay on the shelf.",
  },
] as const;

function typeClass(type: MemoryType): string {
  if (type === "feedback") return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200";
  if (type === "project") return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200";
  return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200";
}

function Surface({
  title,
  icon,
  active,
  children,
  className,
}: {
  title: string;
  icon: React.ReactNode;
  active: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "min-w-0 rounded-lg border p-4 transition-colors",
        active
          ? "border-violet-300 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900",
        className
      )}
    >
      <div className="mb-4 flex min-w-0 items-center gap-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            active
              ? "bg-violet-500 text-white"
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

function QuoteCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 text-lg leading-relaxed text-zinc-700 shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
      {children}
    </div>
  );
}

function CatalogRow({ file, visible, selected }: { file: MemoryFile; visible: boolean; selected: boolean }) {
  if (!visible) return null;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "min-w-0 rounded-lg border p-3",
        selected
          ? "border-violet-300 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/40"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-1 flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0 truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          {file.title}
        </div>
        <span className={cn("shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold", typeClass(file.type))}>
          {file.type}
        </span>
      </div>
      <div className="line-clamp-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
        {file.description}
      </div>
      <div className="mt-2 truncate font-mono text-[11px] text-zinc-400">
        {file.filename}
      </div>
    </motion.div>
  );
}

function MemoryDetail({ file, selected }: { file: MemoryFile; selected: boolean }) {
  return (
    <motion.div
      key={`${file.id}-${selected}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-xl border p-4 shadow-sm",
        selected
          ? "border-violet-300 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/40"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-3 flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <div className="min-w-0">
          <div className="break-words text-base font-bold text-zinc-900 dark:text-zinc-100">
            {file.title}
          </div>
          <div className="mt-1 truncate font-mono text-xs text-zinc-500 dark:text-zinc-400">
            {file.filename}
          </div>
        </div>
        {selected && (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-violet-500 px-2.5 py-1 text-xs font-semibold text-white">
            <CheckCircle2 size={13} />
            selected
          </span>
        )}
      </div>
      <div className="rounded-lg bg-white p-3 text-sm leading-relaxed text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
        {file.body}
      </div>
    </motion.div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-300 px-4 py-8 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
      {label}
    </div>
  );
}

export default function MemoryVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const current = STEPS[step];
  const selectedFile = MEMORY_FILES[0];
  const catalogVisible = step >= 3;
  const futureVisible = step >= 4;
  const selected = step >= 5;
  const injected = step >= 6;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Memory Library"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 grid gap-2 text-sm sm:grid-cols-3">
          {["learn", "catalog", "recall"].map((label, index) => {
            const active =
              (index === 0 && step <= 2) ||
              (index === 1 && (step === 3 || selected)) ||
              (index === 2 && futureVisible);
            return (
              <div
                key={label}
                className={cn(
                  "rounded-lg px-3 py-2 font-medium capitalize",
                  active
                    ? "bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-200"
                    : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
                )}
              >
                {index + 1}. {label}
              </div>
            );
          })}
        </div>

        <div className="grid gap-3 xl:grid-cols-2">
          <Surface title="Session A: learn" icon={<Inbox size={20} />} active={step <= 2}>
            <div className="space-y-3">
              <QuoteCard>"Please keep LCC pages concrete for beginners."</QuoteCard>
              <AnimatePresence>
                {step >= 1 && (
                  <motion.div
                    key="stamp"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
                  >
                    <div className="mb-1 text-base font-semibold">Memory extractor stamp</div>
                    Save a durable preference after the useful work is done.
                  </motion.div>
                )}
              </AnimatePresence>
              <AnimatePresence>
                {step >= 2 && <MemoryDetail file={selectedFile} selected={false} />}
              </AnimatePresence>
            </div>
          </Surface>

          <Surface title="Session B: recall" icon={selected ? <Search size={20} /> : <Sparkles size={20} />} active={futureVisible}>
            <div className="space-y-3">
              {!futureVisible && <EmptyState label="future request has not arrived" />}
              {futureVisible && <QuoteCard>"Continue improving the web lesson visuals."</QuoteCard>}
              {selected && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-lg border border-violet-200 bg-violet-50 p-4 text-sm leading-relaxed text-violet-900 dark:border-violet-900 dark:bg-violet-950/40 dark:text-violet-200"
                >
                  Catalog search selects <span className="font-mono">lcc_visual_preference.md</span>
                </motion.div>
              )}
              {injected && (
                <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
                  <div className="mb-3 text-base font-semibold text-zinc-900 dark:text-zinc-100">
                    Reading stack before LLM
                  </div>
                  <div className="grid gap-2">
                    <div className="rounded-lg bg-zinc-100 px-3 py-2 text-sm dark:bg-zinc-800">current request</div>
                    <div className="rounded-lg bg-violet-100 px-3 py-2 text-sm text-violet-800 dark:bg-violet-900/30 dark:text-violet-200">
                      selected memory detail
                    </div>
                    {step >= 7 && (
                      <div className="rounded-lg bg-emerald-100 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200">
                        answer keeps the user's preference
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Surface>
        </div>

        <Surface
          title=".memory library"
          icon={<BookOpen size={20} />}
          active={catalogVisible || selected}
          className="mt-3"
        >
          <div className="grid min-w-0 gap-3 lg:grid-cols-[320px_minmax(0,1fr)]">
            <div className="min-w-0 rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                <FileText size={16} />
                MEMORY.md catalog
              </div>
              <div className="space-y-2">
                {MEMORY_FILES.map((file, index) => (
                  <CatalogRow
                    key={file.id}
                    file={file}
                    visible={catalogVisible && (index === 0 || step >= 4)}
                    selected={selected && file.relevant === true}
                  />
                ))}
                {!catalogVisible && <EmptyState label="catalog has not been rebuilt yet" />}
              </div>
            </div>

            <div className="min-w-0">
              <div className="mb-3 text-sm font-semibold text-zinc-500 dark:text-zinc-400">
                Memory file preview
              </div>
              {step >= 2 ? (
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(220px,0.85fr)]">
                  <MemoryDetail file={selectedFile} selected={selected} />
                  <div className="space-y-2">
                    {MEMORY_FILES.slice(1).map((file) => (
                      <div
                        key={file.id}
                        className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900"
                      >
                        <div className="flex min-w-0 items-center justify-between gap-2">
                          <div className="min-w-0 truncate text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                            {file.title}
                          </div>
                          <span className={cn("shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold", typeClass(file.type))}>
                            not loaded
                          </span>
                        </div>
                        <div className="mt-1 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
                          {file.description}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState label="no files on the shelf yet" />
              )}
            </div>
          </div>
        </Surface>

        <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
          Beginner rule: the catalog stays cheap and readable; full memory files are borrowed only when the current request needs them.
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
