# Custom Commands System

## Overview

The Custom Commands System (`src/services/customCommands.ts`) enables users to create reusable markdown-based commands that extend Kode's functionality. Commands are discovered from `.claude/commands/` and `.kode/commands/` directories and integrated seamlessly with the built-in command system.

## Architecture

### System Design

```typescript
interface CustomCommandSystem {
  // Discovery
  loadCustomCommands(): Promise<CustomCommandWithScope[]>
  scanMarkdownFiles(directory: string): Promise<string[]>
  
  // Parsing
  parseFrontmatter(content: string): ParsedCommand
  createCustomCommand(parsed: ParsedCommand): Command
  
  // Processing
  executeBashCommands(content: string): Promise<string>
  resolveFileReferences(content: string): Promise<string>
  
  // Management
  reloadCustomCommands(): void
  getCustomCommandDirectories(): CommandDirectories
}
```

## Command Structure

### File Format

```markdown
---
name: command-name
description: Brief description of the command
aliases: [alias1, alias2]
enabled: true
hidden: false
progressMessage: Running command...
argNames: [arg1, arg2]
allowed-tools: [file_read, file_edit]
---

# Command Content

Your command prompt goes here. You can use:
- Arguments: {arg1}, {arg2}
- Official format: $ARGUMENTS
- File references: @src/file.js
- Bash execution: !`git status`
```

### Frontmatter Schema

```typescript
export interface CustomCommandFrontmatter {
  // Core properties
  name?: string              // Command name (defaults to filename)
  description?: string       // Brief description
  aliases?: string[]        // Alternative names
  
  // Behavior control
  enabled?: boolean         // Whether command is active (default: true)
  hidden?: boolean          // Hide from help output (default: false)
  
  // Execution
  progressMessage?: string  // Message shown during execution
  argNames?: string[]       // Named argument placeholders
  'allowed-tools'?: string[] // Tool restrictions
  
  // Metadata (future extensions)
  version?: string
  author?: string
  tags?: string[]
  requires?: string[]       // Dependencies
}
```

## Discovery System

### Directory Scanning

```typescript
class CommandDiscovery {
  private readonly COMMAND_DIRS = {
    user: path.join(homedir(), '.claude', 'commands'),
    project: path.join(process.cwd(), '.claude', 'commands')
  }
  
  async discover(): Promise<CommandFile[]> {
    const files: CommandFile[] = []
    
    // Scan user commands (lower priority)
    if (existsSync(this.COMMAND_DIRS.user)) {
      const userFiles = await this.scanDirectory(this.COMMAND_DIRS.user)
      files.push(...userFiles.map(f => ({ ...f, scope: 'user' })))
    }
    
    // Scan project commands (higher priority)
    if (existsSync(this.COMMAND_DIRS.project)) {
      const projectFiles = await this.scanDirectory(this.COMMAND_DIRS.project)
      files.push(...projectFiles.map(f => ({ ...f, scope: 'project' })))
    }
    
    return files
  }
  
  private async scanDirectory(dir: string): Promise<string[]> {
    const files: string[] = []
    
    async function scan(currentDir: string, depth = 0) {
      if (depth > 5) return // Prevent deep recursion
      
      const entries = await fs.readdir(currentDir, { withFileTypes: true })
      
      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name)
        
        if (entry.isDirectory() && !entry.name.startsWith('.')) {
          await scan(fullPath, depth + 1)
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          files.push(fullPath)
        }
      }
    }
    
    await scan(dir)
    return files
  }
}
```

### Namespace Support

