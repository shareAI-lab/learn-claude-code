import { beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { createDefaultToolPermissionContext } from '@kode-types/toolPermissionContext'
import { hasPermissionsToUseTool, savePermission } from '@permissions'
import { BashTool } from '@tools/BashTool/BashTool'
import { checkBashPermissions } from '@utils/permissions/bashToolPermissionEngine'
import {
  __resetToolPermissionContextStateForTests,
  setToolPermissionContextForConversationKey,
} from '@utils/permissions/toolPermissionContextState'
import { BunShell } from '@utils/bun/shell'
import { getCwd, setCwd } from '@utils/state'
import { loadToolPermissionContextFromDisk } from '@utils/permissions/toolPermissionSettings'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

function makeToolUseContext(toolPermissionContext: any) {
  return {
    abortController: new AbortController(),
    messageId: 'test-message',
    readFileTimestamps: {},
    options: {
      commands: [],
      tools: [],
      verbose: false,
      safeMode: false,
      forkNumber: 0,
      messageLogName: 'test',
      toolPermissionContext,
    },
  } as any
}

describe('Bash permission dont-ask-again (prefix) parity', () => {
  beforeEach(() => {
    __resetToolPermissionContextStateForTests()
    BunShell.restart()

    const current = getCurrentProjectConfig()
    saveCurrentProjectConfig({
      ...current,
      allowedTools: [],
      deniedTools: [],
      askedTools: [],
    })
  })

  test('prefix allow takes effect immediately in same turn after savePermission()', async () => {
    if (process.platform === 'win32') return

    const originalCwd = getCwd()
    const projectDir = mkdtempSync(join(tmpdir(), 'kode-p024-'))
    await setCwd(projectDir)

    try {
      const toolPermissionContext = createDefaultToolPermissionContext()
      toolPermissionContext.mode = 'default'

      const conversationKey = 'test:0'
      setToolPermissionContextForConversationKey({
        conversationKey,
        context: toolPermissionContext,
      })

      const ctx = makeToolUseContext(toolPermissionContext)

      const input = { command: 'python3 -V' }
      const before = await hasPermissionsToUseTool(
        BashTool as any,
        input,
        ctx,
        {} as any,
      )
      expect(before.result).toBe(false)

      await savePermission(BashTool as any, input as any, 'python3', ctx)

      const after = await hasPermissionsToUseTool(
        BashTool as any,
        input,
        ctx,
        {} as any,
      )
      expect(after).toEqual({ result: true })
      expect(
        ctx.options?.toolPermissionContext?.alwaysAllowRules?.localSettings ??
          [],
      ).toContain('Bash(python3:*)')
    } finally {
      await setCwd(originalCwd)
      rmSync(projectDir, { recursive: true, force: true })
    }
  })

  test('prefix allow persists to .kode/settings.local.json and reloads on restart', async () => {
    if (process.platform === 'win32') return

    const originalCwd = getCwd()
    const projectDir = mkdtempSync(join(tmpdir(), 'kode-p024-'))
    const homeDir = mkdtempSync(join(tmpdir(), 'kode-home-'))
    await setCwd(projectDir)

    try {
      const toolPermissionContext = createDefaultToolPermissionContext()
      toolPermissionContext.mode = 'default'

      const conversationKey = 'test:0'
      setToolPermissionContextForConversationKey({
        conversationKey,
        context: toolPermissionContext,
      })

      const ctx = makeToolUseContext(toolPermissionContext)
      const input = { command: 'python3 -V' }

      await savePermission(BashTool as any, input as any, 'python3', ctx)

      const settingsPath = join(projectDir, '.kode', 'settings.local.json')
      const raw = readFileSync(settingsPath, 'utf-8')
      const parsed = JSON.parse(raw)
      expect(parsed.permissions.allow).toContain('Bash(python3:*)')

      const reloaded = loadToolPermissionContextFromDisk({
        projectDir,
        homeDir,
        includeKodeProjectConfig: false,
        isBypassPermissionsModeAvailable: false,
      })

      const result = await checkBashPermissions({
        command: input.command,
        toolPermissionContext: reloaded,
        toolUseContext: makeToolUseContext(reloaded),
      })
      expect(result).toEqual({ result: true })
    } finally {
      await setCwd(originalCwd)
      rmSync(projectDir, { recursive: true, force: true })
      rmSync(homeDir, { recursive: true, force: true })
    }
  })

  test('prefix allow does not bypass dangerous rm -rf / in compound commands', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext()
    toolPermissionContext.mode = 'default'
    toolPermissionContext.alwaysAllowRules.localSettings = ['Bash(echo:*)']

    const result = await checkBashPermissions({
      command: 'echo ok && rm -rf /',
      toolPermissionContext,
      toolUseContext: makeToolUseContext(toolPermissionContext),
    })

    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
  })
})
