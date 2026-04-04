"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

// -- Tool definitions --

interface ToolDef {
  name: string;
  desc: string;
  color: string;
  activeColor: string;
  darkColor: string;
  darkActiveColor: string;
}

const TOOLS: ToolDef[] = [
  {
    name: "bash",
    desc: "Execute shell commands",
    color: "border-orange-300 bg-orange-50",
    activeColor: "border-orange-500 bg-orange-100 ring-2 ring-orange-400",
    darkColor: "dark:border-zinc-700 dark:bg-zinc-800/50",
    darkActiveColor: "dark:border-orange-500 dark:bg-orange-950/40 dark:ring-orange-500",
  },
  {
    name: "read_file",
    desc: "Read file contents",
    color: "border-sky-300 bg-sky-50",
    activeColor: "border-sky-500 bg-sky-100 ring-2 ring-sky-400",
    darkColor: "dark:border-zinc-700 dark:bg-zinc-800/50",
    darkActiveColor: "dark:border-sky-500 dark:bg-sky-950/40 dark:ring-sky-500",
  },
  {
    name: "write_file",
    desc: "Create or overwrite a file",
    color: "border-emerald-300 bg-emerald-50",
    activeColor: "border-emerald-500 bg-emerald-100 ring-2 ring-emerald-400",
    darkColor: "dark:border-zinc-700 dark:bg-zinc-800/50",
    darkActiveColor: "dark:border-emerald-500 dark:bg-emerald-950/40 dark:ring-emerald-500",
  },
  {
    name: "edit_file",
    desc: "Apply targeted edits",
    color: "border-violet-300 bg-violet-50",
    activeColor: "border-violet-500 bg-violet-100 ring-2 ring-violet-400",
    darkColor: "dark:border-zinc-700 dark:bg-zinc-800/50",
    darkActiveColor: "dark:border-violet-500 dark:bg-violet-950/40 dark:ring-violet-500",
  },
];

// Per-step: which tool index is active (-1 = none, 4 = all)
const ACTIVE_TOOL_PER_STEP: number[] = [-1, 0, 1, 2, 3, 4];

// Incoming request JSON per step
const REQUEST_PER_STEP: (string | null)[] = [
  null,
  '{ name: "bash", input: { cmd: "ls -la" } }',
  '{ name: "read_file", input: { path: "src/auth.ts" } }',
  '{ name: "write_file", input: { path: "config.json" } }',
  '{ name: "edit_file", input: { path: "index.ts" } }',
  null,
];

// Step annotations
const STEP_INFO = [
  { title: "The Dispatch Map", desc: "A dictionary maps tool names to handler functions. The loop code never changes." },
  { title: "Route: bash", desc: "tool_call.name -> handlers['bash'](input). Name-based routing." },
  { title: "Route: read_file", desc: "Same pattern, different handler. Validate input, execute, return result." },
  { title: "Route: write_file", desc: "Every tool returns a tool_result that goes back into messages[]." },
  { title: "Route: edit_file", desc: "Adding a new tool = adding one entry to the dispatch map." },
  { title: "The Key Insight", desc: "The while loop stays the same. You only grow the dispatch map. That's it." },
];

// SVG layout constants
const SVG_WIDTH = 600;
const SVG_HEIGHT = 320;
const DISPATCHER_X = SVG_WIDTH / 2;
const DISPATCHER_Y = 60;
const DISPATCHER_W = 160;
const DISPATCHER_H = 50;
const CARD_Y = 230;
const CARD_W = 110;
const CARD_H = 65;
const CARD_GAP = 20;

function getCardX(index: number): number {
  const totalWidth = TOOLS.length * CARD_W + (TOOLS.length - 1) * CARD_GAP;
  const startX = (SVG_WIDTH - totalWidth) / 2;
  return startX + index * (CARD_W + CARD_GAP) + CARD_W / 2;
}

