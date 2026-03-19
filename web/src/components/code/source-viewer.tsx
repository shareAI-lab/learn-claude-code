"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { computeDiffRows } from "@/lib/diff-utils";
import { cn } from "@/lib/utils";
import { Fira_Code } from "next/font/google";
import { useTranslations } from "@/lib/i18n";

const firaCode = Fira_Code({ subsets: ["latin"], display: "swap" });

interface SourceViewerProps {
  source: string;
  filename: string;
  prevSource?: string;
  prevFilename?: string;
}

function highlightLine(line: string): React.ReactNode[] {
  const trimmed = line.trimStart();
  if (trimmed.startsWith("#")) {
    return [
      <span key={0} className="text-zinc-500 italic">
        {line}
      </span>,
    ];
  }
  if (trimmed.startsWith("@")) {
    return [
      <span key={0} className="text-amber-400">
        {line}
      </span>,
    ];
  }
  if (trimmed.startsWith('"""') || trimmed.startsWith("'''")) {
    return [
      <span key={0} className="text-emerald-500/80 italic">
        {line}
      </span>,
    ];
  }

  const keywordSet = new Set([
    "def", "class", "import", "from", "return", "if", "elif", "else",
    "while", "for", "in", "not", "and", "or", "is", "None", "True",
    "False", "try", "except", "raise", "with", "as", "yield", "break",
    "continue", "pass", "global", "lambda", "async", "await",
  ]);

  const parts = line.split(
    /(\b(?:def|class|import|from|return|if|elif|else|while|for|in|not|and|or|is|None|True|False|try|except|raise|with|as|yield|break|continue|pass|global|lambda|async|await|self)\b|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|f"(?:[^"\\]|\\.)*"|f'(?:[^'\\]|\\.)*'|#.*$|\b\d+(?:\.\d+)?\b)/
  );

  return parts.map((part, idx) => {
    if (!part) return null;
    if (keywordSet.has(part)) {
      return <span key={idx} className="text-indigo-400 font-medium">{part}</span>;
    }
    if (part === "self") {
      return <span key={idx} className="text-purple-400">{part}</span>;
    }
    if (part.startsWith("#")) {
      return <span key={idx} className="text-zinc-500 italic">{part}</span>;
    }
    if (
      (part.startsWith('"') && part.endsWith('"')) ||
      (part.startsWith("'") && part.endsWith("'")) ||
      (part.startsWith('f"') && part.endsWith('"')) ||
      (part.startsWith("f'") && part.endsWith("'"))
    ) {
      return <span key={idx} className="text-emerald-400">{part}</span>;
    }
    if (/^\d+(?:\.\d+)?$/.test(part)) {
      return <span key={idx} className="text-orange-400">{part}</span>;
    }
    return <span key={idx} className="text-zinc-300">{part}</span>;
  });
}

export function SourceViewer({ source, filename, prevSource }: SourceViewerProps) {
  const t = useTranslations("version");
  const lines = useMemo(() => source.split("\n"), [source]);
  const hasDiff = !!prevSource && prevSource !== source;
  const [viewMode, setViewMode] = useState<"source" | "diff">("source");

  const diffRows = useMemo(() => {
    if (viewMode === "diff" && prevSource) {
      return computeDiffRows(prevSource, source);
    }
    return [];
  }, [prevSource, source, viewMode]);

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-black overflow-hidden shadow-2xl">
      <div className="flex items-center gap-4 border-b border-zinc-800 bg-zinc-950 px-4 py-2">
        <div className="flex gap-1.5 shrink-0">
          <span className="h-3 w-3 rounded-full bg-rose-500/80 shadow-[0_0_8px_rgba(244,63,94,0.4)]" />
          <span className="h-3 w-3 rounded-full bg-amber-500/80 shadow-[0_0_8px_rgba(245,158,11,0.4)]" />
          <span className="h-3 w-3 rounded-full bg-emerald-500/80 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
        </div>
        <span className={cn("font-mono text-xs text-zinc-400 truncate", firaCode.className)}>{filename}</span>

        {hasDiff && (
          <div className="ml-auto flex items-center rounded-full bg-zinc-900 p-0.5 shadow-inner border border-zinc-800/80 shrink-0">
            <button
              onClick={() => setViewMode("source")}
              className={cn(
                "relative px-3 py-1 text-[11px] uppercase tracking-wider font-bold outline-none transition-colors rounded-full",
                viewMode === "source" ? "text-white" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              {viewMode === "source" && (
                <motion.div
                  layoutId="active-pill-source-viewer"
                  className="absolute inset-0 rounded-full bg-zinc-800 border border-zinc-700/50 shadow-sm"
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
              <span className="relative z-10">{t("view_source") || "Source"}</span>
            </button>
            <button
              onClick={() => setViewMode("diff")}
              className={cn(
                "relative px-3 py-1 text-[11px] uppercase tracking-wider font-bold outline-none transition-colors rounded-full",
                viewMode === "diff" ? "text-white" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              {viewMode === "diff" && (
                <motion.div
                  layoutId="active-pill-source-viewer"
                  className="absolute inset-0 rounded-full bg-zinc-800 border border-zinc-700/50 shadow-sm"
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
              <span className="relative z-10">{t("view_diff") || "Diff"}</span>
            </button>
          </div>
        )}
      </div>

      <div className="relative overflow-x-auto bg-[#050505]">
        <div 
          className="absolute inset-0 opacity-[0.04] pointer-events-none" 
          style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '16px 16px' }}
        />

        <AnimatePresence mode="wait">
          {viewMode === "source" ? (
            <motion.pre
              key="source"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={cn("p-2 text-[10px] leading-[1.6] sm:p-4 sm:text-xs sm:leading-[1.7] relative z-10", firaCode.className)}
            >
              <code>
                {lines.map((line, i) => (
                  <div key={i} className="flex group">
                    <span className="mr-3 inline-block w-6 shrink-0 select-none text-right text-zinc-600/60 sm:mr-5 sm:w-8 group-hover:text-zinc-500 transition-colors">
                      {i + 1}
                    </span>
                    <span>{highlightLine(line) || " "}</span>
                  </div>
                ))}
              </code>
            </motion.pre>
          ) : (
            <motion.pre
              key="diff"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={cn("py-2 text-[10px] leading-[1.6] sm:py-4 sm:text-xs sm:leading-[1.7] relative z-10", firaCode.className)}
            >
              <code>
                {diffRows.map((row, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: Math.min(i * 0.002, 0.1), duration: 0.15 }}
                    className={cn(
                      "flex group border-l-4 px-2 sm:px-4",
                      row.type === "add" && "bg-emerald-950/20 border-emerald-500/60",
                      row.type === "remove" && "bg-rose-950/20 border-rose-500/60",
                      row.type === "context" && "border-transparent hover:bg-white/2"
                    )}
                  >
                    <div className="flex shrink-0 w-12 sm:w-16 select-none opacity-40 group-hover:opacity-80 transition-opacity font-medium">
                      <span className="w-1/2 text-right text-zinc-500 pr-2">
                        {row.oldNum ?? ""}
                      </span>
                      <span className="w-1/2 text-right text-zinc-500 pr-2">
                        {row.newNum ?? ""}
                      </span>
                    </div>
                    <div
                      className={cn(
                        "w-full",
                        row.type === "add" && "shadow-emerald-500",
                        row.type === "remove" && "line-through decoration-rose-500/40 opacity-70",
                      )}
                    >
                      {row.text ? highlightLine(row.text) : " "}
                    </div>
                  </motion.div>
                ))}
              </code>
            </motion.pre>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
