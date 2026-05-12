"use client";

import Link from "next/link";
import { ArchDiagram } from "@/components/architecture/arch-diagram";
import { WhatsNew } from "@/components/diff/whats-new";
import { DesignDecisions } from "@/components/architecture/design-decisions";
import { DocRenderer } from "@/components/docs/doc-renderer";
import { SourceViewer } from "@/components/code/source-viewer";
import { AgentLoopSimulator } from "@/components/simulator/agent-loop-simulator";
import { ExecutionFlow } from "@/components/architecture/execution-flow";
import { SessionVisualization } from "@/components/visualizations";
import { Card } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { useLocale, useTranslations } from "@/lib/i18n";

interface GuideData {
  focus: string;
  confusion: string;
  goal: string;
}

interface BridgeDoc {
  slug: string;
  kind: "map" | "mechanism";
  title: string;
  summary: Record<"zh" | "en" | "ja", string>;
  fallbackLocale: string | null;
}

interface VersionDetailClientProps {
  version: string;
  diff: {
    from: string;
    to: string;
    newClasses: string[];
    newFunctions: string[];
    newTools: string[];
    locDelta: number;
  } | null;
  source: string;
  filename: string;
  guideData: GuideData | null;
  bridgeDocs: BridgeDoc[];
  locale: string;
}

export function VersionDetailClient({
  version,
  diff,
  source,
  filename,
  guideData,
  bridgeDocs,
  locale: serverLocale,
}: VersionDetailClientProps) {
  const t = useTranslations("version");
  const locale = useLocale() || serverLocale;

  const tabs = [
    { id: "learn", label: t("tab_learn") },
    { id: "code", label: t("tab_code") },
    { id: "deep-dive", label: t("tab_deep_dive") },
  ];

  return (
    <Tabs tabs={tabs} defaultTab="learn">
      {(activeTab) => (
        <>
          {activeTab === "learn" && <DocRenderer version={version} />}

          {activeTab === "code" && (
            <SourceViewer source={source} filename={filename} />
          )}

          {activeTab === "deep-dive" && (
            <div className="space-y-8">
              {/* Interactive visualization */}
              <SessionVisualization version={version} />

              {/* Execution flow + Architecture side by side */}
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("execution_flow")}
                  </h3>
                  <ExecutionFlow version={version} />
                </section>
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("architecture")}
                  </h3>
                  <ArchDiagram version={version} />
                </section>
              </div>

              {/* Simulator */}
              <AgentLoopSimulator version={version} />

              {/* Diff / Design decisions */}
              {diff && <WhatsNew diff={diff} />}
              <DesignDecisions version={version} />

              {/* Guide cards */}
              {guideData && (
                <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <Card className="border-emerald-200/70 bg-gradient-to-br from-emerald-50 via-white to-emerald-100/60 p-5 dark:border-emerald-900/70 dark:from-emerald-950/40 dark:via-zinc-950 dark:to-zinc-900">
                    <p className="text-xs uppercase tracking-widest text-emerald-500/80 dark:text-emerald-300/70">
                      {t("guide_focus_title")}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {guideData.focus}
                    </p>
                  </Card>
                  <Card className="border-amber-200/70 bg-gradient-to-br from-amber-50 via-white to-amber-100/70 p-5 dark:border-amber-900/70 dark:from-amber-950/30 dark:via-zinc-950 dark:to-zinc-900">
                    <p className="text-xs uppercase tracking-widest text-amber-500/80 dark:text-amber-300/70">
                      {t("guide_confusion_title")}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {guideData.confusion}
                    </p>
                  </Card>
                  <Card className="border-sky-200/70 bg-gradient-to-br from-sky-50 via-white to-sky-100/60 p-5 dark:border-sky-900/70 dark:from-sky-950/30 dark:via-zinc-950 dark:to-zinc-900">
                    <p className="text-xs uppercase tracking-widest text-sky-500/80 dark:text-sky-300/70">
                      {t("guide_goal_title")}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {guideData.goal}
                    </p>
                  </Card>
                </section>
              )}

              {/* Bridge doc links */}
              {bridgeDocs.length > 0 && (
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("bridge_docs_title")}
                  </h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {t("bridge_docs_intro")}
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {bridgeDocs.map((doc) => (
                      <Link
                        key={doc.slug}
                        href={`/${locale}/docs/${doc.slug}`}
                        className="group rounded-xl border border-zinc-200/80 bg-white p-4 transition-colors hover:border-zinc-300 dark:border-zinc-800/80 dark:bg-zinc-900 dark:hover:border-zinc-700"
                      >
                        <div className="flex items-center gap-2">
                          <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                            {doc.kind === "map"
                              ? t("bridge_docs_kind_map")
                              : t("bridge_docs_kind_mechanism")}
                          </span>
                          {doc.fallbackLocale && (
                            <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-300">
                              {doc.fallbackLocale}
                            </span>
                          )}
                        </div>
                        <h4 className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                          {doc.title}
                        </h4>
                        <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                          {doc.summary[locale as "zh" | "en" | "ja"] ?? doc.summary.en}
                        </p>
                      </Link>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </>
      )}
    </Tabs>
  );
}
