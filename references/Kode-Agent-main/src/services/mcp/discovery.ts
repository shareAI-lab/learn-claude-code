import {
  getCurrentProjectConfig,
  getGlobalConfig,
  getProjectMcpServerDefinitions,
  saveCurrentProjectConfig,
  saveGlobalConfig,
  addMcprcServerForTesting,
  removeMcprcServerForTesting,
  type McpServerConfig,
} from '@utils/config'
import { existsSync, readFileSync, writeFileSync } from 'fs'
import { join } from 'path'
import { getCwd } from '@utils/state'
import { safeParseJSON } from '@utils/text/json'
import { getSessionPlugins } from '@utils/session/sessionPlugins'
import { parseJsonOrJsonc } from './internal/jsonc'

type McpName = string

function expandTemplateString(value: string, pluginRoot: string): string {
  return value.replace(/\$\{([^}]+)\}/g, (match, key) => {
    const k = String(key ?? '').trim()
    if (!k) return match
    if (k === 'CLAUDE_PLUGIN_ROOT') return pluginRoot
    const env = process.env[k]
    return env !== undefined ? env : match
  })
}

function expandTemplateDeep(value: unknown, pluginRoot: string): unknown {
  if (typeof value === 'string') return expandTemplateString(value, pluginRoot)
  if (Array.isArray(value))
    return value.map(v => expandTemplateDeep(v, pluginRoot))
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value)) {
      out[k] = expandTemplateDeep(v, pluginRoot)
    }
    return out
  }
  return value
}

export function listPluginMCPServers(): Record<string, McpServerConfig> {
  const plugins = getSessionPlugins()
  if (plugins.length === 0) return {}

  const out: Record<string, McpServerConfig> = {}

  for (const plugin of plugins) {
    const pluginRoot = plugin.rootDir
    const pluginName = plugin.name

    const configs: Array<Record<string, McpServerConfig>> = []

    for (const configPath of plugin.mcpConfigFiles ?? []) {
      try {
        const raw = readFileSync(configPath, 'utf8')
        const parsed = parseJsonOrJsonc(raw)
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
          continue
        const rawServers =
          (parsed as any).mcpServers &&
          typeof (parsed as any).mcpServers === 'object' &&
          !Array.isArray((parsed as any).mcpServers)
            ? (parsed as any).mcpServers
            : parsed

        if (
          !rawServers ||
          typeof rawServers !== 'object' ||
          Array.isArray(rawServers)
        )
          continue

        const servers: Record<string, McpServerConfig> = {}
        for (const [name, cfg] of Object.entries(rawServers as any)) {
          if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) continue
          servers[name] = expandTemplateDeep(cfg, pluginRoot) as McpServerConfig
        }
        configs.push(servers)
      } catch {
        continue
      }
    }

    const manifestRaw = (plugin.manifest as any)?.mcpServers
    if (
      manifestRaw &&
      typeof manifestRaw === 'object' &&
      !Array.isArray(manifestRaw)
    ) {
      const rawServers =
        (manifestRaw as any).mcpServers &&
        typeof (manifestRaw as any).mcpServers === 'object' &&
        !Array.isArray((manifestRaw as any).mcpServers)
          ? (manifestRaw as any).mcpServers
          : manifestRaw

      if (
        rawServers &&
        typeof rawServers === 'object' &&
        !Array.isArray(rawServers)
      ) {
        const servers: Record<string, McpServerConfig> = {}
        for (const [name, cfg] of Object.entries(rawServers as any)) {
          if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) continue
          servers[name] = expandTemplateDeep(cfg, pluginRoot) as McpServerConfig
        }
        configs.push(servers)
      }
    }

    const merged: Record<string, McpServerConfig> = Object.assign({}, ...configs)

    for (const [serverName, cfg] of Object.entries(merged)) {
      const fullName = `plugin_${pluginName}_${serverName}`
      out[fullName] = cfg
    }
  }

  return out
}

