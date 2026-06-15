"use client";

import { type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  Blocks,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  GitBranch,
  Inbox,
  Network,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

type StageId =
  | "intake"
  | "guardrails"
  | "route"
  | "execute"
  | "external"
  | "recover"
  | "append";

const STAGES: {
  id: StageId;
  label: string;
  detail: string;
  icon: ReactNode;
}[] = [
  {
    id: "intake",
    label: "Intake",
    detail: "request, memory, background notes",
    icon: <Inbox size={15} />,
  },
  {
    id: "guardrails",
    label: "Guardrails",
    detail: "permissions, hooks, policy",
    icon: <ShieldCheck size={15} />,
  },
  {
    id: "route",
    label: "Route",
    detail: "choose the right work surface",
    icon: <GitBranch size={15} />,
  },
  {
    id: "execute",
    label: "Execute",
    detail: "local tools, teams, worktrees",
    icon: <Wrench size={15} />,
  },
  {
    id: "external",
    label: "External",
    detail: "MCP toolboxes return results",
    icon: <Blocks size={15} />,
  },
  {
    id: "recover",
    label: "Recover",
    detail: "retry, compact, repair state",
    icon: <Sparkles size={15} />,
  },
  {
    id: "append",
    label: "Append",
    detail: "one transcript stays authoritative",
    icon: <FileText size={15} />,
  },
];

const SURFACES = [
  { label: "background", icon: <Clock3 size={14} />, text: "slow commands can finish later" },
  { label: "team", icon: <Network size={14} />, text: "teammates work through mailboxes" },
  { label: "worktree", icon: <GitBranch size={14} />, text: "risky edits stay isolated" },
  { label: "MCP", icon: <Blocks size={14} />, text: "external tools are normalized" },
];

const STEPS: {
  title: string;
  desc: string;
  stage: StageId;
  used: StageId[];
  packet: {
    request: string;
    carried: string[];
    decision: string;
    result: string;
  };
  transcript: string[];
}[] = [
  {
    title: "A Turn Starts as a Packet",
    desc: "The comprehensive agent first gathers everything the model should see, instead of scattering context across hidden places.",
    stage: "intake",
    used: ["intake"],
    packet: {
      request: "Fix the web lesson visuals and verify the pages.",
      carried: ["recent messages", "relevant memory", "background notes"],
      decision: "build one model-visible input packet",
      result: "ready for a model call",
    },
    transcript: ["user request enters", "memory and notes are attached"],
  },
  {
    title: "Guardrails Check the Packet",
    desc: "Permissions and hooks are not separate side quests; they are the inspection gate before work happens.",
    stage: "guardrails",
    used: ["intake", "guardrails"],
    packet: {
      request: "Edit files, run build, open browser.",
      carried: ["permission mode", "hook output", "workspace rules"],
      decision: "allowed work continues; risky work asks first",
      result: "safe action envelope",
    },
    transcript: ["policy checked", "allowed actions are visible"],
  },
  {
    title: "The Agent Picks Work Surfaces",
    desc: "The model does not need every mechanism at once. It chooses the smallest surface that matches the job.",
    stage: "route",
    used: ["route", "execute", "external"],
    packet: {
      request: "Search code, patch UI, verify rendered pages.",
      carried: ["available tools", "team status", "MCP registry"],
      decision: "local edit first, external tools only when needed",
      result: "work split into clear lanes",
    },
    transcript: ["route: code search", "route: browser check", "route: no teammate needed"],
  },
  {
    title: "Work Runs in Bounded Places",
    desc: "Tools, teammates, and worktrees all produce small result cards, so parallel work does not become one unreadable chat log.",
    stage: "execute",
    used: ["execute", "route"],
    packet: {
      request: "Apply the patch and run the build.",
      carried: ["tool call", "worktree lane", "expected output"],
      decision: "execute, then return summarized results",
      result: "local evidence collected",
    },
    transcript: ["patch applied", "build output summarized"],
  },
  {
    title: "External Results Re-enter the Same Lane",
    desc: "MCP tools expand capability, but they still come back as ordinary tool results the agent can reason over.",
    stage: "external",
    used: ["external", "execute"],
    packet: {
      request: "Use an external source or tool if local context is missing.",
      carried: ["MCP tool name", "structured arguments", "returned artifact"],
      decision: "normalize external output before the next model step",
      result: "outside work is no longer special",
    },
    transcript: ["MCP result received", "result card appended"],
  },
  {
    title: "Recovery Keeps the Turn Understandable",
    desc: "Long context, command errors, and retries are handled as named recovery moves, not as mysterious branches.",
    stage: "recover",
    used: ["recover", "intake"],
    packet: {
      request: "If context or execution gets messy, repair before continuing.",
      carried: ["error text", "retry count", "compact summary"],
      decision: "retry once, compact old detail, keep the reason visible",
      result: "the turn remains legible",
    },
    transcript: ["error classified", "recovery note added", "work resumes"],
  },
  {
    title: "Everything Writes Back to One Transcript",
    desc: "The big lesson is boring in the best way: all mechanisms eventually append evidence to the same source of truth.",
    stage: "append",
    used: ["append", "intake"],
    packet: {
      request: "Report what changed and what was verified.",
      carried: ["tool evidence", "browser checks", "remaining risks"],
      decision: "answer from the transcript, not from memory alone",
      result: "next turn has a clean starting point",
    },
    transcript: ["tests pass", "visual checks recorded", "final answer drafted"],
  },
];

function StageNode({
  stage,
  index,
  currentIndex,
}: {
  stage: (typeof STAGES)[number];
  index: number;
  currentIndex: number;
}) {
  const active = index === currentIndex;
  const done = index < currentIndex;

  return (
    <motion.div
      layout
      animate={active ? { y: [0, -2, 0] } : { y: 0 }}
      transition={{ duration: 0.8, repeat: active ? Infinity : 0 }}
      className={cn(
        "min-w-0 rounded-lg border p-3 transition-colors",
        active
          ? "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/35 dark:text-blue-200"
          : done
            ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200"
            : "border-zinc-200 bg-white text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
      )}
    >
      <div className="flex min-w-0 items-center gap-2">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
            active
              ? "bg-blue-500 text-white"
              : done
                ? "bg-emerald-500 text-white"
                : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
          )}
        >
          {done ? <CheckCircle2 size={15} /> : stage.icon}
        </span>
        <div className="min-w-0">
          <div className="break-words text-sm font-semibold">
            {index + 1}. {stage.label}
          </div>
          <div className="break-words text-[11px] leading-snug opacity-80">{stage.detail}</div>
        </div>
      </div>
    </motion.div>
  );
}

