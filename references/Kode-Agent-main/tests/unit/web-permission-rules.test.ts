import { beforeEach, describe, expect, test } from 'bun:test'
import { createDefaultToolPermissionContext } from '@kode-types/toolPermissionContext'
import { hasPermissionsToUseTool } from '@permissions'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'
import { WebSearchTool } from '@tools/network/WebSearchTool/WebSearchTool'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

function makeToolUseContext(
  toolPermissionContext: any,
  permissionMode: string = 'default',
) {
  return {
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
      permissionMode,
      toolPermissionContext,
    },
  } as any
}

describe('Web tool permission rules (Reference CLI parity)', () => {
  beforeEach(() => {
    const current = getCurrentProjectConfig()
    saveCurrentProjectConfig({
      ...current,
      allowedTools: [],
      deniedTools: [],
      askedTools: [],
    })
  })

  test('WebFetch uses domain:<hostname> key for valid URLs', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = [
      'WebFetch(domain:example.com)',
    ]

    const result = await hasPermissionsToUseTool(
      WebFetchTool as any,
      { url: 'https://example.com', prompt: '' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(result).toEqual({ result: true })
  })

  test('WebFetch supports wildcard domain rules', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = [
      'WebFetch(domain:*.example.com)',
    ]

    const result = await hasPermissionsToUseTool(
      WebFetchTool as any,
      { url: 'https://api.example.com', prompt: '' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(result).toEqual({ result: true })
  })

  test('WebFetch deny rules override allow rules', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = [
      'WebFetch(domain:*.example.com)',
    ]
    toolPermissionContext.alwaysDenyRules.localSettings = [
      'WebFetch(domain:api.example.com)',
    ]

    const result = await hasPermissionsToUseTool(
      WebFetchTool as any,
      { url: 'https://api.example.com', prompt: '' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(result).toEqual({
      result: false,
      shouldPromptUser: false,
      message: 'Permission to use WebFetch has been denied.',
    })
  })

  test('WebFetch prompts when no rules match', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()

    const result = await hasPermissionsToUseTool(
      WebFetchTool as any,
      { url: 'https://example.com', prompt: '' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
    expect((result as any).message).toContain(
      'requested permissions to use WebFetch',
    )
  })

  test('WebFetch falls back to input:<raw> when schema parsing fails', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = [
      'WebFetch(input:hello)',
    ]

    const result = await hasPermissionsToUseTool(
      WebFetchTool as any,
      'hello' as any,
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(result).toEqual({ result: true })
  })

  test('WebSearch uses query-based keys (WebSearch(<query>)) with WebSearch allow-all fallback', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = [
      'WebSearch(claude ai)',
    ]

    const allowed = await hasPermissionsToUseTool(
      WebSearchTool as any,
      { query: 'claude ai' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(allowed).toEqual({ result: true })

    toolPermissionContext.alwaysAllowRules.localSettings = ['WebSearch']
    const allowAll = await hasPermissionsToUseTool(
      WebSearchTool as any,
      { query: 'some other query' },
      makeToolUseContext(toolPermissionContext),
      {} as any,
    )

    expect(allowAll).toEqual({ result: true })
  })
})