export function parseEnvVars(
  rawEnvArgs: string[] | undefined,
): Record<string, string> {
  const parsedEnv: Record<string, string> = {}

  if (rawEnvArgs) {
    for (const envStr of rawEnvArgs) {
      const [key, ...valueParts] = envStr.split('=')
      if (!key || valueParts.length === 0) {
        throw new Error(
          `Invalid environment variable format: ${envStr}, environment variables should be added as: -e KEY1=value1 -e KEY2=value2`,
        )
      }
      parsedEnv[key] = valueParts.join('=')
    }
  }
  return parsedEnv
}

const VALID_SCOPES = ['project', 'global', 'mcprc', 'mcpjson'] as const
type ConfigScope = (typeof VALID_SCOPES)[number]
const EXTERNAL_SCOPES = [
  'project',
  'global',
  'mcprc',
  'mcpjson',
] as ConfigScope[]

export function ensureConfigScope(scope?: string): ConfigScope {
  if (!scope) return 'project'

  const scopesToCheck =
    process.env.USER_TYPE === 'external' ? EXTERNAL_SCOPES : VALID_SCOPES

  if (!scopesToCheck.includes(scope as ConfigScope)) {
    throw new Error(
      `Invalid scope: ${scope}. Must be one of: ${scopesToCheck.join(', ')}`,
    )
  }

  return scope as ConfigScope
}

export function addMcpServer(
  name: McpName,
  server: McpServerConfig,
  scope: ConfigScope = 'project',
): void {
  if (scope === 'mcprc') {
    if (process.env.NODE_ENV === 'test') {
      addMcprcServerForTesting(name, server)
    } else {
      const mcprcPath = join(getCwd(), '.mcprc')
      let mcprcConfig: Record<string, McpServerConfig> = {}

      if (existsSync(mcprcPath)) {
        try {
          const mcprcContent = readFileSync(mcprcPath, 'utf-8')
          const existingConfig = safeParseJSON(mcprcContent)
          if (existingConfig && typeof existingConfig === 'object') {
            mcprcConfig = existingConfig as Record<string, McpServerConfig>
          }
        } catch {
        }
      }

      mcprcConfig[name] = server

      try {
        writeFileSync(mcprcPath, JSON.stringify(mcprcConfig, null, 2), 'utf-8')
      } catch (error) {
        throw new Error(`Failed to write to .mcprc: ${error}`)
      }
    }
  } else if (scope === 'mcpjson') {
    const mcpJsonPath = join(getCwd(), '.mcp.json')
    let config: Record<string, unknown> = { mcpServers: {} }

    if (existsSync(mcpJsonPath)) {
      try {
        const content = readFileSync(mcpJsonPath, 'utf-8')
        const parsed = safeParseJSON(content)
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          config = parsed as Record<string, unknown>
        }
      } catch {
      }
    }

    const rawServers = (config as { mcpServers?: unknown }).mcpServers
    const servers =
      rawServers && typeof rawServers === 'object' && !Array.isArray(rawServers)
        ? (rawServers as Record<string, McpServerConfig>)
        : ({} as Record<string, McpServerConfig>)

    servers[name] = server
    config.mcpServers = servers

    try {
      writeFileSync(mcpJsonPath, JSON.stringify(config, null, 2), 'utf-8')
    } catch (error) {
      throw new Error(`Failed to write to .mcp.json: ${error}`)
    }
  } else if (scope === 'global') {
    const config = getGlobalConfig()
    if (!config.mcpServers) {
      config.mcpServers = {}
    }
    config.mcpServers[name] = server
    saveGlobalConfig(config)
  } else {
    const config = getCurrentProjectConfig()
    if (!config.mcpServers) {
      config.mcpServers = {}
    }
    config.mcpServers[name] = server
    saveCurrentProjectConfig(config)
  }
}

