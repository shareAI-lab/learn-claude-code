"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Cable, CheckCircle2, PlugZap, Search, Server, Wrench } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Need a New Tool",
    desc: "The agent starts with built-in tools, then notices this task needs an outside capability.",
    active: "need",
  },
  {
    title: "Plug In a Server",
    desc: "MCP is easiest to picture as plugging a named toolbox into the agent workbench.",
    active: "server",
  },
  {
    title: "Read the Tool Labels",
    desc: "The server advertises schemas, so the agent can see what each tool expects.",
    active: "discover",
  },
  {
    title: "Name the Tools Clearly",
    desc: "Each external tool gets a namespaced label, which avoids collisions with built-ins.",
    active: "belt",
  },
  {
    title: "Use It Like Any Tool",
    desc: "Once on the tool belt, the MCP tool follows the same call-and-result rhythm.",
    active: "call",
  },
  {
    title: "Result Comes Back",
    desc: "The returned data is just another tool result for the next model turn.",
    active: "result",
  },
] as const;

const BUILT_INS = ["read_file", "edit_file", "bash"];
const SERVER_TOOLS = [
  { raw: "search", namespaced: "mcp__docs__search" },
  { raw: "fetch", namespaced: "mcp__docs__fetch" },
  { raw: "list_sections", namespaced: "mcp__docs__list_sections" },
];

function ToolChip({
  label,
  active,
  external,
}: {
  label: string;
  active?: boolean;
  external?: boolean;
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "min-w-0 max-w-full break-all rounded-md border px-2 py-1.5 font-mono text-[11px] leading-snug",
        active
          ? "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200"
          : external
            ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
            : "border-zinc-200 bg-white text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
      )}
    >
      {label}
    </motion.div>
  );
}

function Shelf({
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
        "rounded-lg border p-3 transition-colors",
        active
          ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-3 flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
            active
              ? "bg-emerald-500 text-white"
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

export default function McpToolsVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const current = STEPS[step];
  const connected = step >= 1;
  const discovered = step >= 2;
  const namespaced = step >= 3;
  const called = step >= 4;
  const returned = step >= 5;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "MCP Tool Bridge"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr_1fr]">
          <Shelf
            title="Built-in belt"
            icon={<Wrench size={15} />}
            active={current.active === "need"}
          >
            <div className="space-y-2">
              {BUILT_INS.map((tool) => (
                <ToolChip key={tool} label={tool} />
              ))}
              <div className="rounded-md border border-dashed border-zinc-300 px-3 py-5 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
                limited to local skills
              </div>
            </div>
          </Shelf>

          <div className="space-y-3">
            <Shelf
              title="External toolbox"
              icon={<Server size={15} />}
              active={current.active === "server" || current.active === "discover"}
            >
              <div className="flex items-center justify-between rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs dark:border-zinc-700 dark:bg-zinc-800">
                <div className="flex items-center gap-2 font-mono text-zinc-700 dark:text-zinc-200">
                  <Cable size={14} />
                  docs-server
                </div>
                <span
                  className={cn(
                    "rounded px-2 py-0.5 text-[10px] font-semibold",
                    connected
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                      : "bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-300"
                  )}
                >
                  {connected ? "connected" : "offline"}
                </span>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <AnimatePresence>
                  {discovered ? (
                    SERVER_TOOLS.map((tool) => (
                      <ToolChip key={tool.raw} label={tool.raw} external />
                    ))
                  ) : (
                    <motion.div
                      key="no-schema"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="col-span-full rounded-md border border-dashed border-zinc-300 px-3 py-5 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400"
                    >
                      schemas hidden until connected
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </Shelf>

            <Shelf
              title="Agent workbench"
              icon={<PlugZap size={15} />}
              active={current.active === "belt" || current.active === "call"}
            >
              <div className="grid gap-2 sm:grid-cols-2">
                <AnimatePresence>
                  {namespaced ? (
                    SERVER_TOOLS.slice(0, 2).map((tool, index) => (
                      <ToolChip
                        key={tool.namespaced}
                        label={tool.namespaced}
                        active={called && index === 0}
                      />
                    ))
                  ) : (
                    <motion.div
                      key="empty-belt"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="col-span-full rounded-md border border-dashed border-zinc-300 px-3 py-4 text-center text-xs text-zinc-500 dark:border-zinc-700 dark:text-zinc-400"
                    >
                      no MCP tools on the belt
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </Shelf>
          </div>

          <Shelf
            title="Call notebook"
            icon={called ? <Search size={15} /> : <CheckCircle2 size={15} />}
            active={current.active === "call" || current.active === "result"}
          >
            <div className="space-y-2">
              <motion.div
                animate={called && !returned ? { y: [0, -2, 0] } : { y: 0 }}
                transition={{ duration: 1, repeat: called && !returned ? Infinity : 0 }}
              className="break-all rounded-md border border-zinc-200 bg-zinc-50 p-3 font-mono text-[11px] leading-snug text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
              >
                {called ? "mcp__docs__search({ query })" : "waiting for a tool call"}
              </motion.div>
              <AnimatePresence>
                {returned && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="break-words rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs leading-snug text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
                  >
                    tool_result: 3 relevant docs found
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </Shelf>
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
