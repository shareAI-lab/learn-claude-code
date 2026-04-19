import TurndownService from 'turndown'

const turndownService = new TurndownService({
  headingStyle: 'atx',
  hr: '---',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced',
  fence: '```',
  emDelimiter: '_',
  strongDelimiter: '**',
})

turndownService.addRule('removeScripts', {
  filter: ['script', 'style', 'noscript'],
  replacement: () => '',
})

turndownService.addRule('removeComments', {
  filter: node => node.nodeType === 8,
  replacement: () => '',
})

turndownService.addRule('cleanLinks', {
  filter: 'a',
  replacement: (content, node) => {
    const href = node.getAttribute('href')
    if (!href || href.startsWith('javascript:') || href.startsWith('#')) {
      return content
    }
    return `[${content}](${href})`
  },
})

export function convertHtmlToMarkdown(html: string): string {
  try {
    const cleanHtml = html
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/\s+/g, ' ')
      .trim()

    const markdown = turndownService.turndown(cleanHtml)

    return markdown
      .replace(/\n{3,}/g, '\n\n')
      .replace(/^\s+|\s+$/gm, '')
      .trim()
  } catch (error) {
    throw new Error(
      `Failed to convert HTML to markdown: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}