export function removeMcpServer(
  name: McpName,
  scope: ConfigScope = 'project',
): void {
  if (scope === 'mcprc') {
    if (process.env.NODE_ENV === 'test') {
      removeMcprcServerForTesting(name)
    } else {
      const mcprcPath = join(getCwd(), '.mcprc')
      if (!existsSync(mcprcPath)) {
        throw new Error('No .mcprc file found in this directory')
      }

      try {
        const mcprcContent = readFileSync(mcprcPath, 'utf-8')
        const mcprcConfig = safeParseJSON(mcprcContent) as Record<
          string,
          McpServerConfig
        > | null

        if (
          !mcprcConfig ||
          typeof mcprcConfig !== 'object' ||
          !mcprcConfig[name]
        ) {
          throw new Error(`No MCP server found with name: ${name} in .mcprc`)
        }

        delete mcprcConfig[name]
        writeFileSync(mcprcPath, JSON.stringify(mcprcConfig, null, 2), 'utf-8')
      } catch (error) {
        if (error instanceof Error) {
          throw error
        }
        throw new Error(`Failed to remove from .mcprc: ${error}`)
      }
    }
  } else if (scope === 'mcpjson') {
    const mcpJsonPath = join(getCwd(), '.mcp.json')
    if (!existsSync(mcpJsonPath)) {
      throw new Error('No .mcp.json file found in this directory')
    }

    try {
      const content = readFileSync(mcpJsonPath, 'utf-8')
      const parsed = safeParseJSON(content) as Record<string, unknown> | null
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Invalid .mcp.json format')
      }

      const rawServers = (parsed as { mcpServers?: unknown }).mcpServers
      if (
        !rawServers ||
        typeof rawServers !== 'object' ||
        Array.isArray(rawServers)
      ) {
        throw new Error('Invalid .mcp.json format (missing mcpServers)')
      }

      const servers = rawServers as Record<string, McpServerConfig>
      if (!servers[name]) {
        throw new Error(`No MCP server found with name: ${name} in .mcp.json`)
      }

      delete servers[name]
      ;(parsed as any).mcpServers = servers
      writeFileSync(mcpJsonPath, JSON.stringify(parsed, null, 2), 'utf-8')
    } catch (error) {
      if (error instanceof Error) throw error
      throw new Error(`Failed to remove from .mcp.json: ${error}`)
    }
  } else if (scope === 'global') {
    const config = getGlobalConfig()
    if (!config.mcpServers?.[name]) {
      throw new Error(`No global MCP server found with name: ${name}`)
    }
    delete config.mcpServers[name]
    saveGlobalConfig(config)
  } else {
    const config = getCurrentProjectConfig()
    if (!config.mcpServers?.[name]) {
      throw new Error(`No local MCP server found with name: ${name}`)
    }
    delete config.mcpServers[name]
    saveCurrentProjectConfig(config)
  }
}

export function listMCPServers(): Record<string, McpServerConfig> {
  const pluginServers = listPluginMCPServers()
  const globalConfig = getGlobalConfig()
  const projectFileConfig = getProjectMcpServerDefinitions().servers
  const projectConfig = getCurrentProjectConfig()
  return {
    ...(pluginServers ?? {}),
    ...(globalConfig.mcpServers ?? {}),
    ...(projectFileConfig ?? {}),
    ...(projectConfig.mcpServers ?? {}),
  }
}

export type ScopedMcpServerConfig = McpServerConfig & {
  scope: ConfigScope
}

export function getMcpServer(name: McpName): ScopedMcpServerConfig | undefined {
  const projectConfig = getCurrentProjectConfig()
  const projectFileDefinitions = getProjectMcpServerDefinitions()
  const projectFileConfig = projectFileDefinitions.servers
  const globalConfig = getGlobalConfig()

  if (projectConfig.mcpServers?.[name]) {
    return { ...projectConfig.mcpServers[name], scope: 'project' }
  }

  if (projectFileConfig?.[name]) {
    const source = projectFileDefinitions.sources[name]
    const scope: ConfigScope = source === '.mcp.json' ? 'mcpjson' : 'mcprc'
    return { ...projectFileConfig[name], scope }
  }

  if (globalConfig.mcpServers?.[name]) {
    return { ...globalConfig.mcpServers[name], scope: 'global' }
  }

  return undefined
}

export function getMcprcServerStatus(
  serverName: string,
): 'approved' | 'rejected' | 'pending' {
  const config = getCurrentProjectConfig()
  if (config.approvedMcprcServers?.includes(serverName)) {
    return 'approved'
  }
  if (config.rejectedMcprcServers?.includes(serverName)) {
    return 'rejected'
  }
  return 'pending'
}
