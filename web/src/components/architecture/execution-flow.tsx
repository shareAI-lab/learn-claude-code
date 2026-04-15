"use client";

import { motion } from "framer-motion";
import { getFlowForVersion } from "@/data/execution-flows";
import { getChapterGuide } from "@/lib/chapter-guides";
import { useLocale } from "@/lib/i18n";
import { pickDiagramText, translateFlowText } from "@/lib/diagram-localization";
import type { FlowNode, FlowEdge } from "@/types/agent-data";

const NODE_WIDTH = 140;
const NODE_HEIGHT = 40;
const DIAMOND_SIZE = 50;
type AnchorSide = "top" | "right" | "bottom" | "left";

interface AnchorPoint {
  x: number;
  y: number;
  side: AnchorSide;
}

interface EdgePathResult {
  d: string;
  midX: number;
  midY: number;
}

interface FlowBounds {
  minX: number;
  maxX: number;
}

const NODE_COLORS: Record<string, string> = {
  start: "#3B82F6",
  process: "#10B981",
  decision: "#F59E0B",
  subprocess: "#8B5CF6",
  end: "#EF4444",
};

const NODE_GUIDE = {
  start: {
    title: { zh: "入口", en: "Entry", ja: "入口" },
    note: {
      zh: "这轮从哪里开始进入系统。",
      en: "Where the current turn enters the system.",
      ja: "このターンがどこから入るかを示します。",
    },
  },
  process: {
    title: { zh: "主处理", en: "Process", ja: "主処理" },
    note: {
      zh: "系统内部稳定推进的一步。",
      en: "A stable internal processing step.",
      ja: "システム内部で安定して進む一段です。",
    },
  },
  decision: {
    title: { zh: "分叉判断", en: "Decision", ja: "分岐判断" },
    note: {
      zh: "系统在这里决定往哪条分支走。",
      en: "Where the system chooses a branch.",
      ja: "ここでどの分岐へ進むかを決めます。",
    },
  },
  subprocess: {
    title: { zh: "子流程 / 外部通道", en: "Subprocess / Lane", ja: "子過程 / 外部レーン" },
    note: {
      zh: "常见于外部执行、旁路流程（sidecar）或隔离通道。",
      en: "Often used for external execution, sidecars, or isolated lanes.",
      ja: "外部実行、サイドカー、隔離レーンなどでよく現れます。",
    },
  },
  end: {
    title: { zh: "回流 / 结束", en: "Write-back / End", ja: "回流 / 終了" },
    note: {
      zh: "这轮在这里结束或回到主循环。",
      en: "Where the turn ends or writes back into the loop.",
      ja: "このターンが終わるか、主ループへ戻る場所です。",
    },
  },
} as const;

