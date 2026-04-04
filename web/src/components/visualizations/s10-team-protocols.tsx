"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

type Protocol = "shutdown" | "plan";

// -- Layout constants for the sequence diagram --
const SVG_W = 560;
const SVG_H = 360;
const LIFELINE_LEFT_X = 140;
const LIFELINE_RIGHT_X = 420;
const LIFELINE_TOP = 60;
const LIFELINE_BOTTOM = 330;
const ACTIVATION_W = 12;
const ARROW_Y_START = 110;
const ARROW_Y_GAP = 70;

// Request ID shown on message tags
const REQUEST_ID = "req_abc";

// -- Shutdown protocol step definitions --
const SHUTDOWN_STEPS = [
  { title: "Structured Protocols", desc: "Protocols define structured message exchanges with correlated request IDs." },
  { title: "Shutdown Request", desc: "The leader initiates shutdown. The request_id links the request to its response." },
  { title: "Teammate Decides", desc: "The teammate can accept or reject. It's not a forced kill -- it's a polite request." },
  { title: "Approved", desc: "Same request_id in the response. Teammate exits cleanly." },
];

// -- Plan approval protocol step definitions --
const PLAN_STEPS = [
  { title: "Plan Approval", desc: "Teammates in plan_mode must get approval before implementing changes." },
  { title: "Submit Plan", desc: "The teammate designs a plan and sends it to the leader for review." },
  { title: "Leader Reviews", desc: "Leader reviews and approves or rejects with feedback. Same request-response pattern." },
];

// Horizontal arrow between lifelines
function SequenceArrow({
  y,
  direction,
  label,
  tagLabel,
  color,
  tagBg,
  tagStroke,
  tagText,
}: {
  y: number;
  direction: "right" | "left";
  label: string;
  tagLabel?: string;
  color: string;
  tagBg?: string;
  tagStroke?: string;
  tagText?: string;
}) {
  const fromX = direction === "right" ? LIFELINE_LEFT_X + ACTIVATION_W / 2 : LIFELINE_RIGHT_X - ACTIVATION_W / 2;
  const toX = direction === "right" ? LIFELINE_RIGHT_X - ACTIVATION_W / 2 : LIFELINE_LEFT_X + ACTIVATION_W / 2;
  const arrowTip = direction === "right" ? toX - 6 : toX + 6;
  const labelX = (fromX + toX) / 2;

  return (
    <motion.g
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Arrow line */}
      <line
        x1={fromX}
        y1={y}
        x2={toX}
        y2={y}
        stroke={color}
        strokeWidth={2}
      />
      {/* Arrow head */}
      <polygon
        points={
          direction === "right"
            ? `${toX},${y} ${arrowTip},${y - 4} ${arrowTip},${y + 4}`
            : `${toX},${y} ${arrowTip},${y - 4} ${arrowTip},${y + 4}`
        }
        fill={color}
      />
      {/* Message label */}
      <text
        x={labelX}
        y={y - 10}
        textAnchor="middle"
        fontSize={8}
        fontFamily="monospace"
        fontWeight={600}
        fill={color}
      >
        {label}
      </text>
      {/* Request ID tag */}
      {tagLabel && (
        <g>
          <rect
            x={labelX - 36}
            y={y + 4}
            width={72}
            height={16}
            rx={3}
            fill={tagBg || "#f5f3ff"}
            stroke={tagStroke || "#c4b5fd"}
            strokeWidth={0.5}
          />
          <text
            x={labelX}
            y={y + 14}
            textAnchor="middle"
            fontSize={6}
            fontFamily="monospace"
            fill={tagText || "#7c3aed"}
          >
            {tagLabel}
          </text>
        </g>
      )}
    </motion.g>
  );
}

// Decision diamond on a lifeline
function DecisionBox({ x, y }: { x: number; y: number }) {
  const size = 14;
  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      <polygon
        points={`${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`}
        fill="#fef3c7"
        stroke="#f59e0b"
        strokeWidth={1}
      />
      <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle" fontSize={7} fontWeight={700} fill="#92400e">
        ?
      </text>
      <text x={x + size + 6} y={y - 4} fontSize={6} fontFamily="monospace" fill="#10b981">
        approve
      </text>
      <text x={x + size + 6} y={y + 6} fontSize={6} fontFamily="monospace" fill="#ef4444">
        reject
      </text>
    </motion.g>
  );
}

// Activation bar on a lifeline
function ActivationBar({
  x,
  yStart,
  yEnd,
  color,
}: {
  x: number;
  yStart: number;
  yEnd: number;
  color: string;
}) {
  return (
    <motion.rect
      x={x - ACTIVATION_W / 2}
      y={yStart}
      width={ACTIVATION_W}
      height={yEnd - yStart}
      rx={2}
      fill={color}
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.6 }}
      transition={{ duration: 0.4 }}
    />
  );
}

