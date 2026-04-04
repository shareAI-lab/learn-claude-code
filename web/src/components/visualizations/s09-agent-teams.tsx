"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

// -- Layout constants --
const SVG_W = 560;
const SVG_H = 340;
const AGENT_R = 40;

// Agent positions: inverted triangle (Lead top-center, Coder bottom-left, Reviewer bottom-right)
const AGENTS = [
  { id: "lead", label: "Lead", cx: SVG_W / 2, cy: 70, inbox: "lead.jsonl" },
  { id: "coder", label: "Coder", cx: 140, cy: 230, inbox: "coder.jsonl" },
  { id: "reviewer", label: "Reviewer", cx: SVG_W - 140, cy: 230, inbox: "reviewer.jsonl" },
] as const;

// Inbox tray dimensions, positioned below each agent circle
const TRAY_W = 72;
const TRAY_H = 22;
const TRAY_OFFSET_Y = AGENT_R + 14;

// Message block dimensions
const MSG_W = 60;
const MSG_H = 20;

function agentById(id: string) {
  return AGENTS.find((a) => a.id === id)!;
}

function trayCenter(id: string) {
  const a = agentById(id);
  return { x: a.cx, y: a.cy + TRAY_OFFSET_Y + TRAY_H / 2 };
}

// Step configuration
const STEPS = [
  { title: "The Team", desc: "Teams use a leader-worker pattern. Each teammate has a file-based mailbox inbox." },
  { title: "Lead Assigns Work", desc: "Communication is async: write a message to the recipient's .jsonl inbox file." },
  { title: "Read Inbox", desc: "Teammates poll their inbox before each LLM call. New messages become context." },
  { title: "Independent Work", desc: "Each teammate runs its own agent loop independently." },
  { title: "Pass Result", desc: "Results flow through the same mailbox mechanism. All communication is via files." },
  { title: "Feedback Loop", desc: "The mailbox pattern supports any communication topology: linear, broadcast, round-robin." },
  { title: "File-Based Coordination", desc: "No shared memory, no locks. All coordination through append-only files. Simple, robust, debuggable." },
];

// Helper: determine which agent glows at each step
function agentGlows(agentId: string, step: number): boolean {
  if (step === 1 && agentId === "lead") return true;
  if (step === 2 && agentId === "coder") return true;
  if (step === 3 && agentId === "coder") return true;
  if (step === 4 && agentId === "coder") return true;
  if (step === 5 && agentId === "reviewer") return true;
  return false;
}

// Helper: determine which inbox tray has a message sitting in it
function trayHasMessage(agentId: string, step: number): boolean {
  if (step === 2 && agentId === "coder") return true;
  if (step === 4 && agentId === "reviewer") return false;
  if (step === 5 && agentId === "reviewer") return true;
  return false;
}

// Animated message that travels from one point to another
function TravelingMessage({
  fromX,
  fromY,
  toX,
  toY,
  label,
  delay = 0,
}: {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  label: string;
  delay?: number;
}) {
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0, 1, 1, 0.8],
        x: [fromX - MSG_W / 2, fromX - MSG_W / 2, toX - MSG_W / 2, toX - MSG_W / 2],
        y: [fromY - MSG_H / 2, fromY - MSG_H / 2, toY - MSG_H / 2, toY - MSG_H / 2],
      }}
      transition={{
        duration: 1.4,
        delay,
        times: [0, 0.1, 0.7, 1],
        ease: "easeInOut",
      }}
    >
      <rect width={MSG_W} height={MSG_H} rx={4} fill="#f59e0b" />
      <text
        x={MSG_W / 2}
        y={MSG_H / 2 + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="white"
        fontSize={8}
        fontWeight={600}
      >
        {label}
      </text>
    </motion.g>
  );
}

