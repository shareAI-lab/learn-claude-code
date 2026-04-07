import { cn } from "@/lib/utils";

const LAYER_COLORS = {
  core:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  hardening:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  runtime:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  platform:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
} as const;

interface BadgeProps {
  layer: keyof typeof LAYER_COLORS;
  children: React.ReactNode;
  className?: string;
}

export function LayerBadge({ layer, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        LAYER_COLORS[layer],
        className
      )}
    >
      {children}
    </span>
  );
}
