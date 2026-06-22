"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import { getBeginnerChapter } from "@/data/beginner-content";

export function BeginnerChapterGuide({ version, filename }: { version: string; filename: string }) {
  const locale = useLocale();
  const chapter = getBeginnerChapter(version);
  const [copied, setCopied] = useState(false);

  if (locale !== "zh" || !chapter) return null;

  const command = `.\\.venv\\Scripts\\python.exe ${filename.replaceAll("/", "\\")}`;

  async function copyCommand() {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <section className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 dark:border-emerald-900 dark:bg-emerald-950/20">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-bold text-white">小白先看这里</span>
        <span className="rounded-full border border-emerald-300 px-2.5 py-1 text-xs text-emerald-700 dark:border-emerald-800 dark:text-emerald-300">
          {chapter.track}
        </span>
      </div>
      <h2 className="mt-3 text-xl font-bold">这一章只学一件事：{chapter.zhTitle}</h2>
      <p className="mt-2 leading-7 text-zinc-700 dark:text-zinc-200">{chapter.plain}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-white p-4 dark:bg-zinc-900">
          <div className="text-xs font-bold text-zinc-500">生活类比</div>
          <p className="mt-1 text-sm leading-6">{chapter.analogy}</p>
        </div>
        <div className="rounded-xl bg-white p-4 dark:bg-zinc-900">
          <div className="text-xs font-bold text-zinc-500">本章及格线</div>
          <p className="mt-1 text-sm leading-6">{chapter.focus}</p>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-emerald-200 bg-white p-4 dark:border-emerald-900 dark:bg-zinc-900">
        <div className="font-bold">跟着我做（按顺序点击）</div>
        <ol className="mt-3 grid gap-3 text-sm sm:grid-cols-4">
          <li><strong>1. 模拟</strong><br />点上方“模拟”，再反复点“单步”。</li>
          <li><strong>2. 学习</strong><br />回到“学习”，代码下方点“逐句翻译”。</li>
          <li><strong>3. 源码</strong><br />点“源码”，只寻找本章及格线里的关键词。</li>
          <li><strong>4. 实跑</strong><br />配置 API Key 后，在项目根目录运行下方命令。</li>
        </ol>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <code className="min-w-0 flex-1 overflow-x-auto rounded-lg bg-zinc-950 px-3 py-2 text-xs text-emerald-300">{command}</code>
          <button onClick={copyCommand} className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
            {copied ? "已复制" : "复制运行命令"}
          </button>
        </div>
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
          真实运行会调用模型 API。未配置 <code>ANTHROPIC_API_KEY</code> 时，先用“模拟”学习即可；密钥不要截图或发给别人。
        </p>
      </div>
    </section>
  );
}
