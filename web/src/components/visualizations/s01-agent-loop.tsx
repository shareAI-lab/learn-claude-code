"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSvgPalette } from "@/hooks/useDarkMode";
import { useLocale } from "@/lib/i18n";

interface FlowNode {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  type: "rect" | "diamond";
}

interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

interface MessageBlock {
  role: string;
  detail: string;
  colorClass: string;
}

type SupportedLocale = "zh" | "en" | "ja";
type NodeId = "start" | "api_call" | "check" | "execute" | "append" | "end";

const BASE_NODES: Array<Omit<FlowNode, "label">> = [
  { id: "start", x: 160, y: 30, w: 120, h: 40, type: "rect" },
  { id: "api_call", x: 160, y: 110, w: 120, h: 40, type: "rect" },
  { id: "check", x: 160, y: 200, w: 140, h: 50, type: "diamond" },
  { id: "execute", x: 160, y: 300, w: 120, h: 40, type: "rect" },
  { id: "append", x: 160, y: 380, w: 120, h: 40, type: "rect" },
  { id: "end", x: 380, y: 200, w: 120, h: 40, type: "rect" },
];

const EDGES: FlowEdge[] = [
  { from: "start", to: "api_call" },
  { from: "api_call", to: "check" },
  { from: "check", to: "execute", label: "tool_use" },
  { from: "execute", to: "append" },
  { from: "append", to: "api_call" },
  { from: "check", to: "end", label: "end_turn" },
];

const ACTIVE_NODES_PER_STEP: string[][] = [
  [],
  ["start"],
  ["api_call"],
  ["check", "execute"],
  ["execute", "append"],
  ["api_call", "check", "execute", "append"],
  ["check", "end"],
];

const ACTIVE_EDGES_PER_STEP: string[][] = [
  [],
  [],
  ["start->api_call"],
  ["api_call->check", "check->execute"],
  ["execute->append"],
  ["append->api_call", "api_call->check", "check->execute", "execute->append"],
  ["api_call->check", "check->end"],
];

const COPY: Record<
  SupportedLocale,
  {
    title: string;
    loopLabel: string;
    emptyLabel: string;
    lengthLabel: string;
    iterationLabel: string;
    nodeLabels: Record<NodeId, string>;
    messagesPerStep: (MessageBlock | null)[][];
    stepInfo: { title: string; desc: string }[];
  }
