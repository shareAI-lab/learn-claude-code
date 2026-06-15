"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getFlowForVersion } from "@/data/execution-flows";
import type { FlowNode, FlowEdge } from "@/types/agent-data";

const NODE_WIDTH = 140;
const NODE_HEIGHT = 44;
const DIAMOND_WIDTH = 92;
const DIAMOND_HEIGHT = 64;

const LAYER_COLORS: Record<string, string> = {
  start: "#3B82F6",
  process: "#10B981",
  decision: "#F59E0B",
  subprocess: "#8B5CF6",
  end: "#EF4444",
};

function getNodeLines(node: FlowNode): string[] {
  const maxChars = node.type === "decision" ? 12 : 18;
  return node.label.split("\n").flatMap((line) => {
    if (line.length <= maxChars) return [line];

    const parts = line.split(/(\s+\/\s+|\s+|_)/).filter(Boolean);
    const chunks: string[] = [];
    let current = "";

    for (const part of parts) {
      const next = `${current}${part}`;
      if (current && next.trim().length > maxChars) {
        chunks.push(current.trim());
        current = part.trimStart();
      } else {
        current = next;
      }
    }

    if (current.trim()) chunks.push(current.trim());
    return chunks.length ? chunks : [line];
  });
}

function estimateTextWidth(line: string, fontSize: number): number {
  return line.length * fontSize * 0.62;
}

function getNodeMetrics(node: FlowNode) {
  const lines = getNodeLines(node);
  const longest = Math.max(...lines.map((line) => estimateTextWidth(line, 11)), 0);

  if (node.type === "decision") {
    return {
      lines,
      width: Math.max(DIAMOND_WIDTH, longest + 54),
      height: Math.max(DIAMOND_HEIGHT, lines.length * 15 + 42),
    };
  }

  if (node.type === "start" || node.type === "end") {
    return {
      lines,
      width: Math.max(NODE_WIDTH, longest + 34),
      height: Math.max(NODE_HEIGHT, lines.length * 15 + 24),
    };
  }

  return {
    lines,
    width: Math.max(NODE_WIDTH, longest + 30),
    height: Math.max(NODE_HEIGHT, lines.length * 15 + 24),
  };
}

function getNodeBounds(node: FlowNode) {
  const metrics = getNodeMetrics(node);
  const halfW = metrics.width / 2;
  const halfH = metrics.height / 2;

  return {
    cx: node.x,
    cy: node.y,
    left: node.x - halfW,
    right: node.x + halfW,
    top: node.y - halfH,
    bottom: node.y + halfH,
  };
}

const LOOP_RAIL_X = -48;
const RIGHT_LOOP_RAIL_X = 576;
const FLOW_CENTER_X = 300;
const LOOP_PAD = 28;
const LOOP_BACK_DX_LIMIT = 360;
const LOOP_BACK_DY_LIMIT = 70;

type LoopSide = "left" | "right";

function getLoopSide(start: ReturnType<typeof getNodeBounds>, end: ReturnType<typeof getNodeBounds>): LoopSide {
  return (start.cx + end.cx) / 2 > FLOW_CENTER_X ? "right" : "left";
}

function getLoopRailX(
  start: ReturnType<typeof getNodeBounds>,
  end: ReturnType<typeof getNodeBounds>,
  side = getLoopSide(start, end),
) {
  if (side === "right") {
    return Math.max(RIGHT_LOOP_RAIL_X, start.right + LOOP_PAD, end.right + LOOP_PAD);
  }

  return Math.min(LOOP_RAIL_X, start.left - LOOP_PAD, end.left - LOOP_PAD);
}

function isLoopBack(start: ReturnType<typeof getNodeBounds>, end: ReturnType<typeof getNodeBounds>) {
  const dx = end.cx - start.cx;
  const dy = end.cy - start.cy;
  return dy < -LOOP_BACK_DY_LIMIT && Math.abs(dx) <= LOOP_BACK_DX_LIMIT;
}

function shouldUseStepRoute(start: ReturnType<typeof getNodeBounds>, end: ReturnType<typeof getNodeBounds>) {
  const dx = end.cx - start.cx;
  const dy = end.cy - start.cy;
  return dy > 28 && Math.abs(dx) > 44 && end.top > start.bottom;
}

