import { existsSync, realpathSync, statSync } from 'fs'
import { homedir } from 'os'
import path from 'path'
import ignore, { type Ignore } from 'ignore'
import type {
  ToolPermissionContext,
  ToolPermissionContextUpdate,
  ToolPermissionRuleBehavior,
  ToolPermissionUpdateDestination,
} from '@kode-types/toolPermissionContext'
import type { ToolUseContext } from '@tool'
import { getCwd, getOriginalCwd } from '@utils/state'
import { getPlanConversationKey, getPlanFilePath } from '@utils/plan/planMode'
import { getSettingsFileCandidates } from '@utils/config/settingsFiles'
import { PRODUCT_NAME } from '@constants/product'
import { getKodeBaseDir } from '@utils/config/env'

type ToolRuleValue = {
  toolName: string
  ruleContent?: string
}

type ToolRuleEntry = {
  source: ToolPermissionUpdateDestination
  ruleValue: ToolRuleValue
  ruleString: string
}

type FilePermissionOperation = 'read' | 'edit'

type FilePermissionBehavior = ToolPermissionRuleBehavior

const POSIX = path.posix
const POSIX_SEP = POSIX.sep
const SENSITIVE_DIR_NAMES = new Set([
  '.git',
  '.vscode',
  '.idea',
  '.claude',
  '.kode',
  '.ssh',
])
const SENSITIVE_FILE_NAMES = new Set([
  '.gitconfig',
  '.gitmodules',
  '.bashrc',
  '.bash_profile',
  '.zshrc',
  '.zprofile',
  '.profile',
  '.ripgreprc',
  '.mcp.json',
])

