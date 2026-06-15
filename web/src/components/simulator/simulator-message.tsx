"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { SimStep } from "@/types/agent-data";
import { User, Bot, Terminal, ArrowRight, AlertCircle } from "lucide-react";

interface SimulatorMessageProps {
  step: SimStep;
  index: number;
}

const TYPE_CONFIG: Record<
  string,
  { icon: typeof User; label: string; bgClass: string; borderClass: string }
> = {
  user_message: {
    icon: User,
    label: "User",
    bgClass: "bg-blue-50 dark:bg-blue-950/30",
    borderClass: "border-blue-200 dark:border-blue-800",
  },
  assistant_text: {
    icon: Bot,
    label: "Assistant",
    bgClass: "bg-zinc-50 dark:bg-zinc-900",
    borderClass: "border-zinc-200 dark:border-zinc-700",
  },
  tool_call: {
    icon: Terminal,
    label: "Tool Call",
    bgClass: "bg-amber-50 dark:bg-amber-950/30",
    borderClass: "border-amber-200 dark:border-amber-800",
  },
  tool_result: {
    icon: ArrowRight,
    label: "Tool Result",
    bgClass: "bg-emerald-50 dark:bg-emerald-950/30",
    borderClass: "border-emerald-200 dark:border-emerald-800",
  },
  system_event: {
    icon: AlertCircle,
    label: "System",
    bgClass: "bg-purple-50 dark:bg-purple-950/30",
    borderClass: "border-purple-200 dark:border-purple-800",
  },
};

export function SimulatorMessage({ step, index }: SimulatorMessageProps) {
  const config = TYPE_CONFIG[step.type] || TYPE_CONFIG.assistant_text;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn(
        "rounded-lg border p-3",
        config.bgClass,
        config.borderClass
      )}
    >
      <div className="mb-1.5 flex items-center gap-2">
        <Icon size={14} className="shrink-0 text-[var(--color-text-secondary)]" />
        <span className="text-xs font-medium text-[var(--color-text-secondary)]">
          {config.label}
          {step.toolName && (
            <span className="ml-1.5 font-mono text-[var(--color-text)]">
              {step.toolName}
            </span>
          )}
        </span>
      </div>

      {step.type === "tool_call" || step.type === "tool_result" ? (
        <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-zinc-900 p-2.5 font-mono text-xs leading-relaxed text-zinc-100 dark:bg-zinc-950">
          {step.content || "(empty)"}
        </pre>
      ) : step.type === "system_event" ? (
        <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-purple-900/80 p-2.5 font-mono text-xs leading-relaxed text-purple-100 dark:bg-purple-950">
          {step.content}
        </pre>
      ) : (
        <p className="text-sm leading-relaxed">{step.content}</p>
      )}

      <p className="mt-2 text-xs italic text-[var(--color-text-secondary)]">
        {step.annotation}
      </p>
    </motion.div>
  );
}
