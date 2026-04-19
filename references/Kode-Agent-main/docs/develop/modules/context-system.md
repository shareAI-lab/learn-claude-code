# Context System

## Overview

The Context System (`src/context.ts`) manages all contextual information about the project and environment that gets injected into AI conversations. It provides automatic context gathering, caching, and intelligent injection to improve AI response quality.

## Architecture

### Core Context Manager

```typescript
interface ContextManager {
  // Context gathering
  getContext(): Promise<CompleteContext>
  getGitContext(): Promise<GitContext>
  getProjectContext(): Promise<ProjectContext>
  getSystemContext(): SystemContext
  
  // Context files
  loadContextFile(): Promise<string | null>
  loadClaudeFile(): Promise<string | null>
  
  // Context manipulation
  setContext(key: string, value: any): void
  removeContext(key: string): void
  clearContext(): void
  
  // Caching
  invalidateCache(): void
  getCacheStatus(): CacheStatus
}
```

## Context Types

### Complete Context Structure

```typescript
interface CompleteContext {
  // Project information
  projectName?: string
  projectDescription?: string
  projectType?: string
  
  // Git information
  gitStatus?: string
  recentCommits?: string
  currentBranch?: string
  remoteUrl?: string
  
  // Directory structure
  directoryStructure?: string
  importantFiles?: string[]
  
  // Code style and patterns
  codeStyle?: CodeStyle
  dependencies?: Dependencies
  
  // Documentation
  contextFile?: string      // AGENTS.md content
  claudeFile?: string       // CLAUDE.md content
  readmeContent?: string    // README.md content
  
  // System information
  platform?: string
  cwd?: string
  timestamp?: string
  
  // Custom context
  customContext?: Record<string, any>
}
```

### Git Context

```typescript
interface GitContext {
  isGitRepo: boolean
  branch?: string
  status?: string
  recentCommits?: Commit[]
  modifiedFiles?: string[]
  untrackedFiles?: string[]
  stagedFiles?: string[]
  remotes?: Remote[]
  lastCommitInfo?: {
    hash: string
    author: string
    date: string
    message: string
  }
}

async function getGitContext(): Promise<GitContext> {
  const isGitRepo = await checkIsGitRepo()
  
  if (!isGitRepo) {
    return { isGitRepo: false }
  }
  
  const [status, branch, commits, remotes] = await Promise.all([
    getGitStatus(),
    getCurrentBranch(),
    getRecentCommits(10),
    getRemotes()
  ])
  
  return {
    isGitRepo: true,
    branch,
    status,
    recentCommits: commits,
    modifiedFiles: parseModifiedFiles(status),
    untrackedFiles: parseUntrackedFiles(status),
    stagedFiles: parseStagedFiles(status),
    remotes,
    lastCommitInfo: commits[0]
  }
}
```

### Project Context

```typescript
interface ProjectContext {
  type: ProjectType
  framework?: string
  language?: string
  packageManager?: PackageManager
  testFramework?: string
  buildTool?: string
  dependencies?: Record<string, string>
  devDependencies?: Record<string, string>
  scripts?: Record<string, string>
  configuration?: ProjectConfig
}

class ProjectAnalyzer {
  async analyze(): Promise<ProjectContext> {
    const files = await this.discoverProjectFiles()
    const type = this.detectProjectType(files)
    
    switch (type) {
      case 'node':
        return this.analyzeNodeProject()
      case 'python':
        return this.analyzePythonProject()
      case 'rust':
        return this.analyzeRustProject()
      case 'go':
        return this.analyzeGoProject()
      default:
        return this.analyzeGenericProject()
    }
  }
  
  private async analyzeNodeProject(): Promise<ProjectContext> {
    const packageJson = await this.readPackageJson()
    
    return {
      type: 'node',
      framework: this.detectFramework(packageJson),
      language: this.detectLanguage(packageJson),
      packageManager: this.detectPackageManager(),
      testFramework: this.detectTestFramework(packageJson),
      buildTool: this.detectBuildTool(packageJson),
      dependencies: packageJson.dependencies,
      devDependencies: packageJson.devDependencies,
      scripts: packageJson.scripts,
      configuration: await this.loadNodeConfig()
    }
  }
  
  private detectFramework(pkg: PackageJson): string | undefined {
    const deps = { ...pkg.dependencies, ...pkg.devDependencies }
    
    if (deps['react']) return 'react'
    if (deps['vue']) return 'vue'
    if (deps['@angular/core']) return 'angular'
    if (deps['svelte']) return 'svelte'
    if (deps['next']) return 'nextjs'
    if (deps['nuxt']) return 'nuxt'
    if (deps['express']) return 'express'
    if (deps['fastify']) return 'fastify'
    if (deps['koa']) return 'koa'
    if (deps['nest']) return 'nestjs'
    
    return undefined
  }
}
```

