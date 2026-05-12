"use client";

import Link from "next/link";
import { useTranslations } from "@/lib/i18n";
import { useLocale } from "@/lib/i18n";
import { Timeline } from "@/components/timeline/timeline";
import { Card } from "@/components/ui/card";
import { LayerBadge } from "@/components/ui/badge";
import { STAGE_CHECKPOINTS } from "@/lib/stage-checkpoints";

const GUIDE_TEXT = {
  label: {
    zh: "怎么使用这页",
    en: "How to Use This Page",
    ja: "このページの使い方",
  },
  cards: [
    {
      title: {
        zh: "第一次完整读",
        en: "First Full Pass",
        ja: "初回の通読",
      },
      body: {
        zh: "从上往下顺序读，不要急着横跳。前六章是主闭环，后面都建立在它上面。",
        en: "Read top to bottom before jumping around. The first six chapters establish the main loop everything else depends on.",
        ja: "まずは上から順に読む。最初の6章が主ループで、後半はその上に積まれています。",
      },
    },
    {
      title: {
        zh: "中途开始混",
        en: "If Things Start to Blur",
        ja: "途中で混ざり始めたら",
      },
      body: {
        zh: "不要死盯源码。先看这章落在哪个阶段，再回桥接资料校正 task、runtime、teammate、worktree 这些边界。",
        en: "Do not stare at code first. Identify the stage, then use bridge docs to reset boundaries like task, runtime, teammate, and worktree.",
        ja: "先にコードへ潜らず、この章がどの段階に属するかを見て、bridge doc で task・runtime・teammate・worktree の境界を補正します。",
      },
    },
    {
      title: {
        zh: "准备自己实现",
        en: "If You Are Rebuilding It",
        ja: "自分で実装するなら",
      },
      body: {
        zh: "每走完一个阶段，就停下来自己手写一版最小实现。不要等到 s19 再一次性回头补。",
        en: "After each stage, stop and rebuild the minimal version yourself instead of waiting until s19 to backfill everything at once.",
        ja: "各段階が終わるたびに最小版を自分で書き直す。一気に s19 まで進んでからまとめて補わない。",
      },
    },
  ],
  supportLabel: {
    zh: "全程可反复回看的桥接资料",
    en: "Bridge Docs Worth Re-reading",
    ja: "何度も戻る価値のある橋渡し資料",
  },
  supportBody: {
    zh: "如果你读到中后段开始打结，先回这些资料，而不是硬闯下一章。",
    en: "When the middle and late chapters start to tangle, revisit these before forcing the next chapter.",
    ja: "中盤以降で混線し始めたら、次の章へ突っ込む前にまずここへ戻ります。",
  },
  checkpointLabel: {
    zh: "时间线不仅告诉你顺序，也告诉你哪里该停",
    en: "The timeline shows both order and where to pause",
    ja: "このタイムラインは順序だけでなく、どこで止まるべきかも示す",
  },
  checkpointTitle: {
    zh: "每走完一个阶段，先自己重建一版，再进入下一阶段",
    en: "After each stage, rebuild one working slice before entering the next stage",
    ja: "各段階のあとで 1 回作り直してから次の段階へ入る",
  },
  checkpointBody: {
    zh: "如果你只是一路往下读，章节边界迟早会糊。最稳的读法是在 `s06 / s11 / s14 / s19` 各停一次，确认自己真的能把该阶段已经成立的系统重新写出来。",
    en: "If you only keep scrolling downward, chapter boundaries will eventually blur. The safer reading move is to pause at `s06 / s11 / s14 / s19` and confirm that you can rebuild the working system slice for that stage.",
    ja: "ただ下へ読み進めるだけだと、章境界はいつか必ずぼやけます。`s06 / s11 / s14 / s19` で止まり、その段階で成立した system slice を作り直せるか確認する方が安定します。",
  },
  checkpointRebuild: {
    zh: "此时该能手搓出来的东西",
    en: "What You Should Be Able To Rebuild Here",
    ja: "この時点で作り直せるべきもの",
  },
  checkpointOpen: {
    zh: "打开阶段收口",
    en: "Open Stage Exit",
    ja: "段階の収束点を開く",
  },
  links: [
    {
      slug: "s00a-query-control-plane",
      title: { zh: "查询控制平面", en: "Query Control Plane", ja: "クエリ制御プレーン" },
    },
    {
      slug: "s02b-tool-execution-runtime",
      title: { zh: "工具执行运行时", en: "Tool Execution Runtime", ja: "ツール実行ランタイム" },
    },
    {
      slug: "s13a-runtime-task-model",
      title: { zh: "运行时任务模型", en: "Runtime Task Model", ja: "ランタイムタスクモデル" },
    },
    {
      slug: "team-task-lane-model",
      title: { zh: "队友-任务-车道模型", en: "Team Task Lane Model", ja: "チームメイト・タスク・レーンモデル" },
    },
    {
      slug: "s19a-mcp-capability-layers",
      title: { zh: "MCP 能力层地图", en: "MCP Capability Layers", ja: "MCP 能力層マップ" },
    },
  ],
} as const;

