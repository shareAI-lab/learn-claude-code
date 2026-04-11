import zh from "@/i18n/messages/zh.json";

type Messages = typeof zh;

const messagesMap: Record<string, Messages> = { zh };

export function getTranslations(locale: string, namespace: string) {
  const normalizedLocale = locale === "zh" ? "zh" : "zh";
  const messages = messagesMap[normalizedLocale];
  const ns = (messages as Record<string, Record<string, string>>)[namespace];
  const fallbackNs = (zh as Record<string, Record<string, string>>)[namespace];
  return (key: string): string => {
    return ns?.[key] || fallbackNs?.[key] || key;
  };
}
