// @ts-nocheck
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import {
  CallToolRequestSchema,
  CallToolResultSchema,
  ListToolsRequestSchema,
  ListToolsResultSchema,
} from '@modelcontextprotocol/sdk/types.js'
import { z, ZodTypeAny } from 'zod'
import { zodToJsonSchema } from 'zod-to-json-schema'
import { hasPermissionsToUseTool } from '@permissions'
import { setCwd } from '@utils/state'
import { getModelManager } from '@utils/model'
import { logError } from '@utils/log'
import { Tool, getToolDescription } from '@tool'
import { getAllTools } from '@tools'
import { Command } from '@commands'
import review from '@commands/review'
import { lastX } from '@utils/text/generators'
import { MACRO } from '@constants/macros'
type ToolInput = Record<string, unknown>

const state: {
  readFileTimestamps: Record<string, number>
} = {
  readFileTimestamps: {},
}

const MCP_COMMANDS: Command[] = [review]

const MCP_TOOLS: Tool[] = [...getAllTools()]

export async function startMCPServer(cwd: string): Promise<void> {
  await setCwd(cwd)
  const server = new Server(
    {
      name: 'claude/tengu',
      version: MACRO.VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    },
  )

  server.setRequestHandler(
    ListToolsRequestSchema,
    async (): Promise<z.infer<typeof ListToolsResultSchema>> => {
      const tools = await Promise.all(
        MCP_TOOLS.map(async tool => ({
          ...(tool as any),
          description: getToolDescription(tool),
          inputSchema: zodToJsonSchema(
            tool.inputSchema as unknown as z.ZodTypeAny,
          ) as ToolInput,
        })),
      )

      return {
        tools,
      }
    },
  )

  server.setRequestHandler(
    CallToolRequestSchema,
    async (request): Promise<z.infer<typeof CallToolResultSchema>> => {
      const { name, arguments: args } = request.params
      const tool = MCP_TOOLS.find(_ => _.name === name)
      if (!tool) {
        throw new Error(`Tool ${name} not found`)
      }

      try {
        if (!(await tool.isEnabled())) {
          throw new Error(`Tool ${name} is not enabled`)
        }
        const model = getModelManager().getModelName('main')
        const validationResult = await tool.validateInput?.(
          (args as never) ?? {},
          {
            abortController: new AbortController(),
            options: {
              commands: MCP_COMMANDS,
              tools: MCP_TOOLS,
              forkNumber: 0,
              messageLogName: 'unused',
              maxThinkingTokens: 0,
            },
            messageId: undefined,
            readFileTimestamps: state.readFileTimestamps,
          } as any,
        )
        if (validationResult && !validationResult.result) {
          throw new Error(
            `Tool ${name} input is invalid: ${validationResult.message}`,
          )
        }
        const result = tool.call((args ?? {}) as never, {
          abortController: new AbortController(),
          messageId: undefined,
          options: {
            commands: MCP_COMMANDS,
            tools: MCP_TOOLS,
            forkNumber: 0,
            messageLogName: 'unused',
            maxThinkingTokens: 0,
          },
          readFileTimestamps: state.readFileTimestamps,
        })

        const finalResult = await lastX(result)

        if (finalResult.type !== 'result') {
          throw new Error(`Tool ${name} did not return a result`)
        }

        return {
          content: Array.isArray(finalResult)
            ? finalResult.map(item => ({
                type: 'text' as const,
                text: 'text' in item ? item.text : JSON.stringify(item),
              }))
            : [
                {
                  type: 'text' as const,
                  text:
                    typeof finalResult === 'string'
                      ? finalResult
                      : JSON.stringify(finalResult.data),
                },
              ],
        }
      } catch (error) {
        logError(error)
        return {
          isError: true,
          content: [
            {
              type: 'text',
              text: `Error: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
        }
      }
    },
  )

  async function runServer() {
    const transport = new StdioServerTransport()
    await server.connect(transport)
  }

  return await runServer()
}
// @ts-nocheck
