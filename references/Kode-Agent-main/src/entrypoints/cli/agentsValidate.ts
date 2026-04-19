import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import matter from 'gray-matter'
import yaml from 'js-yaml'
import { getModelManager } from '@utils/model'

export type AgentValidateIssue = {
  level: 'error' | 'warning'
  message: string
}

export type AgentValidateFileResult = {
  filePath: string
  agentType: string | null
  issues: AgentValidateIssue[]
  model?: string
  normalizedModel?: string
}

const VALID_PERMISSION_MODES = new Set([
  'default',
  'acceptEdits',
  'plan',
  'bypassPermissions',
  'dontAsk',
  'delegate',
])

const SUBAGENT_HARD_BLOCKED_TOOLS = new Set([
  'Task',
  'TaskOutput',
  'KillShell',
  'EnterPlanMode',
  'ExitPlanMode',
  'AskUserQuestion',
])

function normalizeString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function getClaudePolicyBaseDir(): string {
  switch (process.platform) {
    case 'darwin':
      return '/Library/Application Support/ClaudeCode'
    case 'win32':
      return existsSync('C:\\Program Files\\ClaudeCode')
        ? 'C:\\Program Files\\ClaudeCode'
        : 'C:\\ProgramData\\ClaudeCode'
    default:
      return '/etc/claude-code'
  }
}

function normalizeOverride(value: unknown): string | null {
  const normalized = normalizeString(value)
  return normalized ? resolve(normalized) : null
}

function getUserConfigRoots(): string[] {
  const claudeOverride = normalizeOverride(process.env.CLAUDE_CONFIG_DIR)
  const kodeOverride = normalizeOverride(process.env.KODE_CONFIG_DIR)
  const hasAnyOverride = Boolean(claudeOverride || kodeOverride)
  if (hasAnyOverride) {
    return Array.from(new Set([claudeOverride, kodeOverride].filter(Boolean))) as string[]
  }
  return [join(homedir(), '.claude'), join(homedir(), '.kode')]
}

function findProjectAgentDirs(cwd: string): string[] {
  const result: string[] = []
  const home = resolve(homedir())
  let current = resolve(cwd)

  while (current !== home) {
    const claudeDir = join(current, '.claude', 'agents')
    if (existsSync(claudeDir)) result.push(claudeDir)

    const kodeDir = join(current, '.kode', 'agents')
    if (existsSync(kodeDir)) result.push(kodeDir)

    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }

  return result
}

function listMarkdownFilesRecursively(rootDir: string): string[] {
  const files: string[] = []
  const visitedDirs = new Set<string>()

  const walk = (dirPath: string) => {
    let dirStat: ReturnType<typeof statSync>
    try {
      dirStat = statSync(dirPath)
    } catch {
      return
    }
    if (!dirStat.isDirectory()) return

    const dirKey = `${(dirStat as any).dev}:${(dirStat as any).ino}`
    if (visitedDirs.has(dirKey)) return
    visitedDirs.add(dirKey)

    let entries: Array<{
      name: string
      isDirectory(): boolean
      isFile(): boolean
      isSymbolicLink(): boolean
    }>
    try {
      entries = readdirSync(dirPath, { withFileTypes: true }) as any
    } catch {
      return
    }

    for (const entry of entries) {
      const name = String(entry.name ?? '')
      const fullPath = join(dirPath, name)

      if (entry.isDirectory()) {
        walk(fullPath)
        continue
      }

      if (entry.isFile()) {
        if (name.toLowerCase().endsWith('.md')) files.push(fullPath)
        continue
      }

      if (entry.isSymbolicLink()) {
        try {
          const st = statSync(fullPath)
          if (st.isDirectory()) {
            walk(fullPath)
          } else if (st.isFile() && name.toLowerCase().endsWith('.md')) {
            files.push(fullPath)
          }
        } catch {
          continue
        }
      }
    }
  }

  if (!existsSync(rootDir)) return []
  walk(rootDir)
  return files
}

function readMarkdownFile(filePath: string):
  | { frontmatter: any; content: string }
  | { error: string } {
  try {
    const raw = readFileSync(filePath, 'utf8')
    const yamlSchema = (yaml as any).JSON_SCHEMA
    const parsed = matter(raw, {
      engines: {
        yaml: {
          parse: (input: string) =>
            yaml.load(input, yamlSchema ? { schema: yamlSchema } : undefined) ??
            {},
        },
      },
    })
    return { frontmatter: (parsed.data as any) ?? {}, content: String(parsed.content ?? '') }
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) }
  }
}