export default function ToolDispatch({ title }: { title?: string }) {
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: 6, autoPlayInterval: 2500 });

  const palette = useSvgPalette();
  const activeToolIdx = ACTIVE_TOOL_PER_STEP[currentStep];
  const request = REQUEST_PER_STEP[currentStep];
  const stepInfo = STEP_INFO[currentStep];
  const isAllActive = activeToolIdx === 4;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Tool Dispatch Map"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        {/* Incoming request display */}
        <div className="mb-4 flex min-h-[32px] items-center gap-2">
          <span className="shrink-0 text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Incoming:
          </span>
          <AnimatePresence mode="wait">
            {request && (
              <motion.code
                key={request}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.3 }}
                className="rounded bg-blue-100 px-2.5 py-1 font-mono text-xs font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-300"
              >
                {request}
              </motion.code>
            )}
            {!request && currentStep === 0 && (
              <motion.span
                key="waiting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                className="text-xs text-zinc-400 dark:text-zinc-600"
              >
                waiting for tool_call...
              </motion.span>
            )}
            {isAllActive && (
              <motion.span
                key="all-routes"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-xs font-medium text-emerald-600 dark:text-emerald-400"
              >
                All routes active
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* SVG dispatch diagram */}
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
          style={{ minHeight: 240 }}
        >
          <defs>
            <filter id="dispatch-glow">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.6" />
            </filter>
            <filter id="card-glow-orange">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#f97316" floodOpacity="0.6" />
            </filter>
            <filter id="card-glow-sky">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#0ea5e9" floodOpacity="0.6" />
            </filter>
            <filter id="card-glow-emerald">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#10b981" floodOpacity="0.6" />
            </filter>
            <filter id="card-glow-violet">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#8b5cf6" floodOpacity="0.6" />
            </filter>
            <marker
              id="dispatch-arrow"
              markerWidth="8"
              markerHeight="6"
              refX="8"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
            </marker>
            <marker
              id="dispatch-arrow-dim"
              markerWidth="8"
              markerHeight="6"
              refX="8"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
            </marker>
          </defs>

          {/* Dispatcher box */}
          <motion.rect
            x={DISPATCHER_X - DISPATCHER_W / 2}
            y={DISPATCHER_Y - DISPATCHER_H / 2}
            width={DISPATCHER_W}
            height={DISPATCHER_H}
            rx={10}
            strokeWidth={2}
            animate={{
              fill: currentStep > 0 ? palette.activeNodeFill : palette.nodeFill,
              stroke: currentStep > 0 ? palette.activeNodeStroke : palette.nodeStroke,
            }}
            filter={currentStep > 0 ? "url(#dispatch-glow)" : "none"}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={DISPATCHER_X}
            y={DISPATCHER_Y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={13}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: currentStep > 0 ? palette.activeNodeText : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            dispatch(name)
          </motion.text>

          {/* Connection lines from dispatcher to each tool card */}
          {TOOLS.map((tool, i) => {
            const cardX = getCardX(i);
            const isActive = isAllActive || i === activeToolIdx;
            const lineColor = isActive ? palette.activeEdgeStroke : palette.edgeStroke;

            return (
              <motion.line
                key={`line-${tool.name}`}
                x1={DISPATCHER_X}
                y1={DISPATCHER_Y + DISPATCHER_H / 2}
                x2={cardX}
                y2={CARD_Y - CARD_H / 2}
                strokeWidth={isActive ? 2.5 : 1.5}
                markerEnd={isActive ? "url(#dispatch-arrow)" : "url(#dispatch-arrow-dim)"}
                animate={{ stroke: lineColor, strokeWidth: isActive ? 2.5 : 1.5 }}
                transition={{ duration: 0.4 }}
              />
            );
          })}

          {/* Tool cards */}
          {TOOLS.map((tool, i) => {
            const cardX = getCardX(i);
            const isActive = isAllActive || i === activeToolIdx;
            const glowFilters = [
              "url(#card-glow-orange)",
              "url(#card-glow-sky)",
              "url(#card-glow-emerald)",
              "url(#card-glow-violet)",
            ];
            const activeColors = ["#f97316", "#0ea5e9", "#10b981", "#8b5cf6"];
            const activeBorders = ["#ea580c", "#0284c7", "#059669", "#7c3aed"];

            return (
              <g key={tool.name}>
                <motion.rect
                  x={cardX - CARD_W / 2}
                  y={CARD_Y - CARD_H / 2}
                  width={CARD_W}
                  height={CARD_H}
                  rx={8}
                  strokeWidth={2}
                  animate={{
                    fill: isActive ? activeColors[i] : palette.nodeFill,
                    stroke: isActive ? activeBorders[i] : palette.nodeStroke,
                  }}
                  filter={isActive ? glowFilters[i] : "none"}
                  transition={{ duration: 0.4 }}
                />
                <motion.text
                  x={cardX}
                  y={CARD_Y - 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={11}
                  fontWeight={700}
                  fontFamily="monospace"
                  animate={{ fill: isActive ? "#ffffff" : palette.nodeText }}
                  transition={{ duration: 0.4 }}
                >
                  {tool.name}
                </motion.text>
                <motion.text
                  x={cardX}
                  y={CARD_Y + 12}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={8}
                  fontFamily="sans-serif"
                  animate={{ fill: isActive ? "rgba(255,255,255,0.8)" : palette.labelFill }}
                  transition={{ duration: 0.4 }}
                >
                  {tool.desc}
                </motion.text>
              </g>
            );
          })}

          {/* "+" extensibility indicator on last step */}
          {isAllActive && (
            <motion.g
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3, duration: 0.4 }}
            >
              <circle
                cx={getCardX(3) + CARD_W / 2 + 30}
                cy={CARD_Y}
                r={16}
                fill="none"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="4 3"
              />
              <text
                x={getCardX(3) + CARD_W / 2 + 30}
                y={CARD_Y + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={18}
                fontWeight={700}
                fill="#3b82f6"
              >
                +
              </text>
            </motion.g>
          )}
        </svg>

        {/* Code snippet below the diagram */}
        <div className="mt-3 rounded-md bg-zinc-100 px-3 py-2 dark:bg-zinc-800">
          <code className="block font-mono text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-300">
            <span className="text-blue-600 dark:text-blue-400">const</span> handlers = {"{"}
            {TOOLS.map((tool, i) => {
              const isActive = isAllActive || i === activeToolIdx;
              return (
                <motion.span
                  key={tool.name}
                  animate={{
                    color: isActive ? "#3b82f6" : undefined,
                    fontWeight: isActive ? 700 : 400,
                  }}
                  className="text-zinc-600 dark:text-zinc-300"
                >
                  {" "}{tool.name},
                </motion.span>
              );
            })}
            {" }{"}{"}"};
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
