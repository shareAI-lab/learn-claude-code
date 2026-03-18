"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  ArrowDown,
  Terminal,
  Send,
  MessageSquare,
  Zap,
  Brain,
  BookOpen,
  Shrink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTraceViewer } from "@/hooks/useTraceViewer";
import { JsonBlock } from "./json-block";
import type { TraceCycle, TraceContentBlock, TraceToolExecution } from "@/types/agent-data";

interface AgentIdentity {
  type: "lead" | "subagent" | "teammate";
  name?: string;
  role?: string;
}

function detectAgent(cycle: TraceCycle): AgentIdentity {
  const sys = typeof cycle.request.system === "string" ? cycle.request.system : "";
  const teammateMatch = sys.match(/You are '(\w+)', role: (\w+)/);
  if (teammateMatch) {
    return { type: "teammate", name: teammateMatch[1], role: teammateMatch[2] };
  }
  if (sys.includes("subagent")) {
    return { type: "subagent" };
  }
  return { type: "lead" };
}

function isSubagentCycle(cycle: TraceCycle): boolean {
  const agent = detectAgent(cycle);
  return agent.type === "subagent" || agent.type === "teammate";
}

function StopReasonBadge({ reason }: { reason: string }) {
  const isEnd = reason === "end_turn";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold",
        isEnd
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
          : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
      )}
    >
      {reason}
    </span>
  );
}

function SectionLabel({
  icon: Icon,
  label,
  colorClass,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  colorClass: string;
}) {
  return (
    <div className={cn("flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide", colorClass)}>
      <Icon size={14} />
      {label}
    </div>
  );
}

