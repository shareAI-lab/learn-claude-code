# 自定义命令系统

## 概述

自定义命令系统（`src/services/customCommands.ts`）使用户能够创建可重用的基于 Markdown 的命令来扩展 Kode 的功能。命令从 `.claude/commands/` 和 `.kode/commands/` 目录中发现并与内置命令系统无缝集成。

## 架构

### 系统设计

```typescript
interface CustomCommandSystem {
  // 发现
  loadCustomCommands(): Promise<CustomCommandWithScope[]>
  scanMarkdownFiles(directory: string): Promise<string[]>
  
  // 解析
  parseFrontmatter(content: string): ParsedCommand
  createCustomCommand(parsed: ParsedCommand): Command
  
  // 处理
  executeBashCommands(content: string): Promise<string>
  resolveFileReferences(content: string): Promise<string>
  
  // 管理
  reloadCustomCommands(): void
  getCustomCommandDirectories(): CommandDirectories
}
```

## 命令结构

### 文件格式

```markdown
---
name: command-name
description: 命令的简要描述
aliases: [alias1, alias2]
enabled: true
hidden: false
progressMessage: 运行命令中...
argNames: [arg1, arg2]
allowed-tools: [file_read, file_edit]
---

# 命令内容

您的命令提示在这里。您可以使用：
- 参数：{arg1}、{arg2}
- 官方格式：$ARGUMENTS
- 文件引用：@src/file.js
- Bash 执行：!`git status`
```

### Frontmatter 模式

```typescript
export interface CustomCommandFrontmatter {
  // 核心属性
  name?: string              // 命令名称（默认为文件名）
  description?: string       // 简要描述
  aliases?: string[]        // 替代名称
  
  // 行为控制
  enabled?: boolean         // 命令是否激活（默认：true）
  hidden?: boolean          // 从帮助输出中隐藏（默认：false）
  
  // 执行
  progressMessage?: string  // 执行期间显示的消息
  argNames?: string[]       // 命名参数占位符
  'allowed-tools'?: string[] // 工具限制
  
  // 元数据（未来扩展）
  version?: string
  author?: string
  tags?: string[]
  requires?: string[]       // 依赖项
}
```

## 发现系统

### 目录扫描

