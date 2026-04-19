import { homedir } from 'os'
import path from 'path'
import { parse, quote, type ParseEntry } from 'shell-quote'
import type { ToolUseContext } from '@tool'
import type {
  ToolPermissionContext,
  ToolPermissionContextUpdate,
} from '@kode-types/toolPermissionContext'
import { getCwd } from '@utils/state'
import { getOriginalCwd } from '@utils/state'
import { PRODUCT_NAME } from '@constants/product'
import {
  getWriteSafetyCheckForPath,
  isPathInWorkingDirectories,
  matchPermissionRuleForPath,
  resolveLikeCliPath,
  suggestFilePermissionUpdates,
} from './fileToolPermissionEngine'

type DecisionReason =
  | { type: 'rule'; rule: string }
  | { type: 'other'; reason: string }
  | { type: 'subcommandResults'; reasons: Map<string, BashPermissionDecision> }

export type BashPermissionDecision =
  | {
      behavior: 'allow'
      updatedInput: { command: string }
      decisionReason?: DecisionReason
    }
  | {
      behavior: 'deny' | 'ask' | 'passthrough'
      message: string
      decisionReason?: DecisionReason
      blockedPath?: string
      suggestions?: ToolPermissionContextUpdate[]
    }

export type BashPermissionResult =
  | { result: true }
  | {
      result: false
      message: string
      shouldPromptUser?: boolean
      suggestions?: ToolPermissionContextUpdate[]
    }

const SINGLE_QUOTE = '__SINGLE_QUOTE__'
const DOUBLE_QUOTE = '__DOUBLE_QUOTE__'
const NEW_LINE = '__NEW_LINE__'

const SAFE_SHELL_SEPARATORS = new Set(['&&', '||', ';', '|', ';;'])

type ParsedShellTokens =
  | { success: true; tokens: ParseEntry[] }
  | { success: false; error: string }

function parseShellTokens(
  command: string,
  options?: { preserveNewlines?: boolean },
): ParsedShellTokens {
  try {
    const input = options?.preserveNewlines
      ? command
          .replaceAll('"', `"${DOUBLE_QUOTE}`)
          .replaceAll("'", `'${SINGLE_QUOTE}`)
          .replaceAll('\n', `\n${NEW_LINE}\n`)
      : command
          .replaceAll('"', `"${DOUBLE_QUOTE}`)
          .replaceAll("'", `'${SINGLE_QUOTE}`)

    return {
      success: true,
      tokens: parse(input, varName => `$${varName}`),
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    }
  }
}

function restoreShellStringToken(token: string): string {
  return token.replaceAll(SINGLE_QUOTE, "'").replaceAll(DOUBLE_QUOTE, '"')
}

function tokensToParts(
  tokens: ParseEntry[],
  options?: { preserveNewlines?: boolean },
): Array<string | null> {
  const collapsed: Array<ParseEntry | null> = []

  for (const token of tokens) {
    if (typeof token === 'string') {
      const restored = restoreShellStringToken(token)
      if (options?.preserveNewlines && restored === NEW_LINE) {
        collapsed.push(null)
        continue
      }

      if (
        collapsed.length > 0 &&
        typeof collapsed[collapsed.length - 1] === 'string'
      ) {
        collapsed[collapsed.length - 1] =
          `${collapsed[collapsed.length - 1]} ${restored}`
        continue
      }
      collapsed.push(restored)
      continue
    }

    if (
      token &&
      typeof token === 'object' &&
      'op' in token &&
      token.op === 'glob' &&
      'pattern' in token
    ) {
      const pattern = String((token as any).pattern)
      if (
        collapsed.length > 0 &&
        typeof collapsed[collapsed.length - 1] === 'string'
      ) {
        collapsed[collapsed.length - 1] =
          `${collapsed[collapsed.length - 1]} ${pattern}`
        continue
      }
      collapsed.push(pattern)
      continue
    }

    collapsed.push(token)
  }

  return collapsed
    .map(entry => {
      if (entry === null) return null
      if (typeof entry === 'string') return entry
      if (!entry || typeof entry !== 'object') return null
      if ('comment' in entry) return `#${(entry as any).comment ?? ''}`
      if ('op' in entry) return String((entry as any).op)
      return null
    })
    .filter((p): p is string | null => p !== undefined)
}

export function splitBashCommandIntoSubcommands(command: string): string[] {
  const parsed = parseShellTokens(command, { preserveNewlines: true })
  if ('error' in parsed) throw new Error(parsed.error)

  const out: string[] = []
  let currentTokens: ParseEntry[] = []

  const flush = () => {
    const rebuilt = rebuildCommandFromTokens(currentTokens, '').trim()
    if (rebuilt) out.push(rebuilt)
    currentTokens = []
  }

  for (const token of parsed.tokens) {
    if (typeof token === 'string') {
      const restored = restoreShellStringToken(token)
      if (restored === NEW_LINE) {
        flush()
        continue
      }
    }
    if (token && typeof token === 'object' && 'op' in token) {
      const op = String((token as any).op)
      if (SAFE_SHELL_SEPARATORS.has(op)) {
        flush()
        continue
      }
    }
    currentTokens.push(token)
  }
  flush()
  return out
}

type Redirection = { target: string; operator: '>' | '>>' }

type RedirectionParseResult = {
  commandWithoutRedirections: string
  redirections: Redirection[]
}

function isOpToken(entry: unknown, op: string): entry is { op: string } {
  return (
    !!entry &&
    typeof entry === 'object' &&
    'op' in (entry as any) &&
    (entry as any).op === op
  )
}

function isSafeFd(value: string): boolean {
  const v = value.trim()
  return v === '0' || v === '1' || v === '2'
}

function isSimplePathToken(value: unknown): value is string {
  if (typeof value !== 'string') return false
  const v = value.trim()
  if (!v) return false
  if (/^\d+$/.test(v)) return false
  if (v.includes('$')) return false
  if (v.includes('`')) return false
  if (v.includes('*') || v.includes('?') || v.includes('[')) return false
  return true
}

function hasUnescapedVarSuffixToken(
  token: unknown,
  tokens: ParseEntry[],
  index: number,
): boolean {
  if (typeof token !== 'string') return false
  const t = token
  if (t === '$') return true
  if (!t.endsWith('$')) return false

  if (t.includes('=') && t.endsWith('=$')) return true

  let depth = 1
  for (let i = index + 1; i < tokens.length && depth > 0; i++) {
    const next = tokens[i]
    if (isOpToken(next, '(')) depth++
    if (isOpToken(next, ')') && --depth === 0) {
      const after = tokens[i + 1]
      return typeof after === 'string' && !after.startsWith(' ')
    }
  }
  return false
}

function isWeirdTokenNeedingQuotes(value: string): boolean {
  if (/^\d+>>?$/.test(value)) return false
  if (value.includes(' ') || value.includes('\t')) return true
  if (value.length === 1 && '><|&;()'.includes(value)) return true
  return false
}

function joinTokensWithMinimalSpacing(
  out: string,
  next: string,
  noSpace: boolean,
): string {
  if (!out || noSpace) return `${out}${next}`
  return `${out} ${next}`
}

function rebuildCommandFromTokens(
  tokens: ParseEntry[],
  fallback: string,
): string {
  if (tokens.length === 0) return fallback
  let out = ''
  let parenDepth = 0
  let inProcessSubstitution = false

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]
    const prev = tokens[i - 1]
    const next = tokens[i + 1]

    if (typeof token === 'string') {
      const raw = token
      const restored = restoreShellStringToken(raw)
      const cameFromQuotedString =
        raw.includes(SINGLE_QUOTE) || raw.includes(DOUBLE_QUOTE)
      const needsQuoting = cameFromQuotedString
        ? restored
        : /[|&;]/.test(restored)
          ? `"${restored}"`
          : isWeirdTokenNeedingQuotes(restored)
            ? quote([restored])
            : restored

      const endsWithDollar = needsQuoting.endsWith('$')
      const nextIsParen =
        !!next &&
        typeof next === 'object' &&
        'op' in (next as any) &&
        (next as any).op === '('
      const noSpace =
        out.endsWith('(') ||
        prev === '$' ||
        (!!prev &&
          typeof prev === 'object' &&
          'op' in (prev as any) &&
          (prev as any).op === ')')

      if (out.endsWith('<(')) {
        out += ` ${needsQuoting}`
      } else {
        out = joinTokensWithMinimalSpacing(out, needsQuoting, noSpace)
      }
      void endsWithDollar
      void nextIsParen
      continue
    }

    if (!token || typeof token !== 'object' || !('op' in token)) continue

    const op = String((token as any).op)
    if (op === 'glob' && 'pattern' in token) {
      out = joinTokensWithMinimalSpacing(
        out,
        String((token as any).pattern),
        false,
      )
      continue
    }

    if (
      op === '>&' &&
      typeof prev === 'string' &&
      /^\d+$/.test(prev) &&
      typeof next === 'string' &&
      /^\d+$/.test(next)
    ) {
      const idx = out.lastIndexOf(prev)
      if (idx !== -1) {
        out = out.slice(0, idx) + `${prev}${op}${next}`
        i++
        continue
      }
    }

    if (op === '<' && isOpToken(next, '<')) {
      const after = tokens[i + 2]
      if (typeof after === 'string') {
        out = joinTokensWithMinimalSpacing(out, after, false)
        i += 2
        continue
      }
    }

    if (op === '<<<') {
      out = joinTokensWithMinimalSpacing(out, op, false)
      continue
    }

    if (op === '(') {
      if (hasUnescapedVarSuffixToken(prev, tokens, i) || parenDepth > 0) {
        parenDepth++
        if (out.endsWith(' ')) out = out.slice(0, -1)
        out += '('
      } else if (out.endsWith('$')) {
        if (hasUnescapedVarSuffixToken(prev, tokens, i)) {
          parenDepth++
          out += '('
        } else {
          out = joinTokensWithMinimalSpacing(out, '(', false)
        }
      } else {
        const noSpace = out.endsWith('<(') || out.endsWith('(')
        out = joinTokensWithMinimalSpacing(out, '(', noSpace)
      }
      continue
    }

    if (op === ')') {
      if (inProcessSubstitution) {
        inProcessSubstitution = false
        out += ')'
        continue
      }
      if (parenDepth > 0) parenDepth--
      out += ')'
      continue
    }

    if (op === '<(') {
      inProcessSubstitution = true
      out = joinTokensWithMinimalSpacing(out, op, false)
      continue
    }

    if (['&&', '||', '|', ';', '>', '>>', '<'].includes(op)) {
      out = joinTokensWithMinimalSpacing(out, op, false)
      continue
    }
  }

  return out.trim() || fallback
}

