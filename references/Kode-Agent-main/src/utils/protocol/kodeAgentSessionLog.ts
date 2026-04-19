import { execFileSync } from 'child_process'
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from 'fs'
import { randomBytes } from 'crypto'
import { dirname, join } from 'path'
import type { Message } from '@query'
import { MACRO } from '@constants/macros'
import { getCwd } from '@utils/state'
import { getKodeAgentSessionId } from './kodeAgentSessionId'
import { getKodeBaseDir } from '@utils/config/env'
import {
  PLAN_SLUG_ADJECTIVES,
  PLAN_SLUG_NOUNS,
  PLAN_SLUG_VERBS,
} from '@utils/plan/planSlugWords'

type PersistTarget =
  | { kind: 'session'; sessionId: string }
  | { kind: 'agent'; agentId: string }

type JsonlEnvelopeBase = {
  cwd: string
  sessionId: string
  version: string
  gitBranch?: string
  userType: string
  isSidechain: boolean
  parentUuid: string | null
  logicalParentUuid?: string
  agentId: string
  slug: string
  uuid: string
  timestamp: string
}

type SessionJsonlEntry =
  | (JsonlEnvelopeBase & {
      type: 'user'
      message: any
      toolUseResult?: any
    })
  | (JsonlEnvelopeBase & {
      type: 'assistant'
      message: any
      requestId?: string
      isApiErrorMessage?: boolean
    })
  | { type: 'summary'; summary: string; leafUuid: string }
  | { type: 'custom-title'; sessionId: string; customTitle: string }
  | { type: 'tag'; sessionId: string; tag: string }
  | {
      type: 'file-history-snapshot'
      messageId: string
      snapshot: {
        messageId: string
        trackedFileBackups: Record<string, unknown>
        timestamp: string
      }
      isSnapshotUpdate: boolean
    }

function getSessionStoreBaseDir(): string {
  return getKodeBaseDir()
}

export function sanitizeProjectNameForSessionStore(cwd: string): string {
  return cwd.replace(/[^a-zA-Z0-9]/g, '-')
}

export function getSessionProjectsDir(): string {
  return join(getSessionStoreBaseDir(), 'projects')
}

export function getSessionProjectDir(cwd: string): string {
  return join(getSessionProjectsDir(), sanitizeProjectNameForSessionStore(cwd))
}

export function getSessionLogFilePath(args: {
  cwd: string
  sessionId: string
}): string {
  return join(getSessionProjectDir(args.cwd), `${args.sessionId}.jsonl`)
}

export function getAgentLogFilePath(args: {
  cwd: string
  agentId: string
}): string {
  return join(getSessionProjectDir(args.cwd), `agent-${args.agentId}.jsonl`)
}

function safeMkdir(dir: string): void {
  if (existsSync(dir)) return
  mkdirSync(dir, { recursive: true })
}

function safeEnsureFile(path: string): void {
  safeMkdir(dirname(path))
  if (!existsSync(path)) writeFileSync(path, '', 'utf8')
}

function safeAppendJsonl(path: string, record: unknown): void {
  try {
    safeEnsureFile(path)
    appendFileSync(path, JSON.stringify(record) + '\n', 'utf8')
  } catch {
  }
}

const lastUuidByFile = new Map<string, string | null>()
const snapshotWrittenByFile = new Set<string>()
const slugBySessionId = new Map<string, string>()
let currentSessionCustomTitle: string | null = null
let currentSessionTag: string | null = null

type LastPersistedInfo = { uuid: string | null; slug: string | null }

function safeReadLastPersistedInfo(filePath: string): LastPersistedInfo {
  try {
    if (!existsSync(filePath)) return { uuid: null, slug: null }
    const content = readFileSync(filePath, 'utf8')
    const lines = content.split('\n')

    let lastSlug: string | null = null
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i]?.trim()
      if (!line) continue
      let parsed: any
      try {
        parsed = JSON.parse(line)
      } catch {
        continue
      }
      if (!parsed || typeof parsed !== 'object') continue

      if (!lastSlug && typeof parsed.slug === 'string' && parsed.slug.trim()) {
        lastSlug = parsed.slug.trim()
      }

      if (typeof parsed.uuid === 'string' && parsed.uuid) {
        return { uuid: parsed.uuid, slug: lastSlug }
      }
    }

    return { uuid: null, slug: lastSlug }
  } catch {
    return { uuid: null, slug: null }
  }
}

function pickIndex(length: number): number {
  return randomBytes(4).readUInt32BE(0) % length
}

function pickWord(words: readonly string[]): string {
  return words[pickIndex(words.length)]!
}

function generateSessionSlug(): string {
  const adjective = pickWord(PLAN_SLUG_ADJECTIVES)
  const verb = pickWord(PLAN_SLUG_VERBS)
  const noun = pickWord(PLAN_SLUG_NOUNS)
  return `${adjective}-${verb}-${noun}`
}

function getOrCreateSessionSlug(sessionId: string): string {
  const existing = slugBySessionId.get(sessionId)
  if (existing) return existing
  const slug = generateSessionSlug()
  slugBySessionId.set(sessionId, slug)
  return slug
}

type GitBranchCacheEntry = { cwd: string; value: string | undefined }
let gitBranchCache: GitBranchCacheEntry | null = null

function getGitBranchBestEffort(cwd: string): string | undefined {
  if (gitBranchCache && gitBranchCache.cwd === cwd) return gitBranchCache.value

  let value: string | undefined
  try {
    const stdout = execFileSync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], {
      cwd,
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 750,
    })
    const branch = stdout.toString('utf8').trim()
    value = branch || undefined
  } catch {
    value = undefined
  }

  gitBranchCache = { cwd, value }
  return value
}

