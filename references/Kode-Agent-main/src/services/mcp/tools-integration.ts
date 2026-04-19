import { zipObject, memoize } from 'lodash-es'
import type { Tool } from '@tool'
import { MCPTool } from '@tools/mcp/MCPTool/MCPTool'
import { logMCPError } from '@utils/log'
import type { Command } from '@commands'
import type {
  ImageBlockParam,
  MessageParam,
  ToolResultBlockParam,
} from '@anthropic-ai/sdk/resources/index.mjs'
import {
  CallToolResultSchema,
  type ClientRequest,
  type ListPromptsResult,
  ListPromptsResultSchema,
  type ListToolsResult,
  ListToolsResultSchema,
  type Result,
  ResultSchema,
} from '@modelcontextprotocol/sdk/types.js'
import { getClients, type WrappedClient } from './client'

type ConnectedClient = Extract<WrappedClient, { type: 'connected' }>

function sanitizeMcpIdentifierPart(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, '_')
}

function getMcpToolTimeoutMs(): number | null {
  const raw = process.env.MCP_TOOL_TIMEOUT
  const parsed = raw ? Number.parseInt(raw, 10) : NaN
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return parsed
}

type TimeoutSignal = { signal: AbortSignal; cleanup: () => void }

function createTimeoutSignal(timeoutMs: number): TimeoutSignal {
  const timeoutFn = (AbortSignal as any)?.timeout
  if (typeof timeoutFn === 'function') {
    return { signal: timeoutFn(timeoutMs) as AbortSignal, cleanup: () => {} }
  }

  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  return { signal: controller.signal, cleanup: () => clearTimeout(id) }
}

function mergeAbortSignals(
  signals: Array<AbortSignal | undefined>,
): { signal: AbortSignal; cleanup: () => void } | null {
  const active = signals.filter((s): s is AbortSignal => !!s)
  if (active.length === 0) return null
  if (active.length === 1) return { signal: active[0]!, cleanup: () => {} }

  const controller = new AbortController()

  const abort = () => {
    try {
      controller.abort()
    } catch {}
  }

  for (const s of active) {
    if (s.aborted) {
      abort()
      return { signal: controller.signal, cleanup: () => {} }
    }
    s.addEventListener('abort', abort, { once: true })
  }

  return { signal: controller.signal, cleanup: () => {} }
}

const IDE_MCP_TOOL_ALLOWLIST = new Set([
  'mcp__ide__executeCode',
  'mcp__ide__getDiagnostics',
])

async function requestAll<
  ResultT extends Result,
  ResultSchemaT extends typeof ResultSchema,
>(
  req: ClientRequest,
  resultSchema: ResultSchemaT,
  requiredCapability: string,
): Promise<{ client: ConnectedClient; result: ResultT }[]> {
  const timeoutMs = getMcpToolTimeoutMs()
  const clients = await getClients()
  const results = await Promise.allSettled(
    clients.map(async client => {
      if (client.type === 'failed') return null

      let timeoutSignal: TimeoutSignal | null = null

      try {
        let capabilities: Record<string, unknown> | null = client.capabilities ?? null

        if (!capabilities) {
          try {
            capabilities = client.client.getServerCapabilities() as any
          } catch {
            capabilities = null
          }
          client.capabilities = capabilities
        }

        if (!(capabilities as any)?.[requiredCapability]) {
          return null
        }

        timeoutSignal = timeoutMs ? createTimeoutSignal(timeoutMs) : null
        const merged = mergeAbortSignals([timeoutSignal?.signal])

        return {
          client,
          result: (await client.client.request(
            req,
            resultSchema,
            merged?.signal ? ({ signal: merged.signal } as any) : undefined,
          )) as ResultT,
        }
      } catch (error) {
        if (client.type === 'connected') {
          logMCPError(
            client.name,
            `Failed to request '${req.method}': ${error instanceof Error ? error.message : String(error)}`,
          )
        }
        return null
      } finally {
        timeoutSignal?.cleanup()
      }
    }),
  )
  return results
    .filter(
      (
        result,
      ): result is PromiseFulfilledResult<{ client: ConnectedClient; result: ResultT } | null> =>
        result.status === 'fulfilled',
    )
    .map(result => result.value)
    .filter((result): result is { client: ConnectedClient; result: ResultT } => result !== null)
}

export const getMCPTools = memoize(async (): Promise<Tool[]> => {
  const toolsList = await requestAll<ListToolsResult, typeof ListToolsResultSchema>(
    {
      method: 'tools/list',
    },
    ListToolsResultSchema,
    'tools',
  )

  return toolsList.flatMap(({ client, result: { tools } }) => {
    const serverPart = sanitizeMcpIdentifierPart(client.name)

    return tools
      .map((tool): Tool | null => {
        const toolPart = sanitizeMcpIdentifierPart(tool.name)
        const name = `mcp__${serverPart}__${toolPart}`

        if (name.startsWith('mcp__ide__') && !IDE_MCP_TOOL_ALLOWLIST.has(name)) {
          return null
        }

        return {
          ...MCPTool,
          name,
          isConcurrencySafe() {
            return tool.annotations?.readOnlyHint ?? false
          },
          isReadOnly() {
            return tool.annotations?.readOnlyHint ?? false
          },
          async description() {
            return tool.description ?? ''
          },
          async prompt() {
            return tool.description ?? ''
          },
          inputJSONSchema: tool.inputSchema as Tool['inputJSONSchema'],
          async validateInput() {
            return { result: true }
          },
          async *call(args: Record<string, unknown>, context) {
            const data = await callMCPTool({
              client,
              tool: tool.name,
              args,
              toolUseId: context.toolUseId,
              signal: context.abortController.signal,
            })
            yield {
              type: 'result' as const,
              data,
              resultForAssistant: data,
            }
          },
          userFacingName() {
            const title = tool.annotations?.title || tool.name
            return `${client.name} - ${title} (MCP)`
          },
        }
      })
      .filter((tool): tool is Tool => tool !== null)
  })
})

