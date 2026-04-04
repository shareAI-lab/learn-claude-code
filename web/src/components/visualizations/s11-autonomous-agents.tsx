"use client";

import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

// -- FSM states and their layout positions (diamond: idle top, poll right, claim bottom, work left) --
type Phase = "idle" | "poll" | "claim" | "work";

const FSM_CX = 110;
const FSM_CY = 110;
const FSM_R = 65;
const FSM_STATE_R = 22;

const FSM_STATES: { id: Phase; label: string; angle: number }[] = [
  { id: "idle", label: "idle", angle: -Math.PI / 2 },
  { id: "poll", label: "poll", angle: 0 },
  { id: "claim", label: "claim", angle: Math.PI / 2 },
  { id: "work", label: "work", angle: Math.PI },
];

const FSM_TRANSITIONS: { from: Phase; to: Phase }[] = [
  { from: "idle", to: "poll" },
  { from: "poll", to: "claim" },
  { from: "claim", to: "work" },
  { from: "work", to: "idle" },
];

function fsmPos(angle: number) {
  return { x: FSM_CX + FSM_R * Math.cos(angle), y: FSM_CY + FSM_R * Math.sin(angle) };
}

const PHASE_COLORS: Record<Phase, string> = {
  idle: "#a1a1aa",
  poll: "#f59e0b",
  claim: "#3b82f6",
  work: "#10b981",
};

// -- Task board data --
interface TaskRow {
  id: string;
  name: string;
  status: "unclaimed" | "active" | "complete";
  owner: string;
}

const INITIAL_TASKS: TaskRow[] = [
  { id: "T1", name: "Fix auth bug", status: "unclaimed", owner: "-" },
  { id: "T2", name: "Add rate limiter", status: "unclaimed", owner: "-" },
  { id: "T3", name: "Write tests", status: "unclaimed", owner: "-" },
  { id: "T4", name: "Update API docs", status: "unclaimed", owner: "-" },
];

// Agent positions around the task board (left panel)
const BOARD_CX = 140;
const BOARD_CY = 90;
const AGENT_ORBIT = 85;
const AGENT_R = 20;

const AGENT_ANGLES = [-Math.PI / 2, Math.PI / 6, (5 * Math.PI) / 6];

function agentPos(index: number) {
  const angle = AGENT_ANGLES[index];
  return { x: BOARD_CX + AGENT_ORBIT * Math.cos(angle), y: BOARD_CY + AGENT_ORBIT * Math.sin(angle) };
}

// -- Step definitions --
const STEPS = [
  { title: "Self-Governing Agents", desc: "Autonomous agents need no coordinator. They govern themselves with an idle-poll-claim-work cycle." },
  { title: "Idle Timer", desc: "Each idle agent counts rounds. A timeout triggers self-directed task polling." },
  { title: "Poll Task Board", desc: "Timeout! The agent reads the task board looking for unclaimed work." },
  { title: "Claim Task", desc: "The agent writes its name to the task record. Atomic, no conflicts." },
  { title: "Work", desc: "The agent works on the claimed task using its own agent loop." },
  { title: "Independent Polling", desc: "Multiple agents poll and claim independently. No central coordinator needed." },
  { title: "Complete & Reset", desc: "Task done. Agent returns to idle. The cycle repeats." },
  { title: "Self-Organization", desc: "Three agents, zero coordination overhead. Polling + timeout = emergent organization." },
];

// Per-step state for each agent
interface AgentState {
  phase: Phase;
  timerFill: number;
  color: string;
  taskClaim: string | null;
}

function getAgentStates(step: number): AgentState[] {
  const idle: AgentState = { phase: "idle", timerFill: 0, color: PHASE_COLORS.idle, taskClaim: null };

  switch (step) {
    case 0:
      return [
        { ...idle },
        { ...idle },
        { ...idle },
      ];
    case 1:
      return [
        { phase: "idle", timerFill: 0.6, color: PHASE_COLORS.idle, taskClaim: null },
        { ...idle },
        { ...idle },
      ];
    case 2:
      return [
        { phase: "poll", timerFill: 1.0, color: PHASE_COLORS.poll, taskClaim: null },
        { ...idle },
        { ...idle },
      ];
    case 3:
      return [
        { phase: "claim", timerFill: 0, color: PHASE_COLORS.claim, taskClaim: "T1" },
        { ...idle },
        { ...idle },
      ];
    case 4:
      return [
        { phase: "work", timerFill: 0, color: PHASE_COLORS.work, taskClaim: "T1" },
        { ...idle },
        { ...idle },
      ];
    case 5:
      return [
        { phase: "work", timerFill: 0, color: PHASE_COLORS.work, taskClaim: "T1" },
        { phase: "claim", timerFill: 0, color: PHASE_COLORS.claim, taskClaim: "T2" },
        { ...idle },
      ];
    case 6:
      return [
        { phase: "idle", timerFill: 0, color: PHASE_COLORS.idle, taskClaim: null },
        { phase: "work", timerFill: 0, color: PHASE_COLORS.work, taskClaim: "T2" },
        { ...idle },
      ];
    case 7:
      return [
        { phase: "idle", timerFill: 0, color: PHASE_COLORS.idle, taskClaim: null },
        { phase: "work", timerFill: 0, color: PHASE_COLORS.work, taskClaim: "T2" },
        { phase: "claim", timerFill: 0, color: PHASE_COLORS.claim, taskClaim: "T3" },
      ];
    default:
      return [{ ...idle }, { ...idle }, { ...idle }];
  }
}

