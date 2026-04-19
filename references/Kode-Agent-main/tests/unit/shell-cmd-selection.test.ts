import { describe, expect, test } from 'bun:test'
import { BunShell } from '@utils/bun/shell'

describe('shell command selection', () => {
  test('win32 uses ComSpec when provided', () => {
    const cmd = BunShell.getShellCmdForPlatform('win32', 'echo hi', {
      ComSpec: 'C:\\Windows\\System32\\cmd.exe',
    } as any)
    expect(cmd[0]).toBe('C:\\Windows\\System32\\cmd.exe')
    expect(cmd.slice(1, 3)).toEqual(['/c', 'echo hi'])
  })

  test('win32 falls back to cmd when ComSpec missing', () => {
    const cmd = BunShell.getShellCmdForPlatform('win32', 'echo hi', {} as any)
    expect(cmd[0]).toBe('cmd')
  })

  test('unix uses /bin/sh when available', () => {
    const cmd = BunShell.getShellCmdForPlatform('darwin', 'echo hi', {} as any)
    expect(cmd[1]).toBe('-c')
    expect(cmd[2]).toBe('echo hi')
  })
})
