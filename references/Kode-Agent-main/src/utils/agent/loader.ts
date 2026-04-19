
import {
  existsSync,
  readFileSync,
  readdirSync,
  statSync,
  watch,
  type FSWatcher,
} from 'fs'
import { basename, dirname, join, resolve } from 'path'
import { homedir } from 'os'
import matter from 'gray-matter'
import yaml from 'js-yaml'
import { memoize } from 'lodash-es'
import { z } from 'zod'
import { getCwd } from '@utils/state'
import { getSessionPlugins } from '@utils/session/sessionPlugins'
import { isSettingSourceEnabled } from '@utils/config/settingSources'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

export type AgentSource =
  | 'built-in'
  | 'plugin'
  | 'userSettings'
  | 'projectSettings'
  | 'flagSettings'
  | 'policySettings'

export type AgentLocation = 'built-in' | 'plugin' | 'user' | 'project'

export type AgentModel = 'inherit' | 'haiku' | 'sonnet' | 'opus' | (string & {})

export type AgentPermissionMode =
  | 'default'
  | 'acceptEdits'
  | 'plan'
  | 'bypassPermissions'
  | 'dontAsk'
  | 'delegate'

export interface AgentConfig {
  agentType: string
  whenToUse: string
  tools: string[] | '*'
  disallowedTools?: string[]
  skills?: string[]
  systemPrompt: string
  source: AgentSource
  location: AgentLocation
  baseDir?: string
  filename?: string
  color?: string
  model?: AgentModel
  permissionMode?: AgentPermissionMode
  forkContext?: boolean
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
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed ? resolve(trimmed) : null
}

function dedupeStrings(values: string[]): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  for (const value of values) {
    if (!value) continue
    if (seen.has(value)) continue
    seen.add(value)
    out.push(value)
  }
  return out
}

