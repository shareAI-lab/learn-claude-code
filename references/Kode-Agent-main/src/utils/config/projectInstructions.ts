import { existsSync, readFileSync } from 'fs'
import { dirname, join, parse, relative, resolve, sep } from 'path'

export type ProjectInstructionFile = {
  absolutePath: string
  relativePathFromGitRoot: string
  filename: 'AGENTS.override.md' | 'AGENTS.md'
}

const DEFAULT_PROJECT_DOC_MAX_BYTES = 32 * 1024

function isRegularFile(path: string): boolean {
  try {
    return existsSync(path)
  } catch {
    return false
  }
}

export function findGitRoot(startDir: string): string | null {
  let currentDir = resolve(startDir)
  const fsRoot = parse(currentDir).root

  while (true) {
    const dotGitPath = join(currentDir, '.git')
    if (existsSync(dotGitPath)) {
      return currentDir
    }
    if (currentDir === fsRoot) {
      return null
    }
    currentDir = dirname(currentDir)
  }
}

function getDirsFromGitRootToCwd(gitRoot: string, cwd: string): string[] {
  const absoluteGitRoot = resolve(gitRoot)
  const absoluteCwd = resolve(cwd)

  const rel = relative(absoluteGitRoot, absoluteCwd)
  if (!rel || rel === '.') {
    return [absoluteGitRoot]
  }

  const parts = rel.split(sep).filter(Boolean)
  const dirs: string[] = [absoluteGitRoot]
  for (let i = 0; i < parts.length; i++) {
    dirs.push(join(absoluteGitRoot, ...parts.slice(0, i + 1)))
  }
  return dirs
}

export function getProjectInstructionFiles(
  cwd: string,
): ProjectInstructionFile[] {
  const gitRoot = findGitRoot(cwd)
  const root = gitRoot ?? resolve(cwd)
  const dirs = getDirsFromGitRootToCwd(root, cwd)

  const results: ProjectInstructionFile[] = []
  for (const dir of dirs) {
    const overridePath = join(dir, 'AGENTS.override.md')
    const agentsPath = join(dir, 'AGENTS.md')

    if (isRegularFile(overridePath)) {
      results.push({
        absolutePath: overridePath,
        relativePathFromGitRoot:
          relative(root, overridePath) || 'AGENTS.override.md',
        filename: 'AGENTS.override.md',
      })
      continue
    }

    if (isRegularFile(agentsPath)) {
      results.push({
        absolutePath: agentsPath,
        relativePathFromGitRoot: relative(root, agentsPath) || 'AGENTS.md',
        filename: 'AGENTS.md',
      })
    }
  }

  return results
}

export function getProjectDocMaxBytes(): number {
  const raw = process.env.KODE_PROJECT_DOC_MAX_BYTES
  if (!raw) return DEFAULT_PROJECT_DOC_MAX_BYTES
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed) || parsed <= 0)
    return DEFAULT_PROJECT_DOC_MAX_BYTES
  return parsed
}

export function readAndConcatProjectInstructionFiles(
  files: ProjectInstructionFile[],
  {
    maxBytes = getProjectDocMaxBytes(),
    includeHeadings = true,
  }: { maxBytes?: number; includeHeadings?: boolean } = {},
): { content: string; truncated: boolean } {
  let totalBytes = 0
  let truncated = false

  const parts: string[] = []

  const truncateUtf8ToBytes = (value: string, bytes: number): string => {
    const buf = Buffer.from(value, 'utf8')
    if (buf.length <= bytes) return value
    return buf.subarray(0, Math.max(0, bytes)).toString('utf8')
  }

  for (const file of files) {
    if (totalBytes >= maxBytes) {
      truncated = true
      break
    }

    let raw: string
    try {
      raw = readFileSync(file.absolutePath, 'utf-8')
    } catch {
      continue
    }

    if (!raw.trim()) continue

    const separator = parts.length > 0 ? '\n\n' : ''
    const separatorBytes = Buffer.byteLength(separator, 'utf8')
    const remainingAfterSeparator = maxBytes - totalBytes - separatorBytes
    if (remainingAfterSeparator <= 0) {
      truncated = true
      break
    }

    const heading = includeHeadings
      ? `# ${file.filename}\n\n_Path: ${file.relativePathFromGitRoot}_\n\n`
      : ''

    const block = `${heading}${raw}`.trimEnd()
    const blockBytes = Buffer.byteLength(block, 'utf8')

    if (blockBytes <= remainingAfterSeparator) {
      parts.push(`${separator}${block}`)
      totalBytes += separatorBytes + blockBytes
      continue
    }

    truncated = true
    const suffix = `\n\n... (truncated: project instruction files exceeded ${maxBytes} bytes)`
    const suffixBytes = Buffer.byteLength(suffix, 'utf8')

    let finalBlock = ''
    if (suffixBytes >= remainingAfterSeparator) {
      finalBlock = truncateUtf8ToBytes(suffix, remainingAfterSeparator)
    } else {
      const prefixBudget = remainingAfterSeparator - suffixBytes
      const prefix = truncateUtf8ToBytes(block, prefixBudget)
      finalBlock = `${prefix}${suffix}`
    }

    parts.push(`${separator}${finalBlock}`)
    totalBytes += separatorBytes + Buffer.byteLength(finalBlock, 'utf8')
    break
  }

  return { content: parts.join(''), truncated }
}