function getTaskStates(step: number): TaskRow[] {
  const tasks = INITIAL_TASKS.map((t) => ({ ...t }));
  if (step >= 3) { tasks[0].status = "active"; tasks[0].owner = "A"; }
  if (step >= 5) { tasks[1].status = "active"; tasks[1].owner = "B"; }
  if (step >= 6) { tasks[0].status = "complete"; }
  if (step >= 7) { tasks[2].status = "active"; tasks[2].owner = "C"; }
  return tasks;
}

function getActivePhase(step: number): Phase {
  if (step <= 1) return "idle";
  if (step === 2) return "poll";
  if (step === 3) return "claim";
  if (step === 4 || step === 5) return "work";
  if (step === 6) return "idle";
  return "claim";
}

// Ring timer around an agent
function TimerRing({ cx, cy, r, fill }: { cx: number; cy: number; r: number; fill: number }) {
  if (fill <= 0) return null;
  const circumference = 2 * Math.PI * (r + 4);
  const offset = circumference * (1 - fill);
  return (
    <motion.circle
      cx={cx}
      cy={cy}
      r={r + 4}
      fill="none"
      stroke="#f59e0b"
      strokeWidth={3}
      strokeDasharray={circumference}
      strokeDashoffset={offset}
      strokeLinecap="round"
      initial={{ strokeDashoffset: circumference }}
      animate={{ strokeDashoffset: offset }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      style={{ transform: "rotate(-90deg)", transformOrigin: `${cx}px ${cy}px` }}
    />
  );
}

// FSM arrow between two states
function FSMArrow({ from, to, active, inactiveStroke }: { from: Phase; to: Phase; active: boolean; inactiveStroke: string }) {
  const fState = FSM_STATES.find((s) => s.id === from)!;
  const tState = FSM_STATES.find((s) => s.id === to)!;
  const fPos = fsmPos(fState.angle);
  const tPos = fsmPos(tState.angle);

  const dx = tPos.x - fPos.x;
  const dy = tPos.y - fPos.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist;
  const uy = dy / dist;

  const x1 = fPos.x + ux * FSM_STATE_R;
  const y1 = fPos.y + uy * FSM_STATE_R;
  const x2 = tPos.x - ux * (FSM_STATE_R + 6);
  const y2 = tPos.y - uy * (FSM_STATE_R + 6);

  const perpX = -uy * 12;
  const perpY = ux * 12;
  const cx = (x1 + x2) / 2 + perpX;
  const cy = (y1 + y2) / 2 + perpY;

  return (
    <g>
      <path
        d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
        fill="none"
        stroke={active ? PHASE_COLORS[to] : inactiveStroke}
        strokeWidth={active ? 2 : 1}
        markerEnd="url(#fsm-arrowhead)"
      />
    </g>
  );
}

export default function AutonomousAgents({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const palette = useSvgPalette();

  const agentStates = getAgentStates(step);
  const tasks = getTaskStates(step);
  const activePhase = getActivePhase(step);
  const agentNames = ["A", "B", "C"];

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Autonomous Agent Cycle"}
      </h2>
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900 min-h-[500px]">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Left panel: spatial view with agents and task board */}
          <div className="flex-1">
            <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2">Spatial View</div>
            <svg viewBox="0 0 280 240" className="w-full">
              {/* Task board (small table in center) */}
              <rect x={BOARD_CX - 35} y={BOARD_CY - 20} width={70} height={40} rx={4}
                fill={palette.bgSubtle} stroke={palette.nodeStroke} strokeWidth={1}
              />
              <text x={BOARD_CX} y={BOARD_CY - 8} textAnchor="middle" fontSize={7} fontWeight={600}
                fill={palette.nodeText}
              >
                Task Board
              </text>
              <text x={BOARD_CX} y={BOARD_CY + 4} textAnchor="middle" fontSize={6} fontFamily="monospace"
                fill={palette.labelFill}
              >
                {tasks.filter((t) => t.status === "unclaimed").length} unclaimed
              </text>
              <text x={BOARD_CX} y={BOARD_CY + 14} textAnchor="middle" fontSize={6} fontFamily="monospace"
                fill="#10b981"
              >
                {tasks.filter((t) => t.status === "complete").length} complete
              </text>

              {/* Agents */}
              {agentStates.map((state, i) => {
                const pos = agentPos(i);
                const isPulsing = state.phase === "work";
                const isPolling = state.phase === "poll";

                return (
                  <g key={i}>
                    {/* Dashed line from agent to board when polling */}
                    {isPolling && (
                      <motion.line
                        x1={pos.x} y1={pos.y} x2={BOARD_CX} y2={BOARD_CY}
                        stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="4 3"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                      />
                    )}
                    {/* Solid line from agent to board when claiming */}
                    {state.phase === "claim" && (
                      <motion.line
                        x1={pos.x} y1={pos.y} x2={BOARD_CX} y2={BOARD_CY}
                        stroke="#3b82f6" strokeWidth={2}
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                      />
                    )}

                    {/* Timer ring */}
                    <TimerRing cx={pos.x} cy={pos.y} r={AGENT_R} fill={state.timerFill} />

                    {/* Agent circle */}
                    <motion.circle
                      cx={pos.x} cy={pos.y} r={AGENT_R}
                      fill={state.color}
                      stroke={state.phase === "work" ? "#059669" : palette.nodeStroke}
                      strokeWidth={1.5}
                      animate={{
                        scale: isPulsing ? [1, 1.1, 1] : 1,
                        fill: state.color,
                      }}
                      transition={
                        isPulsing
                          ? { duration: 0.8, repeat: Infinity, ease: "easeInOut" }
                          : { duration: 0.4 }
                      }
                    />
                    <text x={pos.x} y={pos.y + 1} textAnchor="middle" dominantBaseline="middle"
                      fill="white" fontSize={11} fontWeight={700}
                    >
                      {agentNames[i]}
                    </text>

                    {/* Task label below agent when claiming or working */}
                    {state.taskClaim && (
                      <motion.text
                        x={pos.x} y={pos.y + AGENT_R + 12}
                        textAnchor="middle" fontSize={7} fontFamily="monospace"
                        fill={state.phase === "work" ? "#10b981" : "#3b82f6"}
                        fontWeight={600}
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                      >
                        {state.taskClaim}
                      </motion.text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Task table below the spatial view */}
            <div className="mt-2 border border-zinc-200 rounded dark:border-zinc-700 overflow-hidden">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="bg-zinc-50 dark:bg-zinc-800">
                    <th className="px-2 py-1 text-left font-medium text-zinc-500 dark:text-zinc-400">Task</th>
                    <th className="px-2 py-1 text-left font-medium text-zinc-500 dark:text-zinc-400">Status</th>
                    <th className="px-2 py-1 text-left font-medium text-zinc-500 dark:text-zinc-400">Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id} className="border-t border-zinc-100 dark:border-zinc-800">
                      <td className="px-2 py-1 font-mono text-zinc-700 dark:text-zinc-300">{task.name}</td>
                      <td className="px-2 py-1">
                        <span className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-medium ${
                          task.status === "complete"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                            : task.status === "active"
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                              : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                        }`}>
                          {task.status}
                        </span>
                      </td>
                      <td className="px-2 py-1 font-mono text-zinc-600 dark:text-zinc-400">{task.owner}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right panel: FSM state machine diagram */}
          <div className="flex-1">
            <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2">FSM Cycle</div>
            <svg viewBox="0 0 220 220" className="w-full">
              <defs>
                <marker
                  id="fsm-arrowhead"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill={palette.arrowFill} />
                </marker>
              </defs>

              {/* Transition arrows */}
              {FSM_TRANSITIONS.map((t) => {
                const isActive =
                  (activePhase === t.from) ||
                  (activePhase === t.to && t.from === FSM_TRANSITIONS.find((tr) => tr.to === activePhase)?.from);
                return (
                  <FSMArrow
                    key={`${t.from}-${t.to}`}
                    from={t.from}
                    to={t.to}
                    active={isActive}
                    inactiveStroke={palette.nodeStroke}
                  />
                );
              })}

              {/* State circles */}
              {FSM_STATES.map((state) => {
                const pos = fsmPos(state.angle);
                const isActive = state.id === activePhase;
                return (
                  <g key={state.id}>
                    <motion.circle
                      cx={pos.x}
                      cy={pos.y}
                      r={FSM_STATE_R}
                      fill={isActive ? PHASE_COLORS[state.id] : palette.nodeFill}
                      stroke={isActive ? PHASE_COLORS[state.id] : palette.nodeStroke}
                      strokeWidth={isActive ? 2 : 1}
                      animate={{
                        fill: isActive ? PHASE_COLORS[state.id] : palette.nodeFill,
                        scale: isActive ? 1.1 : 1,
                      }}
                      transition={{ duration: 0.4 }}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={9}
                      fontWeight={600}
                      fill={isActive ? "white" : palette.nodeText}
                    >
                      {state.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div className="mt-2 flex flex-wrap gap-3 justify-center">
              {FSM_STATES.map((s) => (
                <div key={s.id} className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PHASE_COLORS[s.id] }} />
                  <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">{s.label}</span>
                </div>
              ))}
            </div>
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
