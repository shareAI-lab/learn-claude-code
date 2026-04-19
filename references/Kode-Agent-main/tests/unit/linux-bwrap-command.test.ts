import { describe, expect, test } from 'bun:test'
import { mkdirSync } from 'fs'
import { buildLinuxBwrapCommand } from '@utils/bun/shell'

describe('Linux bwrap command construction', () => {
  test('includes /tmp/kode bind + TMPDIR env when write-restricted', () => {
    try {
      mkdirSync('/tmp/kode', { recursive: true })
    } catch {}

    const cmd = buildLinuxBwrapCommand({
      bwrapPath: '/usr/bin/bwrap',
      command: 'echo hi',
      needsNetworkRestriction: true,
      readConfig: { denyOnly: [] },
      writeConfig: { allowOnly: ['.'], denyWithinAllow: [] },
      enableWeakerNestedSandbox: false,
      binShellPath: '/bin/bash',
      cwd: '/work',
      homeDir: '/home/user',
    })

    expect(cmd[0]).toBe('/usr/bin/bwrap')
    expect(cmd).toContain('--unshare-net')
    expect(cmd).toContain('--die-with-parent')
    expect(cmd).toContain('--unshare-ipc')
    expect(cmd).toContain('--bind')
    expect(cmd.join(' ')).toContain('/tmp/kode')
    expect(cmd.join(' ')).toContain('--setenv TMPDIR /tmp/kode')
  })
})