```typescript
class CommandNamespace {
  /**
   * Generate namespaced command name from file path
   * 
   * Examples:
   * - /commands/test.md → "test"
   * - /commands/dev/build.md → "dev:build"
   * - /commands/ci/github/deploy.md → "ci:github:deploy"
   */
  static fromPath(filePath: string, baseDir: string): string {
    const relative = path.relative(baseDir, filePath)
    const parts = relative.split(path.sep)
    const fileName = parts[parts.length - 1].replace('.md', '')
    
    if (parts.length === 1) {
      return fileName
    }
    
    // Create namespace from directory structure
    const namespace = parts.slice(0, -1).join(':')
    return `${namespace}:${fileName}`
  }
  
  /**
   * Add scope prefix to command name
   * 
   * Examples:
   * - "test" + "user" → "user:test"
   * - "dev:build" + "project" → "project:dev:build"
   */
  static addScope(name: string, scope: 'user' | 'project'): string {
    if (name.startsWith(`${scope}:`)) {
      return name
    }
    return `${scope}:${name}`
  }
}
```

## Parsing System

### Frontmatter Parser

```typescript
export function parseFrontmatter(content: string): {
  frontmatter: CustomCommandFrontmatter
  content: string
} {
  const FRONTMATTER_REGEX = /^---\s*\n([\s\S]*?)---\s*\n?/
  const match = content.match(FRONTMATTER_REGEX)
  
  if (!match) {
    return { frontmatter: {}, content }
  }
  
  const yamlContent = match[1] || ''
  const markdownContent = content.slice(match[0].length)
  
  const frontmatter = this.parseYAML(yamlContent)
  
  return { frontmatter, content: markdownContent }
}

private parseYAML(yaml: string): CustomCommandFrontmatter {
  const result: CustomCommandFrontmatter = {}
  const lines = yaml.split('\n')
  
  let currentKey: string | null = null
  let arrayMode = false
  let arrayItems: string[] = []
  
  for (const line of lines) {
    const trimmed = line.trim()
    
    // Skip comments and empty lines
    if (!trimmed || trimmed.startsWith('#')) continue
    
    // Handle array items
    if (arrayMode && trimmed.startsWith('-')) {
      const item = trimmed.slice(1).trim().replace(/['"]/g, '')
      arrayItems.push(item)
      continue
    }
    
    // End array mode when we hit a new key
    if (arrayMode && trimmed.includes(':')) {
      if (currentKey) {
        result[currentKey as keyof CustomCommandFrontmatter] = arrayItems as any
      }
      arrayMode = false
      arrayItems = []
      currentKey = null
    }
    
    // Parse key-value pairs
    const colonIndex = trimmed.indexOf(':')
    if (colonIndex === -1) continue
    
    const key = trimmed.slice(0, colonIndex).trim()
    const value = trimmed.slice(colonIndex + 1).trim()
    
    // Handle different value types
    if (value.startsWith('[') && value.endsWith(']')) {
      // Inline array
      result[key as keyof CustomCommandFrontmatter] = this.parseInlineArray(value) as any
    } else if (value === '' || value === '[]') {
      // Multi-line array start
      currentKey = key
      arrayMode = true
      arrayItems = []
    } else if (value === 'true' || value === 'false') {
      // Boolean
      result[key as keyof CustomCommandFrontmatter] = (value === 'true') as any
    } else {
      // String (remove quotes)
      result[key as keyof CustomCommandFrontmatter] = value.replace(/['"]/g, '') as any
    }
  }
  
  // Handle final array if we ended in array mode
  if (arrayMode && currentKey) {
    result[currentKey as keyof CustomCommandFrontmatter] = arrayItems as any
  }
  
  return result
}

private parseInlineArray(value: string): string[] {
  return value
    .slice(1, -1) // Remove brackets
    .split(',')
    .map(s => s.trim().replace(/['"]/g, ''))
    .filter(s => s.length > 0)
}
```

## Content Processing

### Dynamic Content Execution