export default function TeamProtocols({ title }: { title?: string }) {
  const [protocol, setProtocol] = useState<Protocol>("shutdown");

  const totalSteps = protocol === "shutdown" ? SHUTDOWN_STEPS.length : PLAN_STEPS.length;
  const steps = protocol === "shutdown" ? SHUTDOWN_STEPS : PLAN_STEPS;

  const vis = useSteppedVisualization({ totalSteps, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const palette = useSvgPalette();

  const switchProtocol = (p: Protocol) => {
    setProtocol(p);
    vis.reset();
  };

  const leftLabel = protocol === "shutdown" ? "Leader" : "Leader";
  const rightLabel = protocol === "shutdown" ? "Teammate" : "Teammate";

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "FSM Team Protocols"}
      </h2>
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900 min-h-[500px]">
        {/* Protocol toggle */}
        <div className="flex justify-center gap-2 mb-4">
          <button
            onClick={() => switchProtocol("shutdown")}
            className={`rounded-md px-4 py-1.5 text-xs font-medium transition-colors ${
              protocol === "shutdown"
                ? "bg-blue-500 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
            }`}
          >
            Shutdown Protocol
          </button>
          <button
            onClick={() => switchProtocol("plan")}
            className={`rounded-md px-4 py-1.5 text-xs font-medium transition-colors ${
              protocol === "plan"
                ? "bg-emerald-500 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
            }`}
          >
            Plan Approval Protocol
          </button>
        </div>

        {/* Sequence diagram SVG */}
        <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full">
          <defs>
            <marker
              id="seq-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={palette.arrowFill} />
            </marker>
          </defs>

          {/* Lifeline headers */}
          <rect x={LIFELINE_LEFT_X - 40} y={20} width={80} height={28} rx={6} fill="#3b82f6" />
          <text x={LIFELINE_LEFT_X} y={37} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize={11} fontWeight={700}>
            {leftLabel}
          </text>

          <rect x={LIFELINE_RIGHT_X - 40} y={20} width={80} height={28} rx={6} fill="#8b5cf6" />
          <text x={LIFELINE_RIGHT_X} y={37} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize={11} fontWeight={700}>
            {rightLabel}
          </text>

          {/* Lifeline dashed lines */}
          <line
            x1={LIFELINE_LEFT_X}
            y1={LIFELINE_TOP}
            x2={LIFELINE_LEFT_X}
            y2={LIFELINE_BOTTOM}
            stroke={palette.edgeStroke}
            strokeWidth={1}
            strokeDasharray="6 4"
          />
          <line
            x1={LIFELINE_RIGHT_X}
            y1={LIFELINE_TOP}
            x2={LIFELINE_RIGHT_X}
            y2={LIFELINE_BOTTOM}
            stroke={palette.edgeStroke}
            strokeWidth={1}
            strokeDasharray="6 4"
          />

          <AnimatePresence mode="wait">
            {protocol === "shutdown" && (
              <g key="shutdown">
                {/* Activation bars appear as needed */}
                {step >= 1 && (
                  <ActivationBar
                    x={LIFELINE_LEFT_X}
                    yStart={ARROW_Y_START - 10}
                    yEnd={step >= 3 ? ARROW_Y_START + ARROW_Y_GAP * 2 + 20 : ARROW_Y_START + 30}
                    color="#3b82f6"
                  />
                )}
                {step >= 1 && (
                  <ActivationBar
                    x={LIFELINE_RIGHT_X}
                    yStart={ARROW_Y_START - 5}
                    yEnd={step >= 3 ? ARROW_Y_START + ARROW_Y_GAP * 2 + 15 : ARROW_Y_START + ARROW_Y_GAP + 20}
                    color="#8b5cf6"
                  />
                )}

                {/* Step 1: shutdown_request arrow (Leader -> Teammate) */}
                {step >= 1 && (
                  <SequenceArrow
                    y={ARROW_Y_START}
                    direction="right"
                    label="shutdown_request"
                    tagLabel={`request_id: ${REQUEST_ID}`}
                    color="#3b82f6"
                    tagBg={palette.bgSubtle}
                    tagStroke={palette.nodeStroke}
                    tagText={palette.nodeText}
                  />
                )}

                {/* Step 2: decision box on teammate lifeline */}
                {step >= 2 && (
                  <DecisionBox
                    x={LIFELINE_RIGHT_X + 50}
                    y={ARROW_Y_START + ARROW_Y_GAP}
                  />
                )}

                {/* Step 3: shutdown_response arrow (Teammate -> Leader) */}
                {step >= 3 && (
                  <SequenceArrow
                    y={ARROW_Y_START + ARROW_Y_GAP * 2}
                    direction="left"
                    label="shutdown_response { approve: true }"
                    tagLabel={`request_id: ${REQUEST_ID}`}
                    color="#10b981"
                    tagBg={palette.bgSubtle}
                    tagStroke={palette.nodeStroke}
                    tagText={palette.nodeText}
                  />
                )}

                {/* Step 3: exit annotation */}
                {step >= 3 && (
                  <motion.g
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    <line
                      x1={LIFELINE_RIGHT_X - 10}
                      y1={ARROW_Y_START + ARROW_Y_GAP * 2 + 20}
                      x2={LIFELINE_RIGHT_X + 10}
                      y2={ARROW_Y_START + ARROW_Y_GAP * 2 + 36}
                      stroke="#ef4444"
                      strokeWidth={2}
                    />
                    <line
                      x1={LIFELINE_RIGHT_X + 10}
                      y1={ARROW_Y_START + ARROW_Y_GAP * 2 + 20}
                      x2={LIFELINE_RIGHT_X - 10}
                      y2={ARROW_Y_START + ARROW_Y_GAP * 2 + 36}
                      stroke="#ef4444"
                      strokeWidth={2}
                    />
                    <text
                      x={LIFELINE_RIGHT_X + 24}
                      y={ARROW_Y_START + ARROW_Y_GAP * 2 + 32}
                      fontSize={8}
                      fill="#ef4444"
                      fontWeight={600}
                    >
                      exit
                    </text>
                  </motion.g>
                )}
              </g>
            )}

            {protocol === "plan" && (
              <g key="plan">
                {/* Activation bars */}
                {step >= 1 && (
                  <ActivationBar
                    x={LIFELINE_RIGHT_X}
                    yStart={ARROW_Y_START - 10}
                    yEnd={step >= 2 ? ARROW_Y_START + ARROW_Y_GAP * 2 + 15 : ARROW_Y_START + 30}
                    color="#8b5cf6"
                  />
                )}
                {step >= 1 && (
                  <ActivationBar
                    x={LIFELINE_LEFT_X}
                    yStart={ARROW_Y_START - 5}
                    yEnd={step >= 2 ? ARROW_Y_START + ARROW_Y_GAP * 2 + 15 : ARROW_Y_START + ARROW_Y_GAP + 10}
                    color="#3b82f6"
                  />
                )}

                {/* Step 1: plan submission arrow (Teammate -> Leader) */}
                {step >= 1 && (
                  <SequenceArrow
                    y={ARROW_Y_START}
                    direction="left"
                    label="exit_plan_mode { plan }"
                    tagLabel={`request_id: ${REQUEST_ID}`}
                    color="#8b5cf6"
                    tagBg={palette.bgSubtle}
                    tagStroke={palette.nodeStroke}
                    tagText={palette.nodeText}
                  />
                )}

                {/* Step 1: plan content box */}
                {step >= 1 && (
                  <motion.g
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                  >
                    <rect
                      x={20}
                      y={ARROW_Y_START + 20}
                      width={95}
                      height={50}
                      rx={4}
                      fill={palette.bgSubtle}
                      stroke={palette.nodeStroke}
                      strokeWidth={0.5}
                    />
                    <text x={28} y={ARROW_Y_START + 34} fontSize={6} fontFamily="monospace" fill={palette.nodeText} fontWeight={600}>
                      Plan:
                    </text>
                    <text x={28} y={ARROW_Y_START + 44} fontSize={5.5} fontFamily="monospace" fill={palette.labelFill}>
                      1. Add error handler
                    </text>
                    <text x={28} y={ARROW_Y_START + 54} fontSize={5.5} fontFamily="monospace" fill={palette.labelFill}>
                      2. Update tests
                    </text>
                    <text x={28} y={ARROW_Y_START + 64} fontSize={5.5} fontFamily="monospace" fill={palette.labelFill}>
                      3. Refactor module
                    </text>
                  </motion.g>
                )}

                {/* Step 2: approval response arrow (Leader -> Teammate) */}
                {step >= 2 && (
                  <SequenceArrow
                    y={ARROW_Y_START + ARROW_Y_GAP * 2}
                    direction="right"
                    label="plan_approval_response { approve: true }"
                    tagLabel={`request_id: ${REQUEST_ID}`}
                    color="#10b981"
                    tagBg={palette.bgSubtle}
                    tagStroke={palette.nodeStroke}
                    tagText={palette.nodeText}
                  />
                )}

                {/* Step 2: checkmark */}
                {step >= 2 && (
                  <motion.g
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    <circle cx={LIFELINE_RIGHT_X + 40} cy={ARROW_Y_START + ARROW_Y_GAP * 2} r={10} fill="#10b981" />
                    <text
                      x={LIFELINE_RIGHT_X + 40}
                      y={ARROW_Y_START + ARROW_Y_GAP * 2 + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={10}
                      fill="white"
                      fontWeight={700}
                    >
                      OK
                    </text>
                  </motion.g>
                )}
              </g>
            )}
          </AnimatePresence>
        </svg>

        {/* Step controls */}
        <div className="mt-4">
          <StepControls
            currentStep={vis.currentStep}
            totalSteps={vis.totalSteps}
            onPrev={vis.prev}
            onNext={vis.next}
            onReset={vis.reset}
            isPlaying={vis.isPlaying}
            onToggleAutoPlay={vis.toggleAutoPlay}
            stepTitle={steps[step].title}
            stepDescription={steps[step].desc}
          />
        </div>
      </div>
    </section>
  );
}
