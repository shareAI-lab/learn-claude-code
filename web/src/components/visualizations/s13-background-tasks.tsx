"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useDarkMode, useSvgPalette } from "@/hooks/useDarkMode";

interface StepInfo {
  title: string;
  description: string;
}

const STEP_INFO: StepInfo[] = [
  {
    title: "Three Lanes",
    description:
      "The agent has a main thread and can spawn daemon background threads for parallel work.",
  },
  {
    title: "Main Thread Working",
    description:
      "The main agent loop runs as usual, processing user requests.",
  },
  {
    title: "Spawn Background",
    description:
      "Background tasks run as daemon threads. The main loop doesn't wait for them.",
  },
  {
    title: "Multiple Backgrounds",
    description: "Multiple background tasks can run concurrently.",
  },
  {
    title: "Task Completes",
    description:
      "Background task finishes. Its result goes to the notification queue.",
  },
  {
    title: "Queue Fills",
    description:
      "Results accumulate in the queue, invisible to the model during this turn.",
  },
  {
    title: "Drain Queue",
    description:
      "Just before the next LLM call, all queued notifications are injected as tool_results. Non-blocking, async.",
  },
];

const LANE_Y = {
  main: 60,
  bg1: 140,
  bg2: 220,
} as const;

const LANE_HEIGHT = 44;
const TIMELINE_LEFT = 160;
const TIMELINE_RIGHT = 720;
const TIMELINE_WIDTH = TIMELINE_RIGHT - TIMELINE_LEFT;

const QUEUE_Y = 300;

interface WorkBlock {
  lane: "main" | "bg1" | "bg2";
  startFraction: number;
  endFraction: number;
  color: string;
  label?: string;
  appearsAtStep: number;
  completesAtStep?: number;
}

const WORK_BLOCKS: WorkBlock[] = [
  {
    lane: "main",
    startFraction: 0,
    endFraction: 1,
    color: "#8b5cf6",
    label: "Main agent loop",
    appearsAtStep: 1,
  },
  {
    lane: "bg1",
    startFraction: 0.18,
    endFraction: 0.75,
    color: "#10b981",
    label: "Run tests",
    appearsAtStep: 2,
    completesAtStep: 5,
  },
  {
    lane: "bg2",
    startFraction: 0.35,
    endFraction: 0.58,
    color: "#3b82f6",
    label: "Lint code",
    appearsAtStep: 3,
    completesAtStep: 4,
  },
];

interface ForkArrow {
  fromFraction: number;
  toLane: "bg1" | "bg2";
  appearsAtStep: number;
}

const FORK_ARROWS: ForkArrow[] = [
  { fromFraction: 0.18, toLane: "bg1", appearsAtStep: 2 },
  { fromFraction: 0.35, toLane: "bg2", appearsAtStep: 3 },
];

interface QueueCard {
  id: string;
  label: string;
  appearsAtStep: number;
  drainsAtStep: number;
}

const QUEUE_CARDS: QueueCard[] = [
  {
    id: "lint-result",
    label: "Lint: 0 errors",
    appearsAtStep: 4,
    drainsAtStep: 6,
  },
  {
    id: "test-result",
    label: "Tests: 42 passed",
    appearsAtStep: 5,
    drainsAtStep: 6,
  },
];

function fractionToX(fraction: number): number {
  return TIMELINE_LEFT + fraction * TIMELINE_WIDTH;
}

function getBlockEndFraction(block: WorkBlock, step: number): number {
  if (step < block.appearsAtStep) return block.startFraction;
  if (block.completesAtStep !== undefined && step >= block.completesAtStep) {
    return block.endFraction;
  }
  const growthSteps = (block.completesAtStep ?? 6) - block.appearsAtStep;
  const stepsElapsed = step - block.appearsAtStep;
  const progress = Math.min(stepsElapsed / growthSteps, 1);
  const range = block.endFraction - block.startFraction;
  return block.startFraction + range * progress;
}

