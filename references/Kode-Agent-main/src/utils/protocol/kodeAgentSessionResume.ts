import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { basename, join } from 'path'
import {
  getSessionProjectDir,
  getSessionProjectsDir,
} from './kodeAgentSessionLog'
import { isUuid } from '@utils/text/uuid'

export type KodeAgentSessionListItem = {
  sessionId: string
  slug: string | null
  customTitle: string | null
  tag: string | null
  summary: string | null
  cwd: string | null
  createdAt: Date | null
  modifiedAt: Date | null
}

export type ResumeResolveResult =
  | { kind: 'ok'; sessionId: string }
  | { kind: 'ambiguous'; identifier: string; matchingSessionIds: string[] }
  | { kind: 'different_directory'; sessionId: string; otherCwd: string | null }
  | { kind: 'not_found'; identifier: string }

function safeParseJson(line: string): unknown | null {
  try {
    return JSON.parse(line)
  } catch {
    return null
  }
}

function safeParseDate(value: unknown): Date | null {
  if (typeof value !== 'string') return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d
}

function readSessionListItemBestEffort(args: {
  filePath: string
  sessionId: string
}): Omit<KodeAgentSessionListItem, 'sessionId'> {
  const { filePath, sessionId } = args

  let slug: string | null = null
  let cwd: string | null = null
  let createdAt: Date | null = null
  let modifiedAt: Date | null = null
  let customTitle: string | null = null
  let tag: string | null = null
  let lastAssistantUuid: string | null = null
  const summariesByLeaf = new Map<string, string>()
  let lastSummary: string | null = null

  try {
    modifiedAt = new Date(statSync(filePath).mtimeMs)
  } catch {
    modifiedAt = null
  }

  let content: string
  try {
    content = readFileSync(filePath, 'utf8')
  } catch {
    return {
      slug,
      customTitle,
      tag,
      summary: null,
      cwd,
      createdAt,
      modifiedAt,
    }
  }

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const parsed = safeParseJson(line)
    if (!parsed || typeof parsed !== 'object') continue

    const entry: any = parsed

    if (!slug && typeof entry.slug === 'string' && entry.slug.trim()) {
      slug = entry.slug.trim()
    }
    if (!cwd && typeof entry.cwd === 'string' && entry.cwd.trim()) {
      cwd = entry.cwd.trim()
    }
    if (!createdAt) {
      const ts = safeParseDate(entry.timestamp)
      if (ts) createdAt = ts
    }

    if (typeof entry.type !== 'string') continue

    if (entry.type === 'assistant') {
      if (typeof entry.uuid === 'string' && entry.uuid)
        lastAssistantUuid = entry.uuid
      continue
    }

    if (entry.type === 'summary') {
      const leafUuid = typeof entry.leafUuid === 'string' ? entry.leafUuid : ''
      const summary = typeof entry.summary === 'string' ? entry.summary : ''
      if (leafUuid && summary) {
        summariesByLeaf.set(leafUuid, summary)
        lastSummary = summary
      }
      continue
    }

    if (entry.type === 'custom-title') {
      const id = typeof entry.sessionId === 'string' ? entry.sessionId : ''
      const title =
        typeof entry.customTitle === 'string' ? entry.customTitle : ''
      if (id === sessionId && title) customTitle = title
      continue
    }

    if (entry.type === 'tag') {
      const id = typeof entry.sessionId === 'string' ? entry.sessionId : ''
      const t = typeof entry.tag === 'string' ? entry.tag : ''
      if (id === sessionId && t) tag = t
      continue
    }
  }

  const summary =
    (lastAssistantUuid
      ? (summariesByLeaf.get(lastAssistantUuid) ?? null)
      : null) ??
    lastSummary ??
    null

  return {
    slug,
    customTitle,
    tag,
    summary,
    cwd,
    createdAt,
    modifiedAt,
  }
}

export function listKodeAgentSessions(args: {
  cwd: string
}): KodeAgentSessionListItem[] {
  const { cwd } = args
  const projectDir = getSessionProjectDir(cwd)
  if (!existsSync(projectDir)) return []

  const candidates = readdirSync(projectDir)
    .filter(name => name.endsWith('.jsonl'))
    .filter(name => !name.startsWith('agent-'))
    .map(name => ({
      sessionId: basename(name, '.jsonl'),
      filePath: join(projectDir, name),
    }))
    .filter(c => isUuid(c.sessionId))

  const items = candidates.map(({ sessionId, filePath }) => ({
    sessionId,
    ...readSessionListItemBestEffort({ filePath, sessionId }),
  }))

  items.sort((a, b) => {
    const am = a.modifiedAt?.getTime() ?? 0
    const bm = b.modifiedAt?.getTime() ?? 0
    return bm - am
  })

  return items
}

function findSessionFileAcrossProjects(args: {
  sessionId: string
}): { filePath: string } | null {
  const { sessionId } = args
  const projectsDir = getSessionProjectsDir()
  if (!existsSync(projectsDir)) return null

  let projectNames: string[]
  try {
    projectNames = readdirSync(projectsDir)
  } catch {
    return null
  }

  for (const projectName of projectNames) {
    const candidate = join(projectsDir, projectName, `${sessionId}.jsonl`)
    if (existsSync(candidate)) return { filePath: candidate }
  }

  return null
}

function readSessionCwdBestEffort(filePath: string): string | null {
  try {
    const content = readFileSync(filePath, 'utf8')
    for (const rawLine of content.split('\n')) {
      const line = rawLine.trim()
      if (!line) continue
      const parsed = safeParseJson(line)
      if (!parsed || typeof parsed !== 'object') continue
      const cwd = (parsed as any).cwd
      if (typeof cwd === 'string' && cwd.trim()) return cwd.trim()
    }
  } catch {
  }
  return null
}

function sessionExistsInProject(cwd: string, sessionId: string): boolean {
  try {
    return existsSync(join(getSessionProjectDir(cwd), `${sessionId}.jsonl`))
  } catch {
    return false
  }
}

export function resolveResumeSessionIdentifier(args: {
  cwd: string
  identifier: string
}): ResumeResolveResult {
  const { cwd, identifier } = args
  const id = identifier.trim()
  if (!id) return { kind: 'not_found', identifier }

  if (isUuid(id)) {
    if (sessionExistsInProject(cwd, id)) return { kind: 'ok', sessionId: id }

    const elsewhere = findSessionFileAcrossProjects({ sessionId: id })
    if (elsewhere) {
      return {
        kind: 'different_directory',
        sessionId: id,
        otherCwd: readSessionCwdBestEffort(elsewhere.filePath),
      }
    }

    return { kind: 'not_found', identifier: id }
  }

  const sessions = listKodeAgentSessions({ cwd })
  const matches = sessions
    .filter(s => s.slug === id || s.customTitle === id)
    .map(s => s.sessionId)

  if (matches.length === 1) return { kind: 'ok', sessionId: matches[0]! }
  if (matches.length > 1)
    return { kind: 'ambiguous', identifier: id, matchingSessionIds: matches }
  return { kind: 'not_found', identifier: id }
}
