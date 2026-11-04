"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";

type BlockType = "user" | "assistant" | "tool_result";

interface ContextBlock {
  id: string;
  type: BlockType;
  label: string;
  tokens: number;
}

const BLOCK_COLORS: Record<BlockType, string> = {
  user: "bg-blue-500",
  assistant: "bg-zinc-500 dark:bg-zinc-600",
  tool_result: "bg-emerald-500",
};

const BLOCK_LABELS: Record<BlockType, string> = {
  user: "USR",
  assistant: "AST",
  tool_result: "TRL",
};

function generateBlocks(count: number, seed: number): ContextBlock[] {
  const types: BlockType[] = ["user", "assistant", "tool_result"];
  const blocks: ContextBlock[] = [];
  for (let i = 0; i < count; i++) {
    const typeIndex = (i + seed) % 3;
    const type = types[typeIndex];
    const tokens = type === "tool_result" ? 4000 + (i % 3) * 1000 : 1500 + (i % 4) * 500;
    blocks.push({
      id: `b-${seed}-${i}`,
      type,
      label: `${BLOCK_LABELS[type]} ${i + 1}`,
      tokens,
    });
  }
  return blocks;
}

const MAX_TOKENS = 100000;
const WINDOW_HEIGHT = 350;

interface StepState {
  blocks: { id: string; type: BlockType; label: string; heightPx: number; compressed?: boolean }[];
  tokenCount: number;
  fillPercent: number;
  compressionLabel: string | null;
}

function computeStepState(step: number): StepState {
  switch (step) {
    case 0: {
      const raw = generateBlocks(8, 0);
      const tokenCount = 30000;
      const totalRawTokens = raw.reduce((a, b) => a + b.tokens, 0);
      const blocks = raw.map((b) => ({
        ...b,
        heightPx: Math.max(16, (b.tokens / totalRawTokens) * WINDOW_HEIGHT * 0.3),
      }));
      return { blocks, tokenCount, fillPercent: 30, compressionLabel: null };
    }
    case 1: {
      const raw = generateBlocks(16, 0);
      const tokenCount = 60000;
      const totalRawTokens = raw.reduce((a, b) => a + b.tokens, 0);
      const blocks = raw.map((b) => ({
        ...b,
        heightPx: Math.max(12, (b.tokens / totalRawTokens) * WINDOW_HEIGHT * 0.6),
      }));
      return { blocks, tokenCount, fillPercent: 60, compressionLabel: null };
    }
    case 2: {
      const raw = generateBlocks(20, 0);
      const tokenCount = 80000;
      const totalRawTokens = raw.reduce((a, b) => a + b.tokens, 0);
      const blocks = raw.map((b) => ({
        ...b,
        heightPx: Math.max(10, (b.tokens / totalRawTokens) * WINDOW_HEIGHT * 0.8),
      }));
      return { blocks, tokenCount, fillPercent: 80, compressionLabel: null };
    }
    case 3: {
      const raw = generateBlocks(20, 0);
      const tokenCount = 60000;
      const totalRawTokens = raw.reduce((a, b) => a + b.tokens, 0);
      const blocks = raw.map((b) => ({
        ...b,
        heightPx:
          b.type === "tool_result"
            ? 6
            : Math.max(12, (b.tokens / totalRawTokens) * WINDOW_HEIGHT * 0.6),
        compressed: b.type === "tool_result",
      }));
      return {
        blocks,
        tokenCount,
        fillPercent: 60,
        compressionLabel: "MICRO-COMPACT",
      };
    }
    case 4: {
      const raw = generateBlocks(24, 1);
      const tokenCount = 85000;
      const totalRawTokens = raw.reduce((a, b) => a + b.tokens, 0);
      const blocks = raw.map((b) => ({
        ...b,
        heightPx: Math.max(10, (b.tokens / totalRawTokens) * WINDOW_HEIGHT * 0.85),
      }));
      return { blocks, tokenCount, fillPercent: 85, compressionLabel: null };
    }
    case 5: {
      const tokenCount = 25000;
      const summaryBlock = {
        id: "auto-summary",
        type: "assistant" as BlockType,
        label: "SUMMARY",
        heightPx: 40,
        compressed: false,
      };
      const recentBlocks = generateBlocks(4, 2).map((b) => ({
        ...b,
        heightPx: 20,
      }));
      return {
        blocks: [summaryBlock, ...recentBlocks],
        tokenCount,
        fillPercent: 25,
        compressionLabel: "AUTO-COMPACT",
      };
    }
    case 6: {
      const tokenCount = 8000;
      const compactBlock = {
        id: "compact-summary",
        type: "assistant" as BlockType,
        label: "COMPACT SUMMARY",
        heightPx: 24,
        compressed: false,
      };
      return {
        blocks: [compactBlock],
        tokenCount,
        fillPercent: 8,
        compressionLabel: "/compact",
      };
    }
    default:
      return { blocks: [], tokenCount: 0, fillPercent: 0, compressionLabel: null };
  }
}