```typescript
class DynamicContentProcessor {
  /**
   * Process bash command execution: !`command`
   */
  async executeBashCommands(content: string): Promise<string> {
    const BASH_REGEX = /!\`([^`]+)\`/g
    const matches = [...content.matchAll(BASH_REGEX)]
    
    if (matches.length === 0) return content
    
    let result = content
    
    for (const match of matches) {
      const fullMatch = match[0]
      const command = match[1].trim()
      
      try {
        const output = await this.executeBashCommand(command)
        result = result.replace(fullMatch, output)
      } catch (error) {
        console.warn(`Failed to execute: ${command}`, error)
        result = result.replace(fullMatch, `(error: ${error.message})`)
      }
    }
    
    return result
  }
  
  private async executeBashCommand(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
      exec(command, {
        cwd: process.cwd(),
        timeout: 5000,
        maxBuffer: 1024 * 1024 // 1MB
      }, (error, stdout, stderr) => {
        if (error) {
          reject(error)
        } else {
          resolve(stdout.trim() || stderr.trim() || '(no output)')
        }
      })
    })
  }
  
  /**
   * Process file references: @filepath
   */
  async resolveFileReferences(content: string): Promise<string> {
    const FILE_REGEX = /@([a-zA-Z0-9/._-]+(?:\.[a-zA-Z0-9]+)?)/g
    const matches = [...content.matchAll(FILE_REGEX)]
    
    if (matches.length === 0) return content
    
    let result = content
    
    for (const match of matches) {
      const fullMatch = match[0]
      const filePath = match[1]
      
      try {
        const fileContent = await this.readFileContent(filePath)
        const formatted = this.formatFileContent(filePath, fileContent)
        result = result.replace(fullMatch, formatted)
      } catch (error) {
        result = result.replace(fullMatch, `(file not found: ${filePath})`)
      }
    }
    
    return result
  }
  
  private async readFileContent(filePath: string): Promise<string> {
    const fullPath = path.resolve(process.cwd(), filePath)
    
    // Security check
    if (!fullPath.startsWith(process.cwd())) {
      throw new Error('Path traversal detected')
    }
    
    return fs.readFile(fullPath, 'utf-8')
  }
  
  private formatFileContent(filePath: string, content: string): string {
    const ext = path.extname(filePath).slice(1)
    const language = this.detectLanguage(ext)
    
    return `
## File: ${filePath}

\`\`\`${language}
${content}
\`\`\`
`
  }
}
```

### Argument Processing

```typescript
class ArgumentProcessor {
  /**
   * Process command arguments with multiple strategies
   */
  processArguments(
    content: string,
    args: string,
    argNames?: string[]
  ): string {
    let result = content
    
    // Strategy 1: Official $ARGUMENTS placeholder
    if (result.includes('$ARGUMENTS')) {
      result = result.replace(/\$ARGUMENTS/g, args || '')
    }
    
    // Strategy 2: Named placeholders {arg1}, {arg2}
    if (argNames && argNames.length > 0) {
      result = this.processNamedArguments(result, args, argNames)
    }
    
    // Strategy 3: Positional placeholders $1, $2, $3
    result = this.processPositionalArguments(result, args)
    
    // Strategy 4: Append if no placeholders used
    if (!this.hasPlaceholders(content) && args.trim()) {
      result += `\n\nAdditional context: ${args}`
    }
    
    return result
  }
  
  private processNamedArguments(
    content: string,
    args: string,
    argNames: string[]
  ): string {
    const argValues = this.parseArguments(args)
    let result = content
    
    argNames.forEach((name, index) => {
      const value = argValues[index] || ''
      const placeholder = new RegExp(`\\{${name}\\}`, 'g')
      result = result.replace(placeholder, value)
    })
    
    return result
  }
  
  private processPositionalArguments(
    content: string,
    args: string
  ): string {
    const argValues = this.parseArguments(args)
    let result = content
    
    argValues.forEach((value, index) => {
      const placeholder = new RegExp(`\\$${index + 1}`, 'g')
      result = result.replace(placeholder, value)
    })
    
    return result
  }
  
