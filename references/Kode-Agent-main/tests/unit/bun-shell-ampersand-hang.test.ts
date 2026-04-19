import { describe, expect, test } from 'bun:test'
import { BunShell } from '@utils/bun/shell'

describe('BunShell.exec ampersand backgrounding', () => {
  test('returns even if a background child keeps stdout/stderr open', async () => {
    if (process.platform === 'win32') {
      return
    }

    BunShell.restart()
    const shell = BunShell.getInstance()

    const startedAt = Date.now()
    const command = 'sleep 5 & echo $!'

    const result = (await Promise.race([
      shell.exec(command, undefined, 30_000),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('exec hung')), 1_500),
      ),
    ])) as any

    const durationMs = Date.now() - startedAt
    expect(durationMs).toBeLessThan(1_500)
    expect(result.interrupted).toBe(false)
    expect(result.code).toBe(0)

    const pid = Number.parseInt(String(result.stdout).trim(), 10)
    if (Number.isFinite(pid) && pid > 0) {
      try {
        process.kill(pid)
      } catch {}
    }
  })
})
