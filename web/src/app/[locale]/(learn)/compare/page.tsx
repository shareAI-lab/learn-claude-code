"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "@/lib/i18n";
import { LEARNING_PATH } from "@/lib/constants";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { LayerBadge } from "@/components/ui/badge";
import { CodeDiff } from "@/components/diff/code-diff";
import { ArchDiagram } from "@/components/architecture/arch-diagram";
import { ExecutionFlow } from "@/components/architecture/execution-flow";
import { ArrowRight, FileCode, Layers3, Lightbulb, Sparkles, Wrench } from "lucide-react";
import type { DocContent, VersionIndex } from "@/types/agent-data";
import versionData from "@/data/generated/versions.json";
import docsData from "@/data/generated/docs.json";
import { getBridgeDocDescriptors } from "@/lib/bridge-docs";
import { getChapterGuide } from "@/lib/chapter-guides";

const data = versionData as VersionIndex;
const docs = docsData as DocContent[];
type RecommendedBridgeDoc = {
  slug: string;
  title: string;
  summary: string;
  fallbackLocale: DocContent["locale"] | null;
};

function extractLead(content?: string) {
  if (!content) return "";
  const match = content.match(/> \*([^*]+)\*/);
  if (!match) return "";
  return match[1].replace(/^"+|"+$/g, "").trim();
}

function pickText(
  locale: string,
  value: { zh: string; en: string; ja: string }
) {
  if (locale === "zh") return value.zh;
  if (locale === "ja") return value.ja;
  return value.en;
}

const COMPARE_EXTRA_TEXT = {
  goal: {
    zh: "学完 B 后",
    en: "After B",
    ja: "B を読み終えた後の到達点",
  },
  emptyGoal: {
    zh: "该章节的学习目标暂未整理。",
    en: "The learning goal for this chapter has not been filled in yet.",
    ja: "この章の学習目標はまだ整理されていません。",
  },
  diagnosisLabel: {
    zh: "跃迁诊断",
    en: "Jump Diagnosis",
    ja: "ジャンプ診断",
  },
  nextBestLabel: {
    zh: "更稳的读法",
    en: "Safer Reading Move",
    ja: "より安定した読み方",
  },
  adjacentTitle: {
    zh: "这是最稳的一步升级",
    en: "This is the safest upgrade step",
    ja: "これは最も安定した1段階の比較です",
  },
  adjacentBody: {
    zh: "A 和 B 相邻，最适合看“系统刚刚多了一条什么分支、一个什么状态容器、为什么现在引入它”。",
    en: "A and B are adjacent, so this is the cleanest way to see the exact new branch, state container, and reason for introducing it now.",
    ja: "A と B は隣接しているため、何が新しい分岐で、何が新しい状態容器で、なぜ今入るのかを最も素直に見られます。",
  },
  adjacentNext: {
    zh: "先看执行流，再看架构图，最后再决定要不要往下看源码 diff。",
    en: "Read the execution flow first, then the architecture view, and only then decide whether you need the source diff.",
    ja: "まず実行フロー、その後アーキテクチャ図を見て、最後に必要ならソース diff へ進みます。",
  },
  sameLayerTitle: {
    zh: "这是同阶段内的跳读",
    en: "This is a same-stage skip",
    ja: "これは同一段階内の飛び読みです",
  },
  sameLayerBody: {
    zh: "你仍然在同一个能力阶段里，但中间被跳过的章节往往刚好承担了“把概念拆开”的工作，所以阅读风险已经明显高于相邻章节对比。",
    en: "You are still inside one stage, but the skipped chapters often carry the conceptual separation work, so the reading risk is already much higher than an adjacent comparison.",
    ja: "同じ段階内ではありますが、飛ばした章が概念分離を担っていることが多く、隣接比較より理解リスクはかなり高くなります。",
  },
  sameLayerNext: {
    zh: "如果开始读混，先回看 B 的前一章，再回桥接资料，而不是直接硬啃源码差异。",
    en: "If things start to blur, revisit the chapter right before B and then the bridge docs before forcing the source diff.",
    ja: "混ざり始めたら、まず B の直前の章と bridge doc に戻ってからソース diff を見ます。",
  },
  crossLayerTitle: {
    zh: "这是一次跨阶段跃迁",
    en: "This is a cross-stage jump",
    ja: "これは段階をまたぐジャンプです",
  },
  crossLayerBody: {
    zh: "跨阶段对比最大的风险，不是“功能更多了”，而是系统边界已经重画了。你需要先确认自己稳住了前一个阶段的目标，再去看 B。",
    en: "The main risk in a cross-stage jump is not more features. It is that the system boundary has been redrawn. Make sure you actually hold the previous stage before reading B.",
    ja: "段階またぎの最大リスクは機能量ではなく、システム境界そのものが描き直されていることです。B を読む前に前段階を本当に保持している必要があります。",
  },
  crossLayerNext: {
    zh: "先补桥接文档，再用时间线确认阶段切换理由；如果还虚，就先比较 `B` 的前一章和 `B` 本章。",
    en: "Start with the bridge docs, then use the timeline to confirm why the stage boundary changes here. If it still feels shaky, compare the chapter right before B with B first.",
    ja: "先に bridge doc を見て、その後 timeline でなぜここで段階が切り替わるのかを確認します。まだ不安なら、まず B の直前章と B を比較します。",
  },
  bridgeNudge: {
    zh: "这次跳跃前最值得先补的桥接资料",
    en: "Bridge docs most worth reading before this jump",
    ja: "このジャンプ前に最も先に補いたい bridge doc",
  },
  quickLabel: {
    zh: "一键对比入口",
    en: "One-Click Compare",
    ja: "ワンクリック比較",
  },
  quickTitle: {
    zh: "先用这些最稳的比较入口，不必每次手选两章",
    en: "Start with these safe comparison moves instead of selecting two chapters every time",
    ja: "毎回2章を手で選ぶ前に、まず安定した比較入口を使う",
  },
  quickBody: {
    zh: "这些按钮优先覆盖最值得反复看的相邻升级和阶段切换，适合第一次理解章节边界，也适合读到一半开始混时快速重启。",
    en: "These presets cover the most useful adjacent upgrades and stage boundaries. They work both for a first pass and for resetting when chapter boundaries start to blur.",
    ja: "ここには最も見返す価値の高い隣接アップグレードと段階切り替えを置いてあります。初回読みにも、途中で境界が混ざった時の立て直しにも向いています。",
  },
  quickPrevious: {
    zh: "直接改成 B 的前一章 -> B",
    en: "Use B's Previous Chapter -> B",
    ja: "B の直前章と B を比べる",
  },
  quickPreviousBody: {
    zh: "如果现在这次跳跃太大，先退回 B 的前一章和 B 做相邻对比，会更容易看清这章真正新增了什么。",
    en: "If the current jump is too large, compare the chapter right before B with B first. That is usually the clearest way to see what B really adds.",
    ja: "今のジャンプが大きすぎるなら、まず B の直前章と B を比較すると、この章が本当に何を増やしたのかを最も見やすくなります。",
  },
} as const;