function splitCliList(values: string[]): string[] {
  if (values.length === 0) return []
  const out: string[] = []

  for (const value of values) {
    if (!value) continue
    let current = ''
    let inParens = false

    for (const ch of value) {
      switch (ch) {
        case '(':
          inParens = true
          current += ch
          break
        case ')':
          inParens = false
          current += ch
          break
        case ',':
        case ' ': {
          if (inParens) {
            current += ch
            break
          }
          const trimmed = current.trim()
          if (trimmed) out.push(trimmed)
          current = ''
          break
        }
        default:
          current += ch
      }
    }

    const trimmed = current.trim()
    if (trimmed) out.push(trimmed)
  }

  return out
}

function normalizeToolList(value: unknown): string[] | null {
  if (value === undefined || value === null) return null
  if (!value) return []

  let raw: string[] = []
  if (typeof value === 'string') raw = [value]
  else if (Array.isArray(value))
    raw = value.filter((v): v is string => typeof v === 'string')

  if (raw.length === 0) return []
  const parsed = splitCliList(raw)
  if (parsed.includes('*')) return ['*']
  return parsed
}

function z2A(value: unknown): string[] | undefined {
  const normalized = normalizeToolList(value)
  if (normalized === null) return value === undefined ? undefined : []
  if (normalized.includes('*')) return undefined
  return normalized
}

function toolNameFromSpec(spec: string): string {
  const trimmed = spec.trim()
  if (!trimmed) return trimmed
  const match = trimmed.match(/^([^(]+)\(([^)]+)\)$/)
  if (!match) return trimmed
  const toolName = match[1]?.trim()
  return toolName || trimmed
}

function mapClaudeModelToKode(model: string): string | 'inherit' {
  if (model === 'inherit') return 'inherit'
  if (model === 'opus') return 'main'
  if (model === 'sonnet') return 'task'
  if (model === 'haiku') return 'quick'
  return model
}

function validateOneAgentFile(args: {
  filePath: string
  knownToolNames?: Set<string>
}): AgentValidateFileResult {
  const issues: AgentValidateIssue[] = []
  const read = readMarkdownFile(args.filePath)
  if ('error' in read) {
    issues.push({ level: 'error', message: `Failed to parse file: ${read.error}` })
    return { filePath: args.filePath, agentType: null, issues }
  }

  const fm = read.frontmatter ?? {}
  const agentType = normalizeString(fm.name)
  const description = normalizeString(fm.description)

  if (!agentType) {
    issues.push({ level: 'error', message: `Missing required frontmatter field 'name'` })
  }
  if (!description) {
    issues.push({ level: 'error', message: `Missing required frontmatter field 'description'` })
  }

  const toolsList = z2A(fm.tools)
  const tools = toolsList === undefined ? '*' : toolsList
  if (Array.isArray(tools) && tools.length === 0) {
    issues.push({ level: 'warning', message: `No tools selected (tools: [])` })
  }

  const disallowedRaw = fm.disallowedTools ?? fm['disallowed-tools'] ?? fm['disallowed_tools']
  const disallowed = disallowedRaw !== undefined ? z2A(disallowedRaw) : undefined
  if (disallowedRaw !== undefined && disallowed === undefined) {
    issues.push({
      level: 'warning',
      message: `disallowedTools contains '*' and will be ignored (compatibility behavior)`,
    })
  }

  if (Array.isArray(tools)) {
    for (const spec of tools) {
      const toolName = toolNameFromSpec(spec)
      if (SUBAGENT_HARD_BLOCKED_TOOLS.has(toolName)) {
        issues.push({
          level: 'warning',
          message: `Tool '${toolName}' is not available to subagents and will be ignored`,
        })
      }
      if (args.knownToolNames && toolName && !args.knownToolNames.has(toolName)) {
        issues.push({
          level: 'warning',
          message: `Unknown tool '${toolName}' (from '${spec}')`,
        })
      }
    }
  }

  const permissionMode = normalizeString(fm.permissionMode)
  if (permissionMode && !VALID_PERMISSION_MODES.has(permissionMode)) {
    issues.push({
      level: 'error',
      message: `Invalid permissionMode '${permissionMode}' (expected: ${Array.from(VALID_PERMISSION_MODES).join(', ')})`,
    })
  }

  const forkContextValue: unknown = fm.forkContext
  if (
    forkContextValue !== undefined &&
    forkContextValue !== 'true' &&
    forkContextValue !== 'false'
  ) {
    issues.push({
      level: 'error',
      message: `Invalid forkContext value '${String(forkContextValue)}' (must be the string 'true' or 'false')`,
    })
  }
  const forkContext = forkContextValue === 'true'

  let modelRaw: unknown = fm.model
  if (typeof modelRaw !== 'string' && typeof fm.model_name === 'string') {
    modelRaw = fm.model_name
  }
  const model = typeof modelRaw === 'string' ? modelRaw.trim() : undefined

  if (forkContext && model && model !== 'inherit') {
    issues.push({
      level: 'warning',
      message: `forkContext is true, so model will be forced to 'inherit' (compatibility behavior)`,
    })
  }

  const normalizedModel =
    model && model.length > 0 ? mapClaudeModelToKode(model) : undefined

  if (normalizedModel && normalizedModel !== 'inherit') {
    const manager = getModelManager()
    const resolved = manager.resolveModelWithInfo(normalizedModel as any)
    if (!resolved.success || !resolved.profile) {
      issues.push({
        level: 'error',
        message:
          resolved.error ??
          `Model '${String(normalizedModel)}' could not be resolved`,
      })
    }
  }

  const filename = basename(args.filePath, '.md')
  if (agentType && filename !== agentType) {
    issues.push({
      level: 'warning',
      message: `Filename '${filename}.md' does not match agent name '${agentType}'`,
    })
  }

  return {
    filePath: args.filePath,
    agentType: agentType ?? null,
    issues,
    ...(model ? { model } : {}),
    ...(normalizedModel ? { normalizedModel } : {}),
  }
}

