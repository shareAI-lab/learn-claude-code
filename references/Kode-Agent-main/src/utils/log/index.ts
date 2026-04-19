import {
  existsSync,
  mkdirSync,
  writeFileSync,
  readFileSync,
  readdirSync,
  statSync,
  copyFileSync,
  promises as fsPromises,
} from 'fs'
import { dirname, join } from 'path'
import { captureException } from '@services/sentry'
import { randomUUID } from 'crypto'
import envPaths from 'env-paths'
import type { LogOption, SerializedMessage } from '@kode-types/logs'
import { MACRO } from '@constants/macros'
import { PRODUCT_COMMAND } from '@constants/product'
import { getPlanSlugForConversationKey } from '@utils/plan/planMode'
import { getKodeBaseDir } from '@utils/config/env'

const IN_MEMORY_ERROR_LOG: Array<{ error: string; timestamp: string }> = []
const MAX_IN_MEMORY_ERRORS = 100

const PERMISSION_ERROR_CODES = new Set(['EACCES', 'EPERM', 'EROFS'])

function isPermissionError(error: unknown): error is NodeJS.ErrnoException {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    PERMISSION_ERROR_CODES.has((error as NodeJS.ErrnoException).code ?? '')
  )
}

function safeMkdir(dir: string): boolean {
  if (existsSync(dir)) return true
  try {
    mkdirSync(dir, { recursive: true })
    return true
  } catch (error) {
    if (isPermissionError(error)) {
      return false
    }
    throw error
  }
}

function safeWriteFile(
  path: string,
  data: string,
  encoding: BufferEncoding = 'utf8',
): boolean {
  try {
    writeFileSync(path, data, encoding)
    return true
  } catch (error) {
    if (isPermissionError(error)) {
      return false
    }
    throw error
  }
}

export const SESSION_ID = randomUUID()

const paths = envPaths(PRODUCT_COMMAND)

function getProjectDir(cwd: string): string {
  return cwd.replace(/[^a-zA-Z0-9]/g, '-')
}

function getLegacyCacheRoot(): string {
  return process.env.KODE_LEGACY_CACHE_ROOT ?? paths.cache
}

function getNewLogRoot(): string {
  return process.env.KODE_LOG_ROOT ?? getKodeBaseDir()
}

export const CACHE_PATHS = {
  errors: () => join(getNewLogRoot(), getProjectDir(process.cwd()), 'errors'),
  messages: () =>
    join(getNewLogRoot(), getProjectDir(process.cwd()), 'messages'),
  mcpLogs: (serverName: string) =>
    join(
      getLegacyCacheRoot(),
      getProjectDir(process.cwd()),
      `mcp-logs-${serverName}`,
    ),
}

export const LEGACY_CACHE_PATHS = {
  errors: () =>
    join(getLegacyCacheRoot(), getProjectDir(process.cwd()), 'errors'),
  messages: () =>
    join(getLegacyCacheRoot(), getProjectDir(process.cwd()), 'messages'),
  mcpLogs: (serverName: string) =>
    join(
      getLegacyCacheRoot(),
      getProjectDir(process.cwd()),
      `mcp-logs-${serverName}`,
    ),
}

export function dateToFilename(date: Date): string {
  return date.toISOString().replace(/[:.]/g, '-')
}

const DATE = dateToFilename(new Date())

function getErrorsPath(): string {
  return join(CACHE_PATHS.errors(), DATE + '.txt')
}

export function getMessagesPath(
  messageLogName: string,
  forkNumber: number,
  sidechainNumber: number,
): string {
  return join(
    CACHE_PATHS.messages(),
    `${messageLogName}${forkNumber > 0 ? `-${forkNumber}` : ''}${
      sidechainNumber > 0 ? `-sidechain-${sidechainNumber}` : ''
    }.json`,
  )
}

const MIGRATION_MESSAGE_LOG_LIMIT = 50
let didMigrateMessageLogs = false

function migrateLegacyMessageLogsIfNeeded() {
  if (didMigrateMessageLogs) return
  didMigrateMessageLogs = true

  const legacyDir = LEGACY_CACHE_PATHS.messages()
  const newDir = CACHE_PATHS.messages()

  if (!existsSync(legacyDir)) return

  const newHasAny =
    existsSync(newDir) &&
    readdirSync(newDir).some(file => file.endsWith('.json'))
  if (newHasAny) return

  try {
    mkdirSync(newDir, { recursive: true })
  } catch {
    return
  }

  let legacyFiles: string[] = []
  try {
    legacyFiles = readdirSync(legacyDir).filter(file => file.endsWith('.json'))
  } catch {
    return
  }

  const sorted = legacyFiles
    .map(file => {
      try {
        const stats = statSync(join(legacyDir, file))
        return { file, mtimeMs: stats.mtimeMs }
      } catch {
        return { file, mtimeMs: 0 }
      }
    })
    .sort((a, b) => b.mtimeMs - a.mtimeMs)
    .slice(0, MIGRATION_MESSAGE_LOG_LIMIT)

  for (const { file } of sorted) {
    const src = join(legacyDir, file)
    const dest = join(newDir, file)
    if (existsSync(dest)) continue
    try {
      copyFileSync(src, dest)
    } catch {
    }
  }
}