function getStepBusY(start: ReturnType<typeof getNodeBounds>, end: ReturnType<typeof getNodeBounds>) {
  const room = end.top - start.bottom;
  return Math.min(end.top - 16, start.bottom + Math.max(18, room * 0.35));
}

function getEdgePath(from: FlowNode, to: FlowNode): string {
  const start = getNodeBounds(from);
  const end = getNodeBounds(to);
  const dx = end.cx - start.cx;
  const dy = end.cy - start.cy;

  if (isLoopBack(start, end)) {
    const side = getLoopSide(start, end);
    const railX = getLoopRailX(start, end, side);
    const startX = side === "right" ? start.right : start.left;
    const endX = side === "right" ? end.right : end.left;
    const midY = (start.cy + end.cy) / 2;
    return `M ${startX} ${start.cy} C ${railX} ${start.cy}, ${railX} ${midY}, ${railX} ${midY} C ${railX} ${end.cy}, ${endX} ${end.cy}, ${endX} ${end.cy}`;
  }

  if (Math.abs(dx) < 10) {
    if (dy >= 0) {
      return `M ${start.cx} ${start.bottom} L ${end.cx} ${end.top}`;
    }
    return `M ${start.cx} ${start.top} L ${end.cx} ${end.bottom}`;
  }

  if (Math.abs(dy) < 10) {
    const startX = dx > 0 ? start.right : start.left;
    const endX = dx > 0 ? end.left : end.right;
    const midX = (startX + endX) / 2;
    return `M ${startX} ${start.cy} C ${midX} ${start.cy}, ${midX} ${end.cy}, ${endX} ${end.cy}`;
  }

  if (shouldUseStepRoute(start, end)) {
    const busY = getStepBusY(start, end);
    return `M ${start.cx} ${start.bottom} L ${start.cx} ${busY} L ${end.cx} ${busY} L ${end.cx} ${end.top}`;
  }

  if (Math.abs(dx) > 70) {
    const startX = dx > 0 ? start.right : start.left;
    const endX = dx > 0 ? end.left : end.right;
    const control = Math.max(56, Math.abs(dx) * 0.45);
    return `M ${startX} ${start.cy} C ${startX + (dx > 0 ? control : -control)} ${start.cy}, ${endX - (dx > 0 ? control : -control)} ${end.cy}, ${endX} ${end.cy}`;
  }

  const startY = dy > 0 ? start.bottom : start.top;
  const endY = dy > 0 ? end.top : end.bottom;
  const controlDistance = Math.max(44, Math.abs(endY - startY) * 0.42);
  const controlY1 = startY + (endY > startY ? controlDistance : -controlDistance);
  const controlY2 = endY - (endY > startY ? controlDistance : -controlDistance);

  return `M ${start.cx} ${startY} C ${start.cx} ${controlY1}, ${end.cx} ${controlY2}, ${end.cx} ${endY}`;
}

function getEdgeLabelPosition(from: FlowNode, to: FlowNode): { x: number; y: number } {
  const start = getNodeBounds(from);
  const end = getNodeBounds(to);
  const dx = end.cx - start.cx;
  const dy = end.cy - start.cy;

  if (isLoopBack(start, end)) {
    const side = getLoopSide(start, end);
    return {
      x: getLoopRailX(start, end, side) + (side === "right" ? -24 : 24),
      y: (start.cy + end.cy) / 2 - 6,
    };
  }

  if (Math.abs(dy) < 10) {
    return { x: (start.cx + end.cx) / 2, y: start.cy - 12 };
  }

  if (shouldUseStepRoute(start, end)) {
    return { x: (start.cx + end.cx) / 2, y: getStepBusY(start, end) - 8 };
  }

  return {
    x: (start.cx + end.cx) / 2 + (dx > 0 ? 18 : -18),
    y: (start.bottom + end.top) / 2 - 8,
  };
}

