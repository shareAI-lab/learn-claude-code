"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

const MODES = [
  { name: "allow", label: "Allow", color: "#10b981", darkLabel: "Auto-approve" },
  { name: "deny", label: "Deny", color: "#ef4444", darkLabel: "Block" },
  { name: "ask", label: "Ask", color: "#f59e0b", darkLabel: "User prompt" },
  { name: "auto_edit", label: "Auto Edit", color: "#8b5cf6", darkLabel: "Rewrite" },
  { name: "edit", label: "Edit", color: "#6366f1", darkLabel: "Suggest edit" },
];

const STEP_INFO = [
  { title: "Permission Spectrum", desc: "Five modes replace the binary allow/deny. Each mode handles a different risk level." },
  { title: "Allow: Safe Commands", desc: "ls, cat, git status -- well-known safe commands bypass the prompt and run immediately." },
  { title: "Deny: Dangerous Patterns", desc: "rm -rf /, :(){ :|:& };: -- catastrophic patterns are blocked unconditionally." },
  { title: "Ask: User Confirmation", desc: "pip install, npm publish -- commands that could have side effects get escalated to the user." },
  { title: "Edit: Auto-Rewrite", desc: "rm -rf build/ becomes rm -r build/ -- the force flag is removed without blocking the operation." },
  { title: "Compound Detection", desc: "ls; rm -rf / -- shell metacharacters (; & | `) trigger a block even if the first token is whitelisted." },
];

const COMMANDS_PER_STEP: (string | null)[] = [
  null,
  "ls -la",
  "rm -rf /",
  "pip install requests",
  "rm -rf build/",
  "ls; rm -rf /",
];

const ACTIVE_MODE_PER_STEP: number[] = [-1, 0, 1, 2, 3, 1];

const SVG_W = 620;
const SVG_H = 340;
const GUARD_X = SVG_W / 2;
const GUARD_Y = 80;
const GUARD_W = 180;
const GUARD_H = 48;
const CARD_Y = 280;
const CARD_W = 100;
const CARD_H = 52;

function getModeX(i: number): number {
  const gap = 16;
  const total = MODES.length * CARD_W + (MODES.length - 1) * gap;
  const start = (SVG_W - total) / 2;
  return start + i * (CARD_W + gap) + CARD_W / 2;
}

