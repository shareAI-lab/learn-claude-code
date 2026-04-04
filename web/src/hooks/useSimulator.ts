"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { SimStep } from "@/types/agent-data";

interface SimulatorState {
  currentIndex: number;
  isPlaying: boolean;
  speed: number;
}

export function useSimulator(steps: SimStep[]) {
  const [state, setState] = useState<SimulatorState>({
    currentIndex: -1,
    isPlaying: false,
    speed: 1,
  });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stepForward = useCallback(() => {
    setState((prev) => {
      if (prev.currentIndex >= steps.length - 1) {
        return { ...prev, isPlaying: false };
      }
      return { ...prev, currentIndex: prev.currentIndex + 1 };
    });
  }, [steps.length]);

  const play = useCallback(() => {
    setState((prev) => {
      if (prev.currentIndex >= steps.length - 1) {
        return prev;
      }
      return { ...prev, isPlaying: true };
    });
  }, [steps.length]);

  const pause = useCallback(() => {
    clearTimer();
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, [clearTimer]);

  const reset = useCallback(() => {
    clearTimer();
    setState({ currentIndex: -1, isPlaying: false, speed: state.speed });
  }, [clearTimer, state.speed]);

  const setSpeed = useCallback((speed: number) => {
    setState((prev) => ({ ...prev, speed }));
  }, []);

  useEffect(() => {
    if (state.isPlaying && state.currentIndex < steps.length - 1) {
      const delay = 1200 / state.speed;
      timerRef.current = setTimeout(() => {
        stepForward();
      }, delay);
    } else if (state.isPlaying && state.currentIndex >= steps.length - 1) {
      setState((prev) => ({ ...prev, isPlaying: false }));
    }
    return () => clearTimer();
  }, [state.isPlaying, state.currentIndex, state.speed, steps.length, stepForward, clearTimer]);

  return {
    currentIndex: state.currentIndex,
    isPlaying: state.isPlaying,
    speed: state.speed,
    visibleSteps: steps.slice(0, state.currentIndex + 1),
    totalSteps: steps.length,
    isComplete: state.currentIndex >= steps.length - 1,
    play,
    pause,
    stepForward,
    reset,
    setSpeed,
  };
}
