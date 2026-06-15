"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations, useLocale } from "@/lib/i18n";
import { Github, Menu, X, Sun, Moon } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { key: "timeline", href: "/timeline" },
  { key: "compare", href: "/compare" },
  { key: "layers", href: "/layers" },
] as const;

const LOCALES = [
  { code: "en", label: "EN" },
  { code: "zh", label: "中文" },
  { code: "ja", label: "日本語" },
];

export function Header() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const locale = useLocale();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggleDark() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  function switchLocale(newLocale: string) {
    const newPath = pathname.replace(`/${locale}`, `/${newLocale}`);
    window.location.href = newPath;
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-bg)]/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href={`/${locale}`} className="text-lg font-bold">
          Learn Claude Code
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-6 md:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.key}
              href={`/${locale}${item.href}`}
              className={cn(
                "text-sm font-medium transition-colors hover:text-zinc-900 dark:hover:text-white",
                pathname.includes(item.href)
                  ? "text-zinc-900 dark:text-white"
                  : "text-zinc-500 dark:text-zinc-400"
              )}
            >
              {t(item.key)}
            </Link>
          ))}

          {/* Locale switcher */}
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] p-0.5">
            {LOCALES.map((l) => (
              <button
                key={l.code}
                onClick={() => switchLocale(l.code)}
                className={cn(
                  "rounded-md px-2 py-1 text-xs font-medium transition-colors",
                  locale === l.code
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400"
                )}
              >
                {l.label}
              </button>
            ))}
          </div>

          <button
            onClick={toggleDark}
            className="rounded-md p-1.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-white"
          >
            {mounted ? (dark ? <Sun size={16} /> : <Moon size={16} />) : <span className="w-4 h-4 inline-block" />}
          </button>

          <a
            href="https://github.com/shareAI-lab/learn-claude-code"
            target="_blank"
            rel="noopener"
            className="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-white"
          >
            <Github size={18} />
          </a>
        </nav>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center md:hidden"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-[var(--color-border)] bg-[var(--color-bg)] p-4 md:hidden">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.key}
              href={`/${locale}${item.href}`}
              className="flex min-h-[44px] items-center text-sm"
              onClick={() => setMobileOpen(false)}
            >
              {t(item.key)}
            </Link>
          ))}
          <div className="mt-3 flex items-center justify-between border-t border-[var(--color-border)] pt-3">
            <div className="flex gap-2">
              {LOCALES.map((l) => (
                <button
                  key={l.code}
                  onClick={() => switchLocale(l.code)}
                  className={cn(
                    "min-h-[44px] min-w-[44px] rounded-md px-3 text-xs font-medium",
                    locale === l.code
                      ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                      : "border border-[var(--color-border)]"
                  )}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleDark}
                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-white"
              >
                {mounted ? (dark ? <Sun size={18} /> : <Moon size={18} />) : <span className="w-[18px] h-[18px] inline-block" />}
              </button>
              <a
                href="https://github.com/shareAI-lab/learn-claude-code"
                target="_blank"
                rel="noopener"
                className="flex min-h-[44px] min-w-[44px] items-center justify-center text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-white"
              >
                <Github size={18} />
              </a>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
