"use client";

import { Play, Pause, SkipBack, SkipForward, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepControlsProps {
  currentStep: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
  onReset: () => void;
  isPlaying: boolean;
  onToggleAutoPlay: () => void;
  stepTitle: string;
  stepDescription: string;
  className?: string;
}

export function StepControls({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  isPlaying,
  onToggleAutoPlay,
  stepTitle,
  stepDescription,
  className,
}: StepControlsProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {/* Annotation */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-800 dark:bg-blue-950/40">
        <div className="mb-1 text-sm font-semibold text-blue-900 dark:text-blue-200">
          {stepTitle}
        </div>
        <div className="text-sm text-blue-700 dark:text-blue-300">
          {stepDescription}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            onClick={onReset}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            title="Reset"
          >
            <RotateCcw size={16} />
          </button>
          <button
            onClick={onPrev}
            disabled={currentStep === 0}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            title="Previous step"
          >
            <SkipBack size={16} />
          </button>
          <button
            onClick={onToggleAutoPlay}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            title={isPlaying ? "Pause" : "Auto-play"}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button
            onClick={onNext}
            disabled={currentStep === totalSteps - 1}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            title="Next step"
          >
            <SkipForward size={16} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div
                key={i}
                className={cn(
                  "h-1.5 w-1.5 rounded-full transition-colors",
                  i === currentStep
                    ? "bg-blue-500"
                    : i < currentStep
                      ? "bg-blue-300 dark:bg-blue-700"
                      : "bg-zinc-200 dark:bg-zinc-700"
                )}
              />
            ))}
          </div>
          <span className="font-mono text-xs text-zinc-400">
            {currentStep + 1}/{totalSteps}
          </span>
        </div>
      </div>
    </div>
  );
}
