import {
  readFileSync,
  writeFileSync,
  openSync,
  readSync,
  closeSync,
  existsSync,
  readdirSync,
} from 'fs'
import { stat as statAsync } from 'fs/promises'
import { logError } from '@utils/log'
import {
  isAbsolute,
  normalize,
  resolve,
  resolve as resolvePath,
  relative,
  sep,
  basename,
  dirname,
  extname,
  join,
} from 'path'
import { cwd } from 'process'
import { listAllContentFiles } from '@utils/system/ripgrep'
import { LRUCache } from 'lru-cache'
import { getCwd } from '@utils/state'
import { BunSearcher } from '@utils/bun/searcher'

export type File = {
  filename: string
  content: string
}

export type LineEndingType = 'CRLF' | 'LF'

export async function glob(
  filePattern: string,
  cwd: string,
  { limit, offset }: { limit: number; offset: number },
  abortSignal: AbortSignal,
): Promise<{ files: string[]; truncated: boolean }> {
  const allFiles = await BunSearcher.glob(
    filePattern,
    cwd,
    limit + offset + 100,
    abortSignal,
  )

  const resolvedFiles = allFiles
    .map(f => resolve(cwd, f))
    .filter(f => existsSync(f))
  const stats = await Promise.all(
    resolvedFiles.map(async file => {
      try {
        return await statAsync(file)
      } catch {
        return null
      }
    }),
  )
  const sortedFiles = resolvedFiles
    .map((file, i) => [file, stats[i]] as const)
    .filter(([, stat]) => stat !== null)
    .sort((a, b) => {
      const timeComparison = (b[1]!.mtimeMs ?? 0) - (a[1]!.mtimeMs ?? 0)
      if (timeComparison !== 0) return timeComparison
      return a[0].localeCompare(b[0])
    })
    .map(([file]) => file)

  const truncated = sortedFiles.length > offset + limit
  return {
    files: sortedFiles.slice(offset, offset + limit),
    truncated,
  }
}

export function readFileSafe(filepath: string): string | null {
  try {
    return readFileSync(filepath, 'utf-8')
  } catch (error) {
    logError(error)
    return null
  }
}

export function isInDirectory(
  relativePath: string,
  relativeCwd: string,
): boolean {
  if (relativePath === '.') {
    return true
  }

  if (relativePath.startsWith('~')) {
    return false
  }

  if (relativePath.includes('\0') || relativeCwd.includes('\0')) {
    return false
  }

  let normalizedPath = normalize(relativePath)
  let normalizedCwd = normalize(relativeCwd)

  normalizedPath = normalizedPath.endsWith(sep)
    ? normalizedPath
    : normalizedPath + sep
  normalizedCwd = normalizedCwd.endsWith(sep)
    ? normalizedCwd
    : normalizedCwd + sep

  const fullPath = resolvePath(cwd(), normalizedCwd, normalizedPath)
  const fullCwd = resolvePath(cwd(), normalizedCwd)

  const rel = relative(fullCwd, fullPath)
  if (!rel || rel === '') return true
  if (rel.startsWith('..')) return false
  if (isAbsolute(rel)) return false
  return true
}

export function readTextContent(
  filePath: string,
  offset = 0,
  maxLines?: number,
): { content: string; lineCount: number; totalLines: number } {
  const enc = detectFileEncoding(filePath)
  const content = readFileSync(filePath, enc)
  const lines = content.split(/\r?\n/)

  const toReturn =
    maxLines !== undefined && lines.length - offset > maxLines
      ? lines.slice(offset, offset + maxLines)
      : lines.slice(offset)

  return {
    content: toReturn.join('\n'),
    lineCount: toReturn.length,
    totalLines: lines.length,
  }
}

export function writeTextContent(
  filePath: string,
  content: string,
  encoding: BufferEncoding,
  endings: LineEndingType,
): void {
  let toWrite = content
  if (endings === 'CRLF') {
    toWrite = content.split('\n').join('\r\n')
  }

  writeFileSync(filePath, toWrite, { encoding, flush: true })
}

const repoEndingCache = new LRUCache<string, LineEndingType>({
  fetchMethod: path => detectRepoLineEndingsDirect(path),
  ttl: 5 * 60 * 1000,
  ttlAutopurge: false,
  max: 1000,
})

export async function detectRepoLineEndings(
  filePath: string,
): Promise<LineEndingType | undefined> {
  return repoEndingCache.fetch(resolve(filePath))
}

