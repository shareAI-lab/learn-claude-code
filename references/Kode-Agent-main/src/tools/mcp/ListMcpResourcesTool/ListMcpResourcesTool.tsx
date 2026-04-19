import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import type { Tool, ToolUseContext } from '@tool'
import { getClients } from '@services/mcpClient'
import { ListResourcesResultSchema } from '@modelcontextprotocol/sdk/types.js'
import { DESCRIPTION, PROMPT, TOOL_NAME } from './prompt'

const inputSchema = z.strictObject({
  server: z
    .string()
    .optional()
    .describe('Optional server name to filter resources by'),
})

type Input = z.infer<typeof inputSchema>

type OutputItem = {
  uri: string
  name: string
  mimeType?: string
  description?: string
  server: string
}

type Output = OutputItem[]

export const ListMcpResourcesTool = {
  name: TOOL_NAME,
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return PROMPT
  },
  inputSchema,
  userFacingName() {
    return 'listMcpResources'
  },
  async isEnabled() {
    return true
  },
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  needsPermissions() {
    return false
  },
  async validateInput({ server }: Input, context?: ToolUseContext) {
    if (!server) return { result: true }
    const clients =
      (context?.options?.mcpClients as any[]) ?? (await getClients())
    const found = clients.some(c => c.name === server)
    if (!found) {
      return {
        result: false,
        message: `Server "${server}" not found. Available servers: ${clients.map(c => c.name).join(', ')}`,
        errorCode: 1,
      }
    }
    return { result: true }
  },
  renderToolUseMessage({ server }: Input) {
    return server
      ? `List MCP resources from server "${server}"`
      : 'List all MCP resources'
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output) {
    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
          <Text bold>{output.length}</Text>
          <Text> resources</Text>
        </Box>
        <Cost costUSD={0} durationMs={0} debug={false} />
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return JSON.stringify(output)
  },
  async *call({ server }: Input, context: ToolUseContext) {
    const clients =
      (context.options?.mcpClients as any[]) ?? (await getClients())
    const selected = server ? clients.filter(c => c.name === server) : clients
    if (server && selected.length === 0) {
      throw new Error(
        `Server "${server}" not found. Available servers: ${clients.map(c => c.name).join(', ')}`,
      )
    }

    const resources: OutputItem[] = []
    for (const wrapped of selected) {
      if (wrapped.type !== 'connected') continue
      try {
        let capabilities: Record<string, unknown> | null =
          (wrapped as any).capabilities ?? null
        if (!capabilities) {
          try {
            capabilities = wrapped.client.getServerCapabilities() as any
          } catch {
            capabilities = null
          }
        }
        if (!(capabilities as any)?.resources) continue
        const result = await wrapped.client.request(
          { method: 'resources/list' },
          ListResourcesResultSchema,
        )
        if (!result.resources) continue
        resources.push(
          ...result.resources.map(r => ({
            ...r,
            server: wrapped.name,
          })),
        )
      } catch {
      }
    }

    yield {
      type: 'result',
      data: resources,
      resultForAssistant: this.renderResultForAssistant(resources),
    }
  },
} satisfies Tool<typeof inputSchema, Output>
