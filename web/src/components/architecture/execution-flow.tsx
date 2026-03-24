"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getFlowForVersion } from "@/data/execution-flows";
import type { FlowNode, FlowEdge } from "@/types/agent-data";

const NODE_WIDTH = 140;
const NODE_HEIGHT = 40;
const DIAMOND_SIZE = 50;

const LAYER_COLORS: Record<string, string> = {
  start: "#3B82F6",
  process: "#10B981",
  decision: "#F59E0B",
  subprocess: "#8B5CF6",
  end: "#EF4444",
};

function getNodeCenter(node: FlowNode): { cx: number; cy: number } {
  return { cx: node.x, cy: node.y };
}

function getEdgePath(from: FlowNode, to: FlowNode): string {
  const { cx: x1, cy: y1 } = getNodeCenter(from);
  const { cx: x2, cy: y2 } = getNodeCenter(to);

  const halfH = from.type === "decision" ? DIAMOND_SIZE / 2 : NODE_HEIGHT / 2;
  const halfHTo = to.type === "decision" ? DIAMOND_SIZE / 2 : NODE_HEIGHT / 2;

  if (Math.abs(x1 - x2) < 10) {
    const startY = y1 + halfH;
    const endY = y2 - halfHTo;
    return `M ${x1} ${startY} L ${x2} ${endY}`;
  }

  const startY = y1 + halfH;
  const endY = y2 - halfHTo;
  const midY = (startY + endY) / 2;
  return `M ${x1} ${startY} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${endY}`;
}

function NodeShape({ node }: { node: FlowNode }) {
  const color = LAYER_COLORS[node.type];
  const lines = node.label.split("\n");

  if (node.type === "decision") {
    const half = DIAMOND_SIZE / 2;
    return (
      <g>
        <polygon
          points={`${node.x},${node.y - half} ${node.x + half},${node.y} ${node.x},${node.y + half} ${node.x - half},${node.y}`}
          fill="none"
          stroke={color}
          strokeWidth={2}
        />
        {lines.map((line, i) => (
          <text
            key={i}
            x={node.x}
            y={node.y + (i - (lines.length - 1) / 2) * 12}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={10}
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
          x={node.x - NODE_WIDTH / 2}
          y={node.y - NODE_HEIGHT / 2}
          width={NODE_WIDTH}
          height={NODE_HEIGHT}
          rx={NODE_HEIGHT / 2}
          fill="none"
          stroke={color}
          strokeWidth={2}
        />
        <text
          x={node.x}
          y={node.y}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={12}
          fontWeight={600}
          fontFamily="monospace"
          fill="currentColor"
        >
          {node.label}
        </text>
      </g>
    );
  }

  const isSubprocess = node.type === "subprocess";
  return (
    <g>
      <rect
        x={node.x - NODE_WIDTH / 2}
        y={node.y - NODE_HEIGHT / 2}
        width={NODE_WIDTH}
        height={NODE_HEIGHT}
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
  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;

  return (
    <g>
      <motion.path
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
          x={midX + 8}
          y={midY - 4}
          fontSize={10}
          fill="var(--color-text-secondary)"
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

  if (!flow) return null;

  const maxY = Math.max(...flow.nodes.map((n) => n.y)) + 50;

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
      <svg
        viewBox={`0 0 600 ${maxY}`}
        className="mx-auto w-full max-w-[600px]"
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
          <EdgePath key={`${edge.from}-${edge.to}`} edge={edge} nodes={flow.nodes} index={i} />
        ))}

        {flow.nodes.map((node, i) => (
          <motion.g
            key={node.id}
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
