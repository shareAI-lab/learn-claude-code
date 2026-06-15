"use client";

import { useState, useMemo } from "react";
import { diffLines, Change } from "diff";
import { cn } from "@/lib/utils";

interface CodeDiffProps {
  oldSource: string;
  newSource: string;
  oldLabel: string;
  newLabel: string;
}

export function CodeDiff({ oldSource, newSource, oldLabel, newLabel }: CodeDiffProps) {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");

  const changes = useMemo(() => diffLines(oldSource, newSource), [oldSource, newSource]);

  return (
    <div>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 truncate text-sm text-zinc-500 dark:text-zinc-400">
          <span className="font-medium text-zinc-700 dark:text-zinc-300">{oldLabel}</span>
          {" -> "}
          <span className="font-medium text-zinc-700 dark:text-zinc-300">{newLabel}</span>
        </div>
        <div className="flex shrink-0 rounded-lg border border-zinc-200 dark:border-zinc-700">
          <button
            onClick={() => setViewMode("unified")}
            className={cn(
              "min-h-[36px] px-3 text-xs font-medium transition-colors",
              viewMode === "unified"
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400"
            )}
          >
            Unified
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={cn(
              "min-h-[36px] px-3 text-xs font-medium transition-colors sm:inline-flex hidden",
              viewMode === "split"
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400"
            )}
          >
            Split
          </button>
        </div>
      </div>

      {viewMode === "unified" ? (
        <UnifiedView changes={changes} />
      ) : (
        <SplitView changes={changes} />
      )}
    </div>
  );
}

function UnifiedView({ changes }: { changes: Change[] }) {
  let oldLine = 1;
  let newLine = 1;

  const rows: { oldNum: number | null; newNum: number | null; type: "add" | "remove" | "context"; text: string }[] = [];

  for (const change of changes) {
    const lines = change.value.replace(/\n$/, "").split("\n");
    for (const line of lines) {
      if (change.added) {
        rows.push({ oldNum: null, newNum: newLine++, type: "add", text: line });
      } else if (change.removed) {
        rows.push({ oldNum: oldLine++, newNum: null, type: "remove", text: line });
      } else {
        rows.push({ oldNum: oldLine++, newNum: newLine++, type: "context", text: line });
      }
    }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="w-full border-collapse font-mono text-xs leading-5">
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={cn(
                row.type === "add" && "bg-green-50 dark:bg-green-950/30",
                row.type === "remove" && "bg-red-50 dark:bg-red-950/30"
              )}
            >
              <td className="w-10 select-none border-r border-zinc-200 px-2 text-right text-zinc-400 dark:border-zinc-700 dark:text-zinc-600">
                {row.oldNum ?? ""}
              </td>
              <td className="w-10 select-none border-r border-zinc-200 px-2 text-right text-zinc-400 dark:border-zinc-700 dark:text-zinc-600">
                {row.newNum ?? ""}
              </td>
              <td className="w-4 select-none px-1 text-center">
                {row.type === "add" && <span className="text-green-600 dark:text-green-400">+</span>}
                {row.type === "remove" && <span className="text-red-600 dark:text-red-400">-</span>}
              </td>
              <td className="whitespace-pre px-2">
                <span
                  className={cn(
                    row.type === "add" && "text-green-800 dark:text-green-300",
                    row.type === "remove" && "text-red-800 dark:text-red-300",
                    row.type === "context" && "text-zinc-700 dark:text-zinc-300"
                  )}
                >
                  {row.text}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SplitView({ changes }: { changes: Change[] }) {
  let oldLine = 1;
  let newLine = 1;

  type SplitRow = {
    left: { num: number | null; text: string; type: "remove" | "context" | "empty" };
    right: { num: number | null; text: string; type: "add" | "context" | "empty" };
  };

  const rows: SplitRow[] = [];

  for (const change of changes) {
    const lines = change.value.replace(/\n$/, "").split("\n");
    if (change.removed) {
      for (const line of lines) {
        rows.push({
          left: { num: oldLine++, text: line, type: "remove" },
          right: { num: null, text: "", type: "empty" },
        });
      }
    } else if (change.added) {
      let filled = 0;
      for (const line of lines) {
        // Try to fill in empty right-side slots from preceding removes
        const lastUnfilled = rows.length - lines.length + filled;
        if (
          lastUnfilled >= 0 &&
          lastUnfilled < rows.length &&
          rows[lastUnfilled].right.type === "empty" &&
          rows[lastUnfilled].left.type === "remove"
        ) {
          rows[lastUnfilled].right = { num: newLine++, text: line, type: "add" };
        } else {
          rows.push({
            left: { num: null, text: "", type: "empty" },
            right: { num: newLine++, text: line, type: "add" },
          });
        }
        filled++;
      }
    } else {
      for (const line of lines) {
        rows.push({
          left: { num: oldLine++, text: line, type: "context" },
          right: { num: newLine++, text: line, type: "context" },
        });
      }
    }
  }

  const cellClass = (type: string) =>
    cn(
      "whitespace-pre px-2",
      type === "add" && "bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-300",
      type === "remove" && "bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-300",
      type === "context" && "text-zinc-700 dark:text-zinc-300",
      type === "empty" && "bg-zinc-50 dark:bg-zinc-900"
    );

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="w-full border-collapse font-mono text-xs leading-5">
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td className="w-10 select-none border-r border-zinc-200 px-2 text-right text-zinc-400 dark:border-zinc-700 dark:text-zinc-600">
                {row.left.num ?? ""}
              </td>
              <td className={cn("w-1/2 border-r border-zinc-200 dark:border-zinc-700", cellClass(row.left.type))}>
                {row.left.text}
              </td>
              <td className="w-10 select-none border-r border-zinc-200 px-2 text-right text-zinc-400 dark:border-zinc-700 dark:text-zinc-600">
                {row.right.num ?? ""}
              </td>
              <td className={cn("w-1/2", cellClass(row.right.type))}>
                {row.right.text}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
