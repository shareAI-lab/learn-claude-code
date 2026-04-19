import figures from 'figures'
import { memoize } from 'lodash-es'
import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { basename, dirname, join, resolve } from 'path'
import { homedir } from 'os'
import matter from 'gray-matter'
import yaml from 'js-yaml'
import { getSessionPlugins } from '@utils/session/sessionPlugins'
import { readLocalSettings, updateLocalSettings } from '@utils/config/localSettings'
import { getCwd } from '@utils/state'
import { isSettingSourceEnabled } from '@utils/config/settingSources'

export type OutputStyleSource =
  | 'built-in'
  | 'plugin'
  | 'userSettings'
  | 'projectSettings'
  | 'policySettings'

export type OutputStyleDefinition = {
  name: string
  description: string
  prompt: string
  source: OutputStyleSource
  keepCodingInstructions?: boolean
}

export type OutputStyleMap = Record<string, OutputStyleDefinition | null>

export const DEFAULT_OUTPUT_STYLE = 'default'

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

function getUserConfigBaseDirs(): { claude: string; kode: string }[] {
  const out: { claude: string; kode: string }[] = []

  const hasAnyOverride =
    typeof process.env.CLAUDE_CONFIG_DIR === 'string' ||
    typeof process.env.KODE_CONFIG_DIR === 'string'

  const claudeBase = normalizeString(process.env.CLAUDE_CONFIG_DIR)
  const kodeBase = normalizeString(process.env.KODE_CONFIG_DIR)

  if (claudeBase) out.push({ claude: resolve(claudeBase), kode: resolve(claudeBase) })
  if (kodeBase) out.push({ claude: resolve(kodeBase), kode: resolve(kodeBase) })

  if (hasAnyOverride) {
    return dedupeConfigBases(out)
  }

  return dedupeConfigBases([
    { claude: join(homedir(), '.claude'), kode: join(homedir(), '.claude') },
    { claude: join(homedir(), '.kode'), kode: join(homedir(), '.kode') },
  ])
}