## Context Files

### AGENTS.md

```typescript
class ContextFileLoader {
  private readonly CONTEXT_PATHS = [
    'AGENTS.md',
    '.claude/AGENTS.md',
    'docs/AGENTS.md',
    '.github/AGENTS.md'
  ]
  
  async loadContextFile(): Promise<string | null> {
    for (const path of this.CONTEXT_PATHS) {
      const fullPath = join(getCwd(), path)
      
      if (existsSync(fullPath)) {
        try {
          const content = await fs.readFile(fullPath, 'utf-8')
          return this.processContextFile(content)
        } catch (error) {
          console.warn(`Failed to read ${path}:`, error)
        }
      }
    }
    
    return null
  }
  
  private processContextFile(content: string): string {
    // Process includes
    content = this.processIncludes(content)
    
    // Process variables
    content = this.processVariables(content)
    
    // Process conditionals
    content = this.processConditionals(content)
    
    return content
  }
  
  private processIncludes(content: string): string {
    const INCLUDE_REGEX = /<!-- include: (.+) -->/g
    
    return content.replace(INCLUDE_REGEX, (match, filePath) => {
      try {
        const fullPath = join(getCwd(), filePath.trim())
        if (existsSync(fullPath)) {
          return readFileSync(fullPath, 'utf-8')
        }
      } catch (error) {
        console.warn(`Failed to include ${filePath}:`, error)
      }
      return match
    })
  }
  
  private processVariables(content: string): string {
    const variables = {
      PROJECT_NAME: this.getProjectName(),
      CWD: getCwd(),
      DATE: new Date().toISOString(),
      GIT_BRANCH: this.getCurrentBranch(),
      NODE_VERSION: process.version
    }
    
    return content.replace(/\{\{(\w+)\}\}/g, (match, key) => {
      return variables[key] || match
    })
  }
}
```

### CLAUDE.md

```typescript
class ClaudeFileLoader {
  private readonly CLAUDE_PATHS = [
    'CLAUDE.md',
    '.claude/CLAUDE.md'
  ]
  
  private readonly GLOBAL_CLAUDE_PATH = join(homedir(), '.claude', 'CLAUDE.md')
  
  async loadClaudeFile(): Promise<ClaudeFileContent> {
    const [projectFile, globalFile] = await Promise.all([
      this.loadProjectClaudeFile(),
      this.loadGlobalClaudeFile()
    ])
    
    return {
      project: projectFile,
      global: globalFile,
      merged: this.mergeClaudeFiles(projectFile, globalFile)
    }
  }
  
  private async loadProjectClaudeFile(): Promise<string | null> {
    for (const path of this.CLAUDE_PATHS) {
      const fullPath = join(getCwd(), path)
      
      if (existsSync(fullPath)) {
        return fs.readFile(fullPath, 'utf-8')
      }
    }
    
    return null
  }
  
  private async loadGlobalClaudeFile(): Promise<string | null> {
    if (existsSync(this.GLOBAL_CLAUDE_PATH)) {
      return fs.readFile(this.GLOBAL_CLAUDE_PATH, 'utf-8')
    }
    
    return null
  }
  
  private mergeClaudeFiles(
    project: string | null,
    global: string | null
  ): string {
    const parts: string[] = []
    
    if (global) {
      parts.push('# Global Instructions\n\n' + global)
    }
    
    if (project) {
      parts.push('# Project Instructions\n\n' + project)
    }
    
    return parts.join('\n\n---\n\n')
  }
}
```

## Directory Structure Analysis

### Directory Scanner

