import Link from "next/link";
import docsData from "@/data/generated/docs.json";
import { DocRenderer } from "@/components/docs/doc-renderer";
import { getTranslations } from "@/lib/i18n-server";
import { BRIDGE_DOCS, getChaptersForBridgeDoc } from "@/lib/bridge-docs";

const SUPPORTED_LOCALES = ["en", "zh", "ja"] as const;

function findBridgeDoc(locale: string, slug: string) {
  return (
    (docsData as Array<{
      slug?: string;
      locale?: string;
      kind?: string;
      title?: string;
    }>).find(
      (item) => item.kind === "bridge" && item.slug === slug && item.locale === locale
    ) ??
    (docsData as Array<{
      slug?: string;
      locale?: string;
      kind?: string;
      title?: string;
    }>).find(
      (item) => item.kind === "bridge" && item.slug === slug && item.locale === "zh"
    ) ??
    (docsData as Array<{
      slug?: string;
      locale?: string;
      kind?: string;
      title?: string;
    }>).find(
      (item) => item.kind === "bridge" && item.slug === slug && item.locale === "en"
    )
  );
}

export function generateStaticParams() {
  const slugs = Array.from(
    new Set(
      (docsData as Array<{ kind?: string; slug?: string }>)
        .filter((doc) => doc.kind === "bridge" && doc.slug)
        .map((doc) => doc.slug as string)
    )
  );

  return SUPPORTED_LOCALES.flatMap((locale) =>
    slugs.map((slug) => ({ locale, slug }))
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const descriptor = BRIDGE_DOCS[slug];
  const doc = findBridgeDoc(locale, slug);
  const title =
    descriptor?.title?.[locale as "en" | "zh" | "ja"] ??
    descriptor?.title?.en ??
    doc?.title ??
    "Learn Claude Code";
  const description =
    descriptor?.summary?.[locale as "en" | "zh" | "ja"] ??
    descriptor?.summary?.en ??
    undefined;

  return {
    title,
    description,
  };
}

export default async function BridgeDocPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const t = getTranslations(locale, "version");
  const tSession = getTranslations(locale, "sessions");
  const descriptor = BRIDGE_DOCS[slug];
  const doc = findBridgeDoc(locale, slug);
  const relatedVersions = getChaptersForBridgeDoc(slug);

  if (!doc?.title) {
    return (
      <div className="py-20 text-center">
        <h1 className="text-2xl font-bold">Document not found</h1>
        <p className="mt-2 text-zinc-500">{slug}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 py-4">
      <header className="space-y-3">
        <Link
          href={`/${locale}`}
          className="inline-flex items-center gap-2 text-sm text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
        >
          <span>&larr;</span>
          <span>{t("bridge_docs_back")}</span>
        </Link>
        <div className="space-y-2">
          <span className="inline-flex rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-medium text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            {t("bridge_docs_standalone")}
          </span>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
            {descriptor?.title?.[locale as "en" | "zh" | "ja"] ??
              descriptor?.title?.en ??
              doc.title}
          </h1>
          {doc.locale !== locale && (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {t("bridge_docs_fallback_note")} {doc.locale}
            </p>
          )}
        </div>
      </header>

      <section className="rounded-[28px] border border-zinc-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,244,245,0.92))] px-5 py-6 shadow-sm dark:border-zinc-800/80 dark:bg-[linear-gradient(135deg,rgba(24,24,27,0.96),rgba(9,9,11,0.92))] sm:px-6">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
              {locale === "zh"
                ? "这页适合什么时候回看"
                : locale === "ja"
                  ? "このページへ戻るべき場面"
                  : "When This Page Helps"}
            </p>
            <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {descriptor?.summary?.[locale as "en" | "zh" | "ja"] ??
                descriptor?.summary?.en}
            </p>
          </div>

          {relatedVersions.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">
                {locale === "zh"
                  ? "最适合和这些章节一起读"
                  : locale === "ja"
                    ? "いっしょに読むと効く章"
                    : "Best Read Alongside"}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {relatedVersions.map((version) => (
                  <Link
                    key={version}
                    href={`/${locale}/${version}`}
                    className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:text-zinc-50"
                  >
                    {version} · {tSession(version)}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-[28px] border border-zinc-200/80 bg-white/90 px-5 py-6 shadow-sm dark:border-zinc-800/80 dark:bg-zinc-950/80 sm:px-6">
        <DocRenderer slug={slug} />
      </section>
    </div>
  );
}
