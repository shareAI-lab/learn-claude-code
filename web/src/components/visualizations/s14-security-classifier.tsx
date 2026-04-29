"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";

const STEP_INFO = [
  { title: "Two-Layer Pipeline", desc: "Layer 1 (regex) catches known patterns at zero cost. Layer 2 (LLM) handles the rest." },
  { title: "Layer 1: Regex Hit", desc: "rm -rf / matches a dangerous pattern. Blocked immediately with zero API cost." },
  { title: "Layer 1: Whitelist", desc: "ls is on the safe list. Auto-approved without reaching Layer 2." },
  { title: "Layer 1: Miss → Escalate", desc: "curl example.com doesn't match any pattern. Escalated to Layer 2 for semantic analysis." },
  { title: "Layer 2: LLM Classify", desc: "The LLM analyzes intent and returns a level (safe/moderate/dangerous) with a source tag." },
  { title: "Fallback: Moderate Default", desc: "When the LLM fails (timeout, API error), it defaults to moderate → ask mode. Safe by default." },
];

const COMMANDS: (string | null)[] = [
  null,
  "rm -rf /",
  "ls -la",
  "curl example.com",
  "curl example.com",
  "some-command",
];

const SOURCES: (string | null)[] = [
  null, "pattern", "whitelist", null, "llm", "fallback",
];

const RESULTS: (string | null)[] = [
  null, "dangerous → deny", "safe → allow", null, "moderate → ask", "moderate → ask",
];

const SVG_W = 620;
const SVG_H = 380;
const INPUT_X = 100;
const INPUT_Y = 60;
const L1_X = 310;
const L1_Y = 140;
const L2_X = 310;
const L2_Y = 270;
const RESULT_X = 520;
const RESULT_Y = 200;
const BOX_W = 160;
const BOX_H = 48;