export function resolveLikeCliPath(
  inputPath: string,
  baseDir?: string,
): string {
  const base = baseDir ?? getCwd()
  if (typeof inputPath !== 'string') {
    throw new TypeError(`Path must be a string, received ${typeof inputPath}`)
  }
  if (typeof base !== 'string') {
    throw new TypeError(
      `Base directory must be a string, received ${typeof base}`,
    )
  }
  if (inputPath.includes('\0') || base.includes('\0')) {
    throw new Error('Path contains null bytes')
  }

  const trimmed = inputPath.trim()
  if (!trimmed) return path.resolve(base)

  if (trimmed === '~') return path.resolve(homedir())
  if (trimmed.startsWith('~/') || trimmed.startsWith('~\\')) {
    return path.resolve(homedir(), trimmed.slice(2))
  }

  if (process.platform === 'win32' && /^\/[a-z]\//i.test(trimmed)) {
    const driveLetter = trimmed[1]?.toUpperCase() ?? 'C'
    const rest = trimmed.slice(2)
    return path.resolve(`${driveLetter}:\\`, rest.replace(/\//g, '\\'))
  }

  return path.isAbsolute(trimmed)
    ? path.resolve(trimmed)
    : path.resolve(base, trimmed)
}

function toLower(value: string): string {
  return value.toLowerCase()
}

function toPosixPath(value: string): string {
  if (process.platform !== 'win32') return value

  const withSlashes = value.replace(/\\/g, '/')
  const driveMatch = withSlashes.match(/^([A-Za-z]):\/?(.*)$/)
  if (driveMatch) {
    const drive = driveMatch[1]!.toLowerCase()
    const rest = driveMatch[2] ?? ''
    return `/${drive}/${rest}`.replace(/\/+$/, '/')
  }

  if (withSlashes.startsWith('//')) return withSlashes
  return withSlashes
}

function posixRelative(fromPath: string, toPath: string): string {
  if (process.platform === 'win32') {
    return POSIX.relative(toPosixPath(fromPath), toPosixPath(toPath))
  }
  return POSIX.relative(fromPath, toPath)
}

export function expandSymlinkPaths(inputPath: string): string[] {
  const out = [inputPath]
  if (!existsSync(inputPath)) return out
  try {
    const resolved = realpathSync(inputPath)
    if (resolved && resolved !== inputPath) out.push(resolved)
  } catch {
  }
  return out
}

export function hasSuspiciousWindowsPathPattern(inputPath: string): boolean {
  const p = String(inputPath)

  if (p.indexOf(':', 2) !== -1) return true
  if (/~\d/.test(p)) return true
  if (
    p.startsWith('\\\\?\\') ||
    p.startsWith('\\\\.\\') ||
    p.startsWith('//?/') ||
    p.startsWith('//./')
  ) {
    return true
  }
  if (/[.\s]+$/.test(p)) return true
  if (/\.(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i.test(p)) return true
  if (/(^|\/|\\)\.{3,}(\/|\\|$)/.test(p)) return true
  if (matchesSuspiciousWindowsNetworkPathPatterns(p)) return true

  return false
}

function matchesSuspiciousWindowsNetworkPathPatterns(
  inputPath: string,
): boolean {
  if (process.platform !== 'win32') return false
  const p = String(inputPath)
  if (/\\\\[a-zA-Z0-9._\-:[\]%]+(?:@(?:\d+|ssl))?\\/i.test(p)) return true
  if (/\/\/[a-zA-Z0-9._\-:[\]%]+(?:@(?:\d+|ssl))?\//i.test(p)) return true
  if (/@SSL@\d+/i.test(p) || /@\d+@SSL/i.test(p)) return true
  if (/DavWWWRoot/i.test(p)) return true
  if (/^\\\\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\\/]/.test(p)) return true
  if (/^\/\/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\\/]/.test(p)) return true
  if (/^\\\\(\[[\da-fA-F:]+\])[\\/]/.test(p)) return true
  if (/^\/\/(\[[\da-fA-F:]+\])[\\/]/.test(p)) return true
  return false
}

export function isSensitiveFilePath(inputPath: string): boolean {
  const p = String(inputPath)
  if (p.startsWith('\\\\') || p.startsWith('//')) return true

  const absolutePath = resolveLikeCliPath(p)
  const parts = toPosixPath(absolutePath).split(POSIX_SEP)
  const basename = parts[parts.length - 1] ?? ''

  for (const part of parts) {
    if (SENSITIVE_DIR_NAMES.has(toLower(part))) return true
  }
  if (basename && SENSITIVE_FILE_NAMES.has(toLower(basename))) return true
  return false
}

function getSettingsPathsForWriteProtection(options?: {
  projectDir?: string
  homeDir?: string
}): string[] {
  const projectDir = options?.projectDir ?? getOriginalCwd()
  const homeDir = options?.homeDir ?? homedir()
  const destinations: ToolPermissionUpdateDestination[] = [
    'userSettings',
    'projectSettings',
    'localSettings',
  ]
  const out: string[] = []
  for (const destination of destinations) {
    const candidates = getSettingsFileCandidates({
      destination: destination as any,
      projectDir,
      homeDir,
    })
    if (!candidates) continue
    out.push(candidates.primary)
    out.push(...candidates.legacy)
  }
  return Array.from(new Set(out))
}

export function isWriteProtectedPath(
  inputPath: string,
  options?: {
    projectDir?: string
    homeDir?: string
  },
): boolean {
  const absolutePath = resolveLikeCliPath(inputPath)
  const normalized = toLower(toPosixPath(absolutePath))

  const settingsPaths = new Set(
    getSettingsPathsForWriteProtection(options).map(p =>
      toLower(toPosixPath(resolveLikeCliPath(p))),
    ),
  )

  if (normalized.endsWith('/.claude/settings.json')) return true
  if (normalized.endsWith('/.claude/settings.local.json')) return true
  if (normalized.endsWith('/.kode/settings.json')) return true
  if (normalized.endsWith('/.kode/settings.local.json')) return true
  if (settingsPaths.has(normalized)) return true

  const projectRoot = options?.projectDir ?? getOriginalCwd()
  const projectRootPosix = toPosixPath(resolveLikeCliPath(projectRoot))
  const protectedDirs = [
    POSIX.join(projectRootPosix, '.claude', 'commands'),
    POSIX.join(projectRootPosix, '.claude', 'agents'),
    POSIX.join(projectRootPosix, '.claude', 'skills'),
    POSIX.join(projectRootPosix, '.kode', 'commands'),
    POSIX.join(projectRootPosix, '.kode', 'agents'),
    POSIX.join(projectRootPosix, '.kode', 'skills'),
  ]

  for (const dir of protectedDirs) {
    if (isPosixSubpath(dir, toPosixPath(absolutePath))) return true
  }

  return false
}

function hasParentTraversalSegment(relativePath: string): boolean {
  return /(?:^|[\\/])\.\.(?:[\\/]|$)/.test(relativePath)
}

function normalizeMacPrivatePrefix(input: string): string {
  return input
    .replace(/^\/private\/var\//, '/var/')
    .replace(/^\/private\/tmp(\/|$)/, '/tmp$1')
}

function isPosixSubpath(base: string, target: string): boolean {
  const rel = POSIX.relative(base, target)
  if (rel === '') return true
  if (hasParentTraversalSegment(rel)) return false
  if (POSIX.isAbsolute(rel)) return false
  return true
}

export function isPathInWorkingDirectories(
  inputPath: string,
  context: ToolPermissionContext,
): boolean {
  const roots = new Set<string>([
    getOriginalCwd(),
    ...Array.from(context.additionalWorkingDirectories.keys()),
  ])

  return expandSymlinkPaths(inputPath).every(candidate => {
    return Array.from(roots).some(root => {
      const resolvedCandidate = resolveLikeCliPath(candidate)
      const resolvedRoot = resolveLikeCliPath(root)
      const candidatePosix = normalizeMacPrivatePrefix(
        toPosixPath(resolvedCandidate),
      )
      const rootPosix = normalizeMacPrivatePrefix(toPosixPath(resolvedRoot))
      const relative = posixRelative(
        toLower(rootPosix),
        toLower(candidatePosix),
      )
      if (relative === '') return true
      if (hasParentTraversalSegment(relative)) return false
      if (POSIX.isAbsolute(relative)) return false
      return true
    })
  })
}

function operationToolName(
  operation: FilePermissionOperation,
): 'Read' | 'Edit' {
  return operation === 'read' ? 'Read' : 'Edit'
}

function parseToolRule(ruleString: string): ToolRuleValue | null {
  if (typeof ruleString !== 'string') return null
  const trimmed = ruleString.trim()
  if (!trimmed) return null
  const openParen = trimmed.indexOf('(')
  if (openParen === -1) return { toolName: trimmed }
  if (!trimmed.endsWith(')')) return null
  const toolName = trimmed.slice(0, openParen)
  const ruleContent = trimmed.slice(openParen + 1, -1).trim()
  if (!toolName) return null
  return { toolName, ruleContent: ruleContent || undefined }
}

function collectRuleEntries(args: {
  context: ToolPermissionContext
  operation: FilePermissionOperation
  behavior: FilePermissionBehavior
}): ToolRuleEntry[] {
  const toolName = operationToolName(args.operation)

  const groups =
    args.behavior === 'allow'
      ? args.context.alwaysAllowRules
      : args.behavior === 'deny'
        ? args.context.alwaysDenyRules
        : args.context.alwaysAskRules

  const out: ToolRuleEntry[] = []
  for (const [source, rules] of Object.entries(groups) as Array<
    [ToolPermissionUpdateDestination, string[]]
  >) {
    if (!Array.isArray(rules)) continue
    for (const ruleString of rules) {
      if (typeof ruleString !== 'string') continue
      const parsed = parseToolRule(ruleString)
      if (!parsed) continue
      if (parsed.toolName !== toolName) continue
      if (!parsed.ruleContent) continue
      out.push({ source, ruleValue: parsed, ruleString })
    }
  }
  return out
}

function rootPathForSource(source: ToolPermissionUpdateDestination): string {
  switch (source) {
    case 'cliArg':
    case 'command':
    case 'session':
      return resolveLikeCliPath(getOriginalCwd())
    case 'userSettings':
      return resolveLikeCliPath(getKodeBaseDir())
    case 'policySettings':
    case 'projectSettings':
    case 'localSettings':
    case 'flagSettings':
      return resolveLikeCliPath(getOriginalCwd())
    default:
      return resolveLikeCliPath(getOriginalCwd())
  }
}

function splitRulePatternByRoot(args: {
  ruleContent: string
  source: ToolPermissionUpdateDestination
}): { relativePattern: string; root: string | null } {
  const pattern = args.ruleContent

  if (pattern.startsWith(`${POSIX_SEP}${POSIX_SEP}`)) {
    const rest = pattern.slice(1)
    if (process.platform === 'win32' && /^\/[a-z]\//i.test(rest)) {
      const driveLetter = rest[1]?.toUpperCase() ?? 'C'
      const remaining = rest.slice(2)
      return {
        relativePattern: remaining.startsWith('/')
          ? remaining.slice(1)
          : remaining,
        root: `${driveLetter}:\\`,
      }
    }
    return { relativePattern: rest, root: POSIX_SEP }
  }

  if (pattern.startsWith(`~${POSIX_SEP}`)) {
    return { relativePattern: pattern.slice(1), root: homedir() }
  }

  if (pattern.startsWith(POSIX_SEP)) {
    return { relativePattern: pattern, root: rootPathForSource(args.source) }
  }

  const withoutDot = pattern.startsWith(`.${POSIX_SEP}`)
    ? pattern.slice(2)
    : pattern
  return { relativePattern: withoutDot, root: null }
}

function buildIgnoreMatcher(patterns: string[]): Ignore {
  return ignore().add(patterns)
}

export function matchPermissionRuleForPath(args: {
  inputPath: string
  toolPermissionContext: ToolPermissionContext
  operation: FilePermissionOperation
  behavior: FilePermissionBehavior
}): string | null {
  const resolved = resolveLikeCliPath(args.inputPath)
  const targetPosix = toPosixPath(resolved)

  const entries = collectRuleEntries({
    context: args.toolPermissionContext,
    operation: args.operation,
    behavior: args.behavior,
  })

  const grouped = new Map<string | null, Map<string, ToolRuleEntry>>()
  for (const entry of entries) {
    const { relativePattern, root } = splitRulePatternByRoot({
      ruleContent: entry.ruleValue.ruleContent!,
      source: entry.source,
    })
    const existing = grouped.get(root)
    if (existing) {
      existing.set(relativePattern, entry)
    } else {
      grouped.set(root, new Map([[relativePattern, entry]]))
    }
  }

  for (const [root, patternsMap] of grouped.entries()) {
    const baseRoot = root ?? getCwd()
    const relative = posixRelative(baseRoot, targetPosix)
    if (relative.startsWith(`..${POSIX_SEP}`)) continue
    if (!relative) continue

    const matchAll =
      patternsMap.get('/**')?.ruleString ??
      patternsMap.get('**')?.ruleString ??
      null
    if (matchAll) return matchAll

    const patterns = Array.from(patternsMap.keys()).map(pattern => {
      let candidate = pattern
      if (root === POSIX_SEP && pattern.startsWith(POSIX_SEP)) {
        candidate = pattern.slice(1)
      }
      if (candidate.endsWith('/**')) {
        candidate = candidate.slice(0, -3)
      }
      return candidate
    })

    const matcher = buildIgnoreMatcher(patterns)
    const result = matcher.test(relative)
    if (!result.ignored || !result.rule) continue

    let matched = result.rule.pattern
    const matchedWithGlob = `${matched}/**`
    if (patternsMap.has(matchedWithGlob)) {
      return patternsMap.get(matchedWithGlob)?.ruleString ?? null
    }

    if (root === POSIX_SEP && !matched.startsWith(POSIX_SEP)) {
      matched = `${POSIX_SEP}${matched}`
      const matchedGlob = `${matched}/**`
      if (patternsMap.has(matchedGlob)) {
        return patternsMap.get(matchedGlob)?.ruleString ?? null
      }
      return patternsMap.get(matched)?.ruleString ?? null
    }

    return patternsMap.get(matched)?.ruleString ?? null
  }

  return null
}

export function getWriteSafetyCheckForPath(
  inputPath: string,
): { safe: true } | { safe: false; message: string } {
  const candidates = expandSymlinkPaths(inputPath)
  for (const candidate of candidates) {
    if (hasSuspiciousWindowsPathPattern(candidate)) {
      return {
        safe: false,
        message: `${PRODUCT_NAME} requested permissions to write to ${inputPath}, which contains a suspicious Windows path pattern that requires manual approval.`,
      }
    }
  }

  for (const candidate of candidates) {
    if (isWriteProtectedPath(candidate)) {
      return {
        safe: false,
        message: `${PRODUCT_NAME} requested permissions to write to ${inputPath}, but you haven't granted it yet.`,
      }
    }
  }

  for (const candidate of candidates) {
    if (isSensitiveFilePath(candidate)) {
      return {
        safe: false,
        message: `${PRODUCT_NAME} requested permissions to edit ${inputPath} which is a sensitive file.`,
      }
    }
  }

  return { safe: true }
}

export function getPlanFileWritePrivilegeForContext(context: ToolUseContext): string {
  const conversationKey = getPlanConversationKey(context)
  return getPlanFilePath(context.agentId, conversationKey)
}

export function isPlanFileForContext(args: {
  inputPath: string
  context: ToolUseContext
}): boolean {
  const expected = resolveLikeCliPath(
    getPlanFileWritePrivilegeForContext(args.context),
  )
  const actual = resolveLikeCliPath(args.inputPath)
  return actual === expected
}

function getDirectoryForSuggestions(inputPath: string): string {
  const absolute = resolveLikeCliPath(inputPath)
  try {
    if (statSync(absolute).isDirectory()) return absolute
  } catch {}
  return path.dirname(absolute)
}

function makeReadAllowRuleForDirectory(dirPath: string): string | null {
  try {
    if (!statSync(dirPath).isDirectory()) return null
  } catch {
    return null
  }

  const posixDir = toPosixPath(dirPath)
  if (posixDir === POSIX_SEP) return null

  const ruleContent = POSIX.isAbsolute(posixDir)
    ? `/${posixDir}/**`
    : `${posixDir}/**`
  return `Read(${ruleContent})`
}

export function suggestFilePermissionUpdates(args: {
  inputPath: string
  operation: 'read' | 'write' | 'create'
  toolPermissionContext: ToolPermissionContext
}): ToolPermissionContextUpdate[] {
  const isOutsideWorkingDirs = !isPathInWorkingDirectories(
    args.inputPath,
    args.toolPermissionContext,
  )

  if (args.operation === 'read' && isOutsideWorkingDirs) {
    const dirPath = getDirectoryForSuggestions(args.inputPath)
    return expandSymlinkPaths(dirPath).flatMap(dir => {
      const rule = makeReadAllowRuleForDirectory(dir)
      if (!rule) return []
      const update: ToolPermissionContextUpdate = {
        type: 'addRules',
        behavior: 'allow',
        destination: 'session',
        rules: [rule],
      }
      return [update]
    })
  }

  if (args.operation === 'write' || args.operation === 'create') {
    const updates: ToolPermissionContextUpdate[] = [
      { type: 'setMode', mode: 'acceptEdits', destination: 'session' },
    ]
    if (isOutsideWorkingDirs) {
      const dirPath = getDirectoryForSuggestions(args.inputPath)
      updates.push({
        type: 'addDirectories',
        directories: expandSymlinkPaths(dirPath),
        destination: 'session',
      })
    }
    return updates
  }

  return [{ type: 'setMode', mode: 'acceptEdits', destination: 'session' }]
}

export function getSpecialAllowedReadReason(args: {
  inputPath: string
  context: ToolUseContext
}): string | null {
  const absolute = resolveLikeCliPath(args.inputPath)

  const conversationKey = getPlanConversationKey(args.context)

  const baseDirResolved = resolveLikeCliPath(getKodeBaseDir())

  const bashOutputsDir = resolveLikeCliPath(
    path.join(baseDirResolved, 'bash-outputs', conversationKey),
  )
  const bashOutputsDirPosix = toPosixPath(bashOutputsDir)
  const absPosix = toPosixPath(absolute)
  if (
    absPosix === bashOutputsDirPosix ||
    absPosix.startsWith(`${bashOutputsDirPosix}${POSIX_SEP}`)
  ) {
    return 'Bash output files from current session are allowed for reading'
  }

  if (isPlanFileForContext({ inputPath: absolute, context: args.context })) {
    return 'Plan files for current session are allowed for reading'
  }

  const memoryDir = resolveLikeCliPath(path.join(baseDirResolved, 'memory'))
  const memoryDirPosix = toPosixPath(memoryDir)
  if (
    absPosix === memoryDirPosix ||
    absPosix.startsWith(`${memoryDirPosix}${POSIX_SEP}`)
  ) {
    return 'Session memory files are allowed for reading'
  }

  const toolResultsDir = resolveLikeCliPath(
    path.join(baseDirResolved, 'tool-results', conversationKey),
  )
  const toolResultsDirPosix = toPosixPath(toolResultsDir)
  if (
    absPosix === toolResultsDirPosix ||
    absPosix.startsWith(`${toolResultsDirPosix}${POSIX_SEP}`)
  ) {
    return 'Tool result files are allowed for reading'
  }

  const projectDir = process.cwd().replace(/[^a-zA-Z0-9]/g, '-')
  const tasksDir = resolveLikeCliPath(path.join(baseDirResolved, projectDir, 'tasks'))
  const tasksDirPosix = toPosixPath(tasksDir)
  if (
    absPosix === tasksDirPosix ||
    absPosix.startsWith(`${tasksDirPosix}${POSIX_SEP}`)
  ) {
    return 'Project temp directory files are allowed for reading'
  }

  return null
}