> = {
  zh: {
    title: "Agent 主循环",
    loopLabel: 'while (stop_reason === "tool_use")',
    emptyLabel: "[ 空 ]",
    lengthLabel: "长度",
    iterationLabel: "第 2 轮",
    nodeLabels: {
      start: "开始",
      api_call: "调用模型",
      check: "stop_reason?",
      execute: "执行工具",
      append: "追加结果",
      end: "结束 / 完成",
    },
    messagesPerStep: [
      [],
      [{ role: "user", detail: "修复登录 bug", colorClass: "bg-blue-500 dark:bg-blue-600" }],
      [],
      [{ role: "assistant", detail: "tool_use: read_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" }],
      [{ role: "tool_result", detail: "auth.ts 内容...", colorClass: "bg-emerald-500 dark:bg-emerald-600" }],
      [
        { role: "assistant", detail: "tool_use: edit_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" },
        { role: "tool_result", detail: "文件已更新", colorClass: "bg-emerald-500 dark:bg-emerald-600" },
      ],
      [{ role: "assistant", detail: "end_turn: 完成！", colorClass: "bg-purple-500 dark:bg-purple-600" }],
    ],
    stepInfo: [
      {
        title: "主循环本身",
        desc: "每个 agent 的核心都是一个 while 循环：不断调用模型，直到它明确表示这一轮该结束。",
      },
      {
        title: "用户输入",
        desc: "循环从用户消息进入 messages[] 开始。",
      },
      {
        title: "调用模型",
        desc: "把当前消息历史整体发给模型，让它基于已有上下文决定下一步。",
      },
      {
        title: "stop_reason: tool_use",
        desc: "模型想调用工具，所以主循环不能结束，而要继续进入执行分支。",
      },
      {
        title: "执行并回写",
        desc: "执行工具，把结果追加回 messages[]，再喂给下一轮推理。",
      },
      {
        title: "再跑一轮",
        desc: "还是同一条代码路径，只是现在模型已经能看到刚才的真实工具结果。",
      },
      {
        title: "stop_reason: end_turn",
        desc: "模型这轮已经完成，循环退出。这就是最小 agent 的完整闭环。",
      },
    ],
  },
  en: {
    title: "The Agent While-Loop",
    loopLabel: 'while (stop_reason === "tool_use")',
    emptyLabel: "[ empty ]",
    lengthLabel: "length",
    iterationLabel: "iter #2",
    nodeLabels: {
      start: "Start",
      api_call: "API Call",
      check: "stop_reason?",
      execute: "Execute Tool",
      append: "Append Result",
      end: "Break / Done",
    },
    messagesPerStep: [
      [],
      [{ role: "user", detail: "Fix the login bug", colorClass: "bg-blue-500 dark:bg-blue-600" }],
      [],
      [{ role: "assistant", detail: "tool_use: read_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" }],
      [{ role: "tool_result", detail: "auth.ts contents...", colorClass: "bg-emerald-500 dark:bg-emerald-600" }],
      [
        { role: "assistant", detail: "tool_use: edit_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" },
        { role: "tool_result", detail: "file updated", colorClass: "bg-emerald-500 dark:bg-emerald-600" },
      ],
      [{ role: "assistant", detail: "end_turn: Done!", colorClass: "bg-purple-500 dark:bg-purple-600" }],
    ],
    stepInfo: [
      { title: "The While Loop", desc: "Every agent is a while loop that keeps calling the model until it says 'stop'." },
      { title: "User Input", desc: "The loop starts when the user sends a message." },
      { title: "Call the Model", desc: "Send all messages to the LLM. It sees everything and decides what to do." },
      { title: "stop_reason: tool_use", desc: "The model wants to use a tool. The loop continues." },
      { title: "Execute & Append", desc: "Run the tool, append the result to messages[]. Feed it back." },
      { title: "Loop Again", desc: "Same code path, second iteration. The model decides to edit a file." },
      { title: "stop_reason: end_turn", desc: "The model is done. Loop exits. That's the entire agent." },
    ],
  },
  ja: {
    title: "Agent 主ループ",
    loopLabel: 'while (stop_reason === "tool_use")',
    emptyLabel: "[ 空 ]",
    lengthLabel: "長さ",
    iterationLabel: "2 周目",
    nodeLabels: {
      start: "開始",
      api_call: "API 呼び出し",
      check: "stop_reason?",
      execute: "Tool 実行",
      append: "結果を追加",
      end: "終了 / 完了",
    },
    messagesPerStep: [
      [],
      [{ role: "user", detail: "ログイン bug を直す", colorClass: "bg-blue-500 dark:bg-blue-600" }],
      [],
      [{ role: "assistant", detail: "tool_use: read_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" }],
      [{ role: "tool_result", detail: "auth.ts の内容...", colorClass: "bg-emerald-500 dark:bg-emerald-600" }],
      [
        { role: "assistant", detail: "tool_use: edit_file", colorClass: "bg-zinc-600 dark:bg-zinc-500" },
        { role: "tool_result", detail: "ファイルを更新", colorClass: "bg-emerald-500 dark:bg-emerald-600" },
      ],
      [{ role: "assistant", detail: "end_turn: 完了！", colorClass: "bg-purple-500 dark:bg-purple-600" }],
    ],
    stepInfo: [
      {
        title: "主ループそのもの",
        desc: "すべての agent の核は while ループです。モデルが明示的に止まるまで呼び続けます。",
      },
      {
        title: "ユーザー入力",
        desc: "ループはユーザーのメッセージが messages[] に入るところから始まります。",
      },
      {
        title: "モデル呼び出し",
        desc: "現在のメッセージ履歴をまとめてモデルへ渡し、次に何をするか判断させます。",
      },
      {
        title: "stop_reason: tool_use",
        desc: "モデルは tool を使いたいので、ループは終了せず実行分岐へ進みます。",
      },
      {
        title: "実行して回写",
        desc: "tool を実行し、その結果を messages[] に追加して次の推論へ戻します。",
      },
      {
        title: "もう一度回る",
        desc: "コード経路は同じですが、今回は直前の実行結果を見た上でモデルが次を決めます。",
      },
      {
        title: "stop_reason: end_turn",
        desc: "モデルはこのターンを終えました。ループが抜けて、最小 agent 閉ループが完成します。",
      },
    ],
  },
};