function getUserConfigRoots(): string[] {
  const claudeOverride = normalizeOverride(process.env.CLAUDE_CONFIG_DIR)
  const kodeOverride = normalizeOverride(process.env.KODE_CONFIG_DIR)

  const hasAnyOverride = Boolean(claudeOverride || kodeOverride)
  if (hasAnyOverride) {
    return dedupeStrings([claudeOverride ?? '', kodeOverride ?? ''])
  }

  return dedupeStrings([join(homedir(), '.claude'), join(homedir(), '.kode')])
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

    const dirKey = `${dirStat.dev}:${dirStat.ino}`
    if (visitedDirs.has(dirKey)) return
    visitedDirs.add(dirKey)

    let entries: Array<{
      name: string
      isDirectory(): boolean
      isFile(): boolean
      isSymbolicLink(): boolean
    }>
    try {
      entries = readdirSync(dirPath, {
        withFileTypes: true,
        encoding: 'utf8',
      }) as any
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
        if (name.endsWith('.md')) files.push(fullPath)
        continue
      }

      if (entry.isSymbolicLink()) {
        try {
          const st = statSync(fullPath)
          if (st.isDirectory()) {
            walk(fullPath)
          } else if (st.isFile() && name.endsWith('.md')) {
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

function readMarkdownFile(filePath: string): { frontmatter: any; content: string } | null {
  try {
    const raw = readFileSync(filePath, 'utf8')
    const yamlSchema = (yaml as any).JSON_SCHEMA
    const matterOptions = {
      engines: {
        yaml: {
          parse: (input: string) =>
            yaml.load(input, yamlSchema ? { schema: yamlSchema } : undefined) ??
            {},
        },
      },
    }
    const parsed = matter(raw, matterOptions)
    return {
      frontmatter: (parsed.data as any) ?? {},
      content: String(parsed.content ?? ''),
    }
  } catch {
    return null
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
          if (inParens) {
            current += ch
          } else {
            const trimmed = current.trim()
            if (trimmed) out.push(trimmed)
            current = ''
          }
          break
        case ' ':
          if (inParens) {
            current += ch
          } else {
            const trimmed = current.trim()
            if (trimmed) out.push(trimmed)
            current = ''
          }
          break
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

function qP(value: unknown): string[] {
  const normalized = normalizeToolList(value)
  if (normalized === null) return []
  return normalized
}

const VALID_PERMISSION_MODES = [
  'default',
  'acceptEdits',
  'plan',
  'bypassPermissions',
  'dontAsk',
  'delegate',
] as const

function sourceToLocation(source: AgentSource): AgentLocation {
  switch (source) {
    case 'plugin':
      return 'plugin'
    case 'userSettings':
      return 'user'
    case 'projectSettings':
      return 'project'
    case 'built-in':
    case 'flagSettings':
    case 'policySettings':
    default:
      return 'built-in'
  }
}

function parseAgentFromFile(options: {
  filePath: string
  baseDir: string
  source: Exclude<AgentSource, 'flagSettings' | 'built-in'>
}): AgentConfig | null {
  const parsed = readMarkdownFile(options.filePath)
  if (!parsed) return null

  try {
    const fm = parsed.frontmatter ?? {}
    let name: unknown = fm.name
    let description: unknown = fm.description

    if (!name || typeof name !== 'string' || !description || typeof description !== 'string') {
      return null
    }

    const whenToUse = description.replace(/\\n/g, '\n')
    const filename = basename(options.filePath, '.md')

    const color = typeof fm.color === 'string' ? fm.color : undefined

    let modelRaw: unknown = fm.model
    if (typeof modelRaw !== 'string' && typeof fm.model_name === 'string') {
      modelRaw = fm.model_name
    }
    let model =
      typeof modelRaw === 'string' ? modelRaw.trim() : undefined
    if (model === '') model = undefined

    const forkContextValue: unknown = fm.forkContext
    if (
      forkContextValue !== undefined &&
      forkContextValue !== 'true' &&
      forkContextValue !== 'false'
    ) {
      debugLogger.warn('AGENT_LOADER_INVALID_FORK_CONTEXT', {
        filePath: options.filePath,
        forkContext: String(forkContextValue),
      })
    }
    const forkContext = forkContextValue === 'true'

    if (forkContext && model && model !== 'inherit') {
      debugLogger.warn('AGENT_LOADER_FORK_CONTEXT_MODEL_OVERRIDE', {
        filePath: options.filePath,
        model,
      })
      model = 'inherit'
    }

    const permissionModeValue: unknown = fm.permissionMode
    const permissionModeIsValid =
      typeof permissionModeValue === 'string' &&
      VALID_PERMISSION_MODES.includes(permissionModeValue as AgentPermissionMode)
    if (
      typeof permissionModeValue === 'string' &&
      permissionModeValue &&
      !permissionModeIsValid
    ) {
      debugLogger.warn('AGENT_LOADER_INVALID_PERMISSION_MODE', {
        filePath: options.filePath,
        permissionMode: permissionModeValue,
        valid: VALID_PERMISSION_MODES,
      })
    }

    const toolsList = z2A(fm.tools)
    const tools: string[] | '*' =
      toolsList === undefined || toolsList.includes('*') ? '*' : toolsList

    const disallowedRaw =
      fm.disallowedTools ??
      fm['disallowed-tools'] ??
      fm['disallowed_tools']
    const disallowedTools = disallowedRaw !== undefined ? z2A(disallowedRaw) : undefined

    const skills = qP(fm.skills)
    const systemPrompt = parsed.content.trim()

    const agent: AgentConfig = {
      agentType: name,
      whenToUse,
      tools,
      ...(disallowedTools !== undefined ? { disallowedTools } : {}),
      ...(skills.length > 0 ? { skills } : { skills: [] }),
      systemPrompt,
      source: options.source,
      location: sourceToLocation(options.source),
      baseDir: options.baseDir,
      filename,
      ...(color ? { color } : {}),
      ...(model ? { model: model as AgentModel } : {}),
      ...(permissionModeIsValid ? { permissionMode: permissionModeValue as AgentPermissionMode } : {}),
      ...(forkContext ? { forkContext: true } : {}),
    }

    return agent
  } catch {
    return null
  }
}

const agentJsonSchema = z.object({
  description: z.string().min(1, 'Description cannot be empty'),
  tools: z.array(z.string()).optional(),
  disallowedTools: z.array(z.string()).optional(),
  prompt: z.string().min(1, 'Prompt cannot be empty'),
  model: z.string().optional(),
  permissionMode: z.enum(VALID_PERMISSION_MODES).optional(),
})

const agentsJsonSchema = z.record(z.string(), agentJsonSchema)

function parseAgentFromJson(agentType: string, value: unknown): AgentConfig | null {
  const parsed = agentJsonSchema.safeParse(value)
  if (!parsed.success) return null

  const toolsList = z2A(parsed.data.tools)
  const disallowedList =
    parsed.data.disallowedTools !== undefined ? z2A(parsed.data.disallowedTools) : undefined
  const model =
    typeof parsed.data.model === 'string' ? parsed.data.model.trim() : undefined

  return {
    agentType,
    whenToUse: parsed.data.description,
    tools: toolsList === undefined || toolsList.includes('*') ? '*' : toolsList,
    ...(disallowedList !== undefined ? { disallowedTools: disallowedList } : {}),
    systemPrompt: parsed.data.prompt,
    source: 'flagSettings',
    location: 'built-in',
    ...(model ? { model: model as AgentModel } : {}),
    ...(parsed.data.permissionMode ? { permissionMode: parsed.data.permissionMode } : {}),
  }
}

let FLAG_AGENTS: AgentConfig[] = []

export function setFlagAgentsFromCliJson(json: string | undefined): void {
  if (!json) {
    FLAG_AGENTS = []
    clearAgentCache()
    return
  }

  let raw: unknown
  try {
    raw = JSON.parse(json)
  } catch (err) {
    logError(err)
    debugLogger.warn('AGENT_LOADER_FLAG_AGENTS_JSON_PARSE_FAILED', {
      error: err instanceof Error ? err.message : String(err),
    })
    FLAG_AGENTS = []
    clearAgentCache()
    return
  }

  const parsed = agentsJsonSchema.safeParse(raw)
  if (!parsed.success) {
    logError(parsed.error)
    debugLogger.warn('AGENT_LOADER_FLAG_AGENTS_SCHEMA_INVALID', {
      error: parsed.error.message,
    })
    FLAG_AGENTS = []
    clearAgentCache()
    return
  }

  FLAG_AGENTS = Object.entries(parsed.data)
    .map(([agentType, value]) => parseAgentFromJson(agentType, value))
    .filter((agent): agent is AgentConfig => agent !== null)

  clearAgentCache()
}

const BUILTIN_GENERAL_PURPOSE: AgentConfig = {
  agentType: 'general-purpose',
  whenToUse:
    'General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks',
  tools: '*',
  systemPrompt: `You are a general-purpose agent. Given the user's task, use the tools available to complete it efficiently and thoroughly.

When to use your capabilities:
- Searching for code, configurations, and patterns across large codebases
- Analyzing multiple files to understand system architecture  
- Investigating complex questions that require exploring many files
- Performing multi-step research tasks

Guidelines:
- For file searches: Use Grep or Glob when you need to search broadly. Use FileRead when you know the specific file path.
- For analysis: Start broad and narrow down. Use multiple search strategies if the first doesn't yield results.
- Be thorough: Check multiple locations, consider different naming conventions, look for related files.
- Complete tasks directly using your capabilities.`,
  source: 'built-in',
  location: 'built-in',
  baseDir: 'built-in',
}

const BUILTIN_EXPLORE: AgentConfig = {
  agentType: 'Explore',
  whenToUse:
    'Fast agent specialized for exploring codebases. Use this when you need to quickly find files by patterns (eg. "src/components/**/*.tsx"), search code for keywords (eg. "API endpoints"), or answer questions about the codebase (eg. "how do API endpoints work?"). When calling this agent, specify the desired thoroughness level: "quick" for basic searches, "medium" for moderate exploration, or "very thorough" for comprehensive analysis across multiple locations and naming conventions.',
  tools: '*',
  disallowedTools: ['Task', 'ExitPlanMode', 'Edit', 'Write', 'NotebookEdit'],
  model: 'haiku',
  systemPrompt: `You are a file search specialist. You excel at thoroughly navigating and exploring codebases.

=== CRITICAL: READ-ONLY MODE - NO FILE MODIFICATIONS ===
This is a READ-ONLY exploration task. You are STRICTLY PROHIBITED from:
- Creating new files (no Write, touch, or file creation of any kind)
- Modifying existing files (no Edit operations)
- Deleting files (no rm or deletion)
- Moving or copying files (no mv or cp)
- Creating temporary files anywhere, including /tmp
- Using redirect operators (>, >>, |) or heredocs to write to files
- Running ANY commands that change system state

Your role is EXCLUSIVELY to search and analyze existing code. You do NOT have access to file editing tools - attempting to edit files will fail.

Your strengths:
- Rapidly finding files using glob patterns
- Searching code and text with powerful regex patterns
- Reading and analyzing file contents

Guidelines:
- Use Glob for broad file pattern matching
- Use Grep for searching file contents with regex
- Use Read when you know the specific file path you need to read
- Use Bash ONLY for read-only operations (ls, git status, git log, git diff, find, cat, head, tail)
- NEVER use Bash for: mkdir, touch, rm, cp, mv, git add, git commit, npm install, pip install, or any file creation/modification
- Adapt your search approach based on the thoroughness level specified by the caller
- Return file paths as absolute paths in your final response
- For clear communication, avoid using emojis
- Communicate your final report directly as a regular message - do NOT attempt to create files

NOTE: You are meant to be a fast agent that returns output as quickly as possible. In order to achieve this you must:
- Make efficient use of the tools that you have at your disposal: be smart about how you search for files and implementations
- Wherever possible you should try to spawn multiple parallel tool calls for grepping and reading files

Complete the user's search request efficiently and report your findings clearly.`,
  source: 'built-in',
  location: 'built-in',
  baseDir: 'built-in',
}

const BUILTIN_PLAN: AgentConfig = {
  agentType: 'Plan',
  whenToUse:
    'Software architect agent for designing implementation plans. Use this when you need to plan the implementation strategy for a task. Returns step-by-step plans, identifies critical files, and considers architectural trade-offs.',
  tools: '*',
  disallowedTools: ['Task', 'ExitPlanMode', 'Edit', 'Write', 'NotebookEdit'],
  model: 'inherit',
  systemPrompt: `You are a software architect and planning specialist. Your role is to explore the codebase and design implementation plans.

=== CRITICAL: READ-ONLY MODE - NO FILE MODIFICATIONS ===
This is a READ-ONLY planning task. You are STRICTLY PROHIBITED from:
- Creating new files (no Write, touch, or file creation of any kind)
- Modifying existing files (no Edit operations)
- Deleting files (no rm or deletion)
- Moving or copying files (no mv or cp)
- Creating temporary files anywhere, including /tmp
- Using redirect operators (>, >>, |) or heredocs to write to files
- Running ANY commands that change system state

Your role is EXCLUSIVELY to explore the codebase and design implementation plans. You do NOT have access to file editing tools - attempting to edit files will fail.

You will be provided with a set of requirements and optionally a perspective on how to approach the design process.

## Your Process

1. **Understand Requirements**: Focus on the requirements provided and apply your assigned perspective throughout the design process.

2. **Explore Thoroughly**:
   - Read any files provided to you in the initial prompt
   - Find existing patterns and conventions using Glob, Grep, and Read
   - Understand the current architecture
   - Identify similar features as reference
   - Trace through relevant code paths
   - Use Bash ONLY for read-only operations (ls, git status, git log, git diff, find, cat, head, tail)
   - NEVER use Bash for: mkdir, touch, rm, cp, mv, git add, git commit, npm install, pip install, or any file creation/modification

3. **Design Solution**:
   - Create implementation approach based on your assigned perspective
   - Consider trade-offs and architectural decisions
   - Follow existing patterns where appropriate

4. **Detail the Plan**:
   - Provide step-by-step implementation strategy
   - Identify dependencies and sequencing
   - Anticipate potential challenges

## Required Output

End your response with:

### Critical Files for Implementation
List 3-5 files most critical for implementing this plan:
- path/to/file1.ts - [Brief reason: e.g., "Core logic to modify"]
- path/to/file2.ts - [Brief reason: e.g., "Interfaces to implement"]
- path/to/file3.ts - [Brief reason: e.g., "Pattern to follow"]

REMEMBER: You can ONLY explore and plan. You CANNOT and MUST NOT write, edit, or modify any files. You do NOT have access to file editing tools.`,
  source: 'built-in',
  location: 'built-in',
  baseDir: 'built-in',
}

const BUILTIN_STATUSLINE_SETUP: AgentConfig = {
  agentType: 'statusline-setup',
  whenToUse:
    'Set up the CLI status line command (writes to ~/.kode/settings.json statusLine). Use when the user runs /statusline.',
  tools: ['Read', 'Edit', 'Bash'],
  systemPrompt: `You are the status line setup agent.

Your job is to configure a fast, single-line status command for the CLI UI.

Requirements:
- Write/update the user's ~/.kode/settings.json and set the top-level key "statusLine" to a shell command string.
- IMPORTANT: When using Read/Edit tools, use absolute paths (do not pass "~" to tool inputs).
- The command must be quick (ideally <200ms), produce a single line, and be safe to run repeatedly.
- Prefer using information that is generally available: current directory, git branch/dirty state, etc.
- If you can't infer the user's preferred status info from their shell config, ask them what they want and propose a reasonable default.

Suggested approach:
1) Inspect common shell config files (Read):
   - macOS/Linux: ~/.zshrc, ~/.bashrc, ~/.config/fish/config.fish
   - Windows: consider PowerShell profile if the user provides its location
2) Propose a statusLine command:
   - macOS/Linux: e.g. a small sh snippet that prints cwd basename and git branch if present
   - Windows: e.g. a short PowerShell one-liner that prints similar info
3) Update ~/.kode/settings.json:
   - If the file does not exist, create it as a minimal JSON object.
   - Preserve unrelated fields if present.
4) Reply with the exact command you set and how the user can change/remove it later.`,
  source: 'built-in',
  location: 'built-in',
  baseDir: 'built-in',
}

function mergeAgents(allAgents: AgentConfig[]): AgentConfig[] {
  const builtIn = allAgents.filter(a => a.source === 'built-in')
  const plugin = allAgents.filter(a => a.source === 'plugin')
  const user = allAgents.filter(a => a.source === 'userSettings')
  const project = allAgents.filter(a => a.source === 'projectSettings')
  const flag = allAgents.filter(a => a.source === 'flagSettings')
  const policy = allAgents.filter(a => a.source === 'policySettings')

  const ordered = [builtIn, plugin, user, project, flag, policy]
  const map = new Map<string, AgentConfig>()
  for (const group of ordered) {
    for (const agent of group) {
      map.set(agent.agentType, agent)
    }
  }
  return Array.from(map.values())
}

function inodeKeyForPath(filePath: string): string | null {
  try {
    const st = statSync(filePath)
    if (typeof (st as any).dev === 'number' && typeof (st as any).ino === 'number') {
      return `${(st as any).dev}:${(st as any).ino}`
    }
    return null
  } catch {
    return null
  }
}

function scanAgentPaths(options: {
  dirPathOrFile: string
  baseDir: string
  source: Exclude<AgentSource, 'built-in' | 'flagSettings'>
  seenInodes: Map<string, AgentSource>
}): AgentConfig[] {
  const out: AgentConfig[] = []

  const addFile = (filePath: string) => {
    if (!filePath.endsWith('.md')) return

    const inodeKey = inodeKeyForPath(filePath)
    if (inodeKey) {
      const existing = options.seenInodes.get(inodeKey)
      if (existing) return
      options.seenInodes.set(inodeKey, options.source)
    }

    const agent = parseAgentFromFile({
      filePath,
      baseDir: options.baseDir,
      source: options.source,
    })
    if (agent) out.push(agent)
  }

  let st: ReturnType<typeof statSync>
  try {
    st = statSync(options.dirPathOrFile)
  } catch {
    return []
  }

  if (st.isFile()) {
    addFile(options.dirPathOrFile)
    return out
  }

  if (!st.isDirectory()) return []

  for (const filePath of listMarkdownFilesRecursively(options.dirPathOrFile)) {
    addFile(filePath)
  }

  return out
}

async function loadAllAgents(): Promise<{
  activeAgents: AgentConfig[]
  allAgents: AgentConfig[]
}> {
  const builtinAgents: AgentConfig[] = [
    BUILTIN_GENERAL_PURPOSE,
    BUILTIN_STATUSLINE_SETUP,
    BUILTIN_EXPLORE,
    BUILTIN_PLAN,
  ]

  const seenInodes = new Map<string, AgentSource>()

  const sessionPlugins = getSessionPlugins()
  const pluginAgentDirs = sessionPlugins.flatMap(p => p.agentsDirs ?? [])
  const pluginAgents = pluginAgentDirs.flatMap(dir =>
    scanAgentPaths({
      dirPathOrFile: dir,
      baseDir: dir,
      source: 'plugin',
      seenInodes,
    }),
  )

  const policyAgentsDir = join(getClaudePolicyBaseDir(), '.claude', 'agents')
  const policyAgents = scanAgentPaths({
    dirPathOrFile: policyAgentsDir,
    baseDir: policyAgentsDir,
    source: 'policySettings',
    seenInodes,
  })

  const userAgents: AgentConfig[] = []
  if (isSettingSourceEnabled('userSettings')) {
    for (const root of getUserConfigRoots()) {
      const dir = join(root, 'agents')
      userAgents.push(
        ...scanAgentPaths({
          dirPathOrFile: dir,
          baseDir: dir,
          source: 'userSettings',
          seenInodes,
        }),
      )
    }
  }

  const projectAgents: AgentConfig[] = []
  if (isSettingSourceEnabled('projectSettings')) {
    const dirs = findProjectAgentDirs(getCwd())
    for (const dir of dirs) {
      projectAgents.push(
        ...scanAgentPaths({
          dirPathOrFile: dir,
          baseDir: dir,
          source: 'projectSettings',
          seenInodes,
        }),
      )
    }
  }

  const allAgents: AgentConfig[] = [
    ...builtinAgents,
    ...pluginAgents,
    ...userAgents,
    ...projectAgents,
    ...FLAG_AGENTS,
    ...policyAgents,
  ]

  const activeAgents = mergeAgents(allAgents)
  return { activeAgents, allAgents }
}

export const getActiveAgents = memoize(async (): Promise<AgentConfig[]> => {
  const { activeAgents } = await loadAllAgents()
  return activeAgents
})

export const getAllAgents = memoize(async (): Promise<AgentConfig[]> => {
  const { allAgents } = await loadAllAgents()
  return allAgents
})

export const getAgentByType = memoize(
  async (agentType: string): Promise<AgentConfig | undefined> => {
    const agents = await getActiveAgents()
    return agents.find(agent => agent.agentType === agentType)
  },
)

export const getAvailableAgentTypes = memoize(async (): Promise<string[]> => {
  const agents = await getActiveAgents()
  return agents.map(agent => agent.agentType)
})

export function clearAgentCache(): void {
  getActiveAgents.cache?.clear?.()
  getAllAgents.cache?.clear?.()
  getAgentByType.cache?.clear?.()
  getAvailableAgentTypes.cache?.clear?.()
}

let watchers: FSWatcher[] = []

export async function startAgentWatcher(onChange?: () => void): Promise<void> {
  await stopAgentWatcher()

  const watchDirs: string[] = []

  watchDirs.push(join(getClaudePolicyBaseDir(), '.claude', 'agents'))

  if (isSettingSourceEnabled('userSettings')) {
    for (const root of getUserConfigRoots()) {
      watchDirs.push(join(root, 'agents'))
    }
  }

  if (isSettingSourceEnabled('projectSettings')) {
    watchDirs.push(...findProjectAgentDirs(getCwd()))
  }

  for (const plugin of getSessionPlugins()) {
    for (const dir of plugin.agentsDirs ?? []) {
      watchDirs.push(dir)
    }
  }

  for (const dirPath of dedupeStrings(watchDirs)) {
    if (!existsSync(dirPath)) continue
    try {
      const watcher = watch(
        dirPath,
        { recursive: false },
        async (_eventType, filename) => {
          if (filename && filename.endsWith('.md')) {
            clearAgentCache()
            onChange?.()
          }
        },
      )
      watchers.push(watcher)
    } catch {
      continue
    }
  }
}

export async function stopAgentWatcher(): Promise<void> {
  try {
    for (const watcher of watchers) {
      try {
        watcher.close()
      } catch {
      }
    }
  } finally {
    watchers = []
  }
}
