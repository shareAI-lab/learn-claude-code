"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

// -- Flowchart node definitions --

interface FlowNode {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  type: "rect" | "diamond";
}

const NODES: FlowNode[] = [
  { id: "start", label: "Start", x: 160, y: 30, w: 120, h: 40, type: "rect" },
  { id: "api_call", label: "API Call", x: 160, y: 110, w: 120, h: 40, type: "rect" },
  { id: "check", label: "stop_reason?", x: 160, y: 200, w: 140, h: 50, type: "diamond" },
  { id: "execute", label: "Execute Tool", x: 160, y: 300, w: 120, h: 40, type: "rect" },
  { id: "append", label: "Append Result", x: 160, y: 380, w: 120, h: 40, type: "rect" },
  { id: "end", label: "Break / Done", x: 380, y: 200, w: 120, h: 40, type: "rect" },
];

// Edges between nodes (SVG path data computed inline)
interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

const EDGES: FlowEdge[] = [
  { from: "start", to: "api_call" },
  { from: "api_call", to: "check" },
  { from: "check", to: "execute", label: "tool_use" },
  { from: "execute", to: "append" },
  { from: "append", to: "api_call" },
  { from: "check", to: "end", label: "end_turn" },
];

// Which nodes light up at each step
const ACTIVE_NODES_PER_STEP: string[][] = [
  [],
  ["start"],
  ["api_call"],
  ["check", "execute"],
  ["execute", "append"],
  ["api_call", "check", "execute", "append"],
  ["check", "end"],
];

// Which edges highlight at each step
const ACTIVE_EDGES_PER_STEP: string[][] = [
  [],
  [],
  ["start->api_call"],
  ["api_call->check", "check->execute"],
  ["execute->append"],
  ["append->api_call", "api_call->check", "check->execute", "execute->append"],
  ["api_call->check", "check->end"],
];

// -- Message blocks --

interface MessageBlock {
  role: string;
  detail: string;
  colorClass: string;
}

const MESSAGES_PER_STEP: (MessageBlock | null)[][] = [
  [],
  [{ role: "user", detail: "Fix the login bug", colorClass: "bg-blue-500 dark:bg-blue-600" }],
  [],
  [{ role: "assistant", detail: "tool_use: read_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" }],
  [{ role: "tool_result", detail: "auth.ts contents...", colorClass: "bg-emerald-500 dark:bg-emerald-600" }],
  [
    { role: "assistant", detail: "tool_use: edit_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" },
    { role: "tool_result", detail: "file updated", colorClass: "bg-emerald-500 dark:bg-emerald-600" },
  ],
  [{ role: "assistant", detail: "end_turn: Done!", colorClass: "bg-purple-500 dark:bg-purple-600" }],
];

// -- Step annotations --

const STEP_INFO = [
  { title: "The While Loop", desc: "Every agent is a while loop that keeps calling the model until it says 'stop'." },
  { title: "User Input", desc: "The loop starts when the user sends a message." },
  { title: "Call the Model", desc: "Send all messages to the LLM. It sees everything and decides what to do." },
  { title: "stop_reason: tool_use", desc: "The model wants to use a tool. The loop continues." },
  { title: "Execute & Append", desc: "Run the tool, append the result to messages[]. Feed it back." },
  { title: "Loop Again", desc: "Same code path, second iteration. The model decides to edit a file." },
  { title: "stop_reason: end_turn", desc: "The model is done. Loop exits. That's the entire agent." },
];

// -- Helpers --

function getNode(id: string): FlowNode {
  return NODES.find((n) => n.id === id)!;
}

