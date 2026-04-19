# 配置系统

## 概述

Kode 使用复杂的多级配置系统，允许在全局、项目和运行时级别进行自定义。配置从全局默认值通过项目特定设置级联到运行时覆盖。

## 配置层次结构

```
环境变量（最高优先级）
           ↓
    运行时标志 (CLI)
           ↓
  项目配置 (./.claude/config.json)
           ↓
   全局配置 (~/.claude/config.json)
           ↓
      默认值（最低优先级）
```

## 配置文件

### 全局配置
**位置**：`~/.claude/config.json`

```json
{
  "theme": "dark",
  "hasCompletedOnboarding": true,
  "modelProfiles": {
    "default": {
      "type": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "maxTokens": 8192
    }
  },
  "modelPointers": {
    "main": "default",
    "task": "fast",
    "reasoning": "smart",
    "quick": "quick"
  },
  "mcpServers": {},
  "customApiKey": null,
  "autoUpdaterStatus": "enabled",
  "numStartups": 42
}
```

### 项目配置
**位置**：`./.claude/config.json`

```json
{
  "enableArchitectTool": false,
  "allowedCommands": [
    "git *",
    "npm *",
    "bun *"
  ],
  "approvedTools": [
    "file_read",
    "file_edit",
    "bash"
  ],
  "context": {
    "projectName": "my-project",
    "description": "项目描述"
  },
  "mcpServers": {},
  "lastCost": 0.0234,
  "lastDuration": 45000
}
```

## 配置模式

### 模型配置

#### 模型配置文件
定义可重用的 AI 模型配置：

```typescript
interface ModelProfile {
  id: string
  name: string
  provider: 'anthropic' | 'openai' | 'custom'
  config: {
    model: string
    baseURL?: string
    apiKey?: string
    maxTokens?: number
    temperature?: number
    headers?: Record<string, string>
  }
}
```

#### 模型指针
将角色映射到模型配置文件：

```typescript
interface ModelPointers {
  main: string      // 主要对话模型
  task: string      // 任务执行模型
  reasoning: string // 复杂推理模型
  quick: string     // 快速响应模型
}
```

### MCP 服务器配置

```typescript
interface MCPServerConfig {
  type: 'stdio' | 'sse'
  // 对于 stdio 服务器
  command?: string
  args?: string[]
  env?: Record<string, string>
  // 对于 SSE 服务器
  url?: string
}

interface MCPServers {
  [serverName: string]: MCPServerConfig
}
```

### 权限配置

```typescript
interface PermissionConfig {
  // 批准的 shell 命令模式
  allowedCommands: string[]
  
  // 批准的工具名称
  approvedTools: string[]
  
  // 文件/目录访问模式
  allowedPaths: string[]
  
  // 拒绝的 MCP 服务器
  rejectedMcprcServers: string[]
  
  // 批准的 MCP 服务器
  approvedMcprcServers: string[]
}
```

### UI 配置

```typescript
interface UIConfig {
  theme: 'dark' | 'light'
  compactMode: boolean
  showCosts: boolean
  syntaxHighlighting: boolean
  vimKeybindings: boolean
  shiftEnterKeyBindingInstalled: boolean
}
```

## 配置管理 API

### 读取配置

```typescript
import { getGlobalConfig, getCurrentProjectConfig } from './utils/config'

// 获取全局配置
const globalConfig = getGlobalConfig()

// 获取项目配置
const projectConfig = getCurrentProjectConfig()

// 获取合并配置（项目覆盖全局）
const config = {
  ...globalConfig,
  ...projectConfig
}
```

### 写入配置

```typescript
import { saveGlobalConfig, saveCurrentProjectConfig } from './utils/config'

// 更新全局配置
saveGlobalConfig({
  ...getGlobalConfig(),
  theme: 'light'
})

// 更新项目配置
saveCurrentProjectConfig({
  ...getCurrentProjectConfig(),
  enableArchitectTool: true
})
```

### CLI 配置命令

```bash
# 获取配置值
kode config get theme
kode config get -g modelProfiles.default.model

# 设置配置值
kode config set theme dark
kode config set -g autoUpdaterStatus enabled

# 删除配置值
kode config remove customApiKey
kode config remove -g mcpServers.myserver

# 列出所有配置
kode config list
kode config list -g
```

## 环境变量

### 核心变量

> 注意：Anthropic 的环境变量覆盖已禁用，请在 Kode 设置或模型配置中填写密钥。

```bash
# API 密钥
OPENAI_API_KEY=sk-...

# 模型选择
CLAUDE_MODEL=claude-3-5-sonnet-20241022
DEFAULT_MODEL_PROFILE=fast

# 功能标志
ENABLE_ARCHITECT_TOOL=true
DEBUG_MODE=true
VERBOSE=true

# MCP 配置
MCP_SERVER_URL=http://localhost:3000
MCP_TIMEOUT=30000

# 开发
NODE_ENV=development
LOG_LEVEL=debug
```

