"use client";

import { lazy, Suspense } from "react";
import { useTranslations } from "@/lib/i18n";

const visualizations: Record<
  string,
  React.LazyExoticComponent<React.ComponentType<{ title?: string }>>
> = {
  s01: lazy(() => import("./s01-agent-loop")),
  s02: lazy(() => import("./s02-tool-dispatch")),
  s03: lazy(() => import("./s03-permission")),
  s04: lazy(() => import("./s04-hooks")),
  s05: lazy(() => import("./s03-todo-write")),
  s06: lazy(() => import("./s04-subagent")),
  s07: lazy(() => import("./s05-skill-loading")),
  s08: lazy(() => import("./s06-context-compact")),
  s09: lazy(() => import("./s09-memory")),
  s10: lazy(() => import("./s10-system-prompt")),
  s11: lazy(() => import("./s11-error-recovery")),
  s12: lazy(() => import("./s07-task-system")),
  s13: lazy(() => import("./s08-background-tasks")),
  s14: lazy(() => import("./s14-cron-scheduler")),
  s15: lazy(() => import("./s09-agent-teams")),
  s16: lazy(() => import("./s10-team-protocols")),
  s17: lazy(() => import("./s11-autonomous-agents")),
  s18: lazy(() => import("./s12-worktree-task-isolation")),
  s19: lazy(() => import("./s19-mcp-tools")),
  s20: lazy(() => import("./s20-comprehensive")),
};

export function SessionVisualization({ version }: { version: string }) {
  const t = useTranslations("viz");
  const Component = visualizations[version];
  if (!Component) return null;
  return (
    <Suspense
      fallback={
        <div className="min-h-[500px] animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800" />
      }
    >
      <div className="min-h-[500px]">
        <Component title={t(version)} />
      </div>
    </Suspense>
  );
}
