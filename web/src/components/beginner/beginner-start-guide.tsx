"use client";

import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { BEGINNER_TRACKS } from "@/data/beginner-content";

function Command({ children }: { children: string }) {
  return (
    <code className="block overflow-x-auto rounded-lg bg-zinc-950 px-4 py-3 text-xs text-emerald-300 sm:text-sm">
      {children}
    </code>
  );
}

export function BeginnerStartGuide() {
  const locale = useLocale();
  if (locale !== "zh") return null;

  return (
    <section className="mb-12 space-y-6 rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 to-emerald-50 p-5 dark:border-blue-900 dark:from-blue-950/40 dark:to-emerald-950/30 sm:p-7">
      <div>
        <div className="text-sm font-bold text-blue-600 dark:text-blue-300">零基础入口</div>
        <h2 className="mt-1 text-2xl font-bold">先别硬啃代码，我们先把地图看懂</h2>
        <p className="mt-2 text-sm leading-7 text-zinc-600 dark:text-zinc-300">
          你不需要先会 Python。每章按“白话目标 → 页面模拟 → 逐句解释 → 自己运行”走一遍，代码会逐渐从外语变成说明书。
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {BEGINNER_TRACKS.map((track) => (
          <div key={track.name} className="rounded-xl border border-white/80 bg-white/80 p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900/70">
            <div className="font-semibold">{track.zhName}</div>
            <div className="text-xs text-zinc-500">{track.name}</div>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">{track.plain}</p>
            <p className="mt-2 text-xs font-medium text-blue-600 dark:text-blue-300">{track.chapters}</p>
          </div>
        ))}
      </div>

      <details className="group rounded-xl border border-amber-200 bg-amber-50/90 p-4 dark:border-amber-900 dark:bg-amber-950/30" open>
        <summary className="cursor-pointer font-bold">第一次如何打开、学习、测试和关闭？</summary>
        <ol className="mt-4 space-y-5 text-sm leading-6 text-zinc-700 dark:text-zinc-200">
          <li>
            <strong>打开项目：</strong>按 <kbd>Win</kbd> + <kbd>E</kbd> 打开文件资源管理器，在地址栏输入
            <Command>E:\learn-claude-code</Command>
          </li>
          <li>
            <strong>一键打开教程：</strong>双击根目录里的 <code>开始学习.cmd</code>。它会启动网站并自动打开中文学习路径。
          </li>
          <li>
            <strong>先做无密钥练习：</strong>进入任意章节后点击“模拟”页签，再点“单步”。这一步不会调用真实 AI，也不花 API 费用。
          </li>
          <li>
            <strong>测试是否安装成功：</strong>回到根目录，双击 <code>测试安装.cmd</code>。看到绿色的 <code>ALL TESTS PASSED</code> 就是全部通过。
          </li>
          <li>
            <strong>关闭教程：</strong>关闭网页标签并不会停止服务器；请双击 <code>关闭教程.cmd</code>，看到绿色的 <code>Tutorial server stopped</code> 就是服务已停止。
          </li>
        </ol>
      </details>

      <details className="rounded-xl border border-zinc-200 bg-white/80 p-4 dark:border-zinc-700 dark:bg-zinc-900/70">
        <summary className="cursor-pointer font-bold">想手动使用终端？照着复制这 4 条命令</summary>
        <div className="mt-4 space-y-3 text-sm">
          <p>打开 PowerShell 后，先进入项目：</p>
          <Command>cd E:\learn-claude-code</Command>
          <p>测试 Python 环境：</p>
          <Command>.\.venv\Scripts\python.exe --version</Command>
          <p>启动教程网站：</p>
          <Command>cd web; npm.cmd run dev</Command>
          <p>停止时回到这个终端，按：</p>
          <Command>Ctrl + C</Command>
        </div>
      </details>

      <div className="flex flex-wrap gap-3">
        <Link href="/zh/s01" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          从 s01 开始第一课 →
        </Link>
        <span className="self-center text-xs text-zinc-500">建议一天只学一章，先能复述，再看下一章。</span>
      </div>
    </section>
  );
}
