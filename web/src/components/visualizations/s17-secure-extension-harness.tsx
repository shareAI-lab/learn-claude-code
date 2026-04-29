"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

const LAYERS = [
  { id: "prehook", label: "PreHook", color: "#06b6d4", desc: "Intercept before execution" },
  { id: "classify", label: "Classify", color: "#f59e0b", desc: "Security classification" },
  { id: "permission", label: "Permission", color: "#8b5cf6", desc: "Mode-based decision" },
  { id: "execute", label: "Execute", color: "#10b981", desc: "Run handler or MCP" },
  { id: "posthook", label: "PostHook", color: "#3b82f6", desc: "Post-execution hooks" },
];

const STEP_INFO = [
  { title: "The Execution Pipeline", desc: "Five layers compose into a single chokepoint. Every tool call flows through all layers." },
  { title: "Layer 1: PreHook", desc: "Registered hooks fire before execution. They can observe, modify input, or block entirely." },
  { title: "Layer 2: Classify", desc: "For bash commands, the two-layer classifier (regex + LLM) determines intent." },
  { title: "Layer 3: Permission", desc: "The classification result maps to a permission mode (allow/deny/ask/edit)." },
  { title: "Layer 4: Execute", desc: "If permitted, the tool handler or MCP server runs and produces a result." },
  { title: "Layer 5: PostHook", desc: "Post-execution hooks fire: audit logging, notifications, cleanup." },
  { title: "Blocked at Layer 2", desc: "rm -rf / is classified as dangerous → permission denies → execution never starts." },
];

const COMMANDS: (string | null)[] = [
  null, "ls -la", "ls -la", "ls -la", "ls -la", "ls -la", "rm -rf /",
];

const OUTCOMES: (string | null)[] = [
  null, null, "safe", "allow", "✓ result", "audit logged", "✗ BLOCKED",
];

const SVG_W = 600;
const SVG_H = 400;
const PIPE_X = 200;
const PIPE_START_Y = 50;
const LAYER_H = 48;
const LAYER_W = 180;
const LAYER_GAP = 14;
const BLOCKED_X = 450;
const RESULT_X = 450;

function getLayerY(i: number): number {
  return PIPE_START_Y + i * (LAYER_H + LAYER_GAP);
}

