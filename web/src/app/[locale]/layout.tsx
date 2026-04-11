import type { Metadata } from "next";
import { I18nProvider } from "@/lib/i18n";
import { Header } from "@/components/layout/header";
import zh from "@/i18n/messages/zh.json";
import "../globals.css";

const locales = ["zh"];
const metaMessages: Record<string, typeof zh> = { zh };

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const normalizedLocale = locale === "zh" ? "zh" : "zh";
  const messages = metaMessages[normalizedLocale];
  return {
    title: messages.meta?.title || "Learn Claude Code",
    description: messages.meta?.description || "Learn Claude Code 中文教学站",
  };
}

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const normalizedLocale = locale === "zh" ? "zh" : "zh";

  return (
    <html lang={normalizedLocale} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            var theme = localStorage.getItem('theme');
            if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
              document.documentElement.classList.add('dark');
            }
          })();
        `}} />
      </head>
      <body className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] antialiased">
        <I18nProvider locale={normalizedLocale}>
          <Header />
          <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            {children}
          </main>
        </I18nProvider>
      </body>
    </html>
  );
}
