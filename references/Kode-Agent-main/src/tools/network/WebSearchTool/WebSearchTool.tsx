import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool, ToolUseContext } from '@tool'
import { PROMPT, TOOL_NAME_FOR_PROMPT } from './prompt'
import { searchProviders } from './searchProviders'

const inputSchema = z.strictObject({
  query: z.string().min(2).describe('The search query to use'),
  allowed_domains: z
    .array(z.string())
    .optional()
    .describe('Only include search results from these domains'),
  blocked_domains: z
    .array(z.string())
    .optional()
    .describe('Never include search results from these domains'),
})

type Input = z.infer<typeof inputSchema>

type WebSearchHit = {
  title: string
  url: string
}

type WebSearchResultBlock = {
  tool_use_id: string
  content: WebSearchHit[]
}

type Output = {
  query: string
  results: Array<WebSearchResultBlock | string>
  durationSeconds: number
}

function hostnameForUrl(url: string): string | null {
  try {
    return new URL(url).hostname
  } catch {
    return null
  }
}

function summarizeResults(results: Output['results']): {
  searchCount: number
  totalResultCount: number
} {
  let searchCount = 0
  let totalResultCount = 0
  for (const item of results) {
    if (typeof item === 'string') continue
    searchCount += 1
    totalResultCount += item.content.length
  }
  return { searchCount, totalResultCount }
}

export const WebSearchTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description(input?: Input) {
    const query = input?.query ?? ''
    return `Requesting web search for: ${query}`
  },
  userFacingName: () => 'Web Search',
  inputSchema,
  isReadOnly: () => true,
  isConcurrencySafe: () => true,
  async isEnabled() {
    return true
  },
  needsPermissions() {
    return true
  },
  async prompt() {
    return PROMPT
  },
  renderToolUseMessage(
    { query, allowed_domains, blocked_domains }: Input,
    { verbose }: { verbose: boolean },
  ) {
    let summary = `"${query}"`
    if (verbose) {
      if (allowed_domains && allowed_domains.length > 0) {
        summary += `, only allowing domains: ${allowed_domains.join(', ')}`
      }
      if (blocked_domains && blocked_domains.length > 0) {
        summary += `, blocking domains: ${blocked_domains.join(', ')}`
      }
    }
    return summary
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output) {
    const { searchCount } = summarizeResults(output.results)
    const duration =
      output.durationSeconds >= 1
        ? `${Math.round(output.durationSeconds)}s`
        : `${Math.round(output.durationSeconds * 1000)}ms`
    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;Did </Text>
          <Text bold>{searchCount} </Text>
          <Text>
            search{searchCount === 1 ? '' : 'es'} in {duration}
          </Text>
        </Box>
        <Cost
          costUSD={0}
          durationMs={output.durationSeconds * 1000}
          debug={false}
        />
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    let result = `Web search results for query: "${output.query}"\n\n`
    for (const item of output.results) {
      if (typeof item === 'string') {
        result += `${item}\n\n`
        continue
      }
      if (item.content.length > 0) {
        result += `Links: ${JSON.stringify(item.content)}\n\n`
      } else {
        result += `No links found.\n\n`
      }
    }
    result +=
      '\nREMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.'
    return result.trim()
  },
  async validateInput(input: Input) {
    if (!input.query || !input.query.length) {
      return {
        result: false,
        message: 'Error: Missing query',
        errorCode: 1,
      }
    }

    if (input.allowed_domains?.length && input.blocked_domains?.length) {
      return {
        result: false,
        message:
          'Error: Cannot specify both allowed_domains and blocked_domains in the same request',
        errorCode: 2,
      }
    }
    return { result: true }
  },
  async *call(
    { query, allowed_domains, blocked_domains }: Input,
    {}: ToolUseContext,
  ) {
    const start = Date.now()

    try {
      const rawResults = await searchProviders.duckduckgo.search(query)

      const allowed = allowed_domains?.map(d => d.toLowerCase()) ?? null
      const blocked = blocked_domains?.map(d => d.toLowerCase()) ?? null

      const results = rawResults.filter(result => {
        const host = hostnameForUrl(result.link)?.toLowerCase()
        if (!host) return false
        if (allowed && allowed.length > 0) {
          return allowed.some(
            domain => host === domain || host.endsWith(`.${domain}`),
          )
        }
        if (blocked && blocked.length > 0) {
          return !blocked.some(
            domain => host === domain || host.endsWith(`.${domain}`),
          )
        }
        return true
      })

      const hits: WebSearchHit[] = results.map(item => ({
        title: item.title,
        url: item.link,
      }))

      const output: Output = {
        query,
        results: [
          {
            tool_use_id: 'duckduckgo',
            content: hits,
          },
        ],
        durationSeconds: (Date.now() - start) / 1000,
      }

      yield {
        type: 'result' as const,
        resultForAssistant: this.renderResultForAssistant(output),
        data: output,
      }
    } catch (error: any) {
      const output: Output = {
        query,
        results: [
          `Web search error: ${error instanceof Error ? error.message : String(error)}`,
        ],
        durationSeconds: (Date.now() - start) / 1000,
      }
      yield {
        type: 'result' as const,
        resultForAssistant: this.renderResultForAssistant(output),
        data: output,
      }
    }
  },
} satisfies Tool<typeof inputSchema, Output>