function NodeShape({ node }: { node: FlowNode }) {
  const color = LAYER_COLORS[node.type];
  const { lines, width, height } = getNodeMetrics(node);

  if (node.type === "decision") {
    const halfW = width / 2;
    const halfH = height / 2;
    return (
      <g>
        <polygon
          points={`${node.x},${node.y - halfH} ${node.x + halfW},${node.y} ${node.x},${node.y + halfH} ${node.x - halfW},${node.y}`}
          fill="none"
          stroke={color}
          strokeWidth={2}
        />
        {lines.map((line, i) => (
          <text
            key={i}
            x={node.x}
            y={node.y + (i - (lines.length - 1) / 2) * 13}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={lines.length > 2 ? 9 : 10}
            fontFamily="monospace"
            fill="currentColor"
          >
            {line}
          </text>
        ))}
      </g>
    );
  }

  if (node.type === "start" || node.type === "end") {
    return (
      <g>
        <rect
          x={node.x - width / 2}
          y={node.y - height / 2}
          width={width}
          height={height}
          rx={height / 2}
          fill="none"
          stroke={color}
          strokeWidth={2}
        />
        {lines.map((line, i) => (
          <text
            key={i}
            x={node.x}
            y={node.y + (i - (lines.length - 1) / 2) * 14}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={12}
            fontWeight={600}
            fontFamily="monospace"
            fill="currentColor"
          >
            {line}
          </text>
        ))}
      </g>
    );
  }

  const isSubprocess = node.type === "subprocess";
  return (
    <g>
      <rect
        x={node.x - width / 2}
        y={node.y - height / 2}
        width={width}
        height={height}
        rx={4}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray={isSubprocess ? "6 3" : undefined}
      />
      {lines.map((line, i) => (
        <text
          key={i}
          x={node.x}
          y={node.y + (i - (lines.length - 1) / 2) * 13}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={11}
          fontFamily="monospace"
          fill="currentColor"
        >
          {line}
        </text>
      ))}
    </g>
  );
}

function EdgePath({
  edge,
  nodes,
  index,
}: {
  edge: FlowEdge;
  nodes: FlowNode[];
  index: number;
}) {
  const from = nodes.find((n) => n.id === edge.from);
  const to = nodes.find((n) => n.id === edge.to);
  if (!from || !to) return null;

  const d = getEdgePath(from, to);
  const label = getEdgeLabelPosition(from, to);

  return (
    <g>
      <motion.path
        data-edge-from={edge.from}
        data-edge-to={edge.to}
        data-edge-label={edge.label ?? ""}
        d={d}
        fill="none"
        stroke="var(--color-text-secondary)"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.5, delay: index * 0.12 }}
      />
      {edge.label && (
        <motion.text
          x={label.x}
          y={label.y}
          textAnchor="middle"
          fontSize={10}
          fill="var(--color-text-secondary)"
          stroke="var(--color-bg)"
          strokeWidth={5}
          strokeLinejoin="round"
          paintOrder="stroke"
          fontFamily="monospace"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: index * 0.12 + 0.3 }}
        >
          {edge.label}
        </motion.text>
      )}
    </g>
  );
}

interface ExecutionFlowProps {
  version: string;
}

export function ExecutionFlow({ version }: ExecutionFlowProps) {
  const [flow, setFlow] = useState<ReturnType<typeof getFlowForVersion>>(null);

  useEffect(() => {
    setFlow(getFlowForVersion(version));
  }, [version]);

  if (!flow) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] p-6 text-sm text-[var(--color-text-secondary)]">
        Execution flow is not available for this lesson yet.
      </div>
    );
  }

  const bounds = flow.nodes.map(getNodeBounds);
  const minX = Math.min(-40, ...bounds.map((b) => b.left)) - 24;
  const maxX = Math.max(700, ...bounds.map((b) => b.right)) + 24;
  const maxY = Math.max(...bounds.map((b) => b.bottom)) + 50;

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
      <svg
        viewBox={`${minX} 0 ${maxX - minX} ${maxY}`}
        className="mx-auto w-full max-w-[720px]"
        style={{ minHeight: 300 }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth={8}
            markerHeight={6}
            refX={8}
            refY={3}
            orient="auto"
          >
            <polygon
              points="0 0, 8 3, 0 6"
              fill="var(--color-text-secondary)"
            />
          </marker>
        </defs>

        {flow.edges.map((edge, i) => (
          <EdgePath key={`${edge.from}-${edge.to}-${i}`} edge={edge} nodes={flow.nodes} index={i} />
        ))}

        {flow.nodes.map((node, i) => (
          <motion.g
            key={node.id}
            data-node-id={node.id}
            data-node-label={node.label}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, duration: 0.3 }}
          >
            <NodeShape node={node} />
          </motion.g>
        ))}
      </svg>
    </div>
  );
}
