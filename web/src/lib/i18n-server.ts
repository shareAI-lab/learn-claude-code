import en from "@/i18n/messages/en.json";
import zh from "@/i18n/messages/zh.json";
import ja from "@/i18n/messages/ja.json";
import vi from "@/i18n/messages/vi.json";

type Messages = typeof en;

const messagesMap: Record<string, Messages> = { en, zh, ja, vi };

export function getTranslations(locale: string, namespace: string) {
  const messages = messagesMap[locale] || en;
  const ns = (messages as Record<string, Record<string, string>>)[namespace];
  const fallbackNs = (en as Record<string, Record<string, string>>)[namespace];
  return (key: string): string => {
    return ns?.[key] || fallbackNs?.[key] || key;
  };
}