export default function BackgroundTasks({ title }: { title?: string }) {
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: 7, autoPlayInterval: 2500 });

  const isDark = useDarkMode();
  const palette = useSvgPalette();

  const stepInfo = STEP_INFO[currentStep];

  const llmCallFraction = 0.82;
  const showLlmMarker = currentStep >= 5;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Background Task Lanes"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <svg viewBox="0 0 780 380" className="w-full" aria-label="Background task lanes">
          <defs>
            <marker
              id="forkArrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={palette.arrowFill} />
            </marker>
            <marker
              id="drainArrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
            </marker>
            <filter id="blockGlow" x="-10%" y="-20%" width="120%" height="140%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feFlood floodColor="#8b5cf6" floodOpacity="0.2" result="color" />
              <feComposite in="color" in2="blur" operator="in" result="glow" />
              <feMerge>
                <feMergeNode in="glow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Timeline axis */}
          <line
            x1={TIMELINE_LEFT}
            y1={30}
            x2={TIMELINE_RIGHT}
            y2={30}
            stroke={palette.labelFill}
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.5}
          />
          <text
            x={TIMELINE_LEFT}
            y={22}
            fontSize="9"
            fontFamily="monospace"
            fill={palette.labelFill}
          >
            t=0
          </text>
          <text
            x={TIMELINE_RIGHT}
            y={22}
            fontSize="9"
            fontFamily="monospace"
            fill={palette.labelFill}
            textAnchor="end"
          >
            time
          </text>

          {/* Lane backgrounds and labels */}
          {(
            [
              { key: "main", y: LANE_Y.main, label: "Main Thread" },
              { key: "bg1", y: LANE_Y.bg1, label: "Background 1" },
              { key: "bg2", y: LANE_Y.bg2, label: "Background 2" },
            ] as const
          ).map(({ key, y, label }) => (
            <g key={key}>
              <rect
                x={TIMELINE_LEFT}
                y={y}
                width={TIMELINE_WIDTH}
                height={LANE_HEIGHT}
                rx={6}
                fill="none"
                stroke={palette.nodeStroke}
                strokeWidth={1}
                strokeDasharray="4 2"
                opacity={0.6}
              />
              <text
                x={TIMELINE_LEFT - 10}
                y={y + LANE_HEIGHT / 2 + 1}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize="11"
                fontWeight="600"
                fill={palette.labelFill}
              >
                {label}
              </text>
            </g>
          ))}

          {/* Work blocks */}
          {WORK_BLOCKS.map((block) => {
            if (currentStep < block.appearsAtStep) return null;

            const startX = fractionToX(block.startFraction);
            const endFraction = getBlockEndFraction(block, currentStep);
            const endX = fractionToX(endFraction);
            const width = Math.max(endX - startX, 4);
            const y = LANE_Y[block.lane];
            const isComplete =
              block.completesAtStep !== undefined &&
              currentStep >= block.completesAtStep;

            return (
              <motion.g key={`${block.lane}-block`}>
                <motion.rect
                  x={startX}
                  y={y + 4}
                  height={LANE_HEIGHT - 8}
                  rx={5}
                  initial={{ width: 4 }}
                  animate={{
                    width,
                    opacity: isComplete ? 0.7 : 1,
                  }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  fill={block.color}
                  filter={
                    !isComplete && block.lane === "main"
                      ? "url(#blockGlow)"
                      : undefined
                  }
                />
                {width > 60 && block.label && (
                  <motion.text
                    x={startX + width / 2}
                    y={y + LANE_HEIGHT / 2 + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="10"
                    fontWeight="500"
                    fill="white"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    {block.label}
                  </motion.text>
                )}
                {isComplete && (
                  <motion.text
                    x={endX + 6}
                    y={y + LANE_HEIGHT / 2 + 1}
                    dominantBaseline="middle"
                    fontSize="9"
                    fontFamily="monospace"
                    fill="#10b981"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    done
                  </motion.text>
                )}
              </motion.g>
            );
          })}

          {/* Fork arrows from main to background lanes */}
          {FORK_ARROWS.map((arrow) => {
            if (currentStep < arrow.appearsAtStep) return null;
            const x = fractionToX(arrow.fromFraction);
            const fromY = LANE_Y.main + LANE_HEIGHT;
            const toY = LANE_Y[arrow.toLane];

            return (
              <motion.line
                key={`fork-${arrow.toLane}`}
                x1={x}
                y1={fromY}
                x2={x + 20}
                y2={toY}
                stroke={palette.arrowFill}
                strokeWidth={1.5}
                markerEnd="url(#forkArrow)"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4 }}
              />
            );
          })}

          {/* LLM API call marker */}
          {showLlmMarker && (
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
            >
              <line
                x1={fractionToX(llmCallFraction)}
                y1={LANE_Y.main}
                x2={fractionToX(llmCallFraction)}
                y2={LANE_Y.main + LANE_HEIGHT}
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="3 2"
              />
              <rect
                x={fractionToX(llmCallFraction) - 36}
                y={LANE_Y.main - 16}
                width={72}
                height={16}
                rx={3}
                fill="#f59e0b"
              />
              <text
                x={fractionToX(llmCallFraction)}
                y={LANE_Y.main - 6}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="8"
                fontWeight="600"
                fill="white"
              >
                LLM API call
              </text>
            </motion.g>
          )}

          {/* Notification queue area */}
          <rect
            x={TIMELINE_LEFT}
            y={QUEUE_Y}
            width={TIMELINE_WIDTH}
            height={54}
            rx={8}
            fill="none"
            stroke={palette.nodeStroke}
            strokeWidth={1}
          />
          <text
            x={TIMELINE_LEFT - 10}
            y={QUEUE_Y + 18}
            textAnchor="end"
            fontSize="10"
            fontWeight="600"
            fill={palette.labelFill}
          >
            Notification
          </text>
          <text
            x={TIMELINE_LEFT - 10}
            y={QUEUE_Y + 32}
            textAnchor="end"
            fontSize="10"
            fontWeight="600"
            fill={palette.labelFill}
          >
            Queue
          </text>

          {/* Queue cards */}
          <AnimatePresence>
            {QUEUE_CARDS.map((card, idx) => {
              if (currentStep < card.appearsAtStep) return null;
              const isDraining = currentStep >= card.drainsAtStep;
              const cardX = TIMELINE_LEFT + 20 + idx * 150;
              const cardY = QUEUE_Y + 10;
              const drainTargetY = LANE_Y.main + LANE_HEIGHT / 2 - 12;
              const drainTargetX = fractionToX(llmCallFraction) + 10 + idx * 15;

              if (isDraining) {
                return (
                  <motion.g
                    key={`card-${card.id}-drain`}
                    initial={{ x: cardX, y: cardY, opacity: 1 }}
                    animate={{
                      x: drainTargetX,
                      y: drainTargetY,
                      opacity: [1, 1, 0],
                    }}
                    transition={{ duration: 0.8, ease: "easeInOut" }}
                  >
                    <rect
                      x={0}
                      y={0}
                      width={130}
                      height={34}
                      rx={5}
                      fill={isDark ? "#451a0340" : "#fef3c7"}
                      stroke="#f59e0b"
                      strokeWidth={1}
                    />
                    <text
                      x={65}
                      y={13}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize="9"
                      fontWeight="600"
                      fill={isDark ? "#fbbf24" : "#b45309"}
                    >
                      tool_result
                    </text>
                    <text
                      x={65}
                      y={26}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize="8"
                      fontFamily="monospace"
                      fill={isDark ? "#f59e0b" : "#92400e"}
                    >
                      {card.label}
                    </text>
                  </motion.g>
                );
              }

              return (
                <motion.g
                  key={`card-${card.id}`}
                  initial={{ y: cardY - 40, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                >
                  <rect
                    x={cardX}
                    y={cardY}
                    width={130}
                    height={34}
                    rx={5}
                    fill={isDark ? "#06402740" : "#d1fae5"}
                    stroke="#10b981"
                    strokeWidth={1}
                  />
                  <text
                    x={cardX + 65}
                    y={cardY + 13}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="9"
                    fontWeight="600"
                    fill={isDark ? "#34d399" : "#047857"}
                  >
                    tool_result
                  </text>
                  <text
                    x={cardX + 65}
                    y={cardY + 26}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="8"
                    fontFamily="monospace"
                    fill={isDark ? "#10b981" : "#065f46"}
                  >
                    {card.label}
                  </text>
                </motion.g>
              );
            })}
          </AnimatePresence>

          {/* Drain arrows from queue to main thread at step 6 */}
          {currentStep >= 6 && (
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <motion.line
                x1={fractionToX(llmCallFraction) + 20}
                y1={QUEUE_Y}
                x2={fractionToX(llmCallFraction) + 20}
                y2={LANE_Y.main + LANE_HEIGHT + 4}
                stroke="#f59e0b"
                strokeWidth={1.5}
                markerEnd="url(#drainArrow)"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5 }}
              />
            </motion.g>
          )}

          {/* Empty queue label when drained */}
          {currentStep >= 6 && (
            <motion.text
              x={TIMELINE_LEFT + TIMELINE_WIDTH / 2}
              y={QUEUE_Y + 30}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="10"
              fontFamily="monospace"
              fill={palette.labelFill}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              queue drained -- injected into next LLM call
            </motion.text>
          )}
        </svg>

        {/* Legend */}
        <div className="mt-3 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded" style={{ background: "#8b5cf6" }} />
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
              Main thread
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded" style={{ background: "#10b981" }} />
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
              Background 1
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded" style={{ background: "#3b82f6" }} />
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
              Background 2
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded" style={{ background: "#f59e0b" }} />
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
              LLM boundary
            </span>
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
        stepDescription={stepInfo.description}
      />
    </section>
  );
}
