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

function hasFlag(flag) {
  return process.argv.includes(flag)
}

function printHelpLite() {
  process.stdout.write(
    `Usage: kode [options] [command] [prompt]\n\n` +
      `Common options:\n` +
      `  -h, --help           Show full help\n` +
      `  -v, --version        Show version\n` +
      `  -p, --print          Print response and exit (non-interactive)\n` +
      `  -c, --cwd <cwd>      Set working directory\n`,
  )
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

  if (hasFlag('--help-lite')) {
    printHelpLite()
    process.exit(0)
  }

  if (hasFlag('--version') || hasFlag('-v')) {
    process.stdout.write(`${version}\n`)
    process.exit(0)
  }

  // 1) Prefer native binary (Windows OOTB, no Bun required)
  if (version) {
    const binPath = getCachedBinaryPath({ version })
    if (fs.existsSync(binPath)) {
      run(binPath, process.argv.slice(2))
    }
  }

  // 2) Fallback: Node.js runtime (npm install should work without Bun)
  const distEntry = path.join(packageRoot, 'dist', 'index.js')
  if (fs.existsSync(distEntry)) {
    run(process.execPath, [distEntry, ...process.argv.slice(2)])
  }

  // 3) Final fallback: explain what to do
  process.stderr.write(
    [
      '❌ Kode is not runnable on this system.',
      '',
      'Tried:',
      '- Native binary (postinstall download)',
      '- Node.js runtime fallback',
      '',
      'Fix:',
      '- Reinstall (ensure network access), or set KODE_BINARY_BASE_URL to a mirror',
      '- Or download a standalone binary from GitHub Releases',
      '',
    ].join('\n'),
  )
  process.exit(1)
}

main()
