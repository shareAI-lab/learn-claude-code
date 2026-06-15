"use client";

import { ArchDiagram } from "@/components/architecture/arch-diagram";
import { WhatsNew } from "@/components/diff/whats-new";
import { DesignDecisions } from "@/components/architecture/design-decisions";
import { DocRenderer } from "@/components/docs/doc-renderer";
import { SourceViewer } from "@/components/code/source-viewer";
import { AgentLoopSimulator } from "@/components/simulator/agent-loop-simulator";
import { ExecutionFlow } from "@/components/architecture/execution-flow";
import { SessionVisualization } from "@/components/visualizations";
import { Tabs } from "@/components/ui/tabs";
import { useTranslations } from "@/lib/i18n";

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
}

export function VersionDetailClient({
  version,
  diff,
  source,
  filename,
}: VersionDetailClientProps) {
  const t = useTranslations("version");

  const tabs = [
    { id: "learn", label: t("tab_learn") },
    { id: "simulate", label: t("tab_simulate") },
    { id: "code", label: t("tab_code") },
    { id: "deep-dive", label: t("tab_deep_dive") },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Visualization */}
      <SessionVisualization version={version} />

      {/* Tabbed content */}
      <Tabs tabs={tabs} defaultTab="learn">
        {(activeTab) => (
          <>
            {activeTab === "learn" && <DocRenderer version={version} />}
            {activeTab === "simulate" && (
              <AgentLoopSimulator version={version} />
            )}
            {activeTab === "code" && (
              <SourceViewer source={source} filename={filename} />
            )}
            {activeTab === "deep-dive" && (
              <div className="space-y-8">
                <section>
                  <h2 className="mb-4 text-xl font-semibold">
                    {t("execution_flow")}
                  </h2>
                  <ExecutionFlow version={version} />
                </section>
                <section>
                  <h2 className="mb-4 text-xl font-semibold">
                    {t("architecture")}
                  </h2>
                  <ArchDiagram version={version} />
                </section>
                {diff && <WhatsNew diff={diff} />}
                <DesignDecisions version={version} />
              </div>
            )}
          </>
        )}
      </Tabs>
    </div>
  );
}
