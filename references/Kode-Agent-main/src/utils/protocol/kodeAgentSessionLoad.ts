import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { basename, join } from 'path'
import type { Message } from '@query'
import type {
  Message as APIMessage,
  MessageParam,
} from '@anthropic-ai/sdk/resources/index.mjs'
import { getSessionProjectDir } from './kodeAgentSessionLog'
import { isUuid } from '@utils/text/uuid'

type JsonlUserEntry = {
  type: 'user'
  sessionId?: string
  uuid?: string
  message?: MessageParam
  isApiErrorMessage?: boolean
  toolUseResult?: unknown
}

type JsonlAssistantEntry = {
  type: 'assistant'
  sessionId?: string
  uuid?: string
  message?: APIMessage
  isApiErrorMessage?: boolean
  requestId?: string
}

type JsonlSummaryEntry = {
  type: 'summary'
  summary?: string
  leafUuid?: string
}

type JsonlCustomTitleEntry = {
  type: 'custom-title'
  sessionId?: string
  customTitle?: string
}

type JsonlTagEntry = {
  type: 'tag'
  sessionId?: string
  tag?: string
}

type JsonlFileHistorySnapshotEntry = {
  type: 'file-history-snapshot'
  messageId?: string
  snapshot?: unknown
  isSnapshotUpdate?: boolean
}

type JsonlEntry =
  | JsonlUserEntry
  | JsonlAssistantEntry
  | JsonlSummaryEntry
  | JsonlCustomTitleEntry
  | JsonlTagEntry
  | JsonlFileHistorySnapshotEntry
  | Record<string, unknown>

function safeParseJson(line: string): unknown | null {
  try {
    return JSON.parse(line)
  } catch {
    return null
  }
}

function isUserEntry(entry: JsonlEntry): entry is JsonlUserEntry {
  return (
    typeof (entry as any)?.type === 'string' && (entry as any).type === 'user'
  )
}

function isAssistantEntry(entry: JsonlEntry): entry is JsonlAssistantEntry {
  return (
    typeof (entry as any)?.type === 'string' &&
    (entry as any).type === 'assistant'
  )
}

function isSummaryEntry(entry: JsonlEntry): entry is JsonlSummaryEntry {
  return (
    typeof (entry as any)?.type === 'string' &&
    (entry as any).type === 'summary'
  )
}

function isCustomTitleEntry(entry: JsonlEntry): entry is JsonlCustomTitleEntry {
  return (
    typeof (entry as any)?.type === 'string' &&
    (entry as any).type === 'custom-title'
  )
}

function isTagEntry(entry: JsonlEntry): entry is JsonlTagEntry {
  return (
    typeof (entry as any)?.type === 'string' && (entry as any).type === 'tag'
  )
}

function isFileHistorySnapshotEntry(
  entry: JsonlEntry,
): entry is JsonlFileHistorySnapshotEntry {
  return (
    typeof (entry as any)?.type === 'string' &&
    (entry as any).type === 'file-history-snapshot'
  )
}

function normalizeLoadedUser(entry: JsonlUserEntry): Message | null {
  if (!entry.uuid || !entry.message) return null
  return {
    type: 'user',
    uuid: entry.uuid as any,
    message: entry.message as any,
    ...(entry.toolUseResult !== undefined
      ? { toolUseResult: { data: entry.toolUseResult, resultForAssistant: '' } }
      : {}),
  }
}

function normalizeLoadedAssistant(entry: JsonlAssistantEntry): Message | null {
  if (!entry.uuid || !entry.message) return null
  return {
    type: 'assistant',
    uuid: entry.uuid as any,
    costUSD: 0,
    durationMs: 0,
    message: entry.message as any,
    ...(entry.isApiErrorMessage ? { isApiErrorMessage: true } : {}),
    ...(typeof entry.requestId === 'string'
      ? { requestId: entry.requestId }
      : {}),
  } as any
}

export type KodeAgentSessionLogData = {
  messages: Message[]
  summaries: Map<string, string>
  customTitles: Map<string, string>
  tags: Map<string, string>
  fileHistorySnapshots: Map<string, JsonlFileHistorySnapshotEntry>
}

export function loadKodeAgentSessionLogData(args: {
  cwd: string
  sessionId: string
}): KodeAgentSessionLogData {
  const { cwd, sessionId } = args
  const projectDir = getSessionProjectDir(cwd)
  const filePath = join(projectDir, `${sessionId}.jsonl`)
  if (!existsSync(filePath)) {
    throw new Error(`No conversation found with session ID: ${sessionId}`)
  }

  const lines = readFileSync(filePath, 'utf8').split('\n')
  const messages: Message[] = []
  const summaries = new Map<string, string>()
  const customTitles = new Map<string, string>()
  const tags = new Map<string, string>()
  const fileHistorySnapshots = new Map<string, JsonlFileHistorySnapshotEntry>()

  for (const line of lines) {
    const raw = safeParseJson(line.trim())
    if (!raw || typeof raw !== 'object') continue
    const entry = raw as JsonlEntry

    if (isUserEntry(entry)) {
      if (entry.sessionId && entry.sessionId !== sessionId) continue
      const msg = normalizeLoadedUser(entry)
      if (msg) messages.push(msg)
      continue
    }

    if (isAssistantEntry(entry)) {
      if (entry.sessionId && entry.sessionId !== sessionId) continue
      const msg = normalizeLoadedAssistant(entry)
      if (msg) messages.push(msg)
      continue
    }

    if (isSummaryEntry(entry)) {
      const leafUuid = typeof entry.leafUuid === 'string' ? entry.leafUuid : ''
      const summary = typeof entry.summary === 'string' ? entry.summary : ''
      if (leafUuid && summary) summaries.set(leafUuid, summary)
      continue
    }

    if (isCustomTitleEntry(entry)) {
      const id = typeof entry.sessionId === 'string' ? entry.sessionId : ''
      const title =
        typeof entry.customTitle === 'string' ? entry.customTitle : ''
      if (id && title) customTitles.set(id, title)
      continue
    }

    if (isTagEntry(entry)) {
      const id = typeof entry.sessionId === 'string' ? entry.sessionId : ''
      const tag = typeof entry.tag === 'string' ? entry.tag : ''
      if (id && tag) tags.set(id, tag)
      continue
    }

    if (isFileHistorySnapshotEntry(entry)) {
      const messageId =
        typeof entry.messageId === 'string' ? entry.messageId : ''
      if (messageId) fileHistorySnapshots.set(messageId, entry)
      continue
    }
  }

  return { messages, summaries, customTitles, tags, fileHistorySnapshots }
}

export function loadKodeAgentSessionMessages(args: {
  cwd: string
  sessionId: string
}): Message[] {
  return loadKodeAgentSessionLogData(args).messages
}

export function findMostRecentKodeAgentSessionId(cwd: string): string | null {
  const projectDir = getSessionProjectDir(cwd)
  if (!existsSync(projectDir)) return null

  const candidates = readdirSync(projectDir)
    .filter(name => name.endsWith('.jsonl'))
    .filter(name => !name.startsWith('agent-'))
    .map(name => ({
      sessionId: basename(name, '.jsonl'),
      path: join(projectDir, name),
    }))
    .filter(c => isUuid(c.sessionId))

  if (candidates.length === 0) return null

  candidates.sort((a, b) => {
    try {
      return statSync(b.path).mtimeMs - statSync(a.path).mtimeMs
    } catch {
      return 0
    }
  })

  return candidates[0]?.sessionId ?? null
}
