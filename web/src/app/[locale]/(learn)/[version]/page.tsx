import Link from "next/link";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";
import versionsData from "@/data/generated/versions.json";
import { VersionDetailClient } from "./client";
import { getTranslations } from "@/lib/i18n-server";

export function generateStaticParams() {
  return LEARNING_PATH.map((version) => ({ version }));
}

export default async function VersionPage({
  params,
}: {
  params: Promise<{ locale: string; version: string }>;
}) {
  const { locale, version } = await params;

  const versionData = versionsData.versions.find((v) => v.id === version);
  const meta = VERSION_META[version];
  const diff = versionsData.diffs.find((d) => d.to === version) ?? null;

  if (!versionData || !meta) {
    return (
      <div className="py-20 text-center">
        <h1 className="text-2xl font-bold">Version not found</h1>
        <p className="mt-2 text-zinc-500">{version}</p>
      </div>
    );
  }

  const t = getTranslations(locale, "version");
  const tSession = getTranslations(locale, "sessions");
  const tLayer = getTranslations(locale, "layer_labels");
  const layer = LAYERS.find((l) => l.id === meta.layer);

  const pathIndex = LEARNING_PATH.indexOf(version as typeof LEARNING_PATH[number]);
  const prevVersion = pathIndex > 0 ? LEARNING_PATH[pathIndex - 1] : null;
  const nextVersion =
    pathIndex < LEARNING_PATH.length - 1
      ? LEARNING_PATH[pathIndex + 1]
      : null;

  return (
    <div className="mx-auto max-w-3xl space-y-10 py-4">
      {/* Header */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-lg bg-zinc-100 px-3 py-1 font-mono text-lg font-bold dark:bg-zinc-800">
            {version}
          </span>
          <h1 className="text-2xl font-bold sm:text-3xl">{tSession(version) || meta.title}</h1>
          {layer && (
            <LayerBadge layer={meta.layer}>{tLayer(layer.id)}</LayerBadge>
          )}
        </div>
        <p className="text-lg text-zinc-500 dark:text-zinc-400">
          {meta.subtitle}
        </p>
        <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400">
          <span className="font-mono">{versionData.loc} LOC</span>
          <span>{versionData.tools.length} {t("tools")}</span>
          {meta.coreAddition && (
            <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs dark:bg-zinc-800">
              {meta.coreAddition}
            </span>
          )}
        </div>
        {meta.keyInsight && (
          <blockquote className="border-l-4 border-zinc-300 pl-4 text-sm italic text-zinc-500 dark:border-zinc-600 dark:text-zinc-400">
            {meta.keyInsight}
          </blockquote>
        )}
      </header>

      {/* Client-rendered interactive sections */}
      <VersionDetailClient
        version={version}
        diff={diff}
        source={versionData.source}
        filename={versionData.filename}
      />

      {/* Prev / Next navigation */}
      <nav className="flex items-center justify-between border-t border-zinc-200 pt-6 dark:border-zinc-700">
        {prevVersion ? (
          <Link
            href={`/${locale}/${prevVersion}`}
            className="group flex items-center gap-2 text-sm text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-white"
          >
            <span className="transition-transform group-hover:-translate-x-1">
              &larr;
            </span>
            <div>
              <div className="text-xs text-zinc-400">{t("prev")}</div>
              <div className="font-medium">
                {prevVersion} - {tSession(prevVersion) || VERSION_META[prevVersion]?.title}
              </div>
            </div>
          </Link>
        ) : (
          <div />
        )}
        {nextVersion ? (
          <Link
            href={`/${locale}/${nextVersion}`}
            className="group flex items-center gap-2 text-right text-sm text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-white"
          >
            <div>
              <div className="text-xs text-zinc-400">{t("next")}</div>
              <div className="font-medium">
                {tSession(nextVersion) || VERSION_META[nextVersion]?.title} - {nextVersion}
              </div>
            </div>
            <span className="transition-transform group-hover:translate-x-1">
              &rarr;
            </span>
          </Link>
        ) : (
          <div />
        )}
      </nav>
    </div>
  );
}
