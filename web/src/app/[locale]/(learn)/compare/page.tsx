"use client";

import { useState, useMemo } from "react";
import { useLocale, useTranslations } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META } from "@/lib/constants";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { LayerBadge } from "@/components/ui/badge";
import { CodeDiff } from "@/components/diff/code-diff";
import { ArchDiagram } from "@/components/architecture/arch-diagram";
import { ArrowRight, FileCode, Wrench, Box, FunctionSquare } from "lucide-react";
import type { VersionIndex } from "@/types/agent-data";
import versionData from "@/data/generated/versions.json";

const data = versionData as VersionIndex;

export default function ComparePage() {
  const t = useTranslations("compare");
  const locale = useLocale();
  const [versionA, setVersionA] = useState<string>("");
  const [versionB, setVersionB] = useState<string>("");

  const infoA = useMemo(() => data.versions.find((v) => v.id === versionA), [versionA]);
  const infoB = useMemo(() => data.versions.find((v) => v.id === versionB), [versionB]);
  const metaA = versionA ? VERSION_META[versionA] : null;
  const metaB = versionB ? VERSION_META[versionB] : null;

  const comparison = useMemo(() => {
    if (!infoA || !infoB) return null;
    const toolsA = new Set(infoA.tools);
    const toolsB = new Set(infoB.tools);
    const onlyA = infoA.tools.filter((t) => !toolsB.has(t));
    const onlyB = infoB.tools.filter((t) => !toolsA.has(t));
    const shared = infoA.tools.filter((t) => toolsB.has(t));

    const classesA = new Set(infoA.classes.map((c) => c.name));
    const classesB = new Set(infoB.classes.map((c) => c.name));
    const newClasses = infoB.classes.map((c) => c.name).filter((c) => !classesA.has(c));

    const funcsA = new Set(infoA.functions.map((f) => f.name));
    const funcsB = new Set(infoB.functions.map((f) => f.name));
    const newFunctions = infoB.functions.map((f) => f.name).filter((f) => !funcsA.has(f));

    return {
      locDelta: infoB.loc - infoA.loc,
      toolsOnlyA: onlyA,
      toolsOnlyB: onlyB,
      toolsShared: shared,
      newClasses,
      newFunctions,
    };
  }, [infoA, infoB]);

  return (
    <div className="py-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">{t("subtitle")}</p>
      </div>

      {/* Selectors */}
      <div className="mb-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-zinc-600 dark:text-zinc-400">
            {t("select_a")}
          </label>
          <select
            value={versionA}
            onChange={(e) => setVersionA(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="">-- select --</option>
            {LEARNING_PATH.map((v) => (
              <option key={v} value={v}>
                {v} - {VERSION_META[v]?.title}
              </option>
            ))}
          </select>
        </div>

        <ArrowRight size={20} className="mt-5 hidden text-zinc-400 sm:block" />

        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-zinc-600 dark:text-zinc-400">
            {t("select_b")}
          </label>
          <select
            value={versionB}
            onChange={(e) => setVersionB(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="">-- select --</option>
            {LEARNING_PATH.map((v) => (
              <option key={v} value={v}>
                {v} - {VERSION_META[v]?.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      {infoA && infoB && comparison && (
        <div className="space-y-8">
          {/* Side-by-side version info */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{metaA?.title || versionA}</CardTitle>
                <p className="text-sm text-zinc-500">{metaA?.subtitle}</p>
              </CardHeader>
              <div className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <p>{infoA.loc} LOC</p>
                <p>{infoA.tools.length} tools</p>
                {metaA && <LayerBadge layer={metaA.layer}>{metaA.layer}</LayerBadge>}
              </div>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>{metaB?.title || versionB}</CardTitle>
                <p className="text-sm text-zinc-500">{metaB?.subtitle}</p>
              </CardHeader>
              <div className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <p>{infoB.loc} LOC</p>
                <p>{infoB.tools.length} tools</p>
                {metaB && <LayerBadge layer={metaB.layer}>{metaB.layer}</LayerBadge>}
              </div>
            </Card>
          </div>

          {/* Side-by-side Architecture Diagrams */}
          <div>
            <h2 className="mb-4 text-xl font-semibold">{t("architecture")}</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {metaA?.title || versionA}
                </h3>
                <ArchDiagram version={versionA} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {metaB?.title || versionB}
                </h3>
                <ArchDiagram version={versionB} />
              </div>
            </div>
          </div>

          {/* Structural diff */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <FileCode size={16} />
                  <span className="text-sm">{t("loc_delta")}</span>
                </div>
              </CardHeader>
              <CardTitle>
                <span className={comparison.locDelta >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                  {comparison.locDelta >= 0 ? "+" : ""}{comparison.locDelta}
                </span>
                <span className="ml-2 text-sm font-normal text-zinc-500">{t("lines")}</span>
              </CardTitle>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <Wrench size={16} />
                  <span className="text-sm">{t("new_tools_in_b")}</span>
                </div>
              </CardHeader>
              <CardTitle>
                <span className="text-blue-600 dark:text-blue-400">{comparison.toolsOnlyB.length}</span>
              </CardTitle>
              {comparison.toolsOnlyB.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {comparison.toolsOnlyB.map((tool) => (
                    <span key={tool} className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <Box size={16} />
                  <span className="text-sm">{t("new_classes_in_b")}</span>
                </div>
              </CardHeader>
              <CardTitle>
                <span className="text-purple-600 dark:text-purple-400">{comparison.newClasses.length}</span>
              </CardTitle>
              {comparison.newClasses.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {comparison.newClasses.map((cls) => (
                    <span key={cls} className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                      {cls}
                    </span>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <FunctionSquare size={16} />
                  <span className="text-sm">{t("new_functions_in_b")}</span>
                </div>
              </CardHeader>
              <CardTitle>
                <span className="text-amber-600 dark:text-amber-400">{comparison.newFunctions.length}</span>
              </CardTitle>
              {comparison.newFunctions.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {comparison.newFunctions.map((fn) => (
                    <span key={fn} className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                      {fn}
                    </span>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Tool comparison */}
          <Card>
            <CardHeader>
              <CardTitle>{t("tool_comparison")}</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div>
                <h4 className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  {t("only_in")} {metaA?.title || versionA}
                </h4>
                {comparison.toolsOnlyA.length === 0 ? (
                  <p className="text-xs text-zinc-400">{t("none")}</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {comparison.toolsOnlyA.map((tool) => (
                      <span key={tool} className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <h4 className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  {t("shared")}
                </h4>
                {comparison.toolsShared.length === 0 ? (
                  <p className="text-xs text-zinc-400">{t("none")}</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {comparison.toolsShared.map((tool) => (
                      <span key={tool} className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <h4 className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  {t("only_in")} {metaB?.title || versionB}
                </h4>
                {comparison.toolsOnlyB.length === 0 ? (
                  <p className="text-xs text-zinc-400">{t("none")}</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {comparison.toolsOnlyB.map((tool) => (
                      <span key={tool} className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-300">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Code Diff */}
          <div>
            <h2 className="mb-4 text-xl font-semibold">{t("source_diff")}</h2>
            <CodeDiff
              oldSource={infoA.source}
              newSource={infoB.source}
              oldLabel={`${infoA.id} (${infoA.filename})`}
              newLabel={`${infoB.id} (${infoB.filename})`}
            />
          </div>
        </div>
      )}

      {/* Empty state */}
      {(!versionA || !versionB) && (
        <div className="rounded-lg border border-dashed border-zinc-300 p-12 text-center dark:border-zinc-700">
          <p className="text-zinc-400">{t("empty_hint")}</p>
        </div>
      )}
    </div>
  );
}
