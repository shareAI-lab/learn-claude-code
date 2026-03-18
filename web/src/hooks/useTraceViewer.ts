"use client";

import { useState, useCallback, useEffect } from "react";
import type { ApiTrace } from "@/types/agent-data";

interface TraceViewerReturn {
  trace: ApiTrace | null;
  currentCycle: number;
  totalCycles: number;
  next: () => void;
  prev: () => void;
  goToCycle: (n: number) => void;
  isFirst: boolean;
  isLast: boolean;
  cumulativeTokens: { input: number; output: number };
}

function loadTrace(version: string): Promise<{ default: ApiTrace }> | null {
  if (!/^s\d{2}$/.test(version)) return null;
  return import(`@/data/traces/${version}.json`) as Promise<{ default: ApiTrace }>;
}

export function useTraceViewer(version: string): TraceViewerReturn {
  const [trace, setTrace] = useState<ApiTrace | null>(null);
  const [currentCycle, setCurrentCycle] = useState(0);

  useEffect(() => {
    const loader = loadTrace(version);
    if (loader) {
      loader
        .then((mod) => {
          setTrace(mod.default);
          setCurrentCycle(0);
        })
        .catch(() => {
          setTrace(null);
        });
    } else {
      setTrace(null);
    }
  }, [version]);

  const totalCycles = trace?.cycles.length ?? 0;

  const next = useCallback(() => {
    setCurrentCycle((c) => Math.min(c + 1, totalCycles - 1));
  }, [totalCycles]);

  const prev = useCallback(() => {
    setCurrentCycle((c) => Math.max(c - 1, 0));
  }, []);

  const goToCycle = useCallback(
    (n: number) => setCurrentCycle(Math.max(0, Math.min(n, totalCycles - 1))),
    [totalCycles]
  );

  let inputSum = 0;
  let outputSum = 0;
  if (trace) {
    for (let i = 0; i <= currentCycle && i < trace.cycles.length; i++) {
      inputSum += trace.cycles[i].response.usage.input_tokens;
      outputSum += trace.cycles[i].response.usage.output_tokens;
    }
  }

  return {
    trace,
    currentCycle,
    totalCycles,
    next,
    prev,
    goToCycle,
    isFirst: currentCycle === 0,
    isLast: currentCycle >= totalCycles - 1,
    cumulativeTokens: { input: inputSum, output: outputSum },
  };
}