const QUICK_COMPARE_PRESETS = [
  { a: "s01", b: "s02" },
  { a: "s06", b: "s07" },
  { a: "s11", b: "s12" },
  { a: "s14", b: "s15" },
  { a: "s18", b: "s19" },
] as const;

export default function ComparePage() {
  const t = useTranslations("compare");
  const tSession = useTranslations("sessions");
  const tLayer = useTranslations("layer_labels");
  const locale = useLocale();
  const [versionA, setVersionA] = useState<string>(QUICK_COMPARE_PRESETS[0].a);
  const [versionB, setVersionB] = useState<string>(QUICK_COMPARE_PRESETS[0].b);

  const previousOfB = useMemo(() => {
    if (!versionB) return null;
    const index = LEARNING_PATH.indexOf(versionB as (typeof LEARNING_PATH)[number]);
    if (index <= 0) return null;
    return LEARNING_PATH[index - 1];
  }, [versionB]);

  const infoA = useMemo(() => data.versions.find((v) => v.id === versionA), [versionA]);
  const infoB = useMemo(() => data.versions.find((v) => v.id === versionB), [versionB]);

  const docA = useMemo(
    () => docs.find((doc) => doc.version === versionA && doc.locale === locale),
    [locale, versionA]
  );
  const docB = useMemo(
    () => docs.find((doc) => doc.version === versionB && doc.locale === locale),
    [locale, versionB]
  );

  const leadA = useMemo(() => extractLead(docA?.content), [docA]);
  const leadB = useMemo(() => extractLead(docB?.content), [docB]);

  const comparison = useMemo(() => {
    if (!infoA || !infoB) return null;

    const toolsA = new Set(infoA.tools);
    const toolsB = new Set(infoB.tools);

    return {
      toolsOnlyA: infoA.tools.filter((tool) => !toolsB.has(tool)),
      toolsOnlyB: infoB.tools.filter((tool) => !toolsA.has(tool)),
      toolsShared: infoA.tools.filter((tool) => toolsB.has(tool)),
      newSurface: infoB.classes.filter((cls) => !infoA.classes.some((other) => other.name === cls.name)).length
        + infoB.functions.filter((fn) => !infoA.functions.some((other) => other.name === fn.name)).length,
      locDelta: infoB.loc - infoA.loc,
    };
  }, [infoA, infoB]);

  const progression = useMemo(() => {
    if (!infoA || !infoB) return "";

    const indexA = LEARNING_PATH.indexOf(versionA as (typeof LEARNING_PATH)[number]);
    const indexB = LEARNING_PATH.indexOf(versionB as (typeof LEARNING_PATH)[number]);

    if (indexA === indexB) return t("progression_same_chapter");
    if (indexB < indexA) return t("progression_reverse");
    if (indexB === indexA + 1) return t("progression_direct");
    if (infoA.layer === infoB.layer) return t("progression_same_layer");
    return t("progression_cross_layer");
  }, [infoA, infoB, t, versionA, versionB]);

  const chapterDistance = useMemo(() => {
    const indexA = LEARNING_PATH.indexOf(versionA as (typeof LEARNING_PATH)[number]);
    const indexB = LEARNING_PATH.indexOf(versionB as (typeof LEARNING_PATH)[number]);
    if (indexA < 0 || indexB < 0) return 0;
    return Math.abs(indexB - indexA);
  }, [versionA, versionB]);

  const recommendedBridgeDocs = useMemo(() => {
    if (!versionB) return [];

    return getBridgeDocDescriptors(versionB as (typeof LEARNING_PATH)[number])
      .map((descriptor) => {
        const doc =
          docs.find(
            (item) =>
              item.slug === descriptor.slug &&
              item.kind === "bridge" &&
              item.locale === locale
          ) ??
          docs.find(
            (item) =>
              item.slug === descriptor.slug &&
              item.kind === "bridge" &&
              item.locale === "zh"
          ) ??
          docs.find(
            (item) =>
              item.slug === descriptor.slug &&
              item.kind === "bridge" &&
              item.locale === "en"
          );

        if (!doc?.slug) return null;

        return {
          slug: doc.slug,
          title: pickText(locale, descriptor.title),
          summary: pickText(locale, descriptor.summary),
          fallbackLocale: doc.locale !== locale ? doc.locale : null,
        } satisfies RecommendedBridgeDoc;
      })
      .filter(
        (item): item is RecommendedBridgeDoc => Boolean(item)
      );
  }, [locale, versionB]);

  const guideB = useMemo(() => {
    if (!versionB) return null;
    return (
      getChapterGuide(versionB as (typeof LEARNING_PATH)[number], locale) ??
      getChapterGuide(versionB as (typeof LEARNING_PATH)[number], "en")
    );
  }, [locale, versionB]);

  const jumpDiagnosis = useMemo(() => {
    if (!infoA || !infoB) return null;

    const crossLayer = infoA.layer !== infoB.layer;
    if (chapterDistance <= 1) {
      return {
        title: pickText(locale, COMPARE_EXTRA_TEXT.adjacentTitle),
        body: pickText(locale, COMPARE_EXTRA_TEXT.adjacentBody),
        next: pickText(locale, COMPARE_EXTRA_TEXT.adjacentNext),
      };
    }

    if (crossLayer) {
      return {
        title: pickText(locale, COMPARE_EXTRA_TEXT.crossLayerTitle),
        body: pickText(locale, COMPARE_EXTRA_TEXT.crossLayerBody),
        next: pickText(locale, COMPARE_EXTRA_TEXT.crossLayerNext),
      };
    }

    return {
      title: pickText(locale, COMPARE_EXTRA_TEXT.sameLayerTitle),
      body: pickText(locale, COMPARE_EXTRA_TEXT.sameLayerBody),
      next: pickText(locale, COMPARE_EXTRA_TEXT.sameLayerNext),
    };
  }, [chapterDistance, infoA, infoB, locale]);

  return (
    <div className="min-w-0 overflow-x-hidden py-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 max-w-3xl text-zinc-500 dark:text-zinc-400">{t("subtitle")}</p>
      </div>

      <Card className="mb-8 overflow-hidden border-zinc-200/80 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.16),_transparent_34%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(250,250,250,0.98))] dark:border-zinc-800/80 dark:bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.16),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.14),_transparent_34%),linear-gradient(135deg,_rgba(24,24,27,0.98),_rgba(10,10,10,0.98))]">
        <CardHeader className="mb-6">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-500 dark:text-zinc-400">
            {t("learning_jump")}
          </p>
          <CardTitle className="text-xl sm:text-2xl">{t("selector_title")}</CardTitle>
          <p className="mt-2 max-w-2xl text-sm text-zinc-600 dark:text-zinc-300">
            {t("selector_note")}
          </p>
        </CardHeader>

        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <div className="w-full flex-1">
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              {t("select_a")}
            </label>
            <select
              value={versionA}
              onChange={(e) => setVersionA(e.target.value)}
              className="w-full rounded-xl border border-zinc-300/80 bg-white/80 px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-sky-400 dark:border-zinc-700 dark:bg-zinc-950/70 dark:text-zinc-100"
            >
              <option value="">{t("select_placeholder")}</option>
              {LEARNING_PATH.map((version) => (
                <option key={version} value={version}>
                  {version} - {tSession(version)}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-5 hidden rounded-full border border-zinc-300/80 bg-white/70 p-2 text-zinc-500 shadow-sm sm:block dark:border-zinc-700 dark:bg-zinc-900/80 dark:text-zinc-300">
            <ArrowRight size={18} />
          </div>

          <div className="w-full flex-1">
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              {t("select_b")}
            </label>
            <select
              value={versionB}
              onChange={(e) => setVersionB(e.target.value)}
              className="w-full rounded-xl border border-zinc-300/80 bg-white/80 px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-amber-400 dark:border-zinc-700 dark:bg-zinc-950/70 dark:text-zinc-100"
            >
              <option value="">{t("select_placeholder")}</option>
              {LEARNING_PATH.map((version) => (
                <option key={version} value={version}>
                  {version} - {tSession(version)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <div className="rounded-2xl border border-zinc-200/80 bg-white/70 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/60">
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {pickText(locale, COMPARE_EXTRA_TEXT.quickLabel)}
            </p>
            <h2 className="mt-2 text-base font-semibold text-zinc-950 dark:text-zinc-50">
              {pickText(locale, COMPARE_EXTRA_TEXT.quickTitle)}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {pickText(locale, COMPARE_EXTRA_TEXT.quickBody)}
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              {QUICK_COMPARE_PRESETS.map((preset) => (
                <button
                  key={`${preset.a}-${preset.b}`}
                  type="button"
                  onClick={() => {
                    setVersionA(preset.a);
                    setVersionB(preset.b);
                  }}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:text-zinc-50"
                >
                  {preset.a} {"->"} {preset.b}
                </button>
              ))}
            </div>
          </div>

          {versionB && previousOfB && previousOfB !== versionA && (
            <div className="rounded-2xl border border-amber-200/80 bg-amber-50/70 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
              <p className="text-xs uppercase tracking-[0.22em] text-amber-600/80 dark:text-amber-300/80">
                {pickText(locale, COMPARE_EXTRA_TEXT.quickLabel)}
              </p>
              <h2 className="mt-2 text-base font-semibold text-zinc-950 dark:text-zinc-50">
                {pickText(locale, COMPARE_EXTRA_TEXT.quickPrevious)}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                {pickText(locale, COMPARE_EXTRA_TEXT.quickPreviousBody)}
              </p>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => setVersionA(previousOfB)}
                  className="rounded-full border border-amber-200 bg-white px-3 py-1.5 text-sm font-medium text-amber-800 transition-colors hover:border-amber-300 dark:border-amber-900/70 dark:bg-zinc-950 dark:text-amber-200 dark:hover:border-amber-800"
                >
                  {previousOfB} {"->"} {versionB}
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>

      {infoA && infoB && comparison && (
        <div className="space-y-8">
          <Card className="overflow-hidden border-zinc-200/80 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.14),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.14),_transparent_36%),linear-gradient(160deg,_rgba(255,255,255,0.98),_rgba(244,244,245,0.98))] dark:border-zinc-800/80 dark:bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.18),_transparent_36%),linear-gradient(160deg,_rgba(24,24,27,0.98),_rgba(10,10,10,0.98))]">
            <CardHeader className="mb-6">
              <p className="text-xs uppercase tracking-[0.22em] text-zinc-500 dark:text-zinc-400">
                {t("learning_jump")}
              </p>
              <CardTitle className="flex flex-wrap items-center gap-3 text-2xl">
                <span>{tSession(versionA)}</span>
                <ArrowRight className="text-zinc-400" size={20} />
                <span>{tSession(versionB)}</span>
              </CardTitle>
              <p className="mt-2 max-w-3xl text-sm text-zinc-600 dark:text-zinc-300">
                {progression}
              </p>
            </CardHeader>

            <div className="grid gap-4 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-900/70">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-200">
                  <Lightbulb size={16} />
                  <span>{t("carry_from_a")}</span>
                </div>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {leadA || t("empty_lead")}
                </p>
              </div>

              <div className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-900/70">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-200">
                  <Sparkles size={16} />
                  <span>{t("new_in_b")}</span>
                </div>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {leadB || t("empty_lead")}
                </p>
              </div>

              <div className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-900/70">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-200">
                  <Layers3 size={16} />
                  <span>{t("progression")}</span>
                </div>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {progression}
                </p>
              </div>

              <div className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-900/70">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-200">
                  <Wrench size={16} />
                  <span>{pickText(locale, COMPARE_EXTRA_TEXT.goal)}</span>
                </div>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {guideB?.goal ?? pickText(locale, COMPARE_EXTRA_TEXT.emptyGoal)}
                </p>
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {[{ version: versionA, info: infoA, lead: leadA }, { version: versionB, info: infoB, lead: leadB }].map(
              ({ version, info, lead }) => (
                <Card key={version}>
                  <CardHeader>
                    <CardTitle>{tSession(version)}</CardTitle>
                    <p className="text-sm leading-6 text-zinc-500 dark:text-zinc-400">
                      {lead || t("empty_lead")}
                    </p>
                  </CardHeader>
                  <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-600 dark:text-zinc-300">
                    <span>{info.loc} LOC</span>
                    <span>{info.tools.length} tools</span>
                    <LayerBadge layer={info.layer}>{tLayer(info.layer)}</LayerBadge>
                  </div>
                </Card>
              )
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <Layers3 size={16} />
                  <span className="text-sm">{t("chapter_distance")}</span>
                </div>
              </CardHeader>
              <CardTitle>{chapterDistance}</CardTitle>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <Wrench size={16} />
                  <span className="text-sm">{t("new_tools_in_b")}</span>
                </div>
              </CardHeader>
              <CardTitle>{comparison.toolsOnlyB.length}</CardTitle>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <Wrench size={16} />
                  <span className="text-sm">{t("shared_tools_count")}</span>
                </div>
              </CardHeader>
              <CardTitle>{comparison.toolsShared.length}</CardTitle>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                  <FileCode size={16} />
                  <span className="text-sm">{t("new_surface")}</span>
                </div>
              </CardHeader>
              <CardTitle>{comparison.newSurface}</CardTitle>
            </Card>
          </div>

          {jumpDiagnosis && (
            <Card className="overflow-hidden border-zinc-200/80 bg-[linear-gradient(145deg,rgba(255,255,255,0.98),rgba(244,244,245,0.94))] dark:border-zinc-800/80 dark:bg-[linear-gradient(145deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]">
              <CardHeader>
                <p className="text-xs uppercase tracking-[0.22em] text-zinc-500 dark:text-zinc-400">
                  {pickText(locale, COMPARE_EXTRA_TEXT.diagnosisLabel)}
                </p>
                <CardTitle>{jumpDiagnosis.title}</CardTitle>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {jumpDiagnosis.body}
                </p>
              </CardHeader>

              <div className="grid grid-cols-1 gap-4 px-6 pb-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
                <div className="rounded-2xl border border-zinc-200/80 bg-white/85 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                    {pickText(locale, COMPARE_EXTRA_TEXT.nextBestLabel)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                    {jumpDiagnosis.next}
                  </p>
                </div>

                <div className="rounded-2xl border border-zinc-200/80 bg-white/85 p-4 dark:border-zinc-800/80 dark:bg-zinc-950/70">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                    {pickText(locale, COMPARE_EXTRA_TEXT.bridgeNudge)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {recommendedBridgeDocs.slice(0, 3).map((doc) => (
                      <Link
                        key={doc.slug}
                        href={`/${locale}/docs/${doc.slug}`}
                        className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:text-zinc-50"
                      >
                        {doc.title}
                      </Link>
                    ))}
                    {recommendedBridgeDocs.length === 0 && (
                      <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                        {t("empty_lead")}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {recommendedBridgeDocs.length > 0 && (
            <Card className="overflow-hidden border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]">
              <CardHeader>
                <p className="text-xs uppercase tracking-[0.22em] text-zinc-500 dark:text-zinc-400">
                  {pickText(locale, {
                    zh: "跳读辅助",
                    en: "Jump Reading Support",
                    ja: "飛び読み補助",
                  })}
                </p>
                <CardTitle>
                  {pickText(locale, {
                    zh: `从 ${tSession(versionA)} 跳到 ${tSession(versionB)} 前，先补这几张图`,
                    en: `Before jumping from ${tSession(versionA)} to ${tSession(versionB)}, read these bridge docs`,
                    ja: `${tSession(versionA)} から ${tSession(versionB)} へ飛ぶ前に、この橋渡し資料を読む`,
                  })}
                </CardTitle>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                  {pickText(locale, {
                    zh: "对比页不只是告诉你“多了什么”，还应该告诉你为了消化这次跃迁，哪些结构地图和机制展开最值得先看。",
                    en: "A good comparison page should not only show what was added. It should also point you to the best bridge docs for understanding the jump.",
                    ja: "比較ページは「何が増えたか」だけでなく、そのジャンプを理解する前に何を補うべきかも示すべきです。",
                  })}
                </p>
              </CardHeader>

              <div className="grid grid-cols-1 gap-4 px-6 pb-6 md:grid-cols-2">
                {recommendedBridgeDocs.map((doc) => (
                  <Link
                    key={doc.slug}
                    href={`/${locale}/docs/${doc.slug}`}
                    className="group rounded-2xl border border-zinc-200/80 bg-white/85 p-4 transition-colors hover:border-zinc-300 dark:border-zinc-800/80 dark:bg-zinc-950/75 dark:hover:border-zinc-700"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                          {doc.title}
                        </h3>
                        <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                          {doc.summary}
                        </p>
                      </div>
                      <ArrowRight
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
                  </Link>
                ))}
              </div>
            </Card>
          )}

          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold">
                {pickText(locale, {
                  zh: "主线执行对比",
                  en: "Mainline Flow Comparison",
                  ja: "主線実行の比較",
                })}
              </h2>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {pickText(locale, {
                  zh: "先看一条请求在两章之间是怎么变的：新的分支出现在哪里，哪些结果会回流到主循环，哪些部分只是侧车或外部车道。",
                  en: "Compare how one request evolves between the two chapters: where the new branch appears, what writes back into the loop, and what remains a side lane.",
                  ja: "1つの要求が2つの章の間でどう変わるかを先に見ます。どこで新しい分岐が生まれ、何が主ループへ戻り、何が側車レーンに残るのかを比較します。",
                })}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {tSession(versionA)}
                </h3>
                <ExecutionFlow version={versionA} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {tSession(versionB)}
                </h3>
                <ExecutionFlow version={versionB} />
              </div>
            </div>
          </div>

          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold">{t("architecture")}</h2>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {t("architecture_note")}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {tSession(versionA)}
                </h3>
                <ArchDiagram version={versionA} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {tSession(versionB)}
                </h3>
                <ArchDiagram version={versionB} />
              </div>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t("tool_comparison")}</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div>
                <h4 className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  {t("only_in")} {tSession(versionA)}
                </h4>
                {comparison.toolsOnlyA.length === 0 ? (
                  <p className="text-xs text-zinc-400">{t("none")}</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {comparison.toolsOnlyA.map((tool) => (
                      <span key={tool} className="rounded bg-rose-100 px-1.5 py-0.5 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
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
                  {t("only_in")} {tSession(versionB)}
                </h4>
                {comparison.toolsOnlyB.length === 0 ? (
                  <p className="text-xs text-zinc-400">{t("none")}</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {comparison.toolsOnlyB.map((tool) => (
                      <span key={tool} className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Card>

          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold">{t("source_diff")}</h2>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {t("source_diff_note")} {t("loc_delta")}:{" "}
                <span className={comparison.locDelta >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}>
                  {comparison.locDelta >= 0 ? "+" : ""}
                  {comparison.locDelta}
                </span>{" "}
                {t("lines")}
              </p>
            </div>
            <CodeDiff
              oldSource={infoA.source}
              newSource={infoB.source}
              oldLabel={`${infoA.id} (${infoA.filename})`}
              newLabel={`${infoB.id} (${infoB.filename})`}
            />
          </div>
        </div>
      )}

      {(!versionA || !versionB) && (
        <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50/60 p-12 text-center dark:border-zinc-700 dark:bg-zinc-900/40">
          <p className="text-zinc-400">{t("empty_hint")}</p>
        </div>
      )}
    </div>
  );
}
