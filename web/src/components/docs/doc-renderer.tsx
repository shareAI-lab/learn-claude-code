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
  version?: string;
  slug?: string;
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

function postProcessHtml(html: string): string {
  // Add language labels to highlighted code blocks
  html = html.replace(
    /<pre><code class="hljs language-(\w+)">/g,
    '<pre class="code-block" data-language="$1"><code class="hljs language-$1">'
  );

  // Wrap plain pre>code (ASCII art / diagrams) in diagram container
  html = html.replace(
    /<pre><code(?! class="hljs)([^>]*)>/g,
    '<pre class="ascii-diagram"><code$1>'
  );

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

  // Wrap markdown tables so wide teaching maps scroll locally instead of
  // stretching the whole doc page.
  html = html.replace(/<table>/g, '<div class="table-scroll"><table>');
  html = html.replace(/<\/table>/g, "</table></div>");

  return html;
}

export function DocRenderer({ version, slug }: DocRendererProps) {
  const locale = useLocale();

  const doc = useMemo(() => {
    if (!version && !slug) return null;

    const match = docsData.find(
      (d: { version?: string | null; slug?: string; locale: string; kind?: string }) =>
        (version ? d.version === version && d.kind === "chapter" : d.slug === slug) &&
        d.locale === locale
    );
    if (match) return match;
    const zhFallback = docsData.find(
      (d: { version?: string | null; slug?: string; locale: string; kind?: string }) =>
        (version ? d.version === version && d.kind === "chapter" : d.slug === slug) &&
        d.locale === "zh"
    );
    if (zhFallback) return zhFallback;
    return docsData.find(
      (d: { version?: string | null; slug?: string; locale: string; kind?: string }) =>
        (version ? d.version === version && d.kind === "chapter" : d.slug === slug) &&
        d.locale === "en"
    );
  }, [version, slug, locale]);

  if (!doc) return null;

  const html = useMemo(() => {
    const raw = renderMarkdown(doc.content);
    return postProcessHtml(raw);
  }, [doc.content]);

  return (
    <div className="py-4">
      <div
        className="prose-custom"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
