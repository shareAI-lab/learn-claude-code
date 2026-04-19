import { describe, expect, test } from 'bun:test'
import { spawnSync } from 'node:child_process'
import pkg from '../../package.json'

function normalizeNewlines(s: string): string {
  return s.replace(/\r\n/g, '\n')
}

function run(args: string[], options?: { cwd?: string }) {
  return spawnSync(process.execPath, args, {
    cwd: options?.cwd ?? process.cwd(),
    env: { ...process.env, NODE_ENV: 'test' },
    encoding: 'utf8',
  })
}

describe('CLI E2E smoke', () => {
  test('--help-lite prints usage', () => {
    const res = run(['cli.js', '--help-lite'])
    expect(res.status).toBe(0)
    const out = normalizeNewlines(res.stdout ?? '')
    expect(out).toContain('Usage: kode')
    expect(out).toContain('--help')
    expect(out).toContain('--version')
  })

  test('--version prints package version', () => {
    const res = run(['cli.js', '--version'])
    expect(res.status).toBe(0)
    expect((res.stdout ?? '').trim()).toBe(String(pkg.version))
  })

  test('--print validates stream-json requirements (offline)', () => {
    const res = run([
      'src/entrypoints/cli.tsx',
      '--print',
      '--input-format',
      'stream-json',
      '--output-format',
      'stream-json',
    ])
    expect(res.status).toBe(1)
    const err = normalizeNewlines(res.stderr ?? '')
    expect(err).toContain(
      'Error: When using --print, --output-format=stream-json requires --verbose',
    )
  })
})

