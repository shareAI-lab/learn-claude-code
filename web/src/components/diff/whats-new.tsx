"use client";

import { motion } from "framer-motion";
import { useTranslations } from "@/lib/i18n";
import { Card } from "@/components/ui/card";

interface WhatsNewProps {
  diff: {
    from: string;
    to: string;
    newClasses: string[];
    newFunctions: string[];
    newTools: string[];
    locDelta: number;
  } | null;
}

export function WhatsNew({ diff }: WhatsNewProps) {
  const t = useTranslations("version");
  const td = useTranslations("diff");

  if (!diff) {
    return null;
  }

  const hasContent =
    diff.newClasses.length > 0 ||
    diff.newTools.length > 0 ||
    diff.newFunctions.length > 0 ||
    diff.locDelta !== 0;

  if (!hasContent) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("whats_new")}</h2>

      <div className="grid gap-4 sm:grid-cols-2">
        {diff.newClasses.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="h-full">
              <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                {td("new_classes")}
              </h3>
              <div className="space-y-1.5">
                {diff.newClasses.map((cls) => (
                  <div
                    key={cls}
                    className="rounded-md bg-emerald-50 px-3 py-1.5 font-mono text-sm font-medium text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                  >
                    {cls}
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {diff.newTools.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <Card className="h-full">
              <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                {td("new_tools")}
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {diff.newTools.map((tool) => (
                  <span
                    key={tool}
                    className="rounded-full bg-blue-50 px-3 py-1 font-mono text-xs font-medium text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {diff.newFunctions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="h-full">
              <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                {td("new_functions")}
              </h3>
              <ul className="space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                {diff.newFunctions.map((fn) => (
                  <li key={fn} className="font-mono">
                    <span className="text-zinc-400 dark:text-zinc-500">
                      def{" "}
                    </span>
                    {fn}()
                  </li>
                ))}
              </ul>
            </Card>
          </motion.div>
        )}

        {diff.locDelta !== 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            <Card className="flex h-full items-center">
              <div>
                <h3 className="mb-1 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {td("loc_delta")}
                </h3>
                <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  +{diff.locDelta} lines
                </p>
              </div>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
}