function pick(
  locale: string,
  value: {
    zh: string;
    en: string;
    ja: string;
  }
) {
  if (locale === "zh") return value.zh;
  if (locale === "ja") return value.ja;
  return value.en;
}

export default function TimelinePage() {
  const t = useTranslations("timeline");
  const locale = useLocale();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">
          {t("subtitle")}
        </p>
      </div>

      <section className="mb-10 space-y-5">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
            {pick(locale, GUIDE_TEXT.label)}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {GUIDE_TEXT.cards.map((card) => (
            <div
              key={card.title.en}
              className="rounded-2xl border border-zinc-200/80 bg-zinc-50/70 p-5 dark:border-zinc-800/80 dark:bg-zinc-900/60"
            >
              <h2 className="text-base font-semibold">
                {pick(locale, card.title)}
              </h2>
              <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                {pick(locale, card.body)}
              </p>
            </div>
          ))}
        </div>

        <div className="rounded-[24px] border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] p-5 dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))]">
          <h2 className="text-base font-semibold">
            {pick(locale, GUIDE_TEXT.supportLabel)}
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            {pick(locale, GUIDE_TEXT.supportBody)}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {GUIDE_TEXT.links.map((link) => (
              <Link
                key={link.slug}
                href={`/${locale}/docs/${link.slug}`}
                className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:text-zinc-50"
              >
                {pick(locale, link.title)}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="mb-10 rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] p-5 dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))] sm:p-6">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
            {pick(locale, GUIDE_TEXT.checkpointLabel)}
          </p>
          <h2 className="mt-3 text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
            {pick(locale, GUIDE_TEXT.checkpointTitle)}
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            {pick(locale, GUIDE_TEXT.checkpointBody)}
          </p>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {STAGE_CHECKPOINTS.map((checkpoint) => (
            <Card
              key={checkpoint.layer}
              className="border-zinc-200/80 bg-white/90 dark:border-zinc-800/80 dark:bg-zinc-950/75"
            >
              <div className="flex flex-wrap items-center gap-2">
                <LayerBadge layer={checkpoint.layer}>{checkpoint.entryVersion}-{checkpoint.endVersion}</LayerBadge>
              </div>
              <h3 className="mt-4 text-base font-semibold text-zinc-950 dark:text-zinc-50">
                {pick(locale, checkpoint.title)}
              </h3>
              <div className="mt-4 rounded-2xl border border-zinc-200/80 bg-zinc-50/70 p-4 dark:border-zinc-800/80 dark:bg-zinc-900/60">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                  {pick(locale, GUIDE_TEXT.checkpointRebuild)}
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                  {pick(locale, checkpoint.rebuild)}
                </p>
              </div>
              <div className="mt-4">
                <Link
                  href={`/${locale}/${checkpoint.endVersion}`}
                  className="inline-flex rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:text-zinc-50"
                >
                  {pick(locale, GUIDE_TEXT.checkpointOpen)}: {checkpoint.endVersion}
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <Timeline />
    </div>
  );
}
