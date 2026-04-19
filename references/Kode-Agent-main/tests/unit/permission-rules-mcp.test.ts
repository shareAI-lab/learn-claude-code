import { describe, expect, test, beforeEach } from 'bun:test'
import { hasPermissionsToUseTool } from '@permissions'
import {
  saveCurrentProjectConfig,
  getCurrentProjectConfig,
} from '@utils/config'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'

const makeContext = () => ({
  abortController: new AbortController(),
  messageId: 'test',
  options: {
    commands: [],
    tools: [],
    verbose: false,
    slowAndCapableModel: undefined,
    safeMode: true,
    forkNumber: 0,
    messageLogName: 'test',
    maxThinkingTokens: 0,
  },
  readFileTimestamps: {},
})

function setToolRules(rules: {
  allow?: string[]
  deny?: string[]
  ask?: string[]
}) {
  const current = getCurrentProjectConfig()
  saveCurrentProjectConfig({
    ...current,
    allowedTools: rules.allow ?? [],
    deniedTools: rules.deny ?? [],
    askedTools: rules.ask ?? [],
  })
}

describe('Permission rule matching (MCP + allow/deny/ask)', () => {
  beforeEach(() => {
    setToolRules({ allow: [], deny: [], ask: [] })
  })

  test('deny overrides allow for MCP dynamic tool names', async () => {
    const ctx = makeContext()
    const toolName = 'mcp__srv__tool'
    setToolRules({ allow: [toolName], deny: [toolName] })

    const fakeTool = {
      name: toolName,
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).toBe(false)
  })

  test('ask overrides allow for MCP dynamic tool names', async () => {
    const ctx = makeContext()
    const toolName = 'mcp__srv__tool'
    setToolRules({ allow: [toolName], ask: [toolName] })

    const fakeTool = {
      name: toolName,
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })

  test('MCP permissions do not apply across servers', async () => {
    const ctx = makeContext()
    setToolRules({ allow: ['mcp__srv1__tool'] })

    const fakeTool = {
      name: 'mcp__srv2__tool',
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })

  test('MCP wildcard mcp__server__* allows all tools from that server', async () => {
    const ctx = makeContext()
    setToolRules({ allow: ['mcp__srv__*'] })

    const fakeTool = {
      name: 'mcp__srv__toolA',
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(true)
  })

  test('MCP wildcard does not apply across servers', async () => {
    const ctx = makeContext()
    setToolRules({ allow: ['mcp__srv1__*'] })

    const fakeTool = {
      name: 'mcp__srv2__tool',
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })

  test('deny wildcard overrides allow exact for MCP tools', async () => {
    const ctx = makeContext()
    setToolRules({ allow: ['mcp__srv__tool'], deny: ['mcp__srv__*'] })

    const fakeTool = {
      name: 'mcp__srv__tool',
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).toBe(false)
  })

  test('ask wildcard overrides allow wildcard for MCP tools', async () => {
    const ctx = makeContext()
    setToolRules({ allow: ['mcp__srv__*'], ask: ['mcp__srv__*'] })

    const fakeTool = {
      name: 'mcp__srv__tool',
      needsPermissions() {
        return true
      },
      isReadOnly() {
        return false
      },
    } as any

    const result = await hasPermissionsToUseTool(
      fakeTool,
      {},
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })

  test('deny prefix rules apply to SlashCommand', async () => {
    const ctx = makeContext()
    setToolRules({ deny: ['SlashCommand(/review-pr:*)'] })

    const result = await hasPermissionsToUseTool(
      SlashCommandTool as any,
      { command: '/review-pr 123' },
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).toBe(false)
  })

  test('ask prefix rules override allow for SlashCommand', async () => {
    const ctx = makeContext()
    setToolRules({
      allow: ['SlashCommand(/review-pr:*)'],
      ask: ['SlashCommand(/review-pr:*)'],
    })

    const result = await hasPermissionsToUseTool(
      SlashCommandTool as any,
      { command: '/review-pr 123' },
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })
})
