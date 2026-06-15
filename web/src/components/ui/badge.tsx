import { cn } from "@/lib/utils";
import type { AgentLayer } from "@/types/agent-data";

const LAYER_COLORS: Record<string, string> = {
  core:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  hardening:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  runtime:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  platform:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  tools:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  planning:
    "bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300",
  memory:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  concurrency:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  collaboration:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

interface BadgeProps {
  layer: keyof typeof LAYER_COLORS | AgentLayer;
  children: React.ReactNode;
  className?: string;
}

export function LayerBadge({ layer, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        LAYER_COLORS[layer] || LAYER_COLORS.core,
        className
      )}
    >
      {children}
    </span>
  );
}
