import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import type { Tool, ToolUseContext } from '@tool'
import { getClients } from '@services/mcpClient'
import { ReadResourceResultSchema } from '@modelcontextprotocol/sdk/types.js'
import { DESCRIPTION, PROMPT, TOOL_NAME } from './prompt'

const inputSchema = z.strictObject({
  server: z.string().describe('The MCP server name'),
  uri: z.string().describe('The resource URI to read'),
})

type Input = z.infer<typeof inputSchema>

type Output = {
  contents: Array<{
    uri: string
    mimeType?: string
    text?: string
  }>
}

export const ReadMcpResourceTool = {
  name: TOOL_NAME,
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return PROMPT
  },
  inputSchema,
  userFacingName() {
    return 'readMcpResource'
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
    const clients =
      (context?.options?.mcpClients as any[]) ?? (await getClients())
    const match = clients.find(c => c.name === server)
    if (!match) {
      return {
        result: false,
        message: `Server "${server}" not found. Available servers: ${clients.map(c => c.name).join(', ')}`,
        errorCode: 1,
      }
    }
    if (match.type !== 'connected') {
      return {
        result: false,
        message: `Server "${server}" is not connected`,
        errorCode: 2,
      }
    }
    let capabilities: Record<string, unknown> | null =
      (match as any).capabilities ?? null
    if (!capabilities) {
      try {
        capabilities = match.client.getServerCapabilities() as any
      } catch {
        capabilities = null
      }
    }
    if (!(capabilities as any)?.resources) {
      return {
        result: false,
        message: `Server "${server}" does not support resources`,
        errorCode: 3,
      }
    }
    return { result: true }
  },
  renderToolUseMessage({ server, uri }: Input) {
    if (!server || !uri) return null as any
    return `Read resource "${uri}" from server "${server}"`
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output) {
    const count = output.contents?.length ?? 0
    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
          <Text bold>Read MCP resource</Text>
          <Text>
            {count ? ` (${count} part${count === 1 ? '' : 's'})` : ''}
          </Text>
        </Box>
        <Cost costUSD={0} durationMs={0} debug={false} />
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return JSON.stringify(output)
  },
  async *call({ server, uri }: Input, context: ToolUseContext) {
    const clients =
      (context.options?.mcpClients as any[]) ?? (await getClients())
    const match = clients.find(c => c.name === server)
    if (!match) {
      throw new Error(
        `Server "${server}" not found. Available servers: ${clients.map(c => c.name).join(', ')}`,
      )
    }
    if (match.type !== 'connected') {
      throw new Error(`Server "${server}" is not connected`)
    }
    let capabilities: Record<string, unknown> | null =
      (match as any).capabilities ?? null
    if (!capabilities) {
      try {
        capabilities = match.client.getServerCapabilities() as any
      } catch {
        capabilities = null
      }
    }
    if (!(capabilities as any)?.resources) {
      throw new Error(`Server "${server}" does not support resources`)
    }
    const result = (await match.client.request(
      { method: 'resources/read', params: { uri } },
      ReadResourceResultSchema,
    )) as Output
    yield {
      type: 'result',
      data: result,
      resultForAssistant: this.renderResultForAssistant(result),
    }
  },
} satisfies Tool<typeof inputSchema, Output>