export default function SecurityClassifier({ title }: { title?: string }) {
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
  const source = SOURCES[currentStep];
  const result = RESULTS[currentStep];
  const stepInfo = STEP_INFO[currentStep];

  // Layer activity
  const l1Active = currentStep >= 1 && currentStep <= 3;
  const l2Active = currentStep === 4 || currentStep === 5;
  const resultActive = currentStep >= 1;

  // L1 outcome
  const l1Hit = currentStep === 1 || currentStep === 2;
  const l1Miss = currentStep === 3;

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Security Classifier: Regex + LLM Pipeline"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        {/* Command input */}
        <div className="mb-4 flex min-h-[32px] items-center gap-2">
          <span className="shrink-0 text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Input:
          </span>
          <AnimatePresence mode="wait">
            {command && (
              <motion.code
                key={command + currentStep}
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
                command enters pipeline...
              </motion.span>
            )}
          </AnimatePresence>
          {source && (
            <motion.span
              key={source}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded bg-cyan-100 px-2 py-0.5 text-[10px] font-semibold text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300"
            >
              source: {source}
            </motion.span>
          )}
        </div>

        {/* SVG pipeline diagram */}
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
          style={{ minHeight: 280 }}
        >
          <defs>
            <filter id="sc-glow-blue">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.6" />
            </filter>
            <filter id="sc-glow-amber">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#f59e0b" floodOpacity="0.6" />
            </filter>
            <filter id="sc-glow-purple">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#8b5cf6" floodOpacity="0.6" />
            </filter>
            <marker id="sc-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
            </marker>
            <marker id="sc-arrow-dim" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
            </marker>
          </defs>

          {/* Input node */}
          <motion.rect
            x={INPUT_X - BOX_W / 2}
            y={INPUT_Y - BOX_H / 2}
            width={BOX_W}
            height={BOX_H}
            rx={8}
            strokeWidth={2}
            animate={{
              fill: currentStep > 0 ? palette.activeNodeFill : palette.nodeFill,
              stroke: currentStep > 0 ? palette.activeNodeStroke : palette.nodeStroke,
            }}
            filter={currentStep > 0 ? "url(#sc-glow-blue)" : "none"}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={INPUT_X}
            y={INPUT_Y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={12}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: currentStep > 0 ? palette.activeNodeText : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            command
          </motion.text>

          {/* Input → L1 line */}
          <motion.line
            x1={INPUT_X + BOX_W / 2}
            y1={INPUT_Y}
            x2={L1_X - BOX_W / 2}
            y2={L1_Y}
            strokeWidth={l1Active ? 2.5 : 1.5}
            markerEnd={l1Active ? "url(#sc-arrow)" : "url(#sc-arrow-dim)"}
            animate={{ stroke: l1Active ? palette.activeEdgeStroke : palette.edgeStroke }}
            transition={{ duration: 0.4 }}
          />

          {/* Layer 1: Regex */}
          <motion.rect
            x={L1_X - BOX_W / 2}
            y={L1_Y - BOX_H / 2}
            width={BOX_W}
            height={BOX_H}
            rx={10}
            strokeWidth={2}
            animate={{
              fill: l1Active ? "#f59e0b" : palette.nodeFill,
              stroke: l1Active ? "#d97706" : palette.nodeStroke,
            }}
            filter={l1Active ? "url(#sc-glow-amber)" : "none"}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={L1_X}
            y={L1_Y - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={11}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: l1Active ? "#ffffff" : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            Layer 1: Regex
          </motion.text>
          <motion.text
            x={L1_X}
            y={L1_Y + 12}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={8}
            animate={{ fill: l1Active ? "rgba(255,255,255,0.8)" : palette.labelFill }}
            transition={{ duration: 0.4 }}
          >
            zero cost · pattern match
          </motion.text>

          {/* L1 hit label */}
          {l1Hit && (
            <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
              <rect x={L1_X + BOX_W / 2 + 8} y={L1_Y - 14} width={80} height={28} rx={6} fill="#fef2f2" stroke="#ef4444" strokeWidth={1} />
              <text x={L1_X + BOX_W / 2 + 48} y={L1_Y} textAnchor="middle" dominantBaseline="middle" fontSize={9} fontWeight={600} fill="#dc2626" fontFamily="monospace">
                {currentStep === 1 ? "PATTERN HIT" : "WHITELIST"}
              </text>
            </motion.g>
          )}

          {/* L1 → Result (when hit) */}
          <motion.line
            x1={L1_X + BOX_W / 2}
            y1={L1_Y}
            x2={RESULT_X - BOX_W / 2}
            y2={RESULT_Y}
            strokeWidth={l1Hit ? 2.5 : 1}
            markerEnd={l1Hit ? "url(#sc-arrow)" : "url(#sc-arrow-dim)"}
            animate={{ stroke: l1Hit ? palette.activeEdgeStroke : palette.edgeStroke, opacity: l1Hit || currentStep === 0 ? 1 : 0.3 }}
            transition={{ duration: 0.4 }}
          />

          {/* L1 → L2 line */}
          <motion.line
            x1={L1_X}
            y1={L1_Y + BOX_H / 2}
            x2={L2_X}
            y2={L2_Y - BOX_H / 2}
            strokeWidth={l1Miss || l2Active ? 2.5 : 1.5}
            markerEnd={l1Miss || l2Active ? "url(#sc-arrow)" : "url(#sc-arrow-dim)"}
            animate={{ stroke: l1Miss || l2Active ? palette.activeEdgeStroke : palette.edgeStroke, opacity: l1Miss || l2Active ? 1 : 0.4 }}
            transition={{ duration: 0.4 }}
          />

          {/* "miss" label on L1→L2 */}
          {l1Miss && (
            <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
              <rect x={L1_X + 12} y={L1_Y + BOX_H / 2 + 8} width={72} height={22} rx={5} fill="#eff6ff" stroke="#3b82f6" strokeWidth={1} />
              <text x={L1_X + 48} y={L1_Y + BOX_H / 2 + 19} textAnchor="middle" dominantBaseline="middle" fontSize={8} fontWeight={600} fill="#2563eb" fontFamily="monospace">
                ESCALATE
              </text>
            </motion.g>
          )}

          {/* Layer 2: LLM */}
          <motion.rect
            x={L2_X - BOX_W / 2}
            y={L2_Y - BOX_H / 2}
            width={BOX_W}
            height={BOX_H}
            rx={10}
            strokeWidth={2}
            animate={{
              fill: l2Active ? "#8b5cf6" : palette.nodeFill,
              stroke: l2Active ? "#7c3aed" : palette.nodeStroke,
            }}
            filter={l2Active ? "url(#sc-glow-purple)" : "none"}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={L2_X}
            y={L2_Y - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={11}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: l2Active ? "#ffffff" : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            Layer 2: LLM
          </motion.text>
          <motion.text
            x={L2_X}
            y={L2_Y + 12}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={8}
            animate={{ fill: l2Active ? "rgba(255,255,255,0.8)" : palette.labelFill }}
            transition={{ duration: 0.4 }}
          >
            ~10 tokens · intent analysis
          </motion.text>

          {/* L2 → Result line */}
          <motion.line
            x1={L2_X + BOX_W / 2}
            y1={L2_Y}
            x2={RESULT_X - BOX_W / 2}
            y2={RESULT_Y}
            strokeWidth={l2Active ? 2.5 : 1}
            markerEnd={l2Active ? "url(#sc-arrow)" : "url(#sc-arrow-dim)"}
            animate={{ stroke: l2Active ? palette.activeEdgeStroke : palette.edgeStroke, opacity: l2Active ? 1 : 0.3 }}
            transition={{ duration: 0.4 }}
          />

          {/* Result node */}
          <motion.rect
            x={RESULT_X - BOX_W / 2}
            y={RESULT_Y - BOX_H / 2}
            width={BOX_W}
            height={BOX_H}
            rx={8}
            strokeWidth={2}
            animate={{
              fill: resultActive ? palette.endNodeFill : palette.nodeFill,
              stroke: resultActive ? palette.endNodeStroke : palette.nodeStroke,
            }}
            transition={{ duration: 0.4 }}
          />
          <motion.text
            x={RESULT_X}
            y={RESULT_Y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={12}
            fontWeight={700}
            fontFamily="monospace"
            animate={{ fill: resultActive ? palette.activeNodeText : palette.nodeText }}
            transition={{ duration: 0.4 }}
          >
            result
          </motion.text>

          {/* Result annotation */}
          {result && (
            <motion.text
              x={RESULT_X}
              y={RESULT_Y + BOX_H / 2 + 16}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={9}
              fontWeight={600}
              fontFamily="monospace"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              fill={currentStep === 1 ? "#ef4444" : currentStep === 2 ? "#10b981" : "#f59e0b"}
            >
              {result}
            </motion.text>
          )}

          {/* Cost labels */}
          <text x={L1_X} y={L1_Y + BOX_H / 2 + 64} textAnchor="middle" fontSize={8} fill={palette.labelFill}>
            Cost: 0 tokens
          </text>
          <text x={L2_X} y={L2_Y + BOX_H / 2 + 64} textAnchor="middle" fontSize={8} fill={palette.labelFill}>
            Cost: ~10 tokens
          </text>
        </svg>

        {/* Code snippet */}
        <div className="mt-3 rounded-md bg-zinc-100 px-3 py-2 dark:bg-zinc-800">
          <code className="block font-mono text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-300">
            <span className="text-blue-600 dark:text-blue-400">def</span>{" "}
            <span className="text-emerald-600 dark:text-emerald-400">classify</span>(cmd):
            {"\n  "}
            <span className="text-zinc-500">{"# "}</span>
            {currentStep === 1
              ? "quick_scan(cmd) → dangerous (pattern match)"
              : currentStep === 2
                ? "quick_scan(cmd) → safe (whitelist)"
                : currentStep === 3
                  ? "quick_scan(cmd) → None → escalate to LLM"
                  : currentStep === 4
                    ? "llm_classify(cmd) → {level, source: 'llm'}"
                    : currentStep === 5
                      ? "llm_classify failed → fallback moderate (ask)"
                      : "result = quick_scan(cmd) or llm_classify(cmd)"}
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
