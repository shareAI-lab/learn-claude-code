"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface JsonBlockProps {
  data: unknown;
  label: string;
  defaultOpen?: boolean;
  maxHeight?: number;
  accentClass?: string;
}

function formatJson(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

export function JsonBlock({
  data,
  label,
  defaultOpen = false,
  maxHeight = 400,
  accentClass = "border-zinc-200 dark:border-zinc-700",
}: JsonBlockProps) {
  const [open, setOpen] = useState(defaultOpen);
  const formatted = formatJson(data);
  const lineCount = formatted.split("\n").length;

  return (
    <div className={cn("overflow-hidden rounded-lg border", accentClass)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-zinc-500 transition-colors hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/50"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span>{label}</span>
        <span className="ml-auto font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
          {lineCount} lines
        </span>
      </button>
      {open && (
        <div
          className="overflow-auto border-t border-zinc-100 bg-zinc-950 p-3 dark:border-zinc-800"
          style={{ maxHeight }}
        >
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-zinc-300">
            {formatted}
          </pre>
        </div>
      )}
    </div>
  );
}
