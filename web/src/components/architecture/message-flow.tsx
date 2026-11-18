"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";

const FLOW_STEPS = [
  { role: "user", label: "user", color: "bg-blue-500" },
  { role: "assistant", label: "assistant", color: "bg-zinc-600" },
  { role: "tool_call", label: "tool_call", color: "bg-amber-500" },
  { role: "tool_result", label: "tool_result", color: "bg-emerald-500" },
  { role: "assistant", label: "assistant", color: "bg-zinc-600" },
  { role: "tool_call", label: "tool_call", color: "bg-amber-500" },
  { role: "tool_result", label: "tool_result", color: "bg-emerald-500" },
  { role: "assistant", label: "assistant (final)", color: "bg-zinc-600" },
];

export function MessageFlow() {
  const [count, setCount] = useState(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Single self-scheduling timer: only ever one timeout is pending, so a
    // completed cycle can't queue multiple resets that snap the count back.
    const step = (current: number) => {
      const next = current >= FLOW_STEPS.length ? 0 : current + 1;
      setCount(next);
      // Hold on the full array before restarting the cycle.
      const delay = next >= FLOW_STEPS.length ? 1500 : 800;
      timeoutRef.current = setTimeout(() => step(next), delay);
    };

    timeoutRef.current = setTimeout(() => step(0), 800);
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="font-mono text-xs text-[var(--color-text-secondary)]">
          messages[]
        </span>
        <span className="ml-auto rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs tabular-nums dark:bg-zinc-800">
          len={count}
        </span>
      </div>
      <div className="flex flex-wrap gap-1 pb-1">
        {FLOW_STEPS.slice(0, count).map((step, i) => (
          <motion.div
            key={i}
            layout
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.25 }}
            className={`flex shrink-0 items-center rounded-md px-1.5 py-1.5 ${step.color}`}
          >
            <span className="whitespace-nowrap font-mono text-[10px] font-medium text-white">
              {step.label}
            </span>
          </motion.div>
        ))}
        {count === 0 && (
          <div className="flex h-7 items-center text-xs text-[var(--color-text-secondary)]">
            []
          </div>
        )}
      </div>
    </div>
  );
}
