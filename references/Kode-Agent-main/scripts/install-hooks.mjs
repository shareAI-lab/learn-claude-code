#!/usr/bin/env bun
import { existsSync } from 'node:fs'

function run(cmd, options = {}) {
  const proc = Bun.spawnSync({
    cmd,
    stdout: 'pipe',
    stderr: 'pipe',
    ...options,
  })
  if (proc.exitCode !== 0) {
    const stderr = (proc.stderr ? Buffer.from(proc.stderr).toString('utf8') : '').trim()
    throw new Error(stderr || `Command failed (${proc.exitCode}): ${cmd.join(' ')}`)
  }
  return (proc.stdout ? Buffer.from(proc.stdout).toString('utf8') : '').trim()
}

function main() {
  // Only install hooks in a real git checkout.
  if (!existsSync('.git')) return
  if (!existsSync('.husky')) return

  try {
    run(['git', 'config', 'core.hooksPath', '.husky'])
    // Keep output minimal; devs can verify with: git config --get core.hooksPath
    console.log('✅ Git hooks installed (core.hooksPath=.husky)')
  } catch (err) {
    // Best-effort: never block installs.
    const msg = err instanceof Error ? err.message : String(err)
    console.warn(`⚠️  Could not install git hooks: ${msg}`)
  }
}

main()

