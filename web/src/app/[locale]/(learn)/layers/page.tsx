"use client";

import Link from "next/link";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LAYERS, VERSION_META } from "@/lib/constants";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { LayerBadge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { VersionIndex } from "@/types/agent-data";
import versionData from "@/data/generated/versions.json";

const data = versionData as VersionIndex;

const LAYER_BORDER_CLASSES: Record<string, string> = {
  tools: "border-l-blue-500",
  planning: "border-l-emerald-500",
  memory: "border-l-purple-500",
  concurrency: "border-l-amber-500",
  collaboration: "border-l-red-500",
};

const LAYER_HEADER_BG: Record<string, string> = {
  tools: "bg-blue-500",
  planning: "bg-emerald-500",
  memory: "bg-purple-500",
  concurrency: "bg-amber-500",
  collaboration: "bg-red-500",
};

export default function LayersPage() {
  const t = useTranslations("layers");
  const locale = useLocale();

  return (
    <div className="py-4">
      <div className="mb-10">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">{t("subtitle")}</p>
      </div>

      <div className="space-y-6">
        {LAYERS.map((layer, index) => {
          const versionInfos = layer.versions.map((vId) => {
            const info = data.versions.find((v) => v.id === vId);
            const meta = VERSION_META[vId];
            return { id: vId, info, meta };
          });

          return (
            <div
              key={layer.id}
              className={cn(
                "overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800",
                "border-l-4",
                LAYER_BORDER_CLASSES[layer.id]
              )}
            >
              {/* Layer header */}
              <div className="flex items-center gap-3 px-6 py-4">
                <div className={cn("h-3 w-3 rounded-full", LAYER_HEADER_BG[layer.id])} />
                <div>
                  <h2 className="text-xl font-bold">
                    <span className="text-zinc-400 dark:text-zinc-600">L{index + 1}</span>
                    {" "}
                    {layer.label}
                  </h2>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                    {t(layer.id)}
                  </p>
                </div>
              </div>

              {/* Version cards within this layer */}
              <div className="border-t border-zinc-200 bg-zinc-50/50 px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900/50">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {versionInfos.map(({ id, info, meta }) => (
                    <Link
                      key={id}
                      href={`/${locale}/${id}`}
                      className="group"
                    >
                      <Card className="transition-shadow hover:shadow-md">
                        <div className="flex items-start justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-zinc-400">{id}</span>
                              <LayerBadge layer={layer.id}>{layer.id}</LayerBadge>
                            </div>
                            <h3 className="mt-1 font-semibold text-zinc-900 dark:text-zinc-100">
                              {meta?.title || id}
                            </h3>
                            {meta?.subtitle && (
                              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                                {meta.subtitle}
                              </p>
                            )}
                          </div>
                          <ChevronRight
                            size={16}
                            className="mt-1 shrink-0 text-zinc-300 transition-colors group-hover:text-zinc-600 dark:text-zinc-600 dark:group-hover:text-zinc-300"
                          />
                        </div>
                        <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                          <span>{info?.loc ?? "?"} LOC</span>
                          <span>{info?.tools.length ?? "?"} tools</span>
                        </div>
                        {meta?.keyInsight && (
                          <p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400 line-clamp-2">
                            {meta.keyInsight}
                          </p>
                        )}
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Composition indicator */}
              {index < LAYERS.length - 1 && (
                <div className="flex items-center justify-center py-1 text-zinc-300 dark:text-zinc-700">
                  <svg width="20" height="12" viewBox="0 0 20 12" fill="none" className="text-current">
                    <path d="M10 0 L10 12 M5 7 L10 12 L15 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