const UI_TEXT = {
  readLabel: { zh: "读图方式", en: "How to Read", ja: "読み方" },
  readTitle: {
    zh: "先看主线回流，再看左右分支",
    en: "Read the mainline first, then inspect the side branches",
    ja: "まず主線の回流を見て、その後で左右の分岐を見る",
  },
  readNote: {
    zh: "从上往下看时间顺序，中间通常是主线，左右是分支、隔离通道或恢复路径。真正重要的不是节点有多少，而是这一章新增的分叉与回流在哪里。",
    en: "Read top to bottom for time order. The center usually carries the mainline, while the sides hold branches, isolated lanes, or recovery paths. The key question is not how many nodes exist, but where this chapter introduces a new split and write-back.",
    ja: "上から下へ時間順に読みます。中央は主線、左右は分岐・隔離レーン・回復経路です。大事なのはノード数ではなく、この章で新しく増えた分岐と回流がどこかです。",
  },
  focusLabel: { zh: "本章先盯住", en: "Focus First", ja: "まず注目" },
  confusionLabel: { zh: "最容易混", en: "Easy to Confuse", ja: "混同しやすい点" },
  goalLabel: { zh: "学完要会", en: "Build Goal", ja: "学習ゴール" },
  legendLabel: { zh: "节点图例", en: "Node Legend", ja: "ノード凡例" },
  laneTitle: { zh: "版面分区", en: "Visual Lanes", ja: "レーン区分" },
  mainline: { zh: "主线", en: "Mainline", ja: "主線" },
  mainlineNote: {
    zh: "系统当前回合反复回到的那条路径。",
    en: "The path the system keeps returning to during the turn.",
    ja: "システムがこのターン中に繰り返し戻る経路です。",
  },
  sideLane: { zh: "分支 / 旁路通道", en: "Branch / Side Lane", ja: "分岐 / サイドレーン" },
  sideLaneNote: {
    zh: "权限分支、自治扫描、后台槽位、worktree 执行通道常在这里展开。",
    en: "Permission branches, autonomy scans, background slots, and worktree lanes often expand here.",
    ja: "権限分岐、自治スキャン、バックグラウンドスロット、worktree レーンはここで展開されます。",
  },
  bottomNote: {
    zh: "虚线边框通常表示子流程、旁路流程（sidecar）或外部通道；箭头标签说明当前分叉为什么发生。",
    en: "Dashed borders usually indicate a subprocess or external lane; arrow labels explain why a branch was taken.",
    ja: "破線の枠は子過程や外部レーンを示すことが多く、矢印ラベルはなぜ分岐したかを示します。",
  },
} as const;

function getNodeCenter(node: FlowNode): { cx: number; cy: number } {
  return { cx: node.x, cy: node.y };
}

function getNodeHalfWidth(node: FlowNode): number {
  return node.type === "decision" ? DIAMOND_SIZE / 2 : NODE_WIDTH / 2;
}

function getNodeHalfHeight(node: FlowNode): number {
  return node.type === "decision" ? DIAMOND_SIZE / 2 : NODE_HEIGHT / 2;
}

function getAnchor(node: FlowNode, side: AnchorSide): AnchorPoint {
  const { cx, cy } = getNodeCenter(node);
  const halfW = getNodeHalfWidth(node);
  const halfH = getNodeHalfHeight(node);

  if (side === "top") return { x: cx, y: cy - halfH, side };
  if (side === "right") return { x: cx + halfW, y: cy, side };
  if (side === "bottom") return { x: cx, y: cy + halfH, side };
  return { x: cx - halfW, y: cy, side };
}

function getFlowBounds(nodes: FlowNode[]): FlowBounds {
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;

  for (const node of nodes) {
    const halfW = getNodeHalfWidth(node);
    minX = Math.min(minX, node.x - halfW);
    maxX = Math.max(maxX, node.x + halfW);
  }

  return { minX, maxX };
}

function pickSourceSide(from: FlowNode, to: FlowNode): AnchorSide {
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  if (from.type === "decision") {
    if (dx > 24) return "right";
    if (dx < -24) return "left";
    return dy >= 0 ? "bottom" : "top";
  }

  if (Math.abs(dx) > Math.abs(dy) * 1.2) {
    return dx > 0 ? "right" : "left";
  }

  return dy >= 0 ? "bottom" : "top";
}

function pickTargetSide(from: FlowNode, to: FlowNode): AnchorSide {
  const dx = from.x - to.x;
  const dy = from.y - to.y;

  if (to.type === "decision") {
    if (dx > 24) return "right";
    if (dx < -24) return "left";
    return dy < 0 ? "top" : "bottom";
  }

  if (Math.abs(dx) > Math.abs(dy) * 1.2) {
    return dx > 0 ? "right" : "left";
  }

  return dy < 0 ? "top" : "bottom";
}

