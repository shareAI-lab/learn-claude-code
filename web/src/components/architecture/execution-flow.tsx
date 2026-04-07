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
    title: { zh: "子流程 / 外部车道", en: "Subprocess / Lane", ja: "子過程 / 外部レーン" },
    note: {
      zh: "常见于外部执行、侧车流程或隔离车道。",
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
    zh: "从上往下看时间顺序，中间通常是主线，左右是分支、隔离车道或恢复路径。真正重要的不是节点有多少，而是这一章新增的分叉与回流在哪里。",
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
  sideLane: { zh: "分支 / 侧车", en: "Branch / Side Lane", ja: "分岐 / サイドレーン" },
  sideLaneNote: {
    zh: "权限分支、自治扫描、后台槽位、worktree 车道常在这里展开。",
    en: "Permission branches, autonomy scans, background slots, and worktree lanes often expand here.",
    ja: "権限分岐、自治スキャン、バックグラウンドスロット、worktree レーンはここで展開されます。",
  },
  bottomNote: {
    zh: "虚线边框通常表示子流程或外部车道；箭头标签说明当前分叉为什么发生。",
    en: "Dashed borders usually indicate a subprocess or external lane; arrow labels explain why a branch was taken.",
    ja: "破線の枠は子過程や外部レーンを示すことが多く、矢印ラベルはなぜ分岐したかを示します。",
  },
} as const;

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
}: {
  edge: FlowEdge;
  nodes: FlowNode[];
  index: number;
  locale: string;
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

  return (
    <div className="overflow-hidden rounded-[28px] border border-zinc-200/80 bg-white/95 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/90">
      <div className="grid gap-4 border-b border-zinc-200/80 px-5 py-5 dark:border-zinc-800/80 sm:px-6 lg:grid-cols-[1.35fr_0.95fr]">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {pickDiagramText(locale, UI_TEXT.readLabel)}
            </p>
            <h3 className="mt-3 text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {pickDiagramText(locale, UI_TEXT.readTitle)}
            </h3>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {pickDiagramText(locale, UI_TEXT.readNote)}
            </p>
          </div>

          {guide && (
            <div className="grid gap-3 xl:grid-cols-3">
              <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 p-4 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-emerald-700/80 dark:text-emerald-300/80">
                  {pickDiagramText(locale, UI_TEXT.focusLabel)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                  {guide.focus}
                </p>
              </div>
              <div className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-700/80 dark:text-amber-300/80">
                  {pickDiagramText(locale, UI_TEXT.confusionLabel)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                  {guide.confusion}
                </p>
              </div>
              <div className="rounded-2xl border border-sky-200/70 bg-sky-50/80 p-4 dark:border-sky-900/60 dark:bg-sky-950/20">
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-sky-700/80 dark:text-sky-300/80">
                  {pickDiagramText(locale, UI_TEXT.goalLabel)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
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
                <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                  {pickDiagramText(locale, NODE_GUIDE[nodeType].note)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto px-4 py-5 sm:px-6">
        <div className="min-w-[640px]">
          <div className="mb-4 grid grid-cols-3 gap-3">
            <div className="rounded-2xl border border-zinc-200/70 bg-zinc-50/70 px-3 py-2.5 dark:border-zinc-800/70 dark:bg-zinc-900/60">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLane)}
              </p>
              <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLaneNote)}
              </p>
            </div>
            <div className="rounded-2xl border border-blue-200/70 bg-blue-50/70 px-3 py-2.5 dark:border-blue-900/60 dark:bg-blue-950/20">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 dark:text-blue-300">
                {pickDiagramText(locale, UI_TEXT.mainline)}
              </p>
              <p className="mt-1 text-xs leading-5 text-zinc-600 dark:text-zinc-300">
                {pickDiagramText(locale, UI_TEXT.mainlineNote)}
              </p>
            </div>
            <div className="rounded-2xl border border-zinc-200/70 bg-zinc-50/70 px-3 py-2.5 dark:border-zinc-800/70 dark:bg-zinc-900/60">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">
                {pickDiagramText(locale, UI_TEXT.sideLane)}
              </p>
              <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
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