export function logError(error: unknown): void {
  try {
    if (process.env.NODE_ENV === 'test') {
      console.error(error)
    }

    const errorStr =
      error instanceof Error ? error.stack || error.message : String(error)

    const errorInfo = {
      error: errorStr,
      timestamp: new Date().toISOString(),
    }

    if (IN_MEMORY_ERROR_LOG.length >= MAX_IN_MEMORY_ERRORS) {
      IN_MEMORY_ERROR_LOG.shift()
    }
    IN_MEMORY_ERROR_LOG.push(errorInfo)

    appendToLog(getErrorsPath(), {
      error: errorStr,
    })
  } catch {
  }
  captureException(error)
}

export function getErrorsLog(): object[] {
  return readLog(getErrorsPath())
}

export function getInMemoryErrors(): object[] {
  return [...IN_MEMORY_ERROR_LOG]
}

function readLog(path: string): object[] {
  if (!existsSync(path)) {
    return []
  }
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    return []
  }
}

function appendToLog(path: string, message: object): void {
  if (process.env.USER_TYPE === 'external') {
    return
  }

  const dir = dirname(path)
  if (!safeMkdir(dir)) {
    return
  }

  if (!existsSync(path) && !safeWriteFile(path, '[]')) {
    return
  }

  const messages = readLog(path)
  const messageWithTimestamp = {
    ...message,
    cwd: process.cwd(),
    userType: process.env.USER_TYPE,
    sessionId: SESSION_ID,
    timestamp: new Date().toISOString(),
    version: MACRO.VERSION,
  }
  messages.push(messageWithTimestamp)

  safeWriteFile(path, JSON.stringify(messages, null, 2))
}

export function overwriteLog(
  path: string,
  messages: object[],
  options?: { conversationKey?: string },
): void {
  if (process.env.USER_TYPE === 'external') {
    return
  }

  if (!messages.length) {
    return
  }

  const dir = dirname(path)
  if (!safeMkdir(dir)) {
    return
  }

  const slug = options?.conversationKey
    ? getPlanSlugForConversationKey(options.conversationKey)
    : null

  const messagesWithMetadata = messages.map(message => ({
    ...message,
    ...(slug ? { slug } : {}),
    cwd: process.cwd(),
    userType: process.env.USER_TYPE,
    sessionId: SESSION_ID,
    timestamp: new Date().toISOString(),
    version: MACRO.VERSION,
  }))

  safeWriteFile(path, JSON.stringify(messagesWithMetadata, null, 2))
}

export async function loadLogList(
  path = CACHE_PATHS.messages(),
): Promise<LogOption[]> {
  if (path === CACHE_PATHS.messages()) {
    migrateLegacyMessageLogsIfNeeded()
  }

  const searchPaths =
    path === CACHE_PATHS.messages()
      ? [CACHE_PATHS.messages(), LEGACY_CACHE_PATHS.messages()]
      : [path]

  const existingPaths = searchPaths.filter(p => existsSync(p))
  if (existingPaths.length === 0) {
    logError(`No logs found at ${path}`)
    return []
  }

  const filesWithDir = (
    await Promise.all(
      existingPaths.map(async dirPath => {
        const dirFiles = await fsPromises.readdir(dirPath)
        return dirFiles.map(file => ({ file, dirPath }))
      }),
    )
  ).flat()

  const seen = new Set<string>()
  const uniqueFiles = filesWithDir.filter(({ file }) => {
    if (seen.has(file)) return false
    seen.add(file)
    return true
  })

  const logData = await Promise.all(
    uniqueFiles.map(async ({ file, dirPath }, i) => {
      const fullPath = join(dirPath, file)
      const content = await fsPromises.readFile(fullPath, 'utf8')
      const messages = JSON.parse(content) as SerializedMessage[]
      const firstMessage = messages[0]
      const lastMessage = messages[messages.length - 1]
      const firstPrompt =
        firstMessage?.type === 'user' &&
        typeof firstMessage?.message?.content === 'string'
          ? firstMessage?.message?.content
          : 'No prompt'

      const { date, forkNumber, sidechainNumber } = parseLogFilename(file)
      return {
        date,
        forkNumber,
        fullPath,
        messages,
        value: i,
        created: parseISOString(firstMessage?.timestamp || date),
        modified: lastMessage?.timestamp
          ? parseISOString(lastMessage.timestamp)
          : parseISOString(date),
        firstPrompt:
          firstPrompt.split('\n')[0]?.slice(0, 50) +
            (firstPrompt.length > 50 ? '…' : '') || 'No prompt',
        messageCount: messages.length,
        sidechainNumber,
      }
    }),
  )

  return sortLogs(logData.filter(_ => _.messages.length)).map((_, i) => ({
    ..._,
    value: i,
  }))
}

