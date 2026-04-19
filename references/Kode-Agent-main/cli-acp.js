#!/usr/bin/env node

const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

function findPackageRoot(startDir) {
  let dir = startDir
  for (let i = 0; i < 25; i++) {
    if (fs.existsSync(path.join(dir, 'package.json'))) return dir
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return startDir
}

function readPackageJson(packageRoot) {
  try {
    const p = path.join(packageRoot, 'package.json')
    return JSON.parse(fs.readFileSync(p, 'utf8'))
  } catch {
    return null
  }
}

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    stdio: 'inherit',
    env: { ...process.env, KODE_PACKAGED: process.env.KODE_PACKAGED || '1' },
  })
  if (result.error) {
    throw result.error
  }
  process.exit(typeof result.status === 'number' ? result.status : 1)
}

function main() {
  const packageRoot = findPackageRoot(__dirname)
  const pkg = readPackageJson(packageRoot)
  const version = pkg?.version || ''
  const { getCachedBinaryPath } = require(path.join(
    packageRoot,
    'scripts',
    'binary-utils.cjs',
  ))

  // 1) Prefer native binary (postinstall download)
  if (version) {
    const binPath = getCachedBinaryPath({ version })
    if (fs.existsSync(binPath)) {
      run(binPath, ['--acp', ...process.argv.slice(2)])
    }
  }

  // 2) Node.js runtime fallback (npm install should work without Bun)
  const distEntry = path.join(packageRoot, 'dist', 'index.js')
  if (fs.existsSync(distEntry)) {
    run(process.execPath, [distEntry, '--acp', ...process.argv.slice(2)])
  }

  process.stderr.write(
    [
      '❌ kode-acp is not runnable on this system.',
      '',
      'Tried:',
      '- Native binary (postinstall download)',
      '- Node.js runtime fallback',
      '',
      'Fix:',
      '- Reinstall (ensure network access), or set KODE_BINARY_BASE_URL to a mirror',
      '- Or download a standalone binary from GitHub Releases',
      '',
      version ? `Package version: ${version}` : '',
    ]
      .filter(Boolean)
      .join('\n'),
  )
  process.exit(1)
}

main()