const STEPS = [
  {
    title: "Growing Context",
    description:
      "The context window holds the conversation. Each API call adds more messages.",
  },
  {
    title: "Context Growing",
    description:
      "As the agent works, messages accumulate. The context window fills up.",
  },
  {
    title: "Approaching Limit",
    description:
      "Old tool_results are the biggest consumers. Micro-compact targets these first.",
  },
  {
    title: "Stage 1: Micro-Compact",
    description:
      "Replace old tool_results with short summaries. Automatic, transparent to the model.",
  },
  {
    title: "Still Growing",
    description:
      "Work continues. Context grows again toward the threshold...",
  },
  {
    title: "Stage 2: Auto-Compact",
    description:
      "Entire conversation summarized into a compact block. Triggered at token threshold.",
  },
  {
    title: "Stage 3: /compact",
    description:
      "User-triggered, most aggressive. Three layers of strategic forgetting enable infinite sessions.",
  },
];

const COMPRESSION_LAYERS = [
  {
    label: "Micro",
    full: "MICRO-COMPACT",
    trigger: "old tool_result",
    action: "shrink bulky outputs",
    step: 3,
    classes:
      "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200",
  },
  {
    label: "Auto",
    full: "AUTO-COMPACT",
    trigger: "token threshold",
    action: "summarize the conversation",
    step: 5,
    classes:
      "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200",
  },
  {
    label: "Manual",
    full: "/compact",
    trigger: "user command",
    action: "keep one compact summary",
    step: 6,
    classes:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200",
  },
];

