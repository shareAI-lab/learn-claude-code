import { describe, expect, test } from 'bun:test'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

describe('postinstall (binary download)', () => {
  test('KODE_SKIP_BINARY_DOWNLOAD prevents network work and still prints notice', () => {
    const script = join(process.cwd(), 'scripts', 'postinstall.js')
    const res = spawnSync(process.execPath, [script], {
      cwd: process.cwd(),
      env: {
        ...process.env,
        npm_lifecycle_event: 'postinstall',
        KODE_SKIP_BINARY_DOWNLOAD: '1',
      },
      encoding: 'utf8',
    })

    expect(res.status).toBe(0)
    expect(res.stdout).toContain('@shareai-lab/kode installed')
  })
})