// Faded trace line between two agents
function TraceLine({ from, to, strokeColor }: { from: string; to: string; strokeColor: string }) {
  const f = trayCenter(from);
  const t = trayCenter(to);
  return (
    <motion.line
      x1={f.x}
      y1={f.y}
      x2={t.x}
      y2={t.y}
      stroke={strokeColor}
      strokeWidth={1.5}
      strokeDasharray="6 4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.4 }}
      transition={{ duration: 0.6 }}
    />
  );
}

export default function AgentTeams({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const palette = useSvgPalette();

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Agent Team Mailboxes"}
      </h2>
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900 min-h-[500px]">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* SVG visualization */}
          <div className="flex-1">
            <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full">
              <defs>
                <filter id="agent-glow">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Step 6: trace lines */}
              {step === 6 && (
                <>
                  <TraceLine from="lead" to="coder" strokeColor={palette.edgeStroke} />
                  <TraceLine from="coder" to="reviewer" strokeColor={palette.edgeStroke} />
                  <TraceLine from="reviewer" to="lead" strokeColor={palette.edgeStroke} />
                </>
              )}

              {/* Agent nodes */}
              {AGENTS.map((agent) => {
                const glowing = agentGlows(agent.id, step);
                const pulsing = step === 3 && agent.id === "coder";

                return (
                  <g key={agent.id}>
                    {/* Agent circle */}
                    <motion.circle
                      cx={agent.cx}
                      cy={agent.cy}
                      r={AGENT_R}
                      fill={glowing ? "#3b82f6" : palette.edgeStroke}
                      stroke={glowing ? "#60a5fa" : palette.labelFill}
                      strokeWidth={2}
                      animate={{
                        scale: pulsing ? [1, 1.08, 1] : 1,
                        fill: glowing ? "#3b82f6" : palette.edgeStroke,
                      }}
                      transition={
                        pulsing
                          ? { duration: 0.8, repeat: Infinity, ease: "easeInOut" }
                          : { duration: 0.4 }
                      }
                      filter={glowing ? "url(#agent-glow)" : undefined}
                    />
                    {/* Agent label */}
                    <text
                      x={agent.cx}
                      y={agent.cy + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize={12}
                      fontWeight={700}
                    >
                      {agent.label}
                    </text>

                    {/* Inbox tray (file icon style) */}
                    <rect
                      x={agent.cx - TRAY_W / 2}
                      y={agent.cy + TRAY_OFFSET_Y}
                      width={TRAY_W}
                      height={TRAY_H}
                      rx={3}
                      fill={trayHasMessage(agent.id, step) ? "#fef3c7" : palette.nodeFill}
                      stroke={trayHasMessage(agent.id, step) ? "#f59e0b" : palette.nodeStroke}
                      strokeWidth={1}
                    />
                    <text
                      x={agent.cx}
                      y={agent.cy + TRAY_OFFSET_Y + TRAY_H / 2 + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={8}
                      fontFamily="monospace"
                      fill={palette.labelFill}
                    >
                      {agent.inbox}
                    </text>
                  </g>
                );
              })}

              {/* Step 0: team config card */}
              {step === 0 && (
                <motion.g
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <rect x={12} y={12} width={100} height={44} rx={4} fill="#f0f9ff" stroke="#bae6fd" strokeWidth={1} />
                  <text x={20} y={28} fontSize={7} fontFamily="monospace" fill="#0284c7" fontWeight={600}>
                    team.config
                  </text>
                  <text x={20} y={40} fontSize={6} fontFamily="monospace" fill="#0369a1">
                    workers: [coder, reviewer]
                  </text>
                </motion.g>
              )}

              {/* Step 1: message from Lead to Coder inbox */}
              <AnimatePresence>
                {step === 1 && (
                  <TravelingMessage
                    key="msg-lead-coder"
                    fromX={agentById("lead").cx}
                    fromY={agentById("lead").cy + AGENT_R}
                    toX={agentById("coder").cx}
                    toY={agentById("coder").cy + TRAY_OFFSET_Y + TRAY_H / 2}
                    label="task:login"
                  />
                )}
              </AnimatePresence>

              {/* Step 2: message from Coder inbox to Coder circle */}
              <AnimatePresence>
                {step === 2 && (
                  <TravelingMessage
                    key="msg-inbox-coder"
                    fromX={agentById("coder").cx}
                    fromY={agentById("coder").cy + TRAY_OFFSET_Y + TRAY_H / 2}
                    toX={agentById("coder").cx}
                    toY={agentById("coder").cy}
                    label="task:login"
                  />
                )}
              </AnimatePresence>

              {/* Step 3: Coder working, result appears */}
              <AnimatePresence>
                {step === 3 && (
                  <motion.g
                    key="result-msg"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8, duration: 0.4 }}
                  >
                    <rect
                      x={agentById("coder").cx + AGENT_R + 8}
                      y={agentById("coder").cy - MSG_H / 2}
                      width={MSG_W + 10}
                      height={MSG_H}
                      rx={4}
                      fill="#10b981"
                    />
                    <text
                      x={agentById("coder").cx + AGENT_R + 8 + (MSG_W + 10) / 2}
                      y={agentById("coder").cy + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize={8}
                      fontWeight={600}
                    >
                      result:done
                    </text>
                  </motion.g>
                )}
              </AnimatePresence>

              {/* Step 4: Coder result message travels to Reviewer inbox */}
              <AnimatePresence>
                {step === 4 && (
                  <TravelingMessage
                    key="msg-coder-reviewer"
                    fromX={agentById("coder").cx + AGENT_R + 8 + (MSG_W + 10) / 2}
                    fromY={agentById("coder").cy}
                    toX={agentById("reviewer").cx}
                    toY={agentById("reviewer").cy + TRAY_OFFSET_Y + TRAY_H / 2}
                    label="result:done"
                  />
                )}
              </AnimatePresence>

              {/* Step 5: Reviewer reads inbox, sends feedback to Lead */}
              <AnimatePresence>
                {step === 5 && (
                  <>
                    <TravelingMessage
                      key="msg-reviewer-read"
                      fromX={agentById("reviewer").cx}
                      fromY={agentById("reviewer").cy + TRAY_OFFSET_Y + TRAY_H / 2}
                      toX={agentById("reviewer").cx}
                      toY={agentById("reviewer").cy}
                      label="result:done"
                      delay={0}
                    />
                    <TravelingMessage
                      key="msg-reviewer-lead"
                      fromX={agentById("reviewer").cx}
                      fromY={agentById("reviewer").cy}
                      toX={agentById("lead").cx}
                      toY={agentById("lead").cy + TRAY_OFFSET_Y + TRAY_H / 2}
                      label="feedback"
                      delay={1.0}
                    />
                  </>
                )}
              </AnimatePresence>

              {/* Step 6: filesystem tree */}
              {step === 6 && (
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6 }}
                >
                  <rect x={SVG_W / 2 - 110} y={SVG_H - 80} width={220} height={68} rx={6} fill={palette.bgSubtle} stroke={palette.nodeStroke} strokeWidth={1} />
                  <text x={SVG_W / 2 - 96} y={SVG_H - 60} fontSize={8} fontFamily="monospace" fill={palette.labelFill}>
                    .claude/teams/project/
                  </text>
                  <text x={SVG_W / 2 - 82} y={SVG_H - 48} fontSize={8} fontFamily="monospace" fill="#60a5fa">
                    lead.jsonl
                  </text>
                  <text x={SVG_W / 2 - 82} y={SVG_H - 36} fontSize={8} fontFamily="monospace" fill="#60a5fa">
                    coder.jsonl
                  </text>
                  <text x={SVG_W / 2 - 82} y={SVG_H - 24} fontSize={8} fontFamily="monospace" fill="#60a5fa">
                    reviewer.jsonl
                  </text>
                </motion.g>
              )}
            </svg>
          </div>
        </div>

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
            stepTitle={STEPS[step].title}
            stepDescription={STEPS[step].desc}
          />
        </div>
      </div>
    </section>
  );
}