export async function detectRepoLineEndingsDirect(
  cwd: string,
): Promise<LineEndingType> {
  const abortController = new AbortController()
  setTimeout(() => {
    abortController.abort()
  }, 1_000)
  const allFiles = await listAllContentFiles(cwd, abortController.signal, 15)

  let crlfCount = 0
  for (const file of allFiles) {
    const lineEnding = detectLineEndings(file)
    if (lineEnding === 'CRLF') {
      crlfCount++
    }
  }

  return crlfCount > 3 ? 'CRLF' : 'LF'
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
function fetch<K extends {}, V extends {}>(
  cache: LRUCache<K, V>,
  key: K,
  value: () => V,
): V {
  if (cache.has(key)) {
    return cache.get(key)!
  }

  const v = value()
  cache.set(key, v)
  return v
}

const fileEncodingCache = new LRUCache<string, BufferEncoding>({
  fetchMethod: path => detectFileEncodingDirect(path),
  ttl: 5 * 60 * 1000,
  ttlAutopurge: false,
  max: 1000,
})

export function detectFileEncoding(filePath: string): BufferEncoding {
  const k = resolve(filePath)
  return fetch(fileEncodingCache, k, () => detectFileEncodingDirect(k))
}

export function detectFileEncodingDirect(filePath: string): BufferEncoding {
  const BUFFER_SIZE = 4096
  const buffer = Buffer.alloc(BUFFER_SIZE)

  let fd: number | undefined = undefined
  try {
    fd = openSync(filePath, 'r')
    const bytesRead = readSync(fd, buffer, 0, BUFFER_SIZE, 0)

    if (bytesRead >= 2) {
      if (buffer[0] === 0xff && buffer[1] === 0xfe) return 'utf16le'
    }

    if (
      bytesRead >= 3 &&
      buffer[0] === 0xef &&
      buffer[1] === 0xbb &&
      buffer[2] === 0xbf
    ) {
      return 'utf8'
    }

    const isUtf8 = buffer.slice(0, bytesRead).toString('utf8').length > 0
    return isUtf8 ? 'utf8' : 'ascii'
  } catch (error) {
    logError(`Error detecting encoding for file ${filePath}: ${error}`)
    return 'utf8'
  } finally {
    if (fd) closeSync(fd)
  }
}

const lineEndingCache = new LRUCache<string, LineEndingType>({
  fetchMethod: path => detectLineEndingsDirect(path),
  ttl: 5 * 60 * 1000,
  ttlAutopurge: false,
  max: 1000,
})

export function detectLineEndings(filePath: string): LineEndingType {
  const k = resolve(filePath)
  return fetch(lineEndingCache, k, () => detectLineEndingsDirect(k))
}

export function detectLineEndingsDirect(
  filePath: string,
  encoding: BufferEncoding = 'utf8',
): LineEndingType {
  try {
    const buffer = Buffer.alloc(4096)
    const fd = openSync(filePath, 'r')
    const bytesRead = readSync(fd, buffer, 0, 4096, 0)
    closeSync(fd)

    const content = buffer.toString(encoding, 0, bytesRead)
    let crlfCount = 0
    let lfCount = 0

    for (let i = 0; i < content.length; i++) {
      if (content[i] === '\n') {
        if (i > 0 && content[i - 1] === '\r') {
          crlfCount++
        } else {
          lfCount++
        }
      }
    }

    return crlfCount > lfCount ? 'CRLF' : 'LF'
  } catch (error) {
    logError(`Error detecting line endings for file ${filePath}: ${error}`)
    return 'LF'
  }
}

export function normalizeFilePath(filePath: string): string {
  const absoluteFilePath = isAbsolute(filePath)
    ? filePath
    : resolve(getCwd(), filePath)

  if (absoluteFilePath.endsWith(' AM.png')) {
    return absoluteFilePath.replace(
      ' AM.png',
      `${String.fromCharCode(8239)}AM.png`,
    )
  }

  if (absoluteFilePath.endsWith(' PM.png')) {
    return absoluteFilePath.replace(
      ' PM.png',
      `${String.fromCharCode(8239)}PM.png`,
    )
  }

  return absoluteFilePath
}

export function getAbsolutePath(path: string | undefined): string | undefined {
  return path ? (isAbsolute(path) ? path : resolve(getCwd(), path)) : undefined
}

export function getAbsoluteAndRelativePaths(path: string | undefined): {
  absolutePath: string | undefined
  relativePath: string | undefined
} {
  const absolutePath = getAbsolutePath(path)
  const relativePath = absolutePath
    ? relative(getCwd(), absolutePath)
    : undefined
  return { absolutePath, relativePath }
}


export function findSimilarFile(filePath: string): string | undefined {
  try {
    const dir = dirname(filePath)
    const fileBaseName = basename(filePath, extname(filePath))

    if (!existsSync(dir)) {
      return undefined
    }

    const files = readdirSync(dir)

    const similarFiles = files.filter(
      file =>
        basename(file, extname(file)) === fileBaseName &&
        join(dir, file) !== filePath,
    )

    const firstMatch = similarFiles[0]
    if (firstMatch) {
      return firstMatch
    }
    return undefined
  } catch (error) {
    logError(`Error finding similar file for ${filePath}: ${error}`)
    return undefined
  }
}

export function addLineNumbers({
  content,
  startLine,
}: {
  content: string
  startLine: number
}): string {
  if (!content) {
    return ''
  }

  return content
    .split(/\r?\n/)
    .map((line, index) => {
      const lineNum = index + startLine
      const numStr = String(lineNum)
      if (numStr.length >= 6) {
        return `${numStr}→${line}`
      }
      return `${numStr.padStart(6, ' ')}→${line}`
    })
    .join('\n')
}

export function isDirEmpty(dirPath: string): boolean {
  try {
    const entries = readdirSync(dirPath)
    return entries.length === 0
  } catch (error) {
    logError(`Error checking directory: ${error}`)
    return false
  }
}
