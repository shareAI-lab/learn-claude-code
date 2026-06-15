"use client";

import { useTranslations } from "@/lib/i18n";
import { Play, Pause, SkipForward, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

interface SimulatorControlsProps {
  isPlaying: boolean;
  isComplete: boolean;
  currentIndex: number;
  totalSteps: number;
  speed: number;
  onPlay: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onSpeedChange: (speed: number) => void;
}

const SPEEDS = [0.5, 1, 2, 4];

export function SimulatorControls({
  isPlaying,
  isComplete,
  currentIndex,
  totalSteps,
  speed,
  onPlay,
  onPause,
  onStep,
  onReset,
  onSpeedChange,
}: SimulatorControlsProps) {
  const t = useTranslations("sim");

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5">
        {isPlaying ? (
          <button
            onClick={onPause}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-white transition-colors hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
            title={t("pause")}
          >
            <Pause size={16} />
          </button>
        ) : (
          <button
            onClick={onPlay}
            disabled={isComplete}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-white transition-colors hover:bg-zinc-700 disabled:opacity-40 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
            title={t("play")}
          >
            <Play size={16} />
          </button>
        )}
        <button
          onClick={onStep}
          disabled={isComplete}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--color-border)] transition-colors hover:bg-zinc-100 disabled:opacity-40 dark:hover:bg-zinc-800"
          title={t("step")}
        >
          <SkipForward size={16} />
        </button>
        <button
          onClick={onReset}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--color-border)] transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
          title={t("reset")}
        >
          <RotateCcw size={16} />
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[var(--color-text-secondary)]">
          {t("speed")}:
        </span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            className={cn(
              "rounded px-2 py-1 text-xs font-medium transition-colors",
              speed === s
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            )}
          >
            {s}x
          </button>
        ))}
      </div>

      <span className="ml-auto text-xs tabular-nums text-[var(--color-text-secondary)]">
        {Math.max(0, currentIndex + 1)} {t("step_of")} {totalSteps}
      </span>
    </div>
  );
}
