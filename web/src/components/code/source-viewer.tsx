"use client";

import { computeDiffRows } from "@/lib/diff-utils";
import { useTranslations } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { VersionCompareTarget } from "@/types/agent-data";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown } from "lucide-react";
import { Fira_Code } from "next/font/google";
import { useEffect, useMemo, useRef, useState } from "react";

const firaCode = Fira_Code({ subsets: ["latin"], display: "swap" });

interface SourceViewerProps {
  source: string;
  filename: string;
  currentVersionId: string;
  defaultCompareVersionId?: string | null;
  compareTargets: VersionCompareTarget[];
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
    "def",
    "class",
    "import",
    "from",
    "return",
    "if",
    "elif",
    "else",
    "while",
    "for",
    "in",
    "not",
    "and",
    "or",
    "is",
    "None",
    "True",
    "False",
    "try",
    "except",
    "raise",
    "with",
    "as",
    "yield",
    "break",
    "continue",
    "pass",
    "global",
    "lambda",
    "async",
    "await",
  ]);

  const parts = line.split(
    /(\b(?:def|class|import|from|return|if|elif|else|while|for|in|not|and|or|is|None|True|False|try|except|raise|with|as|yield|break|continue|pass|global|lambda|async|await|self)\b|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|f"(?:[^"\\]|\\.)*"|f'(?:[^'\\]|\\.)*'|#.*$|\b\d+(?:\.\d+)?\b)/,
  );

  return parts.map((part, idx) => {
    if (!part) return null;
    if (keywordSet.has(part)) {
      return (
        <span key={idx} className="text-indigo-400 font-medium">
          {part}
        </span>
      );
    }
    if (part === "self") {
      return (
        <span key={idx} className="text-purple-400">
          {part}
        </span>
      );
    }
    if (part.startsWith("#")) {
      return (
        <span key={idx} className="text-zinc-500 italic">
          {part}
        </span>
      );
    }
    if (
      (part.startsWith('"') && part.endsWith('"')) ||
      (part.startsWith("'") && part.endsWith("'")) ||
      (part.startsWith('f"') && part.endsWith('"')) ||
      (part.startsWith("f'") && part.endsWith("'"))
    ) {
      return (
        <span key={idx} className="text-emerald-400">
          {part}
        </span>
      );
    }
    if (/^\d+(?:\.\d+)?$/.test(part)) {
      return (
        <span key={idx} className="text-orange-400">
          {part}
        </span>
      );
    }
    return (
      <span key={idx} className="text-zinc-300">
        {part}
      </span>
    );
  });
}