function ParamTable({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params);
  if (entries.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-700">
      <table className="w-full text-[11px]">
        <tbody>
          {entries.map(([key, value]) => {
            const display =
              typeof value === "string"
                ? value.length > 120
                  ? value.slice(0, 120) + "..."
                  : value
                : JSON.stringify(value, null, 2);
            return (
              <tr key={key} className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-800">
                <td className="whitespace-nowrap bg-zinc-50 px-3 py-1.5 font-mono font-semibold text-zinc-500 dark:bg-zinc-800/50 dark:text-zinc-400">
                  {key}
                </td>
                <td className="px-3 py-1.5 font-mono text-zinc-700 dark:text-zinc-300">
                  <pre className="whitespace-pre-wrap">{display}</pre>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ContentBlockCard({ block, index }: { block: TraceContentBlock; index: number }) {
  if (block.type === "unknown") {
    const thinkingMatch = block.raw?.match(/thinking='([^']*(?:''[^']*)*)'/s);
    const thinkingText = thinkingMatch ? thinkingMatch[1].replace(/''/g, "'") : block.raw;

    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-200 font-mono text-[9px] font-bold text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
            {index + 1}
          </span>
          <Brain size={14} className="text-zinc-500 dark:text-zinc-400" />
          <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">Thinking</span>
        </div>
        <p className="text-xs leading-relaxed text-zinc-500 italic dark:text-zinc-400">
          {thinkingText}
        </p>
      </div>
    );
  }

  if (block.type === "text") {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-800 dark:bg-emerald-950/30">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-200 font-mono text-[9px] font-bold text-emerald-700 dark:bg-emerald-800 dark:text-emerald-200">
            {index + 1}
          </span>
          <MessageSquare size={14} className="text-emerald-600 dark:text-emerald-400" />
          <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Text</span>
        </div>
        <p className="text-sm leading-relaxed text-emerald-900 dark:text-emerald-200">
          {block.text}
        </p>
      </div>
    );
  }

  if (block.type === "tool_use") {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-200 font-mono text-[9px] font-bold text-amber-700 dark:bg-amber-800 dark:text-amber-200">
            {index + 1}
          </span>
          <Terminal size={14} className="text-amber-600 dark:text-amber-400" />
          <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Tool Call</span>
          <span className="rounded-md bg-amber-200 px-1.5 py-0.5 font-mono text-[10px] font-bold text-amber-800 dark:bg-amber-800 dark:text-amber-200">
            {block.name}
          </span>
          <span className="ml-auto font-mono text-[9px] text-amber-400">{block.id}</span>
        </div>
        {block.input && <ParamTable params={block.input as Record<string, unknown>} />}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-200 font-mono text-[9px] font-bold text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
          {index + 1}
        </span>
        <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">{block.type}</span>
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] text-zinc-600 dark:text-zinc-400">
        {block.raw || JSON.stringify(block, null, 2)}
      </pre>
    </div>
  );
}

function ToolExecutionCard({ exec, index }: { exec: TraceToolExecution; index: number }) {
  const [outputOpen, setOutputOpen] = useState(false);
  const outputPreview = exec.output
    ? exec.output.length > 80 ? exec.output.slice(0, 80) + "..." : exec.output
    : "(empty)";

  return (
    <div className="rounded-lg border border-amber-200 bg-white dark:border-amber-800 dark:bg-zinc-900">
      <div className="flex items-center gap-2 border-b border-amber-100 bg-amber-50 px-3 py-2 dark:border-amber-900 dark:bg-amber-950/40">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-200 font-mono text-[9px] font-bold text-amber-700 dark:bg-amber-800 dark:text-amber-200">
          {index + 1}
        </span>
        <Zap size={14} className="text-amber-600 dark:text-amber-400" />
        <span className="font-mono text-xs font-bold text-amber-700 dark:text-amber-300">
          {exec.name}
        </span>
      </div>

      <div className="space-y-3 p-3">
        <div>
          <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Parameters
          </span>
          <ParamTable params={exec.input} />
        </div>

        <div>
          <button
            onClick={() => setOutputOpen(!outputOpen)}
            className="mb-1.5 flex w-full items-center gap-1 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-400 transition-colors hover:text-zinc-600 dark:hover:text-zinc-300"
          >
            {outputOpen ? <ChevronRight size={12} className="rotate-90" /> : <ChevronRight size={12} />}
            Output
            {!outputOpen && (
              <span className="ml-1 truncate font-mono text-[10px] font-normal normal-case text-zinc-400">
                {outputPreview}
              </span>
            )}
          </button>
          {outputOpen && (
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-zinc-950 p-3 font-mono text-[11px] leading-relaxed text-emerald-300">
              {exec.output || "(empty)"}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

interface ParsedSkill {
  name: string;
  description: string;
}

function parseSkillsFromSystem(system: string): ParsedSkill[] {
  const marker = "Skills available:";
  const idx = system.indexOf(marker);
  if (idx === -1) return [];

  const block = system.slice(idx + marker.length);
  const skills: ParsedSkill[] = [];
  const lines = block.split("\n");

  for (const line of lines) {
    const match = line.match(/^\s*-\s+([^:]+):\s*\|?\s*(.*)$/);
    if (match) {
      const name = match[1].trim();
      const desc = match[2].trim();
      if (name) skills.push({ name, description: desc });
    }
  }

  return skills;
}

function SkillCatalog({ skills }: { skills: ParsedSkill[] }) {
  const [open, setOpen] = useState(false);
  if (skills.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-indigo-200 dark:border-indigo-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 bg-indigo-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-indigo-600 transition-colors hover:bg-indigo-100 dark:bg-indigo-950/30 dark:text-indigo-400 dark:hover:bg-indigo-950/50"
      >
        {open ? <ChevronRight size={14} className="rotate-90" /> : <ChevronRight size={14} />}
        <BookOpen size={14} />
        Skills in System Prompt
        <span className="ml-auto font-mono text-[10px] font-normal normal-case text-indigo-400 dark:text-indigo-500">
          {skills.length} skill{skills.length !== 1 ? "s" : ""}
        </span>
      </button>
      {open && (
        <div className="grid gap-2 bg-indigo-50 p-3 pt-0 sm:grid-cols-2 dark:bg-indigo-950/30">
          {skills.map((skill) => (
            <div
              key={skill.name}
              className="rounded-md border border-indigo-100 bg-white px-3 py-2 dark:border-indigo-800 dark:bg-zinc-900"
            >
              <span className="rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                {skill.name}
              </span>
              {skill.description && (
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">
                  {skill.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface CompactionEntry {
  toolName: string;
  placeholder: string;
  originalSize: number;
}

function analyzeCompaction(messages: unknown[]): {
  entries: CompactionEntry[];
  totalSavedChars: number;
  totalSavedTokens: number;
} {
  const compacted: Array<{ toolName: string; placeholder: string }> = [];
  const keptSizes: number[] = [];

  for (const msg of messages) {
    const m = msg as Record<string, unknown>;
    if (m.role === "user" && Array.isArray(m.content)) {
      for (const part of m.content) {
        const p = part as Record<string, unknown>;
        if (p.type !== "tool_result" || typeof p.content !== "string") continue;
        const match = p.content.match(/^\[Previous: used (.+)\]$/);
        if (match) {
          compacted.push({ toolName: match[1], placeholder: p.content });
        } else if (p.content.length > 100) {
          keptSizes.push(p.content.length);
        }
      }
    }
  }

  const avgOriginal = keptSizes.length > 0
    ? Math.round(keptSizes.reduce((a, b) => a + b, 0) / keptSizes.length)
    : 3000;

  const entries = compacted.map((c) => ({
    ...c,
    originalSize: avgOriginal,
  }));

  const totalSavedChars = entries.reduce((sum, e) => sum + (e.originalSize - e.placeholder.length), 0);

  return { entries, totalSavedChars, totalSavedTokens: Math.round(totalSavedChars / 4) };
}

function CompactionBadge({ messages }: { messages: unknown[] }) {
  const [open, setOpen] = useState(false);
  const { entries, totalSavedChars, totalSavedTokens } = analyzeCompaction(messages);
  if (entries.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-orange-200 dark:border-orange-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 bg-orange-50 px-3 py-2 text-left text-xs font-semibold text-orange-700 transition-colors hover:bg-orange-100 dark:bg-orange-950/30 dark:text-orange-300 dark:hover:bg-orange-950/50"
      >
        {open ? <ChevronRight size={14} className="rotate-90" /> : <ChevronRight size={14} />}
        <Shrink size={14} />
        <span className="uppercase tracking-wide">micro_compact</span>
        <span className="ml-auto font-mono text-[10px] font-normal text-orange-500 dark:text-orange-400">
          {entries.length} replaced | ~{totalSavedTokens.toLocaleString()} tokens saved
        </span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-orange-100 bg-white p-3 dark:border-orange-900 dark:bg-zinc-900">
          {entries.map((entry, i) => (
            <div key={i} className="overflow-hidden rounded-md border border-orange-100 dark:border-orange-800">
              <div className="flex items-center gap-2 bg-orange-50 px-3 py-2 dark:bg-orange-950/20">
                <span className="rounded bg-orange-200 px-1.5 py-0.5 font-mono text-[10px] font-bold text-orange-800 dark:bg-orange-800 dark:text-orange-200">
                  {entry.toolName}
                </span>
                <span className="font-mono text-[10px] text-zinc-400 line-through">
                  ~{entry.originalSize.toLocaleString()} chars
                </span>
                <span className="font-mono text-[10px] text-orange-500">
                  {entry.placeholder.length} chars
                </span>
                <span className="ml-auto rounded bg-orange-100 px-1.5 py-0.5 font-mono text-[9px] font-bold text-orange-600 dark:bg-orange-900 dark:text-orange-300">
                  -99%
                </span>
              </div>
              <div className="bg-zinc-950 px-3 py-2">
                <code className="font-mono text-[11px] text-orange-400">{entry.placeholder}</code>
              </div>
            </div>
          ))}

          <div className="flex items-center gap-3 rounded-md bg-orange-50 px-3 py-2 dark:bg-orange-950/20">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-orange-600 dark:text-orange-400">Total saved</span>
            <span className="font-mono text-xs font-bold text-orange-700 dark:text-orange-300">
              ~{totalSavedChars.toLocaleString()} chars
            </span>
            <span className="font-mono text-[10px] text-orange-400">
              (~{totalSavedTokens.toLocaleString()} tokens)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolCatalog({ tools }: { tools: Array<{ name?: string; description?: string }> }) {
  const [open, setOpen] = useState(false);
  if (tools.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-cyan-200 dark:border-cyan-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 bg-cyan-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-cyan-600 transition-colors hover:bg-cyan-100 dark:bg-cyan-950/30 dark:text-cyan-400 dark:hover:bg-cyan-950/50"
      >
        {open ? <ChevronRight size={14} className="rotate-90" /> : <ChevronRight size={14} />}
        <Terminal size={14} />
        Tools Available
        <span className="ml-auto font-mono text-[10px] font-normal normal-case text-cyan-400 dark:text-cyan-500">
          {tools.length} tool{tools.length !== 1 ? "s" : ""}
        </span>
      </button>
      {open && (
        <div className="grid gap-2 bg-cyan-50 p-3 pt-0 sm:grid-cols-2 dark:bg-cyan-950/30">
          {tools.map((tool) => (
            <div
              key={tool.name}
              className="rounded-md border border-cyan-100 bg-white px-3 py-2 dark:border-cyan-800 dark:bg-zinc-900"
            >
              <span className="rounded bg-cyan-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300">
                {tool.name}
              </span>
              {tool.description && (
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">
                  {tool.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CycleView({ cycle }: { cycle: TraceCycle }) {
  const [requestOpen, setRequestOpen] = useState(false);
  const [responseOpen, setResponseOpen] = useState(false);
  const [execOpen, setExecOpen] = useState(false);

  const msgCount = Array.isArray(cycle.request.messages) ? cycle.request.messages.length : 0;
  const toolCount = Array.isArray(cycle.request.tools) ? cycle.request.tools.length : 0;

  const isEnd = cycle.response.stop_reason === "end_turn";
  const agent = detectAgent(cycle);
  const isSub = agent.type !== "lead";
  const skills = typeof cycle.request.system === "string"
    ? parseSkillsFromSystem(cycle.request.system)
    : [];

  const requestTools = Array.isArray(cycle.request.tools) ? cycle.request.tools as Array<{ name?: string; description?: string }> : [];
  const userPrompt = Array.isArray(cycle.request.messages)
    ? (() => {
        const first = cycle.request.messages[0] as Record<string, unknown> | undefined;
        return first?.role === "user" && typeof first.content === "string" ? first.content : null;
      })()
    : null;
  const requestMessages = Array.isArray(cycle.request.messages) ? cycle.request.messages : [];
  const blockCount = cycle.response.content.length;
  const toolNames = cycle.tool_executions.map((e) => e.name);
  const uniqueToolNames = [...new Set(toolNames)];

  return (
    <div className={cn(
      "space-y-3",
      isSub && "rounded-lg border-l-4 border-purple-400 pl-4 dark:border-purple-600"
    )}>
      {agent.type === "subagent" && (
        <div className="flex items-center gap-2 rounded-md bg-purple-50 px-3 py-1.5 dark:bg-purple-950/30">
          <span className="h-2 w-2 rounded-full bg-purple-500" />
          <span className="text-xs font-semibold text-purple-700 dark:text-purple-300">
            Subagent Context
          </span>
          <span className="text-[10px] text-purple-500 dark:text-purple-400">
            Fresh messages[], isolated from parent
          </span>
        </div>
      )}
      {agent.type === "teammate" && (
        <div className="flex items-center gap-2 rounded-md bg-pink-50 px-3 py-1.5 dark:bg-pink-950/30">
          <span className="h-2.5 w-2.5 rounded-full bg-pink-500" />
          <span className="rounded bg-pink-200 px-1.5 py-0.5 font-mono text-[10px] font-bold text-pink-800 dark:bg-pink-800 dark:text-pink-200">
            {agent.name}
          </span>
          <span className="rounded bg-pink-100 px-1.5 py-0.5 text-[10px] text-pink-600 dark:bg-pink-900 dark:text-pink-300">
            {agent.role}
          </span>
          <span className="text-[10px] text-pink-500 dark:text-pink-400">
            Own thread, communicates via JSONL inbox
          </span>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-blue-200 dark:border-blue-800">
        <button
          onClick={() => setRequestOpen(!requestOpen)}
          className="flex w-full items-center gap-2 bg-blue-50 px-3 py-2.5 text-left transition-colors hover:bg-blue-100 dark:bg-blue-950/30 dark:hover:bg-blue-950/50"
        >
          {requestOpen ? <ChevronRight size={14} className="rotate-90 text-blue-500" /> : <ChevronRight size={14} className="text-blue-500" />}
          <Send size={14} className="text-blue-500" />
          <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Request</span>
          <span className="ml-auto flex items-center gap-2 font-mono text-[10px] text-blue-500 dark:text-blue-400">
            <span>POST /v1/messages</span>
            <span className="text-blue-300 dark:text-blue-600">|</span>
            <span>{msgCount} msg{msgCount !== 1 ? "s" : ""}</span>
            <span className="text-blue-300 dark:text-blue-600">|</span>
            <span>{toolCount} tool{toolCount !== 1 ? "s" : ""}</span>
          </span>
        </button>
        {requestOpen && (
          <div className="space-y-2 border-t border-blue-100 bg-white p-3 dark:border-blue-900 dark:bg-zinc-900">
            {userPrompt && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-950/30">
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-200 font-mono text-[9px] font-bold text-blue-700 dark:bg-blue-800 dark:text-blue-200">
                    1
                  </span>
                  <Send size={14} className="text-blue-600 dark:text-blue-400" />
                  <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">User Prompt</span>
                </div>
                <p className="text-sm font-bold leading-relaxed text-blue-900 dark:text-blue-200">{userPrompt}</p>
              </div>
            )}
            <CompactionBadge messages={requestMessages} />
            <ToolCatalog tools={requestTools} />
            <SkillCatalog skills={skills} />
            <JsonBlock
              data={cycle.request}
              label="Full Request JSON"
              defaultOpen={false}
              accentClass="border-blue-200 dark:border-blue-800"
            />
          </div>
        )}
      </div>

      <div className="flex justify-center">
        <ArrowDown size={16} className="text-zinc-300 dark:text-zinc-600" />
      </div>

      <div className="overflow-hidden rounded-lg border border-emerald-200 dark:border-emerald-800">
        <button
          onClick={() => setResponseOpen(!responseOpen)}
          className="flex w-full items-center gap-2 bg-emerald-50 px-3 py-2.5 text-left transition-colors hover:bg-emerald-100 dark:bg-emerald-950/30 dark:hover:bg-emerald-950/50"
        >
          {responseOpen ? <ChevronRight size={14} className="rotate-90 text-emerald-500" /> : <ChevronRight size={14} className="text-emerald-500" />}
          <MessageSquare size={14} className="text-emerald-500" />
          <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Response</span>
          <span className="ml-auto flex items-center gap-2 font-mono text-[10px]">
            <StopReasonBadge reason={cycle.response.stop_reason} />
            <span className="text-zinc-400">{blockCount} block{blockCount !== 1 ? "s" : ""}</span>
            <span className="text-zinc-300 dark:text-zinc-600">|</span>
            <span className="text-zinc-400">{cycle.response.usage.input_tokens} in / {cycle.response.usage.output_tokens} out</span>
            <span className="text-zinc-300 dark:text-zinc-600">|</span>
            <span className="text-zinc-400">{cycle.elapsed_ms}ms</span>
          </span>
        </button>
        {responseOpen && (
          <div className="space-y-3 border-t border-emerald-100 bg-white p-3 dark:border-emerald-900 dark:bg-zinc-900">
            {cycle.response.content.map((block, i) => (
              <ContentBlockCard key={i} block={block} index={i} />
            ))}
            <JsonBlock
              data={cycle.response}
              label="Full Response JSON"
              defaultOpen={false}
              accentClass="border-emerald-200 dark:border-emerald-800"
            />
          </div>
        )}
      </div>

      {cycle.tool_executions.length > 0 && (
        <>
          <div className="flex justify-center">
            <ArrowDown size={16} className="text-zinc-300 dark:text-zinc-600" />
          </div>
          <div className="overflow-hidden rounded-lg border border-amber-200 dark:border-amber-800">
            <button
              onClick={() => setExecOpen(!execOpen)}
              className="flex w-full items-center gap-2 bg-amber-50 px-3 py-2.5 text-left transition-colors hover:bg-amber-100 dark:bg-amber-950/30 dark:hover:bg-amber-950/50"
            >
              {execOpen ? <ChevronRight size={14} className="rotate-90 text-amber-500" /> : <ChevronRight size={14} className="text-amber-500" />}
              <Zap size={14} className="text-amber-500" />
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Tool Execution</span>
              <span className="ml-auto flex items-center gap-2 font-mono text-[10px] text-amber-600 dark:text-amber-400">
                <span>{uniqueToolNames.join(", ")}</span>
                <span className="text-amber-300 dark:text-amber-700">|</span>
                <span>{toolNames.length} run{toolNames.length !== 1 ? "s" : ""}</span>
              </span>
            </button>
            {execOpen && (
              <div className="space-y-3 border-t border-amber-100 bg-white p-3 dark:border-amber-900 dark:bg-zinc-900">
                {cycle.tool_executions.map((exec, i) => (
                  <ToolExecutionCard key={i} exec={exec} index={i} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <div className="flex items-center gap-3 pt-2">
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
        <span
          className={cn(
            "font-mono text-[10px]",
            isEnd ? "text-emerald-500" : "text-zinc-400"
          )}
        >
          {isEnd
            ? "Agent finished (stop_reason: end_turn)"
            : "Loop continues (stop_reason: tool_use)"}
        </span>
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
      </div>
    </div>
  );
}

function CarouselNav({
  currentCycle,
  totalCycles,
  cycles,
  onPrev,
  onNext,
  onGoTo,
  onReset,
  isFirst,
  isLast,
}: {
  currentCycle: number;
  totalCycles: number;
  cycles: TraceCycle[];
  onPrev: () => void;
  onNext: () => void;
  onGoTo: (n: number) => void;
  onReset: () => void;
  isFirst: boolean;
  isLast: boolean;
}) {
  const currentAgent = cycles[currentCycle] ? detectAgent(cycles[currentCycle]) : { type: "lead" as const };
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <button
          onClick={onReset}
          disabled={isFirst}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-200 text-zinc-500 transition-colors hover:bg-zinc-100 disabled:opacity-30 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
          title="Reset to first cycle"
        >
          <RotateCcw size={14} />
        </button>
        <button
          onClick={onPrev}
          disabled={isFirst}
          className="flex h-8 items-center gap-1 rounded-lg border border-zinc-200 px-2.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 disabled:opacity-30 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          title="Previous cycle"
        >
          <ChevronLeft size={16} />
          Prev
        </button>
        <button
          onClick={onNext}
          disabled={isLast}
          className="flex h-8 items-center gap-1 rounded-lg border border-zinc-200 px-2.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 disabled:opacity-30 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          title="Next cycle"
        >
          Next
          <ChevronRight size={16} />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex gap-1.5">
          {cycles.map((c, i) => {
            const a = detectAgent(c);
            const colorMap = {
              lead: { active: "bg-blue-500", inactive: "bg-zinc-300 hover:bg-zinc-400 dark:bg-zinc-600 dark:hover:bg-zinc-500" },
              subagent: { active: "bg-purple-500", inactive: "bg-purple-300 hover:bg-purple-400 dark:bg-purple-700 dark:hover:bg-purple-600" },
              teammate: { active: "bg-pink-500", inactive: "bg-pink-300 hover:bg-pink-400 dark:bg-pink-700 dark:hover:bg-pink-600" },
            };
            const colors = colorMap[a.type];
            const label = a.type === "teammate" ? ` (${a.name})` : a.type === "subagent" ? " (Subagent)" : "";
            return (
              <button
                key={i}
                onClick={() => onGoTo(i)}
                className={cn(
                  "h-2.5 w-2.5 rounded-full transition-all",
                  i === currentCycle ? cn("scale-125", colors.active) : colors.inactive
                )}
                title={`Cycle ${i + 1}${label}`}
              />
            );
          })}
        </div>
        <span className="flex items-center gap-1.5 font-mono text-xs text-zinc-400">
          Cycle {currentCycle + 1} / {totalCycles}
          {currentAgent.type === "subagent" && (
            <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              Subagent
            </span>
          )}
          {currentAgent.type === "teammate" && (
            <span className="rounded-full bg-pink-100 px-1.5 py-0.5 text-[10px] font-semibold text-pink-700 dark:bg-pink-900/40 dark:text-pink-300">
              {currentAgent.name}
              {currentAgent.role && (
                <span className="ml-1 font-normal text-pink-500 dark:text-pink-400">
                  {currentAgent.role}
                </span>
              )}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 80 : -80,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -80 : 80,
    opacity: 0,
  }),
};

interface ApiInspectorProps {
  version: string;
}

export function ApiInspector({ version }: ApiInspectorProps) {
  const {
    trace,
    currentCycle,
    totalCycles,
    next,
    prev,
    goToCycle,
    isFirst,
    isLast,
    cumulativeTokens,
  } = useTraceViewer(version);

  const [direction, setDirection] = useState(0);

  const handleNext = () => {
    setDirection(1);
    next();
  };
  const handlePrev = () => {
    setDirection(-1);
    prev();
  };
  const handleGoTo = (n: number) => {
    setDirection(n > currentCycle ? 1 : -1);
    goToCycle(n);
  };
  const handleReset = () => {
    setDirection(-1);
    goToCycle(0);
  };

  if (!trace) {
    return (
      <div className="flex min-h-[200px] items-center justify-center text-sm text-zinc-400 dark:text-zinc-500">
        No API trace available for {version}. Run{" "}
        <code className="mx-1 rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs dark:bg-zinc-800">
          python agents/capture_trace.py {version} &quot;your prompt&quot;
        </code>{" "}
        to generate one.
      </div>
    );
  }

  const cycle = trace.cycles[currentCycle];

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          API Inspector
        </h2>
        <div className="flex items-center gap-2 text-[11px] text-zinc-400">
          <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono dark:bg-zinc-800">
            {trace.model}
          </span>
          <span className="font-mono">
            {cumulativeTokens.input} in / {cumulativeTokens.output} out
          </span>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-700">
        <div className="sticky top-0 z-10 border-b border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-700 dark:bg-zinc-900">
          <CarouselNav
            currentCycle={currentCycle}
            totalCycles={totalCycles}
            cycles={trace.cycles}
            onPrev={handlePrev}
            onNext={handleNext}
            onGoTo={handleGoTo}
            onReset={handleReset}
            isFirst={isFirst}
            isLast={isLast}
          />
        </div>

        <div className="relative overflow-hidden">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentCycle}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="p-4"
            >
              <CycleView cycle={cycle} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