export default function PermissionGuard({ title }: { title?: string }) {
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
  const activeMode = ACTIVE_MODE_PER_STEP[currentStep];
  const command = COMMANDS_PER_STEP[currentStep];
  const stepInfo = STEP_INFO[currentStep];

  const rewritten = currentStep === 4 ? "rm -r build/" : null;
  const isCompound = currentStep === 5;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Permission Guard: Five-Mode Classification"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        {/* Command input display */}
        <div className="mb-4 flex min-h-[32px] items-center gap-2">
          <span className="shrink-0 text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Command:
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
                {command}
              </motion.code>
            )}
            {!command && (
              <motion.span
                key="waiting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                className="text-xs text-zinc-400 dark:text-zinc-600"
              >
                waiting for command...
              </motion.span>
            )}
          </AnimatePresence>
          {rewritten && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-xs text-emerald-600 dark:text-emerald-400"
            >
              → {rewritten}
            </motion.span>
          )}
        </div>

        {/* SVG diagram */}
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
          style={{ minHeight: 260 }}
        >
          <defs>
            <filter id="guard-glow">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.6" />
            </filter>
            {MODES.map((m) => (
              <filter key={`glow-${m.name}`} id={`glow-${m.name}`}>
                <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={m.color} floodOpacity="0.6" />
              </filter>
            ))}
            <marker id="pg-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
            </marker>
            <marker id="pg-arrow-dim" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
            </marker>
          </defs>

          {/* PermissionGuard classifier box */}
          <motion.rect
            x={GUARD_X - GUARD_W / 2}
            y={GUARD_Y - GUARD_H / 2}
            width={GUARD_W}
            height={GUARD_H}
            rx={10}
            strokeWidth={2}
            animate={{
              fill: currentStep > 0 ? palette.activeNodeFill : palette.nodeFill,
              stroke: currentStep > 0 ? palette.activeNodeStroke : palette.nodeStroke,
            }}
            filter={currentStep > 0 ? "url(#guard-glow)" : "none"}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={GUARD_X}
            y={GUARD_Y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={13}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: currentStep > 0 ? palette.activeNodeText : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            classify(cmd)
          </motion.text>

          {/* Compound detection warning */}
          {isCompound && (
            <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}>
              <rect
                x={GUARD_X + GUARD_W / 2 + 12}
                y={GUARD_Y - 18}
                width={120}
                height={36}
                rx={6}
                fill="#fef2f2"
                stroke="#ef4444"
                strokeWidth={1.5}
              />
              <text
                x={GUARD_X + GUARD_W / 2 + 72}
                y={GUARD_Y - 4}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={9}
                fontWeight={600}
                fill="#dc2626"
                fontFamily="monospace"
              >
                metachar: ;
              </text>
              <text
                x={GUARD_X + GUARD_W / 2 + 72}
                y={GUARD_Y + 10}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={8}
                fill="#dc2626"
              >
                compound detected
              </text>
            </motion.g>
          )}

          {/* Connection lines */}
          {MODES.map((m, i) => {
            const modeX = getModeX(i);
            const isActive = i === activeMode;
            return (
              <motion.line
                key={`line-${m.name}`}
                x1={GUARD_X}
                y1={GUARD_Y + GUARD_H / 2}
                x2={modeX}
                y2={CARD_Y - CARD_H / 2}
                strokeWidth={isActive ? 2.5 : 1.5}
                markerEnd={isActive ? "url(#pg-arrow)" : "url(#pg-arrow-dim)"}
                animate={{
                  stroke: isActive ? m.color : palette.edgeStroke,
                  strokeWidth: isActive ? 2.5 : 1.5,
                }}
                transition={{ duration: 0.4 }}
              />
            );
          })}

          {/* Mode cards */}
          {MODES.map((m, i) => {
            const modeX = getModeX(i);
            const isActive = i === activeMode;
            return (
              <g key={m.name}>
                <motion.rect
                  x={modeX - CARD_W / 2}
                  y={CARD_Y - CARD_H / 2}
                  width={CARD_W}
                  height={CARD_H}
                  rx={8}
                  strokeWidth={2}
                  animate={{
                    fill: isActive ? m.color : palette.nodeFill,
                    stroke: isActive ? m.color : palette.nodeStroke,
                  }}
                  filter={isActive ? `url(#glow-${m.name})` : "none"}
                  transition={{ duration: 0.4 }}
                />
                <motion.text
                  x={modeX}
                  y={CARD_Y - 6}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={11}
                  fontWeight={700}
                  fontFamily="monospace"
                  animate={{ fill: isActive ? "#ffffff" : palette.nodeText }}
                  transition={{ duration: 0.4 }}
                >
                  {m.label}
                </motion.text>
                <motion.text
                  x={modeX}
                  y={CARD_Y + 12}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={8}
                  fontFamily="sans-serif"
                  animate={{ fill: isActive ? "rgba(255,255,255,0.8)" : palette.labelFill }}
                  transition={{ duration: 0.4 }}
                >
                  {m.darkLabel}
                </motion.text>
              </g>
            );
          })}
        </svg>

        {/* Code snippet */}
        <div className="mt-3 rounded-md bg-zinc-100 px-3 py-2 dark:bg-zinc-800">
          <code className="block font-mono text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-300">
            <span className="text-blue-600 dark:text-blue-400">def</span>{" "}
            <span className="text-emerald-600 dark:text-emerald-400">classify</span>(cmd):
            {"\n  "}
            <span className="text-zinc-500">{"# "}</span>
            {currentStep === 5
              ? "if has_metacharacters(cmd): → deny"
              : currentStep === 4
                ? "if matches(edit_rules): → edit (rewrite)"
                : currentStep === 2
                  ? "if matches(denied): → deny"
                  : currentStep === 1
                    ? "if in whitelist: → allow"
                    : "return mode, reason"}
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