function CompareDropdown({
  options,
  value,
  onChange,
  placeholder,
}: {
  options: { id: string; label: string }[];
  value: string;
  onChange: (val: string) => void;
  placeholder: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((o) => o.id === value);

  return (
    <div className="relative mt-0.5" ref={ref}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center justify-between w-full min-w-[180px] py-1 pl-3 pr-2 text-[11px] border rounded outline-none transition-all cursor-pointer",
          isOpen
            ? "border-zinc-600 text-zinc-100 bg-zinc-800/80"
            : "border-zinc-800/80 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 bg-zinc-900/50 hover:bg-zinc-800/50",
        )}
      >
        <span className="truncate pr-2">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 shrink-0 transition-transform duration-200",
            isOpen ? "rotate-180 text-zinc-300" : "text-zinc-500",
          )}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-1.5 w-64 bg-zinc-900/95 backdrop-blur-md border border-zinc-800/80 rounded-md shadow-2xl z-50 overflow-hidden"
          >
            <div className="max-h-[300px] overflow-y-auto py-1">
              {options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => {
                    onChange(opt.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "flex items-center w-full px-3 py-2 text-left text-[11px] transition-colors",
                    value === opt.id
                      ? "bg-zinc-800 text-white font-medium"
                      : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200",
                  )}
                >
                  <span className="flex-1 truncate">{opt.label}</span>
                  {value === opt.id && (
                    <Check className="w-3.5 h-3.5 text-zinc-300 ml-2 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SourceViewer({
  source,
  filename,
  currentVersionId,
  defaultCompareVersionId,
  compareTargets,
}: SourceViewerProps) {
  const t = useTranslations("version");
  const lines = useMemo(() => source.split("\n"), [source]);
  const [viewMode, setViewMode] = useState<"source" | "diff">("source");
  const [selectedBaseId, setSelectedBaseId] = useState(
    defaultCompareVersionId ?? "",
  );

  useEffect(() => {
    setSelectedBaseId(defaultCompareVersionId ?? "");
  }, [currentVersionId, defaultCompareVersionId]);

  const selectedBase = useMemo(
    () => compareTargets.find((target) => target.id === selectedBaseId),
    [compareTargets, selectedBaseId],
  );
  const canDiff = !!selectedBase;

  const diffRows = useMemo(() => {
    if (viewMode === "diff" && selectedBase) {
      return computeDiffRows(selectedBase.source, source);
    }
    return [];
  }, [selectedBase, source, viewMode]);

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-black overflow-hidden shadow-2xl">
      <div className="flex flex-wrap items-center justify-between border-b border-zinc-800/80 bg-[#0a0a0a] px-5 py-3 relative z-20">
        <div className="flex items-center gap-4">
          <div className="flex gap-2 shrink-0">
            <span className="h-2.5 w-2.5 rounded-full bg-zinc-800 hover:bg-rose-500 transition-colors duration-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-zinc-800 hover:bg-amber-500 transition-colors duration-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-zinc-800 hover:bg-emerald-500 transition-colors duration-300" />
          </div>
          <span
            className={cn(
              "font-mono text-[13px] text-zinc-300 tracking-tight",
              firaCode.className,
            )}
          >
            {filename}
          </span>
        </div>

        <div className="ml-auto flex flex-wrap items-center justify-end gap-4">
          <AnimatePresence>
            {viewMode === "diff" && compareTargets.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                exit={{
                  opacity: 0,
                  x: 10,
                  filter: "blur(4px)",
                  position: "absolute",
                }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-2 font-mono text-zinc-500 mr-2 z-30"
              >
                <span className="text-[10px] uppercase tracking-widest opacity-60 mt-0.5">
                  vs
                </span>
                <CompareDropdown
                  options={compareTargets}
                  value={selectedBaseId}
                  onChange={setSelectedBaseId}
                  placeholder={t("select_compare_target") || "Select version"}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {compareTargets.length > 0 && (
            <div className="flex items-center rounded-md bg-zinc-900/60 p-1 border border-zinc-800/80 backdrop-blur-sm shrink-0 relative z-10">
              <button
                onClick={() => setViewMode("source")}
                className={cn(
                  "relative px-4 py-1.5 text-[10px] uppercase tracking-[0.1em] font-bold outline-none transition-colors rounded-sm",
                  viewMode === "source"
                    ? "text-zinc-100"
                    : "text-zinc-500 hover:text-zinc-300",
                )}
              >
                {viewMode === "source" && (
                  <motion.div
                    layoutId="active-pill-source-viewer"
                    className="absolute inset-0 rounded-sm bg-zinc-800 shadow-[0_1px_2px_rgba(0,0,0,0.5)] border border-zinc-700/50"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
                <span className="relative z-10">
                  {t("view_source") || "Source"}
                </span>
              </button>
              <button
                onClick={() => {
                  if (!canDiff) {
                    const fallback = defaultCompareVersionId || compareTargets[0]?.id;
                    if (fallback) setSelectedBaseId(fallback);
                  }
                  setViewMode("diff");
                }}
                className={cn(
                  "relative px-4 py-1.5 text-[10px] uppercase tracking-[0.1em] font-bold outline-none transition-colors rounded-sm",
                  viewMode === "diff" ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300",
                )}
              >
                {viewMode === "diff" && (
                  <motion.div
                    layoutId="active-pill-source-viewer"
                    className="absolute inset-0 rounded-sm bg-zinc-800 shadow-[0_1px_2px_rgba(0,0,0,0.5)] border border-zinc-700/50"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
                <span className="relative z-10">
                  {t("view_diff") || "Diff"}
                </span>
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="relative bg-[#050505]">
        <div
          className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(#ffffff 1px, transparent 1px)",
            backgroundSize: "16px 16px",
          }}
        />

        <div className="overflow-x-auto relative z-10">
          <AnimatePresence mode="wait">
            {viewMode === "source" ? (
              <motion.pre
                key="source"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className={cn(
                  "inline-block min-w-full p-2 text-[10px] leading-[1.6] sm:p-4 sm:text-xs sm:leading-[1.7]",
                  firaCode.className,
                )}
              >
                <code className="block">
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
            ) : !canDiff ? (
              <motion.div
                key="diff-empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-center justify-center py-20 text-zinc-500 text-sm"
              >
                {t("select_compare_target") || "Select a version to compare"}
              </motion.div>
            ) : (
              <motion.pre
                key="diff"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className={cn(
                  "inline-block min-w-full py-2 text-[10px] leading-[1.6] sm:py-4 sm:text-xs sm:leading-[1.7]",
                  firaCode.className,
                )}
              >
                <code className="block">
                  {diffRows.map((row, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{
                        delay: Math.min(i * 0.002, 0.1),
                        duration: 0.15,
                      }}
                      className={cn(
                        "flex group border-l-[3px] px-2 sm:px-4 py-0.5",
                        row.type === "add" &&
                          "bg-emerald-950/30 border-emerald-400/70 shadow-[inset_0_0_15px_rgba(16,185,129,0.03)]",
                        row.type === "remove" &&
                          "bg-rose-950/30 border-rose-500/70 shadow-[inset_0_0_15px_rgba(244,63,94,0.03)]",
                        row.type === "context" &&
                          "border-transparent hover:bg-white/[0.03]",
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
                          row.type === "remove" &&
                            "line-through decoration-rose-500/40 opacity-70",
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
    </div>
  );
}
