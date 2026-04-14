"use client";

import Link from "next/link";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LAYERS, VERSION_META } from "@/lib/constants";
import { getVersionContent } from "@/lib/version-content";
import { Card } from "@/components/ui/card";
import { LayerBadge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { VersionIndex } from "@/types/agent-data";
import versionData from "@/data/generated/versions.json";
import docsData from "@/data/generated/docs.json";
import { BRIDGE_DOCS } from "@/lib/bridge-docs";
import { getStageCheckpoint } from "@/lib/stage-checkpoints";

const data = versionData as VersionIndex;

const docs = docsData as Array<{
  slug?: string;
  locale?: string;
  kind?: string;
  title?: string;
}>;

const LAYER_BORDER_CLASSES: Record<string, string> = {
  core: "border-l-blue-500",
  hardening: "border-l-emerald-500",
  runtime: "border-l-amber-500",
  platform: "border-l-red-500",
};

const LAYER_HEADER_BG: Record<string, string> = {
  core: "bg-blue-500",
  hardening: "bg-emerald-500",
  runtime: "bg-amber-500",
  platform: "bg-red-500",
};

const LAYER_CHECKPOINT_SHELL: Record<string, string> = {
  core: "border-blue-200/80 bg-blue-50/80 dark:border-blue-900/60 dark:bg-blue-950/20",
  hardening:
    "border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-950/20",
  runtime: "border-amber-200/80 bg-amber-50/80 dark:border-amber-900/60 dark:bg-amber-950/20",
  platform: "border-red-200/80 bg-red-50/80 dark:border-red-900/60 dark:bg-red-950/20",
};

const RUNTIME_SUPPORT_DOCS = [
  "s13a-runtime-task-model",
  "data-structures",
  "entity-map",
] as const;

const CORE_SUPPORT_DOCS = [
  "s00-architecture-overview",
  "s00b-one-request-lifecycle",
  "s02a-tool-control-plane",
  "data-structures",
] as const;

const HARDENING_SUPPORT_DOCS = [
  "s00a-query-control-plane",
  "s02b-tool-execution-runtime",
  "s10a-message-prompt-pipeline",
  "s00c-query-transition-model",
  "data-structures",
] as const;

const PLATFORM_SUPPORT_DOCS = [
  "team-task-lane-model",
  "s13a-runtime-task-model",
  "s19a-mcp-capability-layers",
  "entity-map",
  "data-structures",
] as const;

type SupportDocCard = {
  slug: string;
  title: string;
  summary: string;
  fallbackLocale: typeof docs[number]["locale"] | null;
};

type SupportSection = {
  id: "core" | "hardening" | "runtime" | "platform";
  eyebrow: string;
  title: string;
  body: string;
  docs: SupportDocCard[];
};

function pickText(
  locale: string,
  value: { zh: string; en: string; ja: string }
) {
  if (locale === "zh") return value.zh;
  if (locale === "ja") return value.ja;
  return value.en;
}

const LAYER_CHECKPOINT_TEXT = {
  label: {
    zh: "阶段收口提醒",
    en: "Stage Stop Reminder",
    ja: "段階の収束ポイント",
  },
  body: {
    zh: "这一层不是读完最后一章就立刻往后冲。更稳的顺序是：先从入口重新走一遍，自己手搓到收口，再进入下一层。",
    en: "Do not sprint past the last chapter of this layer. The steadier order is: reopen the entry point, rebuild the layer by hand, then enter the next one.",
    ja: "この層の最後の章を読んだら、そのまま先へ走るのではありません。入口へ戻り、この層を自分で作り直してから次へ進む方が安定します。",
  },
  rebuild: {
    zh: "这一层现在应该能自己做出的东西",
    en: "What You Should Now Be Able To Rebuild",
    ja: "この層で今なら自分で作り直せるべきもの",
  },
  entry: {
    zh: "阶段入口",
    en: "Stage Entry",
    ja: "段階の入口",
  },
  exit: {
    zh: "阶段收口",
    en: "Stage Exit",
    ja: "段階の収束章",
  },
} as const;

export default function LayersPage() {
  const t = useTranslations("layers");
  const tSession = useTranslations("sessions");
  const tLayer = useTranslations("layer_labels");
  const locale = useLocale();
  const resolveSupportDocs = (slugs: readonly string[]) =>
    slugs
      .map((slug) => {
        const descriptor = BRIDGE_DOCS[slug];
        if (!descriptor) return null;

        const doc =
          docs.find(
            (item) =>
              item.slug === slug &&
              item.kind === "bridge" &&
              item.locale === locale
          ) ??
          docs.find(
            (item) =>
              item.slug === slug &&
              item.kind === "bridge" &&
              item.locale === "zh"
          ) ??
          docs.find(
            (item) =>
              item.slug === slug &&
              item.kind === "bridge" &&
              item.locale === "en"
          );

        if (!doc?.slug) return null;

        return {
          slug: doc.slug,
          title: pickText(locale, descriptor.title),
          summary: pickText(locale, descriptor.summary),
          fallbackLocale: doc.locale !== locale ? doc.locale : null,
        } satisfies SupportDocCard;
      })
      .filter((item): item is SupportDocCard => Boolean(item));

  const coreSupportDocs = resolveSupportDocs(CORE_SUPPORT_DOCS);
  const hardeningSupportDocs = resolveSupportDocs(HARDENING_SUPPORT_DOCS);
  const runtimeSupportDocs = resolveSupportDocs(RUNTIME_SUPPORT_DOCS);
  const platformSupportDocs = resolveSupportDocs(PLATFORM_SUPPORT_DOCS);
  const supportSections = [
    {
      id: "core",
      eyebrow: pickText(locale, {
        zh: "核心闭环补课",
        en: "Core Loop Support Docs",
        ja: "基礎ループ補助資料",
      }),
      title: pickText(locale, {
        zh: "读 `s01-s06` 时，先把主闭环、工具入口和数据结构边界守住",
        en: "Before reading `s01-s06`, hold the main loop, tool entry path, and data-structure boundaries steady",
        ja: "`s01-s06` を読む前に、主ループ・tool 入口・データ構造境界を先に安定させる",
      }),
      body: pickText(locale, {
        zh: "前六章最容易被低估的，不是某个功能点，而是这条最小闭环到底怎样成立：用户输入怎么进入、工具结果怎么回写、状态容器到底有哪些。",
        en: "The first six chapters are not mainly about isolated features. They are about how the minimal loop truly forms: how user input enters, how tool results write back, and which state containers exist.",
        ja: "最初の6章で大事なのは個別機能ではなく、最小ループがどう成立するかです。ユーザー入力がどう入り、ツール結果がどう戻り、どんな状態容器があるかを先に押さえます。",
      }),
      docs: coreSupportDocs,
    },
    {
      id: "hardening",
      eyebrow: pickText(locale, {
        zh: "系统加固补课",
        en: "Hardening Support Docs",
        ja: "強化段階補助資料",
      }),
      title: pickText(locale, {
        zh: "读 `s07-s11` 时，先把控制面、输入装配和续行原因这几层拆开",
        en: "Before reading `s07-s11`, separate the control plane, input assembly, and continuation reasons",
        ja: "`s07-s11` を読む前に、制御面・入力組み立て・継続理由を分けておく",
      }),
      body: pickText(locale, {
        zh: "加固阶段最容易混的，不是权限、hook、memory 哪个更复杂，而是这些机制都在“控制系统如何继续推进”这一层相遇了。",
        en: "The hardening stage gets confusing not because one feature is harder than another, but because permissions, hooks, memory, prompts, and recovery all meet at the control plane.",
        ja: "強化段階で混ざりやすいのは個別機能の難しさではなく、権限・hook・memory・prompt・recovery がすべて制御面で交わる点です。",
      }),
      docs: hardeningSupportDocs,
    },
    {
      id: "runtime",
      eyebrow: pickText(locale, {
        zh: "运行时补课",
        en: "Runtime Support Docs",
        ja: "実行段階補助資料",
      }),
      title: pickText(locale, {
        zh: "读 `s12-s14` 时，先把目标、执行槽位和定时触发这三层分清",
        en: "Before reading `s12-s14`, separate goals, execution slots, and schedule triggers",
        ja: "`s12-s14` を読む前に、goal・execution slot・schedule trigger を分けておく",
      }),
      body: pickText(locale, {
        zh: "任务运行时最容易让人混的，不是某个函数，而是 task、runtime task、notification、schedule 这几层对象同时出现时，各自到底管什么。",
        en: "The runtime chapters get confusing not because of one function, but because task goals, runtime tasks, notifications, and schedules begin to coexist and need clean boundaries.",
        ja: "実行段階で難しくなるのは個別関数ではなく、作業目標・実行タスク・通知・スケジュールが同時に現れ、それぞれの境界を保つ必要がある点です。",
      }),
      docs: runtimeSupportDocs,
    },
    {
      id: "platform",
      eyebrow: pickText(locale, {
        zh: "平台层补课",
        en: "Platform Support Docs",
        ja: "プラットフォーム補助資料",
      }),
      title: pickText(locale, {
        zh: "读 `s15-s19` 之前，先把这几份桥接资料放在手边",
        en: "Keep these bridge docs nearby before reading `s15-s19`",
        ja: "`s15-s19` を読む前に、まずこの橋渡し資料を手元に置く",
      }),
      body: pickText(locale, {
        zh: "后五章最容易混的是队友、协议请求、任务、运行时槽位、worktree 车道，以及最后接进来的外部能力层。这几份文档就是专门用来反复校正这段心智模型的。",
        en: "The last five chapters are where teammates, protocol requests, tasks, runtime slots, worktree lanes, and finally external capability layers start to blur together. These bridge docs are meant to keep that model clean.",
        ja: "最後の5章では、チームメイト・プロトコル要求・タスク・実行スロット・worktree レーン、そして最後に入ってくる外部能力層の境界が混ざりやすくなります。ここに並べた資料は、その学習モデルを何度でも補正するためのものです。",
      }),
      docs: platformSupportDocs,
    },
  ] satisfies SupportSection[];

  const visibleSupportSections = supportSections.filter(
    (section) => section.docs.length > 0
  );

  return (
    <div className="py-4">
      <div className="mb-10">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">{t("subtitle")}</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="border-zinc-200/80 bg-zinc-50/70 dark:border-zinc-800/80 dark:bg-zinc-900/60">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">{t("guide_label")}</p>
          <h2 className="mt-3 text-base font-semibold">{t("guide_start_title")}</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            {t("guide_start_desc")}
          </p>
        </Card>
        <Card className="border-zinc-200/80 bg-zinc-50/70 dark:border-zinc-800/80 dark:bg-zinc-900/60">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">{t("guide_label")}</p>
          <h2 className="mt-3 text-base font-semibold">{t("guide_middle_title")}</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            {t("guide_middle_desc")}
          </p>
        </Card>
        <Card className="border-zinc-200/80 bg-zinc-50/70 dark:border-zinc-800/80 dark:bg-zinc-900/60">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">{t("guide_label")}</p>
          <h2 className="mt-3 text-base font-semibold">{t("guide_finish_title")}</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            {t("guide_finish_desc")}
          </p>
        </Card>
      </div>

      {visibleSupportSections.map((section) => (
        <section
          key={section.id}
          className="mb-10 rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] p-5 shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))] sm:p-6"
        >
          <div className="max-w-2xl">
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {section.eyebrow}
            </p>
            <h2 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {section.title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {section.body}
            </p>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            {section.docs.map((doc) => (
              <Link key={doc.slug} href={`/${locale}/docs/${doc.slug}`} className="group">
                <Card className="h-full border-zinc-200/80 bg-white/90 transition-colors hover:border-zinc-300 dark:border-zinc-800/80 dark:bg-zinc-950/80 dark:hover:border-zinc-700">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">
                        {doc.title}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                        {doc.summary}
                      </p>
                    </div>
                    <ChevronRight
                      size={16}
                      className="mt-1 shrink-0 text-zinc-300 transition-colors group-hover:text-zinc-600 dark:text-zinc-600 dark:group-hover:text-zinc-300"
                    />
                  </div>
                  {doc.fallbackLocale && (
                    <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
                      {pickText(locale, {
                        zh: `当前语言缺稿，自动回退到 ${doc.fallbackLocale}`,
                        en: `Missing in this locale, falling back to ${doc.fallbackLocale}`,
                        ja: `この言語では未整備のため ${doc.fallbackLocale} へフォールバック`,
                      })}
                    </p>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        </section>
      ))}

      <div className="space-y-6">
        {LAYERS.map((layer, index) => {
          const versionInfos = layer.versions.map((vId) => {
            const info = data.versions.find((v) => v.id === vId);
            const meta = VERSION_META[vId];
            const content = getVersionContent(vId, locale);
            return { id: vId, info, meta, content };
          });
          const checkpoint = getStageCheckpoint(layer.id);

          return (
            <div
              key={layer.id}
              className={cn(
                "overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800",
                "border-l-4",
                LAYER_BORDER_CLASSES[layer.id]
              )}
            >
              {/* Layer header */}
              <div className="flex items-center gap-3 px-6 py-4">
                <div className={cn("h-3 w-3 rounded-full", LAYER_HEADER_BG[layer.id])} />
                <div>
                  <h2 className="text-xl font-bold">
                    <span className="text-zinc-400 dark:text-zinc-600">P{index + 1}</span>
                    {" "}
                    {tLayer(layer.id)}
                  </h2>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                    {t(layer.id)}
                  </p>
                  <p className="mt-2 text-sm font-medium text-zinc-700 dark:text-zinc-200">
                    {t(`${layer.id}_outcome`)}
                  </p>
                </div>
              </div>

              {/* Version cards within this layer */}
              <div className="border-t border-zinc-200 bg-zinc-50/50 px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900/50">
                {checkpoint && (
                  <div
                    className={cn(
                      "mb-4 rounded-2xl border p-4",
                      LAYER_CHECKPOINT_SHELL[layer.id]
                    )}
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="max-w-2xl">
                        <p className="text-xs uppercase tracking-[0.22em] text-zinc-500 dark:text-zinc-400">
                          {pickText(locale, LAYER_CHECKPOINT_TEXT.label)}
                        </p>
                        <h3 className="mt-2 text-base font-semibold text-zinc-950 dark:text-zinc-50">
                          {pickText(locale, checkpoint.title)}
                        </h3>
                        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                          {pickText(locale, LAYER_CHECKPOINT_TEXT.body)}
                        </p>
                      </div>

                      <div className="grid gap-2 text-sm sm:grid-cols-2 lg:min-w-[240px] lg:grid-cols-1">
                        <Link
                          href={`/${locale}/${checkpoint.entryVersion}`}
                          className="rounded-xl border border-white/70 bg-white/80 px-3 py-2 text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-900/60 dark:bg-zinc-950/60 dark:text-zinc-200 dark:hover:border-zinc-700 dark:hover:text-white"
                        >
                          <span className="block text-xs uppercase tracking-[0.18em] text-zinc-400">
                            {pickText(locale, LAYER_CHECKPOINT_TEXT.entry)}
                          </span>
                          <span className="mt-1 block font-mono">{checkpoint.entryVersion}</span>
                        </Link>
                        <Link
                          href={`/${locale}/${checkpoint.endVersion}`}
                          className="rounded-xl border border-white/70 bg-white/80 px-3 py-2 text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-900/60 dark:bg-zinc-950/60 dark:text-zinc-200 dark:hover:border-zinc-700 dark:hover:text-white"
                        >
                          <span className="block text-xs uppercase tracking-[0.18em] text-zinc-400">
                            {pickText(locale, LAYER_CHECKPOINT_TEXT.exit)}
                          </span>
                          <span className="mt-1 block font-mono">{checkpoint.endVersion}</span>
                        </Link>
                      </div>
                    </div>

                    <div className="mt-4 rounded-xl border border-white/70 bg-white/70 p-4 dark:border-zinc-900/60 dark:bg-zinc-950/50">
                      <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                        {pickText(locale, LAYER_CHECKPOINT_TEXT.rebuild)}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                        {pickText(locale, checkpoint.rebuild)}
                      </p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {versionInfos.map(({ id, info, meta, content }) => (
                    <Link key={id} href={`/${locale}/${id}`} className="group">
                      <Card className="transition-shadow hover:shadow-md">
                        <div className="flex items-start justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-zinc-400">{id}</span>
                              <LayerBadge layer={layer.id}>{tLayer(layer.id)}</LayerBadge>
                            </div>
                            <h3 className="mt-1 font-semibold text-zinc-900 dark:text-zinc-100">
                              {tSession(id) || meta?.title || id}
                            </h3>
                            {meta && (
                              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                                {content.subtitle}
                              </p>
                            )}
                          </div>
                          <ChevronRight
                            size={16}
                            className="mt-1 shrink-0 text-zinc-300 transition-colors group-hover:text-zinc-600 dark:text-zinc-600 dark:group-hover:text-zinc-300"
                          />
                        </div>
                        <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                          <span>{info?.loc ?? "?"} LOC</span>
                          <span>{info?.tools.length ?? "?"} tools</span>
                        </div>
                        {meta && (
                          <p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400 line-clamp-2">
                            {content.keyInsight}
                          </p>
                        )}
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Composition indicator */}
              {index < LAYERS.length - 1 && (
                <div className="flex items-center justify-center py-1 text-zinc-300 dark:text-zinc-700">
                  <svg width="20" height="12" viewBox="0 0 20 12" fill="none" className="text-current">
                    <path d="M10 0 L10 12 M5 7 L10 12 L15 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