function edgePath(fromId: string, toId: string): string {
  const from = getNode(fromId);
  const to = getNode(toId);

  // Loop-back: append -> api_call (goes to the left side and back up)
  if (fromId === "append" && toId === "api_call") {
    const startX = from.x - from.w / 2;
    const startY = from.y;
    const endX = to.x - to.w / 2;
    const endY = to.y;
    return `M ${startX} ${startY} L ${startX - 50} ${startY} L ${endX - 50} ${endY} L ${endX} ${endY}`;
  }

  // Horizontal: check -> end
  if (fromId === "check" && toId === "end") {
    const startX = from.x + from.w / 2;
    const startY = from.y;
    const endX = to.x - to.w / 2;
    const endY = to.y;
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  }

  // Vertical (default)
  const startX = from.x;
  const startY = from.y + from.h / 2;
  const endX = to.x;
  const endY = to.y - to.h / 2;
  return `M ${startX} ${startY} L ${endX} ${endY}`;
}

// -- Component --

export default function AgentLoop({ title }: { title?: string }) {
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: 7, autoPlayInterval: 2500 });

  const palette = useSvgPalette();
  const activeNodes = ACTIVE_NODES_PER_STEP[currentStep];
  const activeEdges = ACTIVE_EDGES_PER_STEP[currentStep];

  // Build accumulated messages up to the current step
  const visibleMessages: MessageBlock[] = [];
  for (let s = 0; s <= currentStep; s++) {
    for (const msg of MESSAGES_PER_STEP[s]) {
      if (msg) visibleMessages.push(msg);
    }
  }

  const stepInfo = STEP_INFO[currentStep];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "The Agent While-Loop"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="flex flex-col gap-4 lg:flex-row">
          {/* Left panel: SVG Flowchart (60%) */}
          <div className="w-full lg:w-[60%]">
            <div className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">
              while (stop_reason === "tool_use")
            </div>
            <svg
              viewBox="0 0 500 440"
              className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
              style={{ minHeight: 300 }}
            >
              <defs>
                <filter id="glow-blue">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.7" />
                </filter>
                <filter id="glow-purple">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#a855f7" floodOpacity="0.7" />
                </filter>
                <marker
                  id="arrowhead"
                  markerWidth="8"
                  markerHeight="6"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
                </marker>
                <marker
                  id="arrowhead-active"
                  markerWidth="8"
                  markerHeight="6"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
                </marker>
              </defs>

              {/* Edges */}
              {EDGES.map((edge) => {
                const key = `${edge.from}->${edge.to}`;
                const isActive = activeEdges.includes(key);
                const d = edgePath(edge.from, edge.to);

                return (
                  <g key={key}>
                    <motion.path
                      d={d}
                      fill="none"
                      stroke={isActive ? palette.activeEdgeStroke : palette.edgeStroke}
                      strokeWidth={isActive ? 2.5 : 1.5}
                      strokeDasharray={isActive ? "none" : "none"}
                      markerEnd={isActive ? "url(#arrowhead-active)" : "url(#arrowhead)"}
                      animate={{
                        stroke: isActive ? palette.activeEdgeStroke : palette.edgeStroke,
                        strokeWidth: isActive ? 2.5 : 1.5,
                      }}
                      transition={{ duration: 0.4 }}
                    />
                    {edge.label && (
                      <text
                        x={
                          edge.from === "check" && edge.to === "end"
                            ? (getNode("check").x + getNode("end").x) / 2
                            : getNode(edge.from).x + 75
                        }
                        y={
                          edge.from === "check" && edge.to === "end"
                            ? getNode("check").y - 10
                            : (getNode(edge.from).y + getNode(edge.to).y) / 2
                        }
                        textAnchor="middle"
                        className="fill-zinc-400 text-[10px] dark:fill-zinc-500"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {NODES.map((node) => {
                const isActive = activeNodes.includes(node.id);
                const isEnd = node.id === "end";
                const filterAttr = isActive
                  ? isEnd
                    ? "url(#glow-purple)"
                    : "url(#glow-blue)"
                  : "none";

                if (node.type === "diamond") {
                  // Diamond shape for decision node
                  const cx = node.x;
                  const cy = node.y;
                  const hw = node.w / 2;
                  const hh = node.h / 2;
                  const points = `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`;
                  return (
                    <g key={node.id}>
                      <motion.polygon
                        points={points}
                        rx={6}
                        fill={isActive ? palette.activeNodeFill : palette.nodeFill}
                        stroke={isActive ? palette.activeNodeStroke : palette.nodeStroke}
                        strokeWidth={1.5}
                        filter={filterAttr}
                        animate={{
                          fill: isActive ? palette.activeNodeFill : palette.nodeFill,
                          stroke: isActive ? palette.activeNodeStroke : palette.nodeStroke,
                        }}
                        transition={{ duration: 0.4 }}
                      />
                      <motion.text
                        x={cx}
                        y={cy + 4}
                        textAnchor="middle"
                        fontSize={11}
                        fontWeight={600}
                        fontFamily="monospace"
                        animate={{ fill: isActive ? palette.activeNodeText : palette.nodeText }}
                        transition={{ duration: 0.4 }}
                      >
                        {node.label}
                      </motion.text>
                    </g>
                  );
                }

                return (
                  <g key={node.id}>
                    <motion.rect
                      x={node.x - node.w / 2}
                      y={node.y - node.h / 2}
                      width={node.w}
                      height={node.h}
                      rx={8}
                      fill={isActive ? (isEnd ? palette.endNodeFill : palette.activeNodeFill) : palette.nodeFill}
                      stroke={isActive ? (isEnd ? palette.endNodeStroke : palette.activeNodeStroke) : palette.nodeStroke}
                      strokeWidth={1.5}
                      filter={filterAttr}
                      animate={{
                        fill: isActive ? (isEnd ? palette.endNodeFill : palette.activeNodeFill) : palette.nodeFill,
                        stroke: isActive ? (isEnd ? palette.endNodeStroke : palette.activeNodeStroke) : palette.nodeStroke,
                      }}
                      transition={{ duration: 0.4 }}
                    />
                    <motion.text
                      x={node.x}
                      y={node.y + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontWeight={600}
                      fontFamily="monospace"
                      animate={{ fill: isActive ? palette.activeNodeText : palette.nodeText }}
                      transition={{ duration: 0.4 }}
                    >
                      {node.label}
                    </motion.text>
                  </g>
                );
              })}

              {/* Iteration counter */}
              {currentStep >= 5 && (
                <motion.text
                  x={60}
                  y={130}
                  textAnchor="middle"
                  fontSize={10}
                  fontFamily="monospace"
                  fill="#3b82f6"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  iter #2
                </motion.text>
              )}
            </svg>
          </div>

          {/* Right panel: messages[] array (40%) */}
          <div className="w-full lg:w-[40%]">
            <div className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">
              messages[]
            </div>
            <div className="min-h-[300px] space-y-2 rounded-md border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
              <AnimatePresence mode="popLayout">
                {visibleMessages.length === 0 && (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="py-8 text-center text-xs text-zinc-400 dark:text-zinc-600"
                  >
                    [ empty ]
                  </motion.div>
                )}
                {visibleMessages.map((msg, i) => (
                  <motion.div
                    key={`${msg.role}-${msg.detail}-${i}`}
                    initial={{ opacity: 0, y: 12, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.35, type: "spring", bounce: 0.3 }}
                    className={`rounded-md px-3 py-2 ${msg.colorClass}`}
                  >
                    <div className="font-mono text-[11px] font-semibold text-white">
                      {msg.role}
                    </div>
                    <div className="mt-0.5 text-[10px] text-white/80">
                      {msg.detail}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Array index markers */}
              {visibleMessages.length > 0 && (
                <div className="mt-3 border-t border-zinc-200 pt-2 dark:border-zinc-700">
                  <span className="font-mono text-[10px] text-zinc-400">
                    length: {visibleMessages.length}
                  </span>
                </div>
              )}
            </div>
          </div>
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