```typescript
class DirectoryStructureAnalyzer {
  private readonly IGNORE_PATTERNS = [
    'node_modules',
    '.git',
    'dist',
    'build',
    'coverage',
    '.next',
    '__pycache__',
    '.pytest_cache',
    'venv',
    '.venv',
    'target',
    '.idea',
    '.vscode'
  ]
  
  private readonly MAX_DEPTH = 4
  private readonly MAX_FILES = 1000
  
  async analyze(rootPath: string = getCwd()): Promise<DirectoryStructure> {
    const structure = await this.scanDirectory(rootPath, 0)
    const summary = this.generateSummary(structure)
    const tree = this.generateTree(structure)
    
    return {
      structure,
      summary,
      tree,
      importantFiles: this.identifyImportantFiles(structure)
    }
  }
  
  private async scanDirectory(
    path: string,
    depth: number
  ): Promise<DirectoryNode> {
    if (depth >= this.MAX_DEPTH) {
      return { path, type: 'directory', truncated: true }
    }
    
    const entries = await fs.readdir(path, { withFileTypes: true })
    const children: DirectoryNode[] = []
    let fileCount = 0
    
    for (const entry of entries) {
      if (this.shouldIgnore(entry.name)) continue
      if (fileCount >= this.MAX_FILES) break
      
      const fullPath = join(path, entry.name)
      
      if (entry.isDirectory()) {
        const child = await this.scanDirectory(fullPath, depth + 1)
        children.push(child)
      } else {
        children.push({
          path: fullPath,
          name: entry.name,
          type: 'file',
          size: await this.getFileSize(fullPath),
          extension: extname(entry.name)
        })
        fileCount++
      }
    }
    
    return {
      path,
      type: 'directory',
      children,
      fileCount,
      totalSize: await this.calculateTotalSize(children)
    }
  }
  
  private generateTree(node: DirectoryNode, prefix = ''): string {
    const lines: string[] = []
    
    if (node.type === 'file') {
      lines.push(prefix + node.name)
    } else if (node.children) {
      for (let i = 0; i < node.children.length; i++) {
        const child = node.children[i]
        const isLast = i === node.children.length - 1
        const connector = isLast ? '└── ' : '├── '
        const extension = isLast ? '    ' : '│   '
        
        lines.push(prefix + connector + basename(child.path))
        
        if (child.type === 'directory' && child.children) {
          const subtree = this.generateTree(child, prefix + extension)
          lines.push(subtree)
        }
      }
    }
    
    return lines.join('\n')
  }
  
  private identifyImportantFiles(structure: DirectoryNode): string[] {
    const important: string[] = []
    const importantPatterns = [
      /^package\.json$/,
      /^tsconfig\.json$/,
      /^README\.md$/i,
      /^CONTEXT\.md$/,
      /^CLAUDE\.md$/,
      /^\.env(\.example)?$/,
      /^docker-compose\.yml$/,
      /^Dockerfile$/,
      /^requirements\.txt$/,
      /^pyproject\.toml$/,
      /^Cargo\.toml$/,
      /^go\.mod$/,
      /^pom\.xml$/,
      /^build\.gradle$/
    ]
    
    function traverse(node: DirectoryNode) {
      if (node.type === 'file') {
        const name = basename(node.path)
        if (importantPatterns.some(pattern => pattern.test(name))) {
          important.push(node.path)
        }
      } else if (node.children) {
        node.children.forEach(traverse)
      }
    }
    
    traverse(structure)
    return important
  }
}
```

## Code Style Detection

### Style Analyzer

```typescript
class CodeStyleAnalyzer {
  async analyze(): Promise<CodeStyle> {
    const files = await this.findSourceFiles()
    const samples = await this.takeSamples(files, 10)
    
    return {
      indentation: this.detectIndentation(samples),
      quotes: this.detectQuotes(samples),
      semicolons: this.detectSemicolons(samples),
      lineEndings: this.detectLineEndings(samples),
      trailingCommas: this.detectTrailingCommas(samples),
      bracketSpacing: this.detectBracketSpacing(samples),
      naming: this.detectNamingConventions(samples),
      maxLineLength: this.detectMaxLineLength(samples),
      fileNaming: this.detectFileNaming(files)
    }
  }
  
  private detectIndentation(samples: string[]): IndentationStyle {
    let spaces = 0
    let tabs = 0
    let twoSpaces = 0
    let fourSpaces = 0
    
    for (const sample of samples) {
      const lines = sample.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('\t')) {
          tabs++
        } else if (line.startsWith('    ')) {
          fourSpaces++
          spaces++
        } else if (line.startsWith('  ')) {
          twoSpaces++
          spaces++
        }
      }
    }
    
    if (tabs > spaces) {
      return { type: 'tabs', size: 1 }
    } else if (fourSpaces > twoSpaces) {
      return { type: 'spaces', size: 4 }
    } else {
      return { type: 'spaces', size: 2 }
    }
  }
  
  private detectNamingConventions(samples: string[]): NamingConventions {
    const patterns = {
      camelCase: /[a-z][a-zA-Z0-9]*/g,
      PascalCase: /[A-Z][a-zA-Z0-9]*/g,
      snake_case: /[a-z]+(_[a-z]+)+/g,
      kebab_case: /[a-z]+(-[a-z]+)+/g,
      SCREAMING_SNAKE: /[A-Z]+(_[A-Z]+)+/g
    }
    
    const counts: Record<string, number> = {}
    
    for (const sample of samples) {
      for (const [name, pattern] of Object.entries(patterns)) {
        const matches = sample.match(pattern) || []
        counts[name] = (counts[name] || 0) + matches.length
      }
    }
    
    return {
      variables: this.getMostCommon(counts, ['camelCase', 'snake_case']),
      functions: this.getMostCommon(counts, ['camelCase', 'snake_case']),
      classes: this.getMostCommon(counts, ['PascalCase', 'camelCase']),
      constants: this.getMostCommon(counts, ['SCREAMING_SNAKE', 'camelCase']),
      files: this.getMostCommon(counts, ['kebab_case', 'snake_case', 'camelCase'])
    }
  }
}
```