export function stripOutputRedirections(
  command: string,
): RedirectionParseResult {
  const parsed = parseShellTokens(command)
  if (!parsed.success)
    return { commandWithoutRedirections: command, redirections: [] }

  const tokens = parsed.tokens
  const redirections: Redirection[] = []

  const parenToStrip = new Set<number>()
  const parenStack: Array<{ index: number; isStart: boolean }> = []

  tokens.forEach((token, index) => {
    if (isOpToken(token, '(')) {
      const prev = tokens[index - 1]
      const isStart =
        index === 0 ||
        (!!prev &&
          typeof prev === 'object' &&
          'op' in (prev as any) &&
          ['&&', '||', ';', '|'].includes(String((prev as any).op)))
      parenStack.push({ index, isStart })
    } else if (isOpToken(token, ')') && parenStack.length > 0) {
      const start = parenStack.pop()!
      const next = tokens[index + 1]
      if (start.isStart && (isOpToken(next, '>') || isOpToken(next, '>>'))) {
        parenToStrip.add(start.index).add(index)
      }
    }
  })

  const outTokens: ParseEntry[] = []
  let dollarParenDepth = 0

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]
    if (!token) continue

    const prev = tokens[i - 1]
    const next = tokens[i + 1]
    const afterNext = tokens[i + 2]

    if (
      (isOpToken(token, '(') || isOpToken(token, ')')) &&
      parenToStrip.has(i)
    ) {
      continue
    }

    if (
      isOpToken(token, '(') &&
      typeof prev === 'string' &&
      prev.endsWith('$')
    ) {
      dollarParenDepth++
    } else if (isOpToken(token, ')') && dollarParenDepth > 0) {
      dollarParenDepth--
    }

    if (dollarParenDepth === 0) {
      const { skip } = maybeConsumeRedirection(
        token,
        prev,
        next,
        afterNext,
        redirections,
        outTokens,
      )
      if (skip > 0) {
        i += skip
        continue
      }
    }

    outTokens.push(token)
  }

  return {
    commandWithoutRedirections: rebuildCommandFromTokens(outTokens, command),
    redirections,
  }
}

function maybeConsumeRedirection(
  token: ParseEntry,
  prev: ParseEntry | undefined,
  next: ParseEntry | undefined,
  afterNext: ParseEntry | undefined,
  redirections: Redirection[],
  outputTokens: ParseEntry[],
): { skip: number } {
  const isFd = (v: unknown) => typeof v === 'string' && /^\d+$/.test(v.trim())

  if (isOpToken(token, '>') || isOpToken(token, '>>')) {
    const operator = String((token as any).op) as '>' | '>>'
    if (isFd(prev)) {
      return consumeRedirectionWithFd(
        prev.trim(),
        operator,
        next,
        redirections,
        outputTokens,
      )
    }

    if (isOpToken(next, '|') && isSimplePathToken(afterNext)) {
      redirections.push({ target: String(afterNext), operator })
      return { skip: 2 }
    }

    if (isSimplePathToken(next)) {
      redirections.push({ target: String(next), operator })
      return { skip: 1 }
    }
  }

  if (isOpToken(token, '>&')) {
    if (isFd(prev) && isFd(next)) {
      return { skip: 0 }
    }
    if (isSimplePathToken(next)) {
      redirections.push({ target: String(next), operator: '>' })
      return { skip: 1 }
    }
  }

  return { skip: 0 }
}

function consumeRedirectionWithFd(
  fd: string,
  operator: '>' | '>>',
  next: ParseEntry | undefined,
  redirections: Redirection[],
  outputTokens: ParseEntry[],
): { skip: number } {
  const isStdout = fd === '1'
  const nextIsPath = typeof next === 'string' && isSimplePathToken(next)

  if (redirections.length > 0) redirections.pop()

  if (nextIsPath) {
    redirections.push({ target: String(next), operator })
    if (!isStdout) outputTokens.push(`${fd}${operator}`, String(next))
    return { skip: 1 }
  }

  if (!isStdout) {
    outputTokens.push(`${fd}${operator}`)
  }

  return { skip: 0 }
}

