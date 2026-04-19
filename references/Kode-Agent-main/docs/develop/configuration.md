# Configuration System

## Overview

Kode uses a sophisticated multi-level configuration system that allows customization at global, project, and runtime levels. Configuration cascades from global defaults through project-specific settings to runtime overrides.

## Configuration Hierarchy

```
Environment Variables (Highest Priority)
           ↓
    Runtime Flags (CLI)
           ↓
  Project Configuration (./.claude/config.json)
           ↓
   Global Configuration (~/.claude/config.json)
           ↓
      Default Values (Lowest Priority)
```

## Configuration Files

### Global Configuration
**Location**: `~/.claude/config.json`

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

### Project Configuration
**Location**: `./.claude/config.json`

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
    "description": "Project description"
  },
  "mcpServers": {},
  "lastCost": 0.0234,
  "lastDuration": 45000
}
```

## Configuration Schema

### Model Configuration

#### Model Profiles
Define reusable AI model configurations:

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

#### Model Pointers
Map roles to model profiles:

```typescript
interface ModelPointers {
  main: string      // Primary conversation model
  task: string      // Task execution model
  reasoning: string // Complex reasoning model
  quick: string     // Fast responses model
}
```

### MCP Server Configuration

```typescript
interface MCPServerConfig {
  type: 'stdio' | 'sse'
  // For stdio servers
  command?: string
  args?: string[]
  env?: Record<string, string>
  // For SSE servers
  url?: string
}

interface MCPServers {
  [serverName: string]: MCPServerConfig
}
```

### Permission Configuration

```typescript
interface PermissionConfig {
  // Approved shell command patterns
  allowedCommands: string[]
  
  // Approved tool names
  approvedTools: string[]
  
  // File/directory access patterns
  allowedPaths: string[]
  
  // Rejected MCP servers
  rejectedMcprcServers: string[]
  
  // Approved MCP servers
  approvedMcprcServers: string[]
}
```

### UI Configuration

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

## Configuration Management API

### Reading Configuration

```typescript
import { getGlobalConfig, getCurrentProjectConfig } from './utils/config'

// Get global configuration
const globalConfig = getGlobalConfig()

// Get project configuration
const projectConfig = getCurrentProjectConfig()

// Get merged configuration (project overrides global)
const config = {
  ...globalConfig,
  ...projectConfig
}
```

### Writing Configuration

```typescript
import { saveGlobalConfig, saveCurrentProjectConfig } from './utils/config'

// Update global configuration
saveGlobalConfig({
  ...getGlobalConfig(),
  theme: 'light'
})

// Update project configuration
saveCurrentProjectConfig({
  ...getCurrentProjectConfig(),
  enableArchitectTool: true
})
```

### CLI Configuration Commands

```bash
# Get configuration value
kode config get theme
kode config get -g modelProfiles.default.model

# Set configuration value
kode config set theme dark
kode config set -g autoUpdaterStatus enabled

# Remove configuration value
kode config remove customApiKey
kode config remove -g mcpServers.myserver

# List all configuration
kode config list
kode config list -g
```

## Environment Variables

### Core Variables

> Anthropic environment overrides are disabled—configure Anthropic keys in Kode settings instead.

```bash
# API Keys
OPENAI_API_KEY=sk-...

# Model Selection
CLAUDE_MODEL=claude-3-5-sonnet-20241022
DEFAULT_MODEL_PROFILE=fast

# Feature Flags
ENABLE_ARCHITECT_TOOL=true
DEBUG_MODE=true
VERBOSE=true

# MCP Configuration
MCP_SERVER_URL=http://localhost:3000
MCP_TIMEOUT=30000

# Development
NODE_ENV=development
LOG_LEVEL=debug
```

### Precedence Rules

Environment variables override configuration files (Anthropic keys excluded):
1. Check environment variable
2. Check project configuration
3. Check global configuration
4. Use default value

## Configuration Migration

### Version Migration

The system automatically migrates old configuration formats:

```typescript
function migrateConfig(config: any): Config {
  // v1 to v2: Rename fields
  if (config.iterm2KeyBindingInstalled) {
    config.shiftEnterKeyBindingInstalled = config.iterm2KeyBindingInstalled
    delete config.iterm2KeyBindingInstalled
  }
  
  // v2 to v3: Update model format
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

### Backup and Recovery

Configuration files are backed up before changes:

```typescript
function saveConfigWithBackup(config: Config) {
  // Create backup
  const backupPath = `${configPath}.backup`
  fs.copyFileSync(configPath, backupPath)
  
  try {
    // Save new configuration
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2))
  } catch (error) {
    // Restore from backup on error
    fs.copyFileSync(backupPath, configPath)
    throw error
  }
}
```

## Configuration Validation

### Schema Validation

Using Zod for runtime validation:

```typescript
const ConfigSchema = z.object({
  theme: z.enum(['dark', 'light']).optional(),
  modelProfiles: z.record(ModelProfileSchema).optional(),
  modelPointers: ModelPointersSchema.optional(),
  mcpServers: z.record(MCPServerConfigSchema).optional(),
  // ... other fields
})

function loadConfig(path: string): Config {
  const raw = JSON.parse(fs.readFileSync(path, 'utf-8'))
  return ConfigSchema.parse(raw)
}
```

### Validation Rules

1. **API Keys**: Must match expected format
2. **Model Names**: Must be valid model identifiers
3. **URLs**: Must be valid URLs for endpoints
4. **Paths**: Must be valid file system paths
5. **Commands**: Must not contain dangerous patterns

## Configuration Scopes

### Global Scope
Affects all projects:
- User preferences (theme, keybindings)
- Model profiles and API keys
- Global MCP servers
- Auto-updater settings

### Project Scope
Specific to current project:
- Tool permissions
- Allowed commands
- Project context
- Local MCP servers
- Cost tracking

### Session Scope
Temporary for current session:
- Runtime flags
- Temporary permissions
- Active MCP connections
- Current model selection

## Advanced Configuration

### Custom Model Providers

```json
{
  "modelProfiles": {
    "custom-llm": {
      "type": "custom",
      "name": "My Custom LLM",
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

### MCP Server Examples

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

### Context Configuration

```json
{
  "context": {
    "projectType": "typescript",
    "framework": "react",
    "testingFramework": "jest",
    "buildTool": "webpack",
    "customContext": "This project uses a custom state management solution..."
  }
}
```

## Configuration Best Practices

### 1. Security
- Never commit API keys to version control
- Use environment variables for secrets
- Validate all configuration inputs
- Limit command permissions appropriately

### 2. Organization
- Keep global config for user preferences
- Use project config for project-specific settings
- Document custom configuration in README
- Version control project configuration

### 3. Performance
- Cache configuration in memory
- Reload only when files change
- Use efficient JSON parsing
- Minimize configuration file size

### 4. Debugging
- Use verbose mode for configuration issues
- Check configuration with `config list`
- Validate configuration on load
- Log configuration errors clearly

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**
   - Check file permissions
   - Validate JSON syntax
   - Ensure correct file path

2. **Settings Not Applied**
   - Check configuration hierarchy
   - Verify environment variables
   - Clear configuration cache

3. **Migration Failures**
   - Restore from backup
   - Manually update format
   - Check migration logs

### Debug Commands

```bash
# Show configuration
kode config list

# Reset to defaults
kode config reset

# Show configuration paths
kode config paths
```

The configuration system provides flexible, secure, and robust management of all Kode settings while maintaining backward compatibility and user-friendly defaults.