export default function ContextCompact({ title }: { title?: string }) {
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });

  const state = useMemo(() => computeStepState(currentStep), [currentStep]);

  const fillColor =
    state.fillPercent > 75
      ? "bg-red-500"
      : state.fillPercent > 45
        ? "bg-amber-500"
        : "bg-emerald-500";

  const tokenDisplay = `${(state.tokenCount / 1000).toFixed(0)}K`;

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Three-Layer Context Compression"}
      </h2>

      <div
        className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900 sm:p-6"
        style={{ minHeight: 500 }}
      >
        <div className="grid gap-5 lg:grid-cols-[140px_1fr]">
          {/* Token Window (tall vertical bar on the left) */}
          <div className="min-w-0 flex flex-col items-center">
            <div className="mb-2 font-mono text-[10px] font-semibold text-zinc-500 dark:text-zinc-400">
              Context Window
            </div>
            <div
              className="relative w-20 max-w-full overflow-hidden rounded-xl border-2 border-zinc-300 bg-zinc-50 dark:border-zinc-600 dark:bg-zinc-800 sm:w-24"
              style={{ height: WINDOW_HEIGHT }}
            >
              {/* Blocks stacked from bottom up */}
              <div className="absolute bottom-0 left-0 right-0 flex flex-col-reverse gap-px p-1">
                <AnimatePresence mode="popLayout">
                  {state.blocks.map((block) => (
                    <motion.div
                      key={block.id}
                      initial={{ opacity: 0, scaleY: 0 }}
                      animate={{
                        opacity: 1,
                        scaleY: 1,
                        height: block.heightPx,
                      }}
                      exit={{ opacity: 0, scaleY: 0 }}
                      transition={{ duration: 0.4 }}
                      className={`flex w-full items-center justify-center rounded-sm ${
                        block.compressed
                          ? "bg-emerald-300 dark:bg-emerald-700"
                          : BLOCK_COLORS[block.type]
                      }`}
                      style={{ originY: 1 }}
                    >
                      {block.heightPx >= 14 && (
                        <span className="truncate px-1 text-[8px] font-medium text-white">
                          {block.label}
                        </span>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>

              {/* Fill level line */}
              <motion.div
                animate={{ bottom: `${state.fillPercent}%` }}
                transition={{ duration: 0.5 }}
                className="absolute left-0 right-0 border-t-2 border-dashed border-red-400 dark:border-red-500"
              >
                <span className="absolute -top-4 right-1 font-mono text-[9px] font-bold text-red-500 dark:text-red-400">
                  {state.fillPercent}%
                </span>
              </motion.div>
            </div>

            {/* Token count */}
            <motion.div
              key={state.tokenCount}
              initial={{ scale: 0.85 }}
              animate={{ scale: 1 }}
              className="mt-2 font-mono text-sm font-bold text-zinc-700 dark:text-zinc-200"
            >
              {tokenDisplay}
            </motion.div>
            <div className="font-mono text-[10px] text-zinc-400">
              / 100K
            </div>
          </div>

          {/* Right side: state display and compression stage */}
          <div className="min-w-0">
            {/* Top: horizontal token bar */}
            <div>
              <div className="mb-1 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  Token usage
                </span>
                <span className="break-words font-mono text-xs text-zinc-500 dark:text-zinc-400">
                  {state.tokenCount.toLocaleString()} / {MAX_TOKENS.toLocaleString()}
                </span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                <motion.div
                  animate={{ width: `${state.fillPercent}%` }}
                  transition={{ duration: 0.5 }}
                  className={`h-full rounded-full ${fillColor}`}
                />
              </div>
            </div>

            {/* Message type legend */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1">
                <div className="h-3 w-3 rounded bg-blue-500" />
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400">user</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-3 w-3 rounded bg-zinc-500" />
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400">assistant</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-3 w-3 rounded bg-emerald-500" />
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400">tool_result</span>
              </div>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {COMPRESSION_LAYERS.map((layer) => {
                const reached = currentStep >= layer.step;
                const active = state.compressionLabel === layer.full;
                return (
                  <motion.div
                    key={layer.full}
                    layout
                    animate={active ? { y: [0, -2, 0] } : { y: 0 }}
                    transition={{ duration: 0.8, repeat: active ? Infinity : 0 }}
                    className={`min-w-0 rounded-lg border p-3 transition-colors ${
                      reached
                        ? layer.classes
                        : "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-400"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{layer.label}</span>
                      <span className="rounded bg-white/70 px-1.5 py-0.5 font-mono text-[10px] dark:bg-zinc-900/60">
                        {reached ? "used" : "waiting"}
                      </span>
                    </div>
                    <div className="mt-2 space-y-1 text-[11px] leading-snug">
                      <div className="break-words font-mono">{layer.trigger}</div>
                      <div className="break-words opacity-80">{layer.action}</div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Highlight old tool_results at step 2 */}
            <AnimatePresence>
              {currentStep === 2 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 dark:border-amber-700 dark:bg-amber-900/20"
                >
                  <div className="text-xs font-semibold text-amber-700 dark:text-amber-300">
                    tool_results are the largest blocks
                  </div>
                  <div className="text-[11px] leading-snug text-amber-600 dark:text-amber-400">
                    File contents, command outputs, search results -- each one is thousands of tokens.
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Compression stage label */}
            <AnimatePresence>
              {state.compressionLabel && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.4 }}
                  className="mt-4"
                >
                  <div className={`rounded-lg border-2 p-4 text-center ${
                    currentStep === 3
                      ? "border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-900/20"
                      : currentStep === 5
                        ? "border-blue-400 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20"
                        : "border-emerald-400 bg-emerald-50 dark:border-emerald-600 dark:bg-emerald-900/20"
                  }`}>
                    <div className={`text-lg font-black ${
                      currentStep === 3
                        ? "text-amber-600 dark:text-amber-300"
                        : currentStep === 5
                          ? "text-blue-600 dark:text-blue-300"
                          : "text-emerald-600 dark:text-emerald-300"
                    }`}>
                      {state.compressionLabel}
                    </div>
                    <div className={`mt-1 text-xs leading-snug ${
                      currentStep === 3
                        ? "text-amber-500 dark:text-amber-400"
                        : currentStep === 5
                          ? "text-blue-500 dark:text-blue-400"
                          : "text-emerald-500 dark:text-emerald-400"
                    }`}>
                      {currentStep === 3 && "Old tool_results shrunk to tiny summaries"}
                      {currentStep === 5 && "Full conversation compressed to summary block"}
                      {currentStep === 6 && "Most aggressive compression -- near-empty context"}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Three stages overview on final step */}
            {currentStep === 6 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="mt-4 grid gap-2"
              >
                {COMPRESSION_LAYERS.map((layer, index) => (
                  <div
                    key={`summary-${layer.full}`}
                    className={`flex flex-col gap-1 rounded px-3 py-2 sm:flex-row sm:items-center sm:justify-between ${layer.classes}`}
                  >
                    <span className="break-words text-xs">
                      Stage {index + 1}: {layer.label} -- {layer.action}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] opacity-80">
                      {layer.trigger}
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </div>
        </div>

        {/* Step Controls */}
        <div className="mt-6">
          <StepControls
            currentStep={currentStep}
            totalSteps={totalSteps}
            onPrev={prev}
            onNext={next}
            onReset={reset}
            isPlaying={isPlaying}
            onToggleAutoPlay={toggleAutoPlay}
            stepTitle={STEPS[currentStep].title}
            stepDescription={STEPS[currentStep].description}
          />
        </div>
      </div>
    </section>
  );
}
