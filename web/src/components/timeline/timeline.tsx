"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import versionsData from "@/data/generated/versions.json";

const LAYER_DOT_BG: Record<string, string> = {
  tools: "bg-blue-500",
  planning: "bg-emerald-500",
  memory: "bg-purple-500",
  concurrency: "bg-amber-500",
  collaboration: "bg-red-500",
};

const LAYER_LINE_BG: Record<string, string> = {
  tools: "bg-blue-500/30",
  planning: "bg-emerald-500/30",
  memory: "bg-purple-500/30",
  concurrency: "bg-amber-500/30",
  collaboration: "bg-red-500/30",
};

const LAYER_BAR_BG: Record<string, string> = {
  tools: "bg-blue-500",
  planning: "bg-emerald-500",
  memory: "bg-purple-500",
  concurrency: "bg-amber-500",
  collaboration: "bg-red-500",
};

function getVersionData(id: string) {
  return versionsData.versions.find((v) => v.id === id);
}

const MAX_LOC = Math.max(
  ...versionsData.versions
    .filter((v) => LEARNING_PATH.includes(v.id as (typeof LEARNING_PATH)[number]))
    .map((v) => v.loc)
);

export function Timeline() {
  const t = useTranslations("timeline");
  const tv = useTranslations("version");
  const locale = useLocale();

  return (
    <div className="flex flex-col gap-12">
      {/* Layer Legend */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-[var(--color-text-secondary)]">
          {t("layer_legend")}
        </h3>
        <div className="flex flex-wrap gap-2">
          {LAYERS.map((layer) => (
            <div key={layer.id} className="flex items-center gap-1.5">
              <span
                className={cn("h-3 w-3 rounded-full", LAYER_DOT_BG[layer.id])}
              />
              <span className="text-xs font-medium">{layer.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Vertical Timeline */}
      <div className="relative">
        {LEARNING_PATH.map((versionId, index) => {
          const meta = VERSION_META[versionId];
          const data = getVersionData(versionId);
          if (!meta || !data) return null;

          const isLast = index === LEARNING_PATH.length - 1;
          const locPercent = Math.round((data.loc / MAX_LOC) * 100);

          return (
            <div key={versionId} className="relative flex gap-4 pb-8 sm:gap-6">
              {/* Timeline line + dot */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-4 ring-[var(--color-bg)] sm:h-10 sm:w-10",
                    LAYER_DOT_BG[meta.layer]
                  )}
                >
                  <span className="text-[10px] font-bold text-white sm:text-xs">
                    {versionId.replace("s", "").replace("_mini", "m")}
                  </span>
                </div>
                {!isLast && (
                  <div
                    className={cn(
                      "w-0.5 flex-1",
                      LAYER_LINE_BG[
                        VERSION_META[LEARNING_PATH[index + 1]]?.layer || meta.layer
                      ]
                    )}
                  />
                )}
              </div>

              {/* Content card */}
              <div className="flex-1 pb-2">
                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ duration: 0.4, delay: 0.1 }}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4 transition-colors hover:border-[var(--color-text-secondary)]/30 sm:p-5"
                >
                  <div className="flex flex-wrap items-start gap-2">
                    <LayerBadge layer={meta.layer}>{versionId}</LayerBadge>
                    <span className="text-xs text-[var(--color-text-secondary)]">
                      {meta.coreAddition}
                    </span>
                  </div>

                  <h3 className="mt-2 text-base font-semibold sm:text-lg">
                    {meta.title}
                    <span className="ml-2 text-sm font-normal text-[var(--color-text-secondary)]">
                      {meta.subtitle}
                    </span>
                  </h3>

                  {/* Stats row */}
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-[var(--color-text-secondary)]">
                    <span className="tabular-nums">
                      {data.loc} {tv("loc")}
                    </span>
                    <span className="tabular-nums">
                      {data.tools.length} {tv("tools")}
                    </span>
                  </div>

                  {/* LOC bar */}
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        LAYER_BAR_BG[meta.layer]
                      )}
                      style={{ width: `${locPercent}%` }}
                    />
                  </div>

                  {/* Key insight */}
                  {meta.keyInsight && (
                    <p className="mt-3 text-sm italic text-[var(--color-text-secondary)]">
                      &ldquo;{meta.keyInsight}&rdquo;
                    </p>
                  )}

                  {/* Link */}
                  <Link
                    href={`/${locale}/${versionId}`}
                    className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                  >
                    {t("learn_more")}
                    <span aria-hidden="true">&rarr;</span>
                  </Link>
                </motion.div>
              </div>
            </div>
          );
        })}
      </div>

      {/* LOC Growth Chart */}
      <div>
        <h3 className="mb-4 text-lg font-semibold">{t("loc_growth")}</h3>
        <div className="flex flex-col gap-2">
          {LEARNING_PATH.map((versionId) => {
            const meta = VERSION_META[versionId];
            const data = getVersionData(versionId);
            if (!meta || !data) return null;

            const widthPercent = Math.max(
              2,
              Math.round((data.loc / MAX_LOC) * 100)
            );

            return (
              <div key={versionId} className="flex items-center gap-3">
                <span className="w-8 shrink-0 text-right text-xs font-medium tabular-nums">
                  {versionId}
                </span>
                <div className="flex-1">
                  <div className="h-5 w-full overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${widthPercent}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6, delay: 0.05 * LEARNING_PATH.indexOf(versionId) }}
                      className={cn(
                        "flex h-full items-center rounded px-2",
                        LAYER_BAR_BG[meta.layer]
                      )}
                    >
                      <span className="text-[10px] font-medium text-white">
                        {data.loc}
                      </span>
                    </motion.div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
