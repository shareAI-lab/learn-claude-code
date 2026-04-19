import { parse } from 'node-html-parser'

export interface SearchResult {
  title: string
  snippet: string
  link: string
}

export interface SearchProvider {
  search: (query: string, apiKey?: string) => Promise<SearchResult[]>
  isEnabled: (apiKey?: string) => boolean
}

const duckDuckGoSearchProvider: SearchProvider = {
  isEnabled: () => true,
  search: async (query: string): Promise<SearchResult[]> => {
    const response = await fetch(
      `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`,
      {
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
      },
    )

    if (!response.ok) {
      throw new Error(
        `DuckDuckGo search failed with status: ${response.status}`,
      )
    }

    const html = await response.text()
    const root = parse(html)
    const results: SearchResult[] = []

    const resultNodes = root.querySelectorAll('.result.web-result')

    for (const node of resultNodes) {
      const titleNode = node.querySelector('.result__a')
      const snippetNode = node.querySelector('.result__snippet')

      if (titleNode && snippetNode) {
        const title = titleNode.text
        const link = titleNode.getAttribute('href')
        const snippet = snippetNode.text

        if (title && link && snippet) {
          let cleanLink = link
          if (link.startsWith('https://duckduckgo.com/l/?uddg=')) {
            try {
              const url = new URL(link)
              cleanLink = url.searchParams.get('uddg') || link
            } catch {
              cleanLink = link
            }
          }
          results.push({
            title: title.trim(),
            snippet: snippet.trim(),
            link: cleanLink,
          })
        }
      }
    }

    return results
  },
}

export const searchProviders = {
  duckduckgo: duckDuckGoSearchProvider,
}
