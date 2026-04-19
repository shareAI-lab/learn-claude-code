import { describe, expect, test } from 'bun:test'
import { hasPermissionsToUseTool } from '@permissions'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { homedir } from 'os'
import { resolve } from 'path'

describe('bypassPermissions safety floor', () => {
  test('denies sensitive writes in bypassPermissions mode', async () => {
    const filePath = resolve(homedir(), '.ssh', 'config')
    const result = await hasPermissionsToUseTool(
      FileWriteTool as any,
      { file_path: filePath, content: 'x' },
      {
        abortController: new AbortController(),
        messageId: undefined,
        readFileTimestamps: {},
        options: { permissionMode: 'bypassPermissions', safeMode: false },
      } as any,
      undefined as any,
    )
    expect(result.result).toBe(false)
    if (result.result !== false) throw new Error('Expected write to be denied')
    expect(result.shouldPromptUser).toBe(false)
    expect(result.message).toContain('sensitive')
  })

  test('allows bypassing the safety floor via env (non-safe mode)', async () => {
    const prev = process.env.KODE_BYPASS_SAFETY_FLOOR
    process.env.KODE_BYPASS_SAFETY_FLOOR = '1'
    try {
      const filePath = resolve(homedir(), '.ssh', 'config')
      const result = await hasPermissionsToUseTool(
        FileWriteTool as any,
        { file_path: filePath, content: 'x' },
        {
          abortController: new AbortController(),
          messageId: undefined,
          readFileTimestamps: {},
          options: { permissionMode: 'bypassPermissions', safeMode: false },
        } as any,
        undefined as any,
      )
      expect(result.result).toBe(true)
    } finally {
      if (prev === undefined) delete process.env.KODE_BYPASS_SAFETY_FLOOR
      else process.env.KODE_BYPASS_SAFETY_FLOOR = prev
    }
  })
})
