import { fileURLToPath } from 'node:url'
import { basename, dirname, join } from 'node:path'
import { existsSync } from 'node:fs'

export function ensurePackagedRuntimeEnv(): void {
  if (process.env.KODE_PACKAGED !== undefined) return

  try {
    const exec = basename(process.execPath || '').toLowerCase()
    if (
      exec &&
      exec !== 'bun' &&
      exec !== 'bun.exe' &&
      exec !== 'node' &&
      exec !== 'node.exe'
    ) {
      process.env.KODE_PACKAGED = '1'
    }
  } catch {}
}

export function ensureYogaWasmPath(entrypointUrl: string): void {
  try {
    if (process.env.YOGA_WASM_PATH) return

    const entryFile = fileURLToPath(entrypointUrl)
    const entryDir = dirname(entryFile)
    const devCandidate = join(entryDir, '../../yoga.wasm')
    const distCandidate = join(entryDir, './yoga.wasm')
    const resolved = existsSync(distCandidate)
      ? distCandidate
      : existsSync(devCandidate)
        ? devCandidate
        : undefined
    if (resolved) {
      process.env.YOGA_WASM_PATH = resolved
    }
  } catch {}
}
