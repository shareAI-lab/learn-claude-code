import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool, ToolUseContext } from '@tool'
import { queryQuick } from '@services/llmLazy'
import { PROMPT, TOOL_NAME_FOR_PROMPT } from './prompt'
import { convertHtmlToMarkdown } from './htmlToMarkdown'
import { urlCache } from './cache'

const inputSchema = z.strictObject({
  url: z.string().url().describe('The URL to fetch content from'),
  prompt: z.string().describe('The prompt to run on the fetched content'),
})

type Input = z.infer<typeof inputSchema>
type Output = {
  bytes: number
  code: number
  codeText: string
  result: string
  durationMs: number
  url: string
}

const FETCH_TIMEOUT_MS = 30_000
const MAX_URL_LENGTH = 2000
const MAX_RESPONSE_BYTES = 10 * 1024 * 1024
const MAX_CONTENT_CHARS = 100_000

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes)) return `${bytes}B`
  if (bytes < 1024) return `${Math.max(0, Math.round(bytes))}B`
  const units = ['KB', 'MB', 'GB', 'TB'] as const
  let value = bytes / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex++
  }
  const rounded = Math.round(value * 10) / 10
  return `${rounded}${units[unitIndex]}`
}

function normalizeUrl(url: string): string {
  if (url.startsWith('http://')) {
    return url.replace('http://', 'https://')
  }
  return url
}

function normalizeHostname(hostname: string): string {
  return hostname.replace(/^www\./i, '').toLowerCase()
}

function isSameHost(originalUrl: string, redirectUrl: string): boolean {
  try {
    const original = new URL(originalUrl)
    const redirect = new URL(redirectUrl)
    if (redirect.protocol !== original.protocol) return false
    if (redirect.port !== original.port) return false
    if (redirect.username || redirect.password) return false
    return (
      normalizeHostname(original.hostname) ===
      normalizeHostname(redirect.hostname)
    )
  } catch {
    return false
  }
}

function createTimeoutSignal(
  parent: AbortSignal,
  timeoutMs: number,
): {
  signal: AbortSignal
  cleanup: () => void
} {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  if (parent.aborted) {
    controller.abort()
  } else {
    parent.addEventListener('abort', onAbort, { once: true })
  }
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timeout)
      parent.removeEventListener('abort', onAbort)
    },
  }
}

async function readResponseTextLimited(
  response: Response,
  maxBytes: number,
): Promise<{ text: string; bytes: number }> {
  if (!response.body) return { text: '', bytes: 0 }
  const reader = response.body.getReader()
  const chunks: Uint8Array[] = []
  let bytes = 0
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      if (!value) continue
      bytes += value.byteLength
      if (bytes > maxBytes) {
        try {
          await reader.cancel()
        } catch {
        }
        throw new Error(
          `Response exceeded maximum allowed size (${maxBytes} bytes)`,
        )
      }
      chunks.push(value)
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
    }
  }

  const buffer = Buffer.concat(chunks.map(chunk => Buffer.from(chunk)))
  return { text: buffer.toString('utf-8'), bytes }
}

function truncateFetchedContent(content: string): string {
  if (content.length <= MAX_CONTENT_CHARS) return content
  return `${content.substring(0, MAX_CONTENT_CHARS)}...[content truncated]`
}

function isMarkdownHost(url: string, contentType: string): boolean {
  const lowerContentType = contentType.toLowerCase()
  if (lowerContentType.includes('text/markdown')) return true
  try {
    const parsed = new URL(url)
    const host = parsed.hostname.toLowerCase()
    if (
      host === 'raw.githubusercontent.com' ||
      host === 'gist.githubusercontent.com' ||
      host === 'modelcontextprotocol.io' ||
      host === 'github.com'
    ) {
      return true
    }
    const pathname = parsed.pathname.toLowerCase()
    return pathname.endsWith('.md') || pathname.endsWith('.markdown')
  } catch {
    return false
  }
}

function buildWebFetchApplyPrompt(
  content: string,
  prompt: string,
  allowBroaderQuoting: boolean,
): string {
  return `
Web page content:
---
${content}
---

${prompt}

${
  allowBroaderQuoting
    ? 'Provide a concise response based on the content above. Include relevant details, code examples, and documentation excerpts as needed.'
    : `Provide a concise response based only on the content above. In your response:
 - Enforce a strict 125-character maximum for quotes from any source document. Open Source Software is ok as long as we respect the license.
 - Use quotation marks for exact language from articles; any language outside of the quotation should never be word-for-word the same.
 - You are not a lawyer and never comment on the legality of your own prompts and responses.
 - Never produce or reproduce exact song lyrics.`
}
`
}

async function fetchWithRedirectDetection(
  url: string,
  signal: AbortSignal,
): Promise<
  | {
      type: 'redirect'
      originalUrl: string
      redirectUrl: string
      statusCode: number
    }
  | { type: 'response'; response: Response; finalUrl: string }
> {
  let current = url
  for (let i = 0; i < 10; i++) {
    const response = await fetch(current, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; WebFetch/1.0)',
        Accept: 'text/markdown, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.5',
      },
      signal,
      redirect: 'manual',
    })

    if ([301, 302, 307, 308].includes(response.status)) {
      const location = response.headers.get('location')
      if (!location) {
        return { type: 'response', response, finalUrl: current }
      }
      const redirectUrl = new URL(location, current).toString()
      if (isSameHost(current, redirectUrl)) {
        current = redirectUrl
        continue
      }
      return {
        type: 'redirect',
        originalUrl: url,
        redirectUrl,
        statusCode: response.status,
      }
    }

    return { type: 'response', response, finalUrl: current }
  }

  const response = await fetch(current, { signal })
  return { type: 'response', response, finalUrl: current }
}