function defaultValidationPaths(cwd: string): string[] {
  const out: string[] = []

  const policyDir = join(getClaudePolicyBaseDir(), '.claude', 'agents')
  if (existsSync(policyDir)) out.push(policyDir)

  for (const root of getUserConfigRoots()) {
    const dirPath = join(root, 'agents')
    if (existsSync(dirPath)) out.push(dirPath)
  }

  for (const dirPath of findProjectAgentDirs(cwd)) {
    if (existsSync(dirPath)) out.push(dirPath)
  }

  return out
}

export async function validateAgentTemplates(args: {
  cwd: string
  paths: string[]
  checkTools: boolean
}): Promise<{
  ok: boolean
  errorCount: number
  warningCount: number
  results: AgentValidateFileResult[]
}> {
  const inputPaths = args.paths.length > 0 ? args.paths : defaultValidationPaths(args.cwd)
  const markdownFiles = new Set<string>()
  for (const inputPath of inputPaths) {
    const resolved = resolve(args.cwd, inputPath)
    if (!existsSync(resolved)) continue
    let st: ReturnType<typeof statSync>
    try {
      st = statSync(resolved)
    } catch {
      continue
    }
    if (st.isFile()) {
      if (resolved.toLowerCase().endsWith('.md')) markdownFiles.add(resolved)
      continue
    }
    if (st.isDirectory()) {
      for (const f of listMarkdownFilesRecursively(resolved)) markdownFiles.add(f)
    }
  }

  let knownToolNames: Set<string> | undefined
  if (args.checkTools) {
    try {
      const { getTools } = await import('@tools')
      const { getCurrentProjectConfig } = await import('@utils/config')
      const allTools = await getTools(getCurrentProjectConfig().enableArchitectTool)
      knownToolNames = new Set(allTools.map(t => t.name))
    } catch {
      knownToolNames = undefined
    }
  }

  const results = Array.from(markdownFiles)
    .sort((a, b) => a.localeCompare(b))
    .map(filePath =>
      validateOneAgentFile({
        filePath,
        knownToolNames,
      }),
    )

  const errorCount = results.reduce(
    (sum, r) => sum + r.issues.filter(i => i.level === 'error').length,
    0,
  )
  const warningCount = results.reduce(
    (sum, r) => sum + r.issues.filter(i => i.level === 'warning').length,
    0,
  )

  return { ok: errorCount === 0, errorCount, warningCount, results }
}
