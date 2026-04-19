import { describe, expect, test } from 'bun:test'
import { ListMcpResourcesTool } from '@tools/mcp/ListMcpResourcesTool/ListMcpResourcesTool'
import { ReadMcpResourceTool } from '@tools/mcp/ReadMcpResourceTool/ReadMcpResourceTool'

const makeContext = (mcpClients: any[]) => ({
  abortController: new AbortController(),
  messageId: 'test',
  readFileTimestamps: {},
  options: {
    commands: [],
    tools: [],
    verbose: false,
    safeMode: false,
    forkNumber: 0,
    messageLogName: 'test',
    maxThinkingTokens: 0,
    mcpClients,
  },
})

describe('MCP resource tools parity: use context.options.mcpClients', () => {
  test('ListMcpResourcesTool lists resources from connected clients in context', async () => {
    const fakeClient = {
      request: async () => ({
        resources: [{ uri: 'uri://one', name: 'one' }],
      }),
      getServerCapabilities: () => ({ resources: { listChanged: true } }),
    }

    const ctx = makeContext([
      {
        type: 'connected',
        name: 'srv',
        capabilities: { resources: { listChanged: true } },
        client: fakeClient,
      },
    ])

    const gen = ListMcpResourcesTool.call({} as any, ctx as any)
    const first = await gen.next()
    expect((first.value as any)?.type).toBe('result')
    const data = (first.value as any).data as any[]
    expect(data).toHaveLength(1)
    expect(data[0]).toMatchObject({
      uri: 'uri://one',
      name: 'one',
      server: 'srv',
    })
  })

  test('ReadMcpResourceTool reads resources using context.options.mcpClients', async () => {
    const fakeClient = {
      request: async () => ({
        contents: [{ uri: 'uri://one', text: 'hello' }],
      }),
      getServerCapabilities: () => ({ resources: { listChanged: true } }),
    }

    const ctx = makeContext([
      {
        type: 'connected',
        name: 'srv',
        capabilities: { resources: { listChanged: true } },
        client: fakeClient,
      },
    ])

    const gen = ReadMcpResourceTool.call(
      { server: 'srv', uri: 'uri://one' } as any,
      ctx as any,
    )
    const first = await gen.next()
    expect((first.value as any)?.type).toBe('result')
    expect((first.value as any).data).toMatchObject({
      contents: [{ uri: 'uri://one', text: 'hello' }],
    })
  })
})