function stripQuotes(value: string): string {
  return value.replace(/^['"]|['"]$/g, '')
}

const WILDCARD_PATTERN = /[*?[\]{}]/

type BashPathOp = 'read' | 'write' | 'create'

const PATH_COMMAND_ARG_EXTRACTORS: Record<
  string,
  (args: string[]) => string[]
> = {
  cd: args => (args.length === 0 ? [homedir()] : [args.join(' ')]),
  ls: args => {
    const cleaned = args.filter(a => a && !a.startsWith('-'))
    return cleaned.length > 0 ? cleaned : ['.']
  },
  find: args => {
    const out: string[] = []
    const paramFlags = new Set([
      '-newer',
      '-anewer',
      '-cnewer',
      '-mnewer',
      '-samefile',
      '-path',
      '-wholename',
      '-ilname',
      '-lname',
      '-ipath',
      '-iwholename',
    ])
    const newerRe = /^-newer[acmBt][acmtB]$/
    let sawNonFlag = false
    for (let i = 0; i < args.length; i++) {
      const token = args[i]
      if (!token) continue
      if (token.startsWith('-')) {
        if (['-H', '-L', '-P'].includes(token)) continue
        sawNonFlag = true
        if (paramFlags.has(token) || newerRe.test(token)) {
          const next = args[i + 1]
          if (next) {
            out.push(next)
            i++
          }
        }
        continue
      }
      if (!sawNonFlag) out.push(token)
    }
    return out.length > 0 ? out : ['.']
  },
  mkdir: args => args.filter(a => a && !a.startsWith('-')),
  touch: args => args.filter(a => a && !a.startsWith('-')),
  rm: args => args.filter(a => a && !a.startsWith('-')),
  rmdir: args => args.filter(a => a && !a.startsWith('-')),
  mv: args => args.filter(a => a && !a.startsWith('-')),
  cp: args => args.filter(a => a && !a.startsWith('-')),
  cat: args => args.filter(a => a && !a.startsWith('-')),
  head: args => args.filter(a => a && !a.startsWith('-')),
  tail: args => args.filter(a => a && !a.startsWith('-')),
  sort: args => args.filter(a => a && !a.startsWith('-')),
  uniq: args => args.filter(a => a && !a.startsWith('-')),
  wc: args => args.filter(a => a && !a.startsWith('-')),
  cut: args => args.filter(a => a && !a.startsWith('-')),
  paste: args => args.filter(a => a && !a.startsWith('-')),
  column: args => args.filter(a => a && !a.startsWith('-')),
  file: args => args.filter(a => a && !a.startsWith('-')),
  stat: args => args.filter(a => a && !a.startsWith('-')),
  diff: args => args.filter(a => a && !a.startsWith('-')),
  awk: args => args.filter(a => a && !a.startsWith('-')),
  strings: args => args.filter(a => a && !a.startsWith('-')),
  hexdump: args => args.filter(a => a && !a.startsWith('-')),
  od: args => args.filter(a => a && !a.startsWith('-')),
  base64: args => args.filter(a => a && !a.startsWith('-')),
  nl: args => args.filter(a => a && !a.startsWith('-')),
  sha256sum: args => args.filter(a => a && !a.startsWith('-')),
  sha1sum: args => args.filter(a => a && !a.startsWith('-')),
  md5sum: args => args.filter(a => a && !a.startsWith('-')),
  tr: args => {
    const hasDelete = args.some(
      a =>
        a === '-d' ||
        a === '--delete' ||
        (a.startsWith('-') && a.includes('d')),
    )
    const cleaned = args.filter(a => a && !a.startsWith('-'))
    return cleaned.slice(hasDelete ? 1 : 2)
  },
  grep: args =>
    extractPathArgsLikeClaude(
      args,
      new Set([
        '-e',
        '--regexp',
        '-f',
        '--file',
        '--exclude',
        '--include',
        '--exclude-dir',
        '--include-dir',
        '-m',
        '--max-count',
        '-A',
        '--after-context',
        '-B',
        '--before-context',
        '-C',
        '--context',
      ]),
    ),
  rg: args =>
    extractPathArgsLikeClaude(
      args,
      new Set([
        '-e',
        '--regexp',
        '-f',
        '--file',
        '-t',
        '--type',
        '-T',
        '--type-not',
        '-g',
        '--glob',
        '-m',
        '--max-count',
        '--max-depth',
        '-r',
        '--replace',
        '-A',
        '--after-context',
        '-B',
        '--before-context',
        '-C',
        '--context',
      ]),
      ['.'],
    ),
  sed: args => {
    const out: string[] = []
    let skipNext = false
    let sawExpression = false
    for (let i = 0; i < args.length; i++) {
      if (skipNext) {
        skipNext = false
        continue
      }
      const token = args[i]
      if (!token) continue
      if (token.startsWith('-')) {
        if (token === '-f' || token === '--file') {
          const next = args[i + 1]
          if (next) {
            out.push(next)
            skipNext = true
            sawExpression = true
          }
        } else if (token === '-e' || token === '--expression') {
          skipNext = true
          sawExpression = true
        } else if (token.includes('e') || token.includes('f')) {
          sawExpression = true
        }
        continue
      }
      if (!sawExpression) {
        sawExpression = true
        continue
      }
      out.push(token)
    }
    return out
  },
  jq: args => {
    const out: string[] = []
    const flags = new Set([
      '-e',
      '--expression',
      '-f',
      '--from-file',
      '--arg',
      '--argjson',
      '--slurpfile',
      '--rawfile',
      '--args',
      '--jsonargs',
      '-L',
      '--library-path',
      '--indent',
      '--tab',
    ])
    let sawExpression = false
    for (let i = 0; i < args.length; i++) {
      const token = args[i]
      if (token === undefined || token === null) continue
      if (token.startsWith('-')) {
        const flag = token.split('=')[0]
        if (flag && (flag === '-e' || flag === '--expression'))
          sawExpression = true
        if (flag && flags.has(flag) && !token.includes('=')) i++
        continue
      }
      if (!sawExpression) {
        sawExpression = true
        continue
      }
      out.push(token)
    }
    return out
  },
  git: args => {
    if (args.length >= 1 && args[0] === 'diff') {
      if (args.includes('--no-index')) {
        return args
          .slice(1)
          .filter(a => a && !a.startsWith('-'))
          .slice(0, 2)
      }
    }
    return []
  },
}

const PATH_COMMANDS = new Set(Object.keys(PATH_COMMAND_ARG_EXTRACTORS))

const COMMAND_PATH_BEHAVIOR: Record<string, BashPathOp> = {
  cd: 'read',
  ls: 'read',
  find: 'read',
  mkdir: 'create',
  touch: 'create',
  rm: 'write',
  rmdir: 'write',
  mv: 'write',
  cp: 'write',
  cat: 'read',
  head: 'read',
  tail: 'read',
  sort: 'read',
  uniq: 'read',
  wc: 'read',
  cut: 'read',
  paste: 'read',
  column: 'read',
  tr: 'read',
  file: 'read',
  stat: 'read',
  diff: 'read',
  awk: 'read',
  strings: 'read',
  hexdump: 'read',
  od: 'read',
  base64: 'read',
  nl: 'read',
  grep: 'read',
  rg: 'read',
  sed: 'write',
  git: 'read',
  jq: 'read',
  sha256sum: 'read',
  sha1sum: 'read',
  md5sum: 'read',
}

const COMMAND_DESCRIPTIONS: Record<string, string> = {
  cd: 'change directories to',
  ls: 'list files in',
  find: 'search files in',
  mkdir: 'create directories in',
  touch: 'create or modify files in',
  rm: 'remove files from',
  rmdir: 'remove directories from',
  mv: 'move files to/from',
  cp: 'copy files to/from',
  cat: 'concatenate files from',
  head: 'read the beginning of files from',
  tail: 'read the end of files from',
  sort: 'sort contents of files from',
  uniq: 'filter duplicate lines from files in',
  wc: 'count lines/words/bytes in files from',
  cut: 'extract columns from files in',
  paste: 'merge files from',
  column: 'format files from',
  tr: 'transform text from files in',
  file: 'examine file types in',
  stat: 'read file stats from',
  diff: 'compare files from',
  awk: 'process text from files in',
  strings: 'extract strings from files in',
  hexdump: 'display hex dump of files from',
  od: 'display octal dump of files from',
  base64: 'encode/decode files from',
  nl: 'number lines in files from',
  grep: 'search for patterns in files from',
  rg: 'search for patterns in files from',
  sed: 'edit files in',
  git: 'access files with git from',
  jq: 'process JSON from files in',
  sha256sum: 'compute SHA-256 checksums for files in',
  sha1sum: 'compute SHA-1 checksums for files in',
  md5sum: 'compute MD5 checksums for files in',
}

function extractPathArgsLikeClaude(
  args: string[],
  flagsTakingValues: Set<string>,
  defaultIfEmpty: string[] = [],
): string[] {
  const out: string[] = []
  let sawPatternOrExpr = false

  for (let i = 0; i < args.length; i++) {
    const token = args[i]
    if (token === undefined || token === null) continue
    if (token.startsWith('-')) {
      const flag = token.split('=')[0]
      if (
        flag &&
        (flag === '-e' ||
          flag === '--regexp' ||
          flag === '-f' ||
          flag === '--file')
      ) {
        sawPatternOrExpr = true
      }
      if (flag && flagsTakingValues.has(flag) && !token.includes('=')) {
        i++
      }
      continue
    }
    if (!sawPatternOrExpr) {
      sawPatternOrExpr = true
      continue
    }
    out.push(token)
  }

  return out.length > 0 ? out : defaultIfEmpty
}

type PathPermissionCheck = {
  allowed: boolean
  resolvedPath: string
  decisionReason?: DecisionReason
}

function getAllowedWorkingDirectories(
  context: ToolPermissionContext,
): string[] {
  return [
    resolveLikeCliPath(getOriginalCwd()),
    ...Array.from(context.additionalWorkingDirectories.keys()),
  ]
}

function formatAllowedDirs(dirs: string[], max = 5): string {
  const count = dirs.length
  if (count <= max) return dirs.map(d => `'${d}'`).join(', ')
  return `${dirs
    .slice(0, max)
    .map(d => `'${d}'`)
    .join(', ')}, and ${count - max} more`
}

function resolveTildeLikeClaude(value: string): string {
  if (value === '~' || value.startsWith('~/')) {
    return homedir() + value.slice(1)
  }
  return value
}

function baseDirForGlobPattern(pattern: string): string {
  const match = pattern.match(WILDCARD_PATTERN)
  if (!match || match.index === undefined) return pattern
  const before = pattern.slice(0, match.index)
  const lastSlash = before.lastIndexOf('/')
  if (lastSlash === -1) return '.'
  return before.slice(0, lastSlash) || '/'
}

function checkPathPermission(
  resolvedPath: string,
  toolPermissionContext: ToolPermissionContext,
  op: BashPathOp,
): { allowed: boolean; decisionReason?: DecisionReason } {
  const operation = op === 'read' ? 'read' : 'edit'

  const deniedRule = matchPermissionRuleForPath({
    inputPath: resolvedPath,
    toolPermissionContext,
    operation,
    behavior: 'deny',
  })
  if (deniedRule)
    return {
      allowed: false,
      decisionReason: { type: 'rule', rule: deniedRule },
    }

  if (op !== 'read') {
    const safety = getWriteSafetyCheckForPath(resolvedPath)
    if ('message' in safety) {
      return {
        allowed: false,
        decisionReason: { type: 'other', reason: safety.message },
      }
    }
  }

  if (isPathInWorkingDirectories(resolvedPath, toolPermissionContext))
    return { allowed: true }

  const allowRule = matchPermissionRuleForPath({
    inputPath: resolvedPath,
    toolPermissionContext,
    operation,
    behavior: 'allow',
  })
  if (allowRule)
    return { allowed: true, decisionReason: { type: 'rule', rule: allowRule } }

  return { allowed: false }
}

function checkPathArgAllowed(
  rawPath: string,
  cwd: string,
  toolPermissionContext: ToolPermissionContext,
  op: BashPathOp,
): PathPermissionCheck {
  const unquoted = resolveTildeLikeClaude(stripQuotes(rawPath))

  if (unquoted.includes('$') || unquoted.includes('%')) {
    return {
      allowed: false,
      resolvedPath: unquoted,
      decisionReason: {
        type: 'other',
        reason: 'Shell expansion syntax in paths requires manual approval',
      },
    }
  }

  if (WILDCARD_PATTERN.test(unquoted)) {
    if (op === 'write' || op === 'create') {
      return {
        allowed: false,
        resolvedPath: unquoted,
        decisionReason: {
          type: 'other',
          reason:
            'Glob patterns are not allowed in write operations. Please specify an exact file path.',
        },
      }
    }

    const base = /(?:^|[\\/])\.\.(?:[\\/]|$)/.test(unquoted)
      ? unquoted
      : baseDirForGlobPattern(unquoted)
    const abs = path.isAbsolute(base) ? base : path.resolve(cwd, base)
    const resolved = resolveLikeCliPath(abs)
    const check = checkPathPermission(resolved, toolPermissionContext, op)
    return {
      allowed: check.allowed,
      resolvedPath: resolved,
      decisionReason: check.decisionReason,
    }
  }

  const abs = path.isAbsolute(unquoted) ? unquoted : path.resolve(cwd, unquoted)
  const resolved = resolveLikeCliPath(abs)
  const check = checkPathPermission(resolved, toolPermissionContext, op)
  return {
    allowed: check.allowed,
    resolvedPath: resolved,
    decisionReason: check.decisionReason,
  }
}

function isCriticalRemovalTarget(absPath: string): boolean {
  if (absPath === '*' || absPath.endsWith('/*')) return true

  const normalized = absPath === '/' ? absPath : absPath.replace(/\/$/, '')
  if (normalized === '/') return true

  const home = homedir()
  if (normalized === home) return true

  if (path.posix.dirname(normalized) === '/') return true
  return false
}

function validatePathRestrictedCommand(
  baseCommand: string,
  args: string[],
  cwd: string,
  toolPermissionContext: ToolPermissionContext,
  hasCdInCompound: boolean,
): BashPermissionDecision {
  const op = COMMAND_PATH_BEHAVIOR[baseCommand]
  if (!op)
    return {
      behavior: 'passthrough',
      message: 'Command is not path-restricted',
    }

  const extractor = PATH_COMMAND_ARG_EXTRACTORS[baseCommand]
  const extracted = extractor ? extractor(args) : []

  if (hasCdInCompound && op !== 'read') {
    return {
      behavior: 'ask',
      message:
        "Commands that change directories and perform write operations require explicit approval to ensure paths are evaluated correctly. For security, Kode Agent cannot automatically determine the final working directory when 'cd' is used in compound commands.",
      decisionReason: {
        type: 'other',
        reason:
          'Compound command contains cd with write operation - manual approval required to prevent path resolution bypass',
      },
    }
  }

  for (const rawPath of extracted) {
    const check = checkPathArgAllowed(rawPath, cwd, toolPermissionContext, op)
    if (!check.allowed) {
      const allowedDirs = getAllowedWorkingDirectories(toolPermissionContext)
      const formatted = formatAllowedDirs(allowedDirs)
      const fallback =
        check.decisionReason?.type === 'other'
          ? check.decisionReason.reason
          : `${baseCommand} in '${check.resolvedPath}' was blocked. For security, ${PRODUCT_NAME} may only ${COMMAND_DESCRIPTIONS[baseCommand] ?? 'access'} the allowed working directories for this session: ${formatted}.`

      if (check.decisionReason?.type === 'rule') {
        return {
          behavior: 'deny',
          message: fallback,
          decisionReason: check.decisionReason,
        }
      }

      return {
        behavior: 'ask',
        message: fallback,
        blockedPath: check.resolvedPath,
        decisionReason: check.decisionReason,
      }
    }
  }

  if (baseCommand === 'rm' || baseCommand === 'rmdir') {
    for (const rawPath of extracted) {
      const unquoted = resolveTildeLikeClaude(stripQuotes(rawPath))
      const abs = path.isAbsolute(unquoted)
        ? unquoted
        : path.resolve(cwd, unquoted)
      const resolved = resolveLikeCliPath(abs)
      if (isCriticalRemovalTarget(resolved)) {
        return {
          behavior: 'ask',
          message: `Dangerous ${baseCommand} operation detected: '${resolved}'\n\nThis command would remove a critical system directory. This requires explicit approval and cannot be auto-allowed by permission rules.`,
          decisionReason: {
            type: 'other',
            reason: `Dangerous ${baseCommand} operation on critical path: ${resolved}`,
          },
          suggestions: [],
        }
      }
    }
  }

  return {
    behavior: 'passthrough',
    message: `Path validation passed for ${baseCommand} command`,
  }
}

function parseCommandPathArgs(command: string): string[] {
  const parsed = parseShellTokens(command)
  if (!parsed.success) return []
  const out: string[] = []
  for (const token of parsed.tokens) {
    if (typeof token === 'string') out.push(restoreShellStringToken(token))
    else if (
      token &&
      typeof token === 'object' &&
      'op' in token &&
      (token as any).op === 'glob' &&
      'pattern' in token
    ) {
      out.push(String((token as any).pattern))
    }
  }
  return out
}

function validateOutputRedirections(
  redirections: Redirection[],
  cwd: string,
  toolPermissionContext: ToolPermissionContext,
  hasCdInCompound: boolean,
): BashPermissionDecision {
  if (hasCdInCompound && redirections.length > 0) {
    return {
      behavior: 'ask',
      message:
        "Commands that change directories and write via output redirection require explicit approval to ensure paths are evaluated correctly. For security, Kode Agent cannot automatically determine the final working directory when 'cd' is used in compound commands.",
      decisionReason: {
        type: 'other',
        reason:
          'Compound command contains cd with output redirection - manual approval required to prevent path resolution bypass',
      },
    }
  }

  for (const { target } of redirections) {
    if (target === '/dev/null') continue
    const check = checkPathArgAllowed(
      target,
      cwd,
      toolPermissionContext,
      'create',
    )
    if (!check.allowed) {
      const allowedDirs = getAllowedWorkingDirectories(toolPermissionContext)
      const formatted = formatAllowedDirs(allowedDirs)
      const message =
        check.decisionReason?.type === 'other'
          ? check.decisionReason.reason
          : check.decisionReason?.type === 'rule'
            ? `Output redirection to '${check.resolvedPath}' was blocked by a deny rule.`
            : `Output redirection to '${check.resolvedPath}' was blocked. For security, ${PRODUCT_NAME} may only write to files in the allowed working directories for this session: ${formatted}.`

      if (check.decisionReason?.type === 'rule') {
        return {
          behavior: 'deny',
          message,
          decisionReason: check.decisionReason,
        }
      }

      return {
        behavior: 'ask',
        message,
        blockedPath: check.resolvedPath,
        suggestions: suggestFilePermissionUpdates({
          inputPath: check.resolvedPath,
          operation: 'create',
          toolPermissionContext,
        }),
      }
    }
  }

  return { behavior: 'passthrough', message: 'No unsafe redirections found' }
}

export function validateBashCommandPaths(args: {
  command: string
  cwd: string
  toolPermissionContext: ToolPermissionContext
  hasCdInCompound: boolean
}): BashPermissionDecision {
  if (/(?:>>?)\s*\S*[$%]/.test(args.command)) {
    return {
      behavior: 'ask',
      message: 'Shell expansion syntax in paths requires manual approval',
      decisionReason: {
        type: 'other',
        reason: 'Shell expansion syntax in paths requires manual approval',
      },
    }
  }

  const { redirections } = stripOutputRedirections(args.command)
  const redirectionDecision = validateOutputRedirections(
    redirections,
    args.cwd,
    args.toolPermissionContext,
    args.hasCdInCompound,
  )
  if (redirectionDecision.behavior !== 'passthrough') return redirectionDecision

  const subcommands = splitBashCommandIntoSubcommands(args.command)
  for (const subcommand of subcommands) {
    const parts = parseCommandPathArgs(subcommand)
    const [base, ...rest] = parts
    if (!base || !PATH_COMMANDS.has(base)) continue
    const decision = validatePathRestrictedCommand(
      base,
      rest,
      args.cwd,
      args.toolPermissionContext,
      args.hasCdInCompound,
    )
    if (decision.behavior === 'ask' || decision.behavior === 'deny') {
      if (decision.behavior === 'ask' && decision.blockedPath) {
        const op = COMMAND_PATH_BEHAVIOR[base]
        if (op) {
          decision.suggestions = suggestFilePermissionUpdates({
            inputPath: decision.blockedPath,
            operation: op,
            toolPermissionContext: args.toolPermissionContext,
          })
        }
      }
      return decision
    }
  }

  return {
    behavior: 'passthrough',
    message: 'All path commands validated successfully',
  }
}

type ToolRuleValue = { toolName: string; ruleContent?: string }

function parseToolRuleString(rule: string): ToolRuleValue | null {
  if (typeof rule !== 'string') return null
  const trimmed = rule.trim()
  if (!trimmed) return null
  const open = trimmed.indexOf('(')
  if (open === -1) return { toolName: trimmed }
  if (!trimmed.endsWith(')')) return null
  const toolName = trimmed.slice(0, open)
  const ruleContent = trimmed.slice(open + 1, -1)
  if (!toolName) return null
  return { toolName, ruleContent: ruleContent || undefined }
}

type BashRuleMatchType = 'exact' | 'prefix'
type ParsedBashRuleContent =
  | { type: 'exact'; command: string }
  | { type: 'prefix'; prefix: string }

function parseBashRuleContent(ruleContent: string): ParsedBashRuleContent {
  const normalized = ruleContent.trim().replace(/\s*\[background\]\s*$/i, '')
  const match = normalized.match(/^(.+):\*$/)
  if (match && match[1]) return { type: 'prefix', prefix: match[1] }
  return { type: 'exact', command: normalized }
}

function collectBashRuleStrings(
  context: ToolPermissionContext,
  behavior: 'allow' | 'deny' | 'ask',
): string[] {
  const groups =
    behavior === 'allow'
      ? context.alwaysAllowRules
      : behavior === 'deny'
        ? context.alwaysDenyRules
        : context.alwaysAskRules
  const out: string[] = []
  for (const rules of Object.values(groups)) {
    if (!Array.isArray(rules)) continue
    for (const rule of rules) if (typeof rule === 'string') out.push(rule)
  }
  return out
}

function findMatchingBashRules(args: {
  command: string
  toolPermissionContext: ToolPermissionContext
  behavior: 'allow' | 'deny' | 'ask'
  matchType: BashRuleMatchType
}): string[] {
  const trimmed = args.command.trim()
  const withoutRedirections =
    stripOutputRedirections(trimmed).commandWithoutRedirections
  const candidates =
    args.matchType === 'exact'
      ? [trimmed, withoutRedirections]
      : [withoutRedirections]

  const rules = collectBashRuleStrings(
    args.toolPermissionContext,
    args.behavior,
  )
  const matches: string[] = []

  for (const ruleString of rules) {
    const parsed = parseToolRuleString(ruleString)
    if (!parsed || parsed.toolName !== 'Bash' || !parsed.ruleContent) continue
    const content = parsed.ruleContent
    const ruleContent = parseBashRuleContent(content)

    const matched = candidates.some(candidate => {
      switch (ruleContent.type) {
        case 'exact':
          return ruleContent.command === candidate
        case 'prefix':
          if (args.matchType === 'exact')
            return ruleContent.prefix === candidate
          if (candidate === ruleContent.prefix) return true
          return candidate.startsWith(`${ruleContent.prefix} `)
      }
    })

    if (matched) matches.push(ruleString)
  }

  return matches
}

function buildBashRuleSuggestionExact(
  command: string,
): ToolPermissionContextUpdate[] {
  return [
    {
      type: 'addRules',
      destination: 'localSettings',
      behavior: 'allow',
      rules: [`Bash(${command})`],
    },
  ]
}

function buildBashRuleSuggestionPrefix(
  prefix: string,
): ToolPermissionContextUpdate[] {
  return [
    {
      type: 'addRules',
      destination: 'localSettings',
      behavior: 'allow',
      rules: [`Bash(${prefix}:*)`],
    },
  ]
}

function checkExactBashRules(
  command: string,
  toolPermissionContext: ToolPermissionContext,
): BashPermissionDecision {
  const trimmed = command.trim()
  const denyRules = findMatchingBashRules({
    command: trimmed,
    toolPermissionContext,
    behavior: 'deny',
    matchType: 'exact',
  })
  if (denyRules[0]) {
    return {
      behavior: 'deny',
      message: `Permission to use Bash with command ${trimmed} has been denied.`,
      decisionReason: { type: 'rule', rule: denyRules[0] },
    }
  }

  const askRules = findMatchingBashRules({
    command: trimmed,
    toolPermissionContext,
    behavior: 'ask',
    matchType: 'exact',
  })
  if (askRules[0]) {
    return {
      behavior: 'ask',
      message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
      decisionReason: { type: 'rule', rule: askRules[0] },
    }
  }

  const allowRules = findMatchingBashRules({
    command: trimmed,
    toolPermissionContext,
    behavior: 'allow',
    matchType: 'exact',
  })
  if (allowRules[0]) {
    return {
      behavior: 'allow',
      updatedInput: { command: trimmed },
      decisionReason: { type: 'rule', rule: allowRules[0] },
    }
  }

  return {
    behavior: 'passthrough',
    message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    decisionReason: { type: 'other', reason: 'This command requires approval' },
    suggestions: buildBashRuleSuggestionExact(trimmed),
  }
}

function checkPrefixBashRules(
  command: string,
  toolPermissionContext: ToolPermissionContext,
): { deny?: string; ask?: string; allow?: string } {
  const deny = findMatchingBashRules({
    command,
    toolPermissionContext,
    behavior: 'deny',
    matchType: 'prefix',
  })[0]
  const ask = findMatchingBashRules({
    command,
    toolPermissionContext,
    behavior: 'ask',
    matchType: 'prefix',
  })[0]
  const allow = findMatchingBashRules({
    command,
    toolPermissionContext,
    behavior: 'allow',
    matchType: 'prefix',
  })[0]
  return { deny, ask, allow }
}

const ACCEPT_EDITS_AUTO_ALLOW_BASE_COMMANDS = new Set([
  'mkdir',
  'touch',
  'rm',
  'rmdir',
  'mv',
  'cp',
  'sed',
])

function modeSpecificBashDecision(
  command: string,
  toolPermissionContext: ToolPermissionContext,
): BashPermissionDecision {
  if (toolPermissionContext.mode !== 'acceptEdits') {
    return {
      behavior: 'passthrough',
      message: 'No mode-specific validation required',
    }
  }
  const base = command.trim().split(/\s+/)[0] ?? ''
  if (!base)
    return { behavior: 'passthrough', message: 'Base command not found' }
  if (ACCEPT_EDITS_AUTO_ALLOW_BASE_COMMANDS.has(base)) {
    return {
      behavior: 'allow',
      updatedInput: { command },
      decisionReason: {
        type: 'other',
        reason: 'Auto-allowed in acceptEdits mode',
      },
    }
  }
  return {
    behavior: 'passthrough',
    message: `No mode-specific handling for '${base}' in ${toolPermissionContext.mode} mode`,
  }
}

function flagsAreAllowed(flags: string[], allowed: string[]): boolean {
  for (const flag of flags) {
    if (flag.startsWith('-') && !flag.startsWith('--') && flag.length > 2) {
      for (let i = 1; i < flag.length; i++) {
        const expanded = `-${flag[i]}`
        if (!allowed.includes(expanded)) return false
      }
    } else if (!allowed.includes(flag)) {
      return false
    }
  }
  return true
}

function sedScriptIsSafePrintOnly(script: string): boolean {
  if (!script) return false
  if (!script.endsWith('p')) return false
  if (script === 'p') return true
  const prefix = script.slice(0, -1)
  if (/^\d+$/.test(prefix)) return true
  if (/^\d+,\d+$/.test(prefix)) return true
  return false
}

function sedIsSafePrintCommand(command: string, scripts: string[]): boolean {
  const match = command.match(/^\\s*sed\\s+/)
  if (!match) return false
  const rest = command.slice(match[0].length)
  const parsed = parseShellTokens(rest)
  if (!parsed.success) return false

  const flags: string[] = []
  for (const token of parsed.tokens) {
    if (typeof token === 'string' && token.startsWith('-') && token !== '--')
      flags.push(token)
  }

  if (
    !flagsAreAllowed(flags, [
      '-n',
      '--quiet',
      '--silent',
      '-E',
      '--regexp-extended',
      '-r',
      '-z',
      '--zero-terminated',
      '--posix',
    ])
  ) {
    return false
  }

  const hasNoPrint = flags.some(
    f =>
      f === '-n' ||
      f === '--quiet' ||
      f === '--silent' ||
      (f.startsWith('-') && !f.startsWith('--') && f.includes('n')),
  )
  if (!hasNoPrint) return false

  if (scripts.length === 0) return false
  for (const script of scripts) {
    for (const part of script.split(';')) {
      if (!sedScriptIsSafePrintOnly(part.trim())) return false
    }
  }
  return true
}

function sedIsSafeSimpleSubstitution(
  command: string,
  scripts: string[],
  hasExtraExpressions: boolean,
  options?: { allowFileWrites?: boolean },
): boolean {
  const allowFileWrites = options?.allowFileWrites ?? false
  if (!allowFileWrites && hasExtraExpressions) return false

  const match = command.match(/^\\s*sed\\s+/)
  if (!match) return false
  const rest = command.slice(match[0].length)
  const parsed = parseShellTokens(rest)
  if (!parsed.success) return false

  const flags: string[] = []
  for (const token of parsed.tokens) {
    if (typeof token === 'string' && token.startsWith('-') && token !== '--')
      flags.push(token)
  }

  const allowedFlags = ['-E', '--regexp-extended', '-r', '--posix']
  if (allowFileWrites) allowedFlags.push('-i', '--in-place')
  if (!flagsAreAllowed(flags, allowedFlags)) return false

  if (scripts.length !== 1) return false
  const script = scripts[0]?.trim() ?? ''
  if (!script.startsWith('s')) return false
  const matchScript = script.match(/^s\/(.*?)$/)
  if (!matchScript) return false

  const body = matchScript[1]
  let slashCount = 0
  let lastSlashIndex = -1
  for (let i = 0; i < body.length; i++) {
    if (body[i] === '\\\\') {
      i++
      continue
    }
    if (body[i] === '/') {
      slashCount++
      lastSlashIndex = i
    }
  }
  if (slashCount !== 2) return false

  const flagsPart = body.slice(lastSlashIndex + 1)
  if (!/^[gpimIM]*[1-9]?[gpimIM]*$/.test(flagsPart)) return false
  return true
}

function sedHasExtraExpressions(command: string): boolean {
  const match = command.match(/^\\s*sed\\s+/)
  if (!match) return false
  const rest = command.slice(match[0].length)
  const parsed = parseShellTokens(rest)
  if (!parsed.success) return true

  const tokens = parsed.tokens
  try {
    let nonFlagCount = 0
    let sawExpressionFlag = false
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i]
      if (
        token &&
        typeof token === 'object' &&
        'op' in token &&
        (token as any).op === 'glob'
      )
        return true
      if (typeof token !== 'string') continue

      if (
        (token === '-e' || token === '--expression') &&
        i + 1 < tokens.length
      ) {
        sawExpressionFlag = true
        i++
        continue
      }
      if (token.startsWith('--expression=')) {
        sawExpressionFlag = true
        continue
      }
      if (token.startsWith('-e=')) {
        sawExpressionFlag = true
        continue
      }
      if (token.startsWith('-')) continue

      nonFlagCount++
      if (sawExpressionFlag) return true
      if (nonFlagCount > 1) return true
    }
    return false
  } catch {
    return true
  }
}