  private parseArguments(args: string): string[] {
    // Handle quoted arguments
    const regex = /[^\s"']+|"([^"]*)"|'([^']*)'/g
    const matches: string[] = []
    let match
    
    while ((match = regex.exec(args)) !== null) {
      matches.push(match[1] || match[2] || match[0])
    }
    
    return matches
  }
  
  private hasPlaceholders(content: string): boolean {
    return /\$ARGUMENTS|\$\d+|\{[^}]+\}/.test(content)
  }
}
```

## Command Creation

### Command Factory

```typescript
function createCustomCommand(
  frontmatter: CustomCommandFrontmatter,
  content: string,
  filePath: string,
  baseDir: string
): CustomCommandWithScope | null {
  // Generate command name
  const namespace = CommandNamespace.fromPath(filePath, baseDir)
  const scope = (baseDir.includes('.claude/commands') || baseDir.includes('.kode/commands')) ? 'project' : 'user'
  const finalName = frontmatter.name || 
                   CommandNamespace.addScope(namespace, scope)
  
  // Extract configuration
  const config = {
    description: frontmatter.description || `Custom command: ${finalName}`,
    enabled: frontmatter.enabled !== false,
    hidden: frontmatter.hidden === true,
    aliases: frontmatter.aliases || [],
    progressMessage: frontmatter.progressMessage || `Running ${finalName}...`,
    argNames: frontmatter.argNames,
    allowedTools: frontmatter['allowed-tools']
  }
  
  // Validate command
  if (!finalName) {
    console.warn(`No name for command in ${filePath}`)
    return null
  }
  
  // Create command object
  return {
    type: 'prompt' as const,
    name: finalName,
    ...config,
    scope,
    
    userFacingName(): string {
      return finalName
    },
    
    async getPromptForCommand(args: string): Promise<MessageParam[]> {
      let prompt = content.trim()
      
      // Process dynamic content
      const processor = new DynamicContentProcessor()
      prompt = await processor.executeBashCommands(prompt)
      prompt = await processor.resolveFileReferences(prompt)
      
      // Process arguments
      const argProcessor = new ArgumentProcessor()
      prompt = argProcessor.processArguments(prompt, args, config.argNames)
      
      // Add tool restrictions if specified
      if (config.allowedTools && config.allowedTools.length > 0) {
        prompt += `\n\nIMPORTANT: You are restricted to using only these tools: ${config.allowedTools.join(', ')}.`
      }
      
      return [{
        role: 'user',
        content: prompt
      }]
    }
  }
}
```

## Caching and Performance

### Memoized Loading

```typescript
export const loadCustomCommands = memoize(
  async (): Promise<CustomCommandWithScope[]> => {
    const startTime = Date.now()
    const discovery = new CommandDiscovery()
    
    try {
      // Discover command files
      const files = await discovery.discover()
      
      // Parse and create commands in parallel
      const commands = await Promise.all(
        files.map(async (file) => {
          try {
            const content = await fs.readFile(file.path, 'utf-8')
            const { frontmatter, content: body } = parseFrontmatter(content)
            
            return createCustomCommand(
              frontmatter,
              body,
              file.path,
              file.baseDir
            )
          } catch (error) {
            console.warn(`Failed to load ${file.path}:`, error)
            return null
          }
        })
      )
      
      // Filter out failed commands and disabled ones
      const validCommands = commands
        .filter((cmd): cmd is CustomCommandWithScope => 
          cmd !== null && cmd.isEnabled
        )
      
      // Log metrics
      const duration = Date.now() - startTime
      logEvent('custom_commands_loaded', {
        total: files.length,
        valid: validCommands.length,
        duration
      })
      
      return validCommands
      
    } catch (error) {
      console.error('Failed to load custom commands:', error)
      return []
    }
  },
  // Cache key resolver
  () => {
    const dirs = getCustomCommandDirectories()
    const cacheKey = [
      process.cwd(),
      existsSync(dirs.user),
      existsSync(dirs.project),
      Math.floor(Date.now() / 60000) // 1-minute cache
    ].join(':')
    
    return cacheKey
  }
)
```

### Cache Invalidation

```typescript
export function reloadCustomCommands(): void {
  loadCustomCommands.cache.clear()
  console.log('Custom commands cache cleared')
}

// Watch for changes (optional)
class CommandWatcher {
  private watchers: FSWatcher[] = []
  
