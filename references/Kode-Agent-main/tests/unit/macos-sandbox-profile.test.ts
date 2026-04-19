import { describe, expect, test } from 'bun:test'
import { existsSync } from 'fs'
import { BunShell, buildMacosSandboxExecCommand } from '@utils/bun/shell'
import type { BunShellSandboxOptions } from '@utils/bun/shell'

describe('macOS sandbox-exec profile hardening', () => {
  test('profile allows writing to /dev/null when write-restricted', () => {
    if (process.platform !== 'darwin') return

    const cmd = buildMacosSandboxExecCommand({
      sandboxExecPath: '/usr/bin/sandbox-exec',
      binShellPath: 'bash',
      command: 'echo hi',
      needsNetworkRestriction: false,
      readConfig: { denyOnly: [] },
      writeConfig: { allowOnly: ['.'], denyWithinAllow: [] },
    })

    const profile = cmd[2] as string
    expect(profile).toContain('(literal "/dev/null")')
  })

  test('prefers /usr/bin/sandbox-exec over PATH', () => {
    if (process.platform !== 'darwin') return
    if (!existsSync('/usr/bin/sandbox-exec')) return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const sandbox: BunShellSandboxOptions = {
      enabled: true,
      require: true,
      needsNetworkRestriction: true,
      readConfig: { denyOnly: [] },
      writeConfig: { allowOnly: ['.'], denyWithinAllow: [] },
      __platformOverride: 'darwin',
    }

    const built = (shell as any).buildSandboxCmd('echo hi', sandbox) as {
      cmd: string[]
    } | null
    expect(built).toBeTruthy()
    expect(built!.cmd[0]).toBe('/usr/bin/sandbox-exec')
  })
})