function dedupeConfigBases(
  bases: Array<{ claude: string; kode: string }>,
): Array<{ claude: string; kode: string }> {
  const seen = new Set<string>()
  const out: Array<{ claude: string; kode: string }> = []
  for (const base of bases) {
    const key = `${base.claude}::${base.kode}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(base)
  }
  return out
}

function findProjectSubdirs(subdir: string, cwd: string): string[] {
  const result: string[] = []
  const home = resolve(homedir())
  let current = resolve(cwd)

  while (current !== home) {
    const claudeDir = join(current, '.claude', subdir)
    if (existsSync(claudeDir)) result.push(claudeDir)

    const kodeDir = join(current, '.kode', subdir)
    if (existsSync(kodeDir)) result.push(kodeDir)

    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }

  return result
}

function markdownFirstLineOrHeading(content: string, fallback: string): string {
  const lines = content.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    const heading = trimmed.match(/^#+\s+(.+)$/)?.[1] ?? trimmed
    return heading.length > 100 ? `${heading.substring(0, 97)}...` : heading
  }
  return fallback
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

    let entries: Array<{ name: string; isDirectory(): boolean; isFile(): boolean; isSymbolicLink(): boolean }>
    try {
      entries = readdirSync(dirPath, { withFileTypes: true, encoding: 'utf8' }) as any
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
    return { frontmatter: (parsed.data as any) ?? {}, content: String(parsed.content ?? '') }
  } catch {
    return null
  }
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

const INSIGHTS_SECTION = `
## Insights
In order to encourage learning, before and after writing code, always provide brief educational explanations about implementation choices using (with backticks):
"\`${figures.star} Insight ─────────────────────────────────────\`
[2-3 key educational points]
\`─────────────────────────────────────────────────\`"

These insights should be included in the conversation, not in the codebase. You should generally focus on interesting insights that are specific to the codebase or the code you just wrote, rather than general programming concepts.`

function getBuiltInOutputStyles(): OutputStyleMap {
  return {
    [DEFAULT_OUTPUT_STYLE]: null,
    Explanatory: {
      name: 'Explanatory',
      source: 'built-in',
      description: 'Claude explains its implementation choices and codebase patterns',
      keepCodingInstructions: true,
      prompt: `You are an interactive CLI tool that helps users with software engineering tasks. In addition to software engineering tasks, you should provide educational insights about the codebase along the way.

You should be clear and educational, providing helpful explanations while remaining focused on the task. Balance educational content with task completion. When providing insights, you may exceed typical length constraints, but remain focused and relevant.

# Explanatory Style Active
${INSIGHTS_SECTION}`,
    },
    Learning: {
      name: 'Learning',
      source: 'built-in',
      description:
        'Claude pauses and asks you to write small pieces of code for hands-on practice',
      keepCodingInstructions: true,
      prompt: `You are an interactive CLI tool that helps users with software engineering tasks. In addition to software engineering tasks, you should help users learn more about the codebase through hands-on practice and educational insights.

You should be collaborative and encouraging. Balance task completion with learning by requesting user input for meaningful design decisions while handling routine implementation yourself.   

# Learning Style Active
## Requesting Human Contributions
In order to encourage learning, ask the human to contribute 2-10 line code pieces when generating 20+ lines involving:
- Design decisions (error handling, data structures)
- Business logic with multiple valid approaches  
- Key algorithms or interface definitions

**TodoList Integration**: If using a TodoList for the overall task, include a specific todo item like "Request human input on [specific decision]" when planning to request human input. This ensures proper task tracking. Note: TodoList is not required for all tasks.

Example TodoList flow:
   ✓ "Set up component structure with placeholder for logic"
   ✓ "Request human collaboration on decision logic implementation"
   ✓ "Integrate contribution and complete feature"

### Request Format
\`\`\`
${figures.bullet} **Learn by Doing**
**Context:** [what's built and why this decision matters]
**Your Task:** [specific function/section in file, mention file and TODO(human) but do not include line numbers]
**Guidance:** [trade-offs and constraints to consider]
\`\`\`

### Key Guidelines
- Frame contributions as valuable design decisions, not busy work
- You must first add a TODO(human) section into the codebase with your editing tools before making the Learn by Doing request      
- Make sure there is one and only one TODO(human) section in the code
- Don't take any action or output anything after the Learn by Doing request. Wait for human implementation before proceeding.

### Example Requests

**Whole Function Example:**
\`\`\`
${figures.bullet} **Learn by Doing**

**Context:** I've set up the hint feature UI with a button that triggers the hint system. The infrastructure is ready: when clicked, it calls selectHintCell() to determine which cell to hint, then highlights that cell with a yellow background and shows possible values. The hint system needs to decide which empty cell would be most helpful to reveal to the user.

**Your Task:** In sudoku.js, implement the selectHintCell(board) function. Look for TODO(human). This function should analyze the board and return {row, col} for the best cell to hint, or null if the puzzle is complete.

**Guidance:** Consider multiple strategies: prioritize cells with only one possible value (naked singles), or cells that appear in rows/columns/boxes with many filled cells. You could also consider a balanced approach that helps without making it too easy. The board parameter is a 9x9 array where 0 represents empty cells.
\`\`\`

**Partial Function Example:**
\`\`\`
${figures.bullet} **Learn by Doing**

**Context:** I've built a file upload component that validates files before accepting them. The main validation logic is complete, but it needs specific handling for different file type categories in the switch statement.

**Your Task:** In upload.js, inside the validateFile() function's switch statement, implement the 'case "document":' branch. Look for TODO(human). This should validate document files (pdf, doc, docx).

**Guidance:** Consider checking file size limits (maybe 10MB for documents?), validating the file extension matches the MIME type, and returning {valid: boolean, error?: string}. The file object has properties: name, size, type.
\`\`\`

**Debugging Example:**
\`\`\`
${figures.bullet} **Learn by Doing**

**Context:** The user reported that number inputs aren't working correctly in the calculator. I've identified the handleInput() function as the likely source, but need to understand what values are being processed.

**Your Task:** In calculator.js, inside the handleInput() function, add 2-3 console.log statements after the TODO(human) comment to help debug why number inputs fail.

**Guidance:** Consider logging: the raw input value, the parsed result, and any validation state. This will help us understand where the conversion breaks.
\`\`\`

### After Contributions
Share one insight connecting their code to broader patterns or system effects. Avoid praise or repetition.

## Insights
${INSIGHTS_SECTION}`,
    },
  }
}

function parseKeepCodingInstructions(value: unknown): boolean | undefined {
  if (value === 'true') return true
  if (value === 'false') return false
  return undefined
}

function parseCustomOutputStyleFile(options: {
  filePath: string
  source: Exclude<OutputStyleSource, 'built-in' | 'plugin'>
}): OutputStyleDefinition | null {
  const parsed = readMarkdownFile(options.filePath)
  if (!parsed) return null

  const base = basename(options.filePath, '.md')
  const name = normalizeString(parsed.frontmatter?.name) ?? base
  const description =
    normalizeString(parsed.frontmatter?.description) ??
    markdownFirstLineOrHeading(parsed.content, `Custom ${base} output style`)
  const keepCodingInstructions = parseKeepCodingInstructions(
    parsed.frontmatter?.['keep-coding-instructions'],
  )
  const prompt = parsed.content.trim()

  return {
    name,
    description,
    prompt,
    source: options.source,
    ...(keepCodingInstructions !== undefined ? { keepCodingInstructions } : {}),
  }
}

function parsePluginOutputStyleFile(options: {
  filePath: string
  pluginName: string
  seen: Set<string>
}): OutputStyleDefinition | null {
  const inodeKey = inodeKeyForPath(options.filePath)
  const dedupeKey = inodeKey ? `inode:${inodeKey}` : `path:${options.filePath}`
  if (options.seen.has(dedupeKey)) return null
  options.seen.add(dedupeKey)

  const parsed = readMarkdownFile(options.filePath)
  if (!parsed) return null

  const base = basename(options.filePath, '.md')
  const styleName = normalizeString(parsed.frontmatter?.name) ?? base
  const fullName = `${options.pluginName}:${styleName}`
  const description =
    normalizeString(parsed.frontmatter?.description) ??
    markdownFirstLineOrHeading(
      parsed.content,
      `Output style from ${options.pluginName} plugin`,
    )
  const prompt = parsed.content.trim()

  return {
    name: fullName,
    description,
    prompt,
    source: 'plugin',
  }
}

function loadPluginOutputStyles(): OutputStyleDefinition[] {
  const out: OutputStyleDefinition[] = []
  const plugins = getSessionPlugins()
  for (const plugin of plugins) {
    const pluginName = plugin.name
    const seen = new Set<string>()
    for (const dir of plugin.outputStylesDirs ?? []) {
      let st: ReturnType<typeof statSync>
      try {
        st = statSync(dir)
      } catch {
        continue
      }
      if (st.isFile()) {
        if (!dir.endsWith('.md')) continue
        const style = parsePluginOutputStyleFile({
          filePath: dir,
          pluginName,
          seen,
        })
        if (style) out.push(style)
        continue
      }

      if (st.isDirectory()) {
        const files = listMarkdownFilesRecursively(dir)
        for (const filePath of files) {
          const style = parsePluginOutputStyleFile({
            filePath,
            pluginName,
            seen,
          })
          if (style) out.push(style)
        }
      }
    }
  }
  return out
}

function loadCustomOutputStyles(options: { cwd: string }): OutputStyleDefinition[] {
  const out: OutputStyleDefinition[] = []
  const seen = new Set<string>()

  const policyDir = join(
    getClaudePolicyBaseDir(),
    '.claude',
    'output-styles',
  )
  for (const filePath of listMarkdownFilesRecursively(policyDir)) {
    const inodeKey = inodeKeyForPath(filePath)
    const dedupeKey = inodeKey ? `inode:${inodeKey}` : `path:${filePath}`
    if (seen.has(dedupeKey)) continue
    seen.add(dedupeKey)
    const style = parseCustomOutputStyleFile({
      filePath,
      source: 'policySettings',
    })
    if (style) out.push(style)
  }

  if (isSettingSourceEnabled('userSettings')) {
    const userBases = getUserConfigBaseDirs()
    for (const base of userBases) {
      for (const userBaseDir of new Set([base.claude, base.kode])) {
        const dirPath = join(userBaseDir, 'output-styles')
        for (const filePath of listMarkdownFilesRecursively(dirPath)) {
          const inodeKey = inodeKeyForPath(filePath)
          const dedupeKey = inodeKey ? `inode:${inodeKey}` : `path:${filePath}`
          if (seen.has(dedupeKey)) continue
          seen.add(dedupeKey)
          const style = parseCustomOutputStyleFile({
            filePath,
            source: 'userSettings',
          })
          if (style) out.push(style)
        }
      }
    }
  }

  if (isSettingSourceEnabled('projectSettings')) {
    for (const dirPath of findProjectSubdirs('output-styles', options.cwd)) {
      for (const filePath of listMarkdownFilesRecursively(dirPath)) {
        const inodeKey = inodeKeyForPath(filePath)
        const dedupeKey = inodeKey ? `inode:${inodeKey}` : `path:${filePath}`
        if (seen.has(dedupeKey)) continue
        seen.add(dedupeKey)
        const style = parseCustomOutputStyleFile({
          filePath,
          source: 'projectSettings',
        })
        if (style) out.push(style)
      }
    }
  }

  return out
}

export const getAvailableOutputStyles = memoize((): OutputStyleMap => {
  const cwd = getCwd()
  const builtIn = getBuiltInOutputStyles()
  const merged: OutputStyleMap = { ...builtIn }

  for (const style of loadPluginOutputStyles()) {
    merged[style.name] = style
  }

  const custom = loadCustomOutputStyles({ cwd })
  const user = custom.filter(s => s.source === 'userSettings')
  const project = custom.filter(s => s.source === 'projectSettings')
  const policy = custom.filter(s => s.source === 'policySettings')

  for (const style of user) merged[style.name] = style
  for (const style of project) merged[style.name] = style
  for (const style of policy) merged[style.name] = style

  return merged
})

export function clearOutputStyleCache(): void {
  ;(getAvailableOutputStyles as any).cache?.clear?.()
}

export function getCurrentOutputStyle(): string {
  if (!isSettingSourceEnabled('localSettings')) return DEFAULT_OUTPUT_STYLE

  const settings = readLocalSettings()
  const candidate = normalizeString(settings.outputStyle)
  return candidate ?? DEFAULT_OUTPUT_STYLE
}

export function setCurrentOutputStyle(styleName: string): void {
  updateLocalSettings({ outputStyle: styleName })
}

export function resolveOutputStyleName(input: string): string | null {
  const raw = normalizeString(input)
  if (!raw) return null
  const styles = getAvailableOutputStyles()
  if (raw in styles) return raw
  const lower = raw.toLowerCase()
  for (const name of Object.keys(styles)) {
    if (name.toLowerCase() === lower) return name
  }
  return null
}

export function getCurrentOutputStyleDefinition(): OutputStyleDefinition | null {
  const current = getCurrentOutputStyle()
  const styles = getAvailableOutputStyles()
  return styles[current] ?? null
}

export function getOutputStyleSystemPromptAdditions(): string[] {
  const style = getCurrentOutputStyleDefinition()
  if (!style) return []
  const prompt = style.prompt.trim()
  if (!prompt) return []
  return [`\n# Output Style: ${style.name}\n${prompt}\n`]
}
