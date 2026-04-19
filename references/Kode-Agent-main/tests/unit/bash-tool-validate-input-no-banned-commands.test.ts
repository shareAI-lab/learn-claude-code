import { describe, expect, test } from 'bun:test'
import { createDefaultToolPermissionContext } from '@kode-types/toolPermissionContext'
import { hasPermissionsToUseTool } from '@permissions'
import { BashTool } from '@tools/BashTool/BashTool'

describe('BashTool validateInput does not hard-ban base commands (Reference CLI parity)', () => {
  test('validateInput allows curl/wget/nc; permissions still gate execution', async () => {
    const curlInput = { command: 'curl https://example.com' }
    const wgetInput = { command: 'wget https://example.com' }
    const ncInput = { command: 'nc -vz example.com 443' }

    expect((await BashTool.validateInput!(curlInput as any)).result).toBe(true)
    expect((await BashTool.validateInput!(wgetInput as any)).result).toBe(true)
    expect((await BashTool.validateInput!(ncInput as any)).result).toBe(true)

    const toolPermissionContext = createDefaultToolPermissionContext()
    const toolUseContext: any = {
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
        permissionMode: 'default',
        toolPermissionContext,
      },
    }

    const permission = await hasPermissionsToUseTool(
      BashTool as any,
      curlInput as any,
      toolUseContext,
      {} as any,
    )
    expect(permission.result).toBe(false)
    expect((permission as any).shouldPromptUser).not.toBe(false)
    expect((permission as any).message).toContain(
      'requested permissions to use Bash',
    )
  })
})