## Context Injection

### Message Context Builder

```typescript
class MessageContextBuilder {
  buildSystemContext(context: CompleteContext): string {
    const sections: string[] = []
    
    // Add CLAUDE.md instructions first (highest priority)
    if (context.claudeFile) {
      sections.push(context.claudeFile)
    }
    
    // Add project context
    if (context.contextFile) {
      sections.push('# Project Context\n\n' + context.contextFile)
    }
    
    // Add git status
    if (context.gitStatus) {
      sections.push('# Git Status\n\n```\n' + context.gitStatus + '\n```')
    }
    
    // Add directory structure
    if (context.directoryStructure) {
      sections.push('# Directory Structure\n\n```\n' + context.directoryStructure + '\n```')
    }
    
    // Add important files list
    if (context.importantFiles?.length) {
      sections.push('# Important Files\n\n' + context.importantFiles.map(f => `- ${f}`).join('\n'))
    }
    
    // Add code style
    if (context.codeStyle) {
      sections.push('# Code Style\n\n' + this.formatCodeStyle(context.codeStyle))
    }
    
    // Add custom context
    if (context.customContext) {
      sections.push('# Additional Context\n\n' + JSON.stringify(context.customContext, null, 2))
    }
    
    return sections.join('\n\n---\n\n')
  }
  
  private formatCodeStyle(style: CodeStyle): string {
    return `
- Indentation: ${style.indentation.type} (${style.indentation.size})
- Quotes: ${style.quotes}
- Semicolons: ${style.semicolons}
- Line endings: ${style.lineEndings}
- Trailing commas: ${style.trailingCommas}
- Bracket spacing: ${style.bracketSpacing}
- Max line length: ${style.maxLineLength}
`
  }
}
```

### Smart Context Injection

```typescript
class SmartContextInjector {
  inject(
    messages: Message[],
    context: CompleteContext,
    options: InjectionOptions = {}
  ): Message[] {
    const injector = new ContextInjector(context, options)
    
    // Determine what context to include based on conversation
    const relevantContext = injector.analyzeRelevance(messages)
    
    // Build system message with relevant context
    const systemMessage = injector.buildSystemMessage(relevantContext)
    
    // Inject at appropriate position
    return injector.injectAtPosition(messages, systemMessage, options.position || 'start')
  }
  
  private analyzeRelevance(messages: Message[]): RelevantContext {
    const keywords = this.extractKeywords(messages)
    const topics = this.identifyTopics(keywords)
    
    return {
      includeGit: topics.includes('version-control') || keywords.has('commit'),
      includeStructure: topics.includes('architecture') || keywords.has('structure'),
      includeStyle: topics.includes('formatting') || keywords.has('style'),
      includeDependencies: topics.includes('packages') || keywords.has('install'),
      includeTests: topics.includes('testing') || keywords.has('test'),
      includeConfig: topics.includes('configuration') || keywords.has('config')
    }
  }
  
  private extractKeywords(messages: Message[]): Set<string> {
    const keywords = new Set<string>()
    const commonWords = new Set(['the', 'a', 'an', 'is', 'are', 'was', 'were'])
    
    for (const message of messages) {
      const words = message.content
        .toLowerCase()
        .split(/\W+/)
        .filter(word => word.length > 2 && !commonWords.has(word))
      
      words.forEach(word => keywords.add(word))
    }
    
    return keywords
  }
}
```

