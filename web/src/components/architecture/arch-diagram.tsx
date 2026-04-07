"use client";

import { motion } from "framer-motion";
import { useLocale } from "@/lib/i18n";
import { VERSION_META } from "@/lib/constants";
import {
  pickDiagramText,
  translateArchitectureText,
} from "@/lib/diagram-localization";
import { getVersionContent } from "@/lib/version-content";
import {
  ARCHITECTURE_BLUEPRINTS,
  type ArchitectureSliceId,
} from "@/data/architecture-blueprints";
import { cn } from "@/lib/utils";

interface ArchDiagramProps {
  version: string;
}

const SLICE_STYLE: Record<
  ArchitectureSliceId,
  {
    ring: string;
    badge: string;
    surface: string;
    title: { zh: string; en: string; ja?: string };
    note: { zh: string; en: string; ja?: string };
  }
> = {
  mainline: {
    ring: "ring-blue-500/20",
    badge:
      "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-300",
    surface:
      "from-blue-500/12 via-blue-500/5 to-transparent dark:from-blue-500/10 dark:via-transparent",
    title: { zh: "主线执行", en: "Mainline", ja: "主線実行" },
    note: {
      zh: "真正把系统往前推的那条执行主线。",
      en: "The path that actually pushes the system forward.",
      ja: "実際にシステムを前へ進める主線です。",
    },
  },
  control: {
    ring: "ring-emerald-500/20",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300",
    surface:
      "from-emerald-500/12 via-emerald-500/5 to-transparent dark:from-emerald-500/10 dark:via-transparent",
    title: { zh: "控制面", en: "Control Plane", ja: "制御面" },
    note: {
      zh: "决定怎么运行、何时放行、何时转向。",
      en: "Decides how execution is controlled, gated, and redirected.",
      ja: "どう動かし、いつ通し、いつ向きを変えるかを決めます。",
    },
  },
  state: {
    ring: "ring-amber-500/20",
    badge:
      "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-300",
    surface:
      "from-amber-500/12 via-amber-500/5 to-transparent dark:from-amber-500/10 dark:via-transparent",
    title: { zh: "状态容器", en: "State Records", ja: "状態レコード" },
    note: {
      zh: "真正需要被系统记住和回写的结构。",
      en: "The structures the system must remember and write back.",
      ja: "システムが記憶し、回写すべき構造です。",
    },
  },
  lanes: {
    ring: "ring-rose-500/20",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300",
    surface:
      "from-rose-500/12 via-rose-500/5 to-transparent dark:from-rose-500/10 dark:via-transparent",
    title: { zh: "并行 / 外部车道", en: "Lanes / External", ja: "並行 / 外部レーン" },
    note: {
      zh: "长期队友、后台槽位或外部能力的进入面。",
      en: "Where long-lived workers, background slots, or external capability enter.",
      ja: "長期ワーカー、バックグラウンドスロット、外部能力が入ってくる面です。",
    },
  },
};

const UI_TEXT = {
  summaryTitle: {
    zh: "这章在系统里真正新增了什么",
    en: "What This Chapter Actually Adds",
    ja: "この章でシステムに何が増えたか",
  },
  recordsTitle: {
    zh: "关键记录结构",
    en: "Key Records",
    ja: "主要レコード",
  },
  recordsNote: {
    zh: "这些不是实现细枝末节，而是开发者自己重建系统时最应该抓住的状态容器。",
    en: "These are the state containers worth holding onto when you rebuild the system yourself.",
    ja: "これらは実装の枝葉ではなく、自分で再構築するときに掴むべき状態容器です。",
  },
  handoffTitle: {
    zh: "主回流路径",
    en: "Primary Handoff Path",
    ja: "主回流経路",
  },
  fresh: {
    zh: "新增",
    en: "NEW",
    ja: "新規",
  },
};