function getDefaultEdgePath(from: FlowNode, to: FlowNode): EdgePathResult {
  // 回流边（往上）统一走外侧轨道，避免穿越主干区域造成交叉。
  if (to.y < from.y - 20) {
    const railOnLeft = from.x <= to.x;
    const sourceSide: AnchorSide = railOnLeft ? "left" : "right";
    const targetSide: AnchorSide = railOnLeft ? "left" : "right";
    const start = getAnchor(from, sourceSide);
    const end = getAnchor(to, targetSide);
    const railX = railOnLeft
      ? Math.min(start.x, end.x) - 42
      : Math.max(start.x, end.x) + 42;

    return {
      d: `M ${start.x} ${start.y} L ${railX} ${start.y} L ${railX} ${end.y} L ${end.x} ${end.y}`,
      midX: railX,
      midY: (start.y + end.y) / 2,
    };
  }

  const start = getAnchor(from, pickSourceSide(from, to));
  const end = getAnchor(to, pickTargetSide(from, to));

  if (Math.abs(start.x - end.x) < 1 || Math.abs(start.y - end.y) < 1) {
    return {
      d: `M ${start.x} ${start.y} L ${end.x} ${end.y}`,
      midX: (start.x + end.x) / 2,
      midY: (start.y + end.y) / 2,
    };
  }

  if (start.side === "left" || start.side === "right") {
    if (to.y > from.y + 20) {
      const midY = (start.y + end.y) / 2;
      return {
        d: `M ${start.x} ${start.y} L ${start.x} ${midY} L ${end.x} ${midY} L ${end.x} ${end.y}`,
        midX: (start.x + end.x) / 2,
        midY,
      };
    }

    if (end.side === "left" || end.side === "right") {
      const midX = (start.x + end.x) / 2;
      return {
        d: `M ${start.x} ${start.y} L ${midX} ${start.y} L ${midX} ${end.y} L ${end.x} ${end.y}`,
        midX,
        midY: (start.y + end.y) / 2,
      };
    }

    return {
      d: `M ${start.x} ${start.y} L ${end.x} ${start.y} L ${end.x} ${end.y}`,
      midX: (start.x + end.x) / 2,
      midY: (start.y + end.y) / 2,
    };
  }

  if (end.side === "top" || end.side === "bottom") {
    const midY = (start.y + end.y) / 2;
    return {
      d: `M ${start.x} ${start.y} L ${start.x} ${midY} L ${end.x} ${midY} L ${end.x} ${end.y}`,
      midX: (start.x + end.x) / 2,
      midY,
    };
  }

  return {
    d: `M ${start.x} ${start.y} L ${start.x} ${end.y} L ${end.x} ${end.y}`,
    midX: (start.x + end.x) / 2,
    midY: (start.y + end.y) / 2,
  };
}

function getZhEdgePath(
  from: FlowNode,
  to: FlowNode,
  bounds: FlowBounds,
  edgeIndex: number
): EdgePathResult {
  // 中文讲解模式下，回流统一走图外轨道，尽量避免压在主干上。
  if (to.y < from.y - 20) {
    const railOnLeft = from.x <= to.x;
    const sourceSide: AnchorSide = railOnLeft ? "left" : "right";
    const targetSide: AnchorSide = railOnLeft ? "left" : "right";
    const start = getAnchor(from, sourceSide);
    const end = getAnchor(to, targetSide);
    const railBaseX = railOnLeft ? bounds.minX - 34 : bounds.maxX + 34;
    const laneOffset = (edgeIndex % 3) * 10;
    const railXRaw = railOnLeft ? railBaseX - laneOffset : railBaseX + laneOffset;
    // 轨道保持在可视区域内，避免被 viewBox 裁切导致“流程不完整”。
    const railX = Math.max(16, Math.min(584, railXRaw));

    return {
      d: `M ${start.x} ${start.y} L ${railX} ${start.y} L ${railX} ${end.y} L ${end.x} ${end.y}`,
      midX: railX,
      midY: (start.y + end.y) / 2,
    };
  }

  // 从判断节点向左右分支时，先竖向下落再横向展开，降低与主竖线交叉概率。
  if (from.type === "decision" && to.y > from.y + 8 && Math.abs(to.x - from.x) > 24) {
    const branchRight = to.x > from.x;
    const start = getAnchor(from, branchRight ? "right" : "left");
    const end = getAnchor(to, "top");
    const laneX = start.x + (branchRight ? 16 : -16);
    const entryY = Math.min(start.y + 28, end.y - 14);

    return {
      d: `M ${start.x} ${start.y} L ${laneX} ${start.y} L ${laneX} ${entryY} L ${end.x} ${entryY} L ${end.x} ${end.y}`,
      midX: laneX,
      midY: entryY,
    };
  }

  return getDefaultEdgePath(from, to);
}