async function callMCPTool({
  client: { client, name },
  tool,
  args,
  toolUseId,
  signal,
}: {
  client: ConnectedClient
  tool: string
  args: Record<string, unknown>
  toolUseId?: string
  signal?: AbortSignal
}): Promise<ToolResultBlockParam['content']> {
  const timeoutMs = getMcpToolTimeoutMs()
  const timeoutSignal = timeoutMs ? createTimeoutSignal(timeoutMs) : null
  const merged = mergeAbortSignals([signal, timeoutSignal?.signal])

  const meta =
    toolUseId && toolUseId.trim()
      ? { 'claudecode/toolUseId': toolUseId }
      : undefined

  try {
    const result = await client.callTool(
      {
        name: tool,
        arguments: args,
        ...(meta ? { _meta: meta } : {}),
      },
      CallToolResultSchema,
      merged?.signal ? ({ signal: merged.signal } as any) : undefined,
    )

    if ('isError' in result && result.isError) {
      const contentText =
        'content' in result && Array.isArray(result.content)
          ? result.content.find(item => item.type === 'text' && 'text' in item)
          : null

      const rawMessage =
        contentText && typeof (contentText as any).text === 'string'
          ? String((contentText as any).text)
          : 'error' in result && result.error
            ? String(result.error)
            : ''

      const message = rawMessage || `Error calling tool ${tool}`
      logMCPError(name, `Error calling tool ${tool}: ${message}`)
      throw new Error(message)
    }

    if ('toolResult' in result) {
      return String(result.toolResult)
    }

    if ('structuredContent' in result && result.structuredContent !== undefined) {
      return JSON.stringify(result.structuredContent)
    }

    if ('content' in result && Array.isArray(result.content)) {
      return result.content.map(item => {
        if (item.type === 'image') {
          return {
            type: 'image',
            source: {
              type: 'base64',
              data: String(item.data),
              media_type: item.mimeType as ImageBlockParam.Source['media_type'],
            },
          }
        }
        return item
      })
    }

    throw Error(`Unexpected response format from tool ${tool}`)
  } finally {
    timeoutSignal?.cleanup()
  }
}

export const getMCPCommands = memoize(async (): Promise<Command[]> => {
  const results = await requestAll<ListPromptsResult, typeof ListPromptsResultSchema>(
    {
      method: 'prompts/list',
    },
    ListPromptsResultSchema,
    'prompts',
  )

  return results.flatMap(({ client, result }) =>
    result.prompts?.map(_ => {
      const serverPart = sanitizeMcpIdentifierPart(client.name)
      const argNames = Object.values(_.arguments ?? {}).map(k => k.name)
      return {
        type: 'prompt',
        name: `mcp__${serverPart}__${_.name}`,
        description: _.description ?? '',
        isEnabled: true,
        isHidden: false,
        progressMessage: 'running',
        userFacingName() {
          const title = typeof (_ as any).title === 'string' ? (_ as any).title : _.name
          return `${client.name}:${title} (MCP)`
        },
        argNames,
        async getPromptForCommand(args: string) {
          const argsArray = args.split(' ')
          return await runCommand({ name: _.name, client }, zipObject(argNames, argsArray))
        },
      } satisfies Command
    }),
  )
})

export async function runCommand(
  { name, client }: { name: string; client: ConnectedClient },
  args: Record<string, string>,
): Promise<MessageParam[]> {
  try {
    const result = await client.client.getPrompt({ name, arguments: args })
    return result.messages.map((message): MessageParam => {
      const content = message.content
      if (content.type === 'text') {
        return {
          role: message.role,
          content: [
            {
              type: 'text',
              text: content.text,
            },
          ],
        }
      }
      if (content.type === 'image' && 'data' in content) {
        return {
          role: message.role,
          content: [
            {
              type: 'image',
              source: {
                data: String((content as any).data),
                media_type: (content as any).mimeType as ImageBlockParam.Source['media_type'],
                type: 'base64',
              },
            },
          ],
        }
      }
      return {
        role: message.role,
        content: [
          {
            type: 'text',
            text: `Unsupported MCP content type ${(content as any)?.type ?? 'unknown'}`,
          },
        ],
      }
    })
  } catch (error) {
    logMCPError(
      client.name,
      `Error running command '${name}': ${error instanceof Error ? error.message : String(error)}`,
    )
    throw error
  }
}

