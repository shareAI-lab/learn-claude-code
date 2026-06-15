"use client";

import { useTranslations } from "@/lib/i18n";
import { Timeline } from "@/components/timeline/timeline";

export default function TimelinePage() {
  const t = useTranslations("timeline");

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">
          {t("subtitle")}
        </p>
      </div>
      <Timeline />
    </div>
  );
}