function getEdgePath(
  from: FlowNode,
  to: FlowNode,
  locale: string,
  bounds: FlowBounds,
  edgeIndex: number
): EdgePathResult {
  if (locale === "zh") {
    return getZhEdgePath(from, to, bounds, edgeIndex);
  }
  return getDefaultEdgePath(from, to);
}

function getEdgeColor(edge: FlowEdge, from: FlowNode, to: FlowNode, locale: string): string {
  if (locale !== "zh") return "var(--color-text-secondary)";

  if (to.y < from.y - 20) return "#38bdf8";

  const label = (edge.label ?? "").toLowerCase();
  if (label.includes("no") || label.includes("deny") || label.includes("reject") || label.includes("remove")) {
    return "#f97316";
  }
  if (label.includes("plugin") || label.includes("mcp") || label.includes("external")) {
    return "#a78bfa";
  }
  if (
    label.includes("yes") ||
    label.includes("allow") ||
    label.includes("task") ||
    label.includes("runtime") ||
    label.includes("spawn") ||
    label.includes("local")
  ) {
    return "#34d399";
  }

  return "#94a3b8";
}

function NodeShape({ node }: { node: FlowNode }) {
  const color = NODE_COLORS[node.type];
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
  locale,
  bounds,
}: {
  edge: FlowEdge;
  nodes: FlowNode[];
  index: number;
  locale: string;
  bounds: FlowBounds;
}) {
  const from = nodes.find((n) => n.id === edge.from);
  const to = nodes.find((n) => n.id === edge.to);
  if (!from || !to) return null;

  const { d, midX, midY } = getEdgePath(from, to, locale, bounds, index);
  const strokeColor = getEdgeColor(edge, from, to, locale);

  return (
    <g>
      <motion.path
        d={d}
        fill="none"
        stroke={strokeColor}
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
          fill={strokeColor}
          fontFamily="monospace"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: index * 0.12 + 0.3 }}
        >
          {translateFlowText(locale, edge.label)}
        </motion.text>
      )}
    </g>
  );
}

interface ExecutionFlowProps {
  version: string;
}

