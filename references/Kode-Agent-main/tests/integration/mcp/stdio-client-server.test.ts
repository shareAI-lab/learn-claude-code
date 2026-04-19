import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { join } from 'path'
import {
  getClients,
  getMCPCommands,
  getMCPTools,
  type WrappedClient,
} from '@services/mcpClient'
import { getCurrentProjectConfig, saveCurrentProjectConfig } from '@utils/config'

describe('MCP stdio integration (SDK)', () => {
  const originalTimeout = process.env.MCP_CONNECTION_TIMEOUT_MS
  const originalToolTimeout = process.env.MCP_TOOL_TIMEOUT

  const fixturePath = join(
    process.cwd(),
    'tests',
    'fixtures',
    'mcp',
    'stdio-echo-server.ts',
  )

  let originalProjectConfig: any
  let createdClients: WrappedClient[] | null = null

  beforeEach(() => {
    originalProjectConfig = JSON.parse(JSON.stringify(getCurrentProjectConfig()))
    process.env.MCP_CONNECTION_TIMEOUT_MS = '3000'
    process.env.MCP_TOOL_TIMEOUT = '3000'

    saveCurrentProjectConfig({
      ...getCurrentProjectConfig(),
      mcpServers: {
        fixture: {
          type: 'stdio',
          command: process.execPath,
          args: [fixturePath],
          env: {},
        },
      },
    })

    ;(getClients as any).cache?.clear?.()
    ;(getMCPTools as any).cache?.clear?.()
    ;(getMCPCommands as any).cache?.clear?.()
  })

  afterEach(async () => {
    if (createdClients) {
      for (const client of createdClients) {
        if (client.type !== 'connected') continue
        try {
          await client.client.close()
        } catch {}
      }
    }

    createdClients = null
    ;(getClients as any).cache?.clear?.()
    ;(getMCPTools as any).cache?.clear?.()
    ;(getMCPCommands as any).cache?.clear?.()

    saveCurrentProjectConfig(originalProjectConfig)

    if (originalTimeout === undefined) delete process.env.MCP_CONNECTION_TIMEOUT_MS
    else process.env.MCP_CONNECTION_TIMEOUT_MS = originalTimeout

    if (originalToolTimeout === undefined) delete process.env.MCP_TOOL_TIMEOUT
    else process.env.MCP_TOOL_TIMEOUT = originalToolTimeout
  })

  test('connects and exposes tools/prompts with stable names', async () => {
    const clients = await getClients()
    createdClients = clients

    const fixtureClient = clients.find(c => c.name === 'fixture')
    expect(fixtureClient?.type).toBe('connected')
    expect((fixtureClient as any)?.capabilities).toBeTruthy()

    const tools = await getMCPTools()
    const echoTool = tools.find(t => t.name === 'mcp__fixture__echo')
    expect(echoTool).toBeDefined()
    expect((echoTool as any).inputJSONSchema).toBeTruthy()

    const ctx = { abortController: new AbortController(), toolUseId: 't1' } as any
    const gen = (echoTool as any).call({ message: 'hi' }, ctx)
    const first = await gen.next()
    expect((first.value as any)?.type).toBe('result')
    expect(String((first.value as any).data)).toContain('hi')

    const commands = await getMCPCommands()
    const hello = commands.find(c => c.name === 'mcp__fixture__hello')
    expect(hello).toBeDefined()

    const promptMessages = await (hello as any).getPromptForCommand('Alice')
    expect(promptMessages[0]?.content?.[0]?.type).toBe('text')
    expect(promptMessages[0]?.content?.[0]?.text).toContain('Hello, Alice!')
  })
})