export function parseLogFilename(filename: string): {
  date: string
  forkNumber: number | undefined
  sidechainNumber: number | undefined
} {
  const base = filename.split('.')[0]!
  const segments = base.split('-')
  const hasSidechain = base.includes('-sidechain-')

  let date = base
  let forkNumber: number | undefined = undefined
  let sidechainNumber: number | undefined = undefined

  if (hasSidechain) {
    const sidechainIndex = segments.indexOf('sidechain')
    sidechainNumber = Number(segments[sidechainIndex + 1])
    if (sidechainIndex > 6) {
      forkNumber = Number(segments[sidechainIndex - 1])
      date = segments.slice(0, 6).join('-')
    } else {
      date = segments.slice(0, 6).join('-')
    }
  } else if (segments.length > 6) {
    const lastSegment = Number(segments[segments.length - 1])
    forkNumber = lastSegment >= 0 ? lastSegment : undefined
    date = segments.slice(0, 6).join('-')
  } else {
    date = base
  }

  return { date, forkNumber, sidechainNumber }
}

export function getNextAvailableLogForkNumber(
  date: string,
  forkNumber: number,
  sidechainNumber: number,
): number {
  while (existsSync(getMessagesPath(date, forkNumber, sidechainNumber))) {
    forkNumber++
  }
  return forkNumber
}

export function getNextAvailableLogSidechainNumber(
  date: string,
  forkNumber: number,
): number {
  let sidechainNumber = 1
  while (existsSync(getMessagesPath(date, forkNumber, sidechainNumber))) {
    sidechainNumber++
  }
  return sidechainNumber
}

export function getForkNumberFromFilename(
  filename: string,
): number | undefined {
  const base = filename.split('.')[0]!
  const segments = base.split('-')
  const hasSidechain = base.includes('-sidechain-')

  if (hasSidechain) {
    const sidechainIndex = segments.indexOf('sidechain')
    if (sidechainIndex > 6) {
      return Number(segments[sidechainIndex - 1])
    }
    return undefined
  }

  if (segments.length > 6) {
    const lastNumber = Number(segments[segments.length - 1])
    return lastNumber >= 0 ? lastNumber : undefined
  }
  return undefined
}

export function sortLogs(logs: LogOption[]): LogOption[] {
  return logs.sort((a, b) => {
    const modifiedDiff = b.modified.getTime() - a.modified.getTime()
    if (modifiedDiff !== 0) {
      return modifiedDiff
    }

    const createdDiff = b.created.getTime() - a.created.getTime()
    if (createdDiff !== 0) {
      return createdDiff
    }

    return (b.forkNumber ?? 0) - (a.forkNumber ?? 0)
  })
}

export function formatDate(date: Date): string {
  const now = new Date()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)

  const isToday = date.toDateString() === now.toDateString()
  const isYesterday = date.toDateString() === yesterday.toDateString()

  const timeStr = date
    .toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
    .toLowerCase()

  if (isToday) {
    return `Today at ${timeStr}`
  } else if (isYesterday) {
    return `Yesterday at ${timeStr}`
  } else {
    return (
      date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }) + ` at ${timeStr}`
    )
  }
}

export function parseISOString(s: string): Date {
  const b = s.split(/\D+/)
  return new Date(
    Date.UTC(
      parseInt(b[0]!, 10),
      parseInt(b[1]!, 10) - 1,
      parseInt(b[2]!, 10),
      parseInt(b[3]!, 10),
      parseInt(b[4]!, 10),
      parseInt(b[5]!, 10),
      parseInt(b[6]!, 10),
    ),
  )
}

export function logMCPError(serverName: string, error: unknown): void {
  try {
    const logDir = CACHE_PATHS.mcpLogs(serverName)
    const errorStr =
      error instanceof Error ? error.stack || error.message : String(error)
    const timestamp = new Date().toISOString()

    const logFile = join(logDir, DATE + '.txt')

    if (!existsSync(logDir)) {
      mkdirSync(logDir, { recursive: true })
    }

    if (!existsSync(logFile)) {
      writeFileSync(logFile, '[]', 'utf8')
    }

    const errorInfo = {
      error: errorStr,
      timestamp,
      sessionId: SESSION_ID,
      cwd: process.cwd(),
    }

    const messages = readLog(logFile)
    messages.push(errorInfo)
    writeFileSync(logFile, JSON.stringify(messages, null, 2), 'utf8')
  } catch {
  }
}