export function ExecutionFlow({ version }: ExecutionFlowProps) {
  const locale = useLocale();
  const flow = getFlowForVersion(version);
  const guide = getChapterGuide(version, locale) ?? getChapterGuide(version, "en");

  if (!flow) return null;

  const maxY = Math.max(...flow.nodes.map((n) => n.y)) + 50;
  const bounds = getFlowBounds(flow.nodes);

  return (
    <div className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-white/95 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/90">
      <div className="grid gap-4 border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6 2xl:grid-cols-[1.35fr_0.95fr]">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {pickDiagramText(locale, UI_TEXT.readLabel)}
            </p>
            <h3 className="mt-3 text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {pickDiagramText(locale, UI_TEXT.readTitle)}
            </h3>
            <p className="mt-2 break-words text-sm leading-6 [word-break:keep-all] text-zinc-600 dark:text-zinc-300">
              {pickDiagramText(locale, UI_TEXT.readNote)}
            </p>
          </div>

          {guide && (
            <div className="grid gap-3 2xl:grid-cols-3">
              <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 p-4 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-emerald-700/80 dark:text-emerald-300/80">
                  {pickDiagramText(locale, UI_TEXT.focusLabel)}
                </p>
                <p className="mt-2 break-words text-sm leading-6 [word-break:keep-all] text-zinc-700 dark:text-zinc-200">
                  {guide.focus}
                </p>
              </div>
              <div className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-700/80 dark:text-amber-300/80">
                  {pickDiagramText(locale, UI_TEXT.confusionLabel)}
                </p>
                <p className="mt-2 break-words text-sm leading-6 [word-break:keep-all] text-zinc-700 dark:text-zinc-200">
                  {guide.confusion}
                </p>
              </div>
              <div className="rounded-2xl border border-sky-200/70 bg-sky-50/80 p-4 dark:border-sky-900/60 dark:bg-sky-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-sky-700/80 dark:text-sky-300/80">
                  {pickDiagramText(locale, UI_TEXT.goalLabel)}
                </p>
                <p className="mt-2 break-words text-sm leading-6 [word-break:keep-all] text-zinc-700 dark:text-zinc-200">
                  {guide.goal}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
            {pickDiagramText(locale, UI_TEXT.legendLabel)}
          </p>
          <div className="space-y-2">
            {(
              Object.keys(NODE_GUIDE) as Array<keyof typeof NODE_GUIDE>
            ).map((nodeType) => (
              <div
                key={nodeType}
                className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-3 dark:border-zinc-800/80 dark:bg-zinc-900/70"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: NODE_COLORS[nodeType] }}
                  />
                  <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {pickDiagramText(locale, NODE_GUIDE[nodeType].title)}
                  </span>
                </div>
                <p className="mt-1 break-words text-xs leading-5 [word-break:keep-all] text-zinc-500 dark:text-zinc-400">
                  {pickDiagramText(locale, NODE_GUIDE[nodeType].note)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="px-4 py-5 sm:px-6">
        <div>
          <div className="mb-4 grid grid-cols-1 gap-3 2xl:grid-cols-3">
            <div className="rounded-2xl border border-zinc-200/70 bg-zinc-50/70 px-3 py-2.5 dark:border-zinc-800/70 dark:bg-zinc-900/60">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLane)}
              </p>
              <p className="mt-1 break-words text-xs leading-5 [word-break:keep-all] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLaneNote)}
              </p>
            </div>
            <div className="rounded-2xl border border-blue-200/70 bg-blue-50/70 px-3 py-2.5 dark:border-blue-900/60 dark:bg-blue-950/20">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 dark:text-blue-300">
                {pickDiagramText(locale, UI_TEXT.mainline)}
              </p>
              <p className="mt-1 break-words text-xs leading-5 [word-break:keep-all] text-zinc-600 dark:text-zinc-300">
                {pickDiagramText(locale, UI_TEXT.mainlineNote)}
              </p>
            </div>
            <div className="rounded-2xl border border-zinc-200/70 bg-zinc-50/70 px-3 py-2.5 dark:border-zinc-800/70 dark:bg-zinc-900/60">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLane)}
              </p>
              <p className="mt-1 break-words text-xs leading-5 [word-break:keep-all] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLaneNote)}
              </p>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[24px] border border-zinc-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] dark:border-zinc-800/80 dark:bg-[linear-gradient(180deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]">
            <div className="pointer-events-none absolute inset-0 grid grid-cols-3 gap-3 p-3">
              <div className="rounded-[20px] bg-zinc-100/60 dark:bg-zinc-900/40" />
              <div className="rounded-[20px] bg-blue-50/70 dark:bg-blue-950/20" />
              <div className="rounded-[20px] bg-zinc-100/60 dark:bg-zinc-900/40" />
            </div>

            <svg
              viewBox={`0 0 600 ${maxY}`}
              className="relative mx-auto w-full max-w-[600px]"
              style={{ minHeight: 320 }}
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
                <EdgePath
                  key={`${edge.from}-${edge.to}`}
                  edge={edge}
                  nodes={flow.nodes}
                  index={i}
                  locale={locale}
                  bounds={bounds}
                />
              ))}

              {flow.nodes.map((node, i) => (
                <motion.g
                  key={node.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                >
                  <NodeShape
                    node={{
                      ...node,
                      label: translateFlowText(locale, node.label),
                    }}
                  />
                </motion.g>
              ))}
            </svg>
          </div>

          <p className="mt-4 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
            {pickDiagramText(locale, UI_TEXT.bottomNote)}
          </p>
        </div>
      </div>
    </div>
  );
}
