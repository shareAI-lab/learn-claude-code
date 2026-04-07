"use client";

import Link from "next/link";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { getVersionContent } from "@/lib/version-content";

const LAYER_DOT_COLORS: Record<string, string> = {
  core: "bg-blue-500",
  hardening: "bg-emerald-500",
  runtime: "bg-amber-500",
  platform: "bg-red-500",
};

export default function HomePage() {
  const t = useTranslations("home");
  const tSession = useTranslations("sessions");
  const tLayer = useTranslations("layer_labels");
  const locale = useLocale();

  return (
    <div className="flex flex-col gap-16 pb-16">
      {/* Hero */}
      <section className="flex flex-col items-center px-2 pt-12 text-center sm:pt-24">
        <h1 className="text-3xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          {t("hero_title")}
        </h1>
        <p className="mt-4 max-w-2xl text-base text-[var(--color-text-secondary)] sm:text-xl">
          {t("hero_subtitle")}
        </p>
        <div className="mt-8">
          <Link
            href={`/${locale}/s01`}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {t("start")}
            <span aria-hidden="true">&rarr;</span>
          </Link>
        </div>
      </section>

      {/* Chapter list by stage */}
      <section className="mx-auto w-full max-w-2xl space-y-10 px-4">
        {LAYERS.map((layer) => (
          <div key={layer.id}>
            <div className="flex items-center gap-2 pb-3">
              <span className={`h-2.5 w-2.5 rounded-full ${LAYER_DOT_COLORS[layer.id]}`} />
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                {tLayer(layer.id)}
              </span>
            </div>
            <ul className="space-y-1">
              {layer.versions.map((vId) => {
                const meta = VERSION_META[vId];
                const content = getVersionContent(vId, locale);
                if (!meta) return null;
                return (
                  <li key={vId}>
                    <Link
                      href={`/${locale}/${vId}`}
                      className="group block rounded-lg px-3 py-2.5 transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800/60"
                    >
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-sm text-zinc-400 dark:text-zinc-500">
                          {vId}
                        </span>
                        <span className="text-sm font-medium text-zinc-900 group-hover:underline dark:text-zinc-100">
                          {tSession(vId) || meta.title}
                        </span>
                      </div>
                      <p className="mt-0.5 pl-[calc(theme(fontSize.sm)+0.5rem+2ch)] text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
                        {content.keyInsight}
                      </p>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </section>
    </div>
  );
}
