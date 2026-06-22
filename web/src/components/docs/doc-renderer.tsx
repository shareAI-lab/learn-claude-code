"use client";

import { useMemo } from "react";
import { useLocale } from "@/lib/i18n";
import docsData from "@/data/generated/docs.json";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeHighlight from "rehype-highlight";
import rehypeStringify from "rehype-stringify";

interface DocRendererProps {
  version: string;
}

function renderMarkdown(md: string): string {
  const result = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeHighlight, { detect: false, ignoreMissing: true })
    .use(rehypeStringify)
    .processSync(md);
  return String(result);
}

function decodeHtml(text: string): string {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&#x27;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function explainPythonLine(line: string): string {
  const code = line.trim();

  if (/^(from|import)\s/.test(code)) return "导入别人已经写好的功能，后面可以直接使用。";
  if (/^def\s/.test(code)) return "定义一个可重复调用的函数；括号里是它需要接收的材料。";
  if (/^class\s/.test(code)) return "定义一种对象模板，把相关数据和操作放在一起。";
  if (/^while True:/.test(code)) return "开始持续循环；只有遇到 return 或 break 才会停止。";
  if (/^for\s.+\sin\s/.test(code)) return "把右侧集合里的内容逐个取出，并对每一个执行下面缩进的代码。";
  if (/^if\s/.test(code)) return "进行条件判断；条件成立时才执行下面缩进的代码。";
  if (/^elif\s/.test(code)) return "前一个条件不成立时，再检查这个条件。";
  if (/^else:/.test(code)) return "前面的条件都不成立时，执行这里。";
  if (/^try:/.test(code)) return "尝试执行一段可能失败的操作。";
  if (/^except\s?/.test(code)) return "上面的操作出错时，改走这里的处理办法。";
  if (/^return\b/.test(code)) return "结束当前函数，并把结果交回调用它的地方。";
  if (/^break\b/.test(code)) return "立刻跳出当前循环。";
  if (/messages\s*=\s*\[/.test(code)) return "新建消息清单，先把用户问题作为第一条消息放进去。";
  if (/client\.messages\.create/.test(code)) return "把模型、系统说明、历史消息和工具清单一起发给 LLM。";
  if (/stop_reason/.test(code) && /tool_use/.test(code)) return "检查模型是否还想调用工具；不需要工具就结束本轮。";
  if (/messages\.append/.test(code)) return "把新内容追加到对话历史，让下一轮知道刚才发生了什么。";
  if (/results\.append/.test(code)) return "把一个工具的执行结果加入结果清单。";
  if (/\.append\(/.test(code)) return "把括号里的内容添加到清单末尾。";
  if (/TOOLS\s*=/.test(code)) return "定义 AI 可以选择的工具清单；这是给模型看的工具说明书。";
  if (/TOOL_HANDLERS/.test(code)) return "通过工具名称查找真正负责执行的 Python 函数。";
  if (/block\.type\s*==\s*["']tool_use/.test(code)) return "只处理模型返回内容中的“工具调用”部分。";
  if (/run_bash|read_file|write_file|edit_file|glob/.test(code) && /=/.test(code)) return "调用具体工具，把执行结果保存到左侧变量。";
  if (/^[A-Z_]+\s*=/.test(code)) return "设置一个全局配置值，通常供后面的多个函数共同使用。";
  if (/^[a-zA-Z_]\w*\s*=/.test(code)) return "把右侧计算得到的内容保存到左侧变量，方便后面继续使用。";
  if (/^(print|input)\(/.test(code)) return "和终端用户交互：print 显示文字，input 等待用户输入。";
  if (/^#/.test(code)) return "这是注释，只解释代码，不会被 Python 执行。";
  if (/^[\]\[{}(),]+$/.test(code)) return "结束上方的数据结构或函数调用；它主要用于配对括号。";
  return "执行这一行。先找动词（函数名）和名词（变量名），暂时不用记住全部语法。";
}

function addBeginnerCodeExplanations(html: string): string {
  return html.replace(
    /(<pre class="code-block"[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>)/g,
    (block, _full, codeHtml: string) => {
      const plainCode = decodeHtml(codeHtml.replace(/<[^>]+>/g, ""));
      const lines = plainCode
        .split("\n")
        .map((line) => line.trimEnd())
        .filter((line) => line.trim().length > 0);

      if (lines.length === 0) return block;

      const visibleLines = lines.slice(0, 14);
      const rows = visibleLines
        .map(
          (line, index) =>
            `<li><code>${escapeHtml(line.trim())}</code><span>${escapeHtml(explainPythonLine(line))}</span></li>`
        )
        .join("");
      const remaining = lines.length - visibleLines.length;

      return `${block}<details class="beginner-code-explanation"><summary>看不懂？点这里查看逐句白话翻译</summary><div class="beginner-code-summary">阅读方法：先看每行“做什么”，不要急着背 Python 语法。</div><ol>${rows}</ol>${remaining > 0 ? `<p class="beginner-code-more">后面还有 ${remaining} 行，初学时先掌握上面主干即可。</p>` : ""}</details>`;
    }
  );
}

function postProcessHtml(html: string, locale: string): string {
  // Add language labels to highlighted code blocks
  html = html.replace(
    /<pre><code class="hljs language-(\w+)">/g,
    '<pre class="code-block" data-language="$1"><code class="hljs language-$1">'
  );

  if (locale === "zh") {
    html = addBeginnerCodeExplanations(html);
  }

  // Wrap plain pre>code (ASCII art / diagrams) in diagram container
  html = html.replace(
    /<pre><code(?! class="hljs)([^>]*)>/g,
    '<pre class="ascii-diagram"><code$1>'
  );

  // Keep wide Markdown tables inside the prose column on small screens.
  html = html.replace(/<table>/g, '<div class="table-scroll"><table>');
  html = html.replace(/<\/table>/g, '</table></div>');

  // Mark the first blockquote as hero callout
  html = html.replace(
    /<blockquote>/,
    '<blockquote class="hero-callout">'
  );

  // Remove the h1 (it's redundant with the page header)
  html = html.replace(/<h1>.*?<\/h1>\n?/, "");

  // Fix ordered list counter for interrupted lists (ol start="N")
  html = html.replace(
    /<ol start="(\d+)">/g,
    (_, start) => `<ol style="counter-reset:step-counter ${parseInt(start) - 1}">`
  );

  return html;
}

export function DocRenderer({ version }: DocRendererProps) {
  const locale = useLocale();

  const doc = useMemo(() => {
    const match = docsData.find(
      (d: { version: string; locale: string }) =>
        d.version === version && d.locale === locale
    );
    if (match) return match;
    return docsData.find(
      (d: { version: string; locale: string }) =>
        d.version === version && d.locale === "en"
    );
  }, [version, locale]);

  if (!doc) return null;

  const html = useMemo(() => {
    const raw = renderMarkdown(doc.content);
    return postProcessHtml(raw, locale);
  }, [doc.content, locale]);

  return (
    <div className="py-4">
      <div
        className="prose-custom"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