### 优先级规则

环境变量覆盖配置文件（Anthropic 密钥除外）：
1. 检查环境变量
2. 检查项目配置
3. 检查全局配置
4. 使用默认值

## 配置迁移

### 版本迁移

系统自动迁移旧配置格式：

```typescript
function migrateConfig(config: any): Config {
  // v1 到 v2：重命名字段
  if (config.iterm2KeyBindingInstalled) {
    config.shiftEnterKeyBindingInstalled = config.iterm2KeyBindingInstalled
    delete config.iterm2KeyBindingInstalled
  }
  
  // v2 到 v3：更新模型格式
  if (typeof config.model === 'string') {
    config.modelProfiles = {
      default: {
        type: 'anthropic',
        model: config.model
      }
    }
    delete config.model
  }
  
  return config
}
```

### 备份和恢复

配置文件在更改前备份：

```typescript
function saveConfigWithBackup(config: Config) {
  // 创建备份
  const backupPath = `${configPath}.backup`
  fs.copyFileSync(configPath, backupPath)
  
  try {
    // 保存新配置
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2))
  } catch (error) {
    // 错误时从备份恢复
    fs.copyFileSync(backupPath, configPath)
    throw error
  }
}
```

## 配置验证

### 模式验证

使用 Zod 进行运行时验证：

```typescript
const ConfigSchema = z.object({
  theme: z.enum(['dark', 'light']).optional(),
  modelProfiles: z.record(ModelProfileSchema).optional(),
  modelPointers: ModelPointersSchema.optional(),
  mcpServers: z.record(MCPServerConfigSchema).optional(),
  // ... 其他字段
})

function loadConfig(path: string): Config {
  const raw = JSON.parse(fs.readFileSync(path, 'utf-8'))
  return ConfigSchema.parse(raw)
}
```

### 验证规则

1. **API 密钥**：必须匹配预期格式
2. **模型名称**：必须是有效的模型标识符
3. **URL**：必须是端点的有效 URL
4. **路径**：必须是有效的文件系统路径
5. **命令**：不得包含危险模式

## 配置范围

### 全局范围
影响所有项目：
- 用户偏好（主题、键绑定）
- 模型配置文件和 API 密钥
- 全局 MCP 服务器
- 自动更新程序设置

### 项目范围
特定于当前项目：
- 工具权限
- 允许的命令
- 项目上下文
- 本地 MCP 服务器
- 成本跟踪

### 会话范围
当前会话的临时：
- 运行时标志
- 临时权限
- 活动 MCP 连接
- 当前模型选择

## 高级配置

### 自定义模型提供商

```json
{
  "modelProfiles": {
    "custom-llm": {
      "type": "custom",
      "name": "我的自定义 LLM",
      "config": {
        "baseURL": "https://my-llm-api.com",
        "apiKey": "custom-key",
        "model": "my-model-v1",
        "headers": {
          "X-Custom-Header": "value"
        }
      }
    }
  }
}
```

### MCP 服务器示例

```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_DIRECTORIES": "/home/user/projects"
      }
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "web-api": {
      "type": "sse",
      "url": "https://api.example.com/mcp"
    }
  }
}
```

### 上下文配置

```json
{
  "context": {
    "projectType": "typescript",
    "framework": "react",
    "testingFramework": "jest",
    "buildTool": "webpack",
    "customContext": "该项目使用自定义状态管理解决方案..."
  }
}
```

## 配置最佳实践

### 1. 安全性
- 永远不要将 API 密钥提交到版本控制
- 使用环境变量存储机密
- 验证所有配置输入
- 适当限制命令权限

### 2. 组织
- 为用户偏好保留全局配置
- 为项目特定设置使用项目配置
- 在 README 中记录自定义配置
- 版本控制项目配置

### 3. 性能
- 在内存中缓存配置
- 仅在文件更改时重新加载
- 使用高效的 JSON 解析
- 最小化配置文件大小

### 4. 调试
- 为配置问题使用详细模式
- 使用 `config list` 检查配置
- 加载时验证配置
- 清楚地记录配置错误

## 故障排除

### 常见问题

1. **配置未加载**
   - 检查文件权限
   - 验证 JSON 语法
   - 确保正确的文件路径

2. **设置未应用**
   - 检查配置层次结构
   - 验证环境变量
   - 清除配置缓存

3. **迁移失败**
   - 从备份恢复
   - 手动更新格式
   - 检查迁移日志

### 调试命令

```bash
# 显示配置
kode config list

# 重置为默认值
kode config reset

# 显示配置路径
kode config paths
```

配置系统提供灵活、安全和强大的所有 Kode 设置管理，同时保持向后兼容性和用户友好的默认值。