function normalizeLocale(locale: string): SupportedLocale {
  if (locale === "zh" || locale === "ja") return locale;
  return "en";
}

function getNodes(locale: SupportedLocale): FlowNode[] {
  const labels = COPY[locale].nodeLabels;
  return BASE_NODES.map((node) => ({
    ...node,
    label: labels[node.id as NodeId],
  }));
}

function getNode(nodes: FlowNode[], id: string): FlowNode {
  return nodes.find((node) => node.id === id)!;
}

function edgePath(nodes: FlowNode[], fromId: string, toId: string): string {
  const from = getNode(nodes, fromId);
  const to = getNode(nodes, toId);

  if (fromId === "append" && toId === "api_call") {
    const startX = from.x - from.w / 2;
    const startY = from.y;
    const endX = to.x - to.w / 2;
    const endY = to.y;
    return `M ${startX} ${startY} L ${startX - 50} ${startY} L ${endX - 50} ${endY} L ${endX} ${endY}`;
  }

  if (fromId === "check" && toId === "end") {
    const startX = from.x + from.w / 2;
    const startY = from.y;
    const endX = to.x - to.w / 2;
    const endY = to.y;
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  }

  const startX = from.x;
  const startY = from.y + from.h / 2;
  const endX = to.x;
  const endY = to.y - to.h / 2;
  return `M ${startX} ${startY} L ${endX} ${endY}`;
}

