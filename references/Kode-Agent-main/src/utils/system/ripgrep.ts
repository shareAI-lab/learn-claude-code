import { rgPath } from '@vscode/ripgrep'
import { findActualExecutable } from 'spawn-rx'
import { memoize } from 'lodash-es'
import { existsSync } from 'node:fs'
import { execFile } from 'child_process'
import debug from 'debug'
import { quote } from 'shell-quote'
import { logError } from '@utils/log'
import { execFileNoThrow } from '@utils/system/execFileNoThrow'
import type { BunShellSandboxOptions } from '@utils/bun/shell'
import { BunShell } from '@utils/bun/shell'

const d = debug('kode:ripgrep')

function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

function resolveRipgrepPathOrThrow(): string {
  const explicit = process.env.KODE_RIPGREP_PATH
  if (explicit) {
    if (!existsSync(explicit)) {
      throw new Error(`KODE_RIPGREP_PATH points to a missing file: ${explicit}`)
    }
    return explicit
  }

  const preferBundled = isTruthyEnv(process.env.USE_BUILTIN_RIPGREP)
  if (!preferBundled) {
    const { cmd } = findActualExecutable('rg', [])
    d(`ripgrep initially resolved as: ${cmd}`)
    if (cmd !== 'rg') {
      return cmd
    }
  }

  if (!rgPath || !existsSync(rgPath)) {
    throw new Error(
      [
        'ripgrep (rg) was not found on PATH, and @vscode/ripgrep is missing.',
        'Fix:',
        '- Install ripgrep: https://github.com/BurntSushi/ripgrep',
        '- Or reinstall @shareai-lab/kode (ensure dependencies are present)',
      ].join('\n'),
    )
  }

  d('Using @vscode/ripgrep fallback: %s', rgPath)
  return rgPath
}

export const getRipgrepPath = memoize((): string => resolveRipgrepPathOrThrow())

export async function ripGrep(
  args: string[],
  target: string,
  abortSignal: AbortSignal,
  options?: { sandbox?: BunShellSandboxOptions },
): Promise<string[]> {
  await codesignRipgrepIfNecessary()
  const rg = getRipgrepPath()
  d('ripgrep called: %s %o', rg, target, args)

  if (options?.sandbox?.enabled === true) {
    const cmd = quote([rg, ...args, target])
    const result = await BunShell.getInstance().exec(cmd, abortSignal, 10_000, {
      sandbox: options.sandbox,
    })
    if (result.code === 1) return []
    if (result.code !== 0) {
      logError(`ripgrep failed with exit code ${result.code}: ${result.stderr}`)
      return []
    }
    return result.stdout.trim().split('\n').filter(Boolean)
  }

  return new Promise(resolve => {
    execFile(
      rg,
      [...args, target],
      {
        maxBuffer: 1_000_000,
        signal: abortSignal,
        timeout: 10_000,
      },
      (error, stdout) => {
        if (error) {
          if (error.code !== 1) {
            d('ripgrep error: %o', error)
            logError(error)
          }
          resolve([])
        } else {
          d('ripgrep succeeded with %s', stdout)
          resolve(stdout.trim().split('\n').filter(Boolean))
        }
      },
    )
  })
}

export async function listAllContentFiles(
  path: string,
  abortSignal: AbortSignal,
  limit: number,
): Promise<string[]> {
  try {
    d('listAllContentFiles called: %s', path)
    return (await ripGrep(['-l', '.', path], path, abortSignal)).slice(0, limit)
  } catch (e) {
    d('listAllContentFiles failed: %o', e)

    logError(e)
    return []
  }
}

let alreadyDoneSignCheck = false
async function codesignRipgrepIfNecessary(): Promise<void> {
  if (process.platform !== 'darwin' || alreadyDoneSignCheck) {
    return
  }

  alreadyDoneSignCheck = true

  d('checking if ripgrep is already signed')
  const lines = (
    await execFileNoThrow(
      'codesign',
      ['-vv', '-d', getRipgrepPath()],
      undefined,
      undefined,
      false,
    )
  ).stdout.split('\n')

  const needsSigned = lines.find(line => line.includes('linker-signed'))
  if (!needsSigned) {
    d('seems to be already signed')
    return
  }

  try {
    d('signing ripgrep')
    const signResult = await execFileNoThrow('codesign', [
      '--sign',
      '-',
      '--force',
      '--preserve-metadata=entitlements,requirements,flags,runtime',
      getRipgrepPath(),
    ])

    if (signResult.code !== 0) {
      d('failed to sign ripgrep: %o', signResult)
      logError(
        `Failed to sign ripgrep: ${signResult.stdout} ${signResult.stderr}`,
      )
    }

    d('removing quarantine')
    const quarantineResult = await execFileNoThrow('xattr', [
      '-d',
      'com.apple.quarantine',
      getRipgrepPath(),
    ])

    if (quarantineResult.code !== 0) {
      d('failed to remove quarantine: %o', quarantineResult)
      logError(
        `Failed to remove quarantine: ${quarantineResult.stdout} ${quarantineResult.stderr}`,
      )
    }
  } catch (e) {
    d('failed during sign: %o', e)
    logError(e)
  }
}

export function resetRipgrepPathCacheForTests(): void {
  ;(getRipgrepPath as any).cache?.clear?.()
  alreadyDoneSignCheck = false
}

