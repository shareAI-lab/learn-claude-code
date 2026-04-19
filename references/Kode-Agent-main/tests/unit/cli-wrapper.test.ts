import { describe, expect, test } from 'bun:test'
import { spawnSync } from 'node:child_process'
import {
  chmodSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'

function writeFile(path: string, content: string, mode?: number) {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, content, 'utf8')
  if (mode !== undefined) chmodSync(path, mode)
}

function makeTempPackageRoot(options: { version: string }) {
  const root = mkdtempSync(join(tmpdir(), 'kode-cli-wrapper-'))
  mkdirSync(join(root, 'scripts'), { recursive: true })
  mkdirSync(join(root, 'dist'), { recursive: true })

  writeFileSync(
    join(root, 'package.json'),
    JSON.stringify(
      { name: '@shareai-lab/kode-test', version: options.version },
      null,
      2,
    ) + '\n',
    'utf8',
  )

  const repoRoot = process.cwd()
  writeFileSync(
    join(root, 'cli.js'),
    readFileSync(join(repoRoot, 'scripts', 'cli-wrapper.cjs'), 'utf8'),
    'utf8',
  )
  chmodSync(join(root, 'cli.js'), 0o755)

  writeFileSync(
    join(root, 'scripts', 'binary-utils.cjs'),
    readFileSync(join(repoRoot, 'scripts', 'binary-utils.cjs'), 'utf8'),
    'utf8',
  )

  return {
    root,
    cleanup() {
      rmSync(root, { recursive: true, force: true })
    },
  }
}

function runWrapper(
  packageRoot: string,
  args: string[],
  env: Record<string, string | undefined> = {},
) {
  return spawnSync(process.execPath, [join(packageRoot, 'cli.js'), ...args], {
    cwd: packageRoot,
    env: { ...process.env, ...env },
    encoding: 'utf8',
  })
}

function createFakeBunOnPath(dir: string) {
  mkdirSync(dir, { recursive: true })
  const bunPath = process.execPath
  if (process.platform === 'win32') {
    const cmdPath = join(dir, 'bun.cmd')
    writeFileSync(
      cmdPath,
      [
        '@echo off',
        'if "%1"=="--version" (',
        '  echo 1.0.0-test',
        '  exit /b 0',
        ')',
        `"${bunPath}" %*`,
        '',
      ].join('\r\n'),
      'utf8',
    )
    return
  }

  const shPath = join(dir, 'bun')
  writeFile(
    shPath,
    `#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "1.0.0-test"
  exit 0
fi
exec "${bunPath}" "$@"
`,
    0o755,
  )
}

describe('cli.js wrapper (binary-first + bun fallback)', () => {
  test('--help-lite prints usage without requiring Bun', () => {
    const pkg = makeTempPackageRoot({ version: '9.9.9' })
    const emptyPath = mkdtempSync(join(tmpdir(), 'kode-empty-path-'))
    try {
      const res = runWrapper(pkg.root, ['--help-lite'], {
        PATH: emptyPath,
      })
      expect(res.status).toBe(0)
      expect(res.stdout).toContain('Usage: kode')
      expect(res.stdout).toContain('--help')
    } finally {
      rmSync(emptyPath, { recursive: true, force: true })
      pkg.cleanup()
    }
  })

  test('--version prints package.json version without requiring Bun', () => {
    const pkg = makeTempPackageRoot({ version: '9.9.9' })
    const emptyPath = mkdtempSync(join(tmpdir(), 'kode-empty-path-'))
    try {
      const res = runWrapper(pkg.root, ['--version'], {
        PATH: emptyPath,
      })
      expect(res.status).toBe(0)
      expect(res.stdout.trim()).toBe('9.9.9')
    } finally {
      rmSync(emptyPath, { recursive: true, force: true })
      pkg.cleanup()
    }
  })

  test('falls back to Bun when native binary is missing and Bun is available on PATH', () => {
    const pkg = makeTempPackageRoot({ version: '9.9.9' })
    const stubDir = mkdtempSync(join(tmpdir(), 'kode-stub-bun-'))
    try {
      writeFileSync(
        join(pkg.root, 'dist', 'index.js'),
        `console.log("DIST_OK", process.argv.slice(2).join(" "));`,
        'utf8',
      )

      createFakeBunOnPath(stubDir)

      const res = runWrapper(pkg.root, ['arg1', 'arg2'], {
        PATH: stubDir,
      })

      expect(res.status).toBe(0)
      expect(res.stdout).toContain('DIST_OK arg1 arg2')
    } finally {
      rmSync(stubDir, { recursive: true, force: true })
      pkg.cleanup()
    }
  })

  test('prefers native cached binary when present (non-Windows)', () => {
    if (process.platform === 'win32') return

    const pkg = makeTempPackageRoot({ version: '9.9.9' })
    const binDir = mkdtempSync(join(tmpdir(), 'kode-bin-cache-'))
    try {
      const platform = process.platform
      const arch = process.arch
      const cachedBinary = join(binDir, '9.9.9', `${platform}-${arch}`, 'kode')
      writeFile(cachedBinary, `#!/bin/sh\necho "BINARY_OK"\n`, 0o755)

      writeFileSync(
        join(pkg.root, 'dist', 'index.js'),
        `console.log("DIST_OK_SHOULD_NOT_RUN");`,
        'utf8',
      )

      const emptyPath = mkdtempSync(join(tmpdir(), 'kode-empty-path-'))
      const res = runWrapper(pkg.root, [], {
        KODE_BIN_DIR: binDir,
        PATH: emptyPath,
      })
      rmSync(emptyPath, { recursive: true, force: true })

      expect(res.status).toBe(0)
      expect(res.stdout).toContain('BINARY_OK')
      expect(res.stdout).not.toContain('DIST_OK_SHOULD_NOT_RUN')
    } finally {
      rmSync(binDir, { recursive: true, force: true })
      pkg.cleanup()
    }
  })

  test('prints guidance and exits 1 when neither binary nor Bun is available', () => {
    const pkg = makeTempPackageRoot({ version: '9.9.9' })
    const emptyPath = mkdtempSync(join(tmpdir(), 'kode-empty-path-'))
    try {
      const res = runWrapper(pkg.root, [], {
        PATH: emptyPath,
      })
      expect(res.status).toBe(1)
      expect(res.stderr).toContain('Kode is not runnable')
      expect(res.stderr).toContain('KODE_BINARY_BASE_URL')
    } finally {
      rmSync(emptyPath, { recursive: true, force: true })
      pkg.cleanup()
    }
  })
})
