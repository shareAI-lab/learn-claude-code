import { describe, expect, test } from 'bun:test'
import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join, resolve } from 'path'
import { build as esbuildBuild } from 'esbuild'
import pkg from '../../package.json'

function loadEsbuildTsconfigRaw() {
  const tsconfigPath = resolve(process.cwd(), 'tsconfig.json')
  const raw = JSON.parse(readFileSync(tsconfigPath, 'utf8'))
  const compilerOptions = raw?.compilerOptions ?? {}
  const paths = { ...(compilerOptions.paths ?? {}) }
  delete paths['*']
  return { compilerOptions: { ...compilerOptions, paths } }
}

describe('npm runtime (Node.js)', () => {
  test('built dist/index.js runs on Node for --help-lite/--version', async () => {
    const root = mkdtempSync(join(tmpdir(), 'kode-node-runtime-'))
    const distDir = join(root, 'dist')
    mkdirSync(distDir, { recursive: true })

    try {
      await esbuildBuild({
        entryPoints: [resolve(process.cwd(), 'src/entrypoints/index.ts')],
        outdir: distDir,
        bundle: true,
        platform: 'node',
        target: ['node20'],
        format: 'esm',
        splitting: true,
        packages: 'external',
        sourcemap: false,
        banner: {
          js: 'import { createRequire as __kodeCreateRequire } from "node:module";\nconst require = __kodeCreateRequire(import.meta.url);',
        },
        tsconfigRaw: loadEsbuildTsconfigRaw(),
      })

      writeFileSync(
        join(distDir, 'package.json'),
        JSON.stringify({ type: 'module', main: './index.js' }, null, 2),
      )

      const node = (globalThis as any).Bun?.which?.('node') ?? 'node'

      const versionRes = spawnSync(node, [join(distDir, 'index.js'), '--version'], {
        encoding: 'utf8',
      })
      expect(versionRes.status).toBe(0)
      expect((versionRes.stdout ?? '').trim()).toBe(String(pkg.version))

      const helpRes = spawnSync(node, [join(distDir, 'index.js'), '--help-lite'], {
        encoding: 'utf8',
      })
      expect(helpRes.status).toBe(0)
      expect((helpRes.stdout ?? '')).toContain('Usage: kode')
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
})