export default function AgentLoop({ title }: { title?: string }) {
  const locale = normalizeLocale(useLocale());
  const copy = COPY[locale];
  const nodes = getNodes(locale);
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: 7, autoPlayInterval: 2500 });

  const palette = useSvgPalette();
  const activeNodes = ACTIVE_NODES_PER_STEP[currentStep];
  const activeEdges = ACTIVE_EDGES_PER_STEP[currentStep];
  const visibleMessages: MessageBlock[] = [];

  for (let step = 0; step <= currentStep; step++) {
    for (const message of copy.messagesPerStep[step]) {
      if (message) visibleMessages.push(message);
    }
  }

  const stepInfo = copy.stepInfo[currentStep];

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || copy.title}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="w-full lg:w-[60%]">
            <div className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">
              {copy.loopLabel}
            </div>
            <svg
              viewBox="0 0 500 440"
              className="w-full rounded-md border border-zinc-100 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
              style={{ minHeight: 300 }}
            >
              <defs>
                <filter id="glow-blue">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.7" />
                </filter>
                <filter id="glow-purple">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#a855f7" floodOpacity="0.7" />
                </filter>
                <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill={palette.arrowFill} />
                </marker>
                <marker id="arrowhead-active" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill={palette.activeEdgeStroke} />
                </marker>
              </defs>

              {EDGES.map((edge) => {
                const key = `${edge.from}->${edge.to}`;
                const isActive = activeEdges.includes(key);
                const d = edgePath(nodes, edge.from, edge.to);

                return (
                  <g key={key}>
                    <motion.path
                      d={d}
                      fill="none"
                      stroke={isActive ? palette.activeEdgeStroke : palette.edgeStroke}
                      strokeWidth={isActive ? 2.5 : 1.5}
                      markerEnd={isActive ? "url(#arrowhead-active)" : "url(#arrowhead)"}
                      animate={{
                        stroke: isActive ? palette.activeEdgeStroke : palette.edgeStroke,
                        strokeWidth: isActive ? 2.5 : 1.5,
                      }}
                      transition={{ duration: 0.4 }}
                    />
                    {edge.label && (
                      <text
                        x={
                          edge.from === "check" && edge.to === "end"
                            ? (getNode(nodes, "check").x + getNode(nodes, "end").x) / 2
                            : getNode(nodes, edge.from).x + 75
                        }
                        y={
                          edge.from === "check" && edge.to === "end"
                            ? getNode(nodes, "check").y - 10
                            : (getNode(nodes, edge.from).y + getNode(nodes, edge.to).y) / 2
                        }
                        textAnchor="middle"
                        className="fill-zinc-400 text-[10px] dark:fill-zinc-500"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {nodes.map((node) => {
                const isActive = activeNodes.includes(node.id);
                const isEnd = node.id === "end";
                const filterAttr = isActive
                  ? isEnd
                    ? "url(#glow-purple)"
                    : "url(#glow-blue)"
                  : "none";

                if (node.type === "diamond") {
                  const cx = node.x;
                  const cy = node.y;
                  const hw = node.w / 2;
                  const hh = node.h / 2;
                  const points = `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`;

                  return (
                    <g key={node.id}>
                      <motion.polygon
                        points={points}
                        fill={isActive ? palette.activeNodeFill : palette.nodeFill}
                        stroke={isActive ? palette.activeNodeStroke : palette.nodeStroke}
                        strokeWidth={1.5}
                        filter={filterAttr}
                        animate={{
                          fill: isActive ? palette.activeNodeFill : palette.nodeFill,
                          stroke: isActive ? palette.activeNodeStroke : palette.nodeStroke,
                        }}
                        transition={{ duration: 0.4 }}
                      />
                      <motion.text
                        x={cx}
                        y={cy + 4}
                        textAnchor="middle"
                        fontSize={11}
                        fontWeight={600}
                        fontFamily="monospace"
                        animate={{ fill: isActive ? palette.activeNodeText : palette.nodeText }}
                        transition={{ duration: 0.4 }}
                      >
                        {node.label}
                      </motion.text>
                    </g>
                  );
                }

                return (
                  <g key={node.id}>
                    <motion.rect
                      x={node.x - node.w / 2}
                      y={node.y - node.h / 2}
                      width={node.w}
                      height={node.h}
                      rx={8}
                      fill={isActive ? (isEnd ? palette.endNodeFill : palette.activeNodeFill) : palette.nodeFill}
                      stroke={isActive ? (isEnd ? palette.endNodeStroke : palette.activeNodeStroke) : palette.nodeStroke}
                      strokeWidth={1.5}
                      filter={filterAttr}
                      animate={{
                        fill: isActive ? (isEnd ? palette.endNodeFill : palette.activeNodeFill) : palette.nodeFill,
                        stroke: isActive ? (isEnd ? palette.endNodeStroke : palette.activeNodeStroke) : palette.nodeStroke,
                      }}
                      transition={{ duration: 0.4 }}
                    />
                    <motion.text
                      x={node.x}
                      y={node.y + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontWeight={600}
                      fontFamily="monospace"
                      animate={{ fill: isActive ? palette.activeNodeText : palette.nodeText }}
                      transition={{ duration: 0.4 }}
                    >
                      {node.label}
                    </motion.text>
                  </g>
                );
              })}

              {currentStep >= 5 && (
                <motion.text
                  x={60}
                  y={130}
                  textAnchor="middle"
                  fontSize={10}
                  fontFamily="monospace"
                  fill="#3b82f6"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {copy.iterationLabel}
                </motion.text>
              )}
            </svg>
          </div>

          <div className="w-full lg:w-[40%]">
            <div className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">
              messages[]
            </div>
            <div className="min-h-[300px] space-y-2 rounded-md border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
              <AnimatePresence mode="popLayout">
                {visibleMessages.length === 0 && (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="py-8 text-center text-xs text-zinc-400 dark:text-zinc-600"
                  >
                    {copy.emptyLabel}
                  </motion.div>
                )}

                {visibleMessages.map((message, index) => (
                  <motion.div
                    key={`${message.role}-${message.detail}-${index}`}
                    initial={{ opacity: 0, y: 12, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.35, type: "spring", bounce: 0.3 }}
                    className={`rounded-md px-3 py-2 ${message.colorClass}`}
                  >
                    <div className="font-mono text-[11px] font-semibold text-white">
                      {message.role}
                    </div>
                    <div className="mt-0.5 text-[10px] text-white/80">
                      {message.detail}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {visibleMessages.length > 0 && (
                <div className="mt-3 border-t border-zinc-200 pt-2 dark:border-zinc-700">
                  <span className="font-mono text-[10px] text-zinc-400">
                    {copy.lengthLabel}: {visibleMessages.length}
                  </span>
                </div>
              )}
            </div>
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
        stepDescription={stepInfo.desc}
      />
    </section>
  );
}
