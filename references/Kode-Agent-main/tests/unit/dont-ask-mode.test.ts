import { describe, expect, test, beforeEach } from 'bun:test'
import { hasPermissionsToUseTool } from '@permissions'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

const makeContext = (permissionMode: string) => ({
  abortController: new AbortController(),
  messageId: 'test',
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
  readFileTimestamps: {},
})

describe('dontAsk permission mode', () => {
  beforeEach(() => {
    const current = getCurrentProjectConfig()
    saveCurrentProjectConfig({
      ...current,
      allowedTools: [],
      deniedTools: [],
      askedTools: [],
    })
  })

  test('auto-denies promptable tool uses', async () => {
    const ctx = makeContext('dontAsk')
    const fakeTool = {
      name: 'FakeTool',
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

    expect(result).toEqual({
      result: false,
      shouldPromptUser: false,
      message:
        'Permission to use FakeTool has been auto-denied in dontAsk mode.',
    })
  })
})
