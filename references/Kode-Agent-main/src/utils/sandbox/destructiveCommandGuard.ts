import path from 'path'
import { homedir } from 'os'
import { parse, type ParseEntry } from 'shell-quote'
import { splitCommand } from '@utils/commands'
import type { CommandSource } from '@tools/BashTool/commandSource'

function parseBoolLike(value: string | undefined): boolean {
  if (!value) return false
  const v = value.trim().toLowerCase()
  return ['1', 'true', 'yes', 'y', 'on', 'enable', 'enabled'].includes(v)
}

function tokensToWords(tokens: ParseEntry[]): string[] {
  const out: string[] = []
  for (const token of tokens) {
    if (typeof token === 'string') {
      const trimmed = token.trim()
      if (trimmed) out.push(trimmed)
      continue
    }
    if (token && typeof token === 'object' && 'op' in token) {
      const op = String((token as any).op)
      if (op === 'glob' && 'pattern' in (token as any)) {
        const pattern = String((token as any).pattern).trim()
        if (pattern) out.push(pattern)
      }
    }
  }
  return out
}

function isEnvAssignment(word: string): boolean {
  return /^[A-Za-z_][A-Za-z0-9_]*=/.test(word)
}

function stripWrappers(words: string[]): string[] {
  let i = 0

  while (i < words.length && isEnvAssignment(words[i]!)) i++

  while (i < words.length) {
    const w = words[i]
    if (w === 'command') {
      i++
      continue
    }
    if (w === 'sudo') {
      i++
      while (i < words.length) {
        const next = words[i]!
        if (next === '--') {
          i++
          break
        }
        if (next.startsWith('-')) {
          i++
          continue
        }
        break
      }
      continue
    }
    if (w === 'env') {
      i++
      while (i < words.length) {
        const next = words[i]!
        if (next === '--') {
          i++
          break
        }
        if (next.startsWith('-') || isEnvAssignment(next)) {
          i++
          continue
        }
        break
      }
      continue
    }
    break
  }

  return words.slice(i)
}

type RmInvocation = { cmd: 'rm' | 'rmdir'; args: string[] }

function findRmInvocation(words: string[]): RmInvocation | null {
  const stripped = stripWrappers(words)
  const cmd = stripped[0]
  if (cmd !== 'rm' && cmd !== 'rmdir') return null
  return { cmd, args: stripped.slice(1) }
}

function extractRmTargets(args: string[]): string[] {
  const targets: string[] = []
  let endOfOptions = false
  for (const arg of args) {
    if (!arg) continue
    if (!endOfOptions && arg === '--') {
      endOfOptions = true
      continue
    }
    if (!endOfOptions && arg.startsWith('-')) continue
    targets.push(arg)
  }
  return targets
}

function resolveTilde(value: string, homeDir: string): string {
  if (value === '~') return homeDir
  if (value.startsWith('~/') || value.startsWith('~\\'))
    return homeDir + value.slice(1)
  return value
}

function resolvePathForSafety(
  raw: string,
  cwd: string,
  homeDir: string,
): string {
  const expanded = resolveTilde(raw.trim(), homeDir)
  return path.isAbsolute(expanded)
    ? path.resolve(expanded)
    : path.resolve(cwd, expanded)
}

function isCriticalRemovalTarget(
  resolvedPath: string,
  options: { homeDir: string; originalCwd: string },
): boolean {
  const home = path.resolve(options.homeDir)
  const original = path.resolve(options.originalCwd)
  const target = path.resolve(resolvedPath)

  const root = path.parse(target).root
  if (target === root) return true
  if (target === home) return true
  if (target === original) return true

  const parent = path.dirname(target)
  if (parent === root) return true

  return false
}

export type DestructiveCommandBlock = {
  message: string
  command: string
  subcommand: string
  target: string
  resolvedTarget: string
}

const ENV_ALLOW = 'KODE_ALLOW_DESTRUCTIVE_RM'

export function getBashDestructiveCommandBlock(args: {
  command: string
  cwd: string
  originalCwd: string
  commandSource: CommandSource
  homeDir?: string
  platform?: NodeJS.Platform
  allowOverride?: boolean
}): DestructiveCommandBlock | null {
  if (args.commandSource !== 'agent_call') return null

  const allowOverride =
    args.allowOverride === true || parseBoolLike(process.env[ENV_ALLOW])
  if (allowOverride) return null

  const homeDir = args.homeDir ?? homedir()
  const cwd = args.cwd

  const maybeDestructive = /\brm\b|\brmdir\b/.test(args.command)
  if (!maybeDestructive) return null

  const subcommands = splitCommand(args.command)
  for (const subcommand of subcommands) {
    let parsed: ParseEntry[]
    try {
      parsed = parse(subcommand, varName => `$${varName}`)
    } catch {
      continue
    }

    const words = tokensToWords(parsed)
    const invocation = findRmInvocation(words)
    if (!invocation) continue

    const targets = extractRmTargets(invocation.args)
    for (const target of targets) {
      if (/[`$%]/.test(target)) {
        return {
          command: args.command,
          subcommand,
          target,
          resolvedTarget: target,
          message:
            `Blocked destructive command: ${invocation.cmd} target contains shell expansion (${JSON.stringify(target)}).\n\n` +
            `Specify an explicit path (avoid $VARS, backticks, or %VAR%), or run this command manually.\n` +
            `To override (not recommended), set ${ENV_ALLOW}=1 in the ${args.platform ?? process.platform} environment and rerun.`,
        }
      }

      const resolvedTarget = resolvePathForSafety(target, cwd, homeDir)
      if (
        isCriticalRemovalTarget(resolvedTarget, {
          homeDir,
          originalCwd: args.originalCwd,
        })
      ) {
        return {
          command: args.command,
          subcommand,
          target,
          resolvedTarget,
          message:
            `Blocked destructive command: ${invocation.cmd} target resolves to a critical directory (${JSON.stringify(resolvedTarget)}).\n\n` +
            `This guard prevents accidental deletion of system/home/project roots in non-interactive agent runs.\n` +
            `To override (not recommended), set ${ENV_ALLOW}=1 in the ${args.platform ?? process.platform} environment and rerun.`,
        }
      }
    }
  }

  return null
}
