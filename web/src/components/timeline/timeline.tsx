"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { getVersionContent } from "@/lib/version-content";
import { LayerBadge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import versionsData from "@/data/generated/versions.json";

const LAYER_DOT_BG: Record<string, string> = {
  core: "bg-blue-500",
  hardening: "bg-emerald-500",
  runtime: "bg-amber-500",
  platform: "bg-red-500",
};

const LAYER_LINE_BG: Record<string, string> = {
  core: "bg-blue-500/30",
  hardening: "bg-emerald-500/30",
  runtime: "bg-amber-500/30",
  platform: "bg-red-500/30",
};

const LAYER_BAR_BG: Record<string, string> = {
  core: "bg-blue-500",
  hardening: "bg-emerald-500",
  runtime: "bg-amber-500",
  platform: "bg-red-500",
};

const LAYER_HEADER_BG = LAYER_BAR_BG;

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
  const tSession = useTranslations("sessions");
  const tLayer = useTranslations("layer_labels");
  const tLayersPage = useTranslations("layers");
  const locale = useLocale();

  return (
    <div className="flex flex-col gap-12 overflow-x-hidden">
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
              <span className="text-xs font-medium">{tLayer(layer.id)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Vertical Timeline */}
      <div className="relative">
        {LEARNING_PATH.map((versionId, index) => {
          const meta = VERSION_META[versionId];
          const data = getVersionData(versionId);
          const content = getVersionContent(versionId, locale);
          if (!meta || !data) return null;

          const isLast = index === LEARNING_PATH.length - 1;
          const locPercent = Math.round((data.loc / MAX_LOC) * 100);
          const previousVersion = index > 0 ? LEARNING_PATH[index - 1] : null;
          const previousLayer = previousVersion ? VERSION_META[previousVersion]?.layer : null;
          const isLayerStart = previousLayer !== meta.layer;
          const layerMeta = LAYERS.find((layer) => layer.id === meta.layer);
          const layerRange =
            layerMeta && layerMeta.versions.length > 0
              ? `${layerMeta.versions[0]}-${layerMeta.versions[layerMeta.versions.length - 1]}`
              : versionId;

          return (
            <div key={versionId} className="space-y-4">
              {isLayerStart && layerMeta && (
                <motion.section
                  initial={{ opacity: 0, y: 18 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.32 }}
                  className="rounded-[24px] border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.9))] p-5 shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <LayerBadge layer={meta.layer}>{tLayer(meta.layer)}</LayerBadge>
                        <span className="text-xs uppercase tracking-[0.2em] text-zinc-400">
                          {layerRange}
                        </span>
                      </div>
                      <h3 className="mt-3 text-lg font-semibold text-zinc-950 dark:text-zinc-50">
                        {tLayersPage(meta.layer)}
                      </h3>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                        {tLayersPage(`${meta.layer}_outcome`)}
                      </p>
                    </div>
                    <div
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white",
                        LAYER_HEADER_BG[meta.layer]
                      )}
                    >
                      {t("layer_legend")}
                    </div>
                  </div>
                </motion.section>
              )}

              <div className="relative flex gap-4 pb-8 sm:gap-6">
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
                <div className="min-w-0 flex-1 pb-2">
                  <motion.div
                    initial={{ opacity: 0, x: 30 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: "-50px" }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                    className="w-full min-w-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4 transition-colors hover:border-[var(--color-text-secondary)]/30 sm:p-5"
                  >
                    <div className="flex min-w-0 flex-wrap items-start gap-2">
                      <LayerBadge layer={meta.layer}>{versionId}</LayerBadge>
                      <span className="min-w-0 break-words text-xs text-[var(--color-text-secondary)]">
                        {content.coreAddition}
                      </span>
                    </div>

                    <h3 className="mt-2 break-words text-base font-semibold sm:text-lg">
                      {tSession(versionId) || meta.title}
                      <span className="ml-2 break-words text-sm font-normal text-[var(--color-text-secondary)]">
                        {content.subtitle}
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
                    {content.keyInsight && (
                      <p className="mt-3 text-sm italic text-[var(--color-text-secondary)]">
                        &ldquo;{content.keyInsight}&rdquo;
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
