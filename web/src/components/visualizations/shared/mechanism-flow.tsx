"use client";

import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { useSvgPalette } from "@/hooks/useDarkMode";
import { StepControls } from "./step-controls";
import { cn } from "@/lib/utils";

type NodeKind = "start" | "process" | "decision" | "store" | "external" | "end";

export interface MechanismNode {
  id: string;
  label: string;
  x: number;
  y: number;
  kind?: NodeKind;
  appearsAt?: number;
}

export interface MechanismEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  appearsAt?: number;
}

export interface MechanismStep {
  title: string;
  description: string;
  focus?: string[];
}

interface MechanismFlowProps {
  title?: string;
  fallbackTitle: string;
  nodes: MechanismNode[];
  edges: MechanismEdge[];
  steps: MechanismStep[];
  viewBox?: string;
  footer?: string[];
}

const NODE_WIDTH = 118;
const NODE_HEIGHT = 42;
const DIAMOND_SIZE = 54;

const KIND_COLORS: Record<NodeKind, string> = {
  start: "#3b82f6",
  process: "#10b981",
  decision: "#f59e0b",
  store: "#8b5cf6",
  external: "#ef4444",
  end: "#64748b",
};

function bounds(node: MechanismNode) {
  const halfW = node.kind === "decision" ? DIAMOND_SIZE / 2 : NODE_WIDTH / 2;
  const halfH = node.kind === "decision" ? DIAMOND_SIZE / 2 : NODE_HEIGHT / 2;
  return {
    left: node.x - halfW,
    right: node.x + halfW,
    top: node.y - halfH,
    bottom: node.y + halfH,
  };
}

function edgePath(from: MechanismNode, to: MechanismNode) {
  const a = bounds(from);
  const b = bounds(to);

  if (Math.abs(from.x - to.x) < 12) {
    return `M ${from.x} ${a.bottom} L ${to.x} ${b.top}`;
  }

  if (Math.abs(from.y - to.y) < 12) {
    const startX = to.x > from.x ? a.right : a.left;
    const endX = to.x > from.x ? b.left : b.right;
    const midX = (startX + endX) / 2;
    return `M ${startX} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${endX} ${to.y}`;
  }

  const startY = to.y > from.y ? a.bottom : a.top;
  const endY = to.y > from.y ? b.top : b.bottom;
  const control = Math.max(36, Math.abs(endY - startY) * 0.45);
  const c1 = startY + (endY > startY ? control : -control);
  const c2 = endY - (endY > startY ? control : -control);
  return `M ${from.x} ${startY} C ${from.x} ${c1}, ${to.x} ${c2}, ${to.x} ${endY}`;
}

function labelPosition(from: MechanismNode, to: MechanismNode) {
  return {
    x: (from.x + to.x) / 2,
    y: (from.y + to.y) / 2 - 10,
  };
}

function FlowNode({
  node,
  active,
  visible,
}: {
  node: MechanismNode;
  active: boolean;
  visible: boolean;
}) {
  const kind = node.kind ?? "process";
  const color = KIND_COLORS[kind];
  const lines = node.label.split("\n");

  if (kind === "decision") {
    const half = DIAMOND_SIZE / 2;
    return (
      <motion.g
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: visible ? 1 : 0.16, scale: active ? 1.04 : 1 }}
        transition={{ duration: 0.25 }}
      >
        <polygon
          points={`${node.x},${node.y - half} ${node.x + half},${node.y} ${node.x},${node.y + half} ${node.x - half},${node.y}`}
          fill={active ? `${color}20` : "transparent"}
          stroke={color}
          strokeWidth={active ? 2.4 : 1.5}
        />
        {lines.map((line, i) => (
          <text
            key={line}
            x={node.x}
            y={node.y + (i - (lines.length - 1) / 2) * 12}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={9}
            fontFamily="monospace"
            fontWeight={active ? 700 : 500}
            fill="currentColor"
          >
            {line}
          </text>
        ))}
      </motion.g>
    );
  }

  return (
    <motion.g
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: visible ? 1 : 0.16, y: 0, scale: active ? 1.03 : 1 }}
      transition={{ duration: 0.25 }}
    >
      <rect
        x={node.x - NODE_WIDTH / 2}
        y={node.y - NODE_HEIGHT / 2}
        width={NODE_WIDTH}
        height={NODE_HEIGHT}
        rx={kind === "start" || kind === "end" ? NODE_HEIGHT / 2 : 6}
        fill={active ? `${color}1f` : "transparent"}
        stroke={color}
        strokeWidth={active ? 2.4 : 1.5}
        strokeDasharray={kind === "external" ? "6 3" : undefined}
      />
      {lines.map((line, i) => (
        <text
          key={line}
          x={node.x}
          y={node.y + (i - (lines.length - 1) / 2) * 12}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={10}
          fontFamily="monospace"
          fontWeight={active ? 700 : 500}
          fill="currentColor"
        >
          {line}
        </text>
      ))}
    </motion.g>
  );
}

