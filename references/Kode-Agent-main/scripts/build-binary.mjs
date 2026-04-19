#!/usr/bin/env bun
import { mkdirSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'

function platformArchSuffix() {
  const platform = process.platform
  const arch = process.arch
  return `${platform}-${arch}`
}

function outFileForCurrentPlatform() {
  const suffix = platformArchSuffix()
  const ext = process.platform === 'win32' ? '.exe' : ''
  return join('dist', 'bin', suffix, `kode${ext}`)
}

function runOrThrow(cmd) {
  const proc = Bun.spawnSync({
    cmd,
    stdout: 'inherit',
    stderr: 'inherit',
  })

  if (proc.exitCode !== 0) {
    throw new Error(`Command failed (${proc.exitCode}): ${cmd.join(' ')}`)
  }
}

async function main() {
  const outFile = outFileForCurrentPlatform()
  const outDir = dirname(outFile)

  rmSync(outDir, { recursive: true, force: true })
  mkdirSync(outDir, { recursive: true })

  console.log('🚀 Building standalone executable (Bun --compile)...')
  console.log(`📦 Target: ${platformArchSuffix()}`)
  console.log(`📍 Output: ${outFile}`)

	  runOrThrow([
	    'bun',
	    'build',
	    '--compile',
    '--target=bun',
    '--format=esm',
	    '--outfile',
	    outFile,
	    'src/entrypoints/index.ts',
	  ])

  console.log('✅ Binary build completed')
}

main().catch(err => {
  console.error('❌ Binary build failed:', err)
  process.exit(1)
})
