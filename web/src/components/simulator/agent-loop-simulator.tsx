"use client";

import { useRef, useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { useTranslations } from "@/lib/i18n";
import { useSimulator } from "@/hooks/useSimulator";
import { SimulatorControls } from "./simulator-controls";
import { SimulatorMessage } from "./simulator-message";
import type { Scenario } from "@/types/agent-data";

const scenarioModules: Record<string, () => Promise<{ default: Scenario }>> = {
  s01: () => import("@/data/scenarios/s01.json") as Promise<{ default: Scenario }>,
  s02: () => import("@/data/scenarios/s02.json") as Promise<{ default: Scenario }>,
  s03: () => import("@/data/scenarios/s03.json") as Promise<{ default: Scenario }>,
  s04: () => import("@/data/scenarios/s04.json") as Promise<{ default: Scenario }>,
  s05: () => import("@/data/scenarios/s05.json") as Promise<{ default: Scenario }>,
  s06: () => import("@/data/scenarios/s06.json") as Promise<{ default: Scenario }>,
  s07: () => import("@/data/scenarios/s07.json") as Promise<{ default: Scenario }>,
  s08: () => import("@/data/scenarios/s08.json") as Promise<{ default: Scenario }>,
  s09: () => import("@/data/scenarios/s09.json") as Promise<{ default: Scenario }>,
  s10: () => import("@/data/scenarios/s10.json") as Promise<{ default: Scenario }>,
  s11: () => import("@/data/scenarios/s11.json") as Promise<{ default: Scenario }>,
  s12: () => import("@/data/scenarios/s12.json") as Promise<{ default: Scenario }>,
  s13: () => import("@/data/scenarios/s13.json") as Promise<{ default: Scenario }>,
  s14: () => import("@/data/scenarios/s14.json") as Promise<{ default: Scenario }>,
  s15: () => import("@/data/scenarios/s15.json") as Promise<{ default: Scenario }>,
  s16: () => import("@/data/scenarios/s16.json") as Promise<{ default: Scenario }>,
  s17: () => import("@/data/scenarios/s17.json") as Promise<{ default: Scenario }>,
  s18: () => import("@/data/scenarios/s18.json") as Promise<{ default: Scenario }>,
  s19: () => import("@/data/scenarios/s19.json") as Promise<{ default: Scenario }>,
  s20: () => import("@/data/scenarios/s20.json") as Promise<{ default: Scenario }>,
};

interface AgentLoopSimulatorProps {
  version: string;
}

export function AgentLoopSimulator({ version }: AgentLoopSimulatorProps) {
  const t = useTranslations("version");
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const loader = scenarioModules[version];
    setScenario(null);

    if (!loader) {
      return () => {
        cancelled = true;
      };
    }

    loader()
      .then((mod) => {
        if (!cancelled) setScenario(mod.default);
      })
      .catch(() => {
        if (!cancelled) setScenario(null);
      });

    return () => {
      cancelled = true;
    };
  }, [version]);

  const sim = useSimulator(scenario?.steps ?? []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [sim.visibleSteps.length]);

  if (!scenario) {
    return (
      <section>
        <h2 className="mb-2 text-xl font-semibold">{t("simulator")}</h2>
        <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] p-6 text-sm text-[var(--color-text-secondary)]">
          Simulator scenario is not available for this lesson yet.
        </div>
      </section>
    );
  }

  return (
    <section>
      <h2 className="mb-2 text-xl font-semibold">{t("simulator")}</h2>
      <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
        {scenario.description}
      </p>

      <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
        <div className="border-b border-[var(--color-border)] bg-zinc-50 px-4 py-3 dark:bg-zinc-900">
          <SimulatorControls
            isPlaying={sim.isPlaying}
            isComplete={sim.isComplete}
            currentIndex={sim.currentIndex}
            totalSteps={sim.totalSteps}
            speed={sim.speed}
            onPlay={sim.play}
            onPause={sim.pause}
            onStep={sim.stepForward}
            onReset={sim.reset}
            onSpeedChange={sim.setSpeed}
          />
        </div>

        <div
          ref={scrollRef}
          className="flex max-h-[500px] min-h-[200px] flex-col gap-3 overflow-y-auto p-4"
        >
          {sim.visibleSteps.length === 0 && (
            <div className="flex flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">
              Press Play or Step to begin
            </div>
          )}
          <AnimatePresence mode="popLayout">
            {sim.visibleSteps.map((step, i) => (
              <SimulatorMessage key={i} step={step} index={i} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
