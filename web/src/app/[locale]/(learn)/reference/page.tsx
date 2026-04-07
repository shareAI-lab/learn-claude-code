"use client";

import Link from "next/link";
import { useTranslations, useLocale } from "@/lib/i18n";
import {
  BRIDGE_DOCS,
  FOUNDATION_DOC_SLUGS,
  MECHANISM_DOC_SLUGS,
} from "@/lib/bridge-docs";

type SupportedLocale = "zh" | "en" | "ja";

export default function ReferencePage() {
  const t = useTranslations("reference");
  const locale = useLocale() as SupportedLocale;

  const foundationDocs = FOUNDATION_DOC_SLUGS.map(
    (slug) => BRIDGE_DOCS[slug]
  ).filter(Boolean);

  const mechanismDocs = MECHANISM_DOC_SLUGS.map(
    (slug) => BRIDGE_DOCS[slug]
  ).filter(Boolean);

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">
          {t("subtitle")}
        </p>
      </header>

      <section>
        <h2 className="mb-4 text-xl font-semibold">
          {t("foundation_title")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {foundationDocs.map((doc) => (
            <Link
              key={doc.slug}
              href={`/${locale}/docs/${doc.slug}`}
              className="group rounded-lg border border-[var(--color-border)] p-4 transition-colors hover:border-zinc-400 dark:hover:border-zinc-500"
            >
              <h3 className="font-medium group-hover:text-zinc-900 dark:group-hover:text-white">
                {doc.title[locale] ?? doc.title.en}
              </h3>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {doc.summary[locale] ?? doc.summary.en}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">
          {t("deep_dive_title")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {mechanismDocs.map((doc) => (
            <Link
              key={doc.slug}
              href={`/${locale}/docs/${doc.slug}`}
              className="group rounded-lg border border-[var(--color-border)] p-4 transition-colors hover:border-zinc-400 dark:hover:border-zinc-500"
            >
              <h3 className="font-medium group-hover:text-zinc-900 dark:group-hover:text-white">
                {doc.title[locale] ?? doc.title.en}
              </h3>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {doc.summary[locale] ?? doc.summary.en}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
