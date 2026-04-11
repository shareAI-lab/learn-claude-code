"use client";
import { createContext, useContext, ReactNode } from "react";
import zh from "@/i18n/messages/zh.json";

type Messages = typeof zh;

const messagesMap: Record<string, Messages> = { zh };

const I18nContext = createContext<{ locale: string; messages: Messages }>({
  locale: "zh",
  messages: zh,
});

export function I18nProvider({ locale, children }: { locale: string; children: ReactNode }) {
  const normalizedLocale = locale === "zh" ? "zh" : "zh";
  const messages = messagesMap[normalizedLocale];
  return (
    <I18nContext.Provider value={{ locale: normalizedLocale, messages }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslations(namespace?: string) {
  const { messages } = useContext(I18nContext);
  return (key: string) => {
    const ns = namespace ? (messages as any)[namespace] : messages;
    if (!ns) return key;
    return (ns as any)[key] || key;
  };
}

export function useLocale() {
  return useContext(I18nContext).locale;
}