export function MechanismFlow({
  title,
  fallbackTitle,
  nodes,
  edges,
  steps,
  viewBox = "0 0 720 360",
  footer,
}: MechanismFlowProps) {
  const vis = useSteppedVisualization({ totalSteps: steps.length, autoPlayInterval: 2300 });
  const step = steps[vis.currentStep];
  const palette = useSvgPalette();
  const focused = new Set(step.focus ?? []);

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || fallbackTitle}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <svg viewBox={viewBox} className="w-full" aria-label={title || fallbackTitle}>
          <defs>
            <marker
              id={`mechanism-arrow-${fallbackTitle.replace(/\W/g, "-")}`}
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

          {edges.map((edge) => {
            const from = nodes.find((node) => node.id === edge.from);
            const to = nodes.find((node) => node.id === edge.to);
            if (!from || !to) return null;
            const active = focused.has(edge.id) || focused.has(edge.from) || focused.has(edge.to);
            const visible = active || vis.currentStep >= (edge.appearsAt ?? 0);
            const label = labelPosition(from, to);

            return (
              <motion.g
                key={edge.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: visible ? 1 : 0.12 }}
                transition={{ duration: 0.25 }}
              >
                <path
                  d={edgePath(from, to)}
                  fill="none"
                  stroke={active ? "#3b82f6" : palette.arrowFill}
                  strokeWidth={active ? 2.4 : 1.3}
                  markerEnd={`url(#mechanism-arrow-${fallbackTitle.replace(/\W/g, "-")})`}
                />
                {edge.label && visible && (
                  <text
                    x={label.x}
                    y={label.y}
                    textAnchor="middle"
                    fontSize={9}
                    fontFamily="monospace"
                    fill={active ? "#2563eb" : palette.labelFill}
                    stroke={palette.bgSubtle}
                    strokeWidth={4}
                    paintOrder="stroke"
                  >
                    {edge.label}
                  </text>
                )}
              </motion.g>
            );
          })}

          {nodes.map((node) => {
            const active = focused.has(node.id);
            const visible = active || vis.currentStep >= (node.appearsAt ?? 0);
            return (
              <FlowNode
                key={node.id}
                node={node}
                visible={visible}
                active={active}
              />
            );
          })}
        </svg>

        {footer && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {footer.map((item) => (
              <span
                key={item}
                className={cn(
                  "rounded-md px-2 py-1 font-mono text-xs",
                  "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                )}
              >
                {item}
              </span>
            ))}
          </div>
        )}
      </div>

      <StepControls
        currentStep={vis.currentStep}
        totalSteps={vis.totalSteps}
        onPrev={vis.prev}
        onNext={vis.next}
        onReset={vis.reset}
        isPlaying={vis.isPlaying}
        onToggleAutoPlay={vis.toggleAutoPlay}
        stepTitle={step.title}
        stepDescription={step.description}
      />
    </section>
  );
}
