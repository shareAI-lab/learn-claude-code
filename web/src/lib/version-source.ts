import type { AgentVersion } from "@/types/agent-data";

type SourceLocale = "en" | "zh" | "ja";

function normalizeSourceLocale(locale: string): SourceLocale {
  if (locale === "zh") return "zh";
  if (locale === "ja") return "ja";
  return "en";
}

export function getLocalizedSource(
  version: Pick<AgentVersion, "source" | "sourceByLocale">,
  locale: string
): string {
  const normalized = normalizeSourceLocale(locale);
  const localized = version.sourceByLocale?.[normalized];
  if (localized) return localized;

  // `ja` falls back to English source by design.
  const english = version.sourceByLocale?.en;
  if (english) return english;

  // Backward compatibility for old generated data without `sourceByLocale`.
  return version.source;
}