export default function SecureExtensionHarness({ title }: { title?: string }) {
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: STEP_INFO.length, autoPlayInterval: 2500 });

  const palette = useSvgPalette();
  const command = COMMANDS[currentStep];
  const outcome = OUTCOMES[currentStep];
  const stepInfo = STEP_INFO[currentStep];
  const isBlocked = currentStep === 6;

  // Which layers are active/passed
  const activeLayer = isBlocked ? 1 : currentStep > 0 ? currentStep - 1 : -1;
  const passedLayers = isBlocked ? 1 : currentStep > 0 ? currentStep : 0;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Secure Extension Harness: 5-Layer Pipeline"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        {/* Command input */}
        <div className="mb-4 flex min-h-[32px] items-center gap-2">
          <span className="shrink-0 text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Tool call:
          </span>
          <AnimatePresence mode="wait">
            {command && (
              <motion.code
                key={command}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.3 }}
                className="rounded bg-zinc-100 px-2.5 py-1 font-mono text-xs font-medium text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200"
              >
                bash({command})
              </motion.code>
            )}
            {!command && (
              <motion.span
                key="waiting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                className="text-xs text-zinc-400 dark:text-zinc-600"
              >
                execute_tool() waiting...
              </motion.span>
            )}
          </AnimatePresence>
          {outcome && (
            <motion.span
              key={outcome}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
                outcome.includes("BLOCKED")
                  ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                  : outcome.includes("result")
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                    : "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300"
              }`}
            >
              {outcome}
            </motion.span>
          )}
        </div>

        {/* SVG pipeline */}
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
          style={{ minHeight: 300 }}
        >
          <defs>
            {LAYERS.map((l) => (
              <filter key={`glow-${l.id}`} id={`glow-${l.id}`}>
                <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={l.color} floodOpacity="0.6" />
              </filter>
            ))}
            <filter id="se-glow-red">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.7" />
            </filter>
            <marker id="se-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
            </marker>
            <marker id="se-arrow-dim" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
            </marker>
          </defs>

          {/* Vertical connection lines between layers */}
          {LAYERS.map((_, i) => {
            if (i >= LAYERS.length - 1) return null;
            const y1 = getLayerY(i) + LAYER_H / 2;
            const y2 = getLayerY(i + 1) - LAYER_H / 2;
            const isPassed = isBlocked ? i < 1 : (i < passedLayers && currentStep > 0);
            return (
              <motion.line
                key={`conn-${i}`}
                x1={PIPE_X}
                y1={y1}
                x2={PIPE_X}
                y2={y2}
                strokeWidth={isPassed ? 2.5 : 1.5}
                markerEnd={isPassed ? "url(#se-arrow)" : "url(#se-arrow-dim)"}
                animate={{ stroke: isPassed ? palette.activeEdgeStroke : palette.edgeStroke }}
                transition={{ duration: 0.3 }}
              />
            );
          })}

          {/* Layer boxes */}
          {LAYERS.map((layer, i) => {
            const y = getLayerY(i);
            const isPassedThrough = isBlocked ? i === 0 : (i < passedLayers && currentStep > 0);
            const isBlockedHere = isBlocked && i === 1;
            const isActive = !isBlocked && i === activeLayer;

            return (
              <g key={layer.id}>
                <motion.rect
                  x={PIPE_X - LAYER_W / 2}
                  y={y - LAYER_H / 2}
                  width={LAYER_W}
                  height={LAYER_H}
                  rx={10}
                  strokeWidth={2}
                  animate={{
                    fill: isBlockedHere
                      ? "#ef4444"
                      : isPassedThrough || isActive
                        ? layer.color
                        : palette.nodeFill,
                    stroke: isBlockedHere
                      ? "#dc2626"
                      : isPassedThrough || isActive
                        ? layer.color
                        : palette.nodeStroke,
                  }}
                  filter={isBlockedHere ? "url(#se-glow-red)" : isActive || isPassedThrough ? `url(#glow-${layer.id})` : "none"}
                  transition={{ duration: 0.4 }}
                />
                <motion.text
                  x={PIPE_X}
                  y={y - 6}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={12}
                  fontWeight={700}
                  fontFamily="monospace"
                  animate={{
                    fill: isBlockedHere || isPassedThrough || isActive
                      ? "#ffffff"
                      : palette.nodeText,
                  }}
                  transition={{ duration: 0.4 }}
                >
                  {isBlockedHere ? "✗ BLOCKED" : layer.label}
                </motion.text>
                <motion.text
                  x={PIPE_X}
                  y={y + 12}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={8}
                  animate={{
                    fill: isBlockedHere || isPassedThrough || isActive
                      ? "rgba(255,255,255,0.8)"
                      : palette.labelFill,
                  }}
                  transition={{ duration: 0.4 }}
                >
                  {isBlockedHere ? "dangerous → deny" : layer.desc}
                </motion.text>
              </g>
            );
          })}

          {/* Result node (right of Execute layer) */}
          <AnimatePresence>
            {currentStep >= 5 && !isBlocked && (
              <motion.g
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
              >
                <line
                  x1={PIPE_X + LAYER_W / 2}
                  y1={getLayerY(3)}
                  x2={RESULT_X - 40}
                  y2={getLayerY(3)}
                  stroke="#10b981"
                  strokeWidth={2}
                  markerEnd="url(#se-arrow)"
                />
                <rect
                  x={RESULT_X - 40}
                  y={getLayerY(3) - 18}
                  width={80}
                  height={36}
                  rx={8}
                  fill="#10b981"
                  stroke="#059669"
                  strokeWidth={2}
                />
                <text
                  x={RESULT_X}
                  y={getLayerY(3) + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={10}
                  fontWeight={700}
                  fill="#ffffff"
                  fontFamily="monospace"
                >
                  RESULT
                </text>
              </motion.g>
            )}
          </AnimatePresence>

          {/* Blocked indicator (right of Classify layer) */}
          <AnimatePresence>
            {isBlocked && (
              <motion.g
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
              >
                <line
                  x1={PIPE_X + LAYER_W / 2}
                  y1={getLayerY(1)}
                  x2={BLOCKED_X - 40}
                  y2={getLayerY(1)}
                  stroke="#ef4444"
                  strokeWidth={2.5}
                  strokeDasharray="6 3"
                  markerEnd="url(#se-arrow)"
                />
                <rect
                  x={BLOCKED_X - 40}
                  y={getLayerY(1) - 18}
                  width={80}
                  height={36}
                  rx={8}
                  fill="#ef4444"
                  stroke="#dc2626"
                  strokeWidth={2}
                />
                <text
                  x={BLOCKED_X}
                  y={getLayerY(1) + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={10}
                  fontWeight={700}
                  fill="#ffffff"
                  fontFamily="monospace"
                >
                  DENIED
                </text>
              </motion.g>
            )}
          </AnimatePresence>

          {/* Layer number indicators */}
          {LAYERS.map((_, i) => {
            const y = getLayerY(i);
            return (
              <text
                key={`num-${i}`}
                x={PIPE_X - LAYER_W / 2 - 16}
                y={y + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={10}
                fontWeight={700}
                fill={i === activeLayer ? LAYERS[i].color : palette.labelFill}
                fontFamily="monospace"
              >
                L{i + 1}
              </text>
            );
          })}
        </svg>

        {/* Code snippet */}
        <div className="mt-3 rounded-md bg-zinc-100 px-3 py-2 dark:bg-zinc-800">
          <code className="block font-mono text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-300">
            <span className="text-blue-600 dark:text-blue-400">def</span>{" "}
            <span className="text-emerald-600 dark:text-emerald-400">execute_tool</span>(name, input):
            {"\n  "}
            <span className="text-zinc-500">{"# "}</span>
            {isBlocked
              ? "classify → dangerous → return denied"
              : activeLayer === 0
                ? "hooks.fire('PreToolUse', name, input)"
                : activeLayer === 1
                  ? "level = classifier.classify(input.cmd)"
                  : activeLayer === 2
                    ? "mode = guard.check(level)"
                    : activeLayer === 3
                      ? "result = handler(input) or mcp.call(name)"
                      : activeLayer === 4
                        ? "hooks.fire('PostToolUse', name, result)"
                        : "PreHook → Classify → Permission → Execute → PostHook"}
          </code>
        </div>
      </div>

      <StepControls
        currentStep={currentStep}
        totalSteps={totalSteps}
        onPrev={prev}
        onNext={next}
        onReset={reset}
        isPlaying={isPlaying}
        onToggleAutoPlay={toggleAutoPlay}
        stepTitle={stepInfo.title}
        stepDescription={stepInfo.desc}
      />
    </section>
  );
}