function extractSedScripts(command: string): string[] {
  const scripts: string[] = []
  const match = command.match(/^\\s*sed\\s+/)
  if (!match) return scripts

  const rest = command.slice(match[0].length)
  if (/-e[wWe]/.test(rest) || /-w[eE]/.test(rest)) {
    throw new Error('Dangerous flag combination detected')
  }

  const parsed = parseShellTokens(rest)
  if ('error' in parsed) {
    throw new Error(`Malformed shell syntax: ${parsed.error}`)
  }

  const tokens = parsed.tokens
  try {
    let sawExpressionFlag = false
    let sawInlineScript = false
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i]
      if (typeof token !== 'string') continue

      if (
        (token === '-e' || token === '--expression') &&
        i + 1 < tokens.length
      ) {
        sawExpressionFlag = true
        const next = tokens[i + 1]
        if (typeof next === 'string') {
          scripts.push(next)
          i++
        }
        continue
      }
      if (token.startsWith('--expression=')) {
        sawExpressionFlag = true
        scripts.push(token.slice(13))
        continue
      }
      if (token.startsWith('-e=')) {
        sawExpressionFlag = true
        scripts.push(token.slice(3))
        continue
      }
      if (token.startsWith('-')) continue
      if (!sawExpressionFlag && !sawInlineScript) {
        scripts.push(token)
        sawInlineScript = true
        continue
      }
      break
    }
  } catch (error) {
    throw new Error(
      `Failed to parse sed command: ${error instanceof Error ? error.message : 'Unknown error'}`,
    )
  }

  return scripts
}