export function ArchDiagram({ version }: ArchDiagramProps) {
  const locale = useLocale();
  const blueprint =
    ARCHITECTURE_BLUEPRINTS[version as keyof typeof ARCHITECTURE_BLUEPRINTS];
  const meta = VERSION_META[version];
  const content = getVersionContent(version, locale);

  if (!blueprint || !meta) return null;

  const sliceOrder: ArchitectureSliceId[] = [
    "mainline",
    "control",
    "state",
    "lanes",
  ];
  const visibleSlices = sliceOrder.filter(
    (sliceId) => (blueprint.slices[sliceId] ?? []).length > 0
  );

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[30px] border border-zinc-200/80 bg-white/95 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/90">
        <div className="relative overflow-hidden px-5 py-6 sm:px-6">
          <div className="absolute inset-x-0 top-0 h-28 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.16),transparent_45%),radial-gradient(circle_at_top_right,rgba(59,130,246,0.14),transparent_38%)] dark:bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.16),transparent_45%),radial-gradient(circle_at_top_right,rgba(96,165,250,0.14),transparent_38%)]" />
          <div className="relative">
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {pickDiagramText(locale, UI_TEXT.summaryTitle)}
            </p>
            <h3 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {content.coreAddition}
            </h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-600 dark:text-zinc-300">
              {translateArchitectureText(
                locale,
                pickDiagramText(locale, blueprint.summary)
              )}
            </p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {visibleSlices.map((sliceId, sliceIndex) => {
          const slice = blueprint.slices[sliceId] ?? [];
          const style = SLICE_STYLE[sliceId];

          return (
            <motion.section
              key={sliceId}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: sliceIndex * 0.06, duration: 0.32 }}
              className={cn(
                "overflow-hidden rounded-[28px] border border-zinc-200/80 bg-white/95 shadow-sm ring-1 dark:border-zinc-800/80 dark:bg-zinc-950/90",
                style.ring
              )}
            >
              <div className={cn("bg-gradient-to-br px-5 py-5 sm:px-6", style.surface)}>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-[11px] font-medium",
                      style.badge
                    )}
                  >
                    {pickDiagramText(locale, style.title)}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {pickDiagramText(locale, style.note)}
                </p>
              </div>
              <div className="space-y-3 px-5 py-5 sm:px-6">
                {slice.map((item, itemIndex) => (
                  <motion.div
                    key={`${sliceId}-${itemIndex}-${translateArchitectureText(locale, pickDiagramText(locale, item.name))}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: sliceIndex * 0.06 + itemIndex * 0.04, duration: 0.24 }}
                    className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70"
                  >
                    <div className="flex flex-wrap items-start gap-2">
                      <h4 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                        {translateArchitectureText(
                          locale,
                          pickDiagramText(locale, item.name)
                        )}
                      </h4>
                      {item.fresh && (
                        <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[10px] font-bold uppercase text-white dark:bg-zinc-100 dark:text-zinc-900">
                          {pickDiagramText(locale, UI_TEXT.fresh)}
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                      {translateArchitectureText(
                        locale,
                        pickDiagramText(locale, item.detail)
                      )}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          );
        })}
      </section>

      <section className="rounded-[30px] border border-zinc-200/80 bg-white/95 px-5 py-6 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/90 sm:px-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-xl space-y-2">
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {pickDiagramText(locale, UI_TEXT.recordsTitle)}
            </p>
            <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {pickDiagramText(locale, UI_TEXT.recordsNote)}
            </p>
          </div>
          <div className="grid flex-1 grid-cols-1 gap-3 md:grid-cols-2">
            {blueprint.records.map((record, index) => (
              <motion.div
                key={`${translateArchitectureText(locale, pickDiagramText(locale, record.name))}-${index}`}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05, duration: 0.24 }}
                className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/70"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                    {translateArchitectureText(
                      locale,
                      pickDiagramText(locale, record.name)
                    )}
                  </span>
                  {record.fresh && (
                    <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[10px] font-bold uppercase text-zinc-700 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300">
                      {pickDiagramText(locale, UI_TEXT.fresh)}
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {translateArchitectureText(
                    locale,
                    pickDiagramText(locale, record.detail)
                  )}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-[30px] border border-zinc-200/80 bg-white/95 px-5 py-6 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/90 sm:px-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
          {pickDiagramText(locale, UI_TEXT.handoffTitle)}
        </p>
        <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
          {blueprint.handoff.map((step, index) => (
            <motion.div
              key={`${translateArchitectureText(locale, pickDiagramText(locale, step))}-${index}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.06, duration: 0.26 }}
              className="rounded-2xl border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.9))] p-4 dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]"
            >
              <div className="flex items-start gap-3">
                <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-xs font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
                  {index + 1}
                </span>
                <p className="text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                  {translateArchitectureText(
                    locale,
                    pickDiagramText(locale, step)
                  )}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