function ensureFileHistorySnapshot(
  filePath: string,
  firstMessageUuid: string,
): void {
  if (snapshotWrittenByFile.has(filePath)) return

  try {
    safeEnsureFile(filePath)
    const size = statSync(filePath).size
    if (size > 0) {
      snapshotWrittenByFile.add(filePath)
      return
    }
  } catch {
  }

  const now = new Date().toISOString()
  safeAppendJsonl(filePath, {
    type: 'file-history-snapshot',
    messageId: firstMessageUuid,
    snapshot: {
      messageId: firstMessageUuid,
      trackedFileBackups: {},
      timestamp: now,
    },
    isSnapshotUpdate: false,
  } satisfies SessionJsonlEntry)

  snapshotWrittenByFile.add(filePath)
}

function resolvePersistTarget(toolUseContext: {
  agentId?: string
}): PersistTarget {
  const agentId = toolUseContext.agentId
  if (agentId && agentId !== 'main') return { kind: 'agent', agentId }
  return { kind: 'session', sessionId: getKodeAgentSessionId() }
}

export function appendSessionJsonlFromMessage(args: {
  message: Message
  toolUseContext: { agentId?: string }
}): void {
  const { message, toolUseContext } = args
  if (message.type !== 'user' && message.type !== 'assistant') return

  const cwd = getCwd()
  const userType = (process.env.USER_TYPE ?? 'external').trim() || 'external'
  const sessionId = getKodeAgentSessionId()
  const agentId = (toolUseContext.agentId ?? 'main').trim() || 'main'
  const isSidechain = agentId !== 'main'
  const gitBranch = getGitBranchBestEffort(cwd)

  const target = resolvePersistTarget(toolUseContext)
  const filePath =
    target.kind === 'agent'
      ? getAgentLogFilePath({ cwd, agentId: target.agentId })
      : getSessionLogFilePath({ cwd, sessionId: target.sessionId })

  if (!lastUuidByFile.has(filePath)) {
    const info = safeReadLastPersistedInfo(filePath)
    lastUuidByFile.set(filePath, info.uuid)
    if (info.slug) slugBySessionId.set(sessionId, info.slug)
  }
  const previousUuid = lastUuidByFile.get(filePath) ?? null

  const slug = getOrCreateSessionSlug(sessionId)

  if (target.kind === 'session') {
    ensureFileHistorySnapshot(filePath, message.uuid)
  }

  const base: JsonlEnvelopeBase = {
    parentUuid: previousUuid,
    logicalParentUuid: undefined,
    isSidechain,
    userType,
    cwd,
    sessionId,
    version: MACRO.VERSION,
    ...(gitBranch ? { gitBranch } : {}),
    agentId,
    slug,
    uuid: message.uuid,
    timestamp: new Date().toISOString(),
  }

  const record: SessionJsonlEntry =
    message.type === 'user'
      ? {
          ...base,
          type: 'user',
          message: message.message,
          ...(message.toolUseResult?.data !== undefined
            ? { toolUseResult: message.toolUseResult.data }
            : {}),
        }
      : {
          ...base,
          type: 'assistant',
          message: message.message,
          ...(typeof (message as any).requestId === 'string'
            ? { requestId: String((message as any).requestId) }
            : {}),
          ...(message.isApiErrorMessage ? { isApiErrorMessage: true } : {}),
        }

  safeAppendJsonl(filePath, record)
  lastUuidByFile.set(filePath, message.uuid)
}

export function appendSessionSummaryRecord(args: {
  summary: string
  leafUuid: string
  sessionId?: string
}): void {
  const sessionId = args.sessionId ?? getKodeAgentSessionId()
  const cwd = getCwd()
  safeAppendJsonl(getSessionLogFilePath({ cwd, sessionId }), {
    type: 'summary',
    summary: args.summary,
    leafUuid: args.leafUuid,
  } satisfies SessionJsonlEntry)
}

export function appendSessionCustomTitleRecord(args: {
  sessionId: string
  customTitle: string
}): void {
  const cwd = getCwd()
  safeAppendJsonl(getSessionLogFilePath({ cwd, sessionId: args.sessionId }), {
    type: 'custom-title',
    sessionId: args.sessionId,
    customTitle: args.customTitle,
  } satisfies SessionJsonlEntry)
  if (args.sessionId === getKodeAgentSessionId()) {
    currentSessionCustomTitle = args.customTitle
  }
}

export function appendSessionTagRecord(args: {
  sessionId: string
  tag: string
}): void {
  const cwd = getCwd()
  safeAppendJsonl(getSessionLogFilePath({ cwd, sessionId: args.sessionId }), {
    type: 'tag',
    sessionId: args.sessionId,
    tag: args.tag,
  } satisfies SessionJsonlEntry)
  if (args.sessionId === getKodeAgentSessionId()) {
    currentSessionTag = args.tag
  }
}

export function getCurrentSessionCustomTitle(): string | null {
  return currentSessionCustomTitle
}

export function getCurrentSessionTag(): string | null {
  return currentSessionTag
}

export function resetSessionJsonlStateForTests(): void {
  lastUuidByFile.clear()
  snapshotWrittenByFile.clear()
  slugBySessionId.clear()
  gitBranchCache = null
  currentSessionCustomTitle = null
  currentSessionTag = null
}