## Caching

### Context Cache

```typescript
class ContextCache {
  private cache: Map<string, CachedContext> = new Map()
  private readonly TTL = 60000 // 1 minute
  
  get(key: string): CompleteContext | null {
    const cached = this.cache.get(key)
    
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(key)
      return null
    }
    
    return cached.context
  }
  
  set(key: string, context: CompleteContext): void {
    this.cache.set(key, {
      context,
      timestamp: Date.now()
    })
    
    // Limit cache size
    if (this.cache.size > 10) {
      const oldest = Array.from(this.cache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp)[0]
      
      this.cache.delete(oldest[0])
    }
  }
  
  invalidate(pattern?: string): void {
    if (!pattern) {
      this.cache.clear()
      return
    }
    
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key)
      }
    }
  }
  
  getCacheKey(options: ContextOptions): string {
    return JSON.stringify({
      cwd: getCwd(),
      includeGit: options.includeGit,
      includeStructure: options.includeStructure,
      includeStyle: options.includeStyle
    })
  }
}
```

### Lazy Loading

```typescript
class LazyContextLoader {
  private loaders: Map<string, () => Promise<any>> = new Map()
  private results: Map<string, any> = new Map()
  
  constructor() {
    this.registerLoaders()
  }
  
  private registerLoaders(): void {
    this.loaders.set('git', () => getGitContext())
    this.loaders.set('project', () => new ProjectAnalyzer().analyze())
    this.loaders.set('structure', () => new DirectoryStructureAnalyzer().analyze())
    this.loaders.set('style', () => new CodeStyleAnalyzer().analyze())
    this.loaders.set('contextFile', () => new ContextFileLoader().loadContextFile())
    this.loaders.set('claudeFile', () => new ClaudeFileLoader().loadClaudeFile())
  }
  
  async load(keys: string[]): Promise<Record<string, any>> {
    const promises = keys.map(async key => {
      if (this.results.has(key)) {
        return { key, value: this.results.get(key) }
      }
      
      const loader = this.loaders.get(key)
      if (!loader) {
        console.warn(`No loader for context key: ${key}`)
        return { key, value: null }
      }
      
      try {
        const value = await loader()
        this.results.set(key, value)
        return { key, value }
      } catch (error) {
        console.error(`Failed to load context ${key}:`, error)
        return { key, value: null }
      }
    })
    
    const results = await Promise.all(promises)
    
    return results.reduce((acc, { key, value }) => {
      acc[key] = value
      return acc
    }, {} as Record<string, any>)
  }
  
  clear(): void {
    this.results.clear()
  }
}
```

## Performance Monitoring

### Context Metrics

```typescript
class ContextMetrics {
  private metrics: Map<string, Metric> = new Map()
  
  async measure<T>(
    name: string,
    operation: () => Promise<T>
  ): Promise<T> {
    const start = Date.now()
    
    try {
      const result = await operation()
      const duration = Date.now() - start
      
      this.record(name, duration, 'success')
      return result
      
    } catch (error) {
      const duration = Date.now() - start
      this.record(name, duration, 'error')
      throw error
    }
  }
  
  private record(
    name: string,
    duration: number,
    status: 'success' | 'error'
  ): void {
    const metric = this.metrics.get(name) || {
      count: 0,
      totalDuration: 0,
      avgDuration: 0,
      maxDuration: 0,
      minDuration: Infinity,
      errors: 0
    }
    
    metric.count++
    metric.totalDuration += duration
    metric.avgDuration = metric.totalDuration / metric.count
    metric.maxDuration = Math.max(metric.maxDuration, duration)
    metric.minDuration = Math.min(metric.minDuration, duration)
    
    if (status === 'error') {
      metric.errors++
    }
    
    this.metrics.set(name, metric)
    
    // Log slow operations
    if (duration > 1000) {
      console.warn(`Slow context operation ${name}: ${duration}ms`)
    }
  }
  
  getReport(): MetricsReport {
    return {
      operations: Array.from(this.metrics.entries()).map(([name, metric]) => ({
        name,
        ...metric
      })),
      totalOperations: Array.from(this.metrics.values()).reduce((sum, m) => sum + m.count, 0),
      totalDuration: Array.from(this.metrics.values()).reduce((sum, m) => sum + m.totalDuration, 0)
    }
  }
}
```

The Context System provides comprehensive project understanding through automatic discovery, intelligent caching, and smart injection, ensuring AI responses are always contextually relevant and accurate.