  watch(onChange: () => void): void {
    const dirs = getCustomCommandDirectories()
    
    for (const dir of Object.values(dirs)) {
      if (existsSync(dir)) {
        const watcher = watch(dir, { recursive: true }, (event, filename) => {
          if (filename?.endsWith('.md')) {
            console.log(`Command file changed: ${filename}`)
            reloadCustomCommands()
            onChange()
          }
        })
        
        this.watchers.push(watcher)
      }
    }
  }
  
  stop(): void {
    for (const watcher of this.watchers) {
      watcher.close()
    }
    this.watchers = []
  }
}
```

## Examples

### Basic Command

```markdown
---
name: explain
description: Explain code or concept in detail
aliases: [exp, describe]
---

Please provide a detailed explanation of $ARGUMENTS.

Include:
- Overview and purpose
- How it works
- Key concepts
- Examples if applicable
- Common use cases
```

### Command with File Reference

```markdown
---
name: review-pr
description: Review pull request changes
progressMessage: Analyzing PR changes...
---

Review the following pull request changes:

!`git diff main...HEAD`

@.github/pull_request_template.md

Please analyze:
1. Code quality and style
2. Potential bugs or issues
3. Performance implications
4. Security considerations
5. Test coverage

Provide constructive feedback and suggestions.
```

### Command with Arguments

```markdown
---
name: scaffold
description: Generate project scaffold
argNames: [type, name, features]
---

Create a new {type} project named "{name}" with the following features: {features}

Structure:
!`ls -la`

Requirements:
- Follow best practices for {type} projects
- Include necessary configuration files
- Set up development environment
- Add basic tests
- Create comprehensive README

Current directory context:
@package.json
```

### Command with Tool Restrictions

```markdown
---
name: analyze-only
description: Analyze without making changes
allowed-tools: [file_read, grep, glob]
hidden: false
---

Analyze the codebase to understand $ARGUMENTS.

You may only read files and search for patterns.
Do not make any modifications or execute commands.

Focus on:
- Understanding the implementation
- Identifying patterns
- Documenting findings
```

## Integration with Main System

### Command Registration

```typescript
export async function getCommands(): Promise<Command[]> {
  const [builtIn, mcp, custom] = await Promise.all([
    getBuiltInCommands(),
    getMCPCommands(),
    loadCustomCommands()
  ])
  
  // Merge all commands
  const allCommands = [...builtIn, ...mcp, ...custom]
  
  // Handle conflicts (custom commands override built-in)
  const commandMap = new Map<string, Command>()
  
  for (const cmd of allCommands) {
    const name = cmd.userFacingName()
    
    if (!commandMap.has(name)) {
      commandMap.set(name, cmd)
    } else if (cmd.scope === 'project') {
      // Project commands override others
      commandMap.set(name, cmd)
    }
  }
  
  return Array.from(commandMap.values())
}
```

### Help System Integration

```typescript
class HelpFormatter {
  formatCustomCommands(commands: CustomCommandWithScope[]): string {
    const grouped = this.groupByScope(commands)
    
    let output = ''
    
    if (grouped.project.length > 0) {
      output += '\n📁 Project Commands:\n'
      output += this.formatCommandList(grouped.project)
    }
    
    if (grouped.user.length > 0) {
      output += '\n👤 User Commands:\n'
      output += this.formatCommandList(grouped.user)
    }
    
    return output
  }
  
  private groupByScope(
    commands: CustomCommandWithScope[]
  ): Record<string, CustomCommandWithScope[]> {
    return commands.reduce((acc, cmd) => {
      const scope = cmd.scope || 'user'
      if (!acc[scope]) acc[scope] = []
      acc[scope].push(cmd)
      return acc
    }, {} as Record<string, CustomCommandWithScope[]>)
  }
  
  private formatCommandList(commands: CustomCommandWithScope[]): string {
    return commands
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(cmd => {
        const aliases = cmd.aliases?.length 
          ? ` (${cmd.aliases.join(', ')})` 
          : ''
        return `  /${cmd.name}${aliases} - ${cmd.description}`
      })
      .join('\n')
  }
}
```

The Custom Commands System provides a powerful, flexible way to extend Kode with user-defined commands while maintaining security, performance, and integration with the core system.