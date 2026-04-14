"use client";

import { lazy, Suspense } from "react";
import { useTranslations } from "@/lib/i18n";
import { isGenericOverviewVersion } from "@/lib/session-assets";
import { GenericSessionOverview } from "./generic-session-overview";

const visualizations: Record<
  string,
  React.LazyExoticComponent<React.ComponentType<{ title?: string }>>
> = {
  s01: lazy(() => import("./s01-agent-loop")),
  s02: lazy(() => import("./s02-tool-dispatch")),
  s03: lazy(() => import("./s03-todo-write")),
  s04: lazy(() => import("./s04-subagent")),
  s05: lazy(() => import("./s05-skill-loading")),
  s06: lazy(() => import("./s06-context-compact")),
};

export function SessionVisualization({ version }: { version: string }) {
  const t = useTranslations("viz");
  const title = t(version);

  if (isGenericOverviewVersion(version)) {
    return <GenericSessionOverview version={version} title={title} />;
  }

  const Component = visualizations[version];
  if (!Component) {
    return <GenericSessionOverview version={version} title={title} />;
  }

  return (
    <Suspense
      fallback={
        <div className="min-h-[500px] animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800" />
      }
    >
      <div className="min-h-[500px]">
        <Component title={title} />
      </div>
    </Suspense>
  );
}