function sedScriptContainsDangerousOperations(script: string): boolean {
  const s = script.trim()
  if (!s) return false
  if (/[^\x01-\x7F]/.test(s)) return true
  if (s.includes('{') || s.includes('}')) return true
  if (s.includes('\n')) return true

  const commentIndex = s.indexOf('#')
  if (commentIndex !== -1 && !(commentIndex > 0 && s[commentIndex - 1] === 's'))
    return true

  if (/^!/.test(s) || /[/\d$]!/.test(s)) return true
  if (/\d\s*~\s*\d|,\s*~\s*\d|\$\s*~\s*\d/.test(s)) return true
  if (/^,/.test(s)) return true
  if (/,\s*[+-]/.test(s)) return true
  if (/s\\/.test(s) || /\\[|#%@]/.test(s)) return true
  if (/\\\/.*[wW]/.test(s)) return true
  if (/\/[^/]*\s+[wWeE]/.test(s)) return true
  if (/^s\//.test(s) && !/^s\/[^/]*\/[^/]*\/[^/]*$/.test(s)) return true

  if (/^s./.test(s) && /[wWeE]$/.test(s)) {
    if (!/^s([^\\\n]).*?\1.*?\1[^wWeE]*$/.test(s)) return true
  }

  if (
    /^[wW]\s*\S+/.test(s) ||
    /^\d+\s*[wW]\s*\S+/.test(s) ||
    /^\$\s*[wW]\s*\S+/.test(s) ||
    /^\/[^/]*\/[IMim]*\s*[wW]\s*\S+/.test(s) ||
    /^\d+,\d+\s*[wW]\s*\S+/.test(s) ||
    /^\d+,\$\s*[wW]\s*\S+/.test(s) ||
    /^\/[^/]*\/[IMim]*,\/[^/]*\/[IMim]*\s*[wW]\s*\S+/.test(s)
  ) {
    return true
  }

  if (
    /^e/.test(s) ||
    /^\d+\s*e/.test(s) ||
    /^\$\s*e/.test(s) ||
    /^\/[^/]*\/[IMim]*\s*e/.test(s) ||
    /^\d+,\d+\s*e/.test(s) ||
    /^\d+,\$\s*e/.test(s) ||
    /^\/[^/]*\/[IMim]*,\/[^/]*\/[IMim]*\s*e/.test(s)
  ) {
    return true
  }

  const m = s.match(/s([^\\\n]).*?\1.*?\1(.*?)$/)
  if (m) {
    const flags = m[2] || ''
    if (flags.includes('w') || flags.includes('W')) return true
    if (flags.includes('e') || flags.includes('E')) return true
  }

  if (s.match(/y([^\\\n])/)) {
    if (/[wWeE]/.test(s)) return true
  }

  return false
}

function sedCommandIsSafe(
  command: string,
  options?: { allowFileWrites?: boolean },
): boolean {
  const allowFileWrites = options?.allowFileWrites ?? false
  let scripts: string[]
  try {
    scripts = extractSedScripts(command)
  } catch {
    return false
  }

  const hasExtraExpressions = sedHasExtraExpressions(command)

  let safePrint = false
  let safeSub = false
  if (allowFileWrites) {
    safeSub = sedIsSafeSimpleSubstitution(
      command,
      scripts,
      hasExtraExpressions,
      { allowFileWrites: true },
    )
  } else {
    safePrint = sedIsSafePrintCommand(command, scripts)
    safeSub = sedIsSafeSimpleSubstitution(command, scripts, hasExtraExpressions)
  }

  if (!safePrint && !safeSub) return false

  for (const script of scripts) {
    if (safeSub && script.includes(';')) return false
  }
  for (const script of scripts) {
    if (sedScriptContainsDangerousOperations(script)) return false
  }
  return true
}

export function checkSedCommandSafety(args: {
  command: string
  toolPermissionContext: ToolPermissionContext
}): BashPermissionDecision {
  const subcommands = splitBashCommandIntoSubcommands(args.command)
  for (const subcommand of subcommands) {
    const trimmed = subcommand.trim()
    const base = trimmed.split(/\s+/)[0]
    if (base !== 'sed') continue
    const allowFileWrites = args.toolPermissionContext.mode === 'acceptEdits'
    if (!sedCommandIsSafe(trimmed, { allowFileWrites })) {
      return {
        behavior: 'ask',
        message:
          'sed command requires approval (contains potentially dangerous operations)',
        decisionReason: {
          type: 'other',
          reason:
            'sed command contains operations that require explicit approval (e.g., write commands, execute commands)',
        },
      }
    }
  }
  return {
    behavior: 'passthrough',
    message: 'No dangerous sed operations detected',
  }
}

function parseBoolLikeEnv(value: string | undefined): boolean {
  if (!value) return false
  const v = value.trim().toLowerCase()
  return ['1', 'true', 'yes', 'y', 'on', 'enable', 'enabled'].includes(v)
}

type XiContext = {
  originalCommand: string
  baseCommand: string
  unquotedContent: string
  fullyUnquotedContent: string
}

type XiDecision =
  | { behavior: 'passthrough'; message: string }
  | { behavior: 'ask'; message: string }

function qQ5(
  input: string,
  keepDoubleQuotes = false,
): { withDoubleQuotes: string; fullyUnquoted: string } {
  let withDoubleQuotes = ''
  let fullyUnquoted = ''
  let inSingle = false
  let inDouble = false
  let escape = false

  for (let i = 0; i < input.length; i++) {
    const ch = input[i]!
    if (escape) {
      escape = false
      if (!inSingle) withDoubleQuotes += ch
      if (!inSingle && !inDouble) fullyUnquoted += ch
      continue
    }
    if (ch === '\\\\') {
      escape = true
      if (!inSingle) withDoubleQuotes += ch
      if (!inSingle && !inDouble) fullyUnquoted += ch
      continue
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      continue
    }
    if (ch === '\"' && !inSingle) {
      inDouble = !inDouble
      if (!keepDoubleQuotes) continue
    }
    if (!inSingle) withDoubleQuotes += ch
    if (!inSingle && !inDouble) fullyUnquoted += ch
  }

  return { withDoubleQuotes, fullyUnquoted }
}

function NQ5(input: string): string {
  return input
    .replace(/\s+2\s*>&\s*1(?=\s|$)/g, '')
    .replace(/[012]?\s*>\s*\/dev\/null/g, '')
    .replace(/\s*<\s*\/dev\/null/g, '')
}

function hasUnescapedChar(input: string, ch: string): boolean {
  if (ch.length !== 1)
    throw new Error('hasUnescapedChar only works with single characters')
  let i = 0
  while (i < input.length) {
    if (input[i] === '\\\\' && i + 1 < input.length) {
      i += 2
      continue
    }
    if (input[i] === ch) return true
    i++
  }
  return false
}

function MQ5(ctx: XiContext): {
  behavior: 'allow' | 'passthrough'
  message?: string
} {
  if (!ctx.originalCommand.trim()) {
    return { behavior: 'allow', message: 'Empty command is safe' }
  }
  return { behavior: 'passthrough', message: 'Command is not empty' }
}

function OQ5(ctx: XiContext): XiDecision {
  const cmd = ctx.originalCommand
  const trimmed = cmd.trim()
  if (/^\\s*\\t/.test(cmd))
    return {
      behavior: 'ask',
      message: 'Command appears to be an incomplete fragment (starts with tab)',
    }
  if (trimmed.startsWith('-'))
    return {
      behavior: 'ask',
      message:
        'Command appears to be an incomplete fragment (starts with flags)',
    }
  if (/^\\s*(&&|\\|\\||;|>>?|<)/.test(cmd)) {
    return {
      behavior: 'ask',
      message:
        'Command appears to be a continuation line (starts with operator)',
    }
  }
  return { behavior: 'passthrough', message: 'Command appears complete' }
}

const HEREDOC_IN_SUBSTITUTION = /\$\(.*<</

function RQ5(command: string): boolean {
  if (!HEREDOC_IN_SUBSTITUTION.test(command)) return false
  try {
    const re = /\$\(cat\s*<<-?\s*(?:'+([A-Za-z_]\w*)'+|\\([A-Za-z_]\w*))/g
    const matches: Array<{ start: number; delimiter: string }> = []
    let m: RegExpExecArray | null
    while ((m = re.exec(command)) !== null) {
      const delimiter = m[1] || m[2]
      if (delimiter) matches.push({ start: m.index, delimiter })
    }
    if (matches.length === 0) return false

    for (const { start, delimiter } of matches) {
      const tail = command.substring(start)
      const escaped = delimiter.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')
      if (!new RegExp(`(?:\\n|^[^\\\\n]*\\n)${escaped}\\\\s*\\\\)`).test(tail))
        return false
      const full = new RegExp(
        `^\\\\$\\\\(cat\\\\s*<<-?\\\\s*(?:'+${escaped}'+|\\\\\\\\${escaped})[^\\\\n]*\\\\n(?:[\\\\s\\\\S]*?\\\\n)?${escaped}\\\\s*\\\\)`,
      )
      if (!tail.match(full)) return false
    }

    let remaining = command
    for (const { delimiter } of matches) {
      const escaped = delimiter.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')
      const pattern = new RegExp(
        `\\\\$\\\\(cat\\\\s*<<-?\\\\s*(?:'+${escaped}'+|\\\\\\\\${escaped})[^\\\\n]*\\\\n(?:[\\\\s\\\\S]*?\\\\n)?${escaped}\\\\s*\\\\)`,
      )
      remaining = remaining.replace(pattern, '')
    }

    if (/\$\(/.test(remaining)) return false
    if (/\$\{/.test(remaining)) return false
    return true
  } catch {
    return false
  }
}

function TQ5(ctx: XiContext): {
  behavior: 'allow' | 'passthrough'
  message?: string
} {
  if (!HEREDOC_IN_SUBSTITUTION.test(ctx.originalCommand)) {
    return { behavior: 'passthrough', message: 'No heredoc in substitution' }
  }
  if (RQ5(ctx.originalCommand)) {
    return {
      behavior: 'allow',
      message:
        'Safe command substitution: cat with quoted/escaped heredoc delimiter',
    }
  }
  return {
    behavior: 'passthrough',
    message: 'Command substitution needs validation',
  }
}

function jQ5(ctx: XiContext): {
  behavior: 'allow' | 'ask' | 'passthrough'
  message: string
} {
  const cmd = ctx.originalCommand
  if (ctx.baseCommand !== 'git' || !/^git\s+commit\s+/.test(cmd)) {
    return { behavior: 'passthrough', message: 'Not a git commit' }
  }
  const match = cmd.match(/^git\s+commit\s+.*-m\s+(["'])([\s\S]*?)\1(.*)$/)
  if (!match)
    return { behavior: 'passthrough', message: 'Git commit needs validation' }

  const [, quoteChar, message, tail] = match
  if (quoteChar === '"' && message && /\$\(|`|\$\{/.test(message)) {
    return {
      behavior: 'ask',
      message: 'Git commit message contains command substitution patterns',
    }
  }
  if (tail && /\$\(|`|\$\{/.test(tail)) {
    return { behavior: 'passthrough', message: 'Check patterns in flags' }
  }
  return {
    behavior: 'allow',
    message: 'Git commit with simple quoted message is allowed',
  }
}

function PQ5(ctx: XiContext): {
  behavior: 'allow' | 'passthrough'
  message: string
} {
  if (HEREDOC_IN_SUBSTITUTION.test(ctx.originalCommand)) {
    return { behavior: 'passthrough', message: 'Heredoc in substitution' }
  }
  const safeQuoted = /<<-?\s*'[^']+'/
  const safeEscaped = /<<-?\s*\\\w+/
  if (
    safeQuoted.test(ctx.originalCommand) ||
    safeEscaped.test(ctx.originalCommand)
  ) {
    return {
      behavior: 'allow',
      message: 'Heredoc with quoted/escaped delimiter is safe',
    }
  }
  return { behavior: 'passthrough', message: 'No heredoc patterns' }
}

function SQ5(ctx: XiContext): XiDecision {
  if (ctx.baseCommand !== 'jq')
    return { behavior: 'passthrough', message: 'Not jq' }
  if (/\bsystem\s*\(/.test(ctx.originalCommand)) {
    return {
      behavior: 'ask',
      message:
        'jq command contains system() function which executes arbitrary commands',
    }
  }
  const rest = ctx.originalCommand.substring(3).trim()
  if (
    /(?:^|\s)(?:-f\b|--from-file|--rawfile|--slurpfile|-L\b|--library-path)/.test(
      rest,
    )
  ) {
    return {
      behavior: 'ask',
      message:
        'jq command contains dangerous flags that could execute code or read arbitrary files',
    }
  }
  return { behavior: 'passthrough', message: 'jq command is safe' }
}

function _Q5(ctx: XiContext): XiDecision {
  const q = ctx.unquotedContent
  const msg = 'Command contains shell metacharacters (;, |, or &) in arguments'
  if (/(?:^|\\s)[\"'][^\"']*[;&][^\"']*[\"'](?:\\s|$)/.test(q))
    return { behavior: 'ask', message: msg }
  if (
    [
      /-name\\s+[\"'][^\"']*[;|&][^\"']*[\"']/,
      /-path\\s+[\"'][^\"']*[;|&][^\"']*[\"']/,
      /-iname\\s+[\"'][^\"']*[;|&][^\"']*[\"']/,
    ].some(re => re.test(q))
  ) {
    return { behavior: 'ask', message: msg }
  }
  if (/-regex\\s+[\"'][^\"']*[;&][^\"']*[\"']/.test(q))
    return { behavior: 'ask', message: msg }
  return { behavior: 'passthrough', message: 'No metacharacters' }
}

function yQ5(ctx: XiContext): XiDecision {
  const q = ctx.fullyUnquotedContent
  if (
    /[<>|]\s*\$[A-Za-z_]/.test(q) ||
    /\$[A-Za-z_][A-Za-z0-9_]*\s*[|<>]/.test(q)
  ) {
    return {
      behavior: 'ask',
      message:
        'Command contains variables in dangerous contexts (redirections or pipes)',
    }
  }
  return { behavior: 'passthrough', message: 'No dangerous variables' }
}

const DANGEROUS_PATTERNS = [
  { pattern: /<\(/, message: 'process substitution <()' },
  { pattern: />\(/, message: 'process substitution >()' },
  { pattern: /\$\(/, message: '$() command substitution' },
  { pattern: /\$\{/, message: '${} parameter substitution' },
  { pattern: /~\[/, message: 'Zsh-style parameter expansion' },
  { pattern: /\(e:/, message: 'Zsh-style glob qualifiers' },
  { pattern: /<#/, message: 'PowerShell comment syntax' },
]

function kQ5(ctx: XiContext): XiDecision {
  const unquoted = ctx.unquotedContent
  const fully = ctx.fullyUnquotedContent
  if (hasUnescapedChar(unquoted, '`'))
    return {
      behavior: 'ask',
      message: 'Command contains backticks (`) for command substitution',
    }
  for (const { pattern, message } of DANGEROUS_PATTERNS) {
    if (pattern.test(unquoted))
      return { behavior: 'ask', message: `Command contains ${message}` }
  }
  if (/</.test(fully))
    return {
      behavior: 'ask',
      message:
        'Command contains input redirection (<) which could read sensitive files',
    }
  if (/>/.test(fully))
    return {
      behavior: 'ask',
      message:
        'Command contains output redirection (>) which could write to arbitrary files',
    }
  return { behavior: 'passthrough', message: 'No dangerous patterns' }
}

function xQ5(ctx: XiContext): XiDecision {
  const q = ctx.fullyUnquotedContent
  if (!/[\n\r]/.test(q))
    return { behavior: 'passthrough', message: 'No newlines' }
  if (/[\n\r]\s*[a-zA-Z/.~]/.test(q))
    return {
      behavior: 'ask',
      message:
        'Command contains newlines that could separate multiple commands',
    }
  return {
    behavior: 'passthrough',
    message: 'Newlines appear to be within data',
  }
}

function vQ5(ctx: XiContext): XiDecision {
  if (/\$IFS|\$\{[^}]*IFS/.test(ctx.originalCommand)) {
    return {
      behavior: 'ask',
      message:
        'Command contains IFS variable usage which could bypass security validation',
    }
  }
  return { behavior: 'passthrough', message: 'No IFS injection detected' }
}

function bQ5(ctx: XiContext): XiDecision {
  if (ctx.baseCommand === 'echo')
    return {
      behavior: 'passthrough',
      message: 'echo command is safe and has no dangerous flags',
    }

  const cmd = ctx.originalCommand
  let inSingle = false
  let inDouble = false
  let escape = false
  for (let i = 0; i < cmd.length - 1; i++) {
    const ch = cmd[i]!
    const next = cmd[i + 1]!
    if (escape) {
      escape = false
      continue
    }
    if (ch === '\\\\') {
      escape = true
      continue
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      continue
    }
    if (ch === '\"' && !inSingle) {
      inDouble = !inDouble
      continue
    }
    if (inSingle || inDouble) continue

    if (/\s/.test(ch) && next === '-') {
      let j = i + 1
      let current = ''
      while (j < cmd.length) {
        const v = cmd[j]
        if (!v) break
        if (/[\s=]/.test(v)) break
        if (/['\"`]/.test(v)) {
          if (ctx.baseCommand === 'cut' && current === '-d') break
          if (j + 1 < cmd.length) {
            const after = cmd[j + 1]!
            if (!/[a-zA-Z0-9_'\"-]/.test(after)) break
          }
        }
        current += v
        j++
      }
      if (current.includes('"') || current.includes("'")) {
        return {
          behavior: 'ask',
          message: 'Command contains quoted characters in flag names',
        }
      }
    }
  }

  const fully = ctx.fullyUnquotedContent
  if (/\s['\"`]-/.test(fully))
    return {
      behavior: 'ask',
      message: 'Command contains quoted characters in flag names',
    }
  if (/['\"`]{2}-/.test(fully))
    return {
      behavior: 'ask',
      message: 'Command contains quoted characters in flag names',
    }

  return { behavior: 'passthrough', message: 'No obfuscated flags detected' }
}

export function xi(command: string): XiDecision {
  const base = command.split(' ')[0] || ''
  const { withDoubleQuotes, fullyUnquoted } = qQ5(command, base === 'jq')
  const ctx: XiContext = {
    originalCommand: command,
    baseCommand: base,
    unquotedContent: withDoubleQuotes,
    fullyUnquotedContent: NQ5(fullyUnquoted),
  }

  const allowChecks = [MQ5, OQ5, TQ5, PQ5, jQ5]
  for (const check of allowChecks) {
    const res: any = check(ctx as any)
    if (res.behavior === 'allow')
      return {
        behavior: 'passthrough',
        message: res.message ?? 'Command allowed',
      }
    if (res.behavior !== 'passthrough') return res
  }

  const askChecks = [SQ5, bQ5, _Q5, yQ5, xQ5, vQ5, kQ5]
  for (const check of askChecks) {
    const res = check(ctx)
    if (res.behavior === 'ask') return res
  }

  return {
    behavior: 'passthrough',
    message: 'Command passed all security checks',
  }
}

function isSafeCommandList(command: string): boolean {
  const parsed = parseShellTokens(command)
  if (!parsed.success) return false

  for (let i = 0; i < parsed.tokens.length; i++) {
    const token = parsed.tokens[i]
    const next = parsed.tokens[i + 1]
    if (!token) continue
    if (typeof token === 'string') continue
    if (typeof token !== 'object') continue
    if ('comment' in (token as any)) return false
    if (!('op' in (token as any))) continue

    const op = String((token as any).op)
    if (op === 'glob') continue
    if (SAFE_SHELL_SEPARATORS.has(op)) continue
    if (op === '>&') {
      if (typeof next === 'string' && isSafeFd(next)) continue
    }
    if (op === '>' || op === '>>') continue
    return false
  }
  return true
}

function isUnsafeCompoundCommand(command: string): boolean {
  try {
    return (
      splitBashCommandIntoSubcommands(command).length > 1 &&
      !isSafeCommandList(command)
    )
  } catch {
    return true
  }
}

export function checkBashCommandSyntax(
  command: string,
): BashPermissionDecision {
  const parsed = parseShellTokens(command)
  if ('error' in parsed) {
    const reason: DecisionReason = {
      type: 'other',
      reason: `Command contains malformed syntax that cannot be parsed: ${parsed.error}`,
    }
    return {
      behavior: 'ask',
      message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
      decisionReason: reason,
    }
  }
  return { behavior: 'passthrough', message: 'Command parsed successfully' }
}

function h02(args: {
  command: string
  cwd: string
  toolPermissionContext: ToolPermissionContext
  hasCdInCompound: boolean
}): BashPermissionDecision {
  const trimmed = args.command.trim()

  const exact = checkExactBashRules(trimmed, args.toolPermissionContext)
  if (exact.behavior === 'deny' || exact.behavior === 'ask') return exact

  const prefixMatches = checkPrefixBashRules(
    trimmed,
    args.toolPermissionContext,
  )
  if (prefixMatches.deny) {
    return {
      behavior: 'deny',
      message: `Permission to use Bash with command ${trimmed} has been denied.`,
      decisionReason: { type: 'rule', rule: prefixMatches.deny },
    }
  }
  if (prefixMatches.ask) {
    return {
      behavior: 'ask',
      message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
      decisionReason: { type: 'rule', rule: prefixMatches.ask },
    }
  }

  const pathDecision = validateBashCommandPaths({
    command: trimmed,
    cwd: args.cwd,
    toolPermissionContext: args.toolPermissionContext,
    hasCdInCompound: args.hasCdInCompound,
  })
  if (pathDecision.behavior !== 'passthrough') return pathDecision

  if (exact.behavior === 'allow') return exact

  if (prefixMatches.allow) {
    return {
      behavior: 'allow',
      updatedInput: { command: trimmed },
      decisionReason: { type: 'rule', rule: prefixMatches.allow },
    }
  }

  const sedDecision = checkSedCommandSafety({
    command: trimmed,
    toolPermissionContext: args.toolPermissionContext,
  })
  if (sedDecision.behavior !== 'passthrough') return sedDecision

  const modeDecision = modeSpecificBashDecision(
    trimmed,
    args.toolPermissionContext,
  )
  if (modeDecision.behavior !== 'passthrough') return modeDecision

  if (
    !parseBoolLikeEnv(
      process.env.KODE_DISABLE_COMMAND_INJECTION_CHECK ??
        process.env.CLAUDE_CODE_DISABLE_COMMAND_INJECTION_CHECK,
    )
  ) {
    const security = xi(trimmed)
    if (security.behavior !== 'passthrough') {
      const reason: DecisionReason = {
        type: 'other',
        reason:
          security.message ||
          'This command contains patterns that could pose security risks and requires approval',
      }
      return {
        behavior: 'ask',
        message:
          security.message ||
          `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
        decisionReason: reason,
        suggestions: [],
      }
    }
  }

  return {
    behavior: 'passthrough',
    message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    decisionReason: { type: 'other', reason: 'This command requires approval' },
    suggestions: buildBashRuleSuggestionExact(trimmed),
  }
}

export async function checkBashPermissions(args: {
  command: string
  toolPermissionContext: ToolPermissionContext
  toolUseContext: ToolUseContext
  getCwdForPaths?: () => string
}): Promise<BashPermissionResult> {
  const cwd = (args.getCwdForPaths ?? getCwd)()
  const trimmed = args.command.trim()

  const syntax = checkBashCommandSyntax(trimmed)
  if (syntax.behavior !== 'passthrough') {
    return {
      result: false,
      message:
        'message' in syntax
          ? syntax.message
          : `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    }
  }

  if (
    !parseBoolLikeEnv(
      process.env.KODE_DISABLE_COMMAND_INJECTION_CHECK ??
        process.env.CLAUDE_CODE_DISABLE_COMMAND_INJECTION_CHECK,
    ) &&
    isUnsafeCompoundCommand(trimmed)
  ) {
    const security = xi(trimmed)
    return {
      result: false,
      message:
        security.behavior === 'ask' && security.message
          ? security.message
          : `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    }
  }

  const fullExact = checkExactBashRules(trimmed, args.toolPermissionContext)
  if (fullExact.behavior === 'deny') {
    return {
      result: false,
      message: fullExact.message,
      shouldPromptUser: false,
    }
  }

  const subcommands = splitBashCommandIntoSubcommands(trimmed).filter(
    cmd => cmd !== `cd ${cwd}`,
  )
  const cdCommands = subcommands.filter(cmd => cmd.trim().startsWith('cd '))
  if (cdCommands.length > 1) {
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    }
  }
  const hasCdInCompound = cdCommands.length > 0

  const subResults = new Map<string, BashPermissionDecision>()
  for (const sub of subcommands) {
    const decision = h02({
      command: sub,
      cwd,
      toolPermissionContext: args.toolPermissionContext,
      hasCdInCompound,
    })
    subResults.set(sub, decision)
  }

  for (const decision of subResults.values()) {
    if (decision.behavior === 'deny') {
      return {
        result: false,
        message: decision.message,
        shouldPromptUser: false,
      }
    }
  }

  const fullPathDecision = validateBashCommandPaths({
    command: trimmed,
    cwd,
    toolPermissionContext: args.toolPermissionContext,
    hasCdInCompound,
  })
  if (fullPathDecision.behavior === 'deny') {
    return {
      result: false,
      message: fullPathDecision.message,
      shouldPromptUser: false,
    }
  }
  if (fullPathDecision.behavior === 'ask') {
    return {
      result: false,
      message: fullPathDecision.message,
      suggestions: fullPathDecision.suggestions,
    }
  }

  for (const decision of subResults.values()) {
    if (decision.behavior === 'ask') {
      return {
        result: false,
        message: decision.message,
        suggestions: decision.suggestions,
      }
    }
  }

  if (fullExact.behavior === 'allow') return { result: true }

  if (Array.from(subResults.values()).every(d => d.behavior === 'allow')) {
    return { result: true }
  }

  return {
    result: false,
    message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    suggestions: buildBashRuleSuggestionExact(trimmed),
  }
}

export function checkBashPermissionsAutoAllowedBySandbox(args: {
  command: string
  toolPermissionContext: ToolPermissionContext
}): BashPermissionResult {
  const trimmed = args.command.trim()
  const prefixMatches = checkPrefixBashRules(
    trimmed,
    args.toolPermissionContext,
  )

  if (prefixMatches.deny) {
    return {
      result: false,
      message: `Permission to use Bash with command ${trimmed} has been denied.`,
      shouldPromptUser: false,
    }
  }

  if (prefixMatches.ask) {
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use Bash, but you haven't granted it yet.`,
    }
  }

  return { result: true }
}