function PacketLine({
  label,
  value,
  tone = "zinc",
}: {
  label: string;
  value: string;
  tone?: "zinc" | "blue" | "emerald";
}) {
  const toneClass = {
    zinc: "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200",
    blue: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/35 dark:text-blue-200",
    emerald:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/35 dark:text-emerald-200",
  }[tone];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.22 }}
      className={cn("min-w-0 rounded-md border px-3 py-2 shadow-sm", toneClass)}
    >
      <div className="font-mono text-[10px] uppercase tracking-normal opacity-70">{label}</div>
      <div className="mt-1 break-words text-sm font-medium leading-snug">{value}</div>
    </motion.div>
  );
}

export default function ComprehensiveVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2800 });
  const step = STEPS[vis.currentStep];
  const currentStageIndex = STAGES.findIndex((stage) => stage.id === step.stage);

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Comprehensive Agent Turn"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 lg:grid-cols-[0.9fr_1.2fr]">
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              <Bot size={16} />
              One-turn journey
            </div>
            <div className="space-y-2">
              {STAGES.map((stage, index) => (
                <StageNode
                  key={stage.id}
                  stage={stage}
                  index={index}
                  currentIndex={currentStageIndex}
                />
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                  <Archive size={16} />
                  Turn packet
                </div>
                <span className="w-fit rounded-md bg-white px-2 py-1 font-mono text-[11px] text-zinc-500 dark:bg-zinc-900 dark:text-zinc-300">
                  step {vis.currentStep + 1}/{STEPS.length}
                </span>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25 }}
                  className="space-y-3"
                >
                  <PacketLine label="request" value={step.packet.request} tone="blue" />

                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="rounded-md border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900">
                      <div className="font-mono text-[10px] uppercase tracking-normal text-zinc-500 dark:text-zinc-400">
                        carried context
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {step.packet.carried.map((item) => (
                          <span
                            key={item}
                            className="max-w-full break-words rounded bg-zinc-100 px-2 py-1 text-[11px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                    <PacketLine label="decision" value={step.packet.decision} />
                  </div>

                  <PacketLine label="result" value={step.packet.result} tone="emerald" />
                </motion.div>
              </AnimatePresence>
            </div>

            <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                <FileText size={15} />
                Source-of-truth transcript
              </div>
              <div className="space-y-2">
                <AnimatePresence mode="popLayout">
                  {step.transcript.map((item) => (
                    <motion.div
                      key={item}
                      layout
                      initial={{ opacity: 0, x: 12 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      transition={{ duration: 0.22 }}
                      className="break-words rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                    >
                      {item}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {SURFACES.map((surface) => (
            <div
              key={surface.label}
              className="min-w-0 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/70"
            >
              <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-zinc-100 text-zinc-500 dark:bg-zinc-900 dark:text-zinc-300">
                  {surface.icon}
                </span>
                <span className="break-words">{surface.label}</span>
              </div>
              <div className="mt-2 break-words text-[11px] leading-snug text-zinc-500 dark:text-zinc-400">
                {surface.text}
              </div>
            </div>
          ))}
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
          stepTitle={step.title}
          stepDescription={step.desc}
        />
      </div>
    </section>
  );
}
