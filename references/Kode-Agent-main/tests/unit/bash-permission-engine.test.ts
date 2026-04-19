import { describe, expect, test, beforeEach } from 'bun:test'
import { createDefaultToolPermissionContext } from '@kode-types/toolPermissionContext'
import { checkBashPermissions } from '@utils/permissions/bashToolPermissionEngine'
import { hasPermissionsToUseTool } from '@permissions'
import { BashTool } from '@tools/BashTool/BashTool'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

function makeToolUseContext(permissionMode: string = 'default') {
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
    },
  } as any
}

describe('Bash permission engine parity', () => {
  beforeEach(() => {
    const current = getCurrentProjectConfig()
    saveCurrentProjectConfig({
      ...current,
      allowedTools: [],
      deniedTools: [],
      askedTools: [],
    })
  })

  test('allows when prefix rule matches single command', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = ['Bash(git:*)']

    const result = await checkBashPermissions({
      command: 'git status',
      toolPermissionContext,
      toolUseContext: makeToolUseContext(),
    })

    expect(result).toEqual({ result: true })
  })

  test('deny overrides allow (exact deny beats prefix allow)', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = ['Bash(git:*)']
    toolPermissionContext.alwaysDenyRules.localSettings = ['Bash(git status)']

    const result = await checkBashPermissions({
      command: 'git status',
      toolPermissionContext,
      toolUseContext: makeToolUseContext(),
    })

    expect(result).toEqual({
      result: false,
      message:
        'Permission to use Bash with command git status has been denied.',
      shouldPromptUser: false,
    })
  })

  test('ask overrides allow', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.alwaysAllowRules.localSettings = ['Bash(git:*)']
    toolPermissionContext.alwaysAskRules.localSettings = ['Bash(git status)']

    const result = await checkBashPermissions({
      command: 'git status',
      toolPermissionContext,
      toolUseContext: makeToolUseContext(),
    })

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })

  test('command injection check requires approval', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()

    const result = await checkBashPermissions({
      command: 'echo $(id)',
      toolPermissionContext,
      toolUseContext: makeToolUseContext(),
    })

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
    expect((result as any).message).toContain('$()')
  })

  test('dontAsk mode auto-denies promptable bash tool use', async () => {
    const ctx = makeToolUseContext('dontAsk')
    const result = await hasPermissionsToUseTool(
      BashTool as any,
      { command: 'echo hi' },
      ctx,
      {} as any,
    )

    expect(result).toEqual({
      result: false,
      shouldPromptUser: false,
      message: 'Permission to use Bash has been auto-denied in dontAsk mode.',
    })
  })
})