export const WebFetchTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description(input?: Input) {
    const url = input?.url
    try {
      return `Kode Agent wants to fetch content from ${new URL(url || '').hostname}`
    } catch {
      return 'Kode Agent wants to fetch content from this URL'
    }
  },
  userFacingName: () => 'Fetch',
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
  async validateInput({ url }: Input) {
    if (url.length > MAX_URL_LENGTH) {
      return { result: false, message: 'Invalid URL', errorCode: 1 }
    }
    try {
      const parsed = new URL(url)
      if (parsed.username || parsed.password) {
        return { result: false, message: 'Invalid URL', errorCode: 1 }
      }
      if (parsed.hostname.split('.').length < 2) {
        return { result: false, message: 'Invalid URL', errorCode: 1 }
      }
    } catch {
      return {
        result: false,
        message: `Error: Invalid URL "${url}". The URL provided could not be parsed.`,
        errorCode: 1,
      }
    }
    return { result: true }
  },
  renderToolUseMessage(
    { url, prompt }: Input,
    { verbose }: { verbose: boolean },
  ) {
    if (verbose) {
      return `url: "${url}"${prompt ? `, prompt: "${prompt}"` : ''}`
    }
    return url
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output) {
    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;Received </Text>
          <Text bold>{formatBytes(output.bytes)} </Text>
          <Text>
            ({output.code} {output.codeText})
          </Text>
        </Box>
        <Cost costUSD={0} durationMs={output.durationMs} debug={false} />
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return output.result
  },
  async *call({ url, prompt }: Input, context: ToolUseContext) {
    const normalizedUrl = normalizeUrl(url)
    const start = Date.now()

    const timeoutSignal = createTimeoutSignal(
      context.abortController.signal,
      FETCH_TIMEOUT_MS,
    )

    try {
      const cached = urlCache.get(normalizedUrl)

      const fetched = cached
        ? null
        : await fetchWithRedirectDetection(normalizedUrl, timeoutSignal.signal)

      if (fetched && fetched.type === 'redirect') {
        const codeText =
          fetched.statusCode === 301
            ? 'Moved Permanently'
            : fetched.statusCode === 308
              ? 'Permanent Redirect'
              : fetched.statusCode === 307
                ? 'Temporary Redirect'
                : 'Found'

        const result = `REDIRECT DETECTED: The URL redirects to a different host.

Original URL: ${fetched.originalUrl}
Redirect URL: ${fetched.redirectUrl}
Status: ${fetched.statusCode} ${codeText}

To complete your request, I need to fetch content from the redirected URL. Please use WebFetch again with these parameters:
- url: "${fetched.redirectUrl}"
- prompt: "${prompt}"`

        const output: Output = {
          bytes: Buffer.byteLength(result, 'utf8'),
          code: fetched.statusCode,
          codeText,
          result,
          durationMs: Date.now() - start,
          url: normalizedUrl,
        }
        yield {
          type: 'result' as const,
          resultForAssistant: this.renderResultForAssistant(output),
          data: output,
        }
        return
      }

      let bytes = cached ? cached.bytes : 0
      let code = cached ? cached.code : 200
      let codeText = cached ? cached.codeText : 'OK'
      let markdown = cached ? cached.content : ''
      let contentType = cached ? cached.contentType : ''

      if (fetched && fetched.type === 'response') {
        const response = fetched.response

        code = response.status
        codeText = response.statusText || 'OK'

        contentType = response.headers.get('content-type') || ''

        const { text: raw, bytes: responseBytes } =
          await readResponseTextLimited(response, MAX_RESPONSE_BYTES)
        bytes = responseBytes

        const converted = contentType.toLowerCase().includes('text/html')
          ? convertHtmlToMarkdown(raw)
          : raw
        markdown = truncateFetchedContent(converted)
        urlCache.set(normalizedUrl, {
          bytes,
          code,
          codeText,
          content: markdown,
          contentType,
        })
      }

      const allowBroaderQuoting = isMarkdownHost(normalizedUrl, contentType)
      const userPrompt = buildWebFetchApplyPrompt(
        markdown,
        prompt,
        allowBroaderQuoting,
      )
      const aiResponse = await queryQuick({
        systemPrompt: [],
        userPrompt,
        enablePromptCaching: false,
        signal: timeoutSignal.signal,
      })

      const result =
        aiResponse.message.content[0]?.text || 'No response from model'

      const output: Output = {
        bytes,
        code,
        codeText,
        result,
        durationMs: Date.now() - start,
        url: normalizedUrl,
      }

      yield {
        type: 'result' as const,
        resultForAssistant: this.renderResultForAssistant(output),
        data: output,
      }
    } catch (error: any) {
      const message = error instanceof Error ? error.message : String(error)
      const output: Output = {
        bytes: 0,
        code: 0,
        codeText: '',
        result: `Error processing URL ${normalizedUrl}: ${message}`,
        durationMs: Date.now() - start,
        url: normalizedUrl,
      }
      yield {
        type: 'result' as const,
        resultForAssistant: this.renderResultForAssistant(output),
        data: output,
      }
    } finally {
      timeoutSignal.cleanup()
    }
  },
} satisfies Tool<typeof inputSchema, Output>
