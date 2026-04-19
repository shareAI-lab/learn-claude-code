import { describe, expect, test } from 'bun:test'
import { BunShell } from '@utils/bun/shell'

describe('BunShell.execPromotable', () => {
  test('can promote a running command to background without respawn', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const handle = shell.execPromotable(
      'i=0; while [ $i -lt 10 ]; do i=$((i+1)); echo "tick-$i"; sleep 0.1; done',
      undefined,
      30_000,
    )

    await new Promise(resolve => setTimeout(resolve, 250))

    const promoted = handle.background()
    expect(promoted?.bashId).toBeTruthy()
    if (!promoted) throw new Error('Expected promotion to return a bashId')

    const first = shell.readBackgroundOutput(promoted.bashId)
    expect(first).not.toBeNull()
    expect(first?.stdout).not.toBe('')

    await new Promise(resolve => setTimeout(resolve, 400))

    const second = shell.readBackgroundOutput(promoted.bashId)
    expect(second).not.toBeNull()
    expect(second?.stdout).not.toBe('')

    const result = await handle.result
    expect(result.code).toBe(0)
    expect(result.interrupted).toBe(false)

    const bg = shell.getBackgroundOutput(promoted.bashId)
    expect(bg).not.toBeNull()
    expect(bg?.code).toBe(0)
  })
})