```typescript
class CommandDiscovery {
  private readonly COMMAND_DIRS = {
    user: path.join(homedir(), '.claude', 'commands'),
    project: path.join(process.cwd(), '.claude', 'commands')
  }
  
  async discover(): Promise<CommandFile[]> {
    const files: CommandFile[] = []
    
    // 扫描用户命令（较低优先级）
    if (existsSync(this.COMMAND_DIRS.user)) {
      const userFiles = await this.scanDirectory(this.COMMAND_DIRS.user)
      files.push(...userFiles.map(f => ({ ...f, scope: 'user' })))
    }
    
    // 扫描项目命令（较高优先级）
    if (existsSync(this.COMMAND_DIRS.project)) {
      const projectFiles = await this.scanDirectory(this.COMMAND_DIRS.project)
      files.push(...projectFiles.map(f => ({ ...f, scope: 'project' })))
    }
    
    return files
  }
  
  private async scanDirectory(dir: string): Promise<string[]> {
    const files: string[] = []
    
    async function scan(currentDir: string, depth = 0) {
      if (depth > 5) return // 防止深度递归
      
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

### 命名空间支持

```typescript
class CommandNamespace {
  /**
   * 从文件路径生成命名空间命令名称
   * 
   * 示例：
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
    
    // 从目录结构创建命名空间
    const namespace = parts.slice(0, -1).join(':')
    return `${namespace}:${fileName}`
  }
  
  /**
   * 为命令名称添加范围前缀
   * 
   * 示例：
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

## 解析系统

### Frontmatter 解析器

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
    
    // 跳过注释和空行
    if (!trimmed || trimmed.startsWith('#')) continue
    
    // 处理数组项
    if (arrayMode && trimmed.startsWith('-')) {
      const item = trimmed.slice(1).trim().replace(/['"]/g, '')
      arrayItems.push(item)
      continue
    }
    
    // 当遇到新键时结束数组模式
    if (arrayMode && trimmed.includes(':')) {
      if (currentKey) {
        result[currentKey as keyof CustomCommandFrontmatter] = arrayItems as any
      }
      arrayMode = false
      arrayItems = []
      currentKey = null
    }
    
    // 解析键值对
    const colonIndex = trimmed.indexOf(':')
    if (colonIndex === -1) continue
    
    const key = trimmed.slice(0, colonIndex).trim()
    const value = trimmed.slice(colonIndex + 1).trim()
    
    // 处理不同的值类型
    if (value.startsWith('[') && value.endsWith(']')) {
      // 内联数组
      result[key as keyof CustomCommandFrontmatter] = this.parseInlineArray(value) as any
    } else if (value === '' || value === '[]') {
      // 多行数组开始
      currentKey = key
      arrayMode = true
      arrayItems = []
    } else if (value === 'true' || value === 'false') {
      // 布尔值
      result[key as keyof CustomCommandFrontmatter] = (value === 'true') as any
    } else {
      // 字符串（删除引号）
      result[key as keyof CustomCommandFrontmatter] = value.replace(/['"]/g, '') as any
    }
  }
  
  // 处理最终数组（如果以数组模式结束）
  if (arrayMode && currentKey) {
    result[currentKey as keyof CustomCommandFrontmatter] = arrayItems as any
  }
  
  return result
}
```

## 内容处理

### 动态内容执行

```typescript
class DynamicContentProcessor {
  /**
   * 处理 bash 命令执行：!`command`
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
        console.warn(`执行失败：${command}`, error)
        result = result.replace(fullMatch, `(错误：${error.message})`)
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
          resolve(stdout.trim() || stderr.trim() || '(无输出)')
        }
      })
    })
  }
  
  /**
   * 处理文件引用：@filepath
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
        result = result.replace(fullMatch, `(文件未找到：${filePath})`)
      }
    }
    
    return result
  }
  
  private async readFileContent(filePath: string): Promise<string> {
    const fullPath = path.resolve(process.cwd(), filePath)
    
    // 安全检查
    if (!fullPath.startsWith(process.cwd())) {
      throw new Error('检测到路径遍历')
    }
    
    return fs.readFile(fullPath, 'utf-8')
  }
  
  private formatFileContent(filePath: string, content: string): string {
    const ext = path.extname(filePath).slice(1)
    const language = this.detectLanguage(ext)
    
    return `
## 文件：${filePath}

\`\`\`${language}
${content}
\`\`\`
`
  }
}
```

### 参数处理

```typescript
class ArgumentProcessor {
  /**
   * 使用多种策略处理命令参数
   */
  processArguments(
    content: string,
    args: string,
    argNames?: string[]
  ): string {
    let result = content
    
    // 策略 1：官方 $ARGUMENTS 占位符
    if (result.includes('$ARGUMENTS')) {
      result = result.replace(/\$ARGUMENTS/g, args || '')
    }
    
    // 策略 2：命名占位符 {arg1}、{arg2}
    if (argNames && argNames.length > 0) {
      result = this.processNamedArguments(result, args, argNames)
    }
    
    // 策略 3：位置占位符 $1、$2、$3
    result = this.processPositionalArguments(result, args)
    
    // 策略 4：如果没有使用占位符则追加
    if (!this.hasPlaceholders(content) && args.trim()) {
      result += `\n\n附加上下文：${args}`
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
  
  private parseArguments(args: string): string[] {
    // 处理带引号的参数
    const regex = /[^\s"']+|"([^"]*)"|'([^']*)'/g
    const matches: string[] = []
    let match
    
    while ((match = regex.exec(args)) !== null) {
      matches.push(match[1] || match[2] || match[0])
    }
    
    return matches
  }
}
```

## 命令创建

### 命令工厂

```typescript
function createCustomCommand(
  frontmatter: CustomCommandFrontmatter,
  content: string,
  filePath: string,
  baseDir: string
): CustomCommandWithScope | null {
  // 生成命令名称
  const namespace = CommandNamespace.fromPath(filePath, baseDir)
  const scope = (baseDir.includes('.claude/commands') || baseDir.includes('.kode/commands')) ? 'project' : 'user'
  const finalName = frontmatter.name || 
                   CommandNamespace.addScope(namespace, scope)
  
  // 提取配置
  const config = {
    description: frontmatter.description || `自定义命令：${finalName}`,
    enabled: frontmatter.enabled !== false,
    hidden: frontmatter.hidden === true,
    aliases: frontmatter.aliases || [],
    progressMessage: frontmatter.progressMessage || `运行 ${finalName}...`,
    argNames: frontmatter.argNames,
    allowedTools: frontmatter['allowed-tools']
  }
  
  // 验证命令
  if (!finalName) {
    console.warn(`${filePath} 中的命令没有名称`)
    return null
  }
  
  // 创建命令对象
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
      
      // 处理动态内容
      const processor = new DynamicContentProcessor()
      prompt = await processor.executeBashCommands(prompt)
      prompt = await processor.resolveFileReferences(prompt)
      
      // 处理参数
      const argProcessor = new ArgumentProcessor()
      prompt = argProcessor.processArguments(prompt, args, config.argNames)
      
      // 添加工具限制（如果指定）
      if (config.allowedTools && config.allowedTools.length > 0) {
        prompt += `\n\n重要：您仅限于使用这些工具：${config.allowedTools.join('、')}。`
      }
      
      return [{
        role: 'user',
        content: prompt
      }]
    }
  }
}
```

## 示例

### 基本命令

```markdown
---
name: explain
description: 详细解释代码或概念
aliases: [exp, describe]
---

请详细解释 $ARGUMENTS。

包括：
- 概述和目的
- 工作原理
- 关键概念
- 适用示例
- 常见用例
```

### 带文件引用的命令

```markdown
---
name: review-pr
description: 审查拉取请求更改
progressMessage: 分析 PR 更改...
---

审查以下拉取请求更改：

!`git diff main...HEAD`

@.github/pull_request_template.md

请分析：
1. 代码质量和风格
2. 潜在的错误或问题
3. 性能影响
4. 安全考虑
5. 测试覆盖率

提供建设性的反馈和建议。
```

### 带参数的命令

```markdown
---
name: scaffold
description: 生成项目脚手架
argNames: [type, name, features]
---

创建一个名为"{name}"的新 {type} 项目，具有以下功能：{features}

结构：
!`ls -la`

要求：
- 遵循 {type} 项目的最佳实践
- 包括必要的配置文件
- 设置开发环境
- 添加基本测试
- 创建全面的 README

当前目录上下文：
@package.json
```

### 带工具限制的命令

```markdown
---
name: analyze-only
description: 分析而不进行更改
allowed-tools: [file_read, grep, glob]
hidden: false
---

分析代码库以理解 $ARGUMENTS。

您只能读取文件和搜索模式。
不要进行任何修改或执行命令。

专注于：
- 理解实现
- 识别模式
- 记录发现
```

## 与主系统的集成

### 命令注册

```typescript
export async function getCommands(): Promise<Command[]> {
  const [builtIn, mcp, custom] = await Promise.all([
    getBuiltInCommands(),
    getMCPCommands(),
    loadCustomCommands()
  ])
  
  // 合并所有命令
  const allCommands = [...builtIn, ...mcp, ...custom]
  
  // 处理冲突（自定义命令覆盖内置）
  const commandMap = new Map<string, Command>()
  
  for (const cmd of allCommands) {
    const name = cmd.userFacingName()
    
    if (!commandMap.has(name)) {
      commandMap.set(name, cmd)
    } else if (cmd.scope === 'project') {
      // 项目命令覆盖其他
      commandMap.set(name, cmd)
    }
  }
  
  return Array.from(commandMap.values())
}
```

自定义命令系统提供了一种强大、灵活的方式来使用用户定义的命令扩展 Kode，同时保持与核心系统的安全性、性能和集成。