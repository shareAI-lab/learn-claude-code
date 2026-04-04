"use client";

import { useState, useEffect } from "react";

export function useDarkMode(): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const html = document.documentElement;
    setIsDark(html.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(html.classList.contains("dark"));
    });

    observer.observe(html, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return isDark;
}

export interface SvgPalette {
  nodeFill: string;
  nodeStroke: string;
  nodeText: string;
  activeNodeFill: string;
  activeNodeStroke: string;
  activeNodeText: string;
  endNodeFill: string;
  endNodeStroke: string;
  edgeStroke: string;
  activeEdgeStroke: string;
  arrowFill: string;
  labelFill: string;
  bgSubtle: string;
}

export function useSvgPalette(): SvgPalette {
  const isDark = useDarkMode();

  if (isDark) {
    return {
      nodeFill: "#27272a",
      nodeStroke: "#3f3f46",
      nodeText: "#d4d4d8",
      activeNodeFill: "#3b82f6",
      activeNodeStroke: "#2563eb",
      activeNodeText: "#ffffff",
      endNodeFill: "#a855f7",
      endNodeStroke: "#9333ea",
      edgeStroke: "#52525b",
      activeEdgeStroke: "#3b82f6",
      arrowFill: "#71717a",
      labelFill: "#a1a1aa",
      bgSubtle: "#18181b",
    };
  }

  return {
    nodeFill: "#e2e8f0",
    nodeStroke: "#cbd5e1",
    nodeText: "#475569",
    activeNodeFill: "#3b82f6",
    activeNodeStroke: "#2563eb",
    activeNodeText: "#ffffff",
    endNodeFill: "#a855f7",
    endNodeStroke: "#9333ea",
    edgeStroke: "#cbd5e1",
    activeEdgeStroke: "#3b82f6",
    arrowFill: "#94a3b8",
    labelFill: "#94a3b8",
    bgSubtle: "#f8fafc",
  };
}